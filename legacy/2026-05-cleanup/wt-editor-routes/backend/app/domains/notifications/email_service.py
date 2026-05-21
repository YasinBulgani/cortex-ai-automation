"""Email notification service — SMTP ile test olayları için e-posta gönderimi.

Desteklenen olaylar:
  - test_failure   : Test koşusu başarısız oldu
  - test_complete  : Test koşusu tamamlandı
  - quality_gate   : Quality Gate başarısız oldu
  - schedule_fail  : Zamanlanmış koşu başarısız oldu
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)

# ── SMTP config (env override) ────────────────────────────────────────────────
SMTP_HOST     = os.environ.get("SMTP_HOST", "")
SMTP_PORT     = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER     = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM     = os.environ.get("SMTP_FROM", SMTP_USER)
SMTP_TLS      = os.environ.get("SMTP_TLS", "true").lower() == "true"
SMTP_ENABLED  = bool(SMTP_HOST and SMTP_USER)

# ── HTML şablonlar ─────────────────────────────────────────────────────────────

_BASE_STYLE = """
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f5f5f5; }
  .container { max-width: 600px; margin: 32px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.12); }
  .header { padding: 24px 32px; color: #fff; }
  .header h1 { margin: 0; font-size: 20px; font-weight: 600; }
  .body { padding: 24px 32px; }
  .badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
  .badge-red { background: #fee2e2; color: #dc2626; }
  .badge-green { background: #dcfce7; color: #16a34a; }
  .badge-yellow { background: #fef9c3; color: #ca8a04; }
  .metric { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; font-size: 14px; }
  .metric:last-child { border-bottom: none; }
  .metric-value { font-weight: 600; }
  .footer { padding: 16px 32px; background: #f9f9f9; font-size: 12px; color: #999; text-align: center; }
  .btn { display: inline-block; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px; margin-top: 16px; }
  .btn-primary { background: #6366f1; color: #fff; }
</style>
"""


def _render_test_result(run_name: str, project: str, passed: int, failed: int,
                         duration_s: float, run_url: str = "") -> str:
    total = passed + failed
    pct = round(passed / total * 100) if total else 0
    header_color = "#16a34a" if failed == 0 else "#dc2626"
    status_label = "BAŞARILI" if failed == 0 else "BAŞARISIZ"
    badge_cls = "badge-green" if failed == 0 else "badge-red"

    btn_html = f'<a href="{run_url}" class="btn btn-primary">Koşu Detayını Gör</a>' if run_url else ""

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">{_BASE_STYLE}</head><body>
<div class="container">
  <div class="header" style="background:{header_color}">
    <h1>Test Koşusu {status_label} <span class="badge {badge_cls}" style="background:rgba(255,255,255,.2);color:#fff">{pct}% Geçti</span></h1>
  </div>
  <div class="body">
    <div class="metric"><span>Proje</span><span class="metric-value">{project}</span></div>
    <div class="metric"><span>Koşu</span><span class="metric-value">{run_name}</span></div>
    <div class="metric"><span>Geçen</span><span class="metric-value" style="color:#16a34a">{passed}</span></div>
    <div class="metric"><span>Başarısız</span><span class="metric-value" style="color:#dc2626">{failed}</span></div>
    <div class="metric"><span>Toplam</span><span class="metric-value">{total}</span></div>
    <div class="metric"><span>Süre</span><span class="metric-value">{duration_s:.1f}s</span></div>
    <div class="metric"><span>Tarih</span><span class="metric-value">{datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC</span></div>
    {btn_html}
  </div>
  <div class="footer">TestwrightAI Test Intelligence Platform · Otomatik bildirim</div>
</div></body></html>"""


def _render_quality_gate(project: str, gate_name: str, result: str,
                          checks: list[dict], run_url: str = "") -> str:
    passed = result == "passed"
    header_color = "#16a34a" if passed else "#dc2626"
    btn_html = f'<a href="{run_url}" class="btn btn-primary">Detayları Gör</a>' if run_url else ""

    checks_html = ""
    for c in checks:
        ok = c.get("passed", False)
        icon = "✓" if ok else "✗"
        color = "#16a34a" if ok else "#dc2626"
        checks_html += f'<div class="metric"><span>{icon} {c.get("name")}</span><span class="metric-value" style="color:{color}">{c.get("value")} / {c.get("threshold")}</span></div>'

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">{_BASE_STYLE}</head><body>
<div class="container">
  <div class="header" style="background:{header_color}">
    <h1>Quality Gate {"GEÇTİ" if passed else "BAŞARISIZ"} — {gate_name}</h1>
  </div>
  <div class="body">
    <p style="color:#555;font-size:14px">Proje: <strong>{project}</strong></p>
    {checks_html}
    {btn_html}
  </div>
  <div class="footer">TestwrightAI Test Intelligence Platform · Otomatik bildirim</div>
</div></body></html>"""


# ── Core send ─────────────────────────────────────────────────────────────────

def send_email(to: str | list[str], subject: str, html_body: str) -> bool:
    """SMTP üzerinden HTML e-posta gönderir. Hata olursa False döner."""
    if not SMTP_ENABLED:
        logger.debug("SMTP yapılandırılmamış, e-posta atlandı: %s", subject)
        return False

    recipients = [to] if isinstance(to, str) else to
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_FROM
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if SMTP_TLS:
            srv = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            srv.ehlo()
            srv.starttls()
        else:
            srv = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)
        if SMTP_USER and SMTP_PASSWORD:
            srv.login(SMTP_USER, SMTP_PASSWORD)
        srv.sendmail(SMTP_FROM, recipients, msg.as_string())
        srv.quit()
        logger.info("E-posta gönderildi → %s | %s", recipients, subject)
        return True
    except Exception as exc:
        logger.error("E-posta gönderilemedi: %s", exc)
        return False


# ── High-level notification helpers ──────────────────────────────────────────

def notify_test_complete(
    to: str | list[str],
    *,
    project: str,
    run_name: str,
    passed: int,
    failed: int,
    duration_s: float,
    run_url: str = "",
) -> bool:
    status = "Başarısız" if failed else "Tamamlandı"
    subject = f"[TestwrightAI] Test Koşusu {status} — {project} / {run_name}"
    html = _render_test_result(run_name, project, passed, failed, duration_s, run_url)
    return send_email(to, subject, html)


def notify_quality_gate(
    to: str | list[str],
    *,
    project: str,
    gate_name: str,
    result: str,       # "passed" | "failed"
    checks: list[dict],
    run_url: str = "",
) -> bool:
    verdict = "GEÇTİ" if result == "passed" else "BAŞARISIZ"
    subject = f"[TestwrightAI] Quality Gate {verdict} — {project} / {gate_name}"
    html = _render_quality_gate(project, gate_name, result, checks, run_url)
    return send_email(to, subject, html)


def notify_slack(webhook_url: str, *, project: str, run_name: str, passed: int, failed: int, duration_s: float) -> bool:
    """Slack Incoming Webhook üzerinden test sonucu bildirimi gönderir."""
    import urllib.request, urllib.error
    total = passed + failed
    pct = round(passed / total * 100) if total else 0
    status_emoji = "✅" if failed == 0 else "❌"
    text = (
        f"{status_emoji} *{project}* — {run_name}\n"
        f"Geçti: {passed} | Başarısız: {failed} | Toplam: {total} | Başarı: %{pct} | Süre: {duration_s:.1f}s"
    )
    payload = json.dumps({"text": text}).encode()
    try:
        req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
        logger.info("Slack bildirimi gönderildi: %s / %s", project, run_name)
        return True
    except Exception as exc:
        logger.warning("Slack bildirimi gönderilemedi: %s", exc)
        return False
