"""
TestRunnerAgent — Ajan 8 (Sıfır Müdahale İçin Kritik)

Görevi:
  OutputWriterAgent'ın diske yazdığı testleri otomatik çalıştırır:
  - Playwright e2e testleri → npx playwright test e2e/banking/
  - pytest API testleri → pytest api-tests/banking/
  - Sonuçları JSON olarak okur
  - KnowledgeStore'a feedback olarak yazar (self-improving döngüsü kapanır)
  - update_learning_db.py'yi tetikler

Bu ajan sayesinde:
  Kod üretildi → Diske yazıldı → Çalıştırıldı → Sonuçlar öğrenildi → Döngü
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[5]


class TestRunnerAgent(BaseAgent):
    name = "Test Koşucu"
    # LLM kullanmaz — subprocess ile testleri çalıştırır

    def run(self, context: dict) -> AgentResult:
        """
        context keys:
          written_files  — OutputWriterAgent'ın yazdığı dosyalar
          run_id         — Pipeline run ID
          run_playwright — Playwright testleri çalıştır (default: True)
          run_pytest     — pytest testleri çalıştır (default: True)
          timeout        — Her test suite için max saniye (default: 120)
        """
        run_id = context.get("run_id", "run-unknown")
        run_playwright = context.get("run_playwright", True)
        run_pytest_flag = context.get("run_pytest", True)
        timeout = context.get("timeout", 120)

        results: dict = {
            "playwright": None,
            "pytest": None,
            "total_passed": 0,
            "total_failed": 0,
            "learning_ingested": False,
        }

        # Playwright testleri var mı kontrol et
        pw_dir = REPO_ROOT / "e2e" / "banking"
        pw_files = list(pw_dir.glob("*.spec.ts")) if pw_dir.exists() else []

        # pytest testleri var mı kontrol et
        api_dir = REPO_ROOT / "api-tests" / "banking"
        py_files = list(api_dir.glob("test_*.py")) if api_dir.exists() else []

        # ── Playwright ────────────────────────────────────────────────
        if run_playwright and pw_files:
            results["playwright"] = self._run_playwright(run_id, timeout)
            if results["playwright"]:
                results["total_passed"] += results["playwright"].get("passed", 0)
                results["total_failed"] += results["playwright"].get("failed", 0)
        else:
            logger.info("TestRunner: Playwright testi yok, atlanıyor.")

        # ── pytest ────────────────────────────────────────────────────
        if run_pytest_flag and py_files:
            results["pytest"] = self._run_pytest(run_id, timeout)
            if results["pytest"]:
                results["total_passed"] += results["pytest"].get("passed", 0)
                results["total_failed"] += results["pytest"].get("failed", 0)
        else:
            logger.info("TestRunner: pytest testi yok, atlanıyor.")

        # ── KnowledgeStore'a sonuçları gönder ─────────────────────────
        if results["total_passed"] + results["total_failed"] > 0:
            self._ingest_results(results, run_id)
            results["learning_ingested"] = True

        # ── update_learning_db.py'yi tetikle ─────────────────────────
        self._trigger_learning_db(run_id)

        logger.info(
            "TestRunner: pass=%d fail=%d",
            results["total_passed"], results["total_failed"],
        )

        return AgentResult(
            agent_name=self.name,
            success=True,
            data=results,
        )

    # ── Çalıştırma Metodları ─────────────────────────────────────────────────

    def _run_playwright(self, run_id: str, timeout: int) -> dict:
        """npx playwright test e2e/banking/ --reporter=json"""
        report_dir = REPO_ROOT / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"pw_banking_{run_id}.json"

        try:
            proc = subprocess.run(
                [
                    "npx", "playwright", "test", "e2e/banking/",
                    "--reporter=json",
                    f"--output=reports/pw_banking_{run_id}",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**__import__("os").environ, "PLAYWRIGHT_JSON_OUTPUT_NAME": str(report_path)},
            )

            # 1. Once rapor dosyasindan oku (en guvenilir)
            if report_path.exists():
                try:
                    data = json.loads(report_path.read_text(encoding="utf-8"))
                    stats = data.get("stats", {})
                    return {
                        "passed": stats.get("expected", 0),
                        "failed": stats.get("unexpected", 0),
                        "skipped": stats.get("skipped", 0),
                        "duration_ms": stats.get("duration", 0),
                        "exit_code": proc.returncode,
                    }
                except json.JSONDecodeError:
                    pass

            # 2. stdout'dan JSON parse dene
            stdout = proc.stdout.strip()
            if stdout:
                try:
                    data = json.loads(stdout)
                    stats = data.get("stats", {})
                    return {
                        "passed": stats.get("expected", 0),
                        "failed": stats.get("unexpected", 0),
                        "skipped": stats.get("skipped", 0),
                        "duration_ms": stats.get("duration", 0),
                        "exit_code": proc.returncode,
                    }
                except json.JSONDecodeError:
                    pass

            # 3. Fallback: stdout'dan regex ile parse
            import re as _re
            passed = 0
            failed = 0
            combined = proc.stdout + proc.stderr
            m = _re.search(r"(\d+)\s+passed", combined)
            if m:
                passed = int(m.group(1))
            m = _re.search(r"(\d+)\s+failed", combined)
            if m:
                failed = int(m.group(1))

            return {
                "passed": passed,
                "failed": failed,
                "exit_code": proc.returncode,
                "output": combined[-500:] if not passed and not failed else "",
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Timeout ({timeout}s)", "passed": 0, "failed": 0}
        except FileNotFoundError:
            return {"error": "npx bulunamadi", "passed": 0, "failed": 0}
        except Exception as e:
            return {"error": str(e), "passed": 0, "failed": 0}

    def _run_pytest(self, run_id: str, timeout: int) -> dict:
        """pytest api-tests/banking/ --json-report"""
        report_path = REPO_ROOT / "reports" / f"pytest_banking_{run_id}.json"
        try:
            proc = subprocess.run(
                [
                    "python", "-m", "pytest",
                    "api-tests/banking/",
                    f"--json-report-file=reports/pytest_banking_{run_id}.json",
                    "-q", "--tb=short",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            # JSON raporu oku
            if report_path.exists():
                data = json.loads(report_path.read_text())
                summary = data.get("summary", {})
                return {
                    "passed": summary.get("passed", 0),
                    "failed": summary.get("failed", 0),
                    "error": summary.get("error", 0),
                    "duration": data.get("duration", 0),
                    "exit_code": proc.returncode,
                }
            # JSON yoksa stdout'tan parse et
            import re
            match = re.search(r"(\d+) passed", proc.stdout)
            passed = int(match.group(1)) if match else 0
            match = re.search(r"(\d+) failed", proc.stdout)
            failed = int(match.group(1)) if match else 0
            return {"passed": passed, "failed": failed, "exit_code": proc.returncode}
        except subprocess.TimeoutExpired:
            return {"error": f"Timeout ({timeout}s)", "passed": 0, "failed": 0}
        except Exception as e:
            return {"error": str(e), "passed": 0, "failed": 0}

    def _ingest_results(self, results: dict, run_id: str) -> None:
        """Test sonuçlarını KnowledgeStore'a gönder."""
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            project_id = getattr(self, "_project_id", None)
            store = KnowledgeStore(project_id=project_id)

            pw = results.get("playwright") or {}
            pt = results.get("pytest") or {}

            text = (
                f"Banking Test Koşusu {run_id}: "
                f"Playwright: pass={pw.get('passed', 0)} fail={pw.get('failed', 0)} | "
                f"pytest: pass={pt.get('passed', 0)} fail={pt.get('failed', 0)} | "
                f"Toplam: pass={results['total_passed']} fail={results['total_failed']}"
            )
            store.ingest(
                text=text,
                source="execution",
                metadata={"run_id": run_id, "agent": self.name},
                project_id=project_id,
            )
        except Exception as e:
            logger.debug("TestRunner ingest hatası: %s", e)

    def _trigger_learning_db(self, run_id: str) -> None:
        """update_learning_db.py'yi arka planda tetikle."""
        import threading

        def _run():
            try:
                script = REPO_ROOT / "scripts" / "update_learning_db.py"
                if not script.exists():
                    return
                subprocess.run(
                    ["python", str(script), "--run-id", run_id, "--optimize"],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    timeout=60,
                )
                logger.debug("Learning DB güncellendi: %s", run_id)
            except Exception as e:
                logger.debug("Learning DB tetikleme hatası: %s", e)

        threading.Thread(target=_run, daemon=True).start()
