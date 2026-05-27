"""Unit tests for Jenkins service token encryption.

Tests the pure-crypto parts of app/domains/cicd/jenkins_service.py
(encrypt_token / decrypt_token) without needing a DB connection.
"""

from __future__ import annotations

import pytest


class TestJenkinsTokenCrypto:
    def test_encrypt_decrypt_roundtrip(self) -> None:
        from app.domains.cicd.jenkins_service import decrypt_token, encrypt_token

        plain = "my-secret-api-token"
        cipher = encrypt_token(plain)
        assert decrypt_token(cipher) == plain

    def test_cipher_is_not_plaintext(self) -> None:
        from app.domains.cicd.jenkins_service import encrypt_token

        plain = "super-secret-token"
        cipher = encrypt_token(plain)
        assert plain not in cipher

    def test_empty_string_roundtrip(self) -> None:
        from app.domains.cicd.jenkins_service import decrypt_token, encrypt_token

        assert decrypt_token(encrypt_token("")) == ""

    def test_unicode_token_roundtrip(self) -> None:
        from app.domains.cicd.jenkins_service import decrypt_token, encrypt_token

        plain = "şifreli-token-🔐"
        assert decrypt_token(encrypt_token(plain)) == plain

    def test_two_encryptions_produce_different_cipher(self) -> None:
        """Fernet adds random IV — same plaintext → different ciphertext each time."""
        from app.domains.cicd.jenkins_service import encrypt_token

        plain = "same-token"
        c1 = encrypt_token(plain)
        c2 = encrypt_token(plain)
        assert c1 != c2  # randomised IV

    def test_wrong_cipher_raises_value_error(self) -> None:
        from app.domains.cicd.jenkins_service import decrypt_token

        with pytest.raises(ValueError, match="çözülemedi"):
            decrypt_token("not-a-valid-fernet-token")

    def test_custom_encryption_key_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """If JENKINS_ENCRYPTION_KEY is set, it should be used."""
        from cryptography.fernet import Fernet
        from app.domains.cicd.jenkins_service import encrypt_token, decrypt_token

        # Generate a valid key
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("JENKINS_ENCRYPTION_KEY", key)

        plain = "token-with-custom-key"
        cipher = encrypt_token(plain)
        assert decrypt_token(cipher) == plain
