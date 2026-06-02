"""Conftest for M-50 Threaded Comments + M-45 Notification Inbox tests.

These tests exercise the ``comments_service`` directly against the real
Postgres dev database. We:

* create the small set of tables touched by the service (``mgmt_comments``,
  ``mgmt_notifications``, ``test_management_audit_events``) using
  ``checkfirst=True`` so reruns are idempotent and don't disturb other tables;
* seed a few transient ``sd_users`` rows for FK targets and clean them up.

If Postgres is not reachable the fixtures call ``pytest.skip(...)`` so the
suite stays portable.
"""
from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from typing import Any

import pytest

# Ensure config imports succeed before any model imports.
os.environ.setdefault("JWT_SECRET", "test-secret-please-change")


@pytest.fixture(scope="session")
def _engine_or_skip():
    try:
        from sqlalchemy import text

        from app.infra.database import engine
    except Exception as exc:  # pragma: no cover - import paths
        pytest.skip(f"Cannot import app.infra.database: {exc}")

    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Postgres dev DB unreachable: {exc}")
    return engine


@pytest.fixture(scope="session")
def _tables_ready(_engine_or_skip) -> Any:
    """Create only the tables we need (idempotent)."""
    from sqlalchemy import text

    from app.domains.test_management.models import (
        MgmtCaseDataRow,
        MgmtCaseParamSet,
        MgmtComment,
        MgmtDesignInputField,
        MgmtDesignPartition,
        MgmtDesignTechniqueRun,
        MgmtNotification,
        TestCase,
        TestManagementAuditEvent,
    )

    engine = _engine_or_skip

    # Pre-check sd_users table exists; without it FKs cannot be created.
    with engine.connect() as c:
        sd_users_exists = c.execute(text("SELECT to_regclass('sd_users')")).scalar()
    if not sd_users_exists:
        pytest.skip("sd_users table missing — cannot create dependent test tables.")

    # The mgmt_comments table FK-references test_management_projects which may
    # not exist in this dev DB. Create that minimal parent table if missing.
    with engine.begin() as c:
        c.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS test_management_projects (
                    id UUID PRIMARY KEY,
                    name VARCHAR(200) NOT NULL DEFAULT 'test',
                    tenant_id VARCHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
                )
                """
            )
        )

    # Create our 3 tables (checkfirst=True is default).
    for model in (TestManagementAuditEvent, MgmtComment, MgmtNotification):
        model.__table__.create(bind=engine, checkfirst=True)

    # Design-technique tables (M-1/M-2/M-9). The mgmt_case_param_sets table
    # FK-references test_management_cases — create that minimal parent table
    # if missing so the schema can be applied in lean dev DBs.
    with engine.begin() as c:
        c.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS test_management_cases (
                    id UUID PRIMARY KEY,
                    project_id UUID NOT NULL,
                    case_key VARCHAR(64) NOT NULL DEFAULT 'TC-test',
                    title VARCHAR(500) NOT NULL DEFAULT 'test case',
                    suite_id UUID,
                    folder_id UUID,
                    objective TEXT,
                    preconditions TEXT,
                    test_data JSONB NOT NULL DEFAULT '{}'::jsonb,
                    priority VARCHAR(32) NOT NULL DEFAULT 'medium',
                    severity VARCHAR(32) NOT NULL DEFAULT 'major',
                    type VARCHAR(64) NOT NULL DEFAULT 'functional',
                    automation_status VARCHAR(32) NOT NULL DEFAULT 'manual',
                    status VARCHAR(32) NOT NULL DEFAULT 'draft',
                    source_type VARCHAR(32) NOT NULL DEFAULT 'manual',
                    source_ref VARCHAR(200),
                    owner_id UUID,
                    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                    custom_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
                    current_version INTEGER NOT NULL DEFAULT 1,
                    last_run_status VARCHAR(32),
                    last_run_at TIMESTAMPTZ,
                    last_failed_at TIMESTAMPTZ,
                    last_run_id UUID,
                    archived BOOLEAN NOT NULL DEFAULT false,
                    created_by UUID,
                    updated_by UUID,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        c.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS test_management_requirements (
                    id UUID PRIMARY KEY,
                    project_id UUID,
                    title VARCHAR(500) NOT NULL DEFAULT 'req',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )

    for model in (
        MgmtDesignTechniqueRun,
        MgmtDesignInputField,
        MgmtDesignPartition,
        MgmtCaseParamSet,
        MgmtCaseDataRow,
    ):
        model.__table__.create(bind=engine, checkfirst=True)

    return engine


@pytest.fixture()
def db_session(_tables_ready) -> Generator[Any, None, None]:
    """Yield a real SQLAlchemy session and clean up any rows we created."""
    from app.infra.database import SessionLocal

    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture()
def seeded_users(_tables_ready) -> Generator[dict[str, str], None, None]:
    """Create three transient sd_users rows; yield their UUIDs by alias.

    Returns a dict mapping alias → uuid string:
      ``{"alice": ..., "bob": ..., "carol": ..., "admin": ...}``
    Two distinct tenants are used to exercise tenant isolation.
    """
    from sqlalchemy import bindparam, text

    from app.infra.database import SessionLocal

    s = SessionLocal()
    tenant_a = "00000000-0000-0000-0000-000000000001"
    tenant_b = "00000000-0000-0000-0000-0000000000b2"
    users = {
        "alice": (str(uuid.uuid4()), tenant_a),
        "bob": (str(uuid.uuid4()), tenant_a),
        "carol": (str(uuid.uuid4()), tenant_a),
        "admin": (str(uuid.uuid4()), tenant_a),
        "eve": (str(uuid.uuid4()), tenant_b),
    }
    ids = [uid for uid, _ in users.values()]
    try:
        for alias, (uid, tenant) in users.items():
            s.execute(
                text(
                    """
                    INSERT INTO sd_users (id, email, password_hash, is_active, tenant_id, created_at)
                    VALUES (:id, :email, :pw, true, :tenant, now())
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"id": uid, "email": f"{alias}-{uid[:8]}@test.local", "pw": "x", "tenant": tenant},
            )
        s.commit()
        payload = {alias: uid for alias, (uid, _) in users.items()}
        payload["_tenants"] = {alias: t for alias, (_, t) in users.items()}  # type: ignore[assignment]
        yield payload
    finally:
        s.rollback()
        # Clean up design-run rows authored by these users first (FK targets).
        try:
            stmt = text(
                "DELETE FROM mgmt_design_technique_runs WHERE created_by IN :ids"
            ).bindparams(bindparam("ids", expanding=True))
            s.execute(stmt, {"ids": ids})
            s.commit()
        except Exception:
            s.rollback()
        try:
            stmt = text(
                "DELETE FROM mgmt_case_param_sets WHERE created_by IN :ids"
            ).bindparams(bindparam("ids", expanding=True))
            s.execute(stmt, {"ids": ids})
            s.commit()
        except Exception:
            s.rollback()
        for tbl, col in (
            ("mgmt_notifications", "user_id"),
            ("mgmt_comments", "author_id"),
            ("test_management_audit_events", "actor_id"),
        ):
            try:
                stmt = text(f"DELETE FROM {tbl} WHERE {col} IN :ids").bindparams(
                    bindparam("ids", expanding=True)
                )
                s.execute(stmt, {"ids": ids})
                s.commit()
            except Exception:
                s.rollback()
        try:
            stmt = text("DELETE FROM sd_users WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            s.execute(stmt, {"ids": ids})
            s.commit()
        except Exception:
            s.rollback()
        s.close()


class _StubUser:
    def __init__(self, user_id: str, tenant_id: str = "00000000-0000-0000-0000-000000000001"):
        self.id = user_id
        self.tenant_id = tenant_id


@pytest.fixture()
def make_user():
    """Factory: build a User-like object accepted by comments_service."""
    return _StubUser


@pytest.fixture()
def design_project(_tables_ready) -> Generator[str, None, None]:
    """Create a transient test_management_projects row; yield its id."""
    from sqlalchemy import text as _text

    from app.infra.database import SessionLocal

    s = SessionLocal()
    pid = str(uuid.uuid4())
    tenant = "00000000-0000-0000-0000-000000000001"
    try:
        s.execute(
            _text(
                """
                INSERT INTO test_management_projects (id, name, tenant_id, created_at)
                VALUES (:id, :name, :tenant, now())
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": pid, "name": f"design-{pid[:8]}", "tenant": tenant},
        )
        s.commit()
        yield pid
    finally:
        s.rollback()
        try:
            # delete dependent rows first
            for tbl, col in (
                ("mgmt_case_data_rows", None),
                ("mgmt_case_param_sets", "case_id"),
                ("test_management_cases", "project_id"),
                ("mgmt_design_partitions", None),
                ("mgmt_design_input_fields", None),
                ("mgmt_design_technique_runs", "project_id"),
                ("test_management_projects", "id"),
            ):
                try:
                    if tbl == "mgmt_case_data_rows":
                        s.execute(
                            _text(
                                "DELETE FROM mgmt_case_data_rows WHERE param_set_id IN "
                                "(SELECT id FROM mgmt_case_param_sets WHERE case_id IN "
                                "(SELECT id FROM test_management_cases WHERE project_id = :pid))"
                            ),
                            {"pid": pid},
                        )
                    elif tbl == "mgmt_case_param_sets":
                        s.execute(
                            _text(
                                "DELETE FROM mgmt_case_param_sets WHERE case_id IN "
                                "(SELECT id FROM test_management_cases WHERE project_id = :pid)"
                            ),
                            {"pid": pid},
                        )
                    elif tbl == "mgmt_design_partitions":
                        s.execute(
                            _text(
                                "DELETE FROM mgmt_design_partitions WHERE run_id IN "
                                "(SELECT id FROM mgmt_design_technique_runs WHERE project_id = :pid)"
                            ),
                            {"pid": pid},
                        )
                    elif tbl == "mgmt_design_input_fields":
                        s.execute(
                            _text(
                                "DELETE FROM mgmt_design_input_fields WHERE run_id IN "
                                "(SELECT id FROM mgmt_design_technique_runs WHERE project_id = :pid)"
                            ),
                            {"pid": pid},
                        )
                    else:
                        s.execute(
                            _text(f"DELETE FROM {tbl} WHERE {col} = :pid"),
                            {"pid": pid},
                        )
                    s.commit()
                except Exception:
                    s.rollback()
        finally:
            s.close()


@pytest.fixture()
def design_case(design_project) -> Generator[str, None, None]:
    """Create a transient TestCase row in the project; yield its id."""
    from sqlalchemy import text as _text

    from app.infra.database import SessionLocal

    s = SessionLocal()
    cid = str(uuid.uuid4())
    try:
        s.execute(
            _text(
                """
                INSERT INTO test_management_cases (id, project_id, case_key, title)
                VALUES (:id, :pid, :ck, :t)
                """
            ),
            {"id": cid, "pid": design_project, "ck": f"TC-{cid[:6]}", "t": "Design test case"},
        )
        s.commit()
        yield cid
    finally:
        s.rollback()
        s.close()
