"""
Knowledge Lifecycle Manager — KnowledgeStore'un sınırsız büyümesini önler.

3 temel mekanizma:
  1. TTL & Pruning    — Eski kayıtları sil (source bazlı farklı ömürler)
  2. Deduplication    — Benzer embedding'leri tespit et, birleştir
  3. Summarization    — N eski insight'ı 1 özet'e sıkıştır (LLM ile)

Çalışma zamanı: Her gece pipeline'dan ÖNCE (01:55) otomatik tetiklenir.

Büyüme kontrolü:
  - execution kayıtları:  30 gün (test sonuçları hızla eski kalır)
  - insight kayıtları:    90 gün (ajan öğrenimleri daha uzun geçerli)
  - feature_file:         180 gün (dosya değişmediyse silme, değiştiyse güncelle)
  - docs:                 180 gün
  - error_pattern:        60 gün (hata çözüldüyse gereksiz)
  - code_change:          30 gün (git log'dan yeniden üretilir)
  - chat_history:         60 gün (kullanıcı sohbetleri)

Hedef: Toplam kayıt sayısı hiçbir zaman 10,000'i geçmesin.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Source bazlı ömür (gün)
SOURCE_TTL_DAYS: dict[str, int] = {
    "execution": 30,
    "insight": 90,
    "feature_file": 180,
    "docs": 180,
    "error_pattern": 60,
    "code_change": 30,
    "chat_history": 60,
}

# Bu eşik aşılırsa agresif pruning başlar
MAX_TOTAL_RECORDS = 10_000

# Deduplication: bu benzerliğin üstündeki kayıtlar aynı kabul edilir
DEDUP_SIMILARITY_THRESHOLD = 0.92


class KnowledgeLifecycleManager:
    """KnowledgeStore'un sağlıklı boyutta kalmasını sağlar."""

    def __init__(self, db_url: str | None = None):
        self._db_url = db_url
        self._conn = None

    def _get_conn(self):
        import psycopg2
        if self._conn is None or self._conn.closed:
            from app.domains.ai.knowledge_store import KnowledgeStore
            store = KnowledgeStore(self._db_url)
            dsn = store._db_url.replace("postgresql+psycopg2://", "postgresql://")
            self._conn = psycopg2.connect(dsn)
            self._conn.autocommit = True
        return self._conn

    def _supports_project_scope(self) -> bool:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'project_knowledge'
                  AND column_name = 'project_id'
                """
            )
            return cur.fetchone() is not None

    def _load_summary_rows(self, source: str, cutoff: datetime, batch_size: int):
        conn = self._get_conn()
        with conn.cursor() as cur:
            if self._supports_project_scope():
                cur.execute(
                    """
                    SELECT project_id, id, content, created_at
                    FROM project_knowledge
                    WHERE source = %s AND created_at < %s
                    ORDER BY project_id ASC, created_at ASC
                    LIMIT %s
                    """,
                    (source, cutoff, batch_size),
                )
                rows = cur.fetchall()
                if not rows:
                    return None, []
                project_id = rows[0][0]
                filtered = [r for r in rows if r[0] == project_id]
                return project_id, filtered

            cur.execute(
                """
                SELECT id, content, created_at
                FROM project_knowledge
                WHERE source = %s AND created_at < %s
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (source, cutoff, batch_size),
            )
            return None, cur.fetchall()

    # ── 1. TTL Pruning ───────────────────────────────────────────────────────

    def prune_expired(self) -> dict[str, int]:
        """Her source türü için TTL süresi dolmuş kayıtları sil."""
        conn = self._get_conn()
        deleted = {}
        now = datetime.now(timezone.utc)

        for source, ttl_days in SOURCE_TTL_DAYS.items():
            cutoff = now - timedelta(days=ttl_days)
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM project_knowledge WHERE source = %s AND created_at < %s",
                    (source, cutoff),
                )
                count = cur.rowcount
                if count > 0:
                    deleted[source] = count
                    logger.info("Pruned %d expired %s records (TTL: %d days)", count, source, ttl_days)

        return deleted

    # ── 2. Deduplication ─────────────────────────────────────────────────────

    def deduplicate(self) -> int:
        """
        Aynı source içinde çok benzer embedding'leri bul → eskisini sil.
        pgvector yoksa text hash bazlı dedup yapar.
        """
        conn = self._get_conn()
        removed = 0

        with conn.cursor() as cur:
            # Basit text-hash deduplication (pgvector olmadan da çalışır)
            # Aynı source + aynı content hash → eskisini sil
            cur.execute("""
                DELETE FROM project_knowledge
                WHERE id IN (
                    SELECT id FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY source, md5(content)
                                   ORDER BY created_at DESC
                               ) as rn
                        FROM project_knowledge
                    ) dupes
                    WHERE rn > 1
                )
            """)
            removed = cur.rowcount
            if removed > 0:
                logger.info("Deduplication: %d duplicate records removed", removed)

        return removed

    # ── 3. Summarization ─────────────────────────────────────────────────────

    def summarize_old_insights(self, days_old: int = 30, batch_size: int = 20) -> int:
        """
        N gün'den eski insight'ları LLM ile özetle → 1 kayıt yap, eskileri sil.
        Bu sayede 20 eski insight → 1 özet'e sıkışır.
        """
        conn = self._get_conn()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)
        project_id, rows = self._load_summary_rows("insight", cutoff, batch_size)

        if len(rows) < 5:
            return 0

        content_idx = 2 if project_id is not None else 1
        created_idx = 3 if project_id is not None else 2
        id_idx = 1 if project_id is not None else 0
        combined = "\n".join([f"- {r[content_idx][:200]}" for r in rows])
        date_range = f"{rows[0][created_idx].strftime('%Y-%m-%d')} → {rows[-1][created_idx].strftime('%Y-%m-%d')}"

        try:
            from app.domains.agents.banking_team.base_agent import BaseAgent

            class _Summarizer(BaseAgent):
                name = "Bilgi Özetleyici"
                temperature = 0.1
                max_tokens = 512

            summarizer = _Summarizer()
            summary = summarizer.call(
                system="Türkçe yanıt ver. Verilen QA insight'ları özetle. Sadece en önemli bulgular, kalıplar ve öğrenimleri 3-5 maddede yaz.",
                user=f"Tarih aralığı: {date_range}\n\nÖzetlenecek insight'lar:\n{combined[:2000]}",
            )

            if summary and len(summary) > 50:
                from app.domains.ai.knowledge_store import KnowledgeStore
                store = KnowledgeStore(self._db_url, project_id=project_id)
                store.ingest(
                    text=f"[ÖZET {date_range}] {summary}",
                    source="insight",
                    metadata={
                        "type": "summary",
                        "original_count": len(rows),
                        "date_range": date_range,
                    },
                    project_id=project_id,
                )

                ids = [r[id_idx] for r in rows]
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM project_knowledge WHERE id = ANY(%s)",
                        (ids,),
                    )
                logger.info(
                    "Summarized %d insights into 1 record (%s)",
                    len(rows), date_range,
                )
                return len(rows)

        except Exception as e:
            logger.warning("Summarization failed: %s", e)

        return 0

    # ── 3b. Chat History Summarization ───────────────────────────────────────

    def summarize_old_chats(self, days_old: int = 30, batch_size: int = 30) -> int:
        """Eski chat_history kayıtlarını LLM ile özetle → sıkıştır."""
        conn = self._get_conn()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)
        project_id, rows = self._load_summary_rows("chat_history", cutoff, batch_size)

        if len(rows) < 5:
            return 0

        content_idx = 2 if project_id is not None else 1
        created_idx = 3 if project_id is not None else 2
        id_idx = 1 if project_id is not None else 0
        combined = "\n".join([f"- {r[content_idx][:150]}" for r in rows])
        date_range = f"{rows[0][created_idx].strftime('%Y-%m-%d')} → {rows[-1][created_idx].strftime('%Y-%m-%d')}"

        try:
            from app.domains.agents.banking_team.base_agent import BaseAgent

            class _ChatSummarizer(BaseAgent):
                name = "Sohbet Özetleyici"
                temperature = 0.1
                max_tokens = 512

            summarizer = _ChatSummarizer()
            summary = summarizer.call(
                system="Türkçe yanıt ver. Kullanıcı-AI sohbet geçmişini özetle. Sık sorulan konuları, tercih edilen test stratejilerini ve tekrar eden sorunları 3-5 maddede yaz.",
                user=f"Tarih aralığı: {date_range}\n\nSohbetler:\n{combined[:2000]}",
            )

            if summary and len(summary) > 50:
                from app.domains.ai.knowledge_store import KnowledgeStore
                store = KnowledgeStore(self._db_url, project_id=project_id)
                store.ingest(
                    text=f"[SOHBET ÖZETİ {date_range}] {summary}",
                    source="chat_history",
                    metadata={"type": "summary", "original_count": len(rows), "date_range": date_range},
                    project_id=project_id,
                )
                ids = [r[id_idx] for r in rows]
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM project_knowledge WHERE id = ANY(%s)", (ids,))
                logger.info("Summarized %d chat records into 1 (%s)", len(rows), date_range)
                return len(rows)

        except Exception as e:
            logger.warning("Chat summarization failed: %s", e)

        return 0

    # ── 4. Emergency Trim ─────────────────────────────────────────────────────

    def emergency_trim(self) -> int:
        """MAX_TOTAL_RECORDS aşıldıysa en eski kayıtları sil."""
        conn = self._get_conn()

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM project_knowledge")
            total = cur.fetchone()[0]

        if total <= MAX_TOTAL_RECORDS:
            return 0

        excess = total - MAX_TOTAL_RECORDS + 1000
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM project_knowledge
                WHERE id IN (
                    SELECT id FROM project_knowledge
                    ORDER BY created_at ASC
                    LIMIT %s
                )
                """,
                (excess,),
            )
            removed = cur.rowcount
            logger.warning(
                "Emergency trim: %d records removed (total was %d, max %d)",
                removed, total, MAX_TOTAL_RECORDS,
            )
        return removed

    # ── Ana Çalıştırma ───────────────────────────────────────────────────────

    def run_lifecycle(self) -> dict:
        """
        Tüm lifecycle adımlarını sırayla çalıştır.
        Her gece 01:55'te scheduler tarafından tetiklenir.
        """
        logger.info("Knowledge Lifecycle Manager başlıyor...")
        report = {
            "pruned": {},
            "deduplicated": 0,
            "summarized_insights": 0,
            "summarized_chats": 0,
            "emergency_trimmed": 0,
        }

        try:
            report["pruned"] = self.prune_expired()
            report["deduplicated"] = self.deduplicate()
            report["summarized_insights"] = self.summarize_old_insights()
            report["summarized_chats"] = self.summarize_old_chats()
            report["emergency_trimmed"] = self.emergency_trim()
        except Exception as e:
            report["error"] = str(e)
            logger.error("Lifecycle error: %s", e)

        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM project_knowledge")
                report["remaining_records"] = cur.fetchone()[0]
        except Exception:
            pass

        logger.info("Knowledge Lifecycle tamamlandı: %s", report)
        return report
