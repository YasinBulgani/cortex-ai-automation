"""Add CoverUp code coverage tracking tables

Tables:
  - coverage_reports: Summary coverage data per upload
  - coverage_file_details: Per-file coverage metrics
  - coverup_generated_tests: AI-generated test tracking
Views:
  - coverage_trend: Time-series of coverage metrics
  - coverage_banking_critical: Files with low coverage in banking-critical paths

Revision ID: coverup_0003
Revises: heal_history_0002
"""

from alembic import op

revision = "coverup_0003"
down_revision = "heal_history_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Coverage Reports ─────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS coverage_reports (
        id VARCHAR(64) PRIMARY KEY,
        project_name VARCHAR(256) DEFAULT '',
        commit_sha VARCHAR(64) DEFAULT '',
        branch VARCHAR(128) DEFAULT 'main',
        format VARCHAR(32) NOT NULL,
        total_files INTEGER DEFAULT 0,
        total_lines INTEGER DEFAULT 0,
        covered_lines INTEGER DEFAULT 0,
        missed_lines INTEGER DEFAULT 0,
        line_rate REAL DEFAULT 0.0,
        branch_rate REAL DEFAULT 0.0,
        function_rate REAL DEFAULT 0.0,
        total_functions INTEGER DEFAULT 0,
        covered_functions INTEGER DEFAULT 0,
        files_json JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """)

    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_coverage_reports_project
        ON coverage_reports (project_name, created_at DESC);
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_coverage_reports_branch
        ON coverage_reports (branch, created_at DESC);
    """)

    # ── Per-file Details ─────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS coverage_file_details (
        id SERIAL PRIMARY KEY,
        report_id VARCHAR(64) REFERENCES coverage_reports(id) ON DELETE CASCADE,
        file_path VARCHAR(512) NOT NULL,
        total_lines INTEGER DEFAULT 0,
        covered_lines INTEGER DEFAULT 0,
        missed_lines INTEGER DEFAULT 0,
        line_rate REAL DEFAULT 0.0,
        branch_rate REAL DEFAULT 0.0,
        total_functions INTEGER DEFAULT 0,
        covered_functions INTEGER DEFAULT 0,
        missed_line_numbers INTEGER[] DEFAULT '{}',
        uncovered_functions TEXT[] DEFAULT '{}',
        complexity REAL
    );
    """)

    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_coverage_files_report
        ON coverage_file_details (report_id);
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_coverage_files_path
        ON coverage_file_details (file_path);
    """)

    # ── Generated Tests ──────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS coverup_generated_tests (
        id SERIAL PRIMARY KEY,
        report_id VARCHAR(64),
        target_file VARCHAR(512),
        target_function VARCHAR(256),
        test_file_path VARCHAR(512),
        test_framework VARCHAR(32),
        estimated_gain REAL DEFAULT 0.0,
        lines_targeted INTEGER[] DEFAULT '{}',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """)

    # ── Views ────────────────────────────────────────────────────────────
    op.execute("""
    CREATE OR REPLACE VIEW coverage_trend AS
    SELECT
        id AS report_id,
        project_name,
        commit_sha,
        branch,
        format,
        created_at,
        line_rate,
        branch_rate,
        function_rate,
        total_lines,
        covered_lines,
        total_files
    FROM coverage_reports
    ORDER BY created_at DESC;
    """)

    op.execute("""
    CREATE OR REPLACE VIEW coverage_banking_critical AS
    SELECT
        cfd.report_id,
        cfd.file_path,
        cfd.line_rate,
        cfd.branch_rate,
        cfd.missed_lines,
        cfd.uncovered_functions,
        cr.created_at
    FROM coverage_file_details cfd
    JOIN coverage_reports cr ON cr.id = cfd.report_id
    WHERE cfd.line_rate < 0.70
      AND (
        cfd.file_path ILIKE '%payment%'
        OR cfd.file_path ILIKE '%transfer%'
        OR cfd.file_path ILIKE '%auth%'
        OR cfd.file_path ILIKE '%session%'
        OR cfd.file_path ILIKE '%kyc%'
        OR cfd.file_path ILIKE '%kvkk%'
        OR cfd.file_path ILIKE '%pii%'
        OR cfd.file_path ILIKE '%encrypt%'
        OR cfd.file_path ILIKE '%security%'
        OR cfd.file_path ILIKE '%compliance%'
      )
    ORDER BY cfd.line_rate ASC;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS coverage_banking_critical;")
    op.execute("DROP VIEW IF EXISTS coverage_trend;")
    op.execute("DROP TABLE IF EXISTS coverup_generated_tests;")
    op.execute("DROP INDEX IF EXISTS idx_coverage_files_path;")
    op.execute("DROP INDEX IF EXISTS idx_coverage_files_report;")
    op.execute("DROP TABLE IF EXISTS coverage_file_details;")
    op.execute("DROP INDEX IF EXISTS idx_coverage_reports_branch;")
    op.execute("DROP INDEX IF EXISTS idx_coverage_reports_project;")
    op.execute("DROP TABLE IF EXISTS coverage_reports;")
