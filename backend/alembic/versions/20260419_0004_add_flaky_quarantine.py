"""Flaky karantina — test_run_events + test_stability_scores

Revision ID: flaky_quarantine_0001
Revises: prompts_registry_0001

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §4 / E2.2.

test_run_events:
    Her test koşumunun atomik kaydı. Rolling window hesabı için ts + status
    yeterli. Aynı test farklı suite/env'de de çalışabilir; (project, test_key,
    env) composite lookup için index.

test_stability_scores:
    Son N koşumun derleme sonucu. Günlük batch job bu tabloyu doldurur ve
    UI okur — her dashboard isteğinde on-the-fly hesaplama yapmamak için.
"""
from alembic import op


revision = "flaky_quarantine_0001"
down_revision = "prompts_registry_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS test_run_events (
            id              BIGSERIAL PRIMARY KEY,
            project_id      VARCHAR(64),
            test_key        VARCHAR(256) NOT NULL,
            test_name       VARCHAR(512),
            env             VARCHAR(32) NOT NULL DEFAULT 'ci',
            status          VARCHAR(16) NOT NULL,
            duration_ms     INTEGER,
            error_message   TEXT,
            run_id          VARCHAR(64),
            branch          VARCHAR(128),
            commit_sha      VARCHAR(64),
            ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
            CHECK (status IN ('passed','failed','skipped','error','flaky'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tre_project_test_ts
        ON test_run_events(project_id, test_key, ts DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tre_ts
        ON test_run_events(ts DESC)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS test_stability_scores (
            project_id           VARCHAR(64) NOT NULL,
            test_key             VARCHAR(256) NOT NULL,
            env                  VARCHAR(32) NOT NULL DEFAULT 'ci',
            window_size          INTEGER NOT NULL DEFAULT 20,
            runs_count           INTEGER NOT NULL DEFAULT 0,
            passed_count         INTEGER NOT NULL DEFAULT 0,
            failed_count         INTEGER NOT NULL DEFAULT 0,
            flip_count           INTEGER NOT NULL DEFAULT 0,
            pass_rate            DOUBLE PRECISION NOT NULL DEFAULT 0,
            flakiness_score      DOUBLE PRECISION NOT NULL DEFAULT 0,
            is_quarantined       BOOLEAN NOT NULL DEFAULT FALSE,
            quarantined_at       TIMESTAMPTZ,
            quarantined_until    TIMESTAMPTZ,
            last_ticket_key      VARCHAR(64),
            last_run_ts          TIMESTAMPTZ,
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (project_id, test_key, env),
            CHECK (pass_rate BETWEEN 0 AND 1),
            CHECK (flakiness_score BETWEEN 0 AND 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tss_quarantined
        ON test_stability_scores(is_quarantined, flakiness_score DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_tss_quarantined")
    op.execute("DROP TABLE IF EXISTS test_stability_scores")
    op.execute("DROP INDEX IF EXISTS idx_tre_ts")
    op.execute("DROP INDEX IF EXISTS idx_tre_project_test_ts")
    op.execute("DROP TABLE IF EXISTS test_run_events")
