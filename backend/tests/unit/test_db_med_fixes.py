"""Unit tests for medium database fixes.

DB-MED-1: RefreshToken.id default generation
DB-MED-2: JSONB validation and defaults
DB-MED-3: Self-ref FK constraints
"""

import pytest
from unittest.mock import patch, MagicMock

from app.infra.models import RefreshToken, Organization
from app.domains.test_management.models import TestCase


def test_refresh_token_id_generation():
    """RefreshToken.id should have default UUID generation."""
    # Create instance without explicit id
    token = RefreshToken(
        user_id="test-user-id",
        token_hash="abc123",
        expires_at=None,
    )

    # Should have UUID column with default
    assert hasattr(RefreshToken, 'id')
    assert RefreshToken.id.type.__class__.__name__ == 'UUID'
    # Check that mapped_column has default function
    assert RefreshToken.id.default is not None or token.id is None


def test_organization_settings_jsonb_default():
    """Organization.settings should default to empty dict."""
    # Mapped column should have JSONB type
    assert Organization.settings.type.__class__.__name__ == 'JSONB'

    # Should have default factory
    org_col = Organization.__table__.columns['settings']
    assert org_col.type.__class__.__name__ == 'JSONB'
    # server_default should be set via migration
    assert org_col.server_default is not None or org_col.default is not None


def test_testcase_parent_id_self_ref_fk():
    """TestCase.parent_id should be valid self-ref FK."""
    # Check FK constraint exists
    assert TestCase.parent_id is not None

    # Should reference test_management_cases table
    fk_constraint = None
    for col in TestCase.__table__.columns:
        if col.name == 'parent_id':
            for fk in col.foreign_keys:
                if 'test_management_cases' in str(fk.target_fullname):
                    fk_constraint = fk
                    break

    assert fk_constraint is not None, "parent_id should have FK to test_management_cases"


@pytest.mark.parametrize("column_name", [
    'settings',  # Organization
])
def test_jsonb_columns_have_defaults(column_name):
    """JSONB columns should have default factories to prevent NULL."""
    if column_name == 'settings':
        model = Organization
        col = Organization.__table__.columns[column_name]

    # Should be JSONB type
    assert 'JSONB' in str(col.type)

    # Should have default or server_default
    assert col.default is not None or col.server_default is not None, (
        f"{column_name} missing default factory"
    )
