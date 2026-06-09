# NEUREX Q2 2027+ Enterprise & Optional Features
## Advanced Tracks: LLM MVP, Multi-Region Failover, Event Streaming, Q1 Enhancements

**Document Date:** 2026-06-09  
**Target Timeline:** Q2 2027 – Q4 2027 (6 months, ongoing)  
**Team Required:** 4–6 FTE (distributed)  
**Investment:** $280K–$380K (Phase-based)  
**Expected ARR Impact:** +$2M–$3M (enterprise & premium tier)

---

## EXECUTIVE SUMMARY

After successful completion of Phases 0–3 (core platform, async architecture, mobile MVP, enterprise SSO), Neurex enters the **advanced optionality phase**. This document defines 4 concurrent workstreams addressing enterprise consolidation and differentiation:

1. **Advanced AI Features** — Auto-fix, smart grouping, predictive selection, anomaly detection
2. **GraphQL API** — Modern query language, real-time subscriptions, batch operations
3. **Multi-Region Deployment** — Global data residency, failover automation, sub-100ms replication
4. **Native Mobile Optimization** — iOS SwiftUI/Android Jetpack Compose platform-specific features

**Rationale:** Neurex @ Phase 3 completion has 50K+ users, $10M+ ARR baseline. Enterprise customers demand advanced features; competitive differentiation requires both AI and infrastructure depth.

---

## TRACK 1: ADVANCED AI FEATURES (Q2–Q3 2027)

### 1.1 Auto-Fix Suggestions

**Objective:** Automatically suggest fixes for failing tests with ML-learned patterns.

**Architecture:**

```
Test Failure → Analyze Stack Trace → Historical Similar Failures → Pattern Match
                                    ↓
                        [ML Model: 5-layer Neural Net]
                                    ↓
                        Suggest Fix + Confidence Score + Cost
                                    ↓
                        One-Click Apply + Audit Log
```

**Features:**

- **ML Model Training**
  - Historical failure dataset: 10K+ test runs (from QA execution logs)
  - Features: error type, test stack, environment, timing, recent code changes
  - Output: fix category (retry, add wait, fix locator, mock API, etc.)
  - Retraining: weekly automated pipeline

- **Fix Categories** (learned patterns):
  1. **Flaky Timing** — Add explicit wait, increase retry count, add debug logging
  2. **Broken Locators** — Suggest CSS selector alternatives, XPath, accessibility locator
  3. **Mock Issues** — Detect stale mocks, suggest endpoint reset, add fixture seeding
  4. **API Failures** — Suggest fallback mock, circuit breaker bypass, retry with exponential backoff
  5. **Environment Issues** — Suggest config override, regional endpoint, proxy settings
  6. **Assertion Logic** — Fuzzy match detection, threshold adjustment, BDD rewrite

- **Confidence Scoring**
  - 0.9+: Auto-apply (with audit log)
  - 0.7–0.9: 1-click approve UI
  - <0.7: Suggestion card (no action)
  - False positive rate target: <2%

**Implementation:**

**Backend (350 lines):**
```python
# domains/ai_fixes/models.py
class AutoFixSuggestion:
    run_id: str
    failure_reason: str
    fix_category: Enum  # TIMING, LOCATOR, MOCK, API, ENV, ASSERTION
    suggested_fix: str  # Actual code/config change
    confidence_score: float  # 0.0–1.0
    estimated_cost: int  # Minutes to fix manually
    applied: bool = False
    applied_by: str | None
    applied_at: datetime | None
    feedback: str | None  # User validation
    
class FixHistory:
    org_id: str
    fix_category: str
    success_rate: float  # Of applied fixes that passed next run
    avg_saves_minutes: float

# domains/ai_fixes/service.py
async def suggest_auto_fixes(run_id: str, failures: List[Failure]) -> List[AutoFixSuggestion]:
    """ML-powered fix suggestions."""
    model = await load_ml_model("autofix_v1.pkl")
    suggestions = []
    
    for failure in failures:
        features = extract_features(failure)
        prediction = model.predict_proba([features])
        
        if prediction.max() > 0.7:
            fix = generate_fix(failure, prediction.argmax())
            suggestion = AutoFixSuggestion(
                failure_reason=failure.error_msg,
                fix_category=FIX_CATEGORIES[prediction.argmax()],
                suggested_fix=fix.code,
                confidence_score=float(prediction.max()),
                estimated_cost=estimate_manual_fix_time(failure),
            )
            suggestions.append(suggestion)
    
    return suggestions

async def apply_auto_fix(suggestion_id: str, user_id: str) -> Run:
    """Apply fix & re-run test."""
    suggestion = await db.get(AutoFixSuggestion, suggestion_id)
    
    # Apply fix to test case
    test_case = await db.get(TestCase, suggestion.test_case_id)
    test_case.code = apply_patch(test_case.code, suggestion.suggested_fix)
    await db.update(test_case)
    
    # Re-run
    run = await execute_run(test_case.project_id, [test_case.id])
    
    # Log outcome for model retraining
    suggestion.applied = True
    suggestion.applied_by = user_id
    suggestion.applied_at = datetime.utcnow()
    await db.update(suggestion)
    
    # Feedback placeholder (user can validate)
    return run
```

**Frontend (250 lines):**
```typescript
// components/AutoFixSuggestionCard.tsx
export const AutoFixSuggestionCard: React.FC<{
  suggestion: AutoFixSuggestion;
  onApply: (id: string) => Promise<void>;
  onDismiss: (id: string) => void;
}> = ({ suggestion, onApply, onDismiss }) => {
  const [loading, setLoading] = useState(false);
  
  const confidenceColor = suggestion.confidence_score > 0.8 
    ? 'green' : suggestion.confidence_score > 0.7 
    ? 'yellow' : 'red';
  
  return (
    <div className="border-l-4 rounded p-4" style={{ borderColor: confidenceColor }}>
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <p className="font-medium text-sm">
            {FIX_CATEGORY_LABELS[suggestion.fix_category]}
          </p>
          <p className="text-xs text-gray-600 mt-1">
            {suggestion.suggested_fix}
          </p>
          <div className="flex gap-4 mt-2 text-xs text-gray-500">
            <span>Confidence: {(suggestion.confidence_score * 100).toFixed(0)}%</span>
            <span>Est. saves: {suggestion.estimated_cost} min</span>
          </div>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => {
              setLoading(true);
              onApply(suggestion.id)
                .finally(() => setLoading(false));
            }}
            disabled={loading || suggestion.confidence_score < 0.7}
            className="px-3 py-1 bg-blue-600 text-white rounded text-xs disabled:opacity-50"
          >
            {loading ? 'Applying...' : 'Apply'}
          </button>
          <button
            onClick={() => onDismiss(suggestion.id)}
            className="px-3 py-1 text-gray-600 border rounded text-xs"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};

// hooks/useAutoFix.ts
export const useAutoFix = (runId: string) => {
  const [suggestions, setSuggestions] = useState<AutoFixSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  
  const loadSuggestions = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get(
        `/api/v1/ai-fixes/suggestions?run_id=${runId}`
      );
      setSuggestions(res);
    } finally {
      setLoading(false);
    }
  }, [runId]);
  
  const applySuggestion = useCallback(async (suggestionId: string) => {
    const res = await apiClient.post(
      `/api/v1/ai-fixes/${suggestionId}/apply`
    );
    setSuggestions(prev => prev.filter(s => s.id !== suggestionId));
    return res;
  }, []);
  
  useEffect(() => {
    loadSuggestions();
  }, [runId]);
  
  return { suggestions, loading, applySuggestion };
};
```

**Tests (180 lines):**
```python
# tests/unit/test_autofix_service.py
def test_suggest_auto_fixes_high_confidence():
    """Suggestions >0.8 confidence should be auto-apply ready."""
    failures = [
        Failure(id="f1", error_msg="Element not found", stack_trace="...")
    ]
    suggestions = suggest_auto_fixes(failures)
    
    high_conf = [s for s in suggestions if s.confidence_score > 0.8]
    assert len(high_conf) > 0
    assert high_conf[0].fix_category in FIX_CATEGORIES
    assert high_conf[0].estimated_cost > 0

def test_apply_auto_fix_reruns_test():
    """Applying fix should re-execute the test case."""
    suggestion = AutoFixSuggestion(
        test_case_id="tc1",
        fix_category=FIX_CATEGORY.TIMING,
        suggested_fix="await page.waitForTimeout(1000);"
    )
    
    run = apply_auto_fix(suggestion.id, user_id="user1")
    
    assert run.test_cases[0].code.contains("waitForTimeout")
    assert len(run.steps) > 0  # Re-executed

def test_false_positive_tracking():
    """Track failed auto-fixes to improve model."""
    suggestion = apply_auto_fix("sug1", "user1")
    run = get_run(suggestion.run_id)
    
    if run.status == "FAILED":
        feedback = record_autofix_feedback(
            suggestion_id="sug1",
            success=False,
            new_failure_reason="Fix didn't work"
        )
        
        # Model retraining should penalize this fix category
        assert feedback.marked_for_retraining
```

**Database (Alembic migration):**
```python
# alembic/versions/20270501_0001_auto_fix_suggestions.py
def upgrade():
    op.create_table(
        'auto_fix_suggestions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id')),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id')),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('runs.id')),
        sa.Column('test_case_id', sa.String(36), sa.ForeignKey('test_cases.id')),
        sa.Column('failure_reason', sa.Text),
        sa.Column('fix_category', sa.Enum(FIX_CATEGORY)),
        sa.Column('suggested_fix', sa.Text),
        sa.Column('confidence_score', sa.Float),
        sa.Column('estimated_cost_minutes', sa.Integer),
        sa.Column('applied', sa.Boolean, default=False),
        sa.Column('applied_by', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('applied_at', sa.DateTime),
        sa.Column('feedback', sa.Text),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    )
    op.create_index('ix_auto_fix_suggestions_run_id', 'auto_fix_suggestions', ['run_id'])
    op.create_index('ix_auto_fix_suggestions_org_id', 'auto_fix_suggestions', ['org_id'])
    op.create_table(
        'fix_feedback',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('suggestion_id', sa.String(36), sa.ForeignKey('auto_fix_suggestions.id')),
        sa.Column('success', sa.Boolean),
        sa.Column('feedback_text', sa.Text),
        sa.Column('marked_for_retraining', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
    )
```

**Implementation Timeline:**
- Week 1–2: ML model training pipeline + data collection
- Week 3–4: Backend API endpoints + fix application logic
- Week 5: Frontend components + integration
- Week 6: Testing + A/B deploy (10% cohort)

**Success Metrics:**
- [ ] Auto-fix confidence >85% (false positives <2%)
- [ ] 40%+ of suggested fixes applied by users
- [ ] 70%+ applied fixes result in passing test
- [ ] Avg. saves: 15 min/fix × 100 fixes/week = 25 hrs/week saved
- [ ] Model retraining completes <24h after new feedback

---

### 1.2 Smart Defect Grouping

**Objective:** Automatically detect duplicate defects, root causes, and group related failures.

**Features:**

- **Duplicate Detection**
  - Semantic similarity (NLP embeddings: Sentence-BERT)
  - Stack trace fuzzy matching
  - Error message similarity
  - Threshold: >0.85 = likely duplicate

- **Root Cause Clustering**
  - Group failures by: API endpoint, component, error type, environment
  - ML clustering: K-means on feature vectors
  - Suggest grouping to users ("These 5 defects likely share root cause")

- **Smart Merging**
  - Merge defect B into A (parent)
  - Auto-relink runs, comments, attachments
  - Preserve audit trail

**Implementation:**
```python
# domains/defects/grouping_service.py
async def detect_duplicate_defects(new_defect_id: str) -> List[Defect]:
    """Find likely duplicates using NLP + fuzzy matching."""
    new_defect = await db.get(Defect, new_defect_id)
    candidates = await db.query(Defect).filter(
        Defect.project_id == new_defect.project_id,
        Defect.status.in_(["OPEN", "REOPENED"]),
        Defect.created_at > datetime.utcnow() - timedelta(days=30),
    )
    
    # Semantic similarity
    embedding = await get_embedding(new_defect.title + " " + new_defect.description)
    duplicates = []
    
    for candidate in candidates:
        candidate_emb = await get_embedding(candidate.title + " " + candidate.description)
        similarity = cosine_similarity([embedding], [candidate_emb])[0][0]
        
        # Stack trace fuzzy match
        if new_defect.stack_trace and candidate.stack_trace:
            fuzz_ratio = fuzz.ratio(new_defect.stack_trace[:200], candidate.stack_trace[:200]) / 100
            combined_score = 0.6 * similarity + 0.4 * fuzz_ratio
        else:
            combined_score = similarity
        
        if combined_score > 0.85:
            duplicates.append(candidate)
    
    return duplicates

async def merge_defects(parent_id: str, child_id: str, merged_by: str):
    """Merge child defect into parent (one-way)."""
    parent = await db.get(Defect, parent_id)
    child = await db.get(Defect, child_id)
    
    # Relink all runs
    await db.execute(
        update(Run).where(Run.defect_id == child_id).values(defect_id=parent_id)
    )
    
    # Merge comments
    parent.comments += f"\n\n[MERGED from {child.id}]\n" + child.description
    
    # Mark as duplicate
    child.status = "DUPLICATE"
    child.merged_into = parent_id
    child.merged_at = datetime.utcnow()
    child.merged_by = merged_by
    
    await db.update(parent)
    await db.update(child)
```

**Time Estimate:** 200 lines backend, 150 lines frontend → 3 weeks

---

### 1.3 Predictive Test Selection

**Objective:** ML-powered smart test selection ("what to test next").

**Features:**

- **Risk Scoring**
  - Recent code changes (git diff analysis)
  - Historical failure rate by component
  - Test coverage gaps
  - Output: risk_score [0.0–1.0] per component

- **Smart Selection**
  - Automatically select tests for risky areas
  - Optimize for: speed vs coverage tradeoff
  - "Smoke" (5 min), "Canary" (20 min), "Full" (90 min) profiles

- **ML Learning**
  - Track which tests catch regressions
  - Reweight test importance based on historical catch rate

**Implementation:**
```python
# domains/tspm/predictive_selection_service.py
async def score_risk_by_component(project_id: str) -> Dict[str, float]:
    """Calculate risk scores for all components."""
    # Recent changes
    changed_files = await git_service.get_changed_files(project_id)
    component_changes = defaultdict(int)
    
    for file in changed_files:
        components = infer_components(file)  # Map file to component
        for comp in components:
            component_changes[comp] += 1
    
    # Historical failure rates
    failure_rates = await db.query(Run).with_entities(
        Run.component,
        func.count(Run.id),
        func.count(Run.id).filter(Run.status == "FAILED") / func.count(Run.id)
    ).group_by(Run.component).all()
    
    risk_scores = {}
    for component, change_count, failure_rate in failure_rates:
        recent_change_weight = min(change_count / 10, 1.0)  # Cap at 1.0
        risk_scores[component] = 0.6 * recent_change_weight + 0.4 * failure_rate
    
    return risk_scores

async def select_tests_smart(
    project_id: str,
    profile: Literal["smoke", "canary", "full"] = "canary"
) -> List[TestCase]:
    """Intelligent test selection based on risk."""
    risk_scores = await score_risk_by_component(project_id)
    test_cases = await db.query(TestCase).filter(TestCase.project_id == project_id)
    
    # Score tests
    test_scores = []
    for tc in test_cases:
        component_risk = risk_scores.get(tc.component, 0.5)
        historical_catch = await get_test_catch_rate(tc.id)  # % of regressions caught
        test_score = 0.5 * component_risk + 0.5 * historical_catch
        test_scores.append((tc, test_score))
    
    # Select by profile
    test_scores.sort(key=lambda x: x[1], reverse=True)
    
    if profile == "smoke":
        selected = test_scores[:min(10, len(test_scores))]  # Top 10
    elif profile == "canary":
        selected = test_scores[:min(30, len(test_scores))]  # Top 30
    else:  # full
        selected = test_scores
    
    return [tc for tc, _ in selected]
```

**Time Estimate:** 250 lines backend, 120 lines frontend → 3 weeks

---

### 1.4 Performance Anomaly Detection

**Objective:** Automatically detect performance regressions (slow tests, memory leaks).

**Features:**

- **Baseline Tracking**
  - Per-test execution time baseline (rolling 30-day avg)
  - Alert if >20% slower than baseline
  - Memory usage tracking (heap snapshots)

- **Root Cause Hints**
  - Slow DOM queries? Suggest selector optimization
  - Timeout increases? Suggest environment checks
  - Memory leak? Suggest callback cleanup

- **Dashboard**
  - Slow tests trending (histogram)
  - Performance regression alerts
  - Comparison: expected vs actual

**Implementation:**
```python
# domains/tspm/perf_anomaly_service.py
async def calculate_execution_baseline(test_case_id: str, window_days: int = 30) -> Dict:
    """Rolling 30-day baseline for test execution."""
    cutoff = datetime.utcnow() - timedelta(days=window_days)
    
    runs = await db.query(Run).filter(
        Run.test_case_id == test_case_id,
        Run.created_at > cutoff,
        Run.status == "PASSED",  # Only successful runs
    ).all()
    
    durations = [run.duration_seconds for run in runs]
    
    return {
        "mean": statistics.mean(durations),
        "stddev": statistics.stdev(durations) if len(durations) > 1 else 0,
        "p95": sorted(durations)[int(len(durations) * 0.95)],
        "sample_size": len(durations),
    }

async def detect_performance_anomalies(run_id: str):
    """Check if any test in run is slower than baseline."""
    run = await db.get(Run, run_id)
    
    for step in run.steps:
        baseline = await calculate_execution_baseline(step.test_case_id)
        
        # >20% slower = anomaly
        if step.duration_seconds > baseline["mean"] * 1.2:
            anomaly = PerformanceAnomaly(
                test_case_id=step.test_case_id,
                run_id=run_id,
                expected_duration=baseline["mean"],
                actual_duration=step.duration_seconds,
                anomaly_severity=min(
                    (step.duration_seconds - baseline["mean"]) / baseline["stddev"],
                    10.0  # Cap at 10 stddevs
                ),
                created_at=datetime.utcnow(),
            )
            await db.add(anomaly)
    
    await db.commit()
```

**Time Estimate:** 200 lines backend, 180 lines frontend → 3 weeks

---

## TRACK 2: GraphQL API (Q3 2027)

### 2.1 Core Schema & Resolvers

**Objective:** Modern GraphQL API alongside REST (backward compatibility).

**Schema (200+ types):**
```graphql
type Query {
  # Projects
  project(id: ID!): Project
  projects(filter: ProjectFilter, limit: Int, offset: Int): ProjectConnection!
  
  # Test Cases
  testCase(id: ID!): TestCase
  testCases(projectId: ID!, filter: TestCaseFilter): TestCaseConnection!
  
  # Runs
  run(id: ID!): Run
  runs(projectId: ID!, filter: RunFilter, limit: Int): RunConnection!
  
  # Defects
  defect(id: ID!): Defect
  defects(projectId: ID!, filter: DefectFilter): DefectConnection!
  
  # Analytics
  projectMetrics(projectId: ID!, dateRange: DateRange!): ProjectMetrics!
  testCaseMetrics(testCaseId: ID!, dateRange: DateRange!): TestCaseMetrics!
  
  # Search
  search(query: String!, scope: SearchScope): SearchResult!
}

type Mutation {
  # Projects
  createProject(input: CreateProjectInput!): Project!
  updateProject(id: ID!, input: UpdateProjectInput!): Project!
  
  # Test Cases
  createTestCase(input: CreateTestCaseInput!): TestCase!
  updateTestCase(id: ID!, input: UpdateTestCaseInput!): TestCase!
  
  # Runs
  createRun(input: CreateRunInput!): Run!
  submitRun(id: ID!): Run!
  
  # Defects
  createDefect(input: CreateDefectInput!): Defect!
  mergeDefects(parentId: ID!, childId: ID!): Defect!
  
  # Bulk
  bulkCreateTestCases(input: [CreateTestCaseInput!]!): [TestCase!]!
  bulkUpdateTestCases(input: [UpdateTestCaseInput!]!): [TestCase!]!
}

type Subscription {
  # Real-time updates
  projectUpdated(projectId: ID!): Project!
  runStarted(projectId: ID!): Run!
  runCompleted(runId: ID!): Run!
  defectCreated(projectId: ID!): Defect!
}
```

**Architecture:**
```
Next.js/Frontend → GraphQL Gateway (FastAPI Strawberry)
                        ↓
                    Resolvers (typed)
                        ↓
                    Service Layer (existing)
                        ↓
                    Database (PostgreSQL + Redis)
```

**Implementation:**

**Backend (1200 lines):**
```python
# domains/graphql/schema.py
import strawberry
from typing import List, Optional
from datetime import datetime

@strawberry.type
class Project:
    id: str
    name: str
    description: Optional[str]
    organization_id: str
    created_at: datetime
    updated_at: datetime
    
    @strawberry.field
    async def test_cases(self) -> List["TestCase"]:
        # Resolver
        return await get_test_cases(self.id)
    
    @strawberry.field
    async def runs(self, limit: int = 10) -> List["Run"]:
        return await get_recent_runs(self.id, limit)
    
    @strawberry.field
    async def metrics(
        self,
        date_range: "DateRange",
    ) -> "ProjectMetrics":
        return await calculate_metrics(self.id, date_range)

@strawberry.type
class TestCase:
    id: str
    project_id: str
    title: str
    description: Optional[str]
    created_at: datetime
    
    @strawberry.field
    async def latest_run(self) -> Optional["Run"]:
        return await get_latest_run(self.id)

@strawberry.type
class Run:
    id: str
    project_id: str
    test_case_id: str
    status: str
    duration_seconds: float
    created_at: datetime
    
    @strawberry.field
    async def steps(self) -> List["Step"]:
        return await get_run_steps(self.id)
    
    @strawberry.field
    async def defects(self) -> List["Defect"]:
        return await get_defects_for_run(self.id)

@strawberry.input
class ProjectFilter:
    name: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

@strawberry.type
class Query:
    @strawberry.field
    async def project(
        self,
        info,
        id: str,
    ) -> Optional[Project]:
        user = get_current_user(info)
        return await get_project(id, user.org_id)
    
    @strawberry.field
    async def projects(
        self,
        info,
        filter: Optional[ProjectFilter] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> "ProjectConnection":
        user = get_current_user(info)
        projects = await query_projects(
            user.org_id,
            filter,
            limit,
            offset,
        )
        total = await count_projects(user.org_id, filter)
        return ProjectConnection(
            edges=[ProjectEdge(node=p) for p in projects],
            page_info=PageInfo(
                has_next_page=offset + limit < total,
                has_previous_page=offset > 0,
            ),
        )
    
    @strawberry.field
    async def search(
        self,
        info,
        query: str,
        scope: str = "ALL",
    ) -> "SearchResult":
        user = get_current_user(info)
        
        # Full-text search
        if scope in ["ALL", "TEST_CASES"]:
            test_cases = await search_test_cases(user.org_id, query)
        if scope in ["ALL", "PROJECTS"]:
            projects = await search_projects(user.org_id, query)
        if scope in ["ALL", "DEFECTS"]:
            defects = await search_defects(user.org_id, query)
        
        return SearchResult(
            test_cases=test_cases,
            projects=projects,
            defects=defects,
        )

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_project(
        self,
        info,
        input: "CreateProjectInput",
    ) -> Project:
        user = get_current_user(info)
        require_permission(user, "project:create")
        
        project = await create_project_service(
            org_id=user.org_id,
            name=input.name,
            description=input.description,
        )
        return project
    
    @strawberry.mutation
    async def merge_defects(
        self,
        info,
        parent_id: str,
        child_id: str,
    ) -> Defect:
        user = get_current_user(info)
        parent = await get_defect(parent_id)
        require_permission(user, f"project:{parent.project_id}:defect:edit")
        
        await merge_defects_service(parent_id, child_id, user.id)
        return await get_defect(parent_id)
    
    @strawberry.mutation
    async def bulk_create_test_cases(
        self,
        info,
        input: List["CreateTestCaseInput"],
    ) -> List[TestCase]:
        user = get_current_user(info)
        results = []
        
        for item in input:
            tc = await create_test_case_service(
                user.org_id,
                item.project_id,
                item.title,
                item.description,
            )
            results.append(tc)
        
        return results

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def run_completed(
        self,
        info,
        run_id: str,
    ) -> "Run":
        user = get_current_user(info)
        
        # Redis pub/sub
        async for message in subscribe_to_channel(f"run:{run_id}:complete"):
            run = await get_run(message["run_id"])
            if run.project_id in user.accessible_project_ids:
                yield run

# domains/graphql/router.py
from strawberry.fastapi import GraphQLRouter

schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)
graphql_router = GraphQLRouter(schema)

# Register in main.py
app.include_router(graphql_router, prefix="/graphql")
```

**Frontend Integration (300 lines):**
```typescript
// lib/graphql-client.ts
import { ApolloClient, InMemoryCache, HttpLink, WebSocketLink } from '@apollo/client';
import { split } from '@apollo/client';
import { getMainDefinition } from '@apollo/client/utilities';

const httpLink = new HttpLink({
  uri: '/api/graphql',
  credentials: 'include',
});

const wsLink = new WebSocketLink({
  uri: `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:3000'}/api/graphql`,
  options: {
    reconnect: true,
    connectionParams: {
      authorization: `Bearer ${localStorage.getItem('access_token')}`,
    },
  },
});

const splitLink = split(
  ({ query }) => {
    const definition = getMainDefinition(query);
    return (
      definition.kind === 'OperationDefinition' &&
      definition.operation === 'subscription'
    );
  },
  wsLink,
  httpLink,
);

export const apolloClient = new ApolloClient({
  link: splitLink,
  cache: new InMemoryCache(),
  defaultOptions: {
    watchQuery: {
      fetchPolicy: 'cache-and-network',
    },
  },
});

// hooks/useGraphQL.ts
import { gql, useQuery, useMutation, useSubscription } from '@apollo/client';

export const GET_PROJECT = gql`
  query GetProject($id: ID!) {
    project(id: $id) {
      id
      name
      description
      testCases(limit: 100) {
        id
        title
        latestRun {
          id
          status
          durationSeconds
        }
      }
      metrics(dateRange: { from: "2024-06-01", to: "2024-06-30" }) {
        passRate
        totalRuns
        avgDuration
      }
    }
  }
`;

export const useProject = (projectId: string) => {
  const { data, loading, error } = useQuery(GET_PROJECT, {
    variables: { id: projectId },
  });
  
  return {
    project: data?.project,
    loading,
    error,
  };
};

export const SUBSCRIBE_RUN_COMPLETED = gql`
  subscription OnRunCompleted($runId: ID!) {
    runCompleted(runId: $runId) {
      id
      status
      durationSeconds
      steps {
        id
        status
      }
    }
  }
`;

export const useRunCompletedSubscription = (runId: string) => {
  const { data } = useSubscription(SUBSCRIBE_RUN_COMPLETED, {
    variables: { runId },
  });
  
  return data?.runCompleted;
};

// components/ProjectDashboard.tsx
export const ProjectDashboard: React.FC<{ projectId: string }> = ({
  projectId,
}) => {
  const { project, loading } = useProject(projectId);
  
  if (loading) return <div>Loading...</div>;
  
  return (
    <div>
      <h1>{project.name}</h1>
      <div className="grid grid-cols-3 gap-4">
        <div>Pass Rate: {(project.metrics.passRate * 100).toFixed(1)}%</div>
        <div>Total Runs: {project.metrics.totalRuns}</div>
        <div>Avg Duration: {project.metrics.avgDuration.toFixed(1)}s</div>
      </div>
      <div className="mt-8">
        {project.testCases.map(tc => (
          <TestCaseRow key={tc.id} testCase={tc} />
        ))}
      </div>
    </div>
  );
};
```

**Tests:**
```python
# tests/integration/test_graphql.py
@pytest.mark.asyncio
async def test_graphql_query_project():
    """Basic GraphQL project query."""
    query = """
    {
      project(id: "proj1") {
        id
        name
        testCases {
          id
          title
        }
      }
    }
    """
    
    result = await execute_graphql_query(query, user=user1)
    assert result.data["project"]["id"] == "proj1"
    assert len(result.data["project"]["testCases"]) > 0

@pytest.mark.asyncio
async def test_graphql_mutation_merge_defects():
    """Test defect merge mutation."""
    mutation = """
    mutation {
      mergeDefects(parentId: "def1", childId: "def2") {
        id
        mergedDefectCount
      }
    }
    """
    
    result = await execute_graphql_mutation(mutation, user=user1)
    assert result.data["mergeDefects"]["mergedDefectCount"] == 1

@pytest.mark.asyncio
async def test_graphql_subscription_run_completed():
    """Real-time subscription to run completion."""
    subscription = """
    subscription {
      runCompleted(runId: "run1") {
        id
        status
        steps {
          id
          status
        }
      }
    }
    """
    
    messages = []
    async for msg in execute_graphql_subscription(subscription):
        messages.append(msg)
        if msg.data["runCompleted"]["status"] == "COMPLETED":
            break
    
    assert len(messages) > 0
    assert messages[-1].data["runCompleted"]["status"] == "COMPLETED"
```

**Deployment:**
- Week 1–2: Schema design + core types + resolvers
- Week 3–4: Authentication + authorization + pagination
- Week 5: Subscriptions (WebSocket) + testing
- Week 6: Frontend integration + Apollo setup
- Week 7: Documentation + API playground (Apollo Studio)

**Success Metrics:**
- [ ] 200+ GraphQL types implemented
- [ ] Query performance <500ms (with caching)
- [ ] Subscription real-time latency <1s
- [ ] Apollo Studio playground live
- [ ] 30%+ of API calls migrate to GraphQL (measured at M3)

---

### 2.2 Batch Operations & Optimizations

**Features:**
- Batch query (fetch 10+ resources in 1 request)
- DataLoader (prevent N+1 queries)
- Query complexity scoring (prevent DoS)
- Caching layer (Redis)

**Implementation:**
```python
# domains/graphql/dataloader.py
from promise import Promise
from promise.dataloader import DataLoader

class TestCaseLoader(DataLoader):
    async def batch_load_fn(self, test_case_ids):
        """Batch load test cases (prevent N+1)."""
        test_cases = await db.query(TestCase).filter(
            TestCase.id.in_(test_case_ids)
        ).all()
        
        # Return in order of request
        lookup = {tc.id: tc for tc in test_cases}
        return [lookup.get(id) for id in test_case_ids]

class ProjectMetricsLoader(DataLoader):
    async def batch_load_fn(self, project_ids):
        """Batch calculate metrics."""
        metrics = await db.query(ProjectMetrics).filter(
            ProjectMetrics.project_id.in_(project_ids)
        ).all()
        
        lookup = {m.project_id: m for m in metrics}
        return [lookup.get(id) for id in project_ids]

@strawberry.type
class Query:
    @strawberry.field
    async def projects(
        self,
        info,
        ids: List[str],
    ) -> List[Project]:
        """Batch query projects."""
        loader: TestCaseLoader = info.context["loader"]
        projects = await loader.load_many(ids)
        return projects
```

**Time Estimate:** 250 lines → 2 weeks

---

## TRACK 3: MULTI-REGION DEPLOYMENT (Q3–Q4 2027)

### 3.1 Architecture Overview

```
AWS Regions (US-East, EU-West, AP-Southeast)
        ↓
PostgreSQL Primary (us-east-1)
        ↓
Logical Replication ↙ ↓ ↘
        ↓
Standby (eu-west-1) ← read replicas
Standby (ap-south-1) ← read replicas
        ↓
Failover (automated) — if primary unhealthy → promote replica
        ↓
Application routing (CloudFront + Route53 geo-routing)
        ↓
Replication lag monitoring (<100ms SLA)
```

### 3.2 Database Replication Setup

**Architecture:**

1. **Primary (US):** Read-write, master changeset
2. **Replicas (EU, APAC):** Read-only, apply changes from primary
3. **Logical replication:** Stream changes via WAL (write-ahead log)
4. **Failover:** Automated via Patroni (HA cluster manager)

**Implementation:**

**PostgreSQL Configuration:**
```sql
-- Primary (us-east-1)
ALTER SYSTEM SET wal_level = logical;
ALTER SYSTEM SET max_wal_senders = 10;
ALTER SYSTEM SET max_replication_slots = 10;
SELECT pg_ctl_reload_conf();

-- Create replication slot
SELECT pg_create_logical_replication_slot('eu_replica', 'pgoutput');
SELECT pg_create_logical_replication_slot('ap_replica', 'pgoutput');

-- Replica (eu-west-1) — subscribe to primary
CREATE SUBSCRIPTION eu_sub
CONNECTION 'host=primary.us-east-1.rds.amazonaws.com user=repl password=xxx'
PUBLICATION neurex_pub
FOR ALL TABLES;

-- Monitor lag
SELECT slot_name, restart_lsn, confirmed_flush_lsn
FROM pg_replication_slots;
```

**Monitoring (Python service):**
```python
# services/replication_monitor.py
async def check_replication_lag():
    """Monitor replication lag across regions."""
    regions = ["eu-west-1", "ap-south-1"]
    
    for region in regions:
        lag_bytes = await get_replication_lag(region)
        lag_seconds = lag_bytes / (1024 * 1024)  # Rough estimate
        
        # Alert if >100ms
        if lag_seconds > 0.1:
            await alert(
                f"Region {region} replication lag: {lag_seconds*1000:.1f}ms"
            )
        
        # Log metric
        await log_metric(
            "replication_lag_ms",
            lag_seconds * 1000,
            tags={"region": region}
        )

async def monitor_replica_health():
    """Check if replicas are healthy."""
    for region in REGIONS:
        try:
            health = await query_replica_health(region)
            
            if not health["connected"]:
                await trigger_failover(region)
        except Exception as e:
            await alert(f"Region {region} unhealthy: {e}")
```

**Failover Automation (using Patroni):**
```yaml
# patroni.yml
scope: neurex-cluster
namespace: /neurex/
name: primary

postgresql:
  data_dir: /var/lib/postgresql/14/main
  pgpass: /var/lib/postgresql/.pgpass
  parameters:
    wal_level: logical
    max_wal_senders: 10
    synchronous_commit: remote_apply  # Wait for replicas

ha:
  klusterkit_auto_failover: true
  failover_timeout: 300  # 5 min failover SLA
  postgresql_start_timeout: 300

dcs:
  type: consul
  host: consul.us-east-1.internal
  datacenter: us-east-1
```

**Application-Level Failover:**
```python
# infra/database.py
from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool

class MultiRegionPool:
    def __init__(self):
        self.engines = {
            "us-east-1": create_engine(
                "postgresql://user:pwd@primary.us-east-1.rds.amazonaws.com/neurex"
            ),
            "eu-west-1": create_engine(
                "postgresql://user:pwd@replica.eu-west-1.rds.amazonaws.com/neurex"
            ),
            "ap-south-1": create_engine(
                "postgresql://user:pwd@replica.ap-south-1.rds.amazonaws.com/neurex"
            ),
        }
        self.primary_region = "us-east-1"
        self.replica_regions = ["eu-west-1", "ap-south-1"]
        self.current_region = os.getenv("AWS_REGION", "us-east-1")
    
    async def get_engine(self, is_write: bool = False):
        """Get appropriate engine (write=primary, read=replica)."""
        if is_write:
            # Always use primary
            return self.engines[self.primary_region]
        else:
            # Use replica in same region if available
            if self.current_region in self.engines:
                return self.engines[self.current_region]
            # Fallback to primary
            return self.engines[self.primary_region]
    
    async def test_connection(self, region: str) -> bool:
        """Test if region is healthy."""
        try:
            with self.engines[region].connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    async def handle_failover(self):
        """Detect and handle failover."""
        if not await self.test_connection(self.primary_region):
            # Primary down — promote replica
            for replica in self.replica_regions:
                if await self.test_connection(replica):
                    self.primary_region = replica
                    await alert(f"Failover: {replica} promoted to primary")
                    break

# Usage in FastAPI deps
async def get_db_session(is_write: bool = False):
    """Get DB session (read/write aware)."""
    pool = get_global_pool()
    engine = await pool.get_engine(is_write)
    
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()

# Decorator for write operations
@require_primary
async def create_project(session: Session, ...):
    """This route requires primary connection."""
    ...
```

**Time Estimate:** Week 1–3 (complex infra work)

---

### 3.3 Data Residency & Compliance

**Features:**

- **EU Data Residency:** GDPR-compliant EU-only deployments
- **Data Localization:** Encrypt PII with region-specific keys
- **Audit Trail:** All data access logged by region + user
- **Export/Erasure:** Automated GDPR compliance

**Implementation:**
```python
# domains/compliance/residency_service.py
async def enforce_data_residency(user: User, resource: BaseModel):
    """Ensure resource respects user's data residency preference."""
    residency_pref = user.data_residency_region  # "US", "EU", "APAC"
    current_region = os.getenv("AWS_REGION")
    
    if residency_pref != "ANY" and current_region != map_region(residency_pref):
        raise PermissionError(
            f"Cannot access {resource.type} from {current_region}. "
            f"User data residency: {residency_pref}"
        )

async def anonymize_pii_for_export(user_id: str) -> Dict:
    """GDPR export: return all user data, anonymized."""
    user = await db.get(User, user_id)
    
    export = {
        "user": {
            "id": user.id,
            "email": "[REDACTED]",
            "created_at": user.created_at,
        },
        "projects": [],
        "runs": [],
        "defects": [],
    }
    
    for project in user.projects:
        export["projects"].append({
            "id": project.id,
            "name": project.name,
        })
    
    return export

async def delete_user_data(user_id: str) -> bool:
    """GDPR right to erasure."""
    # Delete projects
    projects = await db.query(Project).filter(Project.creator_id == user_id)
    for project in projects:
        await db.delete(project)
    
    # Delete user
    user = await db.get(User, user_id)
    await db.delete(user)
    
    # Log erasure for audit
    await log_gdpr_action(
        action="USER_ERASURE",
        user_id=user_id,
        timestamp=datetime.utcnow(),
        region=os.getenv("AWS_REGION"),
    )
    
    return True
```

**Time Estimate:** 300 lines → 2 weeks

---

### 3.4 Deployment & Monitoring

**Terraform Infrastructure:**
```hcl
# terraform/multi-region/main.tf
terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

# Primary region (us-east-1)
provider "aws" {
  alias  = "primary"
  region = "us-east-1"
}

resource "aws_rds_cluster" "primary" {
  provider            = aws.primary
  cluster_identifier  = "neurex-primary"
  engine              = "aurora-postgresql"
  master_username     = "admin"
  master_password     = random_password.db_password.result
  database_name       = "neurex"
  backup_retention_period = 30
  
  enabled_cloudwatch_logs_exports = ["postgresql"]
}

resource "aws_rds_cluster_instance" "primary_instance" {
  provider           = aws.primary
  cluster_identifier = aws_rds_cluster.primary.id
  instance_class     = "db.r6g.xlarge"
  engine              = "aurora-postgresql"
}

# Secondary region (eu-west-1) — read replica
provider "aws" {
  alias  = "secondary"
  region = "eu-west-1"
}

resource "aws_rds_cluster" "secondary" {
  provider                  = aws.secondary
  cluster_identifier        = "neurex-secondary"
  replication_source_identifier = aws_rds_cluster.primary.arn
  skip_final_snapshot       = true
}

# Failover configuration
resource "aws_rds_cluster_instance" "secondary_instance" {
  provider           = aws.secondary
  cluster_identifier = aws_rds_cluster.secondary.id
  instance_class     = "db.r6g.xlarge"
  promotion_tier     = 1  # Can be promoted to primary
}
```

**Monitoring Dashboard:**
```python
# monitoring/multi_region_dashboard.py
async def get_region_health() -> Dict:
    """Multi-region health snapshot."""
    health = {}
    
    for region in ["us-east-1", "eu-west-1", "ap-south-1"]:
        status = await check_region_health(region)
        
        health[region] = {
            "db_healthy": status["db_healthy"],
            "replication_lag_ms": status["replication_lag_ms"],
            "api_latency_p95_ms": status["api_latency_p95"],
            "error_rate_pct": status["error_rate"],
            "last_check": datetime.utcnow(),
        }
    
    return health

# FastAPI endpoint
@app.get("/api/v1/infra/region-health")
async def region_health(current_user: User = Depends(get_current_user)):
    """Region health for monitoring dashboard."""
    if not current_user.is_admin:
        raise PermissionError
    
    return await get_region_health()
```

**Time Estimate:** Week 4–6 (deployment + testing)

---

## TRACK 4: NATIVE MOBILE OPTIMIZATION (Q3–Q4 2027)

### 4.1 iOS SwiftUI Rewrite (Optional)

**Objective:** If React Native proves insufficient, rewrite iOS in SwiftUI for native performance.

**Features:**
- SwiftUI UI (native look & feel)
- Fast animations (60 FPS+)
- Apple-exclusive: Siri Shortcuts, Focus modes, Dynamic Island
- Xcode integration for debugging

**Implementation Plan (if triggered):**
```swift
// iOS/Neurex/Views/ProjectListView.swift
import SwiftUI

struct ProjectListView: View {
    @StateObject var viewModel = ProjectListViewModel()
    @State var selectedProject: Project?
    
    var body: some View {
        NavigationStack(path: $viewModel.navigationPath) {
            List(viewModel.projects) { project in
                NavigationLink(value: project) {
                    ProjectRow(project: project)
                        .onAppear {
                            viewModel.trackProjectView(project)
                        }
                }
            }
            .navigationTitle("Projects")
            .navigationDestination(for: Project.self) { project in
                ProjectDetailView(project: project)
            }
            .refreshable {
                await viewModel.loadProjects()
            }
            .task {
                await viewModel.loadProjects()
            }
        }
    }
}

// Siri Shortcuts support
struct SiriShortcutsIntegration {
    static func registerIntents() {
        // "Run test case [name]"
        let runTestIntent = INIntent()
        
        // "Show project [name]"
        let showProjectIntent = INIntent()
        
        // "Create defect with [title]"
        let createDefectIntent = INIntent()
    }
}

// Dynamic Island support (iPhone 14+)
struct DynamicIslandWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: RunActivityAttributes.self) { context in
            // Live activity on Dynamic Island
            VStack(spacing: 2) {
                HStack {
                    Text(context.attributes.runName)
                    Spacer()
                    Text("\(context.state.progress)%")
                }
                ProgressView(value: context.state.progress)
            }
            .padding()
        }
    }
}
```

**Effort:** 8–10 weeks (only if React Native insufficient)  
**Cost:** $180K–$220K (2 senior iOS devs)

---

### 4.2 Android Jetpack Compose Optimization

**Objective:** Modernize Android with Jetpack Compose (instead of XML layouts).

**Features:**
- Compose UI (declarative, modern)
- Material You theming (Android 12+)
- Widgets (test execution, notifications)
- Performance optimizations

**Implementation Plan (if needed):**
```kotlin
// Android/app/src/main/java/com/neurex/ui/ProjectListScreen.kt
@Composable
fun ProjectListScreen(
    navController: NavController,
    viewModel: ProjectListViewModel = hiltViewModel(),
) {
    val projects by viewModel.projects.collectAsState()
    val loading by viewModel.loading.collectAsState()
    
    if (loading) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
    } else {
        LazyColumn {
            items(projects) { project ->
                ProjectCard(
                    project = project,
                    onClick = {
                        navController.navigate("project/${project.id}")
                    }
                )
            }
        }
    }
}

// Material You theming
@Composable
fun NeurexTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val dynamicColor = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
    
    val colorScheme = when {
        dynamicColor && darkTheme -> dynamicDarkColorScheme(LocalContext.current)
        dynamicColor && !darkTheme -> dynamicLightColorScheme(LocalContext.current)
        darkTheme -> darkColorScheme()
        else -> lightColorScheme()
    }
    
    MaterialTheme(
        colorScheme = colorScheme,
        content = content,
    )
}

// Android Widget for test execution
class TestExecutionWidget : GlanceAppWidget() {
    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val run by context.dataStore.data.map { it["currentRun"] }.collectAsState(null)
        
        provideContent {
            Box(
                modifier = GlanceModifier
                    .fillMaxSize()
                    .background(ColorProvider(R.color.widget_bg))
                    .padding(12.dp)
            ) {
                if (run != null) {
                    Column {
                        Text(run.testCaseName)
                        LinearProgressIndicator(
                            progress = run.progress.toFloat() / 100,
                            modifier = GlanceModifier.fillMaxWidth()
                        )
                        Text("${run.progress}%")
                    }
                }
            }
        }
    }
}
```

**Effort:** 6–8 weeks (if needed)  
**Cost:** $140K–$180K (2 senior Android devs)

---

## TRACK 5: Q1 ENHANCEMENTS & CONTINUOUS DELIVERY

### 5.1 Advanced Test Design Techniques

**Pairwise Testing Automation:**
```python
# domains/tspm/pairwise_service.py
async def generate_pairwise_test_cases(
    parameters: Dict[str, List[str]]
) -> List[Dict[str, str]]:
    """Auto-generate minimal test cases covering parameter pairs."""
    # Example: Browser × OS × Network
    # Input: {browser: [Chrome, Safari], os: [macOS, Windows], network: [4G, WiFi]}
    # Output: Minimal set covering all pairs
    
    from allpairspy import AllPairs
    
    pairwise_set = AllPairs(parameters)
    test_cases = list(pairwise_set)
    
    return [dict(zip(parameters.keys(), case)) for case in test_cases]
```

### 5.2 Continuous ML Model Retraining

**Weekly Pipeline:**
- Collect new training data from production runs
- Retrain auto-fix + predictive selection models
- A/B test new model version on 10% cohort
- Deploy if >5% improvement

**Implementation:**
```python
# services/ml_retraining.py
async def weekly_model_retraining():
    """Scheduled job: retrain ML models."""
    # Collect data from past week
    recent_runs = await db.query(Run).filter(
        Run.created_at > datetime.utcnow() - timedelta(days=7)
    )
    
    # Train
    autofix_model = train_autofix_model(recent_runs)
    predictive_model = train_predictive_selection_model(recent_runs)
    
    # A/B test
    await deploy_model_version(
        autofix_model,
        version="v1.1",
        cohort_pct=10,  # 10% of users
    )
    
    # Monitor metrics
    await monitor_model_performance("autofix_v1.1")
```

---

## IMPLEMENTATION ROADMAP

### Phase Timeline

```
Q2 2027 (May–June)
├─ Track 1.1: Auto-Fix Suggestions (6 weeks)
├─ Track 1.2: Smart Defect Grouping (4 weeks, parallel)
└─ Track 3.1: Multi-Region DB Replication (6 weeks, parallel)

Q3 2027 (July–September)
├─ Track 1.3: Predictive Test Selection (4 weeks)
├─ Track 1.4: Performance Anomaly Detection (4 weeks, parallel)
├─ Track 2.1: GraphQL Core API (8 weeks, parallel)
└─ Track 4.1/4.2: Mobile Optimization (if needed, 8–10 weeks)

Q4 2027 (October–December)
├─ Track 2.2: Batch Operations & Caching (4 weeks)
├─ Track 3.2–3.4: Data Residency & Monitoring (6 weeks, parallel)
└─ Q1 Enhancements: ML Retraining, Advanced Design Techniques (ongoing)
```

### Resource Allocation

```
Track 1 (Advanced AI):
  ├─ Backend Lead: 1 FTE (6 months)
  ├─ ML Engineer: 1 FTE (6 months)
  └─ Frontend: 0.5 FTE (3 months)

Track 2 (GraphQL):
  ├─ Backend Engineer: 1.5 FTE (3 months)
  └─ Frontend Engineer: 1 FTE (2 months)

Track 3 (Multi-Region):
  ├─ DevOps Engineer: 1.5 FTE (3 months)
  ├─ Backend Engineer: 0.5 FTE (2 months)
  └─ Security Engineer: 0.5 FTE (1 month)

Track 4 (Mobile Optimization, optional):
  ├─ iOS Engineer: 1 FTE (if triggered, 2.5 months)
  └─ Android Engineer: 1 FTE (if triggered, 2 months)

Total: 4–6 FTE (distributed)
```

---

## BUSINESS IMPACT & ROI

### Revenue Model

| Feature | Pricing Tier | Est. Users | Price/Month | Monthly Revenue |
|---------|-------------|-----------|------------|-----------------|
| Auto-Fix (Premium) | $299/team | 500 teams | $299 | $149.5K |
| Smart Grouping (Premium) | Included | 500 teams | $0 | $0 |
| GraphQL API (Enterprise) | $499/org | 100 orgs | $499 | $49.9K |
| Multi-Region (Enterprise) | +$199/month | 50 orgs | $199 | $9.95K |
| Native Mobile (Premium) | $99/user | 5K users | $99 | $495K |
| **Total Monthly** | — | — | — | **$704.35K** |
| **Annual** | — | — | — | **$8.45M** |

### Cost Model

| Item | Monthly Cost | Notes |
|------|-------------|-------|
| Team (6 FTE @ $15K/mo) | $90K | Distributed |
| Infrastructure (multi-region) | $45K | AWS RDS + compute |
| ML Training (compute) | $8K | Weekly retraining |
| Monitoring + Alerting | $5K | Datadog, Sentry |
| **Total Monthly** | **$148K** | |
| **Annual** | **$1.776M** | |

### Profitability

```
Annual Revenue: $8.45M
Annual Cost: $1.776M
Gross Profit: $6.674M (78.9%)
Payback Period: 2.5 months
```

---

## RISK ASSESSMENT

### High-Risk Items

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| ML model false positives (auto-fix) | Medium (40%) | High | A/B testing, user feedback loop, confidence thresholds |
| Multi-region replication lag >100ms | Low (15%) | High | AWS read replicas, Patroni failover, test under load |
| GraphQL N+1 query performance | Medium (35%) | Medium | DataLoader pattern, query complexity scoring, monitoring |
| Mobile native rewrite complexity | Low (10%) | High | Keep React Native as fallback, phased SwiftUI migration |

### Mitigation Strategies

1. **Feature Flags:** All AI features behind flags (A/B test cohorts)
2. **Gradual Rollout:** 10% → 25% → 100% user base
3. **Fallback Modes:** GraphQL → REST if needed, replica → primary if lag >100ms
4. **Monitoring:** Real-time dashboards for all 4 tracks

---

## SUCCESS CRITERIA

### Metrics per Track

**Track 1 (Advanced AI):**
- [ ] Auto-fix confidence >85% (false positives <2%)
- [ ] 40%+ user adoption of auto-fix
- [ ] 70%+ of applied fixes pass next run
- [ ] Defect merge accuracy >90%
- [ ] Predictive selection recall >80%
- [ ] Anomaly detection true positive rate >75%

**Track 2 (GraphQL):**
- [ ] 200+ types implemented
- [ ] Query latency <500ms (p95)
- [ ] Subscription real-time <1s latency
- [ ] Apollo Studio playground live & documented
- [ ] 30%+ API calls migrate to GraphQL (by M3)

**Track 3 (Multi-Region):**
- [ ] Replication lag <100ms (all regions)
- [ ] Failover time <5 minutes
- [ ] 99.99% uptime (4 nines)
- [ ] GDPR compliance verified
- [ ] Data residency enforced 100%

**Track 4 (Mobile Optimization, optional):**
- [ ] iOS: Siri Shortcuts working
- [ ] Android: Compose migration >70%
- [ ] Performance: 60 FPS (smooth)
- [ ] App store rating >4.5/5

---

## CONCLUSION

These 4 concurrent workstreams position Neurex as a comprehensive QA platform with enterprise features, modern APIs, and global infrastructure. Combined with existing platform maturity (Phase 0–3), this roadmap unlocks $8.45M+ ARR and 50K+ users.

**Next Steps:**
1. Engineering leadership review (1 week)
2. Finalize Q2 2027 sprint plans
3. Hire team leads (5 FTE)
4. Begin Track 1.1 (auto-fix) in May 2027
5. Monthly steering reviews

---

**Document prepared:** 2026-06-09  
**Status:** Ready for stakeholder review & approval
