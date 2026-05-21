"""Continuous background ops agent powered by the AI gateway.

The first phase keeps the scope intentionally narrow:
- periodic health checks for backend / engine / gateway
- a short AI-generated operational summary
- latest report persisted to disk

It does not mutate code, deploy, or trigger destructive flows.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.domains.ai.gateway_client import gateway_complete, gateway_is_available
from app.domains.tspm.scheduler import get_scheduler

logger = logging.getLogger(__name__)

OPS_AGENT_JOB_ID = "bgts-ai-ops-agent"
_run_lock = threading.Lock()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate_payload(payload: Any, limit: int = 600) -> str:
    try:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    except TypeError:
        text = str(payload)
    return text if len(text) <= limit else f"{text[:limit]}..."


def parse_targets(raw: str | None = None) -> list[dict[str, str]]:
    """Parse `name=url` pairs from env config."""
    text = raw if raw is not None else settings.ai_background_targets
    if not text:
        return []

    targets: list[dict[str, str]] = []
    normalized = text.replace("\n", ",").replace(";", ",")
    for chunk in normalized.split(","):
        item = chunk.strip()
        if not item:
            continue
        if "=" in item:
            name, url = item.split("=", 1)
        else:
            url = item
            name = item.rsplit("/", 1)[-1] or "service"
        targets.append({"name": name.strip(), "url": url.strip()})
    return targets


def _check_target(client: httpx.Client, target: dict[str, str]) -> dict[str, Any]:
    start = time.monotonic()
    url = target["url"]
    headers = {}
    if "engine" in target["name"]:
        headers["X-Internal-Key"] = settings.engine_internal_key

    try:
        response = client.get(url, headers=headers)
        latency_ms = int((time.monotonic() - start) * 1000)
        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            payload: Any = response.json()
        else:
            payload = response.text[:400]

        ok = response.status_code < 400
        summary = f"HTTP {response.status_code}"

        if isinstance(payload, dict) and payload.get("status"):
            summary = str(payload["status"])

        providers = payload.get("providers") if isinstance(payload, dict) else None
        if isinstance(providers, dict):
            active = [name for name, value in providers.items() if value]
            summary = (
                f"{payload.get('status', 'unknown')} | aktif sağlayıcılar: "
                f"{', '.join(active) if active else 'yok'}"
            )

        return {
            "name": target["name"],
            "url": url,
            "ok": ok,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "summary": summary,
            "payload": payload,
        }
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "name": target["name"],
            "url": url,
            "ok": False,
            "status_code": None,
            "latency_ms": latency_ms,
            "summary": f"bağlantı hatası: {exc}",
            "payload": None,
        }


def collect_target_health() -> list[dict[str, Any]]:
    targets = parse_targets()
    if not targets:
        return []

    with httpx.Client(timeout=settings.ai_background_request_timeout_seconds) as client:
        return [_check_target(client, target) for target in targets]


def build_fallback_summary(results: list[dict[str, Any]]) -> str:
    failed = [item["name"] for item in results if not item["ok"]]
    if not failed:
        return (
            "Tüm izlenen servisler erişilebilir görünüyor. "
            "Arka plan ajanı şu an yalnızca gözlem ve özet üretimi yapıyor."
        )
    return (
        "Sorun görülen servisler: "
        f"{', '.join(failed)}. "
        "Öncelik sağlık endpoint'lerini ve konteyner loglarını kontrol etmek olmalı."
    )


def generate_ai_summary(results: list[dict[str, Any]], trigger: str) -> str:
    if not gateway_is_available():
        return build_fallback_summary(results)

    prompt_payload = {
        "trigger": trigger,
        "generated_at": _utcnow(),
        "services": [
            {
                "name": item["name"],
                "ok": item["ok"],
                "status_code": item["status_code"],
                "latency_ms": item["latency_ms"],
                "summary": item["summary"],
                "payload": item["payload"],
            }
            for item in results
        ],
    }
    try:
        return gateway_complete(
            task_type="chat",
            system_message=(
                "Sen TestwrightAI için arka planda çalışan operasyon ajanısın. "
                "Türkçe ve kısa Markdown üret. "
                "Şu başlıkları kullan: Genel Durum, Dikkat Edilecekler, Sonraki Adım. "
                "En fazla 180 kelime yaz. Gereksiz tekrar yapma."
            ),
            user_message=(
                "Aşağıdaki servis sağlık çıktılarından operasyon özeti üret.\n\n"
                f"{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}"
            ),
            temperature=0.2,
            max_tokens=500,
            json_mode=False,
        )
    except Exception as exc:
        logger.warning("AI summary fallback'a düştü: %s", exc)
        return build_fallback_summary(results)


def render_report(
    results: list[dict[str, Any]],
    summary: str,
    trigger: str,
    started_at: str,
    completed_at: str,
) -> str:
    lines = [
        "# TestwrightAI AI Ops Report",
        "",
        f"- Tetikleyici: `{trigger}`",
        f"- Başlangıç: `{started_at}`",
        f"- Bitiş: `{completed_at}`",
        f"- İzlenen hedef sayısı: `{len(results)}`",
        "",
        "## Servisler",
    ]
    for item in results:
        status_text = "OK" if item["ok"] else "FAIL"
        lines.append(
            f"- `{item['name']}`: `{status_text}` | {item['summary']} | {item['latency_ms']}ms"
        )

    lines.extend(
        [
            "",
            "## AI Summary",
            summary.strip() or "_Özet üretilemedi._",
            "",
            "## Ham Çıktı",
        ]
    )
    for item in results:
        lines.append(f"### {item['name']}")
        lines.append("```json")
        lines.append(_truncate_payload(item["payload"]))
        lines.append("```")
    lines.append("")
    return "\n".join(lines)


class OpsAgentState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.enabled = settings.ai_background_enabled
        self.running = False
        self.interval_seconds = settings.ai_background_interval_seconds
        self.last_trigger: str | None = None
        self.last_status = "idle"
        self.last_started_at: str | None = None
        self.last_completed_at: str | None = None
        self.last_error: str | None = None
        self.last_summary: str | None = None
        self.last_report_path: str | None = None
        self.last_targets: list[dict[str, Any]] = []

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            snap = {
                "enabled": self.enabled,
                "running": self.running,
                "interval_seconds": self.interval_seconds,
                "last_trigger": self.last_trigger,
                "last_status": self.last_status,
                "last_started_at": self.last_started_at,
                "last_completed_at": self.last_completed_at,
                "last_error": self.last_error,
                "last_summary": self.last_summary,
                "last_report_path": self.last_report_path,
                "last_targets": list(self.last_targets),
            }
        scheduler = get_scheduler()
        job = scheduler.get_job(OPS_AGENT_JOB_ID) if scheduler else None
        snap["scheduled"] = job is not None
        snap["next_run_at"] = (
            job.next_run_time.isoformat() if job and job.next_run_time else None
        )
        return snap

    def mark_running(self, trigger: str) -> None:
        with self._lock:
            self.running = True
            self.last_trigger = trigger
            self.last_status = "running"
            self.last_started_at = _utcnow()
            self.last_error = None

    def mark_finished(
        self,
        *,
        status: str,
        summary: str | None,
        report_path: str | None,
        targets: list[dict[str, Any]],
        error: str | None = None,
    ) -> None:
        with self._lock:
            self.running = False
            self.last_status = status
            self.last_completed_at = _utcnow()
            self.last_error = error
            self.last_summary = summary
            self.last_report_path = report_path
            self.last_targets = targets


ops_agent = OpsAgentState()


def _write_report(content: str) -> str:
    path = Path(settings.ai_background_report_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path.resolve())


def run_maintenance_cycle(trigger: str = "scheduled") -> dict[str, Any]:
    if not _run_lock.acquire(blocking=False):
        raise RuntimeError("Ops agent zaten çalışıyor")

    ops_agent.mark_running(trigger)
    try:
        results = collect_target_health()
        summary = generate_ai_summary(results, trigger)
        report = render_report(
            results=results,
            summary=summary,
            trigger=trigger,
            started_at=ops_agent.last_started_at or _utcnow(),
            completed_at=_utcnow(),
        )
        report_path = _write_report(report)
        ops_agent.mark_finished(
            status="healthy" if all(item["ok"] for item in results) else "degraded",
            summary=summary,
            report_path=report_path,
            targets=results,
        )
        logger.info("AI ops cycle tamamlandı: %s", report_path)
        return ops_agent.snapshot()
    except Exception as exc:
        logger.exception("AI ops cycle başarısız")
        ops_agent.mark_finished(
            status="failed",
            summary=None,
            report_path=ops_agent.last_report_path,
            targets=[],
            error=str(exc),
        )
        raise
    finally:
        _run_lock.release()


def start_ops_agent_loop() -> None:
    scheduler = get_scheduler()
    if scheduler is None:
        logger.warning("Scheduler olmadığı için ops agent loop başlatılamadı")
        return

    if scheduler.get_job(OPS_AGENT_JOB_ID):
        ops_agent.enabled = True
        return

    scheduler.add_job(
        run_maintenance_cycle,
        "interval",
        id=OPS_AGENT_JOB_ID,
        seconds=max(60, settings.ai_background_interval_seconds),
        kwargs={"trigger": "scheduled"},
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc)
        + timedelta(seconds=max(5, settings.ai_background_start_delay_seconds)),
    )
    ops_agent.enabled = True
    logger.info(
        "AI ops agent planlandı: her %ss",
        max(60, settings.ai_background_interval_seconds),
    )


def stop_ops_agent_loop() -> None:
    scheduler = get_scheduler()
    if scheduler is None:
        ops_agent.enabled = False
        return

    job = scheduler.get_job(OPS_AGENT_JOB_ID)
    if job:
        scheduler.remove_job(OPS_AGENT_JOB_ID)
    ops_agent.enabled = False


def read_last_report() -> dict[str, Any]:
    path_str = ops_agent.last_report_path or settings.ai_background_report_path
    path = Path(path_str)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        return {"path": str(path), "content": None}
    return {"path": str(path.resolve()), "content": path.read_text(encoding="utf-8")}
