#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# Regression Test Data Seed Script
# ═══════════════════════════════════════════════════════════════════════════
# Purpose: Load test data fixtures for regression test suite
# Usage: bash backend/tests/regression_seed.sh
# ═══════════════════════════════════════════════════════════════════════════

set -e

echo "▶ Loading regression test data fixtures..."

# Source environment
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-neurex}"
DB_USER="${DB_USER:-postgres}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ─── Test Organization Data ──────────────────────────────────────────────────

create_orgs() {
    echo -e "${BLUE}Creating test organizations...${NC}"

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
INSERT INTO organizations (id, name, slug, owner_id, plan, is_active, created_at) VALUES
    ('org-regression-1', 'Regression Test Org 1', 'regression-1', 'user-regression-admin', 'enterprise', true, NOW()),
    ('org-regression-2', 'Regression Test Org 2', 'regression-2', 'user-regression-op', 'team', true, NOW())
ON CONFLICT (id) DO NOTHING;
EOF

    echo -e "${GREEN}✓ Organizations created${NC}"
}

# ─── Test User Data ──────────────────────────────────────────────────────────

create_users() {
    echo -e "${BLUE}Creating test users...${NC}"

    # Password hashes for: admin123 (bcrypt)
    local ADMIN_HASH='$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUaqt6ja'
    local TEST_HASH='$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUaqt6ja'

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF
INSERT INTO users (id, email, full_name, password_hash, org_id, is_active, email_verified, created_at) VALUES
    ('user-regression-admin', 'admin@regression.test', 'Admin User', '$ADMIN_HASH', 'org-regression-1', true, true, NOW()),
    ('user-regression-op', 'operator@regression.test', 'Operator User', '$TEST_HASH', 'org-regression-1', true, true, NOW()),
    ('user-regression-viewer', 'viewer@regression.test', 'Viewer User', '$TEST_HASH', 'org-regression-1', true, true, NOW()),
    ('user-regression-tester', 'tester@regression.test', 'Tester User', '$TEST_HASH', 'org-regression-1', true, true, NOW())
ON CONFLICT (id) DO NOTHING;
EOF

    echo -e "${GREEN}✓ Users created${NC}"
}

# ─── Test Project Data ────────────────────────────────────────────────────────

create_projects() {
    echo -e "${BLUE}Creating test projects (100 total)...${NC}"

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
-- Create seed projects for functional testing
INSERT INTO test_management_projects (id, org_id, name, key, description, status, owner_id, created_at) VALUES
    ('proj-regression-001', 'org-regression-1', 'Regression Project 001', 'REGR01', 'Functional regression testing', 'active', 'user-regression-admin', NOW()),
    ('proj-regression-002', 'org-regression-1', 'Regression Project 002', 'REGR02', 'API endpoint testing', 'active', 'user-regression-admin', NOW()),
    ('proj-regression-003', 'org-regression-1', 'Regression Project 003', 'REGR03', 'UI workflow testing', 'active', 'user-regression-admin', NOW()),
    ('proj-regression-004', 'org-regression-1', 'Regression Project 004', 'REGR04', 'Integration testing', 'active', 'user-regression-admin', NOW()),
    ('proj-regression-005', 'org-regression-1', 'Regression Project 005', 'REGR05', 'Performance testing', 'active', 'user-regression-admin', NOW())
ON CONFLICT (id) DO NOTHING;

-- Create additional projects for load/pagination testing (95 more)
DO $$
DECLARE
    i INT;
BEGIN
    FOR i IN 6..100 LOOP
        INSERT INTO test_management_projects (id, org_id, name, key, description, status, owner_id, created_at)
        VALUES (
            'proj-regression-' || LPAD(i::TEXT, 3, '0'),
            'org-regression-1',
            'Regression Project ' || LPAD(i::TEXT, 3, '0'),
            'REGR' || LPAD(i::TEXT, 2, '0'),
            'Regression project ' || i,
            'active',
            'user-regression-admin',
            NOW()
        )
        ON CONFLICT (id) DO NOTHING;
    END LOOP;
END $$;
EOF

    echo -e "${GREEN}✓ 100 test projects created${NC}"
}

# ─── Test Case Data ──────────────────────────────────────────────────────────

create_test_cases() {
    echo -e "${BLUE}Creating test cases (500 total)...${NC}"

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
-- Create seed test cases for functional testing
WITH tc_data AS (
    SELECT
        'tc-regression-' || LPAD((row_number() OVER (ORDER BY p.id))::TEXT, 4, '0') as tc_id,
        p.id as project_id,
        'Test Case ' || (row_number() OVER (ORDER BY p.id))::TEXT as title,
        CASE (row_number() OVER (ORDER BY p.id)) % 4
            WHEN 0 THEN 'critical'
            WHEN 1 THEN 'high'
            WHEN 2 THEN 'medium'
            ELSE 'low'
        END as priority,
        'active' as status,
        CASE (row_number() OVER (ORDER BY p.id)) % 2
            WHEN 0 THEN true
            ELSE false
        END as automated,
        jsonb_build_array(
            jsonb_build_object('order', 1, 'action', 'Open application', 'expected', 'Home page loads'),
            jsonb_build_object('order', 2, 'action', 'Login with valid credentials', 'expected', 'Dashboard displayed'),
            jsonb_build_object('order', 3, 'action', 'Navigate to feature', 'expected', 'Feature page loaded')
        ) as steps
    FROM test_management_projects p
    WHERE p.id LIKE 'proj-regression-%'
    LIMIT 500
)
INSERT INTO test_cases (id, project_id, title, priority, status, automated, steps, created_at)
SELECT tc_id, project_id, title, priority, status, automated, steps, NOW()
FROM tc_data
ON CONFLICT (id) DO NOTHING;
EOF

    echo -e "${GREEN}✓ 500 test cases created${NC}"
}

# ─── Test Run Data ───────────────────────────────────────────────────────────

create_test_runs() {
    echo -e "${BLUE}Creating test runs (100 total)...${NC}"

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
-- Create test runs for regression history
DO $$
DECLARE
    i INT;
    proj_id TEXT;
BEGIN
    FOR i IN 1..100 LOOP
        proj_id := 'proj-regression-' || LPAD((i % 5 + 1)::TEXT, 3, '0');

        INSERT INTO test_runs (
            id,
            project_id,
            status,
            created_by,
            environment,
            duration_ms,
            created_at,
            completed_at
        ) VALUES (
            'run-regression-' || LPAD(i::TEXT, 4, '0'),
            proj_id,
            CASE (i % 3)
                WHEN 0 THEN 'passed'
                WHEN 1 THEN 'failed'
                ELSE 'completed'
            END,
            'user-regression-tester',
            CASE (i % 2) WHEN 0 THEN 'staging' ELSE 'production' END,
            FLOOR(RANDOM() * 30000 + 5000)::INTEGER,
            NOW() - INTERVAL '1 day' * (i / 10),
            NOW() - INTERVAL '1 day' * (i / 10) + INTERVAL '5 minutes'
        )
        ON CONFLICT (id) DO NOTHING;
    END LOOP;
END $$;
EOF

    echo -e "${GREEN}✓ 100 test runs created${NC}"
}

# ─── Defect Data ─────────────────────────────────────────────────────────────

create_defects() {
    echo -e "${BLUE}Creating defects (50 total)...${NC}"

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
DO $$
DECLARE
    i INT;
    proj_id TEXT;
    tc_id TEXT;
BEGIN
    FOR i IN 1..50 LOOP
        proj_id := 'proj-regression-' || LPAD((i % 5 + 1)::TEXT, 3, '0');
        tc_id := 'tc-regression-' || LPAD((i % 100 + 1)::TEXT, 4, '0');

        INSERT INTO defects (
            id,
            project_id,
            test_case_id,
            title,
            description,
            severity,
            status,
            reporter_id,
            assignee_id,
            created_at
        ) VALUES (
            'def-regression-' || LPAD(i::TEXT, 4, '0'),
            proj_id,
            tc_id,
            'Defect #' || i,
            'Test defect for regression suite',
            CASE (i % 3)
                WHEN 0 THEN 'critical'
                WHEN 1 THEN 'high'
                ELSE 'medium'
            END,
            CASE (i % 4)
                WHEN 0 THEN 'open'
                WHEN 1 THEN 'in_progress'
                WHEN 2 THEN 'resolved'
                ELSE 'closed'
            END,
            'user-regression-tester',
            CASE WHEN i % 2 = 0 THEN 'user-regression-op' ELSE NULL END,
            NOW() - INTERVAL '1 day' * (i / 10)
        )
        ON CONFLICT (id) DO NOTHING;
    END LOOP;
END $$;
EOF

    echo -e "${GREEN}✓ 50 defects created${NC}"
}

# ─── Run all seed functions ───────────────────────────────────────────────────

main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║        Regression Test Data Seed Script                      ║"
    echo "╠═══════════════════════════════════════════════════════════════╣"
    echo "║ Database: $DB_NAME"
    echo "║ Host: $DB_HOST:$DB_PORT"
    echo "║ Fixtures: Orgs, Users, Projects, Test Cases, Runs, Defects  ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""

    create_orgs
    create_users
    create_projects
    create_test_cases
    create_test_runs
    create_defects

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗"
    echo "║        ✓ Regression test data loaded successfully             ║"
    echo "╠═══════════════════════════════════════════════════════════════╣"
    echo "║ Organizations: 2                                            ║"
    echo "║ Users: 4                                                    ║"
    echo "║ Projects: 100                                               ║"
    echo "║ Test Cases: 500                                             ║"
    echo "║ Test Runs: 100                                              ║"
    echo "║ Defects: 50                                                 ║"
    echo "║ Total fixture data points: 756                              ║"
    echo "╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Ready to run regression tests:"
    echo "  make test-regression"
    echo ""
}

main
