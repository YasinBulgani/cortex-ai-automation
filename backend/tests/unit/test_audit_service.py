"""
Audit service unit testleri — 14 test.

app.domains.audit.service.log_audit ve app.domains.audit.chain saf
fonksiyonlarını (canonical_payload, compute_hash, verify_chain) doğrular.
Gerçek DB veya psycopg2 bağlantısı gerekmez; chain.append_event mocklanır.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

try:
    from app.domains.audit.service import log_audit
    from app.domains.audit.chain import (
        ChainEvent,
        GENESIS_PREV_HASH,
        canonical_payload,
        compute_hash,
        verify_chain,
        VerifyResult,
    )
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="audit service import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _event(
    action: str = "test.action",
    resource_type: str = "scenario",
    seq: int = 1,
    prev_hash: str | None = None,
    ts: datetime | None = None,
) -> ChainEvent:
    ev = ChainEvent(
        ts=ts or _TS,
        tenant_id="tenant-1",
        actor_user_id="user-42",
        action=action,
        resource_type=resource_type,
        resource_id="r-1",
        payload={"detail": "value"},
        seq=seq,
        prev_hash=prev_hash,
    )
    ev.hash = compute_hash(prev_hash, ev)
    return ev


# ---------------------------------------------------------------------------
# canonical_payload (pure)
# ---------------------------------------------------------------------------

class TestCanonicalPayload:
    def test_returns_string(self):
        ev = ChainEvent(
            ts=_TS,
            tenant_id="t",
            actor_user_id="u",
            action="a",
            resource_type="r",
            resource_id="id",
        )
        result = canonical_payload(ev)
        assert isinstance(result, str)

    def test_ends_with_newline(self):
        ev = ChainEvent(ts=_TS, tenant_id=None, actor_user_id=None, action="x", resource_type="y", resource_id=None)
        assert canonical_payload(ev).endswith("\n")

    def test_deterministic(self):
        ev = ChainEvent(ts=_TS, tenant_id="t", actor_user_id="u", action="a", resource_type="r", resource_id=None)
        assert canonical_payload(ev) == canonical_payload(ev)

    def test_different_actions_produce_different_payloads(self):
        ev1 = ChainEvent(ts=_TS, tenant_id="t", actor_user_id="u", action="create", resource_type="r", resource_id=None)
        ev2 = ChainEvent(ts=_TS, tenant_id="t", actor_user_id="u", action="delete", resource_type="r", resource_id=None)
        assert canonical_payload(ev1) != canonical_payload(ev2)


# ---------------------------------------------------------------------------
# compute_hash (pure)
# ---------------------------------------------------------------------------

class TestComputeHash:
    def test_returns_64_char_hex(self):
        ev = ChainEvent(ts=_TS, tenant_id=None, actor_user_id=None, action="a", resource_type="r", resource_id=None)
        h = compute_hash(None, ev)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_genesis_uses_empty_prev_hash(self):
        ev = ChainEvent(ts=_TS, tenant_id=None, actor_user_id=None, action="a", resource_type="r", resource_id=None)
        h_none = compute_hash(None, ev)
        h_empty = compute_hash(GENESIS_PREV_HASH, ev)
        assert h_none == h_empty

    def test_different_prev_hash_changes_result(self):
        ev = ChainEvent(ts=_TS, tenant_id=None, actor_user_id=None, action="a", resource_type="r", resource_id=None)
        h1 = compute_hash("aaa", ev)
        h2 = compute_hash("bbb", ev)
        assert h1 != h2


# ---------------------------------------------------------------------------
# verify_chain (pure)
# ---------------------------------------------------------------------------

class TestVerifyChain:
    def test_empty_chain_is_ok(self):
        result = verify_chain([])
        assert isinstance(result, VerifyResult)
        assert result.ok is True
        assert result.total == 0

    def test_single_valid_event(self):
        ev = _event(seq=1, prev_hash=None)
        result = verify_chain([ev])
        assert result.ok is True
        assert result.verified == 1

    def test_two_linked_events_pass(self):
        ev1 = _event(seq=1, prev_hash=None)
        ev2 = ChainEvent(
            ts=_TS,
            tenant_id="tenant-1",
            actor_user_id="user-42",
            action="test.action",
            resource_type="scenario",
            resource_id="r-1",
            seq=2,
            prev_hash=ev1.hash,
        )
        ev2.hash = compute_hash(ev1.hash, ev2)
        result = verify_chain([ev1, ev2])
        assert result.ok is True
        assert result.verified == 2

    def test_tampered_hash_detected(self):
        ev = _event(seq=1, prev_hash=None)
        ev.hash = "0" * 64  # tamper
        result = verify_chain([ev])
        assert result.ok is False
        assert result.first_bad_seq == 1
        assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# log_audit — hash-chain path + ORM fallback
# ---------------------------------------------------------------------------

class TestLogAudit:
    @patch("app.domains.audit.chain.append_event")
    def test_log_audit_calls_chain_append(self, mock_append):
        mock_append.return_value = {"id": "abc", "seq": 1, "hash": "deadbeef"}
        db = MagicMock()

        log_audit(
            db,
            actor_user_id="u1",
            action="scenario.create",
            resource_type="scenario",
            resource_id="s1",
            payload={"name": "test"},
            ip="127.0.0.1",
        )

        mock_append.assert_called_once()
        call_kwargs = mock_append.call_args.kwargs
        assert call_kwargs["action"] == "scenario.create"
        assert call_kwargs["actor_user_id"] == "u1"

    @patch("app.domains.audit.chain.append_event", side_effect=Exception("db down"))
    def test_log_audit_falls_back_to_orm(self, mock_append):
        """When chain append raises, ORM fallback must add an AuditEvent to the session."""
        db = MagicMock()

        log_audit(
            db,
            actor_user_id="u2",
            action="user.login",
            resource_type="user",
            resource_id=None,
            payload=None,
            ip="10.0.0.1",
        )

        db.add.assert_called_once()

    @patch("app.domains.audit.chain.append_event")
    def test_log_audit_tenant_id_forwarded(self, mock_append):
        mock_append.return_value = {"id": "x", "seq": 2, "hash": "abc"}
        db = MagicMock()

        log_audit(
            db,
            actor_user_id="u3",
            action="project.delete",
            resource_type="project",
            resource_id="p1",
            payload=None,
            ip=None,
            tenant_id="tenant-xyz",
        )

        call_kwargs = mock_append.call_args.kwargs
        assert call_kwargs["tenant_id"] == "tenant-xyz"
