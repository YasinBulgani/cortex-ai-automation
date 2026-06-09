"""
Unit tests for authentication core module.

Category: Core Modules - Authentication & Security
Tests: 8 total
Markers: @pytest.mark.regression, @pytest.mark.unit, @pytest.mark.P1
"""

import pytest
from unittest.mock import patch, MagicMock
import hashlib
import hmac


class TestPasswordHashing:
    """Password hashing and verification unit tests."""

    @pytest.mark.regression
    def test_hash_password_creates_valid_hash(self):
        """Verify password hashing generates non-plain-text hash."""
        from app.domains.auth.service import AuthService

        auth_svc = AuthService(db=None)
        password = "TestPassword123!@#"

        # Hash password
        hashed = auth_svc.hash_password(password)

        # Assert
        assert hashed != password, "Hash should not equal plain password"
        assert len(hashed) > 20, "Hash should have substantial length"
        assert "$2a$" in hashed or "$2b$" in hashed, "Should use bcrypt format"

    @pytest.mark.regression
    def test_hash_password_same_password_different_hashes(self):
        """Verify same password produces different hashes (salt variation)."""
        from app.domains.auth.service import AuthService

        auth_svc = AuthService(db=None)
        password = "TestPassword123!@#"

        # Hash same password twice
        hash1 = auth_svc.hash_password(password)
        hash2 = auth_svc.hash_password(password)

        # Assert — hashes differ due to salt
        assert hash1 != hash2, "Same password should produce different hashes (salt)"

    @pytest.mark.regression
    def test_verify_password_correct(self):
        """Verify correct password validates successfully."""
        from app.domains.auth.service import AuthService

        auth_svc = AuthService(db=None)
        password = "CorrectPassword123"
        hashed = auth_svc.hash_password(password)

        # Verify correct password
        is_valid = auth_svc.verify_password(password, hashed)

        assert is_valid is True, "Correct password should validate"

    @pytest.mark.regression
    def test_verify_password_incorrect(self):
        """Verify incorrect password fails validation."""
        from app.domains.auth.service import AuthService

        auth_svc = AuthService(db=None)
        correct_password = "CorrectPassword123"
        wrong_password = "WrongPassword456"
        hashed = auth_svc.hash_password(correct_password)

        # Verify wrong password
        is_valid = auth_svc.verify_password(wrong_password, hashed)

        assert is_valid is False, "Wrong password should not validate"

    @pytest.mark.regression
    def test_verify_password_empty_string(self):
        """Verify empty password fails validation."""
        from app.domains.auth.service import AuthService

        auth_svc = AuthService(db=None)
        password = "ValidPassword123"
        hashed = auth_svc.hash_password(password)

        # Verify empty password
        is_valid = auth_svc.verify_password("", hashed)

        assert is_valid is False, "Empty password should not validate"


class TestJWTTokenGeneration:
    """JWT token generation and validation tests."""

    @pytest.mark.regression
    def test_generate_jwt_token_contains_claims(self):
        """Verify JWT token contains required claims."""
        from app.domains.auth.service import AuthService
        import jwt
        from app.config import settings

        auth_svc = AuthService(db=None)
        user_id = "user-123"
        email = "test@example.com"

        # Generate token
        token = auth_svc.generate_jwt_token(user_id=user_id, email=email)

        # Decode and verify claims
        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )

        assert decoded["sub"] == user_id, "Token should contain user_id as 'sub'"
        assert decoded["email"] == email, "Token should contain email"
        assert "iat" in decoded, "Token should contain issue time"
        assert "exp" in decoded, "Token should contain expiration"

    @pytest.mark.regression
    def test_jwt_token_expiration_set_correctly(self):
        """Verify JWT token expiration is set to configured value."""
        from app.domains.auth.service import AuthService
        import jwt
        from app.config import settings
        import time

        auth_svc = AuthService(db=None)

        # Generate token
        token = auth_svc.generate_jwt_token(user_id="user-123", email="test@example.com")

        # Decode
        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )

        # Calculate expiration
        iat = decoded["iat"]
        exp = decoded["exp"]
        duration = exp - iat

        # Assert — should be roughly 24 hours (86400 seconds)
        assert 86300 <= duration <= 86500, f"Token duration should be ~24h, got {duration}s"

    @pytest.mark.regression
    def test_jwt_token_invalid_signature_rejected(self):
        """Verify token with invalid signature is rejected."""
        from app.domains.auth.service import AuthService
        import jwt
        from app.config import settings

        auth_svc = AuthService(db=None)

        # Generate valid token
        token = auth_svc.generate_jwt_token(user_id="user-123", email="test@example.com")

        # Tamper with token (change last character)
        tampered = token[:-1] + ("X" if token[-1] != "X" else "Y")

        # Try to decode tampered token
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(
                tampered,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )


class TestMFAOperations:
    """Multi-Factor Authentication operations."""

    @pytest.mark.regression
    def test_mfa_otp_generation_produces_valid_code(self):
        """Verify OTP generation produces numeric string."""
        from app.domains.auth.service import MFAService

        mfa_svc = MFAService(db=None)

        # Generate OTP
        otp = mfa_svc.generate_otp()

        assert isinstance(otp, str), "OTP should be string"
        assert len(otp) == 6, "OTP should be 6 digits"
        assert otp.isdigit(), "OTP should contain only digits"

    @pytest.mark.regression
    def test_mfa_otp_verification_correct_code(self):
        """Verify correct OTP validates successfully."""
        from app.domains.auth.service import MFAService

        mfa_svc = MFAService(db=None)

        # Generate and verify same OTP
        otp = "123456"
        is_valid = mfa_svc.verify_otp("user-123", otp, otp)

        assert is_valid is True, "Correct OTP should validate"

    @pytest.mark.regression
    def test_mfa_otp_verification_incorrect_code(self):
        """Verify incorrect OTP fails validation."""
        from app.domains.auth.service import MFAService

        mfa_svc = MFAService(db=None)

        # Verify different OTP
        is_valid = mfa_svc.verify_otp("user-123", "123456", "654321")

        assert is_valid is False, "Incorrect OTP should not validate"

    @pytest.mark.regression
    def test_session_revocation_invalidates_tokens(self):
        """Verify session revocation clears tokens."""
        from app.domains.auth.service import AuthService

        auth_svc = AuthService(db=None)
        user_id = "user-123"

        # Revoke session
        auth_svc.revoke_session(user_id)

        # Verify token validation would fail
        # (in practice, checks Redis for revoked token list)
        is_revoked = auth_svc.is_session_revoked(user_id)

        assert is_revoked is True, "Session should be marked as revoked"


@pytest.mark.regression
class TestRolePermissions:
    """Role-based permission enforcement."""

    def test_role_grant_permission(self):
        """Verify granting permission to role succeeds."""
        from app.domains.auth.service import RBACService

        rbac = RBACService(db=None)
        role = "tester"
        permission = "create_test_case"

        # Grant permission
        result = rbac.grant_permission(role, permission)

        assert result is True, "Permission grant should succeed"

    def test_role_deny_permission(self):
        """Verify denying permission to role succeeds."""
        from app.domains.auth.service import RBACService

        rbac = RBACService(db=None)
        role = "viewer"
        permission = "delete_project"

        # Deny permission
        result = rbac.deny_permission(role, permission)

        assert result is True, "Permission deny should succeed"

    def test_permission_inheritance_hierarchy(self):
        """Verify child role inherits parent permissions."""
        from app.domains.auth.service import RBACService

        rbac = RBACService(db=None)

        # Grant permission to parent role
        rbac.grant_permission("admin", "view_reports")

        # Verify child role inherits
        has_permission = rbac.has_permission("super_admin", "view_reports")

        assert has_permission is True, "Child role should inherit parent permissions"

    def test_admin_override_restrictions(self):
        """Verify admin can override role restrictions."""
        from app.domains.auth.service import RBACService

        rbac = RBACService(db=None)

        # Try to perform restricted action with admin override
        can_execute = rbac.can_execute(
            user_id="admin-123",
            action="delete_all_projects",
            override=True
        )

        assert can_execute is True, "Admin override should allow action"

    def test_organization_boundary_enforcement(self):
        """Verify org boundary prevents cross-org access."""
        from app.domains.auth.service import RBACService

        rbac = RBACService(db=None)
        user_org = "org-123"
        other_org = "org-456"

        # Try to access resource from other org
        can_access = rbac.can_access_resource(
            user_id="user-123",
            user_org=user_org,
            resource_org=other_org
        )

        assert can_access is False, "User should not access other org resources"
