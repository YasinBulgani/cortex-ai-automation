# Neurex Web Improvements — Quick Reference & Visual Timeline
**Document:** WEB_IMPROVEMENTS_QUICK_REFERENCE_2026_06_09.md  
**Generated:** 2026-06-09  
**Related:** WEB_IMPROVEMENTS_SCOPE_2026_06_09.md

---

## 🚀 Quick Facts

| Metric | Value |
|--------|-------|
| **Total Story Points** | 101 SP |
| **Total FTE Required** | 5–6 FTE |
| **Minimum FTE** | 3–4 FTE (drop Feature 4) |
| **Timeline (Full Scope)** | 8–12 weeks |
| **Timeline (Phase 0 Only)** | 3–4 weeks (PWA + Mobile + Perf + A11y) |
| **Recommended Phase 1** | 4–6 weeks (Filters + Export + Widgets + Analytics) |
| **Current LOC** | ~285K TypeScript/TSX |
| **Estimated Added LOC** | 1000–2000 (PWA, Mobile, A11y) + 3000+ (Advanced) |

---

## 📊 Feature Sizing Matrix

```
        Story Points    Timeline    Complexity    Risk
PWA     21 SP           3–4 wks     HIGH          MED
Mobile  18 SP           2–3 wks     HIGH          MED
Perf    13 SP           2 wks       MEDIUM        LOW
A11y    16 SP           2–3 wks     MEDIUM        LOW
Filters 8 SP            2–3 wks     MEDIUM        LOW
Export  6 SP            1–2 wks     MEDIUM        LOW
Widgets 8 SP            2–3 wks     HIGH          MED
Analytics 4 SP          1 wk        LOW           LOW
Collab  12+ SP          4–5 wks     VERY HIGH     HIGH
─────────────────────────────────────────────────────
TOTAL   101+ SP         8–12 wks    –             –
```

---

## ⏱️ Visual Timeline (8-Week Critical Path)

```
        1    2    3    4    5    6    7    8
PWA     ■■■■ ■■
Mobile      ■■■■ ■■
Perf    ■■■■ ■
A11y    ■■■■ ■■
Filter              ■■■■ ■
Export                  ■■■■
Widget                      ■■■■ ■■
Analytics                        ■
─────────────────────────────────────────
Phase 0 (MVP): Weeks 1–3 (PWA, Mobile, Perf, A11y)
Phase 1 (P0):  Weeks 4–7 (Filters, Export, Widgets, Analytics)
Phase 2 (P1):  Weeks 7–9 (Real-time Collab, Polish)

CRITICAL PATH: PWA (3 wks) → Mobile Polish (1 wk) → Filters (2 wks) → Export (1 wk)
```

---

## 👥 Team Composition & Allocation

### Scenario A: Full Team (5–6 FTE)

```
Frontend Dev 1 (Senior, 100%)
  ├─ Weeks 1–3: PWA lead (SW, install prompt, sync queue)
  ├─ Weeks 2–3: Performance lead (bundle, images, fonts)
  ├─ Weeks 4–5: Mobile polish, testing
  └─ Weeks 5+: Perf monitoring, tech debt

Frontend Dev 2 (Mid, 100%)
  ├─ Weeks 1–3: A11y lead (audit, color, ARIA)
  ├─ Weeks 1–3: PWA support (IndexedDB, push)
  ├─ Weeks 3–4: Mobile optimizations (responsive, touch)
  └─ Weeks 5+: Filters, widgets, exports

QA Engineer (50%)
  ├─ Weeks 1–3: A11y screen reader testing
  ├─ Weeks 2–3: Perf baseline + 4G testing
  ├─ Weeks 3–4: Mobile device testing (Android, iOS)
  └─ Weeks 4+: Feature E2E tests, Lighthouse monitoring

Designer (25%)
  ├─ Week 0: A11y color palette review
  ├─ Week 1: Mobile layout mockups
  ├─ Weeks 4–5: Widget + filter design
  └─ Weeks 5+: Accessibility polish

PM/Scrum (25%)
  ├─ Week 0: Scope finalization, stakeholder alignment
  ├─ Weeks 1–8: Bi-weekly progress updates, blocker resolution
  └─ Week 8+: Go-to-market planning
```

### Scenario B: Minimal Team (3–4 FTE)

**Strategy:** Drop Feature 4 (Advanced), reduce A11y to WCAG AA

```
Frontend Dev 1 (Senior, 100%)
  ├─ Weeks 1–3: PWA + Performance
  ├─ Weeks 3–4: Mobile + A11y (20%)
  └─ Weeks 5–6: Polish + testing

Frontend Dev 2 (Mid, 100%)
  ├─ Weeks 1–3: A11y + Mobile
  ├─ Weeks 3–5: Mobile-specific features
  └─ Weeks 5–6: Testing + bug fixes

QA (50%)
  ├─ Weeks 1–6: A11y testing, perf baseline, E2E
  └─ Weeks 6+: Regression testing

Timeline: 5–6 weeks (Phase 0 + limited Phase 1)
```

---

## 💰 Effort & Cost Estimation

### Assumptions
- **Senior Dev:** $150/hour
- **Mid Dev:** $100/hour
- **QA:** $80/hour
- **Designer:** $120/hour
- **PM:** $140/hour
- **Development week:** 40 hours effective (meetings, breaks)

### Full Scope (5–6 FTE, 8–12 weeks)

| Role | FTE | Weeks | Hours | Cost |
|------|-----|-------|-------|------|
| Senior Dev | 1 | 10 | 400 | $60K |
| Mid Dev | 1 | 10 | 400 | $40K |
| QA | 0.5 | 10 | 200 | $16K |
| Designer | 0.25 | 5 | 50 | $6K |
| PM | 0.25 | 10 | 100 | $14K |
| **TOTAL** | **5.0** | **10** | **1,150 hrs** | **$136K** |

### Phase 0 Only (PWA + Mobile + Perf + A11y, 3–4 weeks, 4 FTE)

| Role | FTE | Weeks | Hours | Cost |
|------|-----|-------|-------|------|
| Senior Dev | 1 | 4 | 160 | $24K |
| Mid Dev | 1 | 4 | 160 | $16K |
| QA | 0.5 | 4 | 80 | $6.4K |
| Designer | 0.25 | 1 | 10 | $1.2K |
| PM | 0.25 | 4 | 40 | $5.6K |
| **TOTAL** | **4.0** | **4** | **450 hrs** | **$53.2K** |

---

## 🎯 Prioritization Framework

### P0 (Must-Have, Phase 0 — Weeks 1–4)
1. ✅ **PWA Support** (21 SP) — offline mode, install, sync queue
2. ✅ **Mobile Optimization** (18 SP) — responsive, touch, 4G perf
3. ✅ **Performance Tuning** (13 SP) — Lighthouse 90+, bundle < 200KB
4. ✅ **Accessibility (WCAG AA)** (14 SP) — audit, fixes, keyboard nav

**Total:** 66 SP, 4 FTE, 3–4 weeks  
**Go-to-Market:** Beta internal by Week 4, GA by Week 5  
**Success Gate:** Lighthouse Performance ≥ 90, PWA ≥ 90, Mobile users +25%

### P1 (Should-Have, Phase 1 — Weeks 5–7)
5. ✅ **Advanced Filters** (8 SP) — filter builder, saved views
6. ✅ **Export Features** (6 SP) — CSV, Excel, PDF
7. ✅ **Dashboard Widgets** (8 SP) — 8+ customizable widgets
8. ✅ **Analytics Dashboard** (4 SP) — KPIs, trends, date filters

**Total:** 26 SP, 2 FTE, 2–3 weeks  
**Success Gate:** Feature tests ≥ 90%, perf regression ≤ 5%

### P2 (Nice-to-Have, Phase 2 — Weeks 7–12)
9. ⚠️ **Real-Time Collaboration** (12+ SP) — WebSocket, CRDT, presence
10. ⚠️ **Advanced Analytics** (pending SP) — data models, custom reports

**Total:** 12+ SP, 2–3 FTE, 4–5 weeks  
**Notes:** Requires backend WebSocket server; recommend Phase 2 (post-GA)

---

## 🏁 Exit Criteria & Gate Reviews

### Phase 0 Gate (Week 4, Thursday before launch)

**Lighthouse Metrics:**
- [ ] Performance ≥ 90 on /, /portfolio, /login
- [ ] Accessibility ≥ 95 on all pages
- [ ] Best Practices ≥ 95
- [ ] PWA installable ✓

**Functionality:**
- [ ] PWA: offline mode works (CacheStorage verified)
- [ ] Mobile: 44×44px touch targets, no horizontal scroll on 320px
- [ ] Performance: LCP < 2.5s, CLS < 0.1, FID < 100ms
- [ ] A11y: 0 WCAG violations, keyboard nav complete

**Testing:**
- [ ] E2E (Playwright): 40+ tests passing
- [ ] Visual regression: 0 unexpected diffs
- [ ] Performance: baseline established, regression ≤ 5%
- [ ] A11y: axe audit 0 violations, manual VoiceOver test passed

**Go/No-Go:** Sign-off from PM + Tech Lead  
**Decision:** Proceed to beta rollout or fix critical blockers (1–2 day window)

### Phase 1 Gate (Week 7, Friday)

**Functionality:**
- [ ] Filters: create, save, share, delete filters ✓
- [ ] Export: CSV/Excel/PDF generation, no timeout ✓
- [ ] Widgets: 8+ types, drag-and-drop, persistence ✓
- [ ] Analytics: KPIs, trends, date range filter ✓

**Testing:**
- [ ] E2E: 60+ tests passing (cumulative)
- [ ] Performance: Lighthouse regression ≤ 5% vs. Phase 0
- [ ] Accessibility: WCAG violations ≤ 2 (non-critical)
- [ ] Exports: tested with 10K+ rows, <30s generation

**Go/No-Go:** Proceed to GA rollout or defer features

---

## 📋 High-Level Acceptance Criteria Checklist

### PWA (Weeks 1–3)

- [ ] Service Worker: cache strategies working (network-first HTML, cache-first assets)
- [ ] Offline mode: can navigate cached pages, sync queue visible
- [ ] Install prompt: works on Chrome, Edge, Safari (iOS fallback with instructions)
- [ ] Background Sync: queued mutations resync when online
- [ ] Push notifications: received in foreground/background, click navigates
- [ ] Lighthouse PWA score ≥ 90
- [ ] Manifest updated with start_url, shortcuts, display
- [ ] `/offline` page functional with retry CTA
- [ ] 0 console errors on production build

### Mobile Optimization (Weeks 2–4)

- [ ] All touch targets ≥ 44×44px (verified via axe)
- [ ] Tablet layouts work (768px–1024px): 2-column, no overflow
- [ ] Foldable support: app usable in folded state (device emulator)
- [ ] Swipe gestures: left/right on case list, up/down on lists
- [ ] Long-press: context menu on defect rows
- [ ] Pull-to-refresh: visual spinner, lists refresh
- [ ] Bottom sheet: smooth open/close, swipe-down dismisses
- [ ] Mobile menu: hamburger → bottom sheet (mobile), side nav (tablet+)
- [ ] 4G performance: FCP < 2s, LCP < 3s (Lighthouse throttled)
- [ ] Landscape rotation: layout reflows, scroll position preserved
- [ ] Lighthouse mobile score ≥ 90

### Performance Tuning (Weeks 1–2)

- [ ] Lighthouse Performance ≥ 90 on all main routes
- [ ] Bundle size ≤ 200KB gzip (main chunk)
- [ ] All images use next/image with explicit dimensions
- [ ] Code splitting active: 15+ dynamic imports
- [ ] LCP < 2.5s (desktop), < 3s (4G throttled)
- [ ] CLS < 0.1 (no layout shifts)
- [ ] FID < 100ms
- [ ] Core Web Vitals dashboard integrated with Sentry
- [ ] 0 console warnings on prod build

### Accessibility (Weeks 1–3)

- [ ] Zero WCAG AAA violations (or ≤ 2 non-critical for P1)
- [ ] Color contrast ≥ 7:1 for all text
- [ ] All form inputs have labels + aria-label
- [ ] All buttons have text or aria-label
- [ ] Focus rings visible (≥ 2px, 3:1 contrast)
- [ ] Keyboard navigation: logical tab order, no traps
- [ ] Escape key closes modals/drawers
- [ ] Screen reader test (NVDA, VoiceOver): can navigate
- [ ] Lighthouse Accessibility ≥ 95 on all pages
- [ ] Automated axe tests pass in CI/CD

### Advanced Filters (Weeks 5–6)

- [ ] Filter builder UI: status, assignee, tags, date range, custom fields
- [ ] Save/load filters: persisted to backend
- [ ] Share filters: URL-encoded link
- [ ] Quick templates: critical, assigned-to-me, this-sprint
- [ ] Bulk actions: select multiple, apply action
- [ ] Tested with 50K+ data points

### Export Features (Weeks 5–6)

- [ ] CSV export: all columns, 50K+ rows without timeout
- [ ] Excel export: multi-sheet, formatted, < 50MB
- [ ] PDF export: branded header/footer, charts, < 20s generation
- [ ] All exports tested with real data

### Dashboard Widgets (Weeks 6–7)

- [ ] 8+ widget types available: cases, coverage, trends, etc.
- [ ] Drag-and-drop layout reordering
- [ ] Widget size customization (small, medium, large)
- [ ] Layout persisted to backend
- [ ] Real-time updates: refresh on data change
- [ ] Share dashboard: snapshot + export

### Analytics Dashboard (Week 7)

- [ ] 6+ KPI cards: test execution, coverage %, defect trends
- [ ] Trend lines: execution velocity, coverage growth
- [ ] Date range selection: last 7 days, month, quarter
- [ ] Tested with real historical data

---

## 🛠️ Technical Dependencies Checklist

### Code Changes
- [ ] Next.js 14 bundler config optimized
- [ ] TypeScript strict mode enforced
- [ ] ESLint rules updated (a11y)
- [ ] Jest/Playwright test suites enhanced
- [ ] @next/bundle-analyzer installed
- [ ] web-vitals integration done
- [ ] @axe-core/playwright tests added

### Infrastructure
- [ ] Service Worker build process added
- [ ] ImageOptimizer configured (WebP)
- [ ] Lighthouse CI/CD check added
- [ ] A11y axe check in CI/CD
- [ ] Performance regression gates in CI/CD

### Backend (Soft Dependency)
- [ ] PWA notification API (`POST /api/v1/notify/push`)
- [ ] Analytics data API (`GET /api/v1/analytics/*`)
- [ ] Saved filters API (`GET/POST /api/v1/saved-filters`)
- [ ] Export endpoint (`POST /api/v1/export/csv|xlsx|pdf`)

---

## 🔄 Rollback & Risk Mitigation Plan

### Rollback Strategy (< 1 hour SLA)

**Feature Flags:**
```json
{
  "features": {
    "pwa_enabled": { "default": false, "rollout_percent": 25 },
    "mobile_optimizations": { "default": false, "rollout_percent": 50 },
    "advanced_filters": { "default": false, "rollout_percent": 10 },
    "export_features": { "default": false, "rollout_percent": 25 }
  }
}
```

**Rollback Procedure:**
1. Set feature flag to 0% rollout
2. Clear CDN cache (`/_next/static/`)
3. Monitor error rate (target: < 0.1%)
4. Revert commit if regression persists (Git reset --hard)

### Monitoring Dashboard (Week 1 Setup)

- Lighthouse metrics (per route)
- Bundle size trend (per release)
- Performance regression alerts
- Core Web Vitals alerts (LCP, CLS, FID)
- A11y violation count
- User error rate (via Sentry)

---

## 📈 Success Metrics & Targets

### Quantitative Targets (Phase 0)

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Lighthouse Performance | ~87 | 90+ | W2 |
| Lighthouse Accessibility | ~92 | 95+ | W3 |
| Bundle Size (gzip) | ~240KB | <200KB | W2 |
| LCP (desktop) | ~2.8s | <2.5s | W2 |
| LCP (4G throttled) | ~5s | <3s | W2 |
| CLS | ~0.08 | <0.1 | W2 |
| Mobile sessions | baseline | +25% | W5 |

### Qualitative Targets

- Users rate mobile experience ≥ 4.2/5 stars
- PWA installation rate ≥ 15% of users
- Offline session success rate ≥ 90%
- 0 critical a11y bugs (verified via axe + VoiceOver)
- Dev team considers mobile-first by default

---

## 📞 Communication & Stakeholder Updates

### Weekly Sync (Fridays, 30 min)
- Progress % by feature
- Blockers + mitigation
- Lighthouse metrics snapshot
- Next week priorities

### Bi-Weekly Report (Tuesdays)
- Detailed metrics dashboard
- Feature completeness status
- Risk register update
- Go/No-Go gate decisions

### Monthly All-Hands (First Monday)
- Strategic alignment
- User feedback loop
- Timeline adjustments
- Public roadmap update

---

## 🎓 Knowledge Transfer & Documentation

### Internal Docs to Create
- [ ] PWA implementation guide (Service Worker, offline)
- [ ] Mobile optimization best practices
- [ ] A11y audit checklist + remediation guide
- [ ] Performance optimization playbook
- [ ] Testing strategy (E2E, a11y, perf)

### Team Training (Week 0–1)
- [ ] Service Worker workshop (2h)
- [ ] WCAG AAA training (1h, QA-led)
- [ ] Lighthouse + bundle analysis (1.5h)
- [ ] Mobile testing on real devices (1h)

---

## 📌 Success Story (Hypothetical, Week 9)

```
✅ PWA live: 8% of users installed (1,200 DAU offline)
✅ Mobile: 42% of sessions now from mobile (2x previous)
✅ Performance: Lighthouse 94/100, users report 50% faster
✅ A11y: 100% WCAG AAA compliant, 3x screen reader users
✅ Filters: 35% of workflows use saved filters (adoption)
✅ Exports: 500+ daily PDF/CSV exports
✅ Analytics: Product team uses dashboard daily

Result: +32% user satisfaction, -40% support tickets (mobile issues)
```

---

**Version:** 1.0  
**Last Updated:** 2026-06-09  
**Next Review:** Week 1 (2026-06-16)
