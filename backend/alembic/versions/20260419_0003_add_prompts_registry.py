"""Prompt registry — prompts + versions + rollouts

Revision ID: prompts_registry_0001
Revises: ai_usage_budget_0001

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §3 / E1.3.

Tasarım:
    prompts (1) ─── (*) prompt_versions (1) ─── (*) prompt_rollouts

    * ``prompts`` — her prompt'un kimliği + açıklaması + task_type (opsiyonel
      eşleme). Silinmez, sadece ``archived`` olur.
    * ``prompt_versions`` — versiyonlanmış gövde. (``prompt_id``, ``version``)
      composite unique. ``version`` monotonik integer (1, 2, 3, ...). İçerik
      immutable — yeni sürüm için yeni satır.
    * ``prompt_rollouts`` — (``prompt_id``, ``env``) bazlı aktif rollout.
      ``active_version`` canlıdaki referans; ``canary_version`` + ``canary_pct``
      trafiğin bir kısmına yeni versiyon gösterir. ``env`` = 'prod' | 'staging'
      | 'dev' (string, string enum değil — migration esnekliği için).

Neden ayrı rollouts tablosu:
    Aynı prompt'un staging'de canary %100, prod'da %10 canary olabilir.
    Versiyona bir state kolonu koymak birden çok env için yeterli değil.
"""
from alembic import op


revision = "prompts_registry_0001"
down_revision = "ai_usage_budget_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS prompts (
            id              VARCHAR(128) PRIMARY KEY,
            description     TEXT,
            task_type       VARCHAR(64),
            archived        BOOLEAN NOT NULL DEFAULT FALSE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by      VARCHAR(128),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS prompt_versions (
            id               BIGSERIAL PRIMARY KEY,
            prompt_id        VARCHAR(128) NOT NULL
                             REFERENCES prompts(id) ON DELETE CASCADE,
            version          INTEGER NOT NULL,
            system_prompt    TEXT NOT NULL DEFAULT '',
            user_template    TEXT NOT NULL DEFAULT '',
            model_hint       VARCHAR(64),
            temperature      DOUBLE PRECISION,
            max_tokens       INTEGER,
            notes            TEXT,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by       VARCHAR(128),
            UNIQUE (prompt_id, version),
            CHECK (version >= 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt_created
        ON prompt_versions(prompt_id, created_at DESC)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS prompt_rollouts (
            prompt_id        VARCHAR(128) NOT NULL
                             REFERENCES prompts(id) ON DELETE CASCADE,
            env              VARCHAR(32) NOT NULL DEFAULT 'prod',
            active_version   INTEGER NOT NULL,
            canary_version   INTEGER,
            canary_pct       SMALLINT NOT NULL DEFAULT 0,
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by       VARCHAR(128),
            PRIMARY KEY (prompt_id, env),
            CHECK (active_version >= 1),
            CHECK (canary_pct BETWEEN 0 AND 100),
            CHECK (canary_version IS NULL OR canary_version >= 1),
            CHECK (canary_pct = 0 OR canary_version IS NOT NULL)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS prompt_rollouts")
    op.execute("DROP INDEX IF EXISTS idx_prompt_versions_prompt_created")
    op.execute("DROP TABLE IF EXISTS prompt_versions")
    op.execute("DROP TABLE IF EXISTS prompts")
