# ADR 0002: httpOnly Cookie Authentication

**Status**: Accepted
**Date**: 2026-05-14
**Severity**: 🔴 Security Critical

## Context

JWT access + refresh tokens were stored in `localStorage`. Any XSS would allow token theft.

```ts
// VULNERABLE — XSS could steal this
localStorage.setItem('tspm_access_token', jwt);
```

## Decision

Move all auth tokens to **httpOnly + Secure + SameSite=lax** cookies. JavaScript cannot read or modify them.

### Backend (FastAPI)
- `/auth/login` — `Set-Cookie: bgts_access_token=...; HttpOnly; Max-Age=1800`
- `/auth/refresh` — rotate cookie
- `/auth/logout` — clear cookie
- `get_current_user` — reads cookie OR `Authorization: Bearer` (back-compat)

### Frontend (Next.js)
- `setTokens()` no-op for localStorage (when `COOKIE_AUTH_ENABLED = true`)
- All `fetch()` use `credentials: 'include'`
- `migrateToCookieAuth()` clears any existing localStorage tokens on next login

## Alternatives Considered

- **In-memory only (Vercel pattern)** — Lost on tab close, poor UX.
- **Sessionless JWT** — Same XSS issue.
- **Service worker token broker** — Complex, edge cases.

## Consequences

✅ XSS cannot steal tokens
✅ CSRF mitigated by SameSite=lax
✅ Refresh token rotation in cookie (httpOnly)
⚠️ CORS: must use `credentials: 'include'` everywhere
⚠️ Cross-origin login (different domain) needs CORS config

## Verification

```js
localStorage.getItem('tspm_access_token')
// → null
fetch('/api/v1/auth/me', { credentials: 'include' })
// → 200 OK (cookie auth)
```
