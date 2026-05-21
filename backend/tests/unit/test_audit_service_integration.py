"""audit/service.py ↔ chain.py bağı — Dalga 0 E3 (BDDK tamper-evident).

Bu testler gerçek DB gerektirmez; ``append_event``'i mock'layıp ``log_audit``
çağrıldığında:
  (a) hash-chain path'i denendi mi
  (b) başarısızlıkta ORM fallback'e düşüldü mü
  (c) hiç veri kaybı yok mu
kontrol eder.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.domains.audit.service import log_audit


class TestHashChainPath:
    @patch("app.domains.audit.chain.append_event")
    def test_log_audit_calls_append_event(self, mock_append):
        mock_append.return_value = {"id": "abc", "seq": 1, "hash": "deadbeef"}
        db = MagicMock()

        log_audit(
            db,
            actor_user_id="u1",
            action="scenario.create",
            resource_type="scenario",
            resource_id="s1",
            payload={"name": "foo"},
            ip="1.2.3.4",
            tenant_id="tenant-a",
        )

        mock_append.assert_called_once()
        call_kwargs = mock_append.call_args.kwargs
        assert call_kwargs["actor_user_id"] == "u1"
        assert call_kwargs["action"] == "scenario.create"
        assert call_kwargs["resource_type"] == "scenario"
        assert call_kwargs["resource_id"] == "s1"
        assert call_kwargs["payload"] == {"name": "foo"}
        assert call_kwargs["tenant_id"] == "tenant-a"

        # ORM fallback çağrılmadı
        db.add.assert_not_called()

    @patch("app.domains.audit.chain.append_event")
    def test_log_audit_without_tenant_id(self, mock_append):
        mock_append.return_value = {"id": "abc", "seq": 1, "hash": "x"}
        log_audit(
            MagicMock(),
            actor_user_id="u1",
            action="auth.login",
            resource_type="user",
            resource_id="u1",
            payload=None,
            ip=None,
        )
        assert mock_append.call_args.kwargs["tenant_id"] is None


class TestFallbackPath:
    @patch("app.domains.audit.chain.append_event")
    def test_fallback_to_orm_on_chain_failure(self, mock_append):
        """DB'ye ulaşılamadığında audit kaybolmaz — ORM'e düşer."""
        mock_append.side_effect = RuntimeError("psycopg2 connection refused")
        db = MagicMock()

        log_audit(
            db,
            actor_user_id="u1",
            action="scenario.create",
            resource_type="scenario",
            resource_id="s1",
            payload={"name": "foo"},
            ip="1.2.3.4",
        )

        # ORM fallback mutlaka çağrılmış olmalı
        db.add.assert_called_once()
        added = db.add.call_args.args[0]
        assert added.action == "scenario.create"
        assert added.actor_user_id == "u1"

    @patch("app.domains.audit.chain.append_event")
    def test_fallback_on_constraint_violation(self, mock_append):
        from psycopg2 import IntegrityError

        mock_append.side_effect = IntegrityError("unique violation")
        db = MagicMock()
        log_audit(
            db,
            actor_user_id="u1",
            action="x.y",
            resource_type="x",
            resource_id="1",
            payload=None,
            ip=None,
        )
        db.add.assert_called_once()


class TestNoSilentDataLoss:
    """Kritik: audit event kaybolamaz. Ne hash-chain ne ORM başarılı olursa
    exception yukarı propagate edilmeli — çağıran code-path kararı versin."""

    @patch("app.domains.audit.chain.append_event")
    def test_both_paths_failing_raises(self, mock_append):
        mock_append.side_effect = RuntimeError("DB down")
        db = MagicMock()
        db.add.side_effect = RuntimeError("ORM session corrupted")

        with pytest.raises(RuntimeError):
            log_audit(
                db,
                actor_user_id="u1",
                action="critical.action",
                resource_type="x",
                resource_id="1",
                payload=None,
                ip=None,
            )
