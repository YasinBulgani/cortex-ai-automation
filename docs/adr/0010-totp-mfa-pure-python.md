# ADR 0010 — TOTP-Based MFA: Pure-Python RFC 6238 Implementation

**Status:** Accepted  
**Date:** 2026-05-24  
**Deciders:** Platform Team

---

## Context

Multi-Factor Authentication was required to meet enterprise security requirements and KVKK/GDPR "security of processing" obligations (GDPR Art. 32). The platform needed:

1. TOTP (Time-based One-Time Password, RFC 6238) support compatible with standard authenticator apps.
2. Backup codes for account recovery when the device is unavailable.
3. Self-contained implementation without new runtime dependencies.
4. Audit trail for MFA lifecycle events (enable, disable, backup code regeneration).

---

## Decision

### Pure-Python TOTP (no third-party OTP library)

Implemented in `backend/app/domains/auth/mfa_service.py` using only Python stdlib (`hmac`, `hashlib`, `struct`, `base64`, `os`, `time`, `secrets`) plus `bcrypt` (already a dependency for password hashing).

| Approach | Pros | Cons |
|---|---|---|
| **Pure stdlib TOTP (chosen)** | No new dependency, auditable, single file | Team maintains HOTP/TOTP algorithm |
| `pyotp` library | Well-known, battle-tested | Adds dependency, less control |
| `authlib` | Full OAuth/OIDC stack | Very heavy for TOTP alone |

The RFC 6238 algorithm is ~30 lines and well-tested in the unit tests (19 tests covering edge cases). The complexity is low enough to maintain in-house.

### Secret storage

- 20 random bytes → Base32 encoded (20 bytes = 160 bits, standard TOTP secret length per RFC 4226 §4)
- Stored in `sd_users.totp_secret` (VARCHAR 64, nullable — NULL = MFA not configured)
- Secret is only stored server-side, never re-transmitted after setup

### Backup codes

- 8 codes × 8 characters (uppercase alphanumeric, no O/0/1/I ambiguity)
- Each code is bcrypt-hashed individually (no shared salt)
- Stored as JSON array of hashes in `sd_users.mfa_backup_codes` (TEXT, nullable)
- Single-use: used code is removed from the JSON array on verification

### TOTP window

±1 time step (30 seconds) to tolerate clock drift between client devices and server. This is the TOTP standard recommendation and accepted by all major authenticator apps.

### Activation flow

1. `POST /auth/mfa/setup` → generates secret + backup codes, stores pending (mfa_enabled=False)
2. `POST /auth/mfa/verify` → validates first TOTP code, sets mfa_enabled=True
3. This two-step flow prevents users from being locked out due to a misconfigured authenticator.

### Login flow (current vs future)

Current: MFA does **not** interrupt the login flow (mfa_enabled field exists but the login endpoint doesn't check it yet). This is intentional — it lets us deploy the MFA infrastructure without forcing a hard break in auth for existing users.

Future: When MFA enforcement is needed, the login endpoint should:
1. Check `user.mfa_enabled`
2. If enabled: return `{ mfa_required: true, mfa_session_token: <short-lived JWT> }`
3. Client calls `POST /auth/mfa/login` with `{ session_token, code }`
4. Server verifies code → issues full access token

The `LoginResponse` schema already supports this with `mfa_required` + `mfa_session_token` fields.

---

## Consequences

### Positive
- No new runtime dependency.
- 19 unit tests cover TOTP generation, verification (window, drift), backup code single-use, and provisioning URI format.
- Audit events logged for all MFA lifecycle actions.
- Backup codes survive device loss.

### Negative / Follow-ups
- **Login enforcement not yet wired** — the login endpoint currently ignores `mfa_enabled`. Must add the step-up auth flow before mandating MFA.
- **No SMS/email OTP** — only TOTP authenticator apps supported. If required, add a separate channel adapter.
- **No FIDO2/WebAuthn** — hardware security keys (YubiKey) not supported. Add when enterprise customers request it.
- **No "remember this device"** — every login with MFA requires a code. Consider adding a trusted-device cookie with a long TTL if UX feedback demands it.

---

## References
- RFC 6238 — TOTP: Time-Based One-Time Password Algorithm
- RFC 4226 — HOTP: An HMAC-Based One-Time Password Algorithm
- NIST SP 800-63B §5.1.3 — Time-Based One-Time Passwords
- Key Uri Format — https://github.com/google/google-authenticator/wiki/Key-Uri-Format
