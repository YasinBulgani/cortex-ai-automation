# Dashboard Component API Reference

**Document:** Dashboard Refactor — Component Contracts  
**Date:** 2026-06-09  
**Scope:** Shared widget component signatures + usage patterns

---

## 1. Shared Widget Components

### 1.1 HeroMetricCard

**Location:** `_components/shared-widgets/HeroMetricCard.tsx`

**Purpose:** Display single large KPI (totalCases, activeRuns, passRate, criticalDefects)

**Props:**
```typescript
interface HeroMetricCardProps {
  label: string;              // "Toplam manuel case"
  value: string | number;     // 145
  sublabel: string;           // "245 suites, 8 klasor"
  icon?: React.ReactNode;     // Optional emoji or icon
  href?: string;              // Link to detail page
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
}
```

**Usage:**
```tsx
<HeroMetricCard
  label="Aktif koşum"
  value={3}
  sublabel="12 toplam run"
  tone="info"
  href={`/p/${projectId}/management/runs`}
/>
```

**Styles:** 25% width on desktop (4-col grid), full-width on mobile

---

### 1.2 StatCard

**Location:** `_components/shared-widgets/StatCard.tsx`

**Purpose:** Small KPI card with label, metric, note, optional link

**Props:**
```typescript
interface StatCardProps {
  label: string;              // "Başarısız case"
  value: string | number;     // 8
  note: string;               // "Acil triage bekleyen case"
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
  href?: string;              // /management/repository
}
```

**Usage:**
```tsx
<StatCard
  label="Başarısız case"
  value={failedCases}
  note="Acil triage bekleyen case"
  tone="danger"
  href={`/p/${projectId}/management/repository`}
/>
```

**Layout:** 4-col grid on desktop, 2-col on tablet, 1-col on mobile  
**Interactivity:** Hover brightness increase if href present

---

### 1.3 ProjectHealthWidget

**Location:** `_components/shared-widgets/ProjectHealthWidget.tsx`

**Purpose:** 4-criteria health score (0-100) with visual bar + status

**Props:**
```typescript
interface ProjectHealthWidgetProps {
  passRatePct: number;        // 82
  coveragePct: number;        // 75
  criticalDefects: number;    // 5
  activeRuns: number;         // 3
}
```

**Criteria:**
1. Pass Rate ≥ 85%
2. Coverage ≥ 70%
3. Critical Defects = 0
4. Active Runs > 0

**Score Calculation:** Each criterion = 25%, max 100

**Color Coding:**
- 76-100: Green (Mükemmel)
- 51-75: Amber (Orta)
- 0-50: Red (Kritik)

**Usage:**
```tsx
<ProjectHealthWidget
  passRatePct={82}
  coveragePct={75}
  criticalDefects={5}
  activeRuns={3}
/>
```

---

### 1.4 SetupTrackerWidget

**Location:** `_components/shared-widgets/SetupTrackerWidget.tsx`

**Purpose:** Onboarding progress tracker (4 items, completion %)

**Props:**
```typescript
interface SetupTrackerWidgetProps {
  projectId: string;          // For href generation
  totalCases: number;         // > 0 = first case created
  plansCount: number;         // > 0 = first plan created
  runsCount: number;          // + hasCompletedRun = first run done
  hasCompletedRun: boolean;   // status === "completed"
  requirementsCount: number;  // > 0 = requirement linked
}
```

**Criteria:**
1. İlk test senaryosu (totalCases > 0)
2. İlk test planı (plansCount > 0)
3. İlk test koşumu (runsCount > 0 && hasCompletedRun)
4. Gereksinim bağlantısı (requirementsCount > 0)

**Completion States:**
- All 4 done: Show "Hazırsınız! 🎉" success message
- Partial: Show progress bar + incomplete checklist (clickable links)

**Usage:**
```tsx
<SetupTrackerWidget
  projectId={projectId}
  totalCases={145}
  plansCount={8}
  runsCount={12}
  hasCompletedRun={true}
  requirementsCount={35}
/>
```

---

### 1.5 BlockersWidget

**Location:** `_components/shared-widgets/BlockersWidget.tsx`

**Purpose:** Release gate blockers (critical defects, coverage gaps, flaky tests)

**Props:**
```typescript
interface ReleaseBlocker {
  label: string;              // "Critical Defects"
  value: string | number;     // 5
  detail?: string;            // "P0-001: Login crash"
}

interface BlockersWidgetProps {
  blockers: ReleaseBlocker[];
  projectId: string;          // For "tümünü gör" link
}
```

**Visual States:**
- No blockers: Green success message "Aktif blocker bulunmuyor — release hazır."
- Blockers present: Red border, list with detail (if provided)

**Usage:**
```tsx
<BlockersWidget
  blockers={[
    { label: "Critical Defects", value: 5, detail: "P0-001: Login crash" },
    { label: "Coverage Gap", value: "15%", detail: "UI module <70%" }
  ]}
  projectId={projectId}
/>
```

---

### 1.6 ReleaseSignoffWidget

**Location:** `_components/shared-widgets/ReleaseSignoffWidget.tsx`

**Purpose:** Release approval form + history

**Props:**
```typescript
interface ReleaseSignoffWidgetProps {
  mpid: string;               // managementProjectId
  projectId: string;          // For navigation
  decision: "GO" | "NO_GO" | "PENDING";
  qualitySnapshot?: Record<string, unknown>;  // Snapshot metadata
}
```

**Features:**
- Display current decision status (color-coded)
- Show latest signoff history (role, decision, comment, date)
- Form toggle: [Onayla / Reddet] button → form (role, decision toggle, comment textarea)
- Submit sends signoff with snapshot

**Hooks Used:**
- `useReleaseSignoffs(mpid)` — fetch signoff history
- `useCreateReleaseSignoff(mpid)` — mutate new signoff

**Usage:**
```tsx
<ReleaseSignoffWidget
  mpid="mp-123"
  projectId="proj-456"
  decision="PENDING"
  qualitySnapshot={{
    pass_rate_pct: 89,
    failed_cases: 8,
    critical_defects: 0
  }}
/>
```

---

### 1.7 RunTrendChart

**Location:** `_components/shared-widgets/RunTrendChart.tsx`

**Purpose:** SVG line chart — pass rate trend over last N runs

**Props:**
```typescript
interface RunTrendPoint {
  name: string;               // Run name
  pass_rate_pct: number;      // 0-100
  passed: number;
  failed: number;
  total_cases: number;
  created_at: string;         // ISO date
}

interface RunTrendChartProps {
  points: RunTrendPoint[];    // Min 2 points to render
}
```

**Features:**
- SVG line + area fill (gradient)
- 85% target line (amber dashed)
- Point dots (color: green >85%, amber 60-85%, red <60%)
- Hover tooltip (run name, %)
- Stats: Avg, Last, Trend direction

**Edge Cases:**
- <2 points: Show "Trend için en az 2 run gerekli."
- All points <85%: Trendline is red
- Increasing trend: Green arrow + % change

**Usage:**
```tsx
<RunTrendChart
  points={[
    { name: "Run 1", pass_rate_pct: 75, passed: 45, failed: 15, total_cases: 60, created_at: "2026-06-01T10:00:00Z" },
    { name: "Run 2", pass_rate_pct: 82, passed: 49, failed: 11, total_cases: 60, created_at: "2026-06-02T10:00:00Z" },
    ...
  ]}
/>
```

---

### 1.8 DefectTrendMini

**Location:** `_components/shared-widgets/DefectTrendMini.tsx`

**Purpose:** Stacked bar chart — open/closed defects over 8 weeks

**Props:**
```typescript
interface DefectLink {
  id: string;
  created_at: string;         // ISO date
  status: string;             // "open", "closed", "resolved", etc
}

interface DefectTrendMiniProps {
  defects: DefectLink[];
}
```

**Features:**
- 8-week bucketing (lookback from now)
- Stacked bars: red (open) + green (closed)
- Hover labels: "Açık: 5", "Kapalı: 3"
- Week labels: "6/1", "6/8", ...
- Legend: Red = Açık, Green = Kapalı

**Edge Cases:**
- No defects: Show "Henüz defect verisi yok."
- All closed: Show green bars only

**Usage:**
```tsx
<DefectTrendMini defects={defects} />
```

---

### 1.9 CoverageHeatmap

**Location:** `_components/shared-widgets/CoverageHeatmap.tsx`

**Purpose:** Suite-level test pass rate heatmap (top 10 suites by case count)

**Props:**
```typescript
interface TestCase {
  id: string;
  suite_id?: string;
  last_run_status?: "passed" | "failed" | "blocked" | "not_run";
  // ... other fields
}

interface TestSuiteLocal {
  id: string;
  name: string;
}

interface CoverageHeatmapProps {
  cases: TestCase[];
  suites: TestSuiteLocal[];
}
```

**Features:**
- Calculate per-suite: total, passed, failed, blocked, not_run
- Sort by case count descending
- Limit top 10
- Horizontal bar per suite (stacked: green/red/amber/gray)
- Pass rate % on right
- Legend below

**Calculation:**
```
passRate = (passed / total) * 100
Color coding:
- ≥80%: Green
- 50-79%: Amber
- <50%: Red
```

**Usage:**
```tsx
<CoverageHeatmap
  cases={cases}
  suites={repoQ.data?.suites ?? []}
/>
```

---

### 1.10 TestInsightsPanel

**Location:** `_components/shared-widgets/TestInsightsPanel.tsx`

**Purpose:** 3-column layout: Type distribution + Priority breakdown + Weekly velocity

**Props:**
```typescript
interface TestInsightsPanelProps {
  cases: TestCase[];
  runs: TestRun[];
}
```

**Column 1: Test Type Distribution**
- Horizontal bar: manual/automated/exploratory (colored)
- List of HorizBar components
- Total case count

**Column 2: Priority Breakdown**
- Horizontal bar: P0/P1/P2/P3
- List of HorizBar components
- Note: "X kritik case — risk değerlendirmesi"

**Column 3: Weekly Velocity**
- 4-week bar chart (H-3, H-2, H-1, Bu Hafta)
- Current week highlighted (brand color)
- Average runs/week at bottom

**Usage:**
```tsx
<TestInsightsPanel cases={cases} runs={runs} />
```

---

### 1.11 FlakyTestsWidget

**Location:** `_components/shared-widgets/FlakyTestsWidget.tsx`

**Purpose:** List flaky tests (flakiness_score ≥ 0.2)

**Props:**
```typescript
interface FlakyTestOut {
  id: string;
  case_key: string;
  title: string;
  flakiness_score: number;    // 0-1
  run_count: number;
}

interface FlakyTestsWidgetProps {
  flakyTests: FlakyTestOut[];
  isLoading?: boolean;
  projectId: string;
}
```

**Features:**
- List flaky tests
- Score % with color gradient (40% ≈ amber, 60% ≈ red)
- Click to navigate to case detail
- Empty state: "Flaky test tespit edilmedi."
- Loading state: 3 skeleton rows

**Usage:**
```tsx
<FlakyTestsWidget
  flakyTests={flakyQ.data?.items ?? []}
  isLoading={flakyQ.isLoading}
  projectId={projectId}
/>
```

---

### 1.12 ReviewQueueWidget

**Location:** `_components/shared-widgets/ReviewQueueWidget.tsx`

**Purpose:** List pending case reviews

**Props:**
```typescript
interface CaseReviewOut {
  id: string;
  case_key: string;
  title: string;
}

interface ReviewQueueWidgetProps {
  reviewQueue: CaseReviewOut[];
  isLoading?: boolean;
  projectId: string;
}
```

**Features:**
- List cases with "İnceleme Bekliyor" badge
- Click to navigate to case detail
- Empty state: "Bekleyen inceleme yok."
- Badge count in header

**Usage:**
```tsx
<ReviewQueueWidget
  reviewQueue={reviewQ.data ?? []}
  isLoading={reviewQ.isLoading}
  projectId={projectId}
/>
```

---

### 1.13 StaleTestsWidget

**Location:** `_components/shared-widgets/StaleTestsWidget.tsx`

**Purpose:** Tests not run in 14+ days

**Props:**
```typescript
interface StaleTestsWidgetProps {
  staleTests: TestCase[];     // Limited to 8
  totalStaleCount: number;    // Full count (for "+N daha" link)
  projectId: string;
  staleDays?: number;         // Default 14
}
```

**Features:**
- Display 8 most critical stale tests (by priority)
- Show days since last run or "Hiç koşulmadı"
- Priority badge (P0=red, P1=orange, P2=amber, P3=slate)
- "View all" link if total > 8

**Color Scheme:**
- Green box: No stale tests
- Orange box: Stale tests present

**Usage:**
```tsx
<StaleTestsWidget
  staleTests={staleTests}
  totalStaleCount={staleTestsAll.length}
  projectId={projectId}
  staleDays={14}
/>
```

---

### 1.14 MyWorkWidget

**Location:** `_components/shared-widgets/MyWorkWidget.tsx`

**Purpose:** Show current user's assigned cases + open defects

**Props:**
```typescript
interface MyWorkWidgetProps {
  projectId: string;
  myCases: TestCase[];        // Limited to 8
  myOpenDefects: DefectLink[]; // Limited to 5
  isLoading?: boolean;
}
```

**Features:**
- 2-column layout: Assigned cases + Open defects
- Cases: Show status badge (failed/passed/blocked/none)
- Defects: Show severity + status
- Empty states: "Size atanmış case yok." / "Açık defektiniz yok."

**Usage:**
```tsx
<MyWorkWidget
  projectId={projectId}
  myCases={myCases}
  myOpenDefects={myOpenDefects}
/>
```

---

### 1.15 ActivityFeedWidget

**Location:** `_components/shared-widgets/ActivityFeedWidget.tsx`

**Purpose:** Recent audit events

**Props:**
```typescript
interface AuditEvent {
  id: string;
  action: string;             // "Test case created: TC-999"
  actor_id?: string;
  created_at: string;         // ISO date
}

interface ActivityFeedWidgetProps {
  events: AuditEvent[];       // Limited to 8
  userIdMap: Record<string, string>;
  projectId: string;
}
```

**Features:**
- List events with actor avatar (first letter)
- Date/time formatted
- Click "View all" → /audit page

**Usage:**
```tsx
<ActivityFeedWidget
  events={auditQ.data?.slice(0, 8) ?? []}
  userIdMap={userIdMap}
  projectId={projectId}
/>
```

---

### 1.16 MiniBar

**Location:** `_components/shared-widgets/MiniBar.tsx`

**Purpose:** Simple horizontal progress bar (reusable, used in many widgets)

**Props:**
```typescript
interface MiniBarProps {
  label: string;              // "Koşum ilerlemesi"
  value: number;              // Current value
  max: number;                // Max value
  tone: string;               // "bg-blue-500", "bg-emerald-500", etc
}
```

**Features:**
- Label on left
- Percentage calculated: (value / max) * 100
- Bar width matches percentage
- Value shown (optional: in label right-aligned)

**Usage:**
```tsx
<MiniBar
  label="Geçme oranı"
  value={89}
  max={100}
  tone="bg-emerald-500"
/>
```

---

### 1.17 HorizBar

**Location:** `_components/shared-widgets/HorizBar.tsx`

**Purpose:** Horizontal bar with label + percentage (test type, priority distribution)

**Props:**
```typescript
interface HorizBarProps {
  label: string;              // "Manuel"
  count: number;              // 80
  total: number;              // 145
  color: string;              // "bg-blue-500"
}
```

**Features:**
- Label, count, percentage bar
- Used in TestInsightsPanel

**Usage:**
```tsx
<HorizBar
  label="Manuel"
  count={80}
  total={145}
  color="bg-blue-500"
/>
```

---

### 1.18 AutoRefreshBadge

**Location:** `_components/shared-widgets/AutoRefreshBadge.tsx`

**Purpose:** Visual countdown timer + pulse animation

**Props:**
```typescript
interface AutoRefreshBadgeProps {
  interval?: number;          // Default 30s
}
```

**Features:**
- Countdown: "30s otomatik yenileniyor" → "5s sonra yenilenir"
- Pulse animation at refresh moment
- Animated dot (green)

**Usage:**
```tsx
<AutoRefreshBadge interval={30000} />
```

---

### 1.19 EmptyState

**Location:** `_components/shared-widgets/EmptyState.tsx`

**Purpose:** First-time user guidance

**Props:**
```typescript
interface EmptyStateProps {
  projectId: string;
}
```

**Features:**
- Icon + message: "Henüz veri bulunmuyor"
- 2 CTA buttons: [Repository'ye git] [Case ekle]

**Usage:**
```tsx
<EmptyState projectId={projectId} />
```

---

## 2. Tab Container Components

### 2.1 DashboardTabs

**Location:** `_components/DashboardTabs.tsx`

**Purpose:** Tab navigation container + lazy child rendering

**Props:**
```typescript
interface DashboardTabsProps {
  projectId: string;
  mpid: string;
  activeTab: string;          // "overview", "trends", "release", "mywork", "activity"
  onTabChange: (tab: string) => void;
  // Eager data
  summaryFast?: any;
  profile?: { id: string };
  // Lazy data (passed only if already loaded)
  trendQ?: useQuery result;
  flakyQ?: useQuery result;
  // ... more props
}
```

**Features:**
- Tab buttons (desktop horizontal, mobile dropdown)
- Lazy child render (only active tab mounts)
- Refresh button (refetch active tab data)
- Loading skeleton per tab

**Tabs:**
1. Overview (default)
2. Trends & Quality
3. Release & Blockers
4. My Work
5. Activity & Insights

**Usage:**
```tsx
<DashboardTabs
  projectId={projectId}
  mpid={mpid}
  activeTab={activeTab}
  onTabChange={setActiveTab}
  summaryFast={summaryFast.data}
  profile={profile.data}
/>
```

---

## 3. Tab Content Components

### 3.1 OverviewTab

**Location:** `_components/dashboard-tabs/OverviewTab.tsx`

**Purpose:** Hero metrics + health + setup + KPI cards + quick actions

**Props:**
```typescript
interface OverviewTabProps {
  projectId: string;
  summaryFast?: { /* aggregated KPIs */ };
  cases: TestCase[];
  runs: TestRun[];
  // ... other computed data
}
```

**No Data Fetching** — Uses data passed from page.tsx

---

### 3.2 TrendsTab

**Location:** `_components/dashboard-tabs/TrendsTab.tsx`

**Purpose:** Run trends, defect trends, coverage heatmap, test insights

**Props:**
```typescript
interface TrendsTabProps {
  projectId: string;
  mpid: string;
}
```

**Data Fetching (Lazy):**
- `useManagementRunTrend(mpid)`
- `useManagementDefects(mpid)`
- `useManagementRepository(mpid)`

---

### 3.3 ReleaseTab

**Location:** `_components/dashboard-tabs/ReleaseTab.tsx`

**Purpose:** Blockers, signoff, regression readiness, checklist

**Props:**
```typescript
interface ReleaseTabProps {
  projectId: string;
  mpid: string;
}
```

**Data Fetching (Lazy):**
- `useReleaseReport(mpid)`
- `useManagementPlans(mpid)`

---

### 3.4 MyWorkTab

**Location:** `_components/dashboard-tabs/MyWorkTab.tsx`

**Purpose:** My work, flaky tests, review queue, workload, module distribution

**Props:**
```typescript
interface MyWorkTabProps {
  projectId: string;
  mpid: string;
  currentUserId: string;
  userIdMap: Record<string, string>;
}
```

**Data Fetching (Lazy):**
- `useManagementFlakyTests(mpid, { ... })`
- `useReviewQueue(mpid)`
- `useManagementRuns(mpid)`
- `useManagementRepository(mpid)`

---

### 3.5 ActivityTab

**Location:** `_components/dashboard-tabs/ActivityTab.tsx`

**Purpose:** Latest runs, latest cases, stale tests, activity feed

**Props:**
```typescript
interface ActivityTabProps {
  projectId: string;
  mpid: string;
  userIdMap: Record<string, string>;
}
```

**Data Fetching (Lazy):**
- `useManagementAuditEvents(mpid, 10)`
- `useManagementRuns(mpid)`
- `useManagementRepository(mpid)`

---

## 4. Utility Functions

### 4.1 dashboard-helpers.ts

**Functions:**

```typescript
// Status translation (TR)
function tr(value: string | undefined | null, fallback?: string): string

// Safe text extraction
function asText(value: unknown, fallback = "Tanimsiz"): string

// Color assignment for priority
function getPriorityColor(priority: string): string

// Defect status classifier
function isDefectClosed(status: string): boolean

// Date formatter
function formatShortDate(date: string): string
```

---

### 4.2 dashboard-hooks.ts

**Hooks:**

```typescript
// Manage active tab (state or URL)
function useTabState(): [string, (tab: string) => void]

// Request tab data on click (prefetch)
function useLazyTabData(tabName: string): { loading: boolean; error?: Error }

// Auto-refresh only active tab
function useAutoRefresh(interval: number, activeTab: string, queries: Query[]): void

// Compute stale tests
function useStaleTests(cases: TestCase[], staleDays: number): TestCase[]
```

---

## 5. Type Definitions

**Location:** `_components/utils/dashboard-types.ts`

```typescript
// Export all types used across dashboard
export type {
  ProjectSummary,
  ExecutionSummary,
  ReleaseReport,
  ReleaseBlocker,
  FlakyTestOut,
  CaseReviewOut,
  RunTrendPoint,
  DefectLink,
  TestCase,
  TestRun,
  AuditEvent,
  TestSuite,
};
```

---

## 6. Usage Patterns

### Pattern 1: Simple Widget (StatCard)

```tsx
// In OverviewTab.tsx
<StatCard
  label="Başarısız case"
  value={failedCases}
  note="Acil triage bekleyen case"
  tone="danger"
  href={`/p/${projectId}/management/repository`}
/>
```

### Pattern 2: Data-Dependent Widget (RunTrendChart)

```tsx
// In TrendsTab.tsx
{trendQ.isLoading ? (
  <div className="h-32 animate-pulse rounded-lg bg-surface-overlay" />
) : (
  <RunTrendChart points={trendQ.data ?? []} />
)}
```

### Pattern 3: Form Widget (ReleaseSignoffWidget)

```tsx
// In ReleaseTab.tsx
<ReleaseSignoffWidget
  mpid={mpid}
  projectId={projectId}
  decision={release?.decision ?? "PENDING"}
  qualitySnapshot={{...}}
/>
```

### Pattern 4: List Widget (FlakyTestsWidget)

```tsx
// In MyWorkTab.tsx
<FlakyTestsWidget
  flakyTests={flakyQ.data?.items ?? []}
  isLoading={flakyQ.isLoading}
  projectId={projectId}
/>
```

---

## 7. Testing Strategies

### Unit Test Template

```typescript
import { render, screen } from "@testing-library/react";
import { StatCard } from "./StatCard";

describe("StatCard", () => {
  it("renders label, value, and note", () => {
    render(
      <StatCard
        label="Test Label"
        value={42}
        note="Test note"
      />
    );
    expect(screen.getByText("Test Label")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Test note")).toBeInTheDocument();
  });

  it("renders as link when href provided", () => {
    render(
      <StatCard
        label="Test"
        value={10}
        note="note"
        href="/test"
      />
    );
    expect(screen.getByRole("link")).toHaveAttribute("href", "/test");
  });
});
```

### Integration Test Template

```typescript
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TrendsTab } from "./TrendsTab";

describe("TrendsTab", () => {
  it("loads data on mount", async () => {
    render(<TrendsTab projectId="p-123" mpid="mp-456" />);
    await waitFor(() => {
      expect(screen.getByText(/Test Koşum Trendi/)).toBeInTheDocument();
    });
  });
});
```

---

## 8. Performance Checklist

- [ ] All components memoized if pure (React.memo)
- [ ] No inline objects/arrays in JSX
- [ ] useCallback for event handlers
- [ ] useMemo for computed data
- [ ] React Query enabled flag for lazy queries
- [ ] No N+1 queries
- [ ] Charts virtualized if >1000 data points
- [ ] Images lazy-loaded
- [ ] CSS-in-JS minimal (prefer Tailwind)

---

**Created:** 2026-06-09  
**Last Updated:** 2026-06-09  
**Status:** Ready for implementation
