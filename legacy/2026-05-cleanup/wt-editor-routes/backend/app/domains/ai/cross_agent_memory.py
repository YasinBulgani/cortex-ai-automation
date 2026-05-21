"""
Cross-Agent Memory — Agent'lar Arasi Bilgi Paylasimi
=====================================================

Her agent kendi calisma sonuclarini yapilandirilmis sekilde kaydeder.
Diger agent'lar bu bilgiyi sorgulayarak zenginlestirilmis context ile calisir.

Ornek akis:
  1. DataAnalyst → "transfer endpoint'i critical risk" insight'i kaydeder
  2. ScenarioGenerator → DataAnalyst'in risk bilgisini okur, ona gore senaryo uretir
  3. SecurityAudit → onceki agent sonuclarini okur, bilinen risk'lere odaklanir
  4. SelfImproving → tum agent'larin sonuclarini meta-analiz yapar

Kaynak tipleri:
  agent_output   — Agent calisma sonuclari (yapilandirilmis)
  agent_insight  — Agent'in kesfettigi onemli bilgi
  agent_feedback — Kalite puani + iyilestirme onerileri
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CrossAgentMemory:
    """Thread-safe, DB-backed cross-agent bilgi paylasim katmani."""

    # In-memory cache (session boyunca gecerli, pipeline run basina)
    _cache: Dict[str, List[Dict[str, Any]]] = {}
    _run_id: Optional[str] = None
    _project_id: Optional[str] = None

    @classmethod
    def reset(cls, run_id: Optional[str] = None, project_id: Optional[str] = None) -> None:
        """Yeni pipeline run baslangicinda cache'i temizle."""
        cls._cache = {}
        cls._run_id = run_id
        cls._project_id = project_id

    @classmethod
    def publish(
        cls,
        agent_name: str,
        event_type: str,
        data: Dict[str, Any],
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Agent ciktisinisini cross-agent memory'ye yayinla.

        Args:
            agent_name: Yayinlayan agent (orn: "DataAnalyst", "SecurityAudit")
            event_type: Olay tipi:
                - "analysis_complete" — Analiz tamamlandi
                - "risk_finding" — Risk/guvenlik bulgusu
                - "test_generated" — Test case uretildi
                - "quality_score" — Kalite puani verildi
                - "improvement" — Iyilestirme onerisi
                - "pattern_detected" — Patern tespiti
                - "failure_insight" — Hata insight'i
                - "performance_baseline" — Performans referans degeri
            data: Yapilandirilmis veri
            tags: Aranabilir etiketler (orn: ["auth", "transfer", "critical"])
        """
        project_id = str(data.get("project_id", "") or cls._project_id or "").strip()
        if not project_id:
            logger.warning("CrossAgentMemory publish project_id olmadan atlandi: agent=%s event=%s", agent_name, event_type)
            return

        entry = {
            "agent_name": agent_name,
            "event_type": event_type,
            "data": data,
            "tags": tags or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": cls._run_id,
            "project_id": project_id,
        }

        # Cache'e ekle
        key = f"{project_id}:{agent_name}:{event_type}"
        if key not in cls._cache:
            cls._cache[key] = []
        cls._cache[key].append(entry)

        # KnowledgeStore'a da kaydet (kalici hafiza)
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore

            store = KnowledgeStore(project_id=project_id)
            text = cls._format_for_storage(entry)
            store.ingest(
                text=text,
                source="agent_insight",
                metadata={
                    "agent_name": agent_name,
                    "event_type": event_type,
                    "tags": json.dumps(tags or []),
                    "run_id": cls._run_id or "",
                },
                project_id=project_id,
            )
        except Exception as exc:
            logger.debug("CrossAgentMemory KnowledgeStore kayit hatasi: %s", exc)

    @classmethod
    def query(
        cls,
        project_id: str,
        requesting_agent: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        exclude_agent: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Cross-agent memory'den bilgi sorgula.

        Args:
            requesting_agent: Sorgulayan agent (log icin)
            event_types: Filtrelenecek olay tipleri
            tags: En az birinin eslesmesi gereken etiketler
            exclude_agent: Haric tutulacak agent (kendi ciktisini haric tutmak icin)
            limit: Maks sonuc sayisi

        Returns:
            Eslesen entry listesi (en yeniden en eskiye)
        """
        if not project_id:
            return []

        results = []

        for key, entries in cls._cache.items():
            for entry in entries:
                if entry.get("project_id") != project_id:
                    continue
                # Agent filtresi
                if exclude_agent and entry["agent_name"] == exclude_agent:
                    continue

                # Event type filtresi
                if event_types and entry["event_type"] not in event_types:
                    continue

                # Tag filtresi (en az bir eslesme)
                if tags:
                    entry_tags = set(entry.get("tags", []))
                    if not entry_tags.intersection(set(tags)):
                        continue

                results.append(entry)

        # En yeniden en eskiye sirala
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results[:limit]

    @classmethod
    def get_context_for_agent(
        cls,
        agent_name: str,
        project_id: str,
        relevant_tags: Optional[List[str]] = None,
        max_chars: int = 3000,
    ) -> str:
        """
        Belirli bir agent icin zenginlestirilmis context olustur.

        Diger agent'larin ciktilarina gore ozet bir metin uretir.
        """
        entries = cls.query(
            project_id=project_id,
            requesting_agent=agent_name,
            exclude_agent=agent_name,
            tags=relevant_tags,
            limit=15,
        )

        if not entries:
            return ""

        parts = ["## DIGER AGENT BULGULARI\n"]
        char_count = len(parts[0])

        # Agent bazinda grupla
        by_agent: Dict[str, List[Dict[str, Any]]] = {}
        for e in entries:
            a = e["agent_name"]
            if a not in by_agent:
                by_agent[a] = []
            by_agent[a].append(e)

        for agent, agent_entries in by_agent.items():
            section = f"\n### {agent}:\n"
            for e in agent_entries[:5]:
                summary = cls._summarize_entry(e)
                line = f"- [{e['event_type']}] {summary}\n"
                if char_count + len(section) + len(line) > max_chars:
                    break
                section += line
            char_count += len(section)
            parts.append(section)

            if char_count > max_chars:
                break

        return "".join(parts)

    @classmethod
    def get_risk_findings(cls) -> List[Dict[str, Any]]:
        """Tum risk bulgularini getir."""
        return []

    @classmethod
    def get_quality_scores(cls) -> List[Dict[str, Any]]:
        """Tum kalite puanlarini getir."""
        return []

    @classmethod
    def get_failure_insights(cls) -> List[Dict[str, Any]]:
        """Tum hata insight'larini getir."""
        return []

    @classmethod
    def stats(cls, project_id: str) -> Dict[str, Any]:
        """Cross-agent memory istatistikleri."""
        if not project_id:
            return {
                "total_entries": 0,
                "by_agent": {},
                "by_event_type": {},
                "top_tags": {},
                "run_id": cls._run_id,
                "project_id": None,
            }
        total = 0
        by_agent: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        all_tags: Dict[str, int] = {}

        for entries in cls._cache.values():
            for e in entries:
                if e.get("project_id") != project_id:
                    continue
                total += 1
                agent = e["agent_name"]
                by_agent[agent] = by_agent.get(agent, 0) + 1
                etype = e["event_type"]
                by_type[etype] = by_type.get(etype, 0) + 1
                for tag in e.get("tags", []):
                    all_tags[tag] = all_tags.get(tag, 0) + 1

        return {
            "total_entries": total,
            "by_agent": by_agent,
            "by_event_type": by_type,
            "top_tags": dict(sorted(all_tags.items(), key=lambda x: x[1], reverse=True)[:20]),
            "run_id": cls._run_id,
            "project_id": project_id,
        }

    # ── Yardimci Metodlar ────────────────────────────────────────────

    @staticmethod
    def _format_for_storage(entry: Dict[str, Any]) -> str:
        """Entry'yi KnowledgeStore icin metin formatina cevir."""
        parts = [
            f"Agent: {entry['agent_name']}",
            f"Olay: {entry['event_type']}",
        ]
        data = entry.get("data", {})
        if isinstance(data, dict):
            for k, v in list(data.items())[:10]:
                if isinstance(v, (str, int, float, bool)):
                    parts.append(f"{k}: {v}")
                elif isinstance(v, list) and len(v) <= 5:
                    parts.append(f"{k}: {', '.join(str(i) for i in v)}")
        tags = entry.get("tags", [])
        if tags:
            parts.append(f"Etiketler: {', '.join(tags)}")
        return " | ".join(parts)

    @staticmethod
    def _summarize_entry(entry: Dict[str, Any]) -> str:
        """Entry'yi tek satirlik ozete cevir."""
        data = entry.get("data", {})
        if isinstance(data, dict):
            # Onemli alanlari cikar
            summary_parts = []
            for key in ["summary", "finding", "endpoint", "risk_level", "score", "issue", "recommendation"]:
                if key in data:
                    val = data[key]
                    if isinstance(val, str) and len(val) > 100:
                        val = val[:97] + "..."
                    summary_parts.append(f"{key}={val}")
            if summary_parts:
                return " | ".join(summary_parts[:4])
        return str(data)[:150]
