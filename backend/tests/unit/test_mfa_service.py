"""Unit tests for auth.mfa_service — TOTP and backup code logic.

No external dependencies required; all stdlib + bcrypt.
"""
from __future__ import annotations

import time

import pytest


# ── TOTP core ─────────────────────────────────────────────────────────────────


class TestTotpCore:
    def test_generate_secret_is_base32(self) -> None:
        from app.domains.auth.mfa_service import generate_totp_secret
        import base64

        secret = generate_totp_secret()
        assert isinstance(secret, str)
        # Must be valid Base32 (with padding restored)
        padding = (8 - len(secret) % 8) % 8
        base64.b32decode(secret + "=" * padding, casefold=True)

    def test_generate_secret_unique(self) -> None:
        from app.domains.auth.mfa_service import generate_totp_secret

        secrets = {generate_totp_secret() for _ in range(20)}
        assert len(secrets) == 20  # all unique

    def test_generate_totp_is_six_digits(self) -> None:
        from app.domains.auth.mfa_service import generate_totp_secret, generate_totp

        secret = generate_totp_secret()
        code = generate_totp(secret)
        assert len(code) == 6
        assert code.isdigit()

    def test_verify_totp_accepts_current_code(self) -> None:
        from app.domains.auth.mfa_service import generate_totp_secret, generate_totp, verify_totp

        secret = generate_totp_secret()
        ts = time.time()
        code = generate_totp(secret, ts=ts)
        assert verify_totp(secret, code, ts=ts) is True

    def test_verify_totp_rejects_wrong_code(self) -> None:
        from app.domains.auth.mfa_service import generate_totp_secret, verify_totp

        secret = generate_totp_secret()
        assert verify_totp(secret, "000000", ts=1_000_000_000) is False

    def test_verify_totp_accepts_adjacent_window(self) -> None:
        """Code from 1 step ago should still be accepted (clock drift tolerance)."""
        from app.domains.auth.mfa_service import generate_totp_secret, generate_totp, verify_totp

        secret = generate_totp_secret()
        ts = time.time()
        past_code = generate_totp(secret, ts=ts - 30)  # previous 30-second window
        assert verify_totp(secret, past_code, ts=ts) is True

    def test_verify_totp_rejects_non_numeric(self) -> None:
        from app.domains.auth.mfa_service import generate_totp_secret, verify_totp

        secret = generate_totp_secret()
        assert verify_totp(secret, "abcdef") is False
        assert verify_totp(secret, "") is False
        assert verify_totp(secret, None) is False  # type: ignore[arg-type]

    def test_verify_totp_rejects_old_window(self) -> None:
        """Code from 2+ steps ago must be rejected."""
        from app.domains.auth.mfa_service import generate_totp_secret, generate_totp, verify_totp

        secret = generate_totp_secret()
        ts = time.time()
        old_code = generate_totp(secret, ts=ts - 90)  # 3 windows ago
        assert verify_totp(secret, old_code, ts=ts) is False


# ── Backup codes ──────────────────────────────────────────────────────────────


class TestBackupCodes:
    def test_generate_returns_eight_codes(self) -> None:
        from app.domains.auth.mfa_service import generate_backup_codes

        codes = generate_backup_codes()
        assert len(codes) == 8

    def test_codes_are_eight_chars_uppercase(self) -> None:
        from app.domains.auth.mfa_service import generate_backup_codes

        for code in generate_backup_codes():
            assert len(code) == 8
            assert code.isupper() or code.isdigit() or (
                all(c.isalnum() for c in code)
            )

    def test_codes_unique(self) -> None:
        from app.domains.auth.mfa_service import generate_backup_codes

        codes = generate_backup_codes()
        assert len(set(codes)) == 8

    def test_verify_backup_code_matches(self) -> None:
        from app.domains.auth.mfa_service import (
            generate_backup_codes, hash_backup_codes, verify_backup_code,
        )

        codes = generate_backup_codes()
        stored = hash_backup_codes(codes)
        matched, updated = verify_backup_code(stored, codes[0])
        assert matched is True
        # Used code should be removed
        import json
        remaining = json.loads(updated)
        assert len(remaining) == 7

    def test_verify_backup_code_wrong_code(self) -> None:
        from app.domains.auth.mfa_service import (
            generate_backup_codes, hash_backup_codes, verify_backup_code,
        )

        codes = generate_backup_codes()
        stored = hash_backup_codes(codes)
        matched, updated = verify_backup_code(stored, "NOTACODE")
        assert matched is False
        assert updated == stored  # unchanged

    def test_verify_backup_code_single_use(self) -> None:
        """Using a code twice should fail the second time."""
        from app.domains.auth.mfa_service import (
            generate_backup_codes, hash_backup_codes, verify_backup_code,
        )

        codes = generate_backup_codes()
        stored = hash_backup_codes(codes)
        _, updated = verify_backup_code(stored, codes[0])
        matched2, _ = verify_backup_code(updated, codes[0])  # try again with removed code
        assert matched2 is False

    def test_verify_backup_code_invalid_json(self) -> None:
        from app.domains.auth.mfa_service import verify_backup_code

        matched, unchanged = verify_backup_code("not-json", "ANYCODE")
        assert matched is False


# ── Provisioning URI ──────────────────────────────────────────────────────────


class TestProvisioningUri:
    def test_uri_starts_with_otpauth(self) -> None:
        from app.domains.auth.mfa_service import generate_totp_secret, totp_provisioning_uri

        secret = generate_totp_secret()
        uri = totp_provisioning_uri(secret, "user@example.com")
        assert uri.startswith("otpauth://totp/")

    def test_uri_contains_secret(self) -> None:
        from app.domains.auth.mfa_service import generate_totp_secret, totp_provisioning_uri

        secret = generate_totp_secret()
        uri = totp_provisioning_uri(secret, "user@example.com")
        assert secret in uri

    def test_uri_contains_account(self) -> None:
        from app.domains.auth.mfa_service import generate_totp_secret, totp_provisioning_uri

        secret = generate_totp_secret()
        uri = totp_provisioning_uri(secret, "alice@example.com")
        assert "alice" in uri

    def test_uri_contains_issuer(self) -> None:
        from app.domains.auth.mfa_service import generate_totp_secret, totp_provisioning_uri

        secret = generate_totp_secret()
        uri = totp_provisioning_uri(secret, "user@example.com", issuer="MyApp")
        assert "MyApp" in uri
