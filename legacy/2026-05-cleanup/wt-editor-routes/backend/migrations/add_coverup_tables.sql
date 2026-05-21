-- Migration: CoverUp — Code coverage tracking tables
-- Safe to run multiple times (IF NOT EXISTS)

CREATE TABLE IF NOT EXISTS coverage_reports (
    id VARCHAR(64) PRIMARY KEY,
    project_name VARCHAR(256) DEFAULT '',
    commit_sha VARCHAR(64) DEFAULT '',
    branch VARCHAR(128) DEFAULT 'main',
    format VARCHAR(32) NOT NULL,  -- lcov, istanbul, cobertura, coveragepy
    -- Summary metrics
    total_files INTEGER DEFAULT 0,
    total_lines INTEGER DEFAULT 0,
    covered_lines INTEGER DEFAULT 0,
    missed_lines INTEGER DEFAULT 0,
    line_rate REAL DEFAULT 0.0,
    branch_rate REAL DEFAULT 0.0,
    function_rate REAL DEFAULT 0.0,
    total_functions INTEGER DEFAULT 0,
    covered_functions INTEGER DEFAULT 0,
    -- Raw data (JSON)
    files_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coverage_reports_project
    ON coverage_reports (project_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_coverage_reports_branch
    ON coverage_reports (branch, created_at DESC);

-- Per-file coverage data (for detailed queries)
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

CREATE INDEX IF NOT EXISTS idx_coverage_files_report
    ON coverage_file_details (report_id);

CREATE INDEX IF NOT EXISTS idx_coverage_files_path
    ON coverage_file_details (file_path);

-- Generated tests tracking
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

-- Coverage trend view
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

-- Banking critical paths view (files with low coverage in sensitive areas)
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
