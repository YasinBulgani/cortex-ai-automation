"""
Playback Engine — Kaydedilmiş event'leri oynatır.

Self-healing cascade desteği:
1. Selector chain üzerinde sırasıyla aday seçicileri dener
2. Bulunamazsa heal log'a kaydeder
3. Tüm adaylar başarısız olursa aksiyon fail olur

Kullanım:
    from core.playback_engine import PlaybackEngine
    from core.recording_event import RecordingEvent

    engine = PlaybackEngine(page)
    results = engine.replay(events)
    print(engine.summary())
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Tek bir aksiyon sonucu."""
    event_id: str
    action_type: str
    selector: str
    status: str  # passed | failed | healed | skipped
    healed_from: str = ""
    healed_to: str = ""
    error: str = ""
    duration_ms: float = 0.0
    screenshot_path: str = ""

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "action_type": self.action_type,
            "selector": self.selector,
            "status": self.status,
            "healed_from": self.healed_from,
            "healed_to": self.healed_to,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class PlaybackReport:
    """Playback sonuç raporu."""
    session_id: str
    started_at: str = ""
    ended_at: str = ""
    results: list[ActionResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == "passed")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")

    @property
    def healed(self) -> int:
        return sum(1 for r in self.results if r.status == "healed")

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == "skipped")

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.passed + self.healed) / self.total * 100

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "healed": self.healed,
            "skipped": self.skipped,
            "pass_rate": round(self.pass_rate, 1),
            "results": [r.to_dict() for r in self.results],
        }


class PlaybackEngine:
    """
    RecordingEvent listesini Playwright Page üzerinde oynatır.
    Selector chain cascade ile self-healing sağlar.
    """

    def __init__(self, page: Page, timeout: int = 10_000):
        self.page = page
        self.timeout = timeout
        self._report: PlaybackReport | None = None

    def replay(self, events: list[dict], session_id: str = "") -> PlaybackReport:
        """
        Event listesini sırasıyla oynatır.

        Args:
            events: RecordingEvent.to_dict() listesi
            session_id: Oturum kimliği

        Returns:
            PlaybackReport
        """
        self._report = PlaybackReport(
            session_id=session_id,
            started_at=datetime.now().isoformat(),
        )

        for event_dict in events:
            result = self._execute_event(event_dict)
            self._report.results.append(result)

        self._report.ended_at = datetime.now().isoformat()
        return self._report

    def replay_from_file(self, path: Path | str) -> PlaybackReport:
        """JSON dosyasından event'leri okuyup oynatır."""
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))

        if isinstance(data, list):
            events = data
            session_id = ""
        elif isinstance(data, dict):
            events = data.get("actions", data.get("events", []))
            session_id = data.get("session_id", data.get("name", ""))
        else:
            raise ValueError(f"Geçersiz dosya formatı: {path}")

        return self.replay(events, session_id)

    def _execute_event(self, event: dict) -> ActionResult:
        """Tek bir event'i çalıştırır."""
        start = time.time()
        event_id = event.get("id", "")
        target = event.get("target", {})
        action = event.get("action", {})
        context = event.get("context", {})
        assertion = event.get("assertion")
        action_type = action.get("type", event.get("action_type", ""))

        if action_type == "navigate":
            return self._do_navigate(event_id, action, start)

        selector_chain = target.get("selector_chain", [])
        primary_selector = target.get("selector", "")

        resolved_selector, healed_from = self._resolve_selector(
            primary_selector, selector_chain
        )

        if not resolved_selector and action_type not in ("navigate", "wait_for", "assert_url"):
            return ActionResult(
                event_id=event_id,
                action_type=action_type,
                selector=primary_selector,
                status="failed",
                error="Element bulunamadı: tüm seçiciler başarısız",
                duration_ms=(time.time() - start) * 1000,
            )

        try:
            self._perform_action(action_type, resolved_selector, action, assertion)
            status = "healed" if healed_from else "passed"
            return ActionResult(
                event_id=event_id,
                action_type=action_type,
                selector=resolved_selector,
                status=status,
                healed_from=healed_from,
                healed_to=resolved_selector if healed_from else "",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as exc:
            return ActionResult(
                event_id=event_id,
                action_type=action_type,
                selector=resolved_selector or primary_selector,
                status="failed",
                error=str(exc)[:200],
                duration_ms=(time.time() - start) * 1000,
            )

    def _resolve_selector(self, primary: str, chain: list[dict]) -> tuple[str, str]:
        """
        Selector chain üzerinde cascade ile element arar.

        Returns:
            (resolved_selector, healed_from_selector)
            healed_from boşsa birincil seçici başarılı demektir.
        """
        if primary:
            try:
                if self.page.locator(primary).count() > 0:
                    return primary, ""
            except Exception as exc:
                logger.debug("Birincil selector gecersiz '%s': %s", primary, exc)

        for candidate in chain:
            value = candidate.get("value", "")
            if not value or value == primary:
                continue
            try:
                if self.page.locator(value).count() > 0:
                    logger.info("Self-heal: '%s' -> '%s'", primary, value)
                    return value, primary
            except Exception:
                continue

        if primary:
            return primary, ""
        return "", ""

    def _perform_action(self, action_type: str, selector: str, action: dict, assertion: dict | None):
        """Aksiyonu Playwright ile çalıştırır."""
        value = action.get("value", "")
        key = action.get("key", "")
        metadata = action.get("metadata", {})

        if action_type == "click":
            self.page.locator(selector).first.click(timeout=self.timeout)

        elif action_type == "dblclick":
            self.page.locator(selector).first.dblclick(timeout=self.timeout)

        elif action_type in ("type", "fill"):
            self.page.locator(selector).fill(value, timeout=self.timeout)

        elif action_type == "clear":
            self.page.locator(selector).clear(timeout=self.timeout)

        elif action_type == "select":
            self.page.locator(selector).select_option(value, timeout=self.timeout)

        elif action_type in ("check",):
            self.page.locator(selector).check(timeout=self.timeout)

        elif action_type == "uncheck":
            self.page.locator(selector).uncheck(timeout=self.timeout)

        elif action_type == "hover":
            self.page.locator(selector).hover(timeout=self.timeout)

        elif action_type == "press_key":
            if selector:
                self.page.locator(selector).press(key or value, timeout=self.timeout)
            else:
                self.page.keyboard.press(key or value)

        elif action_type == "scroll":
            y = metadata.get("y", 500)
            x = metadata.get("x", 0)
            if selector:
                self.page.locator(selector).scroll_into_view_if_needed(timeout=self.timeout)
            else:
                self.page.evaluate(f"window.scrollBy({x}, {y})")

        elif action_type == "wait_for":
            duration = metadata.get("duration_ms", 0)
            if selector:
                self.page.locator(selector).wait_for(state="visible", timeout=self.timeout)
            elif duration:
                self.page.wait_for_timeout(duration)

        elif action_type == "upload":
            self.page.locator(selector).set_input_files(value)

        elif action_type == "screenshot":
            name = metadata.get("name", "playback_screenshot")
            self.page.screenshot(path=f"screenshots/{name}.png")

        elif action_type == "navigate":
            pass  # handled separately

        # Assertions
        if assertion:
            self._perform_assertion(selector, assertion)
        elif action_type == "assert_text":
            expect(self.page.locator(selector)).to_have_text(value, timeout=self.timeout)
        elif action_type == "assert_visible":
            expect(self.page.locator(selector)).to_be_visible(timeout=self.timeout)
        elif action_type == "assert_url":
            expect(self.page).to_have_url(value, timeout=self.timeout)

    def _perform_assertion(self, selector: str, assertion: dict):
        """Assertion event'ini doğrular."""
        a_type = assertion.get("type", "")
        expected = assertion.get("expected", "")

        if a_type == "text":
            expect(self.page.locator(selector)).to_have_text(expected, timeout=self.timeout)
        elif a_type == "visible":
            expect(self.page.locator(selector)).to_be_visible(timeout=self.timeout)
        elif a_type == "hidden":
            expect(self.page.locator(selector)).to_be_hidden(timeout=self.timeout)
        elif a_type == "url":
            expect(self.page).to_have_url(expected, timeout=self.timeout)
        elif a_type == "value":
            expect(self.page.locator(selector)).to_have_value(expected, timeout=self.timeout)

    def _do_navigate(self, event_id: str, action: dict, start: float) -> ActionResult:
        """Navigate aksiyonunu çalıştırır."""
        url = action.get("value", "")
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 3)
            return ActionResult(
                event_id=event_id,
                action_type="navigate",
                selector=url,
                status="passed",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as exc:
            return ActionResult(
                event_id=event_id,
                action_type="navigate",
                selector=url,
                status="failed",
                error=str(exc)[:200],
                duration_ms=(time.time() - start) * 1000,
            )

    @property
    def report(self) -> PlaybackReport | None:
        return self._report

    def summary(self) -> str:
        """İnsan okunabilir sonuç özeti."""
        if not self._report:
            return "Henüz playback çalıştırılmadı."
        r = self._report
        lines = [
            f"Playback Sonucu: {r.session_id}",
            f"  Toplam: {r.total} | Başarılı: {r.passed} | Başarısız: {r.failed} | İyileşen: {r.healed} | Atlanan: {r.skipped}",
            f"  Başarı oranı: %{r.pass_rate:.1f}",
        ]
        if r.healed > 0:
            lines.append(f"  Self-healing: {r.healed} element iyileştirildi")
            for res in r.results:
                if res.status == "healed":
                    lines.append(f"    {res.healed_from} -> {res.healed_to}")
        if r.failed > 0:
            lines.append(f"  Başarısız aksiyonlar:")
            for res in r.results:
                if res.status == "failed":
                    lines.append(f"    [{res.action_type}] {res.selector}: {res.error}")
        return "\n".join(lines)

    def save_report(self, path: Path | str | None = None) -> str:
        """Raporu JSON dosyasına kaydeder."""
        if not self._report:
            raise RuntimeError("Önce replay() çalıştırın.")
        if path is None:
            from config.settings import settings
            reports_dir = settings.BASE_DIR / "reports" / "playback"
            reports_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = reports_dir / f"playback_{self._report.session_id}_{ts}.json"
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return str(path)
