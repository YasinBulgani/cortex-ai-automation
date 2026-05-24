# ADR 0008 — Lightweight i18n via Translation Context

**Date:** 2026-05-24
**Status:** Accepted
**Deciders:** Engineering (autonomous loop iteration)

---

## Context

The Cortex AI Automation frontend is currently written entirely in Turkish
(hard-coded strings).  The product roadmap includes English localisation for
international users.  We need a translation layer that:

1. Works with Next.js 14 App Router (no pages-router assumptions).
2. Does not require locale-prefix routing (e.g., `/en/dashboard`) — users
   switch language via a preference toggle, not the URL.
3. Has zero new npm dependencies.
4. Is incrementally adoptable — pages can migrate to `useT()` one at a time.
5. Preserves TypeScript safety — key typos are caught at compile time.

---

## Decision

Implement a **translation context + `useT()` hook** in
`apps/web/lib/i18n/index.ts`:

```
lib/i18n/
  index.ts          ← I18nProvider, useT(), useI18n()
  locales/
    tr.ts           ← Turkish (default, source of truth)
    en.ts           ← English (must match shape of tr.ts)
```

### Key design choices

**TypeScript dot-path key type**
```ts
type TranslationKey = DotPath<TranslationDictionary>;
// e.g. "common.save" | "management.status.passed" | …
```
Any typo in a key is a compile-time error.  The English locale is typed as
`TranslationDictionary` so missing keys are caught immediately.

**No URL locale prefix**
Language preference is stored in `localStorage` under `cortex_lang` and
detected from `navigator.language` as fallback.  The `html[lang]` attribute is
updated dynamically for accessibility/SEO crawlers.

**`I18nProvider` wraps `QueryProvider` in root layout**
All client components can call `useT()` or `useI18n()` anywhere in the tree.

**Variable interpolation**
```ts
t("someKey", { count: 5 })  // replaces {{count}} in the string
```

**`LanguageSwitcher` component**
A compact toggle placed in `ManagementShell` header (and usable anywhere in
the app shell) — shows the current locale flag + code; click switches to the
other locale.

---

## Migration path

1. **Phase 1 (done):** Infrastructure only — no existing strings migrated.
   The app works unchanged in Turkish; all new strings should use `useT()`.

2. **Phase 2:** Migrate Management pages string-by-string; high-value user-
   facing labels first.

3. **Phase 3:** Migrate remaining pages.  A linting rule can enforce that
   hard-coded Turkish string literals are replaced.

---

## Consequences

**Positive:**
- Zero runtime cost from an extra npm package.
- Strongly typed keys — refactoring is safe.
- No routing change required.
- Incrementally adoptable — zero big-bang migration.

**Negative / Trade-offs:**
- Does not support SSR-rendered translated strings (server components cannot
  call `useT()`).  For SSR pages, we can extend with a `getServerT(locale)` in
  a future iteration.
- Dictionary is bundled in the JS bundle for both locales.  At current size
  (~5 KB minified) this is negligible; lazy-loading is straightforward if needed.

---

## Alternatives Considered

| Alternative | Rejected because |
|---|---|
| `next-intl` | Requires locale-prefix routing or complex middleware patches; adds ~40 KB dependency |
| `react-i18next` | Heavier; loads async JSON; no compile-time key safety without extra codegen |
| Hard-coded strings | Cannot support English without a full rewrite |
