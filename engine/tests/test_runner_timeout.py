"""Runner subprocess timeout watchdog testleri.

Amaç: `_spawn_timeout_watchdog` zamanında devreye girerek asılmış süreci
öldürdüğünü ve normal tamamlanmada engel olmadığını doğrular.
"""

from __future__ import annotations

import subprocess
import sys
import time

import pytest

from routes.runner_routes import _spawn_timeout_watchdog


def test_watchdog_kills_long_process() -> None:
    """Zaman aşımında süreç öldürülmeli ve on_timeout çağrılmalı."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.PIPE,
    )
    called = {"count": 0}

    def _on_timeout() -> None:
        called["count"] += 1

    _spawn_timeout_watchdog(proc, timeout_s=1, on_timeout=_on_timeout)
    rc = proc.wait(timeout=5)

    assert rc != 0, f"Killed process'un return code'u 0 olamaz: {rc}"
    # watchdog thread'in on_timeout'u çağırması için kısa bekleme
    time.sleep(0.2)
    assert called["count"] == 1, "on_timeout tam bir kere çağrılmalıydı"


def test_watchdog_does_not_kill_short_process() -> None:
    """Süreç erken biterse watchdog kill etmemeli, on_timeout çağrılmamalı."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "pass"],
        stdout=subprocess.PIPE,
    )
    called = {"count": 0}

    def _on_timeout() -> None:
        called["count"] += 1

    stop = _spawn_timeout_watchdog(proc, timeout_s=10, on_timeout=_on_timeout)
    rc = proc.wait(timeout=5)
    stop.set()  # erken tamamlanma bildirimi

    assert rc == 0
    time.sleep(0.3)
    assert called["count"] == 0, (
        "Süreç normal bittiğinde on_timeout çağrılmamalı"
    )


def test_watchdog_stop_event_cancels_watchdog() -> None:
    """`stop_event.set()` çağrıldığında watchdog tetiklenmemeli."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        stdout=subprocess.PIPE,
    )
    called = {"count": 0}

    stop = _spawn_timeout_watchdog(
        proc, timeout_s=2, on_timeout=lambda: called.__setitem__("count", called["count"] + 1),
    )
    time.sleep(0.2)
    stop.set()  # iptal
    rc = proc.wait(timeout=10)

    # Süreç normal bitmiş olmalı (kill yok)
    assert rc == 0
    assert called["count"] == 0
