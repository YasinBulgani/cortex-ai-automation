"""
Integration tests for authentication API endpoints.

Category: API Integration Tests - Authentication
Tests: 8 total
Markers: @pytest.mark.regression, @pytest.mark.integration, @pytest.mark.service
Endpoints:
  - POST /api/v1/auth/login
  - POST /api/v1/auth/logout
  - POST /api/v1/auth/refresh
  - POST /api/v1/auth/mfa/enable
  - POST /api/v1/auth/mfa/verify
  - POST /api/v1/auth/password-reset
  - GET /api/v1/auth/me
"""

import pytest
from fastapi.testclient import TestClient
import json


@pytest.mark.regression
@pytest.mark.integration
class TestAuthLoginEndpoint:
    """Authentication login endpoint tests."""

    def test_login_valid_credentials(self, client: TestClient, db_ready):
        """POST /api/v1/auth/login with valid credentials.

        Traceability: TC-AUTH-001, REQ-AUTH-001
        Given: User with email admin@example.com and password admin123
        When: POST /api/v1/auth/login with correct email/password
        Then: Returns 200 with access_token and user data
        """
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "admin123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data, "Response should contain access_token"
        assert "user" in data, "Response should contain user object"
        assert data["user"]["email"] == "admin@example.com"
        assert "refresh_token" in data, "Response should contain refresh_token"

    def test_login_invalid_password(self, client: TestClient, db_ready):
        """POST /api/v1/auth/login with incorrect password.

        Traceability: TC-AUTH-002
        Given: User with known email but wrong password
        When: POST /api/v1/auth/login
        Then: Returns 401 Unauthorized
        """
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401
        assert "detail" in response.json()
        assert "invalid" in response.json()["detail"].lower()

    def test_login_nonexistent_email(self, client: TestClient, db_ready):
        """POST /api/v1/auth/login with unknown email.

        Traceability: TC-AUTH-003
        Given: Email that does not exist in system
        When: POST /api/v1/auth/login
        Then: Returns 401 Unauthorized
        """
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "unknown@nonexistent.com",
                "password": "password123"
            }
        )

        assert response.status_code == 401

    def test_login_missing_email(self, client: TestClient):
        """POST /api/v1/auth/login with missing email field.

        Traceability: TC-AUTH-004
        When: POST /api/v1/auth/login without email
        Then: Returns 422 Unprocessable Entity
        """
        response = client.post(
            "/api/v1/auth/login",
            json={"password": "password123"}
        )

        assert response.status_code == 422

    def test_login_missing_password(self, client: TestClient):
        """POST /api/v1/auth/login with missing password field.

        Traceability: TC-AUTH-005
        When: POST /api/v1/auth/login without password
        Then: Returns 422 Unprocessable Entity
        """
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com"}
        )

        assert response.status_code == 422


@pytest.mark.regression
@pytest.mark.integration
class TestAuthRefreshToken:
    """Token refresh endpoint tests."""

    def test_refresh_token_valid(self, client: TestClient, db_ready):
        """POST /api/v1/auth/refresh with valid refresh token.

        Traceability: TC-AUTH-006
        Given: Valid refresh token from login
        When: POST /api/v1/auth/refresh with refresh_token
        Then: Returns 200 with new access_token
        """
        # First login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin123"}
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["access_token"] != login_response.json()["access_token"]

    def test_refresh_token_invalid(self, client: TestClient):
        """POST /api/v1/auth/refresh with invalid token.

        Traceability: TC-AUTH-007
        When: POST /api/v1/auth/refresh with invalid refresh_token
        Then: Returns 401 Unauthorized
        """
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == 401


@pytest.mark.regression
@pytest.mark.integration
class TestAuthLogout:
    """Logout and session revocation tests."""

    def test_logout_invalidates_session(self, client: TestClient, auth_headers):
        """POST /api/v1/auth/logout clears session.

        Traceability: TC-AUTH-008
        Given: Authenticated user with valid token
        When: POST /api/v1/auth/logout
        Then: Session is invalidated and token no longer works
        """
        # Verify token works before logout
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        assert response.status_code == 200

        # Logout
        logout_response = client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        assert logout_response.status_code == 200

        # Verify token no longer works
        check_response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        assert check_response.status_code == 401


@pytest.mark.regression
@pytest.mark.integration
@pytest.mark.slow
class TestMFAOperations:
    """Multi-Factor Authentication endpoint tests."""

    def test_mfa_enable_send_otp(self, client: TestClient, auth_headers):
        """POST /api/v1/auth/mfa/enable sends OTP.

        Traceability: TC-AUTH-009
        Given: Authenticated user without MFA enabled
        When: POST /api/v1/auth/mfa/enable with method=email
        Then: Returns 200 and OTP sent to email
        """
        response = client.post(
            "/api/v1/auth/mfa/enable",
            headers=auth_headers,
            json={"method": "email"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("otp_sent") is True
        assert "challenge_id" in data

    def test_mfa_verify_otp_correct_code(self, client: TestClient, auth_headers, mocker):
        """POST /api/v1/auth/mfa/verify with correct OTP.

        Traceability: TC-AUTH-010
        Given: User with OTP challenge pending
        When: POST /api/v1/auth/mfa/verify with correct code
        Then: Returns 200 and MFA enabled
        """
        # Mock OTP verification
        mocker.patch(
            "app.domains.auth.service.MFAService.verify_otp",
            return_value=True
        )

        response = client.post(
            "/api/v1/auth/mfa/verify",
            headers=auth_headers,
            json={"code": "123456", "challenge_id": "challenge-123"}
        )

        assert response.status_code == 200

    def test_mfa_verify_otp_incorrect_code(self, client: TestClient, auth_headers, mocker):
        """POST /api/v1/auth/mfa/verify with incorrect OTP.

        Traceability: TC-AUTH-011
        When: POST /api/v1/auth/mfa/verify with wrong code
        Then: Returns 401 Unauthorized
        """
        # Mock OTP verification failure
        mocker.patch(
            "app.domains.auth.service.MFAService.verify_otp",
            return_value=False
        )

        response = client.post(
            "/api/v1/auth/mfa/verify",
            headers=auth_headers,
            json={"code": "000000", "challenge_id": "challenge-123"}
        )

        assert response.status_code == 401


@pytest.mark.regression
@pytest.mark.integration
class TestPasswordReset:
    """Password reset endpoint tests."""

    def test_password_reset_request(self, client: TestClient, db_ready, mocker):
        """POST /api/v1/auth/password-reset sends email.

        Traceability: TC-AUTH-012
        Given: User with known email
        When: POST /api/v1/auth/password-reset with email
        Then: Returns 200 and password reset email sent
        """
        # Mock email service
        mocker.patch("app.domains.notifications.email.send_email", return_value=True)

        response = client.post(
            "/api/v1/auth/password-reset",
            json={"email": "admin@example.com"}
        )

        assert response.status_code == 200
        assert response.json().get("message") is not None

    def test_password_reset_nonexistent_email(self, client: TestClient):
        """POST /api/v1/auth/password-reset with unknown email.

        Traceability: TC-AUTH-013
        Given: Email that does not exist
        When: POST /api/v1/auth/password-reset
        Then: Returns 200 (for security, doesn't reveal user existence)
        """
        response = client.post(
            "/api/v1/auth/password-reset",
            json={"email": "nonexistent@example.com"}
        )

        # Security: always return 200 to not leak user existence
        assert response.status_code == 200


@pytest.mark.regression
@pytest.mark.integration
class TestGetCurrentUser:
    """Get current user endpoint tests."""

    def test_get_current_user_authenticated(self, client: TestClient, auth_headers):
        """GET /api/v1/auth/me returns current user.

        Traceability: TC-AUTH-014
        Given: Authenticated user with valid token
        When: GET /api/v1/auth/me
        Then: Returns 200 with user data
        """
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "full_name" in data

    def test_get_current_user_unauthenticated(self, client: TestClient):
        """GET /api/v1/auth/me without authentication.

        Traceability: TC-AUTH-015
        When: GET /api/v1/auth/me without Authorization header
        Then: Returns 401 Unauthorized
        """
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client: TestClient):
        """GET /api/v1/auth/me with invalid token.

        Traceability: TC-AUTH-016
        When: GET /api/v1/auth/me with malformed Authorization header
        Then: Returns 401 Unauthorized
        """
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401
