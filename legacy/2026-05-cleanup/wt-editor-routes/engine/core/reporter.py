"""
Reporter - HTML ve terminal test raporu üretimi
"""
import json
from datetime import datetime
from pathlib import Path

from config.settings import settings


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Test Raporu — {title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }}
  header {{ background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border-bottom: 1px solid #334155; padding: 24px 32px; }}
  header h1 {{ font-size: 1.5rem; color: #f8fafc; }}
  header p  {{ color: #94a3b8; font-size: 0.875rem; margin-top: 4px; }}
  .stats {{ display: flex; gap: 16px; padding: 24px 32px; }}
  .stat {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px;
           padding: 16px 24px; flex: 1; text-align: center; }}
  .stat .num {{ font-size: 2rem; font-weight: 700; }}
  .stat .label {{ color: #94a3b8; font-size: 0.75rem; margin-top: 4px; }}
  .passed  .num {{ color: #22c55e; }}
  .failed  .num {{ color: #ef4444; }}
  .total   .num {{ color: #60a5fa; }}
  .pct     .num {{ color: #a78bfa; }}
  .results {{ padding: 0 32px 32px; display: flex; flex-direction: column; gap: 16px; }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; overflow: hidden; }}
  .card-header {{ padding: 14px 20px; display: flex; align-items: center; gap: 12px;
                  border-bottom: 1px solid #334155; }}
  .badge {{ padding: 3px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 600; }}
  .badge.passed {{ background: #14532d; color: #86efac; }}
  .badge.failed {{ background: #450a0a; color: #fca5a5; }}
  .card-header h3 {{ font-size: 0.95rem; color: #f1f5f9; }}
  .steps {{ padding: 12px 20px; display: flex; flex-direction: column; gap: 6px; }}
  .step {{ display: flex; gap: 10px; font-size: 0.82rem; padding: 6px 10px;
           border-radius: 6px; align-items: flex-start; }}
  .step.pass {{ background: #052e16; color: #86efac; }}
  .step.fail {{ background: #3b0a0a; color: #fca5a5; }}
  .step-icon {{ min-width: 18px; }}
  .meta {{ padding: 10px 20px 14px; color: #64748b; font-size: 0.78rem; }}
  footer {{ text-align: center; padding: 24px; color: #475569; font-size: 0.8rem; }}
</style>
</head>
<body>
<header>
  <h1>🤖 AI Web Otomasyon Test Raporu</h1>
  <p>{title} &nbsp;|&nbsp; {date}</p>
</header>
<div class="stats">
  <div class="stat total"><div class="num">{total}</div><div class="label">TOPLAM</div></div>
  <div class="stat passed"><div class="num">{passed}</div><div class="label">BAŞARILI</div></div>
  <div class="stat failed"><div class="num">{failed}</div><div class="label">BAŞARISIZ</div></div>
  <div class="stat pct"><div class="num">{pct}%</div><div class="label">BAŞARI ORANI</div></div>
</div>
<div class="results">
{cards}
</div>
<footer>AI Web Otomasyon Test Altyapısı &copy; {year}</footer>
</body>
</html>
"""

CARD_TEMPLATE = """  <div class="card">
    <div class="card-header">
      <span class="badge {status_cls}">{status_label}</span>
      <h3>{test_name}</h3>
    </div>
    <div class="steps">{steps_html}</div>
    <div class="meta">⏱ Süre: {duration} &nbsp;|&nbsp; 🌐 {url}</div>
  </div>"""

STEP_TEMPLATE = '      <div class="step {cls}"><span class="step-icon">{icon}</span><span>{text}</span></div>'


class Reporter:
    """Test sonuçlarını HTML ve JSON olarak raporlar."""

    def __init__(self, report_name: str = None):
        self.report_name = report_name or "test_report"
        self.results: list[dict] = []
        self.start_time = datetime.now()

    def add_result(
        self,
        test_name: str,
        url: str,
        action_results: list[dict],
        duration_ms: int = 0,
    ):
        """Bir test sonucu ekler."""
        passed = all(r.get("status") == "passed" for r in action_results)
        self.results.append({
            "test_name": test_name,
            "url": url,
            "action_results": action_results,
            "duration_ms": duration_ms,
            "passed": passed,
            "timestamp": datetime.now().isoformat(),
        })

    def save(self) -> str:
        """HTML raporu kaydeder ve dosya yolunu döndürür."""
        settings.REPORTS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = settings.REPORTS_DIR / f"{self.report_name}_{ts}.html"
        json_path = settings.REPORTS_DIR / f"{self.report_name}_{ts}.json"

        # JSON kaydet
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        # HTML üret
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        pct = round(passed / total * 100) if total else 0

        cards = "\n".join(self._build_card(r) for r in self.results)

        html = HTML_TEMPLATE.format(
            title=self.report_name.replace("_", " ").title(),
            date=datetime.now().strftime("%d.%m.%Y %H:%M"),
            total=total, passed=passed, failed=failed, pct=pct,
            cards=cards,
            year=datetime.now().year,
        )
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        return str(html_path)

    def _build_card(self, result: dict) -> str:
        steps_html = ""
        for ar in result["action_results"]:
            if ar["status"] == "passed":
                cls, icon = "pass", "✓"
                text = f"{ar['action'].get('action', '')} — {ar.get('detail', '')}"
            else:
                cls, icon = "fail", "✗"
                text = f"{ar['action'].get('action', '')} — {ar.get('error', '')}"
            steps_html += "\n" + STEP_TEMPLATE.format(cls=cls, icon=icon, text=text)

        status_cls   = "passed" if result["passed"] else "failed"
        status_label = "BAŞARILI" if result["passed"] else "BAŞARISIZ"
        duration = f"{result['duration_ms']}ms"

        return CARD_TEMPLATE.format(
            status_cls=status_cls,
            status_label=status_label,
            test_name=result["test_name"],
            steps_html=steps_html,
            duration=duration,
            url=result["url"],
        )
