"""Unit tests for multi-team foundation: mentions, crypto, i18n, presence."""

from __future__ import annotations


# ── @mention parser ──────────────────────────────────────────────
def test_extract_handles_basic():
    from app.domains.collaboration.mentions import extract_handles

    body = "Hey @alice and @bob.smith, ping @charlie-99 please."
    handles = sorted(extract_handles(body))
    assert handles == ["alice", "bob.smith", "charlie-99"]


def test_extract_handles_skips_emails():
    from app.domains.collaboration.mentions import extract_handles

    # Emails contain @ but should not be picked up as handles
    body = "Contact me at user@example.com or @validhandle"
    handles = extract_handles(body)
    assert handles == ["validhandle"]


def test_extract_handles_dedup_and_lower():
    from app.domains.collaboration.mentions import extract_handles

    body = "@Alice @alice @ALICE"
    assert extract_handles(body) == ["alice"]


def test_extract_handles_empty_or_short():
    from app.domains.collaboration.mentions import extract_handles

    assert extract_handles("") == []
    assert extract_handles("@x") == []  # < 2 chars


# ── i18n helper ──────────────────────────────────────────────────
def test_i18n_translate_default_locale():
    from app.core.i18n import t

    assert t("auth.invalid_credentials", locale="tr") == "E-posta veya sifre hatali"
    assert t("auth.invalid_credentials", locale="en") == "Invalid email or password"


def test_i18n_fallback_to_default():
    from app.core.i18n import t

    # Key only exists in some locales? Use a real key and unknown locale.
    msg = t("auth.invalid_credentials", locale="fr")  # fr not supported -> fallback tr
    assert "sifre" in msg.lower() or "password" in msg.lower()


def test_i18n_unknown_key_returns_key():
    from app.core.i18n import t

    assert t("does.not.exist", locale="en") == "does.not.exist"


def test_i18n_format_args():
    from app.core.i18n import t

    out = t("auth.no_permission", locale="en", perm="project.create")
    assert "project.create" in out


def test_i18n_parse_accept_language():
    from app.core.i18n import parse_accept_language

    assert parse_accept_language("tr-TR,tr;q=0.9,en;q=0.8") == "tr"
    assert parse_accept_language("en-US,en;q=0.9") == "en"
    assert parse_accept_language("") == "tr"  # default
    assert parse_accept_language("fr,de") == "tr"  # nothing supported -> default


# ── Crypto (Fernet) ──────────────────────────────────────────────
def test_crypto_roundtrip():
    from app.infra.crypto import encrypt_secret, decrypt_secret

    plaintext = "sk_live_super_secret_api_key_12345"
    ct = encrypt_secret(plaintext)
    assert ct != plaintext
    assert decrypt_secret(ct) == plaintext


def test_crypto_handles_none():
    from app.infra.crypto import encrypt_secret, decrypt_secret

    assert encrypt_secret(None) is None  # type: ignore[arg-type]
    assert decrypt_secret(None) is None  # type: ignore[arg-type]


def test_crypto_different_outputs_each_call():
    """Fernet token has random IV; same input -> different ciphertext."""
    from app.infra.crypto import encrypt_secret, decrypt_secret

    ct1 = encrypt_secret("hello")
    ct2 = encrypt_secret("hello")
    assert ct1 != ct2
    assert decrypt_secret(ct1) == decrypt_secret(ct2) == "hello"


# ── Invitation token helper ──────────────────────────────────────
def test_invite_token_hash_deterministic():
    from app.domains.organizations.service import _hash_token, issue_invite_token

    raw, h = issue_invite_token()
    assert h == _hash_token(raw)
    # Same raw -> same hash
    assert _hash_token(raw) == _hash_token(raw)
    # Different raw -> different hash
    raw2, h2 = issue_invite_token()
    assert h != h2


# ── Project-role permission map ──────────────────────────────────
def test_project_role_perms_admin_grants_all():
    from app.deps import _PROJECT_ROLE_PERMS

    assert "admin.*" in _PROJECT_ROLE_PERMS["admin"]
    # Viewer is read-only
    assert "scenario.create" not in _PROJECT_ROLE_PERMS["viewer"]
    assert "scenario.read" in _PROJECT_ROLE_PERMS["viewer"]


# ── Storage local backend ────────────────────────────────────────
def test_local_storage_roundtrip(tmp_path):
    from app.infra.storage import LocalStorage

    s = LocalStorage(str(tmp_path))
    s.put_bytes("runs/abc/output.json", b'{"k":"v"}')
    assert s.exists("runs/abc/output.json")
    assert s.get_bytes("runs/abc/output.json") == b'{"k":"v"}'
    url = s.presigned_url("runs/abc/output.json")
    assert "/artifacts/" in url
    assert s.delete("runs/abc/output.json") is True
    assert not s.exists("runs/abc/output.json")


def test_local_storage_blocks_path_traversal(tmp_path):
    import pytest
    from app.infra.storage import LocalStorage

    s = LocalStorage(str(tmp_path))
    # Path traversal attempt — must raise, never escape root
    with pytest.raises(ValueError):
        s.put_bytes("../../etc/passwd", b"x")
