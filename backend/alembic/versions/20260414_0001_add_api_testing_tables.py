"""Add AI-Powered API Testing tables

6 yeni tablo:
  - sd_apitest_environments  (ortam degisken yonetimi)
  - sd_apitest_specs         (OpenAPI/Swagger spec depolama)
  - sd_apitest_endpoints     (spec'ten cikarilan endpoint envanteri)
  - sd_apitest_cases         (AI uretilmis test case'ler)
  - sd_apitest_chains        (zincirlenmis istek akislari)
  - sd_apitest_execution_details (istek bazinda calisma detayi)

Revision ID: api_testing_0001
Revises: refresh_tokens_0003
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "api_testing_0001"
down_revision = "refresh_tokens_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Environments
    op.execute("""
    CREATE TABLE IF NOT EXISTS sd_apitest_environments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id UUID NOT NULL REFERENCES tspm_projects(id) ON DELETE CASCADE,
        name VARCHAR(200) NOT NULL,
        description TEXT,
        variables JSONB NOT NULL DEFAULT '{}',
        sensitive_keys JSONB NOT NULL DEFAULT '[]',
        is_default BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_apienv_project ON sd_apitest_environments(project_id)")

    # 2. Specs
    op.execute("""
    CREATE TABLE IF NOT EXISTS sd_apitest_specs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id UUID NOT NULL REFERENCES tspm_projects(id) ON DELETE CASCADE,
        name VARCHAR(300) NOT NULL,
        version VARCHAR(64),
        spec_format VARCHAR(32) NOT NULL,
        spec_content JSONB NOT NULL DEFAULT '{}',
        resolved_content JSONB,
        source_url VARCHAR(1000),
        source_file VARCHAR(500),
        endpoint_count INTEGER DEFAULT 0,
        schema_count INTEGER DEFAULT 0,
        ai_analysis JSONB,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_apispec_project ON sd_apitest_specs(project_id)")

    # 3. Endpoints
    op.execute("""
    CREATE TABLE IF NOT EXISTS sd_apitest_endpoints (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        spec_id UUID NOT NULL REFERENCES sd_apitest_specs(id) ON DELETE CASCADE,
        method VARCHAR(16) NOT NULL,
        path VARCHAR(1000) NOT NULL,
        operation_id VARCHAR(200),
        summary VARCHAR(500),
        description TEXT,
        tags JSONB DEFAULT '[]',
        parameters JSONB DEFAULT '[]',
        request_body_schema JSONB,
        response_schemas JSONB DEFAULT '{}',
        security_requirements JSONB,
        auth_required BOOLEAN DEFAULT TRUE,
        risk_level VARCHAR(32) DEFAULT 'medium',
        has_pii BOOLEAN DEFAULT FALSE,
        has_financial BOOLEAN DEFAULT FALSE,
        compliance_tags JSONB DEFAULT '[]',
        depends_on JSONB DEFAULT '[]',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_apiendpoint_spec ON sd_apitest_endpoints(spec_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_apiendpoint_method_path ON sd_apitest_endpoints(method, path)")

    # 4. Test Cases
    op.execute("""
    CREATE TABLE IF NOT EXISTS sd_apitest_cases (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id UUID NOT NULL REFERENCES tspm_projects(id) ON DELETE CASCADE,
        endpoint_id UUID REFERENCES sd_apitest_endpoints(id) ON DELETE SET NULL,
        collection_id UUID REFERENCES tspm_api_collections(id) ON DELETE SET NULL,

        title VARCHAR(500) NOT NULL,
        description TEXT,
        test_type VARCHAR(64) NOT NULL,
        priority VARCHAR(32) DEFAULT 'P2',

        owasp_category VARCHAR(16),
        regulation VARCHAR(32),
        cwe_id VARCHAR(16),

        request_method VARCHAR(16) NOT NULL,
        request_path VARCHAR(1000) NOT NULL,
        request_headers JSONB DEFAULT '{}',
        request_params JSONB DEFAULT '{}',
        request_body JSONB,

        pre_request_vars JSONB,
        setup_chain JSONB,
        assertions JSONB DEFAULT '[]',

        ai_generated BOOLEAN DEFAULT TRUE,
        ai_model VARCHAR(128),
        ai_confidence FLOAT,
        ai_reasoning TEXT,

        review_status VARCHAR(32) DEFAULT 'pending',
        reviewer_id UUID,
        reviewer_note TEXT,

        last_run_status VARCHAR(32),
        last_run_at TIMESTAMPTZ,
        last_run_duration_ms FLOAT,
        run_count INTEGER DEFAULT 0,
        pass_count INTEGER DEFAULT 0,
        fail_count INTEGER DEFAULT 0,

        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_apitc_project ON sd_apitest_cases(project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_apitc_endpoint ON sd_apitest_cases(endpoint_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_apitc_type ON sd_apitest_cases(test_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_apitc_review ON sd_apitest_cases(review_status)")

    # 5. Chains
    op.execute("""
    CREATE TABLE IF NOT EXISTS sd_apitest_chains (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id UUID NOT NULL REFERENCES tspm_projects(id) ON DELETE CASCADE,
        name VARCHAR(300) NOT NULL,
        description TEXT,
        nodes JSONB DEFAULT '[]',
        edges JSONB DEFAULT '[]',
        global_variables JSONB DEFAULT '{}',
        ai_generated BOOLEAN DEFAULT FALSE,
        ai_reasoning TEXT,
        stop_on_failure BOOLEAN DEFAULT TRUE,
        max_retries INTEGER DEFAULT 0,
        delay_between_ms INTEGER DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_apichain_project ON sd_apitest_chains(project_id)")

    # 6. Execution Details
    op.execute("""
    CREATE TABLE IF NOT EXISTS sd_apitest_execution_details (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        run_id UUID NOT NULL REFERENCES tspm_api_test_runs(id) ON DELETE CASCADE,
        test_case_id UUID REFERENCES sd_apitest_cases(id) ON DELETE SET NULL,

        actual_method VARCHAR(16) NOT NULL,
        actual_url VARCHAR(2000) NOT NULL,
        actual_headers JSONB DEFAULT '{}',
        actual_body JSONB,

        status_code INTEGER,
        response_headers JSONB DEFAULT '{}',
        response_body TEXT,
        response_size_bytes INTEGER,

        dns_ms FLOAT,
        tcp_ms FLOAT,
        tls_ms FLOAT,
        ttfb_ms FLOAT,
        download_ms FLOAT,
        total_ms FLOAT DEFAULT 0,

        assertion_results JSONB DEFAULT '[]',
        passed BOOLEAN DEFAULT FALSE,
        error_message TEXT,

        schema_valid BOOLEAN,
        schema_errors JSONB DEFAULT '[]',

        diff_from_previous JSONB,
        extracted_variables JSONB DEFAULT '{}',

        executed_at TIMESTAMPTZ DEFAULT now(),
        execution_order INTEGER DEFAULT 0
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_apiexec_run ON sd_apitest_execution_details(run_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_apiexec_testcase ON sd_apitest_execution_details(test_case_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_apiexec_status ON sd_apitest_execution_details(passed)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sd_apitest_execution_details CASCADE")
    op.execute("DROP TABLE IF EXISTS sd_apitest_chains CASCADE")
    op.execute("DROP TABLE IF EXISTS sd_apitest_cases CASCADE")
    op.execute("DROP TABLE IF EXISTS sd_apitest_endpoints CASCADE")
    op.execute("DROP TABLE IF EXISTS sd_apitest_specs CASCADE")
    op.execute("DROP TABLE IF EXISTS sd_apitest_environments CASCADE")
