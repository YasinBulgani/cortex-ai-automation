# Dashboard Refactoring — Implementation Checklist

**Project:** Cortex Neurex Management Dashboard  
**Phase:** 1-6 (4-5 weeks)  
**Start Date:** 2026-06-10 (estimated)  
**Status:** Planning Complete → Ready to Implement

---

## Phase 1: Component Extraction (Week 1, Days 1-3)

**Goal:** Extract all 40+ inline widgets into reusable components  
**Effort:** 16 hours  
**Team:** 1-2 Frontend Engineers

### 1.1 Setup & Scaffolding

- [ ] Create directory structure:
  ```
  /management/dashboard/_components/
  ├── shared-widgets/
  │   └── .gitkeep
  ├── dashboard-tabs/
  │   └── .gitkeep
  └── utils/
      └── .gitkeep
  ```
- [ ] Create TypeScript interfaces file (`dashboard-types.ts`)
- [ ] Create helpers file (`dashboard-helpers.ts`)
- [ ] Create hooks file (`dashboard-hooks.ts`)
- [ ] Create barrel exports (`shared-widgets/index.ts`)

### 1.2 Extract Simple Components (No hooks)

**Time per component:** 30-45 min (copy → refactor → test)

- [ ] `HeroMetricCard.tsx` (80 lines)
  - [ ] Props interface
  - [ ] Component render
  - [ ] Unit test (2 cases)
  - [ ] Storybook (optional)

- [ ] `StatCard.tsx` (60 lines)
  - [ ] Props interface
  - [ ] Component render
  - [ ] Unit test (3 cases: with/without href, tone variants)

- [ ] `MiniBar.tsx` (40 lines)
  - [ ] Props interface
  - [ ] Component render
  - [ ] Unit test (1 case)

- [ ] `HorizBar.tsx` (40 lines)
  - [ ] Props interface
  - [ ] Component render
  - [ ] Unit test (1 case)

- [ ] `AutoRefreshBadge.tsx` (60 lines)
  - [ ] Props interface
  - [ ] useEffect countdown loop
  - [ ] Unit test (countdown logic)

- [ ] `EmptyState.tsx` (60 lines)
  - [ ] Props interface
  - [ ] Component render + 2 CTA buttons
  - [ ] Unit test (1 case)

**Checklist for each:**
- [ ] Copy relevant code from page.tsx
- [ ] Create `.tsx` file with component
- [ ] Define Props interface
- [ ] Add JSDoc comments
- [ ] Create `.test.tsx` file (2-3 test cases)
- [ ] Run `npm test -- --testPathPattern=SharedWidget`
- [ ] Verify 0 console warnings
- [ ] Type check: `npx tsc --noEmit`

### 1.3 Extract Chart Components (SVG/Canvas)

**Time per component:** 1-1.5 hours (includes logic review)

- [ ] `RunTrendChart.tsx` (180 lines)
  - [ ] Props interface + edge cases
  - [ ] SVG rendering logic
  - [ ] Extract stat calculations (avg, trend, etc)
  - [ ] Unit test (3 cases: <2 points, all green, mixed)
  - [ ] Visual regression snapshot

- [ ] `DefectTrendMini.tsx` (100 lines)
  - [ ] Props interface
  - [ ] Weekly bucket logic
  - [ ] SVG stacked bar rendering
  - [ ] Unit test (2 cases: no data, data)

### 1.4 Extract Data-Dependent Widgets (With hooks)

**Time per component:** 1-1.5 hours

- [ ] `ProjectHealthWidget.tsx` (120 lines)
  - [ ] Props interface (4 inputs)
  - [ ] Score calculation logic
  - [ ] Color coding rules
  - [ ] Criteria display
  - [ ] Unit test (4 cases: each health threshold)

- [ ] `SetupTrackerWidget.tsx` (120 lines)
  - [ ] Props interface (6 inputs)
  - [ ] Completion calculation
  - [ ] Success vs. in-progress states
  - [ ] Unit test (3 cases: 0%, 50%, 100%)

- [ ] `BlockersWidget.tsx` (100 lines)
  - [ ] Props interface
  - [ ] Conditional rendering (no blockers vs. with)
  - [ ] Link to defect list
  - [ ] Unit test (2 cases)

- [ ] `ReleaseSignoffWidget.tsx` (140 lines)
  - [ ] Props interface
  - [ ] Form toggle state
  - [ ] Hook usage: useReleaseSignoffs, useCreateReleaseSignoff
  - [ ] Form submission logic
  - [ ] Unit test (3 cases: view only, form open, loading)
  - [ ] Integration test (form submit)

### 1.5 Extract Panel Components (Complex layouts)

**Time per component:** 1.5-2 hours

- [ ] `CoverageHeatmap.tsx` (140 lines)
  - [ ] Props interface
  - [ ] Suite aggregation logic
  - [ ] Top 10 filtering
  - [ ] Stacked bar calculation
  - [ ] Unit test (2 cases: with/without data)

- [ ] `TestInsightsPanel.tsx` (150 lines)
  - [ ] Props interface (cases + runs)
  - [ ] Type/Priority/Velocity computation
  - [ ] 3-column layout (responsive)
  - [ ] Child: 3× HorizBar + velocity chart
  - [ ] Unit test (2 cases)

### 1.6 Extract List/Feature Widgets

**Time per component:** 1-1.5 hours

- [ ] `FlakyTestsWidget.tsx` (120 lines)
  - [ ] Props interface
  - [ ] List rendering + click handler
  - [ ] Score color gradient
  - [ ] Loading skeleton
  - [ ] Unit test (3 cases: loading, empty, data)

- [ ] `ReviewQueueWidget.tsx` (100 lines)
  - [ ] Props interface
  - [ ] List rendering + click handler
  - [ ] Badge badge count
  - [ ] Empty state
  - [ ] Unit test (2 cases)

- [ ] `StaleTestsWidget.tsx` (130 lines)
  - [ ] Props interface
  - [ ] Days-since calculation
  - [ ] Priority color coding
  - [ ] "View all" link
  - [ ] Unit test (2 cases: no stale, with stale)

- [ ] `MyWorkWidget.tsx` (200 lines)
  - [ ] Props interface
  - [ ] 2-column layout
  - [ ] Status badge logic (cases)
  - [ ] Severity color coding (defects)
  - [ ] Empty states (per column)
  - [ ] Unit test (4 cases: both empty, mixed, loading)

- [ ] `ActivityFeedWidget.tsx` (100 lines)
  - [ ] Props interface
  - [ ] Actor name display
  - [ ] Date formatting
  - [ ] Truncation handling
  - [ ] Unit test (2 cases)

### 1.7 Utility Functions & Helpers

- [ ] Create `dashboard-helpers.ts` (150 lines)
  - [ ] `STATUS_TR` mapping (export from page.tsx)
  - [ ] `tr(value, fallback)` function
  - [ ] `asText(value, fallback)` function
  - [ ] `getPriorityColor(priority)` function
  - [ ] `isDefectClosed(status)` function
  - [ ] `formatShortDate(date)` function
  - [ ] Unit test (6 test cases)

- [ ] Create `dashboard-hooks.ts` (placeholder)
  - [ ] `useTabState()` hook (stub)
  - [ ] `useLazyTabData()` hook (stub)
  - [ ] `useAutoRefresh()` hook (stub)
  - [ ] `useStaleTests()` hook (stub)
  - [ ] (Will implement in Phase 2-3)

- [ ] Create `dashboard-types.ts`
  - [ ] Export all TypeScript interfaces
  - [ ] Document prop requirements
  - [ ] Add JSDoc comments

### 1.8 Verification & Cleanup

- [ ] Run full test suite: `npm test -- dashboard`
  - [ ] Target: All tests pass
  - [ ] Coverage: >80% for extracted components

- [ ] TypeScript strict mode: `npx tsc --noEmit`
  - [ ] 0 type errors
  - [ ] 0 warnings

- [ ] ESLint check: `npx eslint _components/`
  - [ ] 0 violations

- [ ] Bundle size check: `npm run build`
  - [ ] No significant increase (extracted code = same size)

- [ ] Visual verification:
  - [ ] No component renders in isolation (storybook or test)
  - [ ] CSS classes applied correctly
  - [ ] No layout shifts

### Phase 1 Sign-Off

- [ ] All 19 components extracted
- [ ] 25+ unit tests pass
- [ ] 0 type errors
- [ ] 0 ESLint violations
- [ ] Page.tsx still works (widgets not yet replaced)
- [ ] PR created + code review

**Estimated Hours:** 16  
**Buffer:** 20% → 19.2 hours (plan 20 hours)

---

## Phase 2: Tab Architecture (Week 1-2, Days 4-8)

**Goal:** Create tab structure + refactor page.tsx  
**Effort:** 20 hours

### 2.1 Create DashboardTabs Container

- [ ] Create `DashboardTabs.tsx` (250 lines)
  - [ ] Props interface (activeTab, onTabChange, data props)
  - [ ] Tab navigation UI (5 buttons)
  - [ ] Active tab highlight logic
  - [ ] Lazy child mounting (conditional render)
  - [ ] Refresh button (refetch active tab)
  - [ ] Unit test (4 cases: tab switch, active highlight, refresh)
  - [ ] Responsive design (mobile dropdown at <768px)

### 2.2 Create Tab Components (Directories)

- [ ] Create `/dashboard-tabs/` directory
- [ ] Create `index.ts` barrel export

### 2.3 OverviewTab (No New Queries)

- [ ] Create `OverviewTab.tsx` (350 lines)
  - [ ] Props interface (uses page.tsx data)
  - [ ] Layout: Hero + Health + Setup + Cards + Actions
  - [ ] Import: HeroMetricCard, ProjectHealthWidget, SetupTrackerWidget, StatCard (8×)
  - [ ] Import: Quick Actions button grid
  - [ ] Responsive: 4-col grid → 2-col → 1-col
  - [ ] Unit test (1 case: renders with data)
  - [ ] Visual regression (snapshot)

### 2.4 TrendsTab (Lazy Load)

- [ ] Create `TrendsTab.tsx` (280 lines)
  - [ ] Props interface (projectId, mpid)
  - [ ] useManagementRunTrend hook (optional if already in page)
  - [ ] useManagementDefects hook (optional)
  - [ ] useManagementRepository hook (optional, for heatmap suites)
  - [ ] useManagementRuns hook (optional, for insights)
  - [ ] Layout: RunTrendChart + DefectTrendMini + CoverageHeatmap + TestInsightsPanel
  - [ ] Loading state: skeleton per widget
  - [ ] Error handling: graceful fallback
  - [ ] Unit test (2 cases: loading, with data)

### 2.5 ReleaseTab (Lazy Load)

- [ ] Create `ReleaseTab.tsx` (220 lines)
  - [ ] Props interface (projectId, mpid)
  - [ ] useReleaseReport hook (optional)
  - [ ] useManagementPlans hook (optional)
  - [ ] Layout: Blockers + Signoff + Regression Readiness + Checklist
  - [ ] Loading states
  - [ ] Error handling
  - [ ] Unit test (2 cases: loading, with data)

### 2.6 MyWorkTab (Lazy Load)

- [ ] Create `MyWorkTab.tsx` (300 lines)
  - [ ] Props interface (projectId, mpid, currentUserId)
  - [ ] useManagementFlakyTests hook (lazy)
  - [ ] useReviewQueue hook (lazy)
  - [ ] useManagementRuns hook (optional)
  - [ ] useManagementRepository hook (optional)
  - [ ] Pass userIdMap, currentUserId from page
  - [ ] Layout: MyWork + Flaky + Review Queue + Workload + ModuleDistribution
  - [ ] Loading states
  - [ ] Error handling
  - [ ] Unit test (2 cases: loading, with data)

### 2.7 ActivityTab (Lazy Load)

- [ ] Create `ActivityTab.tsx` (200 lines)
  - [ ] Props interface (projectId, mpid, userIdMap)
  - [ ] useManagementAuditEvents hook (lazy, limit=10)
  - [ ] useManagementRuns hook (optional, for latest)
  - [ ] useManagementRepository hook (optional, for latest cases)
  - [ ] Layout: LatestRuns + LatestCases + StaleTests + ActivityFeed
  - [ ] Loading states
  - [ ] Error handling
  - [ ] Unit test (2 cases: loading, with data)

### 2.8 Refactor page.tsx

- [ ] Backup original (git stash or branch)
- [ ] Remove all widget inline code (keep imports from new files)
- [ ] New structure (200 lines):
  ```typescript
  export default function ManagementDashboardPage() {
    // 1. Router setup & data loading (50 lines)
    const projectId = useRouteParam("projectId");
    const mpid = useManagementProjectId(projectId);
    const summaryFast = useManagementDashboardSummary(mpid);
    const profile = useProfile();
    
    // 2. Tab state (10 lines)
    const [activeTab, setActiveTab] = useState("overview");
    
    // 3. Error boundary (20 lines)
    if (hasError && !summaryFast.data) return <ErrorFallback />;
    
    // 4. Render (120 lines)
    return (
      <div className="min-h-full space-y-5 bg-surface-base px-6 py-6">
        {/* Header */}
        {/* DashboardTabs wrapper */}
        {/* Conditional lazy render per tab */}
      </div>
    );
  }
  ```
- [ ] Migrate all queries to tab components (remove from page.tsx)
- [ ] Keep only: summaryFast, profile, projectId, mpid routing
- [ ] Update imports to use new components

### 2.9 Test Tab Navigation

- [ ] Unit test: Tab switching
  ```typescript
  it("switches tabs on button click", () => {
    render(<DashboardTabs activeTab="overview" onTabChange={...} />);
    click tab "Trends";
    expect(onTabChange).toHaveBeenCalledWith("trends");
  });
  ```

- [ ] Unit test: Lazy render
  ```typescript
  it("only renders active tab", () => {
    render(<DashboardTabs activeTab="overview" ... />);
    expect(screen.getByText("Overview Tab")).toBeInTheDocument();
    expect(screen.queryByText("Trends Tab")).not.toBeInTheDocument();
  });
  ```

- [ ] Integration test: Full dashboard
  ```typescript
  it("loads data and switches tabs", async () => {
    render(<ManagementDashboardPage projectId="p-123" />);
    await waitFor(() => screen.getByText("Project Health"));
    click("Trends");
    await waitFor(() => screen.getByText("Test Koşum Trendi"));
  });
  ```

### 2.10 Mobile Responsive Testing

- [ ] Test at 375px: Tabs collapse to dropdown
- [ ] Test at 768px: Tabs horizontal, cards 2-col
- [ ] Test at 1024px: Full layout

### Phase 2 Sign-Off

- [ ] All 5 tab components created
- [ ] page.tsx refactored to 200 lines
- [ ] Tab switching works
- [ ] Lazy loading works (verify via Network tab)
- [ ] 5+ integration tests pass
- [ ] 0 type errors
- [ ] 0 ESLint violations
- [ ] Mobile responsive verified

**Estimated Hours:** 20  
**Buffer:** 25% → 25 hours (plan 25 hours)

---

## Phase 3: Data Loading Optimization (Week 2, Days 9-10)

**Goal:** Smart prefetch + refetch optimization  
**Effort:** 12 hours

### 3.1 Create useTabState Hook

- [ ] Create hook in `dashboard-hooks.ts`
  ```typescript
  function useTabState(): [activeTab: string, setActiveTab: (tab: string) => void] {
    // Option 1: React state (simpler)
    // Option 2: URL search param (shareable)
    // Implement Option 1 for MVP
  }
  ```
- [ ] Test: Tab state persists across re-renders

### 3.2 Create useLazyTabData Hook

- [ ] Create hook in `dashboard-hooks.ts`
  ```typescript
  function useLazyTabData(tabName: string) {
    // Prefetch data when tab is about to be viewed
    // Use React Query's `prefetchQuery`
    // Trigger on mouse hover (optional optimization)
  }
  ```
- [ ] Implement for each lazy tab
- [ ] Test: Data prefetches before tab click

### 3.3 Optimize useAutoRefresh

- [ ] Move from page.tsx to `dashboard-hooks.ts`
- [ ] Modify to only refetch active tab queries:
  ```typescript
  useEffect(() => {
    if (activeTab !== "overview") return; // Only refresh active
    const id = setInterval(() => {
      summaryFast.refetch(); // Only this query
    }, REFETCH_INTERVAL);
    return () => clearInterval(id);
  }, [activeTab]);
  ```
- [ ] Apply per tab in each component

### 3.4 Implement useStaleTests Hook

- [ ] Extract from page.tsx logic to hook
- [ ] Memoize: useMemo + useCallback
- [ ] Test: Returns correct stale tests (14 days)

### 3.5 Tune React Query Settings

- [ ] Review all useQuery calls for staleTime + cacheTime:
  ```typescript
  // Current: no staleTime
  // New:
  const summaryFast = useQuery({
    queryKey: ["management", "summary", projectId],
    queryFn: ...,
    staleTime: 30_000,      // 30s (auto-refresh interval)
    cacheTime: 5 * 60_000,  // 5min
    enabled: !!projectId,
  });
  ```
- [ ] Set per query (eager vs. lazy)

### 3.6 Add Network Status Check

- [ ] Create hook: `useOnline()`
- [ ] Disable auto-refresh if offline
- [ ] Show "Offline" indicator in refresh badge

### 3.7 Memoization Audit

- [ ] Review expensive computations:
  - [ ] staleTests calculation: wrap useMemo
  - [ ] workload calculation: wrap useMemo
  - [ ] moduleDistribution: wrap useMemo
  - [ ] userIdMap: wrap useMemo
  - [ ] Event handlers: wrap useCallback

### 3.8 Performance Benchmarks

- [ ] Before:
  - [ ] First paint: 2000ms
  - [ ] TTI: 2500ms
  - [ ] Requests: 11 parallel
  - [ ] Memory: ~50MB

- [ ] After (target):
  - [ ] First paint: <500ms ✓
  - [ ] TTI: <1000ms ✓
  - [ ] Requests: 3-5 per tab ✓
  - [ ] Memory: ~30MB ✓

- [ ] Measure with:
  ```bash
  npm run build
  npm run start
  # Chrome DevTools → Performance → Record → Navigate
  # Check LCP, FID, CLS
  ```

### Phase 3 Sign-Off

- [ ] useTabState hook created + tested
- [ ] useLazyTabData hook created + tested
- [ ] useAutoRefresh refactored (active tab only)
- [ ] useStaleTests hook created + tested
- [ ] React Query staleTime/cacheTime tuned
- [ ] Memoization added to expensive computations
- [ ] Performance benchmarks show improvement:
  - [ ] First paint: <500ms
  - [ ] Requests per tab: 3-5
- [ ] 0 type errors

**Estimated Hours:** 12  
**Buffer:** 15% → 13.8 hours (plan 14 hours)

---

## Phase 4: Mobile & Responsive (Week 2-3, Days 10-12)

**Goal:** Mobile-first responsive design  
**Effort:** 8 hours

### 4.1 Responsive Testing Setup

- [ ] Create test breakpoints:
  - [ ] Mobile: 375px (iPhone SE)
  - [ ] Tablet: 768px (iPad)
  - [ ] Desktop: 1024px (standard)
  - [ ] Desktop Large: 1440px (wide screen)

- [ ] Use DevTools device emulation or Playwright:
  ```bash
  npx playwright test --device="Pixel 5" dashboard/page.test.ts
  npx playwright test --device="iPad Pro" dashboard/page.test.ts
  ```

### 4.2 OverviewTab Mobile Responsiveness

- [ ] Hero Metrics: 4-col → 2-col → 1-col
- [ ] Health + Setup: Full-width on mobile
- [ ] StatCards: 4-col → 2-col → 1-col
- [ ] Quick Actions: Wrap, vertical scroll
- [ ] Test all breakpoints

### 4.3 Trends Tab Mobile Responsiveness

- [ ] Charts: Add scroll container for mobile
- [ ] RunTrendChart: Reduce font sizes
- [ ] DefectTrendMini: Scale down bar heights
- [ ] CoverageHeatmap: Single column
- [ ] TestInsightsPanel: Stack 3 columns vertically

### 4.4 Release Tab Mobile Responsiveness

- [ ] Blockers: Full-width
- [ ] Signoff: Form fields stack
- [ ] Checklist: 2-col → 1-col

### 4.5 MyWorkTab Mobile Responsiveness

- [ ] MyWork: Cases + defects stack vertically
- [ ] Flaky/Review: Full-width lists
- [ ] Workload: Single column bars
- [ ] ModuleDistribution: Single column

### 4.6 ActivityTab Mobile Responsiveness

- [ ] Lists: Full-width, single column
- [ ] Dates: Shortened format
- [ ] Activity feed: Reduce avatar size

### 4.7 Tab Navigation Mobile

- [ ] Desktop: Horizontal button tabs
- [ ] Mobile: Dropdown select or scrollable tabs
- [ ] Implement in DashboardTabs.tsx:
  ```tsx
  {isMobile ? (
    <select onChange={(e) => setActiveTab(e.target.value)}>
      <option value="overview">Overview</option>
      ...
    </select>
  ) : (
    <div className="flex gap-2">
      {/* Tab buttons */}
    </div>
  )}
  ```

### 4.8 Touch Target Sizing

- [ ] All buttons: min 44×44px (iOS guideline)
- [ ] Links: min 44×48px
- [ ] Verify with axe DevTools

### 4.9 Readability Check

- [ ] Font sizes on mobile: No <12px
- [ ] Line height: >1.4
- [ ] Contrast ratio: >4.5:1 (WCAG AA)

### 4.10 Lighthouse Mobile Score

- [ ] Target: >85
- [ ] Run: `npm run build && npx lighthouse http://localhost:3000 --view`
- [ ] Check:
  - [ ] LCP: <2.5s
  - [ ] FID: <100ms
  - [ ] CLS: <0.1

### Phase 4 Sign-Off

- [ ] All tabs responsive at 375px/768px/1024px
- [ ] Touch targets min 44px
- [ ] No horizontal scroll on mobile
- [ ] Tab navigation works on mobile (dropdown or scroll)
- [ ] Lighthouse mobile score >85
- [ ] 4+ responsive design tests pass
- [ ] 0 axe a11y violations

**Estimated Hours:** 8  
**Buffer:** 20% → 9.6 hours (plan 10 hours)

---

## Phase 5: Testing & QA (Week 3, Days 13-17)

**Goal:** Comprehensive testing + quality gates  
**Effort:** 16 hours

### 5.1 Unit Tests

**Target:** >80% coverage for all components

- [ ] Shared widgets (15 components):
  ```bash
  npm test -- dashboard/_components/shared-widgets/
  # Target: 15+ tests, 80%+ coverage
  ```

- [ ] Checklist:
  - [ ] StatCard.test.tsx (3 cases)
  - [ ] ProjectHealthWidget.test.tsx (4 cases)
  - [ ] SetupTrackerWidget.test.tsx (3 cases)
  - [ ] BlockersWidget.test.tsx (2 cases)
  - [ ] RunTrendChart.test.tsx (3 cases)
  - [ ] DefectTrendMini.test.tsx (2 cases)
  - [ ] CoverageHeatmap.test.tsx (2 cases)
  - [ ] TestInsightsPanel.test.tsx (2 cases)
  - [ ] FlakyTestsWidget.test.tsx (3 cases)
  - [ ] ReviewQueueWidget.test.tsx (2 cases)
  - [ ] StaleTestsWidget.test.tsx (2 cases)
  - [ ] MyWorkWidget.test.tsx (4 cases)
  - [ ] ActivityFeedWidget.test.tsx (2 cases)
  - [ ] AutoRefreshBadge.test.tsx (2 cases)
  - [ ] dashboard-helpers.test.ts (6 cases)

### 5.2 Integration Tests

**Target:** All tab flows work end-to-end

- [ ] Tab switching:
  ```typescript
  it("switches between tabs without errors", async () => {
    render(<ManagementDashboardPage projectId="p-123" />);
    for (const tab of ["overview", "trends", "release", "mywork", "activity"]) {
      click(tab);
      await waitFor(() => {
        expect(screen.getByText(/tab content/i)).toBeInTheDocument();
      });
    }
  });
  ```

- [ ] Lazy data loading:
  ```typescript
  it("loads tab data on click", async () => {
    render(<ManagementDashboardPage projectId="p-123" />);
    expect(screen.queryByText("Test Koşum Trendi")).not.toBeInTheDocument();
    click("Trends");
    await waitFor(() => {
      expect(screen.getByText("Test Koşum Trendi")).toBeInTheDocument();
    });
  });
  ```

- [ ] Auto-refresh active tab only:
  ```typescript
  it("only refreshes active tab data", async () => {
    // Setup: Mock queries
    // Act: Wait 30s
    // Verify: Only active tab query refetched
  });
  ```

- [ ] Checklist:
  - [ ] page.tsx integration test (1 case)
  - [ ] DashboardTabs.test.tsx (4 cases)
  - [ ] OverviewTab.test.tsx (1 case)
  - [ ] TrendsTab.test.tsx (2 cases)
  - [ ] ReleaseTab.test.tsx (2 cases)
  - [ ] MyWorkTab.test.tsx (2 cases)
  - [ ] ActivityTab.test.tsx (2 cases)

### 5.3 E2E Tests (if using Playwright/Cypress)

**Target:** Critical user journeys

- [ ] Complete flow:
  ```
  1. Load dashboard
  2. Verify Overview tab renders
  3. Click Trends tab
  4. Wait for data load
  5. Verify Trends content
  6. Click Release tab
  7. Scroll down
  8. Verify mobile responsive (at 375px)
  ```

- [ ] Checklist (4 E2E tests):
  - [ ] Dashboard load + Overview (happy path)
  - [ ] Tab switching + lazy load
  - [ ] Mobile responsive flow
  - [ ] Auto-refresh behavior

### 5.4 Visual Regression Tests

**Target:** No unexpected visual changes

- [ ] Snapshot tests for all 5 tabs
- [ ] Update snapshots if intentional changes
- [ ] Checklist:
  - [ ] OverviewTab snapshot
  - [ ] TrendsTab snapshot
  - [ ] ReleaseTab snapshot
  - [ ] MyWorkTab snapshot
  - [ ] ActivityTab snapshot
  - [ ] Mobile layout snapshot (375px)
  - [ ] Tablet layout snapshot (768px)

### 5.5 Accessibility Testing

**Target:** WCAG AA compliance (Level AA)

- [ ] Manual audit with axe DevTools:
  ```bash
  npm run build && npx axe http://localhost:3000/p/proj-123/management/dashboard
  ```

- [ ] Checklist:
  - [ ] No critical axe violations
  - [ ] Keyboard navigation (Tab through all tabs)
  - [ ] Color contrast ratio >4.5:1
  - [ ] ARIA labels on interactive elements
  - [ ] Screen reader testing (Safari VoiceOver or NVDA)

### 5.6 Performance Tests

**Target:** Lighthouse score >85 (desktop + mobile)

- [ ] Run Lighthouse:
  ```bash
  npm run build
  npm run start
  npx lighthouse http://localhost:3000 --view
  npx lighthouse http://localhost:3000 --emulated-form-factor=mobile --view
  ```

- [ ] Bundle analysis:
  ```bash
  npm run build
  npm run analyze  # If webpack-bundle-analyzer configured
  ```

- [ ] Checklist:
  - [ ] Desktop Lighthouse: >85 (Performance, Accessibility, Best Practices, SEO)
  - [ ] Mobile Lighthouse: >85
  - [ ] LCP: <2.5s
  - [ ] FID: <100ms
  - [ ] CLS: <0.1
  - [ ] Bundle size: No regression (or <5% increase)

### 5.7 Browser Compatibility

**Target:** Latest 2 versions of major browsers

- [ ] Chrome 125+
- [ ] Safari 17+
- [ ] Firefox 124+
- [ ] Edge 125+

- [ ] Manual testing matrix (4 browsers × 3 breakpoints):
  ```
  Browser | 375px | 768px | 1024px
  --------|-------|-------|-------
  Chrome  | ✓     | ✓     | ✓
  Safari  | ✓     | ✓     | ✓
  Firefox | ✓     | ✓     | ✓
  Edge    | ✓     | ✓     | ✓
  ```

### 5.8 Network Throttling

**Target:** Acceptable performance on 4G/3G

- [ ] Simulate in Chrome DevTools:
  - [ ] Offline: Graceful degradation
  - [ ] 3G: Page load <5s (LCP <3s)
  - [ ] 4G: Page load <2s (LCP <1.5s)

- [ ] Checklist:
  - [ ] Tab switch on 3G: <2s perceived delay
  - [ ] Auto-refresh disabled when offline
  - [ ] Error messages clear

### Phase 5 Sign-Off

- [ ] All unit tests pass: npm test -- dashboard
- [ ] All integration tests pass
- [ ] All E2E tests pass (if configured)
- [ ] Visual regressions: 0 unexpected changes
- [ ] Accessibility: 0 critical axe violations
- [ ] Lighthouse (desktop): >85
- [ ] Lighthouse (mobile): >85
- [ ] Browser compat: 4 browsers × 3 breakpoints
- [ ] Network throttling: Acceptable

**Test Coverage Summary:**
```
dashboard/
├── __tests__/
│   ├── page.test.tsx ..................... 1 integration test
│   ├── DashboardTabs.test.tsx ............ 4 unit tests
│   ├── shared-widgets/
│   │   ├── StatCard.test.tsx ............ 3 tests
│   │   ├── ProjectHealthWidget.test.tsx . 4 tests
│   │   └── ... (13 more) ................ 30 tests
│   └── dashboard-tabs/
│       ├── OverviewTab.test.tsx ......... 1 test
│       ├── TrendsTab.test.tsx ........... 2 tests
│       └── ... (3 more) ................. 9 tests
│
├── e2e/
│   ├── dashboard.e2e.ts ................. 4 scenarios
│   └── dashboard.mobile.e2e.ts .......... 2 scenarios (optional)
│
└── __snapshots__/
    ├── OverviewTab.snap.tsx ............. 3 snapshots (mobile/tablet/desktop)
    ├── TrendsTab.snap.tsx ............... 3 snapshots
    └── ... (3 more) ..................... 15 snapshots

Total: 50+ tests, 18 snapshots, 80%+ coverage
```

**Estimated Hours:** 16  
**Buffer:** 25% → 20 hours (plan 20 hours)

---

## Phase 6: Release & Documentation (Week 3-4, Days 18-20)

**Goal:** Merge, deploy, document  
**Effort:** 4 hours

### 6.1 Pre-Merge Checklist

- [ ] All tests passing locally: `npm test -- dashboard`
- [ ] Type check: `npx tsc --noEmit` → 0 errors
- [ ] ESLint: `npx eslint _components/` → 0 violations
- [ ] Build: `npm run build` → no errors
- [ ] Manual smoke test (5 min):
  - [ ] Load dashboard → Overview renders
  - [ ] Click Trends → data loads
  - [ ] Click Release → data loads
  - [ ] Click MyWork → data loads
  - [ ] Click Activity → data loads
  - [ ] Mobile (375px) → responsive works

### 6.2 Create Pull Request

- [ ] Title: "Refactor: Tab-based dashboard architecture"
- [ ] Description:
  ```markdown
  ## Summary
  - Extract 40+ inline widgets into 19 reusable components
  - Implement tab-based dashboard (5 tabs: Overview, Trends, Release, MyWork, Activity)
  - Optimize data loading: eager (overview) + lazy (other tabs)
  - Auto-refresh only active tab (reduce API calls 50%)
  - Mobile responsive design (375px/768px/1024px tested)

  ## Breaking Changes
  None — UX remains similar, tabs added as enhancement

  ## Performance Improvement
  - First paint: 2000ms → 400ms (5× faster)
  - Requests per session: 11 parallel → 3-5 per tab
  - Bundle size: Same (refactoring only)
  - Mobile Lighthouse: 70 → 88

  ## Testing
  - 50+ unit tests (80%+ coverage)
  - 9+ integration tests
  - 4+ E2E tests
  - Visual regression: 18 snapshots
  - Accessibility: 0 critical violations
  - Browser compat: Chrome, Safari, Firefox, Edge

  ## Related Issues
  - Closes: #XXXX (if applicable)

  ## Checklist
  - [x] Tests pass locally
  - [x] Type safe (0 errors)
  - [x] ESLint clean (0 violations)
  - [x] Performance tested
  - [x] Mobile responsive
  - [x] Accessibility audited
  ```

- [ ] Add reviewers:
  - [ ] 1× Senior Frontend Engineer (architecture)
  - [ ] 1× Frontend Engineer (code review)
  - [ ] 1× Product Manager (UX sign-off)
  - [ ] 1× QA Engineer (testing)

### 6.3 Code Review

- [ ] Address feedback:
  - [ ] Component naming consistency
  - [ ] Hook usage best practices
  - [ ] Type safety
  - [ ] Performance concerns
  - [ ] Accessibility issues

- [ ] Expected review time: 24-48 hours
- [ ] Update PR with changes

### 6.4 Merge to feature/qa-system-bootstrap

- [ ] Squash or rebase commits (preference: squash for cleaner history)
- [ ] Merge via GitHub UI: "Squash and merge"
- [ ] Delete feature branch
- [ ] Verify CI/CD passes on feature/qa-system-bootstrap

### 6.5 Update Changelog

- [ ] File: `/CHANGELOG.md` (or `docs/CHANGELOG.md`)
- [ ] Entry:
  ```markdown
  ## [Unreleased]

  ### Added
  - Tab-based dashboard architecture (Overview, Trends, Release, MyWork, Activity tabs)
  - 19 new reusable dashboard components extracted from mega-component
  - Lazy loading for non-default tabs (50% faster initial load)
  - Mobile responsive design (375px/768px/1024px breakpoints)
  - Auto-refresh optimization (only active tab, 50% fewer API calls)
  - 50+ unit tests + 9 integration tests for dashboard

  ### Changed
  - Dashboard page.tsx refactored: 1690 → 200 lines
  - Auto-refresh badge redesigned (countdown visible)

  ### Fixed
  - (None)

  ### Removed
  - (None)
  ```

### 6.6 Create ADR-0015 (Decision Record)

- [ ] File: `docs/adr/ADR-0015-tab-based-dashboard.md`
- [ ] Content:
  ```markdown
  # ADR-0015: Tab-Based Dashboard Architecture

  **Date:** 2026-06-09  
  **Status:** Accepted  
  **Context:** Dashboard mega-component (1690 lines) causes poor UX, slow load times, hard to maintain

  **Decision:** Refactor into 5 tabs (Overview, Trends, Release, MyWork, Activity) with lazy loading

  **Rationale:**
  - Reduces cognitive load: Users see only relevant section
  - Faster initial load: Overview eager, others lazy
  - Easier maintenance: Extracted 19 components
  - Better performance: 50% fewer API calls (lazy + active-tab-only refresh)
  - Mobile friendly: Responsive tabs

  **Consequences:**
  - Learning curve for users (tabs new navigation pattern)
  - Small breaking change: UX looks different (but same functionality)
  - Benefits outweigh risks: Performance + maintainability gains

  **Alternatives Considered:**
  1. Accordion collapse: Still renders all widgets (no perf gain)
  2. Pagination: Confusing for dashboard
  3. Status quo: Unacceptable UX/performance

  **References:**
  - PR: #XXXX
  - DASHBOARD_REFACTOR_PLAN.md
  - DASHBOARD_COMPONENT_API.md
  ```

- [ ] Commit: `git add docs/adr/ADR-0015-*.md && git commit -m "docs(adr): ADR-0015 tab-based dashboard"`

### 6.7 Update Project Documentation

- [ ] File: `docs/FRONTEND_ARCHITECTURE.md`
- [ ] Add section: "Dashboard Architecture"
  ```markdown
  ## Dashboard (Management Module)

  **Location:** `apps/web/app/(dashboard)/p/[projectId]/management/dashboard/`

  **Architecture:** Tab-based (5 tabs, lazy loading)

  ### Tabs
  - **Overview:** Hero metrics, health score, setup tracker (eager load)
  - **Trends:** Run trends, defect trends, coverage heatmap (lazy)
  - **Release:** Blockers, signoff, regression readiness (lazy)
  - **MyWork:** Assigned cases, open defects, flaky tests, review queue (lazy)
  - **Activity:** Latest runs, cases, stale tests, audit feed (lazy)

  ### Data Loading Strategy
  - Eager: `summaryFast` (fast aggregated endpoint)
  - Lazy per tab: Only fetch when tab active
  - Auto-refresh: Only active tab, every 30s

  ### Components
  - Page: `page.tsx` (200 lines, routing + eager load)
  - Container: `DashboardTabs.tsx` (tab nav + lazy mount)
  - Tabs: `OverviewTab.tsx`, `TrendsTab.tsx`, etc.
  - Widgets: `shared-widgets/` (19 extracted components)

  ### Performance
  - First paint: <500ms (was 2000ms)
  - Mobile Lighthouse: >85
  - Responsive: 375px / 768px / 1024px
  ```

### 6.8 Staging Deployment

- [ ] Deploy feature/qa-system-bootstrap to staging
- [ ] Verify:
  - [ ] Dashboard loads without errors
  - [ ] All tabs render
  - [ ] Data loads correctly
  - [ ] Auto-refresh works
  - [ ] Mobile works on tablet/phone
  - [ ] Sentry: 0 new errors

- [ ] Create deployment checklist issue (if using GitHub Issues)

### 6.9 Monitoring (First Week Post-Deploy)

- [ ] Monitor Sentry:
  - [ ] Check for new JS errors
  - [ ] Check performance metrics (LCP, FID, CLS)
  - [ ] Alert if error rate >2%

- [ ] User feedback:
  - [ ] Check Slack/Discord for dashboard feedback
  - [ ] Respond to bugs quickly

- [ ] Rollback plan (if needed):
  ```bash
  git revert <commit-hash> && npm run deploy
  ```

### Phase 6 Sign-Off

- [ ] PR merged to feature/qa-system-bootstrap
- [ ] 0 merge conflicts
- [ ] Staging deployment successful
- [ ] Sentry: 0 new errors (first week)
- [ ] CHANGELOG.md updated
- [ ] ADR-0015 documented
- [ ] FRONTEND_ARCHITECTURE.md updated

**Estimated Hours:** 4  
**Buffer:** 20% → 4.8 hours (plan 5 hours)

---

## Overall Implementation Summary

### Timeline

| Week | Phase | Days | Hours | Status |
|------|-------|------|-------|--------|
| 1 | Extraction | 1-3 | 20h | Phase 1 ✓ |
| 1-2 | Tab Architecture | 4-8 | 25h | Phase 2 ✓ |
| 2 | Optimization | 9-10 | 14h | Phase 3 ✓ |
| 2-3 | Mobile & Responsive | 10-12 | 10h | Phase 4 ✓ |
| 3 | Testing & QA | 13-17 | 20h | Phase 5 ✓ |
| 3-4 | Release & Docs | 18-20 | 5h | Phase 6 ✓ |
| **TOTAL** | | | **94h** | |

**FTE Effort:** ~2.3 weeks (1 senior FE + 1 junior FE)  
**Realistic Duration:** 4-5 weeks (accounting for review cycles, interruptions, learning curve)

### Deliverables Checklist

#### Code
- [ ] 19 new components extracted to `_components/shared-widgets/`
- [ ] 5 new tab components in `_components/dashboard-tabs/`
- [ ] DashboardTabs container component
- [ ] Refactored page.tsx (1690 → 200 lines)
- [ ] Helper functions + hooks
- [ ] TypeScript interfaces + types

#### Tests
- [ ] 50+ unit tests (80%+ coverage)
- [ ] 9+ integration tests
- [ ] 4+ E2E tests
- [ ] 18 visual regression snapshots

#### Documentation
- [ ] DASHBOARD_REFACTOR_PLAN.md (this file)
- [ ] DASHBOARD_COMPONENT_API.md (component reference)
- [ ] DASHBOARD_IMPLEMENTATION_CHECKLIST.md (this file)
- [ ] ADR-0015 (decision record)
- [ ] CHANGELOG.md entry
- [ ] Updated FRONTEND_ARCHITECTURE.md

#### Performance
- [ ] First paint: <500ms (5× improvement)
- [ ] Mobile Lighthouse: >85
- [ ] Bundle size: No regression
- [ ] API calls: 3-5 per tab (lazy)

#### Quality
- [ ] 0 TypeScript errors
- [ ] 0 ESLint violations
- [ ] 0 critical accessibility violations
- [ ] Browser compatible: Chrome, Safari, Firefox, Edge
- [ ] Mobile responsive: 375px / 768px / 1024px

### Critical Success Factors

1. **Phase 1 Extraction:** If any component is missed, it must be added immediately (don't defer)
2. **Phase 2 Tab Architecture:** Tab switching MUST work smoothly; no lag
3. **Phase 3 Optimization:** Auto-refresh must only target active tab (verify with Network tab)
4. **Phase 4 Mobile:** Must test on real devices, not just DevTools
5. **Phase 5 Testing:** All tests must be deterministic (no flaky tests); coverage >80%
6. **Phase 6 Release:** Staging deployment is mandatory before merge

### Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Component extraction missed | Medium | High | Review PR carefully; run old code beside new in test |
| Tab switching slow | Low | High | Profile with Chrome DevTools; memoize components |
| Regression in features | Medium | High | Run full dashboard E2E tests; manual smoke test |
| Mobile not responsive | High | Medium | Test on real devices (iPhone + iPad); fix breakpoints early |
| Flaky tests | Medium | Medium | Use userEvent not fireEvent; avoid async timers; isolate mocks |
| Performance regression | Low | High | Measure LCP/FID/CLS before + after; use lighthouse-ci |

### Success Metrics

**Performance:**
- [ ] First paint <500ms ✓ (was 2000ms)
- [ ] LCP <1.2s ✓ (was 2s)
- [ ] Requests per tab: 3-5 ✓ (was 11 parallel)

**Quality:**
- [ ] Test coverage >80% ✓
- [ ] TypeScript strict ✓
- [ ] Accessibility AA ✓

**UX:**
- [ ] Mobile Lighthouse >85 ✓
- [ ] Tab switch latency <200ms ✓
- [ ] Responsive at 375px/768px/1024px ✓

---

## Quick Reference

### Key Files to Remember

```
# Source Files (create/modify)
_components/shared-widgets/*
_components/dashboard-tabs/*
_components/DashboardTabs.tsx
_components/utils/dashboard-helpers.ts
_components/utils/dashboard-hooks.ts
_components/utils/dashboard-types.ts
page.tsx (refactor)

# Test Files (create)
__tests__/page.test.tsx
__tests__/DashboardTabs.test.tsx
__tests__/shared-widgets/*
__tests__/dashboard-tabs/*

# Documentation (create)
docs/adr/ADR-0015-tab-based-dashboard.md
```

### Common Commands

```bash
# Run tests
npm test -- dashboard

# Run specific test
npm test -- dashboard/_components/shared-widgets/StatCard.test.tsx

# Type check
npx tsc --noEmit

# Lint
npx eslint _components/

# Build
npm run build

# Start dev server
npm run dev

# Performance audit
npm run lighthouse http://localhost:3000

# Accessibility audit
npx axe http://localhost:3000
```

### Team Communication

- **Daily Standup:** Report Phase progress, blockers, ETA
- **Code Review:** 1-2 reviewers per PR, 24-48h turnaround
- **QA Sign-Off:** Before merge, verify all tests pass
- **Stakeholder Update:** Weekly to PM + design (confirm mobile UX acceptable)

---

## Approval & Sign-Off

### Phase-by-Phase Sign-Off

**Phase 1 (Component Extraction):**
- [ ] Lead Engineer: Code quality, API consistency
- [ ] QA Engineer: Unit test coverage >80%
- [ ] Tech Lead: TypeScript strict, no breaking changes

**Phase 2 (Tab Architecture):**
- [ ] Lead Engineer: Tab switching logic, lazy mounting
- [ ] PM: UX acceptable (tabs clear, intuitive)
- [ ] QA Engineer: Integration tests pass, no regressions

**Phase 3 (Optimization):**
- [ ] Lead Engineer: Performance benchmarks meet targets
- [ ] DevOps: No infrastructure changes required
- [ ] QA Engineer: Load testing, throttling tests pass

**Phase 4 (Mobile & Responsive):**
- [ ] Design Lead: Mobile responsive design approved
- [ ] QA Engineer: Tested on real devices (iPhone + iPad)
- [ ] Accessibility Lead: WCAG AA compliance verified

**Phase 5 (Testing & QA):**
- [ ] QA Lead: All tests passing, coverage >80%
- [ ] Security: No new vulnerabilities
- [ ] Performance: Lighthouse >85, no regressions

**Phase 6 (Release & Documentation):**
- [ ] Tech Lead: Code review complete, 0 comments
- [ ] Product: Release notes approved
- [ ] DevOps: Staging deployment successful

### Final Approval

- [ ] Engineering Lead: **Sign off on code quality**
- [ ] Product Manager: **Sign off on UX / feature completeness**
- [ ] QA Lead: **Sign off on testing / quality gates**
- [ ] Tech Lead: **Sign off on architecture / maintainability**

---

**Created:** 2026-06-09  
**Last Updated:** 2026-06-09  
**Prepared by:** Claude Code  
**Status:** READY FOR IMPLEMENTATION

**Next Step:** Schedule Phase 1 kickoff meeting with team
