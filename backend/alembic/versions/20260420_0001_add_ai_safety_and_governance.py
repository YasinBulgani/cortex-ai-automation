"""AI safety + governance — output violations, review queue, learned routing

Revision ID: ai_safety_0001
Revises: llm_correlation_0001

Plan: AI Stack "derin" geliştirme turu.

Eklenen tablolar:
    - ``output_violations``           — output_shield tarafindan yakalanan ihlaller
    - ``llm_review_queue``            — human-in-the-loop onay kuyrugu
    - ``learned_routing_preferences`` — router_learning çıktısı (shadow/active)
"""

from alembic import op


revision = "ai_safety_0001"
down_revision = "llm_correlation_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── output_violations ───────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS output_violations (
            id                  BIGSERIAL PRIMARY KEY,
            task_type           VARCHAR(64)   NOT NULL,
            decision            VARCHAR(16)   NOT NULL,   -- allow | warn | block
            hits                JSONB         NOT NULL DEFAULT '[]'::jsonb,
            correlation_id      VARCHAR(64),
            tenant_id           VARCHAR(64),
            created_at          TIMESTAMPTZ   NOT NULL DEFAULT now(),
            CHECK (decision IN ('allow','warn','block'))
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_output_violations_task ON output_violations(task_type, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_output_violations_decision ON output_violations(decision, created_at DESC)"
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_output_violations_correlation
        ON output_violations(correlation_id)
        WHERE correlation_id IS NOT NULL
        """
    )

    # ── llm_review_queue ────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_review_queue (
            id                  VARCHAR(36)   PRIMARY KEY,
            task_type           VARCHAR(64)   NOT NULL,
            user_prompt         TEXT          NOT NULL,
            response            TEXT          NOT NULL,
            reason              VARCHAR(128)  NOT NULL,
            confidence          NUMERIC(4,3),
            judge_overall       NUMERIC(4,2),
            status              VARCHAR(16)   NOT NULL DEFAULT 'pending',
            project_id          VARCHAR(36),
            correlation_id      VARCHAR(64),
            tenant_id           VARCHAR(64),
            reviewer            VARCHAR(128),
            reviewed_at         TIMESTAMPTZ,
            review_comment      TEXT,
            edited_response     TEXT,
            created_at          TIMESTAMPTZ   NOT NULL DEFAULT now(),
            CHECK (status IN ('pending','approved','rejected','edited'))
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_review_queue_status ON llm_review_queue(status, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_review_queue_task ON llm_review_queue(task_type, status)"
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_review_queue_project
        ON llm_review_queue(project_id)
        WHERE project_id IS NOT NULL
        """
    )

    # ── learned_routing_preferences ─────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS learned_routing_preferences (
            task_type           VARCHAR(64)   PRIMARY KEY,
            preferred_model     VARCHAR(128)  NOT NULL,
            preferred_score     NUMERIC(6,4),
            default_model       VARCHAR(128),
            default_score       NUMERIC(6,4),
            suggestion          VARCHAR(32)   NOT NULL,   -- switch|keep|insufficient_data|no_baseline
            sample_size         INTEGER       NOT NULL DEFAULT 0,
            updated_at          TIMESTAMPTZ   NOT NULL DEFAULT now(),
            CHECK (suggestion IN ('switch','keep','insufficient_data','no_baseline'))
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS learned_routing_preferences")
    op.execute("DROP TABLE IF EXISTS llm_review_queue")
    op.execute("DROP TABLE IF EXISTS output_violations")
