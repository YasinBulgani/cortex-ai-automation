"""
OutputWriterAgent — Ajan 7 (Sıfır Müdahale İçin Kritik)

Görevi:
  Üretilen tüm kodları doğru klasörlere otomatik yazar:
  - BDD .feature → engine/features/ai_generated/
  - Playwright .spec.ts → e2e/banking/
  - pytest API testleri → api-tests/banking/
  - Regülasyon kuralları → docs/regulation_rules.json
  - Senaryo listesi → reports/scenarios_{run_id}.json
  - Otomasyon matrisi → reports/automation_matrix_{run_id}.json

Kullanıcı hiçbir şey yapmak zorunda değil — dosyalar otomatik oluşur.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[5]


class OutputWriterAgent(BaseAgent):
    name = "Çıktı Yazıcı"
    # LLM kullanmaz — saf dosya yazma ajanı

    def run(self, context: dict) -> AgentResult:
        """
        context keys:
          run_id            — Pipeline run ID
          scenarios         — Üretilen senaryo listesi
          regulation_rules  — Regülasyon kural motoru
          automation_matrix — Otomasyon uygunluk matrisi
          generated_code    — BDD + Playwright + API kodu
          manual_keys       — Manuel test key listesi
        """
        run_id = context.get("run_id", "run-unknown")
        written: list[str] = []
        errors: list[str] = []

        # ── 1. BDD Feature Dosyaları ──────────────────────────────────
        bdd_dir = REPO_ROOT / "engine" / "features" / "ai_generated"
        bdd_dir.mkdir(parents=True, exist_ok=True)

        for item in context.get("generated_code", {}).get("bdd_features", []):
            try:
                fname = item.get("feature_file", f"scenario_{run_id}.feature")
                # Dosya adını temizle
                fname = fname.replace("/", "_").replace("\\", "_")
                if not fname.endswith(".feature"):
                    fname += ".feature"
                fpath = bdd_dir / fname
                fpath.write_text(item.get("content", ""), encoding="utf-8")
                written.append(str(fpath.relative_to(REPO_ROOT)))
            except Exception as e:
                errors.append(f"BDD yazma hatası: {e}")

        # ── 2. Playwright Testleri ────────────────────────────────────
        pw_dir = REPO_ROOT / "e2e" / "banking"
        pw_dir.mkdir(parents=True, exist_ok=True)

        for item in context.get("generated_code", {}).get("playwright_tests", []):
            try:
                fpath_str = item.get("file_path", f"e2e/banking/test_{run_id}.spec.ts")
                # Güvenli yol: sadece dosya adını al
                fname = Path(fpath_str).name
                if not fname.endswith(".spec.ts"):
                    fname += ".spec.ts"
                fpath = pw_dir / fname
                fpath.write_text(item.get("content", ""), encoding="utf-8")
                written.append(str(fpath.relative_to(REPO_ROOT)))
            except Exception as e:
                errors.append(f"Playwright yazma hatası: {e}")

        # ── 3. API Testleri ───────────────────────────────────────────
        api_dir = REPO_ROOT / "api-tests" / "banking"
        api_dir.mkdir(parents=True, exist_ok=True)

        for item in context.get("generated_code", {}).get("api_tests", []):
            try:
                fpath_str = item.get("file_path", f"api-tests/banking/test_{run_id}.py")
                fname = Path(fpath_str).name
                if not fname.endswith(".py"):
                    fname += ".py"
                fpath = api_dir / fname
                fpath.write_text(item.get("content", ""), encoding="utf-8")
                written.append(str(fpath.relative_to(REPO_ROOT)))
            except Exception as e:
                errors.append(f"API test yazma hatası: {e}")

        # ── 4. Regülasyon Kuralları ───────────────────────────────────
        reports_dir = REPO_ROOT / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        reg_rules = context.get("regulation_rules", {})
        if reg_rules:
            try:
                rpath = reports_dir / f"regulation_rules_{run_id}.json"
                rpath.write_text(
                    json.dumps(reg_rules, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                written.append(str(rpath.relative_to(REPO_ROOT)))
            except Exception as e:
                errors.append(f"Regülasyon yazma hatası: {e}")

        # ── 5. Senaryo Listesi ────────────────────────────────────────
        scenarios = context.get("scenarios", [])
        if scenarios:
            try:
                spath = reports_dir / f"scenarios_{run_id}.json"
                spath.write_text(
                    json.dumps(scenarios, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                written.append(str(spath.relative_to(REPO_ROOT)))
            except Exception as e:
                errors.append(f"Senaryo yazma hatası: {e}")

        # ── 6. Otomasyon Matrisi ──────────────────────────────────────
        matrix = context.get("automation_matrix", [])
        if matrix:
            try:
                mpath = reports_dir / f"automation_matrix_{run_id}.json"
                mpath.write_text(
                    json.dumps(matrix, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                written.append(str(mpath.relative_to(REPO_ROOT)))
            except Exception as e:
                errors.append(f"Matris yazma hatası: {e}")

        # ── 7. Manuel Key Listesi ─────────────────────────────────────
        manual_keys = context.get("manual_keys", [])
        if manual_keys:
            try:
                kpath = reports_dir / f"manual_keys_{run_id}.json"
                kpath.write_text(
                    json.dumps(manual_keys, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                written.append(str(kpath.relative_to(REPO_ROOT)))
            except Exception as e:
                errors.append(f"Manuel key yazma hatası: {e}")

        # ── 8. Run Özet Raporu ────────────────────────────────────────
        try:
            summary = {
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "written_files": written,
                "scenario_count": len(scenarios),
                "bdd_count": len(context.get("generated_code", {}).get("bdd_features", [])),
                "playwright_count": len(context.get("generated_code", {}).get("playwright_tests", [])),
                "api_test_count": len(context.get("generated_code", {}).get("api_tests", [])),
                "errors": errors,
            }
            spath = reports_dir / f"run_summary_{run_id}.json"
            spath.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            written.append(str(spath.relative_to(REPO_ROOT)))
        except Exception as e:
            errors.append(f"Özet yazma hatası: {e}")

        logger.info("OutputWriter: %d dosya yazıldı, %d hata", len(written), len(errors))

        return AgentResult(
            agent_name=self.name,
            success=len(errors) == 0,
            data={
                "written_files": written,
                "file_count": len(written),
                "errors": errors,
            },
        )
