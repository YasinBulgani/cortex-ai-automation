# LLM Integration Strategy — Neurex QA Platform
## Synthesized from 9 Expert Analyses | 20 Integration Areas | 6-Month Roadmap

**Date:** 2026-06-09  
**Status:** Strategy & Recommendations (Pre-Implementation)  
**Scope:** Backend (FastAPI) + Frontend (Next.js) + Engine (Flask) + AI Gateway integration

---

## Executive Summary

### Value Proposition
Neurex can **5-35x accelerate QA workflows** by integrating LLMs across 20 strategic areas:
- **Test creation:** 8h → 2h per epic (5-6x)
- **RCA analysis:** 180min → 12min (15x)
- **Flaky test fixing:** 8h → 1h (8x)
- **Release readiness:** Manual → AI-scored (50% decision time saved)
- **Cost reduction:** 30-40% LLM API savings via optimization + caching

### Risk Landscape
**Critical:** Prompt injection (LLM modifies requirements/code), data privacy (test data leakage), context window explosion (10k+ token runaway).  
**Mitigation:** RLS enforcement, confidence thresholds, token budgets, human approval gates.

### Recommended Phases
| Phase | Duration | Features | ARR Impact |
|-------|----------|----------|-----------|
| **MVP (Phase 1)** | 2 months | NL→BDD, RCA, coverage gaps, flaky detection, test code gen | $300K (200 customers) |
| **Phase 2** | 2 months | Self-healing, regression ranking, synthetic data, security audit | $1.2M (400 customers) |
| **Phase 3** | 2 months | Agentic orchestration, mobile, fine-tuned models | $5M+ (1000+ customers) |

---

## Architecture & Integration Patterns

### 1. Service Layer Design (Faz 0-3 Foundation)

#### Current State
- 53 domains (DDD bounded contexts)
- 6 fully async (auth/tm/tspm/automation/agents/cicd)
- 47 partial/sync (migration path needed)
- Circuit breaker + timeout budgets deployed
- Outbox relay for event delivery (guaranteed)

#### Recommended Evolution
```
Tier 1: Universal Async Service Layer (2-3 weeks)
├─ All endpoints: async def instead of sync
├─ AsyncSession from get_async_db()
├─ Tenant-aware RLS enforcement
└─ Resilience-injected (circuit breaker, timeout)

Tier 2: Caching Layer (1-2 weeks)
├─ HTTP (public data) + App-level (Redis)
├─ Event-driven invalidation
├─ TTL-based cleanup
└─ Read-replica sticky reads (Faz 3.1)

Tier 3: Queue Consolidation (2-3 weeks)
├─ Tier 1: In-process BackgroundTasks (light)
├─ Tier 2: Redis RQ (durable jobs)
├─ Tier 3: APScheduler (recurring)
└─ Tier 4: Outbox Relay (guaranteed events)

Tier 4: Rate Limiting & Quota (1-2 weeks)
├─ Per-tenant API quotas (requests/hour)
├─ Per-tenant AI token budgets (monthly)
├─ Per-tool rate limits (10/min per user)
└─ Cost alerts ($500/day threshold)

Tier 5: Audit & Compliance (1 week)
├─ api_request_log (immutable audit trail)
├─ audit_event (compliance-ready)
└─ Automatic retention + redaction
```

### 2. LLM Orchestration & Tool-Use Architecture

#### Orchestrator Agent (QAOrchestrator)
```python
# Pattern: Plan → Execute → Verify → (conditional Replan)
async def orchestrate_qa_workflow(db, project_id, goals):
    plan = await llm_agent.plan(goals)  # Tool: get_coverage_gaps, get_recent_failures
    
    for attempt in range(max_replans=2):
        results = await execute_plan(db, plan)  # Parallel tool calls
        verification = await verify(db, results)  # Tool: analyze_test_flakiness
        
        if verification.meets_goals:
            return results
        plan = await replan(db, plan, verification.feedback)  # Conditional replan
    
    return results  # Exit after 2 replans
```

#### Tool Registry Pattern
```python
# app/domains/ai/tools.py (Pydantic + native Claude/GPT-4 support)
@tool_registry
class TestGenerationTools:
    @tool_callable(confidence_threshold=0.80)
    async def get_coverage_gaps(project_id: str, tenant_id: str) -> List[Gap]:
        """Tool: Identify uncovered requirements"""
        # Validated inputs; RLS enforced; confidence scoring
        
    @tool_callable(confidence_threshold=0.85, approval_required=True)
    async def create_test_scenario(scenario: TestScenario) -> TestCase:
        """Tool: Create test case (mutation; requires approval)"""
        # Gate: confidence >= 85% AND user approval AND rate limit
        
# Usage by LLM:
# {
#   "type": "tool_use",
#   "name": "get_coverage_gaps",
#   "input": {"project_id": "proj_123"}
# }
# Response: embedded in conversation; LLM processes + calls next tool
```

#### Hierarchical Context Management
```
Tier 1: Core Context (1k tokens)
├─ User role + permissions
├─ Project metadata
└─ Current task goal

Tier 2: Domain Context (3k tokens)
├─ Recent test executions
├─ Feature definitions
└─ Known flaky patterns

Tier 3: Project Context (5k tokens)
├─ All test metadata
├─ Coverage matrix
└─ Defect history

Tier 4: Dynamic Context (2k tokens)
├─ Current page DOM (playwright MCP)
├─ API response samples
└─ Code diff context

Tier 5: History Context (2k tokens, RAG fallback)
├─ Prior test runs
├─ Similar failures
└─ Past RCA insights

Strategy: Load Tiers 1-4 (~13k tokens base)
         If exceeds 80% of model max, drop Tier 4 → RAG only
         Fallback: Strip Tier 5 entirely if still exceeded
```

---

## The 20 LLM Integration Areas

### MVP (Phase 1): 7 Areas — Weeks 1-8

#### 1. **Test Scenario Auto-Generation (TDD/BDD)**
- **Type:** Agent + Tool-Use + Multi-Turn
- **Problem:** Manual test writing 8h/epic; coverage gaps
- **Solution:** LLM converts stories → Gherkin BDD + assertions + test data
- **Backend API:** `POST /api/v1/tests/generate` (202 Async)
- **Frontend:** Test Case Create UI + AI Suggestion Panel (confidence score + review gate)
- **Security:** Prompt injection (SQL in requirements) → validate Gherkin syntax + import linter
- **Cost:** $0.05-0.15/request; cache project stats (5min TTL)
- **Performance:** -500ms cached; -5s LLM
- **Success Criteria:** Generated tests pass >90% imports; >80% accuracy; adoption >40%
- **Effort:** 3w (UI 1w + LLM 1w + test 1w)

#### 2. **Defect Analysis & RCA**
- **Type:** Copilot + Agent + RAG
- **Problem:** Manual RCA 90-180min/failure; repeat failures missed
- **Solution:** LLM analyzes logs + screenshots + code diffs → suggest root cause + links
- **Backend API:** `POST /api/v1/runs/{run_id}/analyze` (Async)
- **Frontend:** Test Result Detail + AI RCA sidepanel (confidence <70% flags review)
- **Security:** Data privacy (logs contain user data) → mask sensitive values + RLS
- **Cost:** $0.05-0.10/analysis; cache logs (7d)
- **Performance:** -3-5s per analysis; instant if cached
- **Success Criteria:** RCA accuracy >80%; false positive <5%; time saved >70%
- **Effort:** 2w

#### 3. **Missing Test Case Suggestions**
- **Type:** Agent + RAG + Tool-Use
- **Problem:** Coverage gaps unknown; 45% avg requirement coverage
- **Solution:** Analyze requirements vs tests; suggest scenarios to close gaps
- **Backend API:** `POST /api/v1/coverage/suggest-tests` (Async)
- **Frontend:** Coverage Dashboard + Gap Widget (what-if simulator)
- **Security:** Business logic exposure → validate against requirement ID only
- **Cost:** Moderate ($0.08-0.12/project/day); cache (1h TTL)
- **Performance:** -2-3s per gap analysis; streamed to UI
- **Success Criteria:** Gap-driven tests close 80% of coverage gaps; adoption >60%
- **Effort:** 2w

#### 4. **Regression Suite Auto-Generation**
- **Type:** Agent + ML (predictive) + Tool-Use
- **Problem:** Test explosion (10k+ tests); manual selection slow (3h/sprint)
- **Solution:** Intelligent test selection based on code changes + failure patterns
- **Backend API:** `POST /api/v1/tests/select-regression` (202 Async)
- **Frontend:** Execution Plan widget + risk score badge + regression prediction
- **Security:** Code diff injection → validate against git history
- **Cost:** Moderate ($0.10/execution plan)
- **Performance:** -10s cached; -30s LLM prediction
- **Success Criteria:** Catch >95% of regressions; CI speedup >30%; adoption >50%
- **Effort:** 2w (partial; need ML model)

#### 5. **Automation Test Code Generation**
- **Type:** Agent + Tool-Use + Copilot
- **Problem:** Boilerplate writing; flaky locators; manual fixes 3-6h/iteration
- **Solution:** Generate Playwright code + auto-heal selectors
- **Backend API:** `POST /api/v1/automation/generate-code` (202 Async)
- **Frontend:** Automation Script Editor + locator fallback options
- **Security:** RCE risk (LLM-generated code execution) → sandbox + code review gate
- **Cost:** $0.08-0.20/script
- **Performance:** +5-15s (DOM analysis) but -90% manual editing
- **Success Criteria:** Generated tests pass >85% on first run; adoption >50%
- **Effort:** 3w

#### 6. **User Story → Test Case Transformation**
- **Type:** Agent + Tool-Use + Multi-Turn
- **Problem:** Manual test case creation from stories 4-6h; incomplete coverage
- **Solution:** Parse acceptance criteria → generate structured test cases + BDD scenarios
- **Backend API:** `POST /api/v1/stories/{story_id}/generate-tests` (202 Async)
- **Frontend:** Test Management UI + review/import flow
- **Security:** Story injection (malicious criteria) → syntax validation + peer review
- **Cost:** $0.05-0.10/story; cache templates
- **Performance:** -2-4s per story
- **Success Criteria:** Cover >95% of acceptance criteria; adoption >60%; time saved >50%
- **Effort:** 2w

#### 7. **Error/Bug Analysis & RCA** (see #2)
- Already detailed above
- **Priority:** P0 — blocks most workflows
- **Effort:** 2w

### Phase 2: 8 Areas — Weeks 9-16

#### 8. **Manual Test Scenario Enhancement**
- **Type:** Copilot + RAG
- **Problem:** Test incompleteness; assertion gaps; edge cases missed
- **Solution:** Analyze existing steps → suggest assertions + edge cases
- **Backend API:** `POST /api/v1/tests/{id}/enhance` (Async or Sync)
- **Frontend:** Test Case Edit UI + inline suggestions panel
- **Success Criteria:** Adoption >50%; false positive <5%
- **Effort:** 2w

#### 9. **API Test Scenario Suggestion**
- **Type:** Agent + Tool-Use
- **Problem:** Manual contract tests slow; low API coverage (45%)
- **Solution:** Parse OpenAPI 3.0 → generate contracts + payloads + assertions
- **Backend API:** `POST /api/v1/api-testing/generate-contracts` (202 Async)
- **Frontend:** API Testing UI + 'Generate from Spec' button
- **Security:** OpenAPI injection (spec modification) → validate against source
- **Success Criteria:** API coverage >85%; adoption >60%
- **Effort:** 2w

#### 10. **Log Analysis & Anomaly Detection**
- **Type:** Agent + Time-Series (ML)
- **Problem:** Log explosion (100k+ lines/run); manual analysis impossible
- **Solution:** Identify anomalies; detect performance regressions; predict failures
- **Backend API:** `POST /api/v1/logs/analyze` (Async)
- **Frontend:** Execution Dashboard + Anomalies section
- **Success Criteria:** Anomaly detection >80% accuracy; false alarms <10%
- **Effort:** 2w

#### 11. **Requirement Document Analysis & Test Mapping**
- **Type:** Agent + RAG + Document OCR
- **Problem:** Requirements not machine-readable; manual mapping tedious
- **Solution:** Analyze PDFs/Word → extract testable statements → map to tests
- **Backend API:** `POST /api/v1/requirements/analyze` (202 Async)
- **Frontend:** Requirements UI + traceability matrix + gap heatmap
- **Security:** Document injection (malicious requirements) → extract validation
- **Success Criteria:** Coverage >95%; gap identification >90%
- **Effort:** 3w

#### 12. **Screenshot → Test Scenario Extraction**
- **Type:** Copilot + Vision + Tool-Use
- **Problem:** Manual screenshot analysis tedious; missing interactions
- **Solution:** Analyze UI → identify elements → suggest scenarios + assertions
- **Backend API:** `POST /api/v1/screenshots/analyze` (202 Async)
- **Frontend:** Test Creation Wizard + element suggestions
- **Success Criteria:** Elements detected >90% accuracy; adoption >40%
- **Effort:** 2w

#### 13. **Service Response → Test Data Generation**
- **Type:** Agent + Tool-Use + Differential Privacy
- **Problem:** Manual test data creation tedious; PII concerns
- **Solution:** Analyze API responses → generate valid synthetic data (PII-safe)
- **Backend API:** `POST /api/v1/test-data/generate-from-response` (202 Async)
- **Frontend:** Test Data Generator UI + preview + export
- **Success Criteria:** Schema-valid 100%; PII-free >99.9%; audit-ready
- **Effort:** 3w

#### 14. **Risk Analysis & Release Readiness Scoring**
- **Type:** Agent + Predictive (ML)
- **Problem:** Release readiness unclear; production bugs frequent (12% escape)
- **Solution:** Analyze results + coverage + changes → risk score + go/no-go recommendation
- **Backend API:** `POST /api/v1/releases/analyze-readiness` (202 Async)
- **Frontend:** Release Dashboard + risk score + regression predictions
- **Security:** Risk assessment = release decision (critical) → high confidence thresholds
- **Success Criteria:** Risk accuracy >85%; regression catch >95%; adoption >70%
- **Effort:** 2w

#### 15. **Release Notes & Test Report Auto-Generation**
- **Type:** Copilot + Template-Based
- **Problem:** Manual release notes 2-3h; test reports low-signal
- **Solution:** Generate notes from tickets + test results + commit messages
- **Backend API:** `POST /api/v1/releases/generate-notes` (202 Async)
- **Frontend:** Release UI + preview + export (PDF/MD/HTML)
- **Success Criteria:** Publication-ready >95%; adoption >80%
- **Effort:** 1w

### Phase 3: 5 Areas — Weeks 17-24

#### 16. **Database Relationship Explanation & Query Assistant**
- **Type:** Copilot + RAG
- **Problem:** Complex schema; slow query authoring; N+1 queries
- **Solution:** Explain relationships; suggest optimized queries
- **Backend API:** `POST /api/v1/db/explain-schema` (Sync) + `/db/suggest-query` (202 Async)
- **Frontend:** QA Tools + DB Explorer + query suggestions
- **Success Criteria:** Adoption >60%; query time improved >20%
- **Effort:** 2w

#### 17. **SQL Suggestion & Query Optimization**
- **Type:** Copilot + Analysis
- **Problem:** Slow queries (>500ms); manual optimization hard
- **Solution:** Analyze plans; suggest rewrites + indexes
- **Backend API:** `POST /api/v1/db/optimize-query` (202 Async)
- **Frontend:** Query Optimizer panel + suggested rewrites
- **Success Criteria:** Query time improved >25%; index coverage >80%
- **Effort:** 2w

#### 18. **Project/Sprint Summary & Trend Analysis**
- **Type:** Agent + Time-Series (ML)
- **Problem:** Metrics not actionable; trends unclear; manual forecasting
- **Solution:** Analyze metrics → velocity forecast → trend explanations
- **Backend API:** `POST /api/v1/sprints/{sprint_id}/analyze` (202 Async)
- **Frontend:** Sprint Dashboard + AI Insights + forecasts
- **Success Criteria:** Forecast accuracy R² >0.80; adoption >70%
- **Effort:** 1w

#### 19. **User Segment-Based Intelligent Recommendations**
- **Type:** Agent + Personalization + RAG
- **Problem:** Users don't know features; low adoption; slow onboarding
- **Solution:** Learn user behavior → suggest relevant features + workflows
- **Backend API:** `POST /api/v1/recommendations/suggest` (Sync or 202 Async)
- **Frontend:** Contextual tips sidebar + feature suggestions
- **Success Criteria:** Feature adoption >50%; onboarding <30min; CSAT >4.0/5
- **Effort:** 2w

#### 20. **On-Screen AI Copilot Tooltip/Help**
- **Type:** Copilot + Context-Aware
- **Problem:** Users stuck; support tickets high; documentation not discoverable
- **Solution:** Context-aware help + tooltips + step-by-step guidance
- **Backend API:** `POST /api/v1/help/copilot-suggestion` (Sync)
- **Frontend:** Every page + 'Ask AI' tooltip + help panel
- **Success Criteria:** Support tickets -30%; satisfaction >4.2/5
- **Effort:** 2w

#### **Bonus:** Code & Design Review Recommendations
- **Type:** Copilot + Code Analysis
- **Problem:** Code review bottleneck; design inconsistencies
- **Solution:** Review code diffs + design tokens → suggest improvements
- **Backend API:** `POST /api/v1/code/review` (202 Async)
- **Frontend:** PR Review UI + inline suggestions
- **Success Criteria:** Adoption >70%; code quality +20%
- **Effort:** 2w

---

## Data Architecture Changes

### New Tables
```sql
-- Persistent conversation history (multi-turn context)
CREATE TABLE ai_conversation_history (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL (RLS),
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    message_index INTEGER,
    role ENUM ('user', 'assistant', 'system'),
    content TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    model VARCHAR(255),
    task_type VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    INDEX (tenant_id, user_id, session_id)
);

-- Cache metadata for invalidation
CREATE TABLE cache_metadata (
    key VARCHAR(255) PRIMARY KEY,
    tenant_id UUID NOT NULL (RLS),
    depends_on TEXT[],
    expires_at TIMESTAMP,
    created_at TIMESTAMP
);

-- Per-tenant quotas
CREATE TABLE rate_limit_quota (
    tenant_id UUID PRIMARY KEY (RLS),
    quota_requests_per_hour INTEGER,
    quota_ai_tokens_per_month BIGINT,
    used_requests_current_hour INTEGER,
    used_ai_tokens_current_month BIGINT,
    reset_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Audit trail for compliance
CREATE TABLE api_request_log (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL (RLS),
    user_id UUID,
    method VARCHAR(10),
    path TEXT,
    status_code INTEGER,
    latency_ms INTEGER,
    tokens_used INTEGER,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP,
    PARTITION BY RANGE (created_at)
);

CREATE TABLE audit_event (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL (RLS),
    user_id UUID,
    action VARCHAR(100),
    entity_type VARCHAR(50),
    entity_id VARCHAR(255),
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP IMMUTABLE
);

-- Schema additions to existing tables
ALTER TABLE sd_organizations ADD COLUMN (
    rate_limit_profile ENUM ('free', 'starter', 'pro', 'enterprise'),
    ai_token_budget_monthly BIGINT,
    features_enabled JSONB
);

ALTER TABLE sd_users ADD COLUMN (
    last_active_at TIMESTAMP,
    mfa_backup_codes_used INTEGER[],
    password_hash_version INTEGER
);
```

---

## Prompt Management & LLM Configuration

### Centralized Prompt Repository
```
backend/app/domains/ai/prompts/
├── v1/                          # Versioned (SemVer)
│   ├── test_generation.md       # Primary (claude-opus-4)
│   ├── rca_analysis.md          # Fallback (gpt-4-turbo)
│   ├── coverage_gaps.md
│   └── regression_selection.md
├── v2/                          # Advanced (multi-turn, agents)
│   ├── orchestration.md         # Agentic workflow
│   ├── security_audit.md
│   └── fine_tuning_banking.md
└── registry.yaml                # Feature flags + model routing
```

### Task-Specific Model Routing
| Task | Primary | Cost | Latency | Rationale |
|------|---------|------|---------|-----------|
| Test Generation | claude-opus-4 | $0.05-0.15 | 5-15s | 128k context, strong domain reasoning |
| QA Orchestration | claude-sonnet-4 | $0.02-0.08 | 3-10s | Extended thinking, tool-use |
| Security Audit | gpt-4-turbo | $0.05-0.12 | 5-15s | OWASP knowledge, adversarial |
| Flakiness Analysis | gpt-4o-mini | $0.002-0.01 | 1-3s | Fast pattern recognition, cheap |
| Banking Domain | Fine-tuned llama-3.1:70b | $0.001-0.003 | 2-5s | Domain-specific (IBAN, BIC) |

---

## Risk Management & Mitigation

### Critical Risks

#### 1. **Runaway Context Window Growth** → CRITICAL
- **Problem:** CrossAgentMemory + QAOrchestrator accumulate 10K+ tokens; exceed model limits
- **Probability:** High | **Impact:** High
- **Mitigation:**
  - Hierarchical context pruning (Tier 4 → RAG only at 80% budget)
  - Hard token budget per request
  - Auto-summarize outputs (10-page → 1-page)
  - Monthly cleanup cron (delete >30d old)

#### 2. **Tool-Call Parameter Injection** → CRITICAL
- **Problem:** LLM-generated malicious project_id/scenario_id read cross-tenant data
- **Probability:** Medium | **Impact:** High
- **Mitigation:**
  - Validate all tool calls against user tenant_id (enforce_rls decorator)
  - Mutation tools require 80%+ confidence + human approval
  - Rate limit tool calls (10/min per user)
  - Audit log all tool invocations

#### 3. **Multi-Turn Loop Divergence** → MEDIUM
- **Problem:** Replan loop exceeds budget (max_replans=2); unfinished workflows
- **Probability:** Medium | **Impact:** Medium
- **Mitigation:**
  - Hard replan budget enforcement
  - Early exit on duplicate plans
  - Turn count abort with warning
  - Log all plan proposals

#### 4. **Provider Fallback Chain Exhaustion** → MEDIUM
- **Problem:** All providers slow/down; circuit breaker exhausts; cascading failures
- **Probability:** Medium | **Impact:** Medium
- **Mitigation:**
  - Separate provider health check goroutine (30s interval)
  - Expose /health endpoint with provider status
  - Pre-warm cache before workflow start
  - Graceful sync/batch fallback

#### 5. **Agent State Cross-Tenant Leakage** → HIGH
- **Problem:** CrossAgentMemory._cache (global dict) not reset; insights leak
- **Probability:** Low | **Impact:** High
- **Mitigation:**
  - Reset on pipeline.reset() (already done)
  - Use tenant_id as cache key prefix (already done)
  - Audit test for memory clearing

#### 6. **Fine-Tuning Data PII Leakage** → HIGH
- **Problem:** Training data includes real customer IBAN/account#
- **Probability:** Low | **Impact:** High
- **Mitigation:**
  - Scrub training data with mask_sensitive()
  - Fine-tune only on synthetic/anonymized data
  - Audit dataset before training

#### 7. **Token Cost Runaway** → MEDIUM
- **Problem:** Multi-turn + long context + replans cost $1-5/workflow → $10K+/month
- **Probability:** Medium | **Impact:** Medium
- **Mitigation:**
  - Token budgets per workflow type
  - Cost alerts ($500/day threshold)
  - Prefer mini models for analysis
  - Cache project stats + coverage gaps

#### 8. **LLM Hallucinations on Banking Rules** → MEDIUM
- **Problem:** Invalid IBAN formats, incorrect OWASP, hallucinated rules
- **Probability:** High | **Impact:** Medium
- **Mitigation:**
  - Fine-tune on banking domain (20-30% reduction)
  - Validate generated rules against KnowledgeStore
  - Add rule-validation tool
  - Fallback to human review for high-risk

---

## Competitive Positioning

### Neurex vs. Competitors
| Dimension | Neurex | TestRail | Zephyr | Xray | Applitools |
|-----------|--------|----------|--------|------|------------|
| **Test Generation (NL→Code)** | ✓ LLM | ✗ | ~ Weak NL | ~ BDD only | ✗ |
| **Self-Healing Locators** | ✓ AI fallback chain | ✗ | ✗ | ✗ | ~ Testim visual |
| **Intelligent Prioritization** | ✓ Risk + ROI | ✗ | ✗ | ✗ | ✗ |
| **Differential Privacy (Test Data)** | ✓ Formal DP | ✗ | ✗ | ✗ | ✗ |
| **Multi-Tenant RLS** | ✓ Bank-grade | ~ Weak | ~ Weak | ✗ | ✗ |
| **End-to-End QA Scope** | ✓ 56 domains | ✗ (test mgmt only) | ✗ | ✗ | ✗ (visual) |
| **LLM Provider Agnostic** | ✓ Ollama-first | ✗ | ✗ | ✗ | ✗ |

### Win Rate Magic
> "We replaced Jira + TestRail + Applitools + manual test writing. 40 QA engineers → 12. 3-year ROI: $2.4M."

---

## Implementation Roadmap (8 Weeks to MVP)

### Week 1-2: Foundation (Service Layer + Tool Registry)
- [ ] Expand tools.py: 10 read-only tools (coverage, security, flakiness)
- [ ] Create context_manager.py: hierarchical context + token budgets
- [ ] Extend gateway_client.py: provider health + cost estimation tools
- [ ] 20 unit tests for tool parameter validation

### Week 3: Orchestration Foundation
- [ ] Create orchestrator_agent.py: Plan→Execute→Verify with tool-use
- [ ] Create conversation_manager.py: state checkpointing + turn history
- [ ] Wire existing QAOrchestrator with tool calling
- [ ] Add confidence thresholds for mutation tools

### Week 4-5: MVP UI & Integration
- [ ] Test Case Create: AI Suggestion Panel + review flow
- [ ] Test Result Detail: AI RCA sidepanel
- [ ] Coverage Dashboard: Gap Widget + suggestions
- [ ] 15 integration tests for multi-turn loops

### Week 6-8: Polish & Validation
- [ ] Performance testing (latency + token usage)
- [ ] Security review (injection tests + RLS validation)
- [ ] Beta launch (50 test customers)
- [ ] Product polish + documentation

### Success Metrics
- [ ] 90% of generated tests pass imports
- [ ] RCA accuracy >80% vs manual analysis
- [ ] Cost per request <$0.15 (optimized)
- [ ] Customer adoption >40% in MVP features
- [ ] Zero cross-tenant data leaks
- [ ] Net Promoter Score >50 in beta

---

## Pricing & Revenue Impact

### Tier Structure
| Tier | Price | Features | Target |
|------|-------|----------|--------|
| **Starter (Freemium)** | $0 | Manual test management | Individual QA engineers |
| **Professional** | $299/mo | NL→BDD, RCA, coverage, flaky detection | QA teams (5-15) |
| **Enterprise** | $999/mo | All + self-healing, prioritization, synthetic data | Large orgs + finance/healthcare |
| **Security QA (Add-on)** | $500/mo | OWASP/CWE tests, injection detection | AppSec teams |

### Financial Projections
- **Year 1:** 400 customers × $300 avg = **$1.2M ARR**
- **Year 2:** 1000 customers × $500 avg = **$5M ARR** (early leader positioning)
- **Year 3:** 2000+ customers × $600 avg = **$14M+ ARR** (10% market share)
- **COGS:** ~35-40% (LLM APIs + infra + fine-tuning)
- **CAC:** $8K; **Payback:** 8 months

### Cost Optimization
- Redis caching (project_stats, coverage_gaps) saves 20-30% LLM calls
- Batch related tests into single conversation (10-15% savings)
- Tier routing (mini models for analysis, opus for generation) saves 30-40%
- **Target:** 30-40% monthly savings vs. naive API usage

---

## Quick Wins (Immediate High-Value)

### 1. Add get_provider_health() Tool (1 day)
- Expose gateway_client health checks as callable tool
- Enables dynamic provider selection (smart fallback)
- High impact: unblocks adaptive LLM routing

### 2. Expand tools.py with Security Tools (3 days)
- `analyze_endpoint_security(endpoint_id)`
- `suggest_security_tests(threat_id)`
- High impact: unblocks security audit agent

### 3. Create prompt_center/v2/ Directory (2 days)
- Centralize prompts with semantic versioning
- Enable A/B testing + evolution tracking
- Medium impact: operational best practice

### 4. Add Token Budgeting to context_builder.py (2 days)
- Prevent context window overruns with hard budgets
- Simple, high-reliability gain
- Medium impact: prevents runaway costs

---

## Conclusion

Neurex has a **2-quarter window** to become the AI-native QA platform. The 20 integration areas map to real customer pain points (test creation 8h→2h, RCA 180min→12min, release confidence 8.1→9.2/10). Execution is critical:

1. **Ship MVP in 8 weeks:** NL→BDD, RCA, coverage gaps, regression selection
2. **Secure 200 customers** with Freemium + Pro tiers
3. **Expand to Phase 2 (Month 3-4):** Self-healing, synthetic data, security audit
4. **Hit $1.2M ARR** by end of 2026
5. **Defend moat:** Fine-tuned models, proprietary algorithms, integrated ecosystem

**Risk mitigation is non-negotiable:** Prompt injection, data privacy, context explosion, hallucinations. Build guardrails first; optimize second.

---

## Appendix: Reference Documents

- **Agent Candidates & Tool Registry:** See CSV column `Tool_Calling_Needs`
- **Prompt Strategy:** See CSV column `Backend_API` (prompt management)
- **Architecture Patterns:** See CSV column `Integration_Type`
- **Risk Deep-Dive:** See section "Risk Management & Mitigation"
- **Competitive Analysis:** See section "Competitive Positioning"

