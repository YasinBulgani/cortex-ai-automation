"""Neurex Management domain smoke tests."""

from __future__ import annotations

from app.domains.auth.permissions import Permission, ROLE_PERMISSIONS
from app.domains.rbac.policy import ROLES, has_permission, role_permissions
from app.domains.test_management.router import router


def test_test_management_router_exposes_core_surfaces() -> None:
    paths = {route.path for route in router.routes}

    assert "/test-management/health" in paths
    assert "/test-management/projects" in paths
    assert "/test-management/projects/{project_id}/repository" in paths
    assert "/test-management/projects/{project_id}/cases" in paths
    assert "/test-management/projects/{project_id}/plans" in paths
    assert "/test-management/projects/{project_id}/runs" in paths
    assert "/test-management/projects/{project_id}/reports/execution-summary" in paths
    assert "/test-management/projects/{project_id}/requirements" in paths
    assert "/test-management/projects/{project_id}/defects" in paths
    assert "/test-management/projects/{project_id}/imports" in paths
    assert "/test-management/projects/{project_id}/export" in paths


def test_test_management_permissions_are_mapped_to_runtime_roles() -> None:
    operator_permissions = set(ROLE_PERMISSIONS["operator"])
    viewer_permissions = set(ROLE_PERMISSIONS["viewer"])

    assert Permission.TEST_MANAGEMENT_READ.value in viewer_permissions
    assert Permission.TEST_MANAGEMENT_WRITE.value in operator_permissions
    assert Permission.TEST_MANAGEMENT_EXECUTE.value in operator_permissions
    assert Permission.TEST_MANAGEMENT_ADMIN.value in ROLE_PERMISSIONS["admin"]


def test_rbac_policy_roles_include_management_contract() -> None:
    assert has_permission(role_permissions(["viewer"]), "test_management.read")
    assert has_permission(role_permissions(["test_author"]), "test_management.write")
    assert has_permission(role_permissions(["test_author"]), "test_management.execute")
    assert has_permission(role_permissions(["ops"]), "test_management.admin")
    assert "test_management.audit" in ROLES["auditor"]
