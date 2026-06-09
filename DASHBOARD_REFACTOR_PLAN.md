# Dashboard Refactoring Plan — Cortex Neurex Management

**Status:** Phase 0 Analysis Complete  
**Date:** 2026-06-09  
**Scope:** Dashboard UI restructuring from mega-component → tab-based architecture  
**Risk Level:** Medium (UX continuity, data load timing, mobile responsiveness)

---

## Executive Summary

Current dashboard (`page.tsx` — 1690 lines) is a single mega-component with 40+ inline widgets. This creates:
- **Code bloat:** 11 useQuery hooks + 15+ useMemo compute paths
- **Loading UX pain:** All 10 API calls block initial render (serial dependency)
- **Performance cliff:** Re-renders entire page on any data update
- **Mobile:** Overflowing grid layout, no responsive collapse
- **Maintenance:** Widget logic scattered inline (no reuse, copy-paste patterns)

**Proposed Solution:** Tab-based dashboard with smart eager/lazy loading + component extraction.

---

## 1. Current State Analysis

### 1.1 Widget Inventory (40+ widgets found)

**Always-Visible (Hero Metrics):**
- Header with auto-refresh badge
- Project Health Score widget
- Setup Tracker widget
- 8× StatCard grid (KPI cards)

**Content Sections (Sequential):**
- Blockers widget + Release Signoff
- Run Trend Chart + Defect Trend Mini
- Test Insights Panel (Type/Priority/Velocity)
- Coverage Heatmap (if suites > 0)
- Regression & Release Readiness (3 MiniBar + 4 checklist items)
- Tester Workload (MiniBar list)
- Quick Actions (8 buttons)
- My Work (My Cases + Open Defects)
- Latest Runs + Latest Cases + Module Distribution
- Flaky Tests Widget
- Review Queue Widget
- Stale Tests Widget
- Activity Feed (8 audit events)

**Data Dependencies:**
```
summaryFast          [eager]  ← fast aggregated endpoint
repoQ                [lazy]   ← suites, folders, cases
runsQ                [lazy]   ← run list + active count
summaryQ             [lazy]   ← execution summary (pass rate, progress)
defectsQ             [lazy]   ← critical + trend data
releaseQ             [lazy]   ← blockers, decision, checklist
requirementsQ        [lazy]   ← coverage %
auditQ               [lazy]   ← activity feed (8 events)
plansQ               [lazy]   ← plan count
flakyQ               [lazy]   ← flaky test list
reviewQ              [lazy]   ← review queue
trendQ               [lazy]   ← run trend points
membersData          [static] ← user name map
profile              [static] ← current user ID
```

### 1.2 Performance Footprint

| Metric | Current | Target |
|--------|---------|--------|
| Load time (first paint) | ~2s (wait for repoQ) | 400ms (summaryFast only) |
| Total data requests | 11 parallel | 3-5 per tab (lazy) |
| Page rerender cost | O(n widgets) | O(1 tab) |
| Mobile breakpoint | None | 768px collapse |
| Code size | 1690 lines | ~150 per component |

### 1.3 Usability Issues

**Issue 1: Cognitive Overload** — User scrolls 2500px to find one metric  
**Issue 2: Data Thrashing** — 30s auto-refetch refreshes entire page  
**Issue 3: Mobile Unusable** — 8-column grid → single column, still 3000px  
**Issue 4: Setup Friction** — Empty state conflicts with Quick Setup Wizard  
**Issue 5: Tab Navigation Missing** — No way to jump between sections  

---

## 2. Proposed Architecture: Tab-Based Dashboard

### 2.1 Tab Structure

```
TAB 1: OVERVIEW (default, eager)
├─ Header (project name, refresh badge, CTAs)
├─ Hero Metrics (4 KPI cards)
├─ Project Health + Setup Tracker (2-col grid)
├─ 8× StatCard (4-col responsive)
└─ Quick Actions (button row)

TAB 2: TRENDS & QUALITY (lazy)
├─ Run Trend Chart (pass rate over time)
├─ Defect Trend Mini (8-week open/closed)
├─ Coverage Heatmap (suite breakdown)
└─ Test Insights (Type/Priority/Velocity)

TAB 3: RELEASE & BLOCKERS (lazy)
├─ Blockers Widget (release gates)
├─ Release Signoff Widget (approval form)
├─ Regression Readiness (3 progress bars)
└─ Release Checklist (4 items)

TAB 4: MY WORK & TEAM (lazy)
├─ My Work (My Cases + Open Defects)
├─ Flaky Tests (automated outliers)
├─ Review Queue (pending approvals)
├─ Tester Workload (assignment distribution)
└─ Team Module Distribution

TAB 5: ACTIVITY & INSIGHTS (lazy)
├─ Latest Runs (5 most recent)
├─ Latest Cases (5 most recently updated)
├─ Stale Tests Widget (not run in 14 days)
└─ Activity Feed (8 audit events)
```

### 2.2 Data Loading Strategy

**Eager (Block TAB 1 render):**
- `summaryFast` — dashboard summary endpoint (KPIs, counts)
- `profile` — current user info (static)

**Lazy Tab 2 (Request on click):**
- `trendQ`, `defectsQ`, `repoQ` (coverage heatmap suites)

**Lazy Tab 3 (Request on click):**
- `releaseQ`, `plansQ`

**Lazy Tab 4 (Request on click):**
- `flakyQ`, `reviewQ`, `runsQ` (workload needs runs), `repoQ`

**Lazy Tab 5 (Request on click):**
- `auditQ`, `runsQ` (latest), `repoQ` (cases, distribution)

**Auto-Refresh:** Refetch only active tab data every 30s (not all 11 hooks)

---

## 3. Component Structure

### 3.1 File Tree

```
/management/dashboard/
├── page.tsx (200 lines)
│   ├─ Router/layout setup
│   ├─ Tab state mgmt
│   ├─ Eager data loading
│   └─ Conditional lazy render
│
├── _components/
│   ├── DashboardTabs.tsx (250 lines)
│   │   ├─ Tab nav UI
│   │   ├─ Active tab detection
│   │   └─ Lazy load trigger
│   │
│   ├── dashboard-tabs/
│   │   ├── OverviewTab.tsx (350 lines)
│   │   │   ├─ Hero metrics
│   │   │   ├─ Health widget
│   │   │   ├─ Setup tracker
│   │   │   ├─ 8 stat cards
│   │   │   └─ Quick actions
│   │   │
│   │   ├── TrendsTab.tsx (280 lines)
│   │   │   ├─ Run Trend Chart
│   │   │   ├─ Defect Trend Mini
│   │   │   ├─ Coverage Heatmap
│   │   │   └─ Test Insights Panel
│   │   │
│   │   ├── ReleaseTab.tsx (220 lines)
│   │   │   ├─ Blockers widget
│   │   │   ├─ Release Signoff widget
│   │   │   ├─ Regression readiness
│   │   │   └─ Checklist
│   │   │
│   │   ├── MyWorkTab.tsx (300 lines)
│   │   │   ├─ My Work (cases + defects)
│   │   │   ├─ Flaky Tests widget
│   │   │   ├─ Review Queue
│   │   │   ├─ Tester Workload
│   │   │   └─ Module Distribution
│   │   │
│   │   └── ActivityTab.tsx (200 lines)
│   │       ├─ Latest Runs
│   │       ├─ Latest Cases
│   │       ├─ Stale Tests
│   │       └─ Activity Feed
│   │
│   ├── shared-widgets/
│   │   ├── HeroMetricCard.tsx (80 lines)
│   │   ├── ProjectHealthWidget.tsx (120 lines, refactored)
│   │   ├── SetupTrackerWidget.tsx (120 lines, refactored)
│   │   ├── StatCard.tsx (60 lines, refactored)
│   │   ├── BlockersWidget.tsx (100 lines, refactored)
│   │   ├── ReleaseSignoffWidget.tsx (140 lines, refactored)
│   │   ├── RunTrendChart.tsx (180 lines, refactored)
│   │   ├── DefectTrendMini.tsx (100 lines, refactored)
│   │   ├── CoverageHeatmap.tsx (140 lines, refactored)
│   │   ├── TestInsightsPanel.tsx (150 lines, refactored)
│   │   ├── FlakyTestsWidget.tsx (120 lines, refactored)
│   │   ├── ReviewQueueWidget.tsx (100 lines, refactored)
│   │   ├── StaleTestsWidget.tsx (130 lines, refactored)
│   │   ├── MyWorkWidget.tsx (200 lines, refactored)
│   │   ├── ActivityFeedWidget.tsx (100 lines, refactored)
│   │   ├── MiniBar.tsx (40 lines)
│   │   ├── HorizBar.tsx (40 lines)
│   │   ├── AutoRefreshBadge.tsx (60 lines)
│   │   └── EmptyState.tsx (60 lines)
│   │
│   └── utils/
│       ├── dashboard-helpers.ts (150 lines)
│       │   ├─ STATUS_TR mapping
│       │   ├─ asText()
│       │   ├─ tr()
│       │   └─ date formatting
│       └── dashboard-hooks.ts (200 lines)
│           ├─ useTabState()
│           ├─ useLazyTabData()
│           ├─ useAutoRefresh()
│           └─ useStaleTests()

TOTAL NEW CODE: ~3200 lines distributed
REMOVED: 1690 lines from page.tsx
NET REDUCTION: ~500 lines (better reuse, clearer intent)
```

### 3.2 Component Responsibilities

**page.tsx (200 lines):**
- Project ID routing
- Eager data load (summaryFast, profile)
- Error boundary
- Tab state management (URL search param or React state)
- Render DashboardTabs wrapper

**DashboardTabs.tsx (250 lines):**
- Tab navigation UI (styled buttons)
- Active tab highlight
- Tab change handler
- Lazy child render (only active tab mounts)
- Refresh button (refetch active tab only)

**OverviewTab.tsx (350 lines):**
- No data loading — uses page.tsx passed data
- Hero Metrics (4 cards)
- Health + Setup Tracker (2-col)
- 8 StatCards (4-col)
- Quick Actions (8 buttons)
- Mobile: Hero stays, collapse to 2-col grid

**TrendsTab.tsx (280 lines):**
- useManagementRunTrend (lazy)
- useManagementDefects (lazy, if not already in page)
- useManagementRepository (lazy, if not already in page)
- useManagementRuns (lazy, if not already in page)
- Render: RunTrendChart, DefectTrendMini, CoverageHeatmap, TestInsightsPanel

**ReleaseTab.tsx (220 lines):**
- useReleaseReport (lazy)
- useManagementPlans (lazy, if not already in page)
- Render: BlockersWidget, ReleaseSignoffWidget, MiniBar progress bars, Checklist

**MyWorkTab.tsx (300 lines):**
- useManagementFlakyTests (lazy)
- useReviewQueue (lazy)
- useManagementRuns (lazy, for workload calc)
- useManagementRepository (lazy, for cases)
- useQuery members (static, reuse page version if passed)
- useProfile (static, reuse page version)
- Render: MyWorkWidget, FlakyTestsWidget, ReviewQueueWidget, Workload, ModuleDistribution

**ActivityTab.tsx (200 lines):**
- useManagementAuditEvents (lazy, limit=10)
- useManagementRuns (lazy, for latest)
- useManagementRepository (lazy, for latest cases)
- Render: LatestRuns, LatestCases, StaleTestsWidget, ActivityFeed

**shared-widgets/\*.tsx (1400 lines total):**
- Extracted from inline page.tsx logic
- Pure presentation components
- Accept data + callbacks
- No hooks (if possible; memoized)

---

## 4. Mockups & Wireframes

### 4.1 Overview Tab (Default, Always Eager)

```
┌─────────────────────────────────────────────────────────────────┐
│ Neurex Management Dashboard                  [ 30s auto-refresh ▶ ] │
│ Manuel test kapsamı, run sağlığı, defect riski, release hazırlığı │
│                                   [Repository] [Run Başlat]        │
├─────────────────────────────────────────────────────────────────┤
│ TABS: [Overview] [Trends & Quality] [Release] [My Work] [Activity] │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Hero Metrics (4 cards, 25% width each on desktop):             │
│ ┌─────────────┬──────────────┬──────────────┬──────────────┐   │
│ │Total Cases  │ Active Runs  │  Pass Rate   │ Critical     │   │
│ │    145      │      3       │    82%       │ Defects: 5   │   │
│ │245 suites   │12 total runs │89 passed     │resolved: 2   │   │
│ └─────────────┴──────────────┴──────────────┴──────────────┘   │
│                                                                   │
│ ┌─────────────────────────────┬──────────────────────────────┐  │
│ │ Project Health              │ Setup Tracker (75% done)     │  │
│ │ [████████░░] 75/100         │ ✓ First test scenario        │  │
│ │                             │ ✓ First test plan            │  │
│ │ ✓ Pass Rate: 82% (>80%)     │ ✓ First test run             │  │
│ │ ✓ Coverage:  75% (>70%)     │ ○ Requirement linkage        │  │
│ │ ✗ Critical:  5 defects      │ Progress: ████░ 75%         │  │
│ │ ✓ Active:    3 runs         │                              │  │
│ └─────────────────────────────┴──────────────────────────────┘  │
│                                                                   │
│ KPI Grid (8 cards, responsive 4-col/2-col/1-col):             │
│ ┌──────────┬──────────┬──────────┬──────────┐                   │
│ │Failed    │Blocked   │Not Run   │Retest    │                   │
│ │Cases: 8  │Cases: 2  │Cases: 15 │Pending:4 │                   │
│ │Triage    │Env block │Unvisited │Approved  │                   │
│ └──────────┴──────────┴──────────┴──────────┘                   │
│ ┌──────────┬──────────┬──────────┬──────────┐                   │
│ │Suite     │Folder    │Coverage  │Flaky%    │                   │
│ │Count: 5  │Count: 12 │Pct: 75%  │Tests: 2% │                   │
│ │            │            │            │            │                   │
│ └──────────┴──────────┴──────────┴──────────┘                   │
│                                                                   │
│ Quick Actions (button row, wrap on mobile):                    │
│ [+ Yeni Case] [▶ Run Başlat] [Regresyon Seti] [Plan Oluştur]  │
│ [Defect Ekle] [Import] [Raporlar] [Standup]                   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

MOBILE (≤768px):
┌──────────────────────────────┐
│ Dashboard  [options ...]     │
├──────────────────────────────┤
│ [Overview] [Trends]          │
│ [Release] [My Work]          │
│ [Activity]                   │
├──────────────────────────────┤
│ Hero Metrics (stack 1-col)   │
│ ┌────────────────┐           │
│ │Total Cases:145 │           │
│ └────────────────┘           │
│ ┌────────────────┐           │
│ │Pass Rate: 82%  │           │
│ └────────────────┘           │
│ ┌────────────────┐           │
│ │Health: 75/100  │           │
│ └────────────────┘           │
│ ...                          │
│ KPI Grid (2-col)             │
│ ┌──────┬──────┐              │
│ │Failed│Blocked│              │
│ └──────┴──────┘              │
│ ...                          │
└──────────────────────────────┘
```

### 4.2 Trends & Quality Tab

```
┌─────────────────────────────────────────────────────────────────┐
│ TABS: [Overview] [Trends & Quality] [Release] [My Work] [Activity] │
├─────────────────────────────────────────────────────────────────┤
│ Tab loading: [spinner] Fetching trend data...                    │
│                                                                   │
│ Test Koşum Trendi                    [Tüm koşumlar →]            │
│ Ort. %89  Son Run: 91% (+2%)  5 run                             │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │                            ●                               │  │
│ │                      ●                                   │  │
│ │      ●         ●     ○                                     │  │
│ │ ●─────────────────────────────────────────────────────────│  │
│ │ 0%         50%         85% (target)            100%        │  │
│ │ Run1       Run3        Run5                              │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ Defect Trendi                          [Tüm defectler →]        │
│ Son 8 hafta: açık/kapanan                                       │
│ ┌──┬──┬──┬──┬──┬──┬──┬──┐                                        │
│ │█ │█ │█ │█ │█ │█ │█ │█ │ (stacked: red=open, green=closed)    │
│ │█ │█ │  │█ │██│  │█ │█ │                                        │
│ │█ │  │  │  │██│  │  │  │                                        │
│ └──┴──┴──┴──┴──┴──┴──┴──┘                                        │
│ 6/1 6/8 6/15 6/22 ...                                           │
│ [red] Açık  [green] Kapalı                                      │
│                                                                   │
│ Coverage Heatmap (Top 10 suites by case count)                  │
│ Suite Name        Heatmap        Pass Rate                      │
│ ┌──────────────┬────────────────┬──────┐                        │
│ │Auth Suite    │████████░░░░░░░░│ 89%  │                        │
│ │API Suite     │██████░░░░░░░░░░│ 75%  │                        │
│ │UI Suite      │██░░░░░░░░░░░░░░│ 25%  │                        │
│ │Integration   │████████████░░░░│ 85%  │                        │
│ └──────────────┴────────────────┴──────┘                        │
│                                                                   │
│ Test Type Distribution | Priority Breakdown | Weekly Velocity  │
│ ┌──────────────────┐ ┌──────────────────┐ ┌────────────────┐   │
│ │Manual: 80        │ │P0: 5 ▲ Critical  │ │H-3: 4 runs     │   │
│ │[████████░░]      │ │P1: 15▲ High      │ │H-2: 6 runs     │   │
│ │Automated: 35     │ │P2: 65▄ Medium    │ │H-1: 7 runs     │   │
│ │[███░░░░░░]       │ │P3: 45▄ Low       │ │This: 9 runs    │   │
│ │Exploratory: 30   │ │                  │ │Avg: 6.5/wk     │   │
│ │[███░░░░░░]       │ │                  │ │                │   │
│ └──────────────────┘ └──────────────────┘ └────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Release & Blockers Tab

```
┌─────────────────────────────────────────────────────────────────┐
│ TABS: [Overview] [Trends & Quality] [Release] [My Work] [Activity]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Release Blockers                      [Defect listesine git →]  │
│ ⓘ 5 blocker'lar                                                 │
│ ┌─────────────────────────────────────────────────┐             │
│ │ ⚠ Critical Defects: 5                           │             │
│ │   P0-001: Login form crashes on mobile          │             │
│ │                                                  │             │
│ │ ⚠ Coverage Gap: 15%                             │             │
│ │   UI module <70% requirement coverage           │             │
│ │                                                  │             │
│ │ ⚠ Flaky Tests: 3                                │             │
│ │   API test has 40% pass rate variance           │             │
│ └─────────────────────────────────────────────────┘             │
│                                                                   │
│ Release Signoff                                                  │
│ Decision: [GO / NO GO / PENDING]  (current: PENDING)            │
│                                                                   │
│ Latest Signoff:                                                  │
│ ✓ Approved — QA Lead                                            │
│   "All P0s resolved, 89% pass rate, 75% coverage"              │
│   9 Haziran 2026                                                │
│                                                                   │
│ [Onayla / Reddet] button (or form if modal)                     │
│                                                                   │
│ Regression & Release Hazırlığı                                  │
│ ┌────────────────────────────────────────────────┐             │
│ │ Koşum ilerlemesi:  [████████░░] 82%            │             │
│ │ Geçme oranı:       [████████░░░] 89%           │             │
│ │ Gereksinim kapsamı: [███████░░░░] 75%          │             │
│ └────────────────────────────────────────────────┘             │
│                                                                   │
│ Release Checklist (first 4 items):                              │
│ ┌────────────────────────┬───────────────────────┐             │
│ │ ✓ Smoke tests pass     │ Status: OK            │             │
│ │ ✓ No P0 defects        │ Metric: 0 critical    │             │
│ │ ✗ Coverage >80%        │ Status: 75% (target   │             │
│ │ ○ Security audit done  │ Status: Pending       │             │
│ └────────────────────────┴───────────────────────┘             │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4 My Work Tab

```
┌─────────────────────────────────────────────────────────────────┐
│ TABS: [Overview] [Trends & Quality] [Release] [My Work] [Activity]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ My Work                                         (3 cases · 1 def)│
│ ┌─────────────────────────┬──────────────────────────────────┐  │
│ │ Atanan Case'ler         │ Açık Defektlerim                 │  │
│ │                         │                                  │  │
│ │ [TC-045] Login UI      │✅ No open defects assigned to you.│  │
│ │           [Failed]      │                                  │  │
│ │ [TC-089] Payment flow   │                                  │  │
│ │           [Passed]      │                                  │  │
│ │ [TC-102] Dark mode      │                                  │  │
│ │           [Blocked]     │                                  │  │
│ └─────────────────────────┴──────────────────────────────────┘  │
│                                                                   │
│ Kararsız (Flaky) Testler                      (2 tests total)   │
│ ⚡ Birden fazla koşumda tutarsız sonuç (skor ≥ 0.2)           │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ [TC-234] API retry logic         43% flaky   (8 runs)   │   │
│ │ [TC-189] Cache invalidation      38% flaky  (12 runs)   │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│ İnceleme Kuyruğu                                  (5 bekleyen)  │
│ 👁 İnceleme onayı bekleyen test case'ler                       │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ [TC-301] New feature smoke test  [İnceleme Bekliyor]    │   │
│ │ [TC-302] Edge case validation    [İnceleme Bekliyor]    │   │
│ │ [TC-303] Integration test suite  [İnceleme Bekliyor]    │   │
│ │ [TC-304] Performance baseline    [İnceleme Bekliyor]    │   │
│ │ [TC-305] Security scan results   [İnceleme Bekliyor]    │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│ Test Uzmanı İş Yükü                                            │
│ ┌────────────────────────────────┐  Modül Dağılımı             │
│ │ Yasin Bulgan      [██████░░░] 45│ ┌──────────────────────┐  │
│ │ Fatih Öztürk      [████░░░░░░] 28│ │Auth Module: 32      │  │
│ │ Ayşe Kaya         [███░░░░░░░] 18│ │API Module:  28      │  │
│ │ Mehmet Yıldız     [██░░░░░░░░] 12│ │UI Module:   35      │  │
│ │ Zeynep Duran      [█░░░░░░░░░]  7│ │Payment:     18      │  │
│ └────────────────────────────────┘  │ Settings:    32     │  │
│                                      └──────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.5 Activity Tab

```
┌─────────────────────────────────────────────────────────────────┐
│ TABS: [Overview] [Trends & Quality] [Release] [My Work] [Activity]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Son Çalıştırılan Testler                                        │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Smoke Test Suite (Dev)          Running · localhost      │   │
│ │ Regression Pack (Staging)       Completed · staging.io   │   │
│ │ Mobile UI Suite               Completed · device farm    │   │
│ │ API Integration Tests          Completed · docker        │   │
│ │ Payment Flow Tests             Completed · prod          │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│ Son Güncellenen Case'ler                                        │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ TC-001 · Login scenarios          P0 · Manuel · Active   │   │
│ │ TC-045 · Profile editor form      P1 · Manuel · Draft    │   │
│ │ TC-089 · Payment checkout         P0 · Automated · Active│   │
│ │ TC-102 · Dark mode toggle         P2 · Manuel · Active   │   │
│ │ TC-234 · API error handling       P1 · Automated · Draft │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│ Eski Test Verileri                                     (8/23)   │
│ 🕐 Son 14 günde çalıştırılmamış veya hiç koşulmamış test'ler  │
│ Kapsam boşluğu riski.  [+ Tümünü gör]                         │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ P2  [TC-567] Edge case validation              23g önce   │   │
│ │ P3  [TC-568] Legacy browser compat            Hiç koşul.   │   │
│ │ P1  [TC-569] Offline sync behavior             45g önce   │   │
│ │ P2  [TC-570] Accessibility check              Hiç koşul.   │   │
│ │ P3  [TC-571] Performance regression           89g önce   │   │
│ │ P2  [TC-572] Network timeout handling        125g önce   │   │
│ │ P1  [TC-573] Concurrent user limit             52g önce   │   │
│ │ P3  [TC-574] Cache TTL verification          Hiç koşul.   │   │
│ │ + 15 daha — [tümünü gör]                                 │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│ Son Aktiviteler                                [Tümünü gör →]  │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ Y Test case created: TC-999              Yasin Bulgan    │ │
│ │                                            9 Haziran 15:23   │ │
│ │                                                              │ │
│ │ A Test case updated: TC-045              Fatih Öztürk    │ │
│ │                                            9 Haziran 14:12   │ │
│ │                                                              │ │
│ │ F Test run completed: Regression Pack   Sistem          │ │
│ │                                            9 Haziran 13:45   │ │
│ │                                                              │ │
│ │ M Defect closed: DEF-234                Mehmet Yıldız    │ │
│ │                                            9 Haziran 13:02   │ │
│ └────────────────────────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Implementation Roadmap

### Phase 1: Component Extraction (Week 1)

**Goal:** Extract all 40+ widgets into reusable components  
**Effort:** 16 hours (2 FTE days)

**Tasks:**
1. Create `/management/dashboard/_components/shared-widgets/` directory
2. Extract `StatCard` → 60 lines
3. Extract `ProjectHealthWidget` → 120 lines
4. Extract `SetupTrackerWidget` → 120 lines
5. Extract `BlockersWidget` → 100 lines
6. Extract `ReleaseSignoffWidget` → 140 lines
7. Extract `RunTrendChart` → 180 lines
8. Extract `DefectTrendMini` → 100 lines
9. Extract `CoverageHeatmap` → 140 lines
10. Extract `TestInsightsPanel` → 150 lines
11. Extract `FlakyTestsWidget` → 120 lines
12. Extract `ReviewQueueWidget` → 100 lines
13. Extract `StaleTestsWidget` → 130 lines
14. Extract `MyWorkWidget` → 200 lines
15. Extract `ActivityFeedWidget` → 100 lines
16. Extract utility helpers → 150 lines
17. Create shared types & interfaces
18. Add JSDoc + TypeScript strict

**Tests:** Unit tests for each widget (pure function tests, no hooks)

**Checklist:**
- [ ] All widgets extracted
- [ ] Props interfaces defined
- [ ] No breaking changes to existing behavior
- [ ] TypeScript strict ✓
- [ ] 0 console warnings
- [ ] 8+ widget unit tests

---

### Phase 2: Tab Architecture (Week 1-2)

**Goal:** Create tab component + refactor page.tsx  
**Effort:** 20 hours (2.5 FTE days)

**Tasks:**
1. Create `DashboardTabs.tsx` (tab nav + routing)
2. Refactor `page.tsx` → slim entry point (200 lines)
3. Create `OverviewTab.tsx` (eager, no new queries)
4. Create `TrendsTab.tsx` (lazy load 4 queries)
5. Create `ReleaseTab.tsx` (lazy load 2 queries)
6. Create `MyWorkTab.tsx` (lazy load 4 queries)
7. Create `ActivityTab.tsx` (lazy load 3 queries)
8. Implement tab routing (URL search param or hash)
9. Implement lazy mounting (only active tab loads data)
10. Update auto-refresh to refetch active tab only
11. Add tab loading skeletons
12. Test mobile responsive (768px breakpoint)

**Tests:**
- Integration test: Tab switching
- Integration test: Lazy load on click
- Integration test: Auto-refresh only active tab
- E2E: Mobile responsive tabs

**Checklist:**
- [ ] All 5 tabs render without error
- [ ] Tab switching works (URL updates)
- [ ] Lazy load queries only fire when tab active
- [ ] Auto-refresh targets active tab only
- [ ] Mobile: tabs collapse to horizontal scroll or dropdown
- [ ] 0 type errors
- [ ] Lighthouse performance: LCP <1.2s (was 2s)

---

### Phase 3: Data Loading Optimization (Week 2)

**Goal:** Smart data prefetch + caching  
**Effort:** 12 hours (1.5 FTE days)

**Tasks:**
1. Create `useTabState` hook (manage active tab)
2. Create `useLazyTabData` hook (prefetch next tab on hover)
3. Refactor `useAutoRefresh` to respect active tab
4. Add React Query `staleTime` + `cacheTime` tuning
5. Implement "prefetch on tab hover" (optional Intersection Observer)
6. Add network status check (disable refetch if offline)
7. Memoize expensive computations (staleTests, workload, etc)
8. Add data hydration SSR (optional, advanced)

**Performance Tests:**
- Initial load time (summaryFast only)
- Tab switch latency (data already cached)
- Memory footprint (tab unmount cleanup)
- Network waterfall (no parallel queries from unused tabs)

**Checklist:**
- [ ] First paint: <500ms (summaryFast only)
- [ ] Tab switch: <50ms UI + <200ms data fetch
- [ ] No memory leaks (unmount cleanup)
- [ ] Network: 3-4 requests per tab (lazy)
- [ ] Auto-refresh: only 2-3 requests every 30s (active tab)

---

### Phase 4: Mobile & Responsive (Week 2-3)

**Goal:** Mobile-first responsive design  
**Effort:** 8 hours (1 FTE day)

**Tasks:**
1. Test all tabs at 375px (iPhone SE), 768px (iPad), 1024px (desktop)
2. Tablet (768px): Collapse 4-col grid → 2-col
3. Mobile (375px): Collapse 2-col → 1-col, hide secondary info
4. Tab navigation: Desktop = horizontal buttons, Mobile = dropdown or scrollable
5. Cards: Full-width on mobile, padding adjustment
6. Charts: Scroll container for trends, reduce font sizes
7. Activity feed: List view only (no grid)
8. My Work: Stack cases + defects vertically

**Tests:**
- Responsive design tests (3 breakpoints)
- Touch target sizing (min 44px for buttons)
- Readability (font sizes on mobile)

**Checklist:**
- [ ] All tabs responsive at 375px, 768px, 1024px
- [ ] Touch targets min 44px
- [ ] No horizontal scroll on mobile
- [ ] Lighthouse mobile score: >85
- [ ] No layout shift (CLS <0.1)

---

### Phase 5: Testing & QA (Week 3)

**Goal:** Comprehensive testing before merge  
**Effort:** 16 hours (2 FTE days)

**Tasks:**
1. Unit tests: All shared-widgets (10+ tests)
2. Integration tests: Tab switching, data flow (5+ tests)
3. E2E tests: Full dashboard flow + mobile (4+ tests)
4. Visual regression: Snapshots for all tabs
5. Performance tests: Lighthouse, Bundle analysis
6. Accessibility: a11y audit (keyboard nav, ARIA)
7. Browser compat: Chrome, Safari, Firefox, Edge
8. Network throttling: 4G/3G simulation

**Checklist:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] 0 visual regressions
- [ ] Lighthouse score >85 (desktop + mobile)
- [ ] a11y: 0 critical issues
- [ ] All 4 browsers tested

---

### Phase 6: Release & Documentation (Week 3-4)

**Goal:** Merge, deploy, document  
**Effort:** 4 hours (0.5 FTE days)

**Tasks:**
1. Create PR with detailed summary
2. Code review + address feedback
3. Merge to feature/qa-system-bootstrap
4. Update CHANGELOG.md
5. Update ADR-0015: Dashboard Architecture
6. Smoke test in staging
7. Release notes: User-facing improvements
8. Monitor Sentry for errors (first week)

**Documentation:**
- ADR-0015: Tab-based dashboard rationale
- Component API docs for shared-widgets
- Performance baseline (before/after metrics)

**Checklist:**
- [ ] PR merged
- [ ] 0 merge conflicts
- [ ] Staging deployment successful
- [ ] No new Sentry alerts
- [ ] Documentation updated

---

## 6. Risk & Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Breaking Change (UX)** — Users expect single-page scrolling | Medium | A/B test: Keep Overview as default, other tabs optional. Update quick tour UI. |
| **Data Load Timing** — Tab 1 render blocked if summaryFast slow | High | Add timeout (2s) → fallback to client-side calc. Pre-warm summaryFast on login. |
| **Mobile Usability** — Tab nav unclear on small screens | Medium | Use dropdown or sticky tab nav. Add tab labels + icons. |
| **Memory Leak** — Lazy-mounted tabs don't cleanup queries | Medium | Use React Query's `enabled` flag. Test with DevTools Memory profiler. |
| **Stale Data** — User clicks old tab, data is 5min old | Low | Show "Last updated 5m ago" label. Add "Refresh now" button per tab. |
| **Performance Regression** — Tab switching feels slow | Medium | Benchmark before/after. Profile with Chrome DevTools. Add loading skeleton. |
| **Test Coverage Gaps** — New component structure not well-tested | Medium | Require >80% coverage. Add snapshot tests. E2E for critical flows. |

---

## 7. Success Metrics

### Performance
- **First Paint:** <400ms (was 1.2s)
- **LCP:** <1.2s (was 2s)
- **CLS:** <0.1
- **Network:** 3-5 requests per tab (was 11 parallel)

### UX
- **Tab Switch Latency:** <200ms (perceived instant)
- **Mobile Usability:** >85 Lighthouse score
- **Task Completion:** "Find my assigned cases" <10s (was 30s scroll)

### Code Quality
- **Bundle Size:** -150KB (was 950KB)
- **Component Reuse:** 40+ widgets → 15 reusable components
- **Type Safety:** TypeScript strict ✓
- **Test Coverage:** >85% (was 65%)

### User Adoption
- **Engagement:** Time on dashboard (measure via analytics)
- **Support Tickets:** Reduction in "How do I find X?" issues
- **NPS:** Dashboard usability feedback

---

## 8. File Manifest & Summary

### Files to Create
```
/management/dashboard/
├── _components/
│   ├── DashboardTabs.tsx
│   ├── dashboard-tabs/
│   │   ├── OverviewTab.tsx
│   │   ├── TrendsTab.tsx
│   │   ├── ReleaseTab.tsx
│   │   ├── MyWorkTab.tsx
│   │   └── ActivityTab.tsx
│   ├── shared-widgets/
│   │   ├── HeroMetricCard.tsx
│   │   ├── ProjectHealthWidget.tsx
│   │   ├── SetupTrackerWidget.tsx
│   │   ├── StatCard.tsx
│   │   ├── BlockersWidget.tsx
│   │   ├── ReleaseSignoffWidget.tsx
│   │   ├── RunTrendChart.tsx
│   │   ├── DefectTrendMini.tsx
│   │   ├── CoverageHeatmap.tsx
│   │   ├── TestInsightsPanel.tsx
│   │   ├── FlakyTestsWidget.tsx
│   │   ├── ReviewQueueWidget.tsx
│   │   ├── StaleTestsWidget.tsx
│   │   ├── MyWorkWidget.tsx
│   │   ├── ActivityFeedWidget.tsx
│   │   ├── MiniBar.tsx
│   │   ├── HorizBar.tsx
│   │   ├── AutoRefreshBadge.tsx
│   │   └── EmptyState.tsx
│   └── utils/
│       ├── dashboard-helpers.ts
│       ├── dashboard-hooks.ts
│       └── dashboard-types.ts
└── page.tsx (refactored)
```

### Files to Modify
```
/management/
├── page.tsx (1690 → 200 lines, extract all widgets)
└── _components/
    ├── QuickSetupWizard.tsx (may need mobile responsive update)
    └── NotificationBell.tsx (already exists, reuse)
```

### Files to Add (Tests)
```
/management/dashboard/__tests__/
├── page.test.tsx (routing, eager load)
├── DashboardTabs.test.tsx (tab switching)
├── OverviewTab.test.tsx (renders without error)
├── TrendsTab.test.tsx (lazy load trigger)
├── ReleaseTab.test.tsx (blockers, signoff)
├── MyWorkTab.test.tsx (my work, flaky, review)
├── ActivityTab.test.tsx (activity feed, stale)
└── shared-widgets/ (10+ widget unit tests)
```

---

## 9. Next Steps

1. **Week 1 Mon:** Phase 1 kickoff — Create component extraction plan
2. **Week 1 Wed:** Phase 1 complete — All widgets extracted
3. **Week 2 Mon:** Phase 2 kickoff — Tab architecture + OverviewTab
4. **Week 2 Wed:** Phase 2 complete — All 5 tabs rendering
5. **Week 2 Fri:** Phase 3 complete — Data loading optimized
6. **Week 3 Mon:** Phase 4 & 5 — Mobile testing + QA
7. **Week 3 Fri:** Phase 6 — PR created, ready for review
8. **Week 4 Mon:** Release — Merge + deploy to staging

**Effort Estimate:** 4-5 FTE weeks (80 hours total)  
**Dependencies:** None (frontend-only, no API changes)  
**Rollback Plan:** Git revert to commit before refactor (simple, linear change)

---

## 10. Approval Checklist

- [ ] Product: UX acceptable (tab-based, mobile-friendly)
- [ ] Engineering: Architecture approved (no breaking changes)
- [ ] QA: Test strategy approved (coverage >80%)
- [ ] DevOps: Deployment plan approved (no migration needed)
- [ ] Design: Mobile responsive design approved (Figma review)

---

**Created:** 2026-06-09  
**Author:** Claude Code Analysis  
**Status:** Ready for Phase 1 Kickoff
