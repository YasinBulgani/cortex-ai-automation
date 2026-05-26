"""
prompts domain service unit testleri — 14 test.

prompts/service.py DB'ye (psycopg2) bağlanır.  Testler _get_conn()'u
mock'lar; gerçek PostgreSQL gerekmez.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime

try:
    from app.domains.prompts import service as prompts_service
    from app.domains.prompts.service import (
        list_prompts,
        get_prompt,
        upsert_prompt,
        archive_prompt,
        add_version,
        get_version,
    )
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(
    not _IMPORT_OK, reason="prompts service import failed"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 1, 1, 12, 0, 0)


def _prompt_row(pid="p1"):
    """(id, description, task_type, archived, created_at, created_by, updated_at, latest_version)"""
    return (pid, "desc", "generation", False, _NOW, "tester", _NOW, 1)


def _version_row(pid="p1", ver=1):
    """(id, prompt_id, version, system_prompt, user_template, model_hint,
       temperature, max_tokens, notes, created_at, created_by)"""
    return (10, pid, ver, "sys", "user tmpl", "gpt-4o", 0.7, 1000, "note", _NOW, "tester")


def _mock_conn(fetchall=None, fetchone=None, rowcount=1):
    """Cursor + connection mock oluştur."""
    cur = MagicMock()
    cur.fetchall.return_value = fetchall or []
    cur.fetchone.return_value = fetchone
    cur.rowcount = rowcount
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.cursor.return_value = cur
    conn.close = MagicMock()
    return conn, cur


# ---------------------------------------------------------------------------
# list_prompts
# ---------------------------------------------------------------------------

class TestListPrompts:
    def test_returns_list(self):
        conn, cur = _mock_conn(fetchall=[_prompt_row()])
        with patch.object(prompts_service, "_get_conn", return_value=conn):
            result = list_prompts()
        assert isinstance(result, list)

    def test_db_unavailable_returns_empty_list(self):
        with patch.object(prompts_service, "_get_conn", side_effect=Exception("no db")):
            result = list_prompts()
        assert result == []

    def test_include_archived_false_by_default(self):
        conn, cur = _mock_conn(fetchall=[])
        with patch.object(prompts_service, "_get_conn", return_value=conn):
            list_prompts()
        # execute çağrıldı; False parametresi geçildi
        args = cur.execute.call_args[0]
        assert False in args[1]

    def test_returns_one_item_per_row(self):
        rows = [_prompt_row("p1"), _prompt_row("p2")]
        conn, cur = _mock_conn(fetchall=rows)
        with patch.object(prompts_service, "_get_conn", return_value=conn):
            result = list_prompts()
        assert len(result) == 2


# ---------------------------------------------------------------------------
# get_prompt
# ---------------------------------------------------------------------------

class TestGetPrompt:
    def test_found_returns_prompt_out(self):
        conn, _ = _mock_conn(fetchone=_prompt_row("p1"))
        with patch.object(prompts_service, "_get_conn", return_value=conn):
            result = get_prompt("p1")
        assert result is not None
        assert result.id == "p1"

    def test_not_found_returns_none(self):
        conn, _ = _mock_conn(fetchone=None)
        with patch.object(prompts_service, "_get_conn", return_value=conn):
            result = get_prompt("nonexistent")
        assert result is None

    def test_conn_closed_after_query(self):
        conn, _ = _mock_conn(fetchone=_prompt_row())
        with patch.object(prompts_service, "_get_conn", return_value=conn):
            get_prompt("p1")
        conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# upsert_prompt
# ---------------------------------------------------------------------------

class TestUpsertPrompt:
    def _make_payload(self, description="d", task_type="generation"):
        p = MagicMock()
        p.description = description
        p.task_type = task_type
        return p

    def test_empty_prompt_id_raises_value_error(self):
        with pytest.raises(ValueError, match="boş olamaz"):
            upsert_prompt("", self._make_payload())

    def test_whitespace_prompt_id_raises_value_error(self):
        with pytest.raises(ValueError):
            upsert_prompt("   ", self._make_payload())

    def test_successful_upsert_returns_prompt_out(self):
        row = (
            "p1", "desc", "generation", False, _NOW, "tester", _NOW
        )
        conn, _ = _mock_conn(fetchone=row)
        with patch.object(prompts_service, "_get_conn", return_value=conn):
            result = upsert_prompt("p1", self._make_payload(), actor="tester")
        assert result.id == "p1"

    def test_no_row_returned_raises_runtime_error(self):
        conn, _ = _mock_conn(fetchone=None)
        with patch.object(prompts_service, "_get_conn", return_value=conn):
            with pytest.raises(RuntimeError, match="satır dönmedi"):
                upsert_prompt("p1", self._make_payload())


# ---------------------------------------------------------------------------
# archive_prompt
# ---------------------------------------------------------------------------

class TestArchivePrompt:
    def test_returns_true_when_row_updated(self):
        conn, _ = _mock_conn(rowcount=1)
        with patch.object(prompts_service, "_get_conn", return_value=conn):
            result = archive_prompt("p1", archived=True)
        assert result is True

    def test_returns_false_when_no_row_updated(self):
        conn, _ = _mock_conn(rowcount=0)
        with patch.object(prompts_service, "_get_conn", return_value=conn):
            result = archive_prompt("nonexistent", archived=True)
        assert result is False


# ---------------------------------------------------------------------------
# add_version / get_version
# ---------------------------------------------------------------------------

class TestAddVersion:
    def test_returns_version_out(self):
        row = _version_row("p1", 1)
        # fetchone first call = max version (0), second = inserted row
        conn = MagicMock()
        cur = MagicMock()
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        cur.fetchone.side_effect = [(0,), row]
        conn.cursor.return_value = cur
        conn.close = MagicMock()

        payload = MagicMock()
        payload.system_prompt = "sys"
        payload.user_template = "tmpl"
        payload.model_hint = "gpt-4o"
        payload.temperature = 0.7
        payload.max_tokens = 1000
        payload.notes = "note"

        with patch.object(prompts_service, "_get_conn", return_value=conn):
            result = add_version("p1", payload, actor="tester")
        assert result is not None


class TestGetVersion:
    def test_not_found_returns_none(self):
        conn, _ = _mock_conn(fetchone=None)
        with patch.object(prompts_service, "_get_conn", return_value=conn):
            result = get_version("p1", 99)
        assert result is None
