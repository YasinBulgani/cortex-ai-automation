"""
UnifiedHealingBridge — Engine self-healing ile E2E (TS) self-healing
arasindaki koprü.

Bu modul:
1. Engine'in SelfHealingEngine sonuclarini ortak formata donusturur
2. Heal sonuclarini TS tarafindaki healing-log.json ile uyumlu kaydeder
3. LocatorRecovery sonuclarini locator_repository.json'a geri yazar
4. CI/CD pipeline'lari icin birlesik heal raporu uretir

Boylece 3 ayri heal mekanizmasi (engine Python, e2e TS helpers,
e2e TS self-healer) tek bir veri akisinda birlesir.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class UnifiedHealingBridge:
    """Tum heal sonuclarini birlestiren orkestrator."""

    def __init__(self):
        from core.self_healing.healer import SelfHealingEngine

        self.engine = SelfHealingEngine()
        self._unified_log_path = Path(settings.REPORTS_DIR) / "unified-healing-log.json"
        self._locator_repo_path = Path("locators/locator_repository.json")

    def heal_and_record(
        self,
        test_id: str,
        error_message: str,
        page_url: str = "",
        page_content: str = "",
        dom_snapshot: str = "",
        source: str = "engine",
    ) -> dict:
        """
        Heal islemini calistir ve sonucu birlesik formatta kaydet.

        Returns:
            {
                "healed": bool,
                "new_locator": str,
                "confidence": float,
                "strategy": str,
                "category": str,
                "source": str,
                "duration_ms": int,
            }
        """
        start = time.time()
        result = self.engine.diagnose_and_heal(
            test_id=test_id,
            error_message=error_message,
            page_content=page_content,
            dom_snapshot=dom_snapshot,
        )

        duration_ms = int((time.time() - start) * 1000)

        if result is None:
            output = {
                "healed": False,
                "new_locator": "",
                "confidence": 0.0,
                "strategy": "none",
                "category": "unknown",
                "source": source,
                "duration_ms": duration_ms,
            }
        else:
            output = {
                "healed": result.auto_applied,
                "new_locator": result.fix_applied,
                "confidence": result.confidence,
                "strategy": result.category.value,
                "category": result.category.value,
                "source": source,
                "duration_ms": result.duration_ms or duration_ms,
            }

            if result.auto_applied and result.category.value == "selector":
                self._update_locator_repo(
                    test_id, error_message, result.fix_applied
                )

        self._append_unified_log(test_id, page_url, output)
        return output

    def get_unified_stats(self) -> dict:
        """Engine + TS tarafindaki heal sonuclarini birlestir."""
        engine_stats = self.engine.get_stats()

        ts_log_path = Path(settings.REPORTS_DIR) / "bdd" / "healing-log.json"
        ts_stats = {"total": 0, "healed": 0}

        if ts_log_path.exists():
            try:
                with open(ts_log_path) as f:
                    ts_records = json.load(f)
                ts_stats["total"] = len(ts_records)
                ts_stats["healed"] = sum(
                    1 for r in ts_records if r.get("result", {}).get("healed")
                )
            except (json.JSONDecodeError, OSError):
                pass

        total = engine_stats.get("total", 0) + ts_stats["total"]
        success = engine_stats.get("success", 0) + ts_stats["healed"]

        return {
            "total": total,
            "success": success,
            "success_rate": round(success / total, 2) if total > 0 else 0,
            "engine": engine_stats,
            "typescript": ts_stats,
        }

    def _update_locator_repo(
        self, test_id: str, error_msg: str, new_locator: str
    ) -> None:
        """Basarili selector heal sonrasinda locator repo'yu guncelle."""
        if not self._locator_repo_path.exists():
            return

        try:
            with open(self._locator_repo_path) as f:
                repo = json.load(f)

            for _page_name, page_def in repo.items():
                for _elem_name, elem in page_def.get("elements", {}).items():
                    old_tid = elem.get("test_id", "")
                    if old_tid and old_tid in error_msg:
                        elem["_last_healed"] = {
                            "test_id": test_id,
                            "new_locator": new_locator,
                            "timestamp": time.time(),
                        }
                        logger.info(
                            "Locator repo updated: %s.%s healed",
                            _page_name,
                            _elem_name,
                        )

            with open(self._locator_repo_path, "w", encoding="utf-8") as f:
                json.dump(repo, f, indent=2, ensure_ascii=False)

        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to update locator repo: %s", exc)

    def _append_unified_log(
        self, test_id: str, page_url: str, result: dict
    ) -> None:
        """Birlesik heal loguna kayit ekle."""
        try:
            self._unified_log_path.parent.mkdir(parents=True, exist_ok=True)

            records: list[dict] = []
            if self._unified_log_path.exists():
                try:
                    with open(self._unified_log_path) as f:
                        records = json.load(f)
                except (json.JSONDecodeError, OSError):
                    records = []

            records.append(
                {
                    "test_id": test_id,
                    "page_url": page_url,
                    "timestamp": time.time(),
                    **result,
                }
            )

            with open(self._unified_log_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, ensure_ascii=False)

        except OSError:
            logger.warning("Failed to write unified healing log")
