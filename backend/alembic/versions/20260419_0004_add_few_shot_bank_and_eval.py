"""Few-shot bank, LLM judge and eval harness tables.

Revision ID: few_shot_bank_0001
Revises: prompts_registry_0001

Plan: AI Stack Derin Gelistirme, Faz 2 + Faz 4.

Eklenen tablolar:
    - ``few_shot_examples``      — dinamik ornek bankasi
    - ``llm_judge_runs``         — LLM-as-Judge skor kayitlari
    - ``llm_eval_runs``          — golden set eval harness sonuclari

Ek olarak ``project_knowledge`` tablosuna hibrit arama icin:
    - ``content_tsv``  (tsvector + GIN index)
    - ``content_hash`` (sha256 dedup)
    - ``occurrence_count`` (dedup sayaci)
    - ``last_seen_at``
"""

from alembic import op


revision = "few_shot_bank_0001"
down_revision = "prompts_registry_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── few_shot_examples ────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS few_shot_examples (
            id                  SERIAL PRIMARY KEY,
            mode                VARCHAR(64)   NOT NULL,
            key                 VARCHAR(128)  NOT NULL,
            input_text          TEXT          NOT NULL,
            output_json         JSONB         NOT NULL,
            domain_tags         TEXT[]        DEFAULT ARRAY[]::TEXT[],
            quality_score       NUMERIC(4,2)  NOT NULL DEFAULT 5.00,
            verified_by_human   BOOLEAN       NOT NULL DEFAULT FALSE,
            is_negative         BOOLEAN       NOT NULL DEFAULT FALSE,
            bad_reason          TEXT,
            usage_count         INTEGER       NOT NULL DEFAULT 0,
            source              VARCHAR(64)   NOT NULL DEFAULT 'seed',
            created_at          TIMESTAMPTZ   NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ   NOT NULL DEFAULT now(),
            CONSTRAINT uq_few_shot_mode_key UNIQUE (mode, key)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_few_shot_mode ON few_shot_examples(mode)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_few_shot_quality ON few_shot_examples(quality_score DESC)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_few_shot_verified ON few_shot_examples(verified_by_human, quality_score DESC)"
    )
    # pgvector varsa embedding_vec kolonu + IVFFLAT index
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                ALTER TABLE few_shot_examples
                    ADD COLUMN IF NOT EXISTS embedding_vec vector(768);
                CREATE INDEX IF NOT EXISTS ix_few_shot_embedding_vec
                    ON few_shot_examples
                    USING ivfflat (embedding_vec vector_cosine_ops)
                    WITH (lists = 10);
            END IF;
        END
        $$;
        """
    )

    # ── llm_judge_runs ───────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_judge_runs (
            id                  BIGSERIAL PRIMARY KEY,
            trace_id            BIGINT,
            task_type           VARCHAR(64)   NOT NULL,
            judged_model        VARCHAR(128)  NOT NULL,
            judge_model         VARCHAR(128)  NOT NULL,
            correctness         NUMERIC(4,2),
            completeness        NUMERIC(4,2),
            domain_fit          NUMERIC(4,2),
            format_validity     NUMERIC(4,2),
            overall             NUMERIC(4,2),
            rationale           TEXT,
            sampled             BOOLEAN       NOT NULL DEFAULT TRUE,
            created_at          TIMESTAMPTZ   NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_judge_runs_task ON llm_judge_runs(task_type, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_judge_runs_judged_model ON llm_judge_runs(judged_model, created_at DESC)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_llm_judge_runs_trace ON llm_judge_runs(trace_id)")

    # ── llm_eval_runs ────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_eval_runs (
            id                  BIGSERIAL PRIMARY KEY,
            suite_name          VARCHAR(64)   NOT NULL,
            prompt_id           VARCHAR(128)  NOT NULL,
            task_type           VARCHAR(64)   NOT NULL,
            model               VARCHAR(128)  NOT NULL,
            tier                VARCHAR(16),
            pass_all            BOOLEAN       NOT NULL,
            property_results    JSONB         NOT NULL DEFAULT '[]'::jsonb,
            judge_overall       NUMERIC(4,2),
            latency_ms          INTEGER,
            cost_usd            NUMERIC(10,6),
            response_preview    TEXT,
            created_at          TIMESTAMPTZ   NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_eval_runs_suite ON llm_eval_runs(suite_name, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_eval_runs_prompt ON llm_eval_runs(prompt_id, created_at DESC)"
    )

    # ── knowledge_store hibrid arama: tsvector + dedup ───────────────────
    op.execute(
        """
        ALTER TABLE project_knowledge
        ADD COLUMN IF NOT EXISTS content_tsv tsvector
        """
    )
    op.execute(
        """
        UPDATE project_knowledge
        SET content_tsv = to_tsvector('simple', COALESCE(content, ''))
        WHERE content_tsv IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_project_knowledge_content_tsv
        ON project_knowledge USING GIN (content_tsv)
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION project_knowledge_tsv_update() RETURNS trigger AS $$
        BEGIN
            NEW.content_tsv := to_tsvector('simple', COALESCE(NEW.content, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_project_knowledge_tsv ON project_knowledge")
    op.execute(
        """
        CREATE TRIGGER trg_project_knowledge_tsv
        BEFORE INSERT OR UPDATE OF content ON project_knowledge
        FOR EACH ROW EXECUTE FUNCTION project_knowledge_tsv_update();
        """
    )

    op.execute(
        "ALTER TABLE project_knowledge ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)"
    )
    op.execute(
        "ALTER TABLE project_knowledge ADD COLUMN IF NOT EXISTS occurrence_count INTEGER NOT NULL DEFAULT 1"
    )
    op.execute(
        "ALTER TABLE project_knowledge ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ"
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_project_knowledge_hash
        ON project_knowledge(content_hash)
        WHERE content_hash IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_project_knowledge_hash")
    op.execute("ALTER TABLE project_knowledge DROP COLUMN IF EXISTS last_seen_at")
    op.execute("ALTER TABLE project_knowledge DROP COLUMN IF EXISTS occurrence_count")
    op.execute("ALTER TABLE project_knowledge DROP COLUMN IF EXISTS content_hash")

    op.execute("DROP TRIGGER IF EXISTS trg_project_knowledge_tsv ON project_knowledge")
    op.execute("DROP FUNCTION IF EXISTS project_knowledge_tsv_update()")
    op.execute("DROP INDEX IF EXISTS idx_project_knowledge_content_tsv")
    op.execute("ALTER TABLE project_knowledge DROP COLUMN IF EXISTS content_tsv")

    op.execute("DROP TABLE IF EXISTS llm_eval_runs")
    op.execute("DROP TABLE IF EXISTS llm_judge_runs")
    op.execute("DROP TABLE IF EXISTS few_shot_examples")
