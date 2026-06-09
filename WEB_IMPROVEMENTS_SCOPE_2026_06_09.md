# Neurex Web Improvements — Comprehensive Scope & Timeline
**Document:** WEB_IMPROVEMENTS_SCOPE_2026_06_09.md  
**Date:** 2026-06-09  
**Status:** Planning  
**Project:** Cortex AI Automation (Neurex QA)  
**Tech Stack:** Next.js 14 + React 18 + TailwindCSS + TypeScript 6.0  
**Current LOC:** ~285K (TS/TSX)  
**Current State:** Feature-complete (core QA platform), PWA partially implemented (manifest + SW exist)

---

## Executive Summary

| Feature | Complexity | Story Points | FTE | Timeline | Blocked By |
|---------|-----------|--------------|-----|----------|-----------|
| **1. PWA Support** | High | 21 | 2 | 3–4 weeks | None |
| **2. Mobile Optimization** | High | 18 | 2 | 2–3 weeks | PWA Faze (optional) |
| **3. Performance Tuning** | Medium | 13 | 1 | 2 weeks | None (parallel) |
| **4. Advanced Features** | Very High | 34 | 3 | 4–6 weeks | Perf baseline (soft) |
| **5. Accessibility (WCAG AAA)** | High | 15 | 2 | 2–3 weeks | None (parallel) |
| **TOTAL** | — | **101 SP** | **5–6 FTE** | **8–12 weeks** | — |

---

## Feature 1: PWA Support (Progressive Web App)

### 🎯 Scope

Current State:
- ✅ Manifest file exists (`/public/manifest.json`)
- ✅ Service Worker template in place (`/public/sw.js`) — network-first HTML + cache-first static
- ✅ Basic install prompt capability
- ❌ Background Sync not implemented
- ❌ Push notifications incomplete (FCM/APNs not wired to frontend)
- ❌ Offline page minimal (`/app/offline/page.tsx`)
- ❌ Sync queue UI / monitoring absent
- ❌ IndexedDB persistence for larger datasets

Deliverables:
1. **Service Worker Enhancement**
   - Implement cache versioning strategy (semantic, tied to app release)
   - Background sync registration for offline mutations
   - Stale-while-revalidate for read-heavy routes
   - Error boundary + offline fallback pages for all critical routes
   - Service worker lifecycle (skip waiting, claim clients)
   - Tests for cache hit/miss + network scenarios

2. **Install Prompt & App Shell**
   - Detect installability (`beforeinstallprompt` event)
   - Custom install CTA (banner or modal)
   - iOS home screen instructions (fallback for mobile Safari)
   - Splash screen with loading animation
   - App shell architecture (layout caching)

3. **Background Sync & Queue**
   - IndexedDB schema for offline mutations (test runs, defect comments, settings)
   - Sync queue manager (retry logic, exponential backoff)
   - Background Sync API with tag-based routing
   - UI: Sync status indicator + manual trigger option
   - Conflict resolution (merge vs. discard strategies)
   - Test data persistence across offline sessions

4. **Push Notifications (Frontend)**
   - Service Worker push event handler
   - Badge + notification grouping (NotificationBadge API)
   - Deep-link routing on notification click
   - Permission request + storage (localStorage or cookie)
   - Notification data shape alignment with backend
   - E2E test: send push via browser, verify click-through

5. **Progressive Enhancement**
   - Fallback for browsers without SW support
   - No-JS experiences for critical paths (login, offline status)
   - Detection: `navigator.serviceWorker`, `'serviceWorker' in navigator`
   - Graceful degradation (toast warnings when SW unavailable)

### Acceptance Criteria

- [ ] Service Worker passes cache strategies test (network-first HTML, cache-first assets)
- [ ] App installable on Chrome/Edge/Samsung Internet (Android); home screen on iOS
- [ ] Offline mode: navigate to cached pages, see sync queue UI
- [ ] Background sync: queued mutations resync when online (verified in DevTools → Application → Background Sync)
- [ ] Push notifications: sent from backend via `/api/v1/notify/push`, received in foreground/background
- [ ] Lighthouse PWA score ≥ 90 (installable, offline functional, 2+ URLs cached)
- [ ] Offline page accessible at `/offline` with clear status + retry CTA
- [ ] All 4 main routes cached at install: `/`, `/portfolio`, `/ide`, `/login`
- [ ] Manifest updated: start_url, display, theme_color, shortcuts
- [ ] Tests: Service Worker cache layers + background sync + notification click

### Story Points & Breakdown

| Task | SP | Assignee | Timeline |
|------|----|---------|---------:|
| Service Worker (cache, sync, lifecycle) | 5 | Dev 1 | W1 |
| Install prompt + splash screen + icons | 4 | Dev 1 | W1 |
| IndexedDB + sync queue manager | 5 | Dev 2 | W2 |
| Push notification handler (frontend) | 4 | Dev 2 | W2 |
| Offline UI + routing fallback | 2 | Dev 1 | W2 |
| Tests (E2E: offline nav, push, sync) | 1 | QA | W3 |
| **Subtotal** | **21** | — | **3–4 weeks** |

### Dependencies & Risks

- **Risk:** Service Worker caching conflicts with next-auth token refresh → Mitigation: API routes excluded from cache
- **Risk:** Background Sync on iOS limited → Fallback to manual sync button
- **Risk:** IndexedDB quota exceeded (quota ~50–100MB) → Implement quota check, UI warning
- **Dependency:** None (can start immediately after feature freeze)

### Tech Stack
- Service Worker API (native)
- IndexedDB (native)
- Background Sync API (Chromium, fallback manual)
- Push API (Chromium, APNs for iOS via backend)
- TanStack Query for offline mutation coordination

---

## Feature 2: Mobile Optimization

### 🎯 Scope

Current State:
- ✅ Responsive grid layout (Tailwind + CSS Grid)
- ✅ Mobile fonts configured (Inter sans-serif)
- ✅ Viewport meta tag set
- ❌ Tablet edge cases (foldable, split-screen)
- ❌ Touch gestures (swipe, long-press) not implemented
- ❌ Bottom sheet navigation not implemented (mobile hamburger → full page modal)
- ❌ Mobile-first navigation tree redesigned
- ❌ 4G load performance not verified (<3s target)
- ❌ Landscape orientation handling
- ❌ Safe area insets for notch/dynamic island

Deliverables:

1. **Responsive Design Refinement**
   - Tablet layout (768px–1024px): 2-column layouts, card grids
   - Foldable support: `viewport-fit=cover`, CSS environment variables (`env(safe-area-inset-*)`)
   - Landscape: horizontal splitview, minimized sidebars
   - Touch targets: all interactive elements ≥ 44×44px (WCAG)
   - Density modes: compact (mobile), normal (tablet), spacious (desktop)
   - Media queries: 320px, 768px, 1024px, 1440px breakpoints

2. **Touch Gestures**
   - Swipe left/right: case list pagination, sidebar toggle
   - Long-press: context menu (defect actions: edit, assign, close)
   - Pinch-zoom: disabled on app shell, enabled on images/charts
   - Pull-to-refresh: case list, test run history (via `framer-motion`)
   - Tap-and-hold: tooltip preview on mobile (fallback for hover)
   - Double-tap: zoom in on complex UIs (defect timeline, test steps)

3. **Bottom Sheet & Mobile Navigation**
   - Radix bottom sheet (custom, not fully built) OR third-party `react-bottom-sheet`
   - Mobile menu: side drawer → bottom sheet (mobile) + side nav (tablet+)
   - Filter drawer: slide up from bottom on mobile
   - Sorting/grouping: bottom sheet modal
   - Swipe-down to dismiss bottom sheet
   - Keyboard handling: arrow keys in bottom sheets

4. **Mobile-First Architecture**
   - Redesign `/` (dashboard): card grid → single column on mobile
   - Redesign `/portfolio`: project list → accordion on mobile
   - Redesign `/ide`: 2-pane (editor + preview) → tabs on mobile
   - Test runs: table → card list on mobile
   - Defects: table → expandable rows on mobile
   - Use CSS grid `auto-fit` for flexible columns

5. **Performance on 4G**
   - Target: First Contentful Paint (FCP) < 2s, Largest Contentful Paint (LCP) < 3s on 4G
   - Baseline: Measure via Lighthouse with network throttling
   - Route code-splitting: lazy load dashboard sections
   - Image optimization: WebP with JPEG fallback, srcset for density
   - Font subsetting: only use 400/500/600/700 weights
   - Critical CSS inlining for above-the-fold content

6. **Orientation & Dynamic Island Support**
   - Detect device orientation changes (`orientationchange` event)
   - Persist scroll position on rotate
   - Dynamic Island: safe area padding top (iOS 15.1+)
   - Landscape mode: full-screen modals, minimized chrome
   - Notch detection: use `viewport-fit=cover` + `env(safe-area-inset-*)`

### Acceptance Criteria

- [ ] All interactive elements 44×44px minimum (verified via axe DevTools)
- [ ] Tablet (768px–1024px): 2-column layout functional, no overflow
- [ ] Foldable (surface Duo emulator): app usable in folded state
- [ ] Swipe left/right works on CaseRow component (navigate list)
- [ ] Long-press opens context menu (defect row)
- [ ] Pull-to-refresh refreshes case list (visual spinner)
- [ ] Bottom sheet: filters open/close smoothly, swipe-down dismisses
- [ ] Mobile menu: hamburger → bottom sheet (mobile), side nav (tablet+)
- [ ] 4G performance: FCP < 2s, LCP < 3s (Lighthouse throttled)
- [ ] Landscape rotation: layout reflows, scroll position restored
- [ ] Safe area insets applied (no overlap with notch/dynamic island)
- [ ] Lighthouse mobile score ≥ 90 (performance + accessibility)
- [ ] No horizontal scroll on 320px viewports
- [ ] All modals and drawers mobile-optimized

### Story Points & Breakdown

| Task | SP | Assignee | Timeline |
|------|----|---------|---------:|
| Responsive grid refinement (tablet, foldable) | 4 | Dev 1 | W1 |
| Touch gestures (swipe, long-press, pinch) | 4 | Dev 2 | W1–W2 |
| Bottom sheet component + mobile nav | 3 | Dev 1 | W2 |
| 4G performance tuning (code-split, images) | 3 | Dev 2 | W2 |
| Orientation + safe area handling | 2 | Dev 1 | W2 |
| Tests (E2E: touch, mobile layout, perf) | 2 | QA | W3 |
| **Subtotal** | **18** | — | **2–3 weeks** |

### Dependencies & Risks

- **Risk:** Complex gesture handling on iOS (Webkit restrictions) → Fallback to standard buttons
- **Risk:** Bottom sheet library incompatibility with Next.js 14 → Consider custom implementation
- **Dependency:** Performance Tuning (soft) — should establish baseline before mobile optimizations
- **Dependency:** None blocking (can start in parallel)

### Tech Stack
- TailwindCSS (responsive utilities)
- Radix UI components (or custom bottom sheet)
- `framer-motion` for gesture animations
- `react-use` for orientation detection
- E2E tests with Playwright (viewport mocking)

---

## Feature 3: Performance Tuning

### 🎯 Scope

Current State:
- ✅ Next.js 14 configured (optimizePackageImports)
- ✅ Gzip/Brotli compression enabled
- ✅ Font optimization (display: swap)
- ❌ Lighthouse audit not run (estimated baseline 85–87)
- ❌ Bundle size not analyzed (no webpack-bundle-analyzer)
- ❌ Code splitting not optimized (no route-based lazy loading)
- ❌ Image optimization incomplete (no WebP, srcset)
- ❌ Font subsetting not done (loading all weights)
- ❌ Core Web Vitals not monitored (no web-vitals package)

Deliverables:

1. **Lighthouse Audit Baseline & Targets**
   - Run Lighthouse (PageSpeed Insights) on all main routes
   - Current baseline: estimate 85 (target: 95+)
   - Metrics:
     - Performance: 90–95
     - Accessibility: 95+ (WCAG AAA prep)
     - Best Practices: 95+
     - SEO: 100 (already good)
   - Identify bottlenecks: JS bundle, images, third-party scripts

2. **Bundle Size Analysis & Reduction**
   - Add `@next/bundle-analyzer` to build
   - Analyze chunk sizes: identify large dependencies (recharts, framer-motion, etc.)
   - Strategies:
     - Tree-shake unused Lucide icons (120KB+ potential)
     - Lazy-load Recharts (only on specific dashboards)
     - Remove unused Radix UI (only load used components)
     - Review `node_modules` for duplicates (use npm ls --depth=3)
   - Target: reduce main bundle by 15–25% (120–200KB gzip)

3. **Code Splitting & Route-Based Lazy Loading**
   - Identify heavy routes: `/ide`, `/test-runs`, `/agents`
   - Lazy-load components: `dynamic(() => import('...'), { loading: <Skeleton /> })`
   - Split charts library: load Recharts only on dashboard + analytics
   - Split code editor: load Monaco-like editor only on `/ide`
   - Split Reactflow: load only on `/pipeline` visualization
   - Verify with Next.js built-in chunk analysis

4. **Image Optimization**
   - Replace `<img>` with `<Image>` from next/image (99% coverage)
   - Generate WebP variants for all images (with JPEG fallback)
   - Implement responsive srcset (1x, 2x, 3x for high-DPI)
   - Set explicit width/height (prevents layout shift, CLS optimization)
   - Lazy-load images below fold (`loading="lazy"`)
   - Compress PNG/JPEG: use tinypng or squoosh (10–20% reduction)
   - Create SVG versions for icons (already done for manifest icons)

5. **Font Optimization**
   - Audit font weights: confirm only 400/500/600/700 needed
   - Font-display strategy: currently `swap` (correct, readable immediately)
   - Load only Latin extended (no unnecessary scripts)
   - Consider system fonts for body (Inter already optimal)
   - Preload critical fonts: `<link rel="preload" as="font" href="..." />`
   - Variable fonts: evaluate Inter/JB Mono variable fonts (save ~10KB)

6. **Core Web Vitals Monitoring**
   - Add `web-vitals` package (5KB gzip)
   - Integrate with Sentry for production monitoring
   - Dashboard metric: track LCP, FID, CLS per route
   - Client-side reporting: beacon to backend
   - Frontend alert: show warning if metrics degrade
   - Baseline: LCP < 2.5s, FID < 100ms, CLS < 0.1

7. **Third-Party Script Optimization**
   - Audit Sentry payload: ensure sampling enabled
   - Defer non-critical scripts (analytics, chat widgets)
   - Use `next/script` strategy="lazyOnload" for non-essential JS
   - Review CSP: ensure only necessary external sources

### Acceptance Criteria

- [ ] Lighthouse Performance ≥ 90 on `/` (dashboard)
- [ ] Lighthouse Performance ≥ 90 on `/portfolio` (project list)
- [ ] Lighthouse Performance ≥ 85 on `/ide` (heavy route with editor)
- [ ] Lighthouse Accessibility ≥ 95 (WCAG AAA ready)
- [ ] Bundle size reduced by ≥ 15% from baseline
- [ ] Main chunk ≤ 200KB gzip (currently ~240KB estimated)
- [ ] All images use `next/image` with explicit dimensions
- [ ] LCP < 2.5s on 4G throttling (Lighthouse)
- [ ] CLS < 0.1 (no layout shifts)
- [ ] FID < 100ms (interaction to paint)
- [ ] Code splitting verified: 15+ dynamic imports active
- [ ] Fonts preloaded for above-the-fold text
- [ ] web-vitals integrated with Sentry
- [ ] No console warnings on production build

### Story Points & Breakdown

| Task | SP | Assignee | Timeline |
|------|----|---------|---------:|
| Lighthouse audit + bottleneck analysis | 2 | Dev 1 | W1 |
| Bundle analysis + tree-shaking | 2 | Dev 1 | W1 |
| Code splitting (routes + libraries) | 3 | Dev 2 | W1–W2 |
| Image optimization (all assets) | 3 | Dev 2 | W2 |
| Font optimization + preloading | 2 | Dev 1 | W2 |
| Core Web Vitals monitoring + dashboard | 1 | Dev 1 | W2 |
| **Subtotal** | **13** | — | **2 weeks** |

### Dependencies & Risks

- **Risk:** Tree-shaking Lucide icons may break dynamic icon loading → Use static imports where possible
- **Risk:** Lazy-loading Monaco on `/ide` may show load delay → Show skeleton while loading
- **Risk:** WebP not supported on old browsers → JPEG fallback via `<picture>` tag
- **Dependency:** None blocking (can start immediately)

### Tech Stack
- `@next/bundle-analyzer`
- `web-vitals`
- `next/image` (built-in)
- TinyPNG / Squoosh (compression)
- Sentry (monitoring)

---

## Feature 4: Advanced Features

### 🎯 Scope

**Very High complexity — recommend prioritization or phased delivery**

Deliverables:

1. **Real-Time Collaboration (WebSocket)**
   - User presence: who's viewing/editing (cursor, user badge)
   - Live updates: test runs, defects, comments (real-time feed)
   - Conflict-free collaborative editing: use CRDT or OT (Yjs recommended)
   - Technology: socket.io (already in backend?)
   - UI: presence avatars, activity log, live notifications
   - Testing: concurrent user actions, conflict resolution

   **Scope Issues:**
   - Requires backend WebSocket server (not in current FastAPI)
   - Requires CRDT library (~50KB gzip)
   - Complex state synchronization
   - Browser compatibility (requires polyfill for older Safari)
   - Estimated: 12 SP (4–5 weeks for 2 FTE)

2. **Advanced Filters & Saved Views**
   - UI: filter builder (status, assignee, tags, date range, custom fields)
   - Persistence: save filter sets to backend (`/api/v1/saved-filters`)
   - Quick access: filter templates (critical, assigned-to-me, this-sprint)
   - URL encoding: shareable filter links (`?filter=xyz`)
   - Bulk actions: select multiple, apply action (reassign, tag, close)
   - Estimated: 8 SP (2–3 weeks for 1 FTE)

3. **Custom Dashboard Widgets**
   - Drag-and-drop widget library: case count, coverage %, test trends
   - Widget editor: size, refresh rate, data source
   - Persistence: save widget layout to backend
   - Real-time updates: refresh widgets on data change
   - Share dashboards: snapshot + export
   - Estimated: 8 SP (2–3 weeks for 1 FTE)

4. **Export (PDF, CSV, Excel)**
   - CSV: test runs, defects, coverage reports (via TanStack React Table)
   - Excel: multi-sheet (summary, details, metadata) — `xlsx` library already added
   - PDF: styled report with charts — `pdfkit` or `react-pdf`
   - Server-side rendering: generate PDFs on backend for large datasets
   - Estimated: 6 SP (1–2 weeks for 1 FTE)

5. **Analytics Integration**
   - Metrics dashboard: test execution trends, coverage growth, defect trends
   - Reporting: date range selection, KPI cards
   - Data source: backend `/api/v1/analytics/*` endpoints
   - Charts: trend lines (Recharts already configured)
   - Estimated: 4 SP (1 week for 1 FTE)

### Acceptance Criteria

- [ ] Real-time collaboration: presence avatars visible, edits synced within 500ms
- [ ] Filter builder: 5+ filter types (status, assignee, tags, date, custom)
- [ ] Saved views: create, update, delete filters; share links
- [ ] Widgets: 8+ widget types, drag-and-drop layout, persistence
- [ ] CSV export: 50K+ rows without timeout
- [ ] Excel export: multi-sheet, formatted, < 50MB file size
- [ ] PDF export: header/footer, branded, <= 20s generation time
- [ ] Analytics dashboard: 6+ KPI cards, trend lines, date filtering
- [ ] All exports tested with real data

### Story Points & Breakdown

| Task | SP | Assignee | Timeline |
|------|----|---------|---------:|
| WebSocket infrastructure (presence) | 5 | Dev 1 | W1–W2 |
| CRDT or OT library integration | 4 | Dev 2 | W2–W3 |
| Collaborative UI (avatars, live edits) | 3 | Dev 1 | W3 |
| Advanced filters + saved views | 8 | Dev 2 | W1–W2 |
| Dashboard widgets (8+ types) | 8 | Dev 1 | W2–W4 |
| Export (CSV, Excel, PDF) | 6 | Dev 2 | W2–W3 |
| Analytics dashboard + KPIs | 4 | QA | W4 |
| **Subtotal** | **38** | — | **4–6 weeks** |

### Dependencies & Risks

- **Risk:** WebSocket requires backend server upgrade → coordinate with backend team (3–4 week effort)
- **Risk:** PDF generation slow for large reports → implement server-side rendering, queue jobs
- **Risk:** CRDT library complexity → consider simpler eventual consistency model first
- **Risk:** Analytics data freshness → implement eventual consistency cache
- **Dependency:** Backend WebSocket support (blocks real-time collaboration)
- **Recommendation:** Phase 1 (P0): Filters + Exports (4–5 weeks). Phase 2 (P1): Widgets + Analytics (4 weeks). Phase 3 (P2): Real-time collaboration (5+ weeks)

### Tech Stack
- socket.io (or native WebSocket API)
- Yjs (CRDT) or Automerge (alternative)
- TanStack React Table (advanced filtering)
- `xlsx` (Excel export)
- `pdfkit` or `react-pdf` (PDF generation)
- Recharts (analytics charts)

---

## Feature 5: Accessibility (WCAG 2.1 AAA)

### 🎯 Scope

Current State:
- ✅ Semantic HTML (mostly)
- ✅ Color contrast baseline (WCAG AA, not AAA)
- ⚠️ ARIA labels incomplete (form inputs, buttons)
- ❌ Screen reader testing not done
- ❌ Keyboard navigation incomplete (tab order, focus trapping)
- ❌ Focus indicators not visible enough
- ❌ 0 automated a11y tests

Deliverables:

1. **Comprehensive A11y Audit**
   - Run axe DevTools on all pages (35+ routes)
   - Identify: WCAG violations, best practices
   - Categories: color contrast, ARIA labels, keyboard nav, focus
   - Tools: axe, Lighthouse, WebAIM contrast checker
   - Document findings in a11y report

2. **Color Contrast Fixes**
   - WCAG AAA requires 7:1 contrast (AA: 4.5:1)
   - Audit: text colors, background colors, disabled states
   - Tools: WebAIM contrast checker, Polished library
   - Fix: adjust Tailwind color variables or component styles
   - Estimated impact: 30–50 color updates

3. **ARIA Labels & Semantic HTML**
   - Audit all form inputs: add `<label>`, `aria-label`, `aria-describedby`
   - Buttons: add `aria-pressed`, `aria-expanded` where needed
   - Landmarks: ensure `<nav>`, `<main>`, `<aside>` present
   - Live regions: add `aria-live="polite"` for toasts, notifications
   - List semantics: ensure list items use `<ul>/<li>`
   - Estimated: 80+ ARIA updates

4. **Keyboard Navigation**
   - Tab order: verify logical flow through UI (use Lighthouse keyboard nav test)
   - Focus trapping: modals, drawers, popovers should trap focus
   - Escape key: close modals, drawers, popovers
   - Arrow keys: navigate lists, tabs, comboboxes
   - Screen reader + keyboard: cross-check (NVDA, JAWS, VoiceOver)

5. **Focus Indicators**
   - Visible focus ring: min 2px, sufficient contrast (WCAG AAA: 3:1)
   - Remove `outline: none` (or replace with visible alternative)
   - Custom focus styles: use Tailwind `focus:ring-*` utilities
   - Applied to: buttons, links, inputs, tabs, menus

6. **Screen Reader Testing**
   - Tools: NVDA (Windows), JAWS (Windows), VoiceOver (Mac/iOS)
   - Test scenarios: login flow, navigate dashboard, execute test case
   - Verify: headings, landmarks, form labels, button purposes
   - Document: tested paths, verified with assistive tech

7. **Automated A11y Tests**
   - Add `@axe-core/playwright` (already in package.json)
   - E2E tests: run axe on critical pages
   - Continuous: axe audit in CI/CD pipeline
   - Block on critical violations

### Acceptance Criteria

- [ ] Zero WCAG AAA violations (axe audit)
- [ ] Color contrast ≥ 7:1 for all text (verified via WebAIM)
- [ ] All form inputs have visible labels + aria-label
- [ ] All buttons have text or aria-label
- [ ] Landmarks present: `<nav>`, `<main>`, `<aside>` on all pages
- [ ] Focus rings visible (min 2px, 3:1 contrast)
- [ ] Keyboard navigation: Tab order logical, no traps
- [ ] Escape key closes modals/drawers/popovers
- [ ] Screen reader (NVDA/VoiceOver): can navigate all flows
- [ ] Lighthouse Accessibility ≥ 95 on all pages
- [ ] Automated axe tests pass in CI/CD (0 violations)
- [ ] No `outline: none` without replacement

### Story Points & Breakdown

| Task | SP | Assignee | Timeline |
|------|----|---------|---------:|
| Comprehensive a11y audit (all pages) | 3 | QA/Dev 1 | W1 |
| Color contrast fixes (50–80 updates) | 3 | Dev 2 | W1 |
| ARIA labels + semantic HTML (80+ updates) | 4 | Dev 1 | W1–W2 |
| Keyboard navigation + focus handling | 2 | Dev 2 | W2 |
| Focus indicators (custom styling) | 1 | Dev 1 | W2 |
| Screen reader testing (NVDA, VoiceOver) | 2 | QA | W2 |
| Automated axe tests + CI integration | 1 | Dev 1 | W2 |
| **Subtotal** | **16** | — | **2–3 weeks** |

### Dependencies & Risks

- **Risk:** Design system tokens may not support 7:1 contrast → rework color palette
- **Risk:** Third-party component libraries (Radix) may have a11y issues → patches needed
- **Risk:** Screen reader testing requires assistive tech setup → coordinate with QA team
- **Dependency:** None blocking (can start in parallel)

### Tech Stack
- axe DevTools (audit)
- @axe-core/playwright (automated testing)
- WebAIM contrast checker
- NVDA, JAWS, VoiceOver (manual testing)
- Tailwind CSS (focus utilities)

---

## Detailed Timeline & Resource Allocation

### Phase 0: Planning & Setup (Week 0 — 3 days)
- **Deliverables:**
  - Finalize this scope document
  - Set up branch: `feature/web-improvements-2026`
  - Create GitHub milestone + issues (per feature)
  - Define PM+ feedback loop

### Phase 1: PWA + Accessibility (Weeks 1–3)
- **Team:** Dev 1 (PWA lead), Dev 2 (a11y lead), QA (testing)
- **Parallel tracks:**
  - Track A: PWA (SW, install prompt, sync queue) — Dev 1 + Dev 2
  - Track B: Accessibility (audit, a11y fixes) — Dev 1 + Dev 2 (30% allocation)
- **Deliverables:** PWA-complete, WCAG AAA compliant
- **Go/No-Go Gate:** Lighthouse PWA ≥ 90, Accessibility ≥ 95

### Phase 2: Performance + Mobile (Weeks 2–4)
- **Team:** Dev 1 (perf), Dev 2 (mobile), QA (perf testing)
- **Parallel tracks:**
  - Track C: Performance tuning (bundle, images, fonts) — Dev 1
  - Track D: Mobile optimization (responsive, touch gestures) — Dev 2
- **Deliverables:** Lighthouse 90+ (all metrics), 4G load < 3s
- **Go/No-Go Gate:** Lighthouse Performance ≥ 90, bundle size ≤ 200KB gzip

### Phase 3: Advanced Features (Weeks 4–8, P0-centric)
- **Team:** Dev 1 + Dev 2 (1.5 FTE effective due to other commitments)
- **Sequencing (P0 first):**
  1. Advanced Filters + Saved Views (Weeks 4–5) — 8 SP
  2. Export (CSV/Excel/PDF) (Weeks 5–6) — 6 SP
  3. Dashboard Widgets (Weeks 6–7) — 8 SP
  4. Analytics Dashboard (Week 7) — 4 SP
  5. Real-time Collaboration (Weeks 7–9, optional/Phase 2) — 12+ SP
- **Deliverables (P0):** Filters, Exports, basic widgets, analytics KPIs
- **Go/No-Go Gate:** Feature tests ≥ 90% coverage, performance regression ≤ 5%

### Timeline Summary

```
Week 1:  [PWA Planning] [PWA Dev] [A11y Audit] [Perf Audit]
Week 2:  [PWA + Sync]  [Mobile Responsive] [Perf Tuning] [A11y Fixes]
Week 3:  [PWA Testing] [Mobile Touch]      [Perf Testing] [A11y Testing]
Week 4:  [Mobile Polish] [Filters] [Code Split] [Lighthouse Push]
Week 5:  [Filters + Saved Views] [Export Design]
Week 6:  [Export Impl] [Widgets Design]
Week 7:  [Widgets Impl] [Analytics KPIs]
Week 8:  [Analytics Testing] [Real-time Collab Start (opt)]
Week 9:  [Real-time Collab] [Final Testing + Prod Readiness]

Timeline: 8–12 weeks (Phase 0: PWA + Mobile + Perf + A11y = 3–4 weeks, Phase 1: Advanced = 4–6 weeks)
```

---

## Resource Allocation & Team Structure

### Ideal Team Composition (5–6 FTE)

| Role | Count | Allocation | Responsibilities |
|------|-------|-----------|---|
| Frontend Dev (Senior) | 1 | 100% | PWA, performance, architecture |
| Frontend Dev (Mid) | 1 | 100% | Mobile, touch gestures, UX polish |
| QA Engineer | 1 | 50% | A11y audit, performance testing, E2E tests |
| UI/UX Designer | 1 | 25% | Mobile layouts, widget mockups, a11y review |
| PM/Scrum Master | 1 | 25% | Prioritization, stakeholder updates, scope management |
| Backend Support (optional) | — | 10% | PWA notifications, analytics data API |

### Minimum Viable Team (3–4 FTE)

If fewer resources available:
1. **Drop Feature 4 (Advanced Features)** until Phase 2 (saves 4–6 weeks)
2. **Reduce A11y to WCAG AA** instead of AAA (saves 1 week, 3 SP)
3. **Real-time Collaboration → defer** (lowest priority)
4. **Timeline shrinks to 5–7 weeks** (Phase 0: PWA + Mobile + Perf = 3–4 weeks)

---

## Risk & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-----------|-----------|
| Service Worker caching breaks auth tokens | High | Medium | Exclude `/api/*` from SW cache, use network-only for auth |
| Bottom sheet library incompatible with Next.js 14 | Medium | Low | Build custom bottom sheet (1–2 days) |
| Lazy loading causes UI jump (CLS regression) | Medium | Medium | Use skeletons, define dimensions, test with Lighthouse |
| CRDT library increases bundle by 50KB | Medium | Low | Defer real-time collab or use lighter OT lib |
| IndexedDB quota exceeded (sync queue huge) | Low | Low | Implement quota check, UI warning, auto-cleanup old records |
| WebSocket backend not ready | High | Medium | Implement HTTP polling fallback for Phase 1 |
| Performance regression from new features | High | Medium | Continuous Lighthouse monitoring, CI/CD gates, before/after perf tests |
| Accessibility fixes require design rework | Medium | Low | Work with design early (Week 0), use WCAG color palette |

---

## Success Metrics & KPIs

### Performance KPIs
- **Lighthouse Performance:** 90+ (all pages)
- **Bundle Size:** ≤ 200KB gzip (main chunk)
- **LCP:** < 2.5s on 4G
- **CLS:** < 0.1
- **FID:** < 100ms

### UX KPIs
- **Mobile Load Time (4G):** < 3s
- **Touch Interaction Latency:** < 100ms
- **Gesture Success Rate:** > 95% (swipe, long-press)
- **Mobile Session Duration:** +20% vs. current

### A11y KPIs
- **WCAG AAA Violations:** 0
- **Automated Axe Test Pass Rate:** 100%
- **Screen Reader Success Rate:** 95%+ (manual testing)
- **Keyboard Navigation Coverage:** 100% of interactive elements

### Feature Adoption
- **PWA Installation Rate:** > 15% of users (target)
- **Offline Usage:** > 5% of sessions
- **Advanced Filters Usage:** > 40% of daily active users
- **Export Feature Usage:** > 20% of workflows

---

## Dependencies & Prerequisites

### External
- Backend: PWA notification API (`POST /api/v1/notify/push`)
- Backend: Analytics data API (`GET /api/v1/analytics/*`)
- Backend: WebSocket server (for real-time collab, Phase 2+)
- Design team: Color palette review (a11y compliance)

### Internal
- Feature freeze: 2026-06-15 (after current build stabilizes)
- No major Next.js upgrades during Phase 1
- Continuous integration: ensure CI/CD green before feature releases

---

## Appendix: Tooling & Dev Setup

### New Dependencies to Add
```json
{
  "dependencies": {
    "web-vitals": "^3.5.0",           // Core Web Vitals tracking
    "yjs": "^13.5.0",                 // CRDT (optional, for real-time)
    "y-websocket": "^1.4.0",          // CRDT WebSocket provider (optional)
    "@axe-core/playwright": "^4.10.0" // Already in package.json
  },
  "devDependencies": {
    "@next/bundle-analyzer": "^14.2.0", // Bundle analysis
    "@axe-core/react": "^4.10.0"        // React a11y testing
  }
}
```

### Dev Tools & Commands
```bash
# Performance profiling
npm run build && npm run analyze  # Bundle analysis (ANALYZE=true)
npx next build                    # Production build
npx lighthouse https://localhost:3000

# A11y testing
npx axe https://localhost:3000
npm run test:a11y                 # axe + Playwright tests (new)

# Mobile testing
npx playwright test --device="iPhone 12"
npx playwright test --device="iPad"

# Core Web Vitals
npm run web-vitals-report         # Dashboard (new)
```

### Testing Strategy
- **Unit tests:** Component logic (Jest)
- **Integration tests:** Service Worker, IndexedDB (Playwright)
- **E2E tests:** Full flows (PWA offline, mobile gestures, exports)
- **Performance tests:** Lighthouse, bundle size regression
- **A11y tests:** axe automated, manual screen reader (NVDA, VoiceOver)
- **Target:** 85%+ test coverage (up from current ~60%)

---

## Go-to-Market Plan

### Release Cadence
- **Beta (Internal):** Weeks 1–4 (PWA, mobile, performance — team only)
- **Staged Rollout:** Weeks 4–5 (PWA to 25% → 50% → 100% of users)
- **GA:** Week 5 (PWA + Mobile fully live)
- **Advanced Features (Filters/Export):** Week 6 (staged rollout → GA by Week 7)

### Communication
- **Week 0:** Announce scope + timeline to stakeholders
- **Weeks 1–3:** Bi-weekly progress updates (% complete, blockers)
- **Week 4:** Beta feedback collection
- **Week 5:** User education (PWA install guide, mobile tips)
- **Week 6+:** Analytics & usage monitoring

### Rollback Plan
- Feature flags: PWA, mobile optimizations, advanced filters (via backend config)
- Enable/disable per user segment
- Revert commits if regression detected (< 1 hour window)

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-09  
**Prepared By:** Claude Code (Agent)  
**Status:** Ready for Stakeholder Review
