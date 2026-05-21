"""RBAC permission definitions."""

from enum import Enum


class Permission(str, Enum):
    PROJECT_CREATE = "project.create"
    PROJECT_READ = "project.read"
    PROJECT_UPDATE = "project.update"
    PROJECT_DELETE = "project.delete"
    SCENARIO_CREATE = "scenario.create"
    SCENARIO_READ = "scenario.read"
    SCENARIO_UPDATE = "scenario.update"
    SCENARIO_DELETE = "scenario.delete"
    APPROVAL_DECIDE = "approval.decide"
    EXECUTION_CREATE = "execution.create"
    EXECUTION_UPDATE = "execution.update"
    IMPORT_CREATE = "import.create"
    FLOW_MANAGE = "flow.manage"
    REQUIREMENT_MANAGE = "requirement.manage"
    SCHEDULE_MANAGE = "schedule.manage"
    INTEGRATION_MANAGE = "integration.manage"
    API_TEST_MANAGE = "api_test.manage"
    TEST_DATA_MANAGE = "test_data.manage"
    ADMIN_FULL = "admin.*"


ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": [p.value for p in Permission],
    "operator": [
        Permission.PROJECT_CREATE.value,
        Permission.PROJECT_READ.value,
        Permission.PROJECT_UPDATE.value,
        Permission.SCENARIO_CREATE.value,
        Permission.SCENARIO_READ.value,
        Permission.SCENARIO_UPDATE.value,
        Permission.SCENARIO_DELETE.value,
        Permission.APPROVAL_DECIDE.value,
        Permission.EXECUTION_CREATE.value,
        Permission.EXECUTION_UPDATE.value,
        Permission.IMPORT_CREATE.value,
        Permission.FLOW_MANAGE.value,
        Permission.REQUIREMENT_MANAGE.value,
        Permission.SCHEDULE_MANAGE.value,
        Permission.INTEGRATION_MANAGE.value,
        Permission.API_TEST_MANAGE.value,
        Permission.TEST_DATA_MANAGE.value,
    ],
    "viewer": [
        Permission.PROJECT_READ.value,
        Permission.SCENARIO_READ.value,
    ],
}
