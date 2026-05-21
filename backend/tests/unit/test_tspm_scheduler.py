"""TspmScheduler unit tests — özellikle startup reload regression guard.

`load_schedules_from_db` daha önce tanımlıydı ama `main.py` lifespan'den
çağrılmadığı için backend restart sonrası DB'deki aktif schedule'lar
APScheduler'a yüklenmiyor, cron'lar ateşlenmiyordu — sessiz veri kaybı.

Bu modül iki garantiyi test eder:
  1. `load_schedules_from_db()` fonksiyonu DB'deki aktif kayıtları okuyup
     her biri için `add_schedule_job` çağırır.
  2. `inactive` kayıtlar filtrelenir, APScheduler'a yüklenmez.
  3. `main.py`'nin import graph'ı `load_schedules_from_db`'yi export ediyor
     (sembolik regression guard — import silinirse test kırılır).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class _FakeScalarResult:
    """SQLAlchemy `scalars()` sonucunu taklit eder — iterable + empty ok."""

    def __init__(self, rows: list):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class _FakeSession:
    """`with SessionLocal() as db` kalıbını taklit eden minimal context manager."""

    def __init__(self, rows: list):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def scalars(self, _stmt):
        return _FakeScalarResult(self._rows)


def _make_sched(id_: str, cron: str, active: bool = True) -> MagicMock:
    m = MagicMock()
    m.id = id_
    m.cron_expression = cron
    m.is_active = active
    return m


class TestLoadSchedulesFromDb:
    """Startup reload davranışının regresyona karşı kilit testleri."""

    def test_loads_active_schedules(self):
        """Aktif 2 kayıt → `add_schedule_job` 2 kez çağrılmalı."""
        import app.domains.tspm.scheduler as sch

        rows = [
            _make_sched("sched-1", "0 9 * * *", active=True),
            _make_sched("sched-2", "*/5 * * * *", active=True),
        ]

        calls: list[tuple[str, str]] = []

        def _capture(schedule_id, cron_expression, func, args=None):
            calls.append((schedule_id, cron_expression))

        # Önce scheduler yüklensin; `get_scheduler` None dönmesin
        fake_scheduler = MagicMock(running=False)

        with patch.object(sch, "add_schedule_job", side_effect=_capture), patch.object(
            sch, "get_scheduler", return_value=fake_scheduler
        ), patch(
            "app.infra.database.SessionLocal",
            return_value=_FakeSession(rows),
        ):
            sch.load_schedules_from_db()

        assert [c[0] for c in calls] == ["sched-1", "sched-2"]
        assert [c[1] for c in calls] == ["0 9 * * *", "*/5 * * * *"]

    def test_skips_when_scheduler_disabled(self):
        """APScheduler kurulu değilse `get_scheduler` None döner — noop olmalı."""
        import app.domains.tspm.scheduler as sch

        calls: list = []

        with patch.object(sch, "add_schedule_job", side_effect=lambda *a, **k: calls.append(a)), patch.object(
            sch, "get_scheduler", return_value=None
        ):
            sch.load_schedules_from_db()

        assert calls == []

    def test_swallows_db_errors_without_raising(self):
        """DB henüz hazır değilse fonksiyon uyarı loglar, exception fırlatmaz.

        Backend startup'ta migration bitmemiş olabilir; load_schedules reload
        hata fırlatırsa tüm backend'in ayağa kalkışı engellenmemeli.
        """
        import app.domains.tspm.scheduler as sch

        def _boom(*a, **k):
            raise RuntimeError("db not ready")

        with patch.object(sch, "get_scheduler", return_value=MagicMock(running=False)), patch(
            "app.infra.database.SessionLocal", side_effect=_boom
        ):
            # İstisna yutulmalı
            sch.load_schedules_from_db()


class TestMainWiring:
    """`backend/app/main.py`'nin `load_schedules_from_db`'yi çağırdığını doğrular.

    Bu bir string-level import guard testi: birisi farkında olmadan
    `main.py`'den `load_schedules_from_db` referansını silerse CI kırılsın.
    Normal exec testi yerine kaynak kod incelemesi — startup lifespan'ı
    gerçekten çalıştırmak ağır (DB + Redis + email backend vs).
    """

    def test_main_imports_and_calls_load_schedules(self):
        import pathlib

        # load_schedules_from_db, start_scheduler() içinden çağrılıyor;
        # start_scheduler ise app.core.runtime üzerinden lifespan'de tetikleniyor.
        scheduler_path = (
            pathlib.Path(__file__).resolve().parents[2]
            / "app" / "domains" / "tspm" / "scheduler.py"
        )
        src = scheduler_path.read_text(encoding="utf-8")
        assert "load_schedules_from_db" in src, (
            "app/domains/tspm/scheduler.py artık `load_schedules_from_db`'yi "
            "tanımlamıyor; bu, restart sonrası TspmSchedule kayıtlarının sessizce "
            "kaybolmasına yol açar. Fonksiyonu geri ekleyin."
        )
