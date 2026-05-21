"""
bgts_reporter.py — TestwrightAI raporlama modülü (engine/core/reporter.py wrapper'ı)

Mevcut Reporter sınıfını DEĞİŞTİRMEDEN, TestwrightAI'a özgü rapor formatları sunar:
  - HTML (Tailwind dark theme, Türkçe)
  - JSON (makine okunabilir)
  - CSV (paydaşlar için)
  - Trend raporu (geçmiş koşularla karşılaştırma)
  - Slack/Teams webhook bildirimi
  - Executive summary
"""
from __future__ import annotations

import csv
import io
import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.settings import settings

TEMPLATES_DIR = ROOT.parent / "reports" / "templates"
REPORTS_OUTPUT_DIR = settings.REPORTS_DIR


class ReportTemplate:
    """Basit şablon motoru — Jinja2'ye gerek kalmadan {{ var }} interpolasyonu."""

    def __init__(self, template_path: Path | str):
        self._path = Path(template_path)
        self._content = ""

    def load(self) -> "ReportTemplate":
        if self._path.exists():
            self._content = self._path.read_text(encoding="utf-8")
        return self

    def render(self, **kwargs: Any) -> str:
        output = self._content
        for key, value in kwargs.items():
            output = output.replace("{{ " + key + " }}", str(value))
        return output


class TestwrightAIReporter:
    """TestwrightAI'a özelleştirilmiş rapor üretici."""

    def __init__(self, report_name: str = "bgts_rapor"):
        self.report_name = report_name
        self.ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def _env_info() -> dict:
        return {
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "python": platform.python_version(),
            "tarih": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "base_url": os.getenv("BASE_URL", "http://localhost:3000"),
            "ortam": os.getenv("TEST_ENV", "test"),
        }

    # ── HTML Raporu ───────────────────────────────────────────

    def generate_html_report(self, results: dict) -> str:
        REPORTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        template_path = TEMPLATES_DIR / "html_report.html"
        out_path = REPORTS_OUTPUT_DIR / f"{self.report_name}_{self.ts}.html"

        env = self._env_info()
        failures = results.get("failures", [])
        total = results.get("total", 0)
        passed = results.get("passed", 0)
        failed = results.get("failed", 0)
        skipped = results.get("skipped", 0)
        duration = results.get("duration_seconds", 0)
        success_rate = round(passed / total * 100, 1) if total else 0

        failure_rows = self._build_failure_rows_html(failures)
        pass_pct = success_rate
        fail_pct = round(100 - success_rate, 1)

        env_rows = "".join(
            f'<tr><td class="env-label">{k}</td><td class="env-value">{v}</td></tr>'
            for k, v in env.items()
        )

        if template_path.exists():
            tpl = ReportTemplate(template_path).load()
            html = tpl.render(
                report_title=self.report_name.replace("_", " ").upper(),
                timestamp=env["tarih"],
                total=str(total),
                passed=str(passed),
                failed=str(failed),
                skipped=str(skipped),
                duration=f"{duration:.1f}",
                success_rate=f"{success_rate:.1f}",
                pass_pct=f"{pass_pct:.1f}",
                fail_pct=f"{fail_pct:.1f}",
                failure_rows=failure_rows,
                env_rows=env_rows,
                year=str(datetime.now().year),
            )
        else:
            html = self._fallback_html(results, env)

        out_path.write_text(html, encoding="utf-8")
        return str(out_path)

    def _build_failure_rows_html(self, failures: list[dict]) -> str:
        if not failures:
            return '<tr><td colspan="4" class="empty-msg">Tüm testler başarılı!</td></tr>'
        rows = []
        for i, f in enumerate(failures, 1):
            detail = (f.get("text") or f.get("message") or "").replace("<", "&lt;").replace(">", "&gt;")
            rows.append(
                f'<tr class="failure-row" onclick="toggleDetail(this)">'
                f'<td>{i}</td>'
                f'<td class="test-name">{f.get("test", "")}</td>'
                f'<td class="fail-type">{f.get("type", "AssertionError")}</td>'
                f'<td class="fail-msg">{f.get("message", "")[:120]}</td>'
                f'</tr>'
                f'<tr class="detail-row" style="display:none">'
                f'<td colspan="4"><pre>{detail}</pre></td>'
                f'</tr>'
            )
        return "\n".join(rows)

    @staticmethod
    def _fallback_html(results: dict, env: dict) -> str:
        total = results.get("total", 0)
        passed = results.get("passed", 0)
        failed = results.get("failed", 0)
        return f"""<!DOCTYPE html><html lang='tr'><head><meta charset='UTF-8'>
<title>TestwrightAI Test Raporu</title></head><body style='background:#0f172a;color:#e2e8f0;font-family:sans-serif;padding:2rem'>
<h1>TestwrightAI Test Raporu</h1>
<p>Tarih: {env['tarih']}</p>
<p>Toplam: {total} | Başarılı: {passed} | Başarısız: {failed}</p>
</body></html>"""

    # ── JSON Raporu ───────────────────────────────────────────

    def generate_json_report(self, results: dict) -> str:
        REPORTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = REPORTS_OUTPUT_DIR / f"{self.report_name}_{self.ts}.json"
        payload = {
            "rapor_adi": self.report_name,
            "tarih": datetime.now().isoformat(),
            "ortam": self._env_info(),
            "sonuclar": results,
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(out_path)

    # ── Executive Summary ─────────────────────────────────────

    def generate_summary(self, results: dict) -> dict:
        total = results.get("total", 0)
        passed = results.get("passed", 0)
        failed = results.get("failed", 0)
        skipped = results.get("skipped", 0)
        duration = results.get("duration_seconds", 0)
        failures = results.get("failures", [])

        top_failures = [
            {"test": f.get("test", ""), "mesaj": f.get("message", "")}
            for f in failures[:5]
        ]

        verdict = "BAŞARILI" if failed == 0 else "BAŞARISIZ"

        return {
            "karar": verdict,
            "toplam": total,
            "basarili": passed,
            "basarisiz": failed,
            "atlanan": skipped,
            "basari_orani": round(passed / total * 100, 2) if total else 0,
            "sure_saniye": duration,
            "en_kritik_hatalar": top_failures,
            "tarih": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "ortam": self._env_info(),
        }

    # ── Trend Raporu ──────────────────────────────────────────

    def generate_trend_report(self, history_dir: str | Path) -> dict:
        history_path = Path(history_dir)
        runs: list[dict] = []

        if history_path.exists():
            for jf in sorted(history_path.glob("bgts_rapor_*.json"))[-20:]:
                try:
                    data = json.loads(jf.read_text(encoding="utf-8"))
                    res = data.get("sonuclar", data)
                    runs.append({
                        "dosya": jf.name,
                        "tarih": data.get("tarih", ""),
                        "toplam": res.get("total", 0),
                        "basarili": res.get("passed", 0),
                        "basarisiz": res.get("failed", 0),
                        "basari_orani": round(
                            res.get("passed", 0) / max(res.get("total", 1), 1) * 100, 2
                        ),
                    })
                except (json.JSONDecodeError, KeyError):
                    continue

        trend = "stabil"
        if len(runs) >= 2:
            last_two = runs[-2:]
            diff = last_two[1]["basari_orani"] - last_two[0]["basari_orani"]
            if diff > 5:
                trend = "iyileşiyor"
            elif diff < -5:
                trend = "kötüleşiyor"

        return {
            "trend": trend,
            "son_kosular": runs,
            "toplam_kosu": len(runs),
        }

    # ── Webhook Bildirimi ─────────────────────────────────────

    def send_notification(self, results: dict, channel: str = "slack") -> bool:
        """Slack veya Teams webhook'una bildirim gönderir."""
        import urllib.request
        import urllib.error

        summary = self.generate_summary(results)
        webhook_url = os.getenv(f"WEBHOOK_{channel.upper()}_URL", "")

        if not webhook_url:
            return False

        emoji = "\u2705" if summary["karar"] == "BAŞARILI" else "\u274c"
        text = (
            f"{emoji} *TestwrightAI Test Sonuçları*\n"
            f"Karar: *{summary['karar']}*\n"
            f"Toplam: {summary['toplam']} | "
            f"Başarılı: {summary['basarili']} | "
            f"Başarısız: {summary['basarisiz']} | "
            f"Atlanan: {summary['atlanan']}\n"
            f"Başarı Oranı: %{summary['basari_orani']}\n"
            f"Süre: {summary['sure_saniye']}s\n"
            f"Tarih: {summary['tarih']}"
        )

        if summary["en_kritik_hatalar"]:
            text += "\n\n*En Kritik Hatalar:*"
            for h in summary["en_kritik_hatalar"]:
                text += f"\n• `{h['test']}` — {h['mesaj'][:80]}"

        if channel == "slack":
            payload = {"text": text}
        else:
            payload = {
                "@type": "MessageCard",
                "summary": f"TestwrightAI Test: {summary['karar']}",
                "text": text.replace("*", "**"),
            }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            return True
        except (urllib.error.URLError, OSError):
            return False

    # ── CSV Export ─────────────────────────────────────────────

    def export_to_csv(self, results: dict, path: str | Path | None = None) -> str:
        REPORTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = Path(path) if path else REPORTS_OUTPUT_DIR / f"{self.report_name}_{self.ts}.csv"

        rows = [
            ["Metrik", "Değer"],
            ["Toplam Test", results.get("total", 0)],
            ["Başarılı", results.get("passed", 0)],
            ["Başarısız", results.get("failed", 0)],
            ["Atlanan", results.get("skipped", 0)],
            ["Süre (s)", results.get("duration_seconds", 0)],
            ["Başarı Oranı (%)", round(results.get("passed", 0) / max(results.get("total", 1), 1) * 100, 2)],
            ["Tarih", datetime.now().strftime("%d.%m.%Y %H:%M:%S")],
            ["Ortam", os.getenv("TEST_ENV", "test")],
        ]

        failures = results.get("failures", [])
        if failures:
            rows.append([])
            rows.append(["Başarısız Test", "Hata Mesajı", "Hata Tipi"])
            for f in failures:
                rows.append([f.get("test", ""), f.get("message", ""), f.get("type", "")])

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerows(rows)

        return str(out_path)

    # ── Email Raporu ──────────────────────────────────────────

    def generate_email_report(self, results: dict) -> str:
        REPORTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        template_path = TEMPLATES_DIR / "email_report.html"
        out_path = REPORTS_OUTPUT_DIR / f"{self.report_name}_email_{self.ts}.html"

        summary = self.generate_summary(results)
        env = self._env_info()

        failure_list = ""
        for h in summary["en_kritik_hatalar"]:
            failure_list += f'<li><code>{h["test"]}</code> &mdash; {h["mesaj"][:100]}</li>'
        if not failure_list:
            failure_list = "<li>Hata yok — tüm testler başarılı!</li>"

        bar_green = summary["basari_orani"]
        bar_red = 100 - bar_green

        if template_path.exists():
            tpl = ReportTemplate(template_path).load()
            html = tpl.render(
                karar=summary["karar"],
                toplam=str(summary["toplam"]),
                basarili=str(summary["basarili"]),
                basarisiz=str(summary["basarisiz"]),
                atlanan=str(summary["atlanan"]),
                basari_orani=f"{summary['basari_orani']:.1f}",
                sure=f"{summary['sure_saniye']:.1f}",
                tarih=summary["tarih"],
                ortam=env["ortam"],
                hostname=env["hostname"],
                failure_list=failure_list,
                bar_green=f"{bar_green:.0f}",
                bar_red=f"{bar_red:.0f}",
                year=str(datetime.now().year),
            )
        else:
            html = f"<html><body><h1>TestwrightAI: {summary['karar']}</h1></body></html>"

        out_path.write_text(html, encoding="utf-8")
        return str(out_path)
