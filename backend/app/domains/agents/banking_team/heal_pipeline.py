"""
HealPipeline -- Test fail -> Heal -> Verify -> Update dongusu.

Akis:
  1. TestRunner fail rapor eder
  2. AutoHealer kırık selector'lari tamir onerir
  3. Playwright MCP ile onerilen selector gerçek browser'da dogrulanir
  4. Dogrulanan selector test dosyasina yazilir
  5. Test tekrar kosulur
  6. Sonuclar KnowledgeStore'a kaydedilir
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Result Dataclass ─────────────────────────────────────────────────────────


@dataclass
class HealPipelineResult:
    """Heal pipeline çalışma sonucu."""
    total_broken: int = 0
    healed: int = 0
    verified: int = 0
    updated_files: int = 0
    details: list[dict] = field(default_factory=list)
    duration_ms: int = 0


# ── Pipeline ─────────────────────────────────────────────────────────────────


class HealPipeline:
    """
    Test fail -> Heal -> Verify -> Update orkestratoru.

    AutoHealer'i Playwright MCP dogrulama ve dosya guncelleme ile birlestirerek
    uctan uca otomatik tamir dongusu saglar.
    """

    def __init__(self, project_root: Path, project_id: str | None = None) -> None:
        self.project_root = Path(project_root)
        self.project_id = project_id
        self._healer = None  # lazy init

    @property
    def healer(self):
        """AutoHealerAgent lazy init."""
        if self._healer is None:
            from app.domains.agents.banking_team.auto_healer import AutoHealerAgent
            self._healer = AutoHealerAgent()
            self._healer._project_id = self.project_id
        return self._healer

    # ── Ana Çalışma Metodu ───────────────────────────────────────────────────

    async def run(
        self,
        failed_tests: list,
        session_id: str = "",
    ) -> HealPipelineResult:
        """Kırık testleri tamir et, dogrula ve dosyalari guncelle.

        Args:
            failed_tests: Kırık test bilgileri listesi.
                Her eleman: {file, test_name, error, selector, dom_snippet, page_url, ...}
            session_id: Playwright MCP oturum ID'si (opsiyonel).

        Returns:
            HealPipelineResult: Toplam sonuclar.
        """
        t0 = time.time()
        result = HealPipelineResult(total_broken=len(failed_tests))

        for test_info in failed_tests[:20]:  # Guvenlik limiti: max 20 test
            detail = await self._process_single(test_info, session_id)
            result.details.append(detail)

            if detail.get("healed"):
                result.healed += 1
            if detail.get("verified_in_browser"):
                result.verified += 1
            if detail.get("file_updated"):
                result.updated_files += 1

        result.duration_ms = int((time.time() - t0) * 1000)

        # Sonuclari KnowledgeStore'a kaydet (fire-and-forget)
        self._save_to_knowledge_store(result)

        return result

    async def _process_single(self, test_info: dict, session_id: str) -> dict:
        """Tek bir kırık testi isle.

        Akis:
          1. Hata mesajindan selector ve DOM context cikart
          2. Session varsa canli DOM al
          3. AutoHealer ile tamir onerileri al
          4. Session varsa gerçek browser'da dogrula
          5. Dogrulanan selector'i dosyaya yaz
        """
        detail: dict = {
            "file": test_info.get("file", ""),
            "test_name": test_info.get("test_name", ""),
            "broken_selector": test_info.get("selector", ""),
            "healed": False,
            "new_selector": "",
            "strategy": "",
            "tier": "",
            "confidence": 0.0,
            "verified_in_browser": False,
            "live_dom_used": False,
            "file_updated": False,
            "error": "",
        }

        try:
            # 1. Hata mesajindan ek bilgi cikart
            error_msg = test_info.get("error", "")
            if error_msg and not test_info.get("selector"):
                parsed = self._parse_playwright_error(error_msg)
                if parsed.get("selector"):
                    test_info["selector"] = parsed["selector"]
                    detail["broken_selector"] = parsed["selector"]
                if parsed.get("line_number"):
                    test_info["line_number"] = parsed["line_number"]

            # 2. Session varsa canli DOM ile zenginlestirilmis healing yap
            if session_id or test_info.get("page_url"):
                heal_result = self.healer.heal_with_live_dom(test_info, session_id)
            else:
                heal_result = self.healer._heal_single(test_info)

            # Sonuclari detail'e aktar
            detail.update({
                "healed": heal_result.get("healed", False),
                "new_selector": heal_result.get("new_selector", ""),
                "strategy": heal_result.get("strategy", ""),
                "tier": heal_result.get("tier", ""),
                "confidence": heal_result.get("confidence", 0.0),
                "verified_in_browser": heal_result.get("verified_in_browser", False),
                "live_dom_used": heal_result.get("live_dom_used", False),
                "screenshot_before": heal_result.get("screenshot_before", ""),
                "screenshot_after": heal_result.get("screenshot_after", ""),
            })

            # 3. Dogrulanan ve auto_update aktifse dosyayi guncelle
            if detail["healed"] and detail["broken_selector"] and detail["new_selector"]:
                file_path = detail.get("file", "")
                if file_path:
                    updated = self._update_test_file(
                        file_path,
                        detail["broken_selector"],
                        detail["new_selector"],
                    )
                    detail["file_updated"] = updated

        except Exception as exc:
            detail["error"] = str(exc)[:500]
            logger.warning("Heal pipeline tek test hatasi: %s", exc)

        return detail

    # ── Hata Ayristirma ──────────────────────────────────────────────────────

    def _parse_playwright_error(self, error: str) -> dict:
        """Playwright hata mesajindan selector, satir numarasi ve DOM bilgisi cikart.

        Ornek hata:
          'Error: locator.click: Timeout 30000ms exceeded.
           Call log:
             - waiting for locator("#login-btn")'

          'page.getByTestId("submit-button") resolved to 0 elements'

        Returns:
            {"selector": "...", "line_number": 0, "dom_context": ""}
        """
        result: dict = {"selector": "", "line_number": 0, "dom_context": ""}

        # Pattern 1: locator("...") veya locator('...')
        loc_match = re.search(r'locator\(["\'](.+?)["\']\)', error)
        if loc_match:
            result["selector"] = loc_match.group(1)

        # Pattern 2: getByTestId("..."), getByRole("..."), getByText("...")
        if not result["selector"]:
            get_match = re.search(r'(getBy\w+)\(["\'](.+?)["\']\)', error)
            if get_match:
                result["selector"] = f"page.{get_match.group(1)}('{get_match.group(2)}')"

        # Pattern 3: page.locator("...")
        if not result["selector"]:
            page_loc = re.search(r'page\.\w+\(["\'](.+?)["\']\)', error)
            if page_loc:
                result["selector"] = page_loc.group(1)

        # Satir numarasi: "at /path/to/file.ts:42:10" veya "file.spec.ts:42"
        line_match = re.search(r'\.(?:spec|test)\.\w+:(\d+)', error)
        if line_match:
            result["line_number"] = int(line_match.group(1))

        return result

    # ── Dosya Guncelleme ─────────────────────────────────────────────────────

    def _update_test_file(
        self,
        file_path: str,
        old_selector: str,
        new_selector: str,
    ) -> bool:
        """Test dosyasinda eski selector'i yenisiyle değiştir.

        Guvenlik onlemleri:
          - Dosya proje dizini icinde olmali
          - Yedek dosya olusturulur (.bak)
          - Sadece tam eslesme degistirilir (partial replace yok)
        """
        try:
            target = Path(file_path)

            # Guvenlik: proje dizini icinde mi?
            try:
                target.resolve().relative_to(self.project_root.resolve())
            except ValueError:
                logger.warning("Guvenlik: %s proje dizini disinda, atlanıyor", file_path)
                return False

            if not target.exists():
                logger.debug("Dosya bulunamadi: %s", file_path)
                return False

            content = target.read_text(encoding="utf-8")

            # Eski selector dosyada var mi?
            if old_selector not in content:
                # Olasi farklilik: tirnak türü degismis olabilir
                alt_selector = old_selector.replace("'", '"')
                if alt_selector not in content:
                    alt_selector = old_selector.replace('"', "'")
                    if alt_selector not in content:
                        logger.debug(
                            "Eski selector dosyada bulunamadi: %s", old_selector[:80],
                        )
                        return False
                old_selector = alt_selector

            # Yedek oluştur
            bak_path = target.with_suffix(target.suffix + ".bak")
            bak_path.write_text(content, encoding="utf-8")

            # Değiştir
            new_content = content.replace(old_selector, new_selector, 1)
            target.write_text(new_content, encoding="utf-8")

            logger.info(
                "Selector guncellendi: %s -> %s (%s)",
                old_selector[:40],
                new_selector[:40],
                file_path,
            )
            return True

        except Exception as exc:
            logger.warning("Dosya guncelleme hatasi (%s): %s", file_path, exc)
            return False

    # ── Istatistik Toplama ───────────────────────────────────────────────────

    def _collect_stats(self, results: list) -> dict:
        """Heal sonuclarindan istatistik cikart.

        Args:
            results: HealPipelineResult.details listesi.

        Returns:
            Aggregated stats dict.
        """
        total = len(results)
        healed = sum(1 for r in results if r.get("healed"))
        verified = sum(1 for r in results if r.get("verified_in_browser"))
        updated = sum(1 for r in results if r.get("file_updated"))

        # Strateji bazinda dagilim
        by_strategy: dict[str, int] = {}
        by_tier: dict[str, int] = {}
        confidences: list[float] = []

        for r in results:
            if r.get("healed"):
                strategy = r.get("strategy", "unknown")
                by_strategy[strategy] = by_strategy.get(strategy, 0) + 1

                tier = r.get("tier", "unknown")
                by_tier[tier] = by_tier.get(tier, 0) + 1

                conf = r.get("confidence", 0.0)
                if conf:
                    confidences.append(conf)

        return {
            "total": total,
            "healed": healed,
            "verified": verified,
            "updated_files": updated,
            "success_rate": round(healed / total, 3) if total else 0.0,
            "verified_rate": round(verified / healed, 3) if healed else 0.0,
            "by_strategy": by_strategy,
            "by_tier": by_tier,
            "avg_confidence": round(
                sum(confidences) / len(confidences), 3,
            ) if confidences else 0.0,
        }

    # ── KnowledgeStore Kayit ─────────────────────────────────────────────────

    def _save_to_knowledge_store(self, result: HealPipelineResult) -> None:
        """Heal sonuclarini KnowledgeStore'a kaydet (fire-and-forget)."""
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            store = KnowledgeStore(project_id=self.project_id)

            stats = self._collect_stats(result.details)
            summary = (
                f"HealPipeline: {result.healed}/{result.total_broken} tamir edildi, "
                f"{result.verified} dogrulandi, {result.updated_files} dosya guncellendi. "
                f"Sure: {result.duration_ms}ms"
            )

            store.ingest(
                text=summary,
                source="insight",
                metadata={
                    "type": "heal_pipeline_run",
                    "total_broken": result.total_broken,
                    "healed": result.healed,
                    "verified": result.verified,
                    "updated_files": result.updated_files,
                    "duration_ms": result.duration_ms,
                    "stats": stats,
                },
                project_id=self.project_id,
            )
        except Exception as exc:
            logger.debug("KnowledgeStore kayit hatasi: %s", exc)
