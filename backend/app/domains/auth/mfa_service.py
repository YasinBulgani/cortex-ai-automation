"""TOTP-based Multi-Factor Authentication (RFC 6238).

Pure-Python implementation — no third-party OTP library required.
Uses only stdlib: hmac, hashlib, struct, os, base64, time.

Key design decisions
────────────────────
* Secret is 20 random bytes → Base32 encoded (standard TOTP secret length).
* TOTP window ±1 step (30-second windows) to tolerate clock drift.
* Backup codes: 8 × 8-character alphanumeric codes, stored as bcrypt hashes.
* Provisioning URI format follows the Key Uri Format spec so any TOTP app
  (Google Authenticator, Authy, 1Password, Bitwarden) can scan the QR code.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from typing import Optional

import bcrypt

# ── Constants ─────────────────────────────────────────────────────────────────

_TOTP_ISSUER = "Cortex AI"
_TOTP_DIGITS = 6
_TOTP_PERIOD = 30          # seconds
_TOTP_WINDOW = 1           # ±1 period tolerance
_BACKUP_CODE_COUNT = 8
_BACKUP_CODE_LEN = 8


# ── TOTP core ─────────────────────────────────────────────────────────────────


def generate_totp_secret() -> str:
    """Return a new Base32-encoded TOTP secret (compatible with TOTP apps)."""
    raw = os.urandom(20)
    # RFC 4648 Base32, uppercase, strip padding for URL friendliness
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _hotp(secret_b32: str, counter: int) -> int:
    """Compute HMAC-based OTP for the given counter value (RFC 4226)."""
    # Pad Base32 secret back to correct length before decoding
    padding = (8 - len(secret_b32) % 8) % 8
    secret_bytes = base64.b32decode(secret_b32 + "=" * padding, casefold=True)

    msg = struct.pack(">Q", counter)
    h = hmac.new(secret_bytes, msg, hashlib.sha1).digest()

    # Dynamic truncation
    offset = h[-1] & 0x0F
    code = (
        ((h[offset] & 0x7F) << 24)
        | ((h[offset + 1] & 0xFF) << 16)
        | ((h[offset + 2] & 0xFF) << 8)
        | (h[offset + 3] & 0xFF)
    )
    return code % (10 ** _TOTP_DIGITS)


def _current_counter(ts: Optional[float] = None) -> int:
    """Return the current TOTP time step counter."""
    return int((ts or time.time()) / _TOTP_PERIOD)


def generate_totp(secret_b32: str, ts: Optional[float] = None) -> str:
    """Return the current TOTP code (zero-padded to 6 digits)."""
    return str(_hotp(secret_b32, _current_counter(ts))).zfill(_TOTP_DIGITS)


def verify_totp(secret_b32: str, code: str, ts: Optional[float] = None) -> bool:
    """Verify a TOTP code, accepting ±WINDOW time steps for clock drift."""
    try:
        code_int = int(code)
    except (ValueError, TypeError):
        return False

    counter = _current_counter(ts)
    for delta in range(-_TOTP_WINDOW, _TOTP_WINDOW + 1):
        if _hotp(secret_b32, counter + delta) == code_int:
            return True
    return False


# ── Backup codes ──────────────────────────────────────────────────────────────


def generate_backup_codes() -> list[str]:
    """Generate N random alphanumeric backup codes (plain-text, shown once)."""
    charset = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no O/0/1/I ambiguity
    return [
        "".join(secrets.choice(charset) for _ in range(_BACKUP_CODE_LEN))
        for _ in range(_BACKUP_CODE_COUNT)
    ]


def hash_backup_codes(codes: list[str]) -> str:
    """Return a JSON string of bcrypt-hashed backup codes for DB storage."""
    hashed = [bcrypt.hashpw(c.upper().encode(), bcrypt.gensalt()).decode() for c in codes]
    return json.dumps(hashed)


def verify_backup_code(stored_json: str, candidate: str) -> tuple[bool, str]:
    """
    Check *candidate* against stored hashed codes.

    Returns (matched, updated_json) where updated_json has the used code
    removed (single-use). Returns (False, stored_json) on mismatch.
    """
    try:
        hashed_list: list[str] = json.loads(stored_json)
    except (json.JSONDecodeError, TypeError):
        return False, stored_json

    candidate_bytes = candidate.upper().replace("-", "").encode()
    for i, h in enumerate(hashed_list):
        try:
            if bcrypt.checkpw(candidate_bytes, h.encode()):
                remaining = hashed_list[:i] + hashed_list[i + 1:]
                return True, json.dumps(remaining)
        except Exception:
            continue
    return False, stored_json


# ── Provisioning URI ──────────────────────────────────────────────────────────


def totp_provisioning_uri(secret_b32: str, account: str, issuer: str = _TOTP_ISSUER) -> str:
    """
    Return an otpauth:// URI for QR-code generation.

    Format: otpauth://totp/{issuer}:{account}?secret={secret}&issuer={issuer}&digits=6&period=30
    """
    from urllib.parse import quote

    label = quote(f"{issuer}:{account}", safe="")
    params = (
        f"secret={secret_b32}"
        f"&issuer={quote(issuer)}"
        f"&digits={_TOTP_DIGITS}"
        f"&period={_TOTP_PERIOD}"
        f"&algorithm=SHA1"
    )
    return f"otpauth://totp/{label}?{params}"
