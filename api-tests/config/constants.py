"""API path constants and shared values."""


class FastAPIPaths:
    HEALTH = "/health"
    READY = "/ready"

    AUTH_LOGIN = "/api/v1/auth/login"
    AUTH_ME = "/api/v1/auth/me"

    DATASETS = "/api/v1/datasets"
    DATASET_DETAIL = "/api/v1/datasets/{dataset_id}"
    DATASET_VERSIONS = "/api/v1/datasets/{dataset_id}/versions"
    DATASET_VERSION_SCHEMA = "/api/v1/datasets/{dataset_id}/versions/{version_id}/schema"

    RULE_SETS = "/api/v1/datasets/{dataset_id}/rule-sets"
    RULE_SET_DETAIL = "/api/v1/datasets/{dataset_id}/rule-sets/{rule_set_id}"

    JOBS = "/api/v1/jobs"
    JOB_DETAIL = "/api/v1/jobs/{job_id}"
    JOB_EVENTS = "/api/v1/jobs/{job_id}/events"
    JOB_ARTIFACTS = "/api/v1/jobs/{job_id}/artifacts"

    ARTIFACT_DOWNLOAD = "/api/v1/artifacts/{artifact_id}/download"

    TSPM_PROJECTS = "/api/v1/tspm/projects"
    TSPM_PROJECT_DASHBOARD = "/api/v1/tspm/projects/{project_id}/dashboard"

    TSPM_SCENARIOS = "/api/v1/tspm/projects/{project_id}/scenarios"
    TSPM_SCENARIO_DETAIL = "/api/v1/tspm/projects/{project_id}/scenarios/{scenario_id}"
    TSPM_SCENARIOS_GENERATE_BDD = "/api/v1/tspm/projects/{project_id}/scenarios/generate-bdd"
    TSPM_SCENARIOS_SAVE_BDD = "/api/v1/tspm/projects/{project_id}/scenarios/save-bdd"
    TSPM_SCENARIOS_BULK_DELETE = "/api/v1/tspm/projects/{project_id}/scenarios/bulk-delete"

    TSPM_REQUIREMENTS = "/api/v1/tspm/projects/{project_id}/requirements"
    TSPM_REQUIREMENT_DETAIL = "/api/v1/tspm/projects/{project_id}/requirements/{requirement_id}"
    TSPM_SCENARIO_REQUIREMENTS = "/api/v1/tspm/projects/{project_id}/scenarios/{scenario_id}/requirements"
    TSPM_COVERAGE_MATRIX = "/api/v1/tspm/projects/{project_id}/coverage-matrix"
    TSPM_COVERAGE_GAPS = "/api/v1/tspm/projects/{project_id}/coverage-gaps"

    TSPM_EXECUTIONS = "/api/v1/tspm/projects/{project_id}/executions"
    TSPM_EXECUTION_DETAIL = "/api/v1/tspm/projects/{project_id}/executions/{run_id}"
    TSPM_EXECUTION_RESULT = "/api/v1/tspm/projects/{project_id}/executions/{run_id}/results/{result_id}"

    TSPM_FLOWS = "/api/v1/tspm/projects/{project_id}/flows"
    TSPM_FLOW_DETAIL = "/api/v1/tspm/projects/{project_id}/flows/{flow_id}"
    TSPM_FLOW_GRAPH = "/api/v1/tspm/projects/{project_id}/flows/{flow_id}/graph"

    TSPM_REGRESSION_SETS = "/api/v1/tspm/projects/{project_id}/regression-sets"
    TSPM_REGRESSION_SET_ADD = "/api/v1/tspm/projects/{project_id}/regression-sets/{set_id}/add"
    TSPM_REGRESSION_SUGGEST = "/api/v1/tspm/projects/{project_id}/regression-sets/suggest"

    TSPM_SCHEDULES = "/api/v1/tspm/projects/{project_id}/schedules"
    TSPM_SCHEDULE_TRIGGER = "/api/v1/tspm/projects/{project_id}/schedules/{schedule_id}/trigger"

    TSPM_INTEGRATIONS = "/api/v1/tspm/projects/{project_id}/integrations"
    TSPM_INTEGRATION_SYNC = "/api/v1/tspm/projects/{project_id}/integrations/{integration_id}/sync"

    TSPM_API_COLLECTIONS = "/api/v1/tspm/projects/{project_id}/api-tests/collections"
    TSPM_API_COLLECTION_RUN = "/api/v1/tspm/projects/{project_id}/api-tests/collections/{collection_id}/run"
    TSPM_API_RUNS = "/api/v1/tspm/projects/{project_id}/api-tests/runs"

    TSPM_APPROVALS = "/api/v1/tspm/projects/{project_id}/approvals"
    TSPM_APPROVAL_DECIDE = "/api/v1/tspm/projects/{project_id}/approvals/{approval_id}/decide"

    TSPM_MEMBERS = "/api/v1/tspm/projects/{project_id}/members"

    WS_NOTIFICATIONS = "/api/v1/ws/notifications"


class EnginePaths:
    HEALTH = "/health"
    API_HEALTH = "/api/health"

    AUTH_REGISTER = "/api/auth/register"
    AUTH_LOGIN = "/api/auth/login"
    AUTH_LOGOUT = "/api/auth/logout"
    AUTH_VERIFY = "/api/auth/verify/{token}"

    FEATURES = "/api/features"
    FEATURE_FOLDER = "/api/features/folder"
    FEATURE_DETAIL = "/api/features/{name}"

    REGRESSION_SETS = "/api/regression-sets"
    REGRESSION_SET_DETAIL = "/api/regression-sets/{set_id}"
    REGRESSION_SET_FEATURES = "/api/regression-sets/{set_id}/features"

    MANUAL_TESTS = "/api/manual-tests"
    MANUAL_TEST_DETAIL = "/api/manual-tests/{test_id}"
    MANUAL_TEST_STEPS = "/api/manual-tests/{test_id}/steps"
    MANUAL_STEP_DETAIL = "/api/manual-test-steps/{step_id}"
    GENERATE_MANUAL = "/api/generate-manual-from-doc"

    LOCATORS = "/api/locators"
    LOCATOR_DETAIL = "/api/locators/{loc_id}"
    DISCOVER = "/api/discover"

    RUN = "/api/run"
    RUN_STREAM = "/api/run/{run_id}/stream"
    RUN_MAVEN = "/api/run-maven"

    GENERATE_FEATURE = "/api/generate-feature"
    ANALYZE_API = "/api/analyze-api-request"
    SECURITY_SCAN = "/api/security-scan"
    INSPECT = "/api/inspect"

    SETTINGS = "/api/settings"
    STATS = "/api/stats"
    REPORTS = "/api/reports/comprehensive"
    PROXY_REQUEST = "/api/request"
    EXPORT = "/api/export"

    DATASIM_DATASETS = "/api/datasim/datasets"
    DATASIM_LOAD = "/api/datasim/datasets/load"
    DATASIM_GENERATE = "/api/datasim/generate"

    VISUAL_BASELINES = "/api/visual/baselines"
    VISUAL_COMPARE = "/api/visual/compare"
    VISUAL_BATCH = "/api/visual/batch"

    A11Y_TEST = "/api/a11y/test"
    A11Y_BATCH = "/api/a11y/test/batch"
    A11Y_REPORT = "/api/a11y/report"
    A11Y_CONFIG = "/api/a11y/config"

    RECORDER_START = "/api/recorder/start"
    RECORDER_STOP = "/api/recorder/{session_id}/stop"
    RECORDER_SESSIONS = "/api/recorder/sessions"
    RECORDER_GENERATE = "/api/recorder/generate"

    PROJECTS = "/api/projects"
    PROJECT_CREATE = "/api/projects/create"
    PROJECT_DETAIL = "/api/projects/{name}"

    LIFECYCLE_ANALYST = "/api/lifecycle/process-analyst"
