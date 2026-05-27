# ADR 0009 — Cookie Consent & GDPR/KVKK Compliance

**Status:** Accepted  
**Date:** 2026-05-24  
**Deciders:** Platform Team

---

## Context

Cortex AI is deployed to Turkish enterprise customers (subject to **KVKK** — Turkish Personal Data Protection Law) and has EU users (subject to **GDPR**). Both regulations require:

1. Informed consent before non-essential cookies are set.
2. Granular opt-in/opt-out per cookie category.
3. Easily accessible preference management (re-opening consent dialog).
4. Documented cookie usage policy (Privacy page).

Before this ADR, no cookie consent mechanism existed. The landing page and application set no third-party cookies, but the gap still posed a compliance risk when analytics or marketing integrations are added.

---

## Decision

### Client-side consent banner (`CookieConsentBanner`)

Implemented as a zero-dependency React client component at `apps/web/components/CookieConsentBanner.tsx`:

- Renders a bottom-fixed banner on first visit (no stored consent).
- Three categories: **necessary** (always on), **analytics** (default off), **marketing** (default off).
- "Accept All", "Necessary Only", and "Details" (granular toggle panel) buttons.
- Choice stored in `localStorage` under `cortex_cookie_consent` with a version key. Version bump forces re-prompt when categories change.
- After save, fires `window.dispatchEvent(new CustomEvent("cortexConsent", { detail }))` so external scripts (GTM, GA, Hotjar, etc.) can react without polling storage.
- Exports `useConsentStatus()` hook for conditional analytics loading elsewhere in the app.

### Why localStorage (not a cookie)?

Storing consent in localStorage avoids the irony of setting a cookie before consent is given. The GDPR Article 25 "privacy by default" principle supports this approach.

### Why not a third-party Consent Management Platform (CMP)?

| Option | Pros | Cons |
|---|---|---|
| Third-party CMP (Cookiebot, OneTrust) | Pre-certified, vendor-maintained | Expensive, adds external JS, vendor lock-in |
| **Custom component (chosen)** | Zero cost, no external dependencies, full control | Team maintains it; must audit on regulatory updates |

For current scale (single tenant enterprise, minimal third-party integrations), the custom approach is proportionate. When/if Google Consent Mode v2 certification is required, migrate to a CMP.

---

## Consequences

### Positive
- GDPR/KVKK consent requirement satisfied for current cookie posture.
- No external CMP dependency or cost.
- `useConsentStatus()` hook provides a clean API for conditional analytics.

### Negative / Follow-ups
- Must audit consent categories whenever a new third-party integration is added.
- Version number (`CONSENT_VERSION`) must be bumped on any category change.
- A server-side consent log (audit table) is **not** implemented yet — required for GDPR Art. 7 proof-of-consent. Add when legal requires it.
- IAB TCF 2.2 compatibility not implemented — add if advertising integrations are needed.

---

## References
- GDPR Art. 6, 7, 25 — lawful basis, consent requirements, privacy by default
- KVKK Madde 5 — kişisel veri işleme şartları
- ePrivacy Directive — cookie rules
- Google Consent Mode v2 — future consideration
