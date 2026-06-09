# Neurex LLM Entegrasyon Mimarisi — Teknik Tasarım

**Tarihi:** 2026-06-09  
**Scope:** MVP Architecture (Weeks 1-8)

---

## 1. System Architecture Overview

### High-Level Data Flow

```
Frontend (Next.js)
├─ Chat Panel (Global AI Assistant)
├─ Feature Copilots (Test Gen, Story→Test, etc.)
└─ Approval Modals (for risky actions)
    ↓
API Gateway (FastAPI Backend)
├─ Input Validator
├─ Rate Limiter
├─ Router (Intent classification)
└─ Permission Checker
    ↓
Service Layer
├─ RAG Pipeline (retrieval + masking)
├─ LLM Orchestrator (tool selection, context management)
├─ Validator (hallucination detection)
└─ Approval Queue (if human approval needed)
    ↓
AI Gateway (FastAPI, port 8080, internal)
├─ Model Router (task-type → model)
│   ├─ ANALYZE (test case quality) → qwen2.5:14b
│   ├─ FAST (release notes, summaries) → llama3.1:8b
│   ├─ CODER (automation code) → qwen2.5-coder:7b
│   └─ CHAT (general questions) → Claude/GPT-4
├─ Fallback Chain
│   ├─ Ollama (local, free)
│   ├─ vLLM (self-hosted)
│   ├─ Groq (external, fast)
│   └─ Gemini (fallback)
├─ Token Counter
└─ Cost Tracker
    ↓
External LLM Services
├─ Local: Ollama (via Docker)
├─ Self-hosted: vLLM cluster
├─ Cloud: Groq API, Gemini API
└─ Monitoring: Token usage, latency, errors
    ↓
Response Post-Processing
├─ Output Validator (hallucination detection)
├─ Formatter (JSON/markdown/text)
├─ Action Extractor (for tool-calling)
└─ Audit Logger
    ↓
Frontend Response
└─ User sees result + confidence score
```

---

## 2. Service Layer Architecture

### New Service: `ai_service` (backend/app/domains/ai_service)

```
ai_service/
├─ router.py                    # 8 endpoints
│   ├─ POST /generate-bdd       # Test scenario generation
│   ├─ POST /improve-test       # Suggestion/editing
│   ├─ POST /suggest-missing    # Gap analysis
│   ├─ POST /select-regression  # Regression suite
│   ├─ POST /analyze-defect     # RCA
│   ├─ POST /generate-release-notes
│   ├─ POST /generate-from-story
│   └─ POST /validate-output    # Hallucination check
│
├─ service.py                   # Core logic
│   ├─ BDDGeneratorService
│   │   ├─ generate_from_story()
│   │   ├─ improve_test_case()
│   │   └─ suggest_missing_tests()
│   │
│   ├─ AutomationCodeGenService
│   │   ├─ generate_automation_code()
│   │   └─ validate_syntax()
│   │
│   ├─ RCAService
│   │   ├─ analyze_defect()
│   │   └─ find_similar_defects()
│   │
│   ├─ OutputValidatorService
│   │   ├─ detect_hallucination()
│   │   ├─ validate_against_source()
│   │   └─ get_confidence_score()
│   │
│   └─ DocumentGeneratorService
│       ├─ generate_release_notes()
│       └─ generate_test_report()
│
├─ rag_service.py               # RAG pipeline
│   ├─ RAGEngine
│   │   ├─ index_documents()
│   │   ├─ retrieve_context()    # with masking
│   │   ├─ rerank_results()
│   │   └─ mask_sensitive_data()
│   │
│   └─ EmbeddingManager
│       ├─ generate_embedding()
│       ├─ semantic_search()
│       └─ index_upsert()
│
├─ llm_orchestrator.py          # LLM call handling
│   ├─ LLMOrchestrator
│   │   ├─ route_to_model()      # task-type routing
│   │   ├─ build_context()       # with token budget
│   │   ├─ call_llm()            # with fallback
│   │   ├─ parse_output()
│   │   └─ track_cost()
│   │
│   └─ PromptTemplateManager
│       ├─ get_template()
│       ├─ inject_context()
│       ├─ estimate_tokens()
│       └─ validate_size()
│
├─ approval_service.py          # Human approval workflow
│   ├─ ApprovalQueue
│   │   ├─ create_approval_request()
│   │   ├─ get_pending_approvals()
│   │   ├─ approve_action()
│   │   ├─ reject_action()
│   │   └─ timeout_old_requests()
│   │
│   └─ ApprovalRules
│       ├─ requires_approval(feature)
│       └─ requires_multiple_approval(feature)
│
├─ audit_service.py             # Audit logging
│   ├─ AuditLogger
│   │   ├─ log_llm_call()
│   │   ├─ log_approval()
│   │   ├─ log_hallucination_detected()
│   │   └─ log_tool_call()
│   │
│   └─ ComplianceChecker
│       ├─ check_pii_leakage()
│       └─ generate_compliance_report()
│
├─ schemas.py
│   ├─ BDDGenerationRequest
│   ├─ LLMCallLog
│   ├─ ApprovalRequest
│   ├─ HallucinationDetection
│   └─ CostUsage
│
├─ models.py                    # SQLAlchemy models
│   ├─ LLMCall (audit trail)
│   ├─ ApprovalQueue
│   ├─ CostLog (token tracking)
│   └─ HallucinationReport
│
└─ deps.py                      # Dependencies
    ├─ get_rag_engine()
    ├─ get_llm_orchestrator()
    ├─ get_approval_service()
    ├─ check_ai_permission()
    └─ get_tenant_context()
```

---

## 3. RAG (Retrieval-Augmented Generation) Design

### Documents to Index

```
Category                  Source                    Update Freq
─────────────────────────────────────────────────────────────
Test Patterns            test_management_test_cases  Real-time (on create)
DSL Phrases              sd_dsl_phrases              Real-time (on approve)
Requirements             Knowledge Base             Batch (daily)
API Specs                api_testing_specs          Batch (on upload)
Code Snippets            GitHub (Git Fetch domain)  Batch (weekly)
Defect History           sd_defects                 Real-time (on create)
Execution Logs           test_management_test_runs  Batch (daily)
Documentation            Knowledge Base             Batch (on update)
Architecture Patterns    Internal Wiki              Manual (quarterly)
```

### RAG Pipeline

```
1. Document Ingestion
   ├─ Fetch from PostgreSQL tables
   ├─ Fetch from external sources (GitHub, confluence)
   ├─ Normalize format (to text)
   └─ PII Scan & Mask
       └─ Customer names → [CUSTOMER]
       └─ Phone numbers → [PHONE]
       └─ Email addresses → [EMAIL]
       └─ API tokens → [TOKEN]

2. Chunking
   ├─ Strategy: Sliding window (1024 tokens, 256 overlap)
   ├─ Respect semantic boundaries (by line, paragraph, code block)
   └─ Add metadata (source, date, author, tenant_id)

3. Embedding Generation
   ├─ Model: text-embedding-3-small (OpenAI)
   │  └─ Dimension: 1536
   │  └─ Cost: $0.02 per 1M tokens
   ├─ Batch size: 100 chunks
   ├─ Caching: Embed same text only once
   └─ Per-tenant: Keep embeddings segregated

4. Vector DB Storage
   ├─ Provider: Pinecone (managed) OR Weaviate (self-hosted) OR FAISS (local)
   ├─ Schema:
   │   {
   │     "id": "uuid",
   │     "embedding": [1536 floats],
   │     "content": "text chunk",
   │     "metadata": {
   │       "source": "test_cases|requirements|dsl",
   │       "source_id": "uuid",
   │       "tenant_id": "uuid",
   │       "chunk_index": 0,
   │       "created_at": "timestamp"
   │     }
   │   }
   ├─ Indexing: HNSW (Hierarchical Navigable Small World)
   └─ Tenant Isolation: Separate namespaces per tenant

5. Retrieval & Ranking
   ├─ Semantic search (cosine similarity)
   ├─ Top-K retrieval (k=5, then rerank to 3)
   ├─ Reranking: Cross-encoder model (nli-microsoft/deberta-base)
   ├─ Tenant filtering: WHERE metadata.tenant_id == current_tenant
   ├─ Freshness: Exclude docs older than threshold (configurable)
   └─ Confidence score: similarity > 0.7 (else skip)

6. Context Assembly
   ├─ Take top-3 reranked chunks
   ├─ Format as "Recent examples:"
   ├─ Respect token budget (max context = 30% of model's window)
   └─ Order by relevance (highest first)

7. Masking & Filtering
   ├─ PII mask all [MASKED] tokens in context
   ├─ RLS check: Exclude cross-tenant docs
   ├─ Permission check: User can access source (e.g., test case in their project)
   └─ Sensitive exclusions: Internal architecture docs, cost models
```

### Example: Test Case RAG for BDD Generation

```
User Input:
  "Generate BDD test cases for login flow with MFA"

Step 1: Query
  ├─ Embedding: "login MFA test cases"
  └─ Vector search: similarity > 0.7

Step 2: Retrieved Chunks (top-3)
  1. "Feature: User Login with MFA
      Scenario: Successful login with TOTP
        Given user has TOTP enabled
        When user enters valid TOTP
        Then user is logged in"
       [source: test_case_id, confidence: 0.92]

  2. "Step patterns: 'Given user has {status} enabled'
      Common TOTP scenarios: invalid code, expired, backup codes"
       [source: dsl_phrases, confidence: 0.88]

  3. "Previous MFA tests had issues with timing.
      Solution: Use mock time for TOTP verification"
       [source: defect_analysis, confidence: 0.81]

Step 3: Context Assembly (respecting 30% token budget)
  ```
  Recent test cases for MFA:
  - Successful login with TOTP
  - Invalid TOTP code handling
  - Backup code usage
  - TOTP expiry scenarios

  DSL patterns:
  - Given user has {status} enabled
  - When user enters {code}
  - Then user {action}

  Known issues:
  - Timing problems with TOTP (use mock time)
  ```

Step 4: LLM Prompt (with context)
  ```
  Generate BDD test cases for login flow with MFA.
  
  Recent examples:
  [CONTEXT HERE - with PII masked]
  
  Requirements:
  - Cover success + error paths
  - Use existing DSL patterns
  - Include timing considerations
  ```

Step 5: LLM Output
  ```
  Feature: User Login with MFA
    Scenario: Successful login with TOTP
      Given user has TOTP enabled
      When user enters valid TOTP code
      Then user is logged in
  
    Scenario: Invalid TOTP code
      Given user has TOTP enabled
      When user enters invalid TOTP code
      Then user sees error "Invalid code"
  ```

Step 6: Validation
  ├─ BDD syntax valid? ✓
  ├─ DSL patterns match library? ✓
  ├─ Hallucination check (familiar pattern)? ✓
  └─ Store in test_management_test_cases
```

---

## 4. LLM Model Routing & Fallback

### Task-Type to Model Mapping

```python
TASK_ROUTING = {
    # Analysis tasks: longer reasoning
    "ANALYZE": {
        "models": ["qwen2.5:14b", "claude-opus-4.8"],
        "max_tokens": 2000,
        "temperature": 0.3,
        "timeout": 10,
        "cost_per_1k": 0.01
    },

    # Code generation: accuracy critical
    "CODER": {
        "models": ["qwen2.5-coder:7b", "claude-opus-4.8"],
        "max_tokens": 4000,
        "temperature": 0.1,
        "timeout": 15,
        "cost_per_1k": 0.015
    },

    # Fast tasks: speed critical
    "FAST": {
        "models": ["llama3.1:8b", "groq"],
        "max_tokens": 500,
        "temperature": 0.5,
        "timeout": 3,
        "cost_per_1k": 0.0002
    },

    # Chat: general purpose
    "CHAT": {
        "models": ["gpt-4", "claude-opus-4.8"],
        "max_tokens": 2000,
        "temperature": 0.7,
        "timeout": 8,
        "cost_per_1k": 0.003
    }
}
```

### Fallback Strategy

```
For each task:

Try Model 1
├─ Success? ✓ Return result
└─ Timeout/Error? Try Model 2
    ├─ Success? ✓ Return result
    └─ Timeout/Error? Try Model 3
        ├─ Success? ✓ Return result
        └─ Timeout/Error? Try Model 4 (last resort)
            ├─ Success? ✓ Return result (with low confidence warning)
            └─ All failed? Return error + fallback to UI hint

Fallback Chain (per task):
├─ Priority 1 (free/fast): Ollama (local)
├─ Priority 2 (self-hosted): vLLM
├─ Priority 3 (external, fast): Groq
└─ Priority 4 (fallback, slow): Gemini

If all fail:
├─ Log error with context
├─ Return user-friendly error
└─ Alert SRE (if >5% failure rate in 5min window)
```

---

## 5. Token Budget & Context Management

### Per-Feature Token Budgets

```
Feature                      Max Input    Max Output   Max Turnes
────────────────────────────────────────────────────────────────
Test Generation              2000         2000         1
Story→Test                   2000         1500         1
RCA Analysis                 3000         1000         2
Regression Selection         1500         1000         1
Release Notes                2000         1500         1
Bug Analysis                 2500         1000         2
Chatbot (multi-turn)         1000         500          5
```

### Context Token Counter

```python
def estimate_tokens(text: str, model: str) -> int:
    """Estimate tokens using tiktoken"""
    # OpenAI models: ~4 chars per token
    # Llama models: ~3.5 chars per token
    # Return: token count

def build_context_within_budget(
    system_prompt: str,
    user_input: str,
    rag_chunks: List[str],
    max_context_tokens: int
) -> Tuple[str, int]:
    """
    Build context respecting token budget
    
    Priority:
    1. System prompt (always included)
    2. User input (always included)
    3. RAG chunks (in order of relevance, until budget exhausted)
    """
```

### Hard Limits (Enforcement)

```
1. Token Budget Exceeded?
   └─ Drop lowest-relevance RAG chunks
   └─ If still over: Return error to user
   
2. Too Many Turns?
   └─ Limit multi-turn to 3 turns max (per session)
   └─ Reset conversation after 30 minutes
   
3. Cost Overrun?
   └─ Track per-tenant, per-feature
   └─ Disable feature if costs exceed threshold
   └─ Alert admin
```

---

## 6. Hallucination Detection & Correction

### Detection Strategy (Pre-Deployment)

```
For each LLM output:

1. Syntax Validation
   ├─ If code: Run parser (Python AST, JavaScript ESLint)
   ├─ If BDD: Parse Gherkin syntax
   └─ If JSON: Validate schema

2. Source Grounding
   ├─ For facts: Check against RAG source
   ├─ For code: Check against existing patterns
   ├─ Confidence: similarity to source ≥ 0.8 (else flag as ungrounded)

3. Semantic Sanity Check
   ├─ Given step-based test: Check preconditions are met
   ├─ For code: Check variables are defined before use
   ├─ For story: Check acceptance criteria are specific

4. Self-Consistency Check
   ├─ Does output contradict known facts?
   ├─ Is reasoning internally consistent?

5. Confidence Scoring
   ├─ Hallucination Score = (syntax_valid + grounded + consistent) / 3
   ├─ If score < 0.7: Flag with warning
   ├─ If score < 0.5: Block output + ask user to refine input
```

### Example: Test Case Hallucination

```
User: "Generate test for password reset"
LLM Output:
  Scenario: User resets password with SMS
    Given user initiates password reset
    When user enters SMS code from [PHONE_PROVIDER]  ← HALLUCINATION!
    Then user password is reset

Validator Detects:
  ├─ Syntax OK (Gherkin valid)
  ├─ Source check: No "SMS code" in test history (confidence: 0.3)
  ├─ RAG context: Only TOTP + backup codes mentioned
  └─ Hallucination Score: 0.4 (< 0.7 threshold)

Action:
  ├─ Flag: "⚠️ Unverified feature (SMS not in source docs)"
  ├─ User can: Accept with warning / Edit / Regenerate
  └─ If accepted: Store with "user_verified: true"
```

---

## 7. Approval Workflow (for Risky Actions)

### Actions Requiring Approval

```
Feature                         Approver        Timeout
────────────────────────────────────────────────────────
Automation Code Generation      QA Lead         4 hours
Defect Auto-Creation            Project Owner   2 hours
Approval DSL Edit Proposals      Admin            6 hours
SQL Query Generation            DBA              2 hours
Test Data Generation (PII)      Compliance       4 hours
```

### Approval Request Flow

```
User Action (e.g., Generate Automation Code)
  ↓
[Check if approval required]
  ├─ No → Execute immediately
  └─ Yes → Create ApprovalRequest
            ├─ requestor_id
            ├─ feature_id
            ├─ action_intent
            ├─ payload (code, params)
            ├─ required_approver_role
            └─ expires_at (current_time + timeout)
  ↓
[Notify approver]
  ├─ Email: "Code generation awaiting approval"
  ├─ In-app: Notification badge
  └─ Slack: Optional webhook
  ↓
[Approver reviews]
  ├─ Clicks request
  ├─ Sees: Generated code + context + confidence score
  ├─ Can: Approve / Reject / Request Changes
  └─ Submits decision
  ↓
[If Approved]
  ├─ Execute action
  ├─ Log approval decision
  └─ Return result to user
  ↓
[If Rejected]
  ├─ Return rejection reason
  └─ User can refine + resubmit
  ↓
[If Timeout]
  ├─ Notify approver: "Request expired"
  ├─ Notify user: "Approval timed out, please retry"
  └─ Clean up request
```

---

## 8. Audit Logging & Compliance

### Logged Events

```
Event Type                  Fields
─────────────────────────────────────────────────────
llm_call_start            requestor, feature, task_type, intent, timestamp
llm_call_end              llm_call_id, model, tokens_used, cost_usd, duration_ms
hallucination_detected    llm_call_id, confidence_score, hallucination_type
approval_requested        action_id, approver_role, expires_at
approval_decision         action_id, approver_id, decision (approved/rejected)
tool_call_executed        tool_name, action_id, params, result
rag_query                 query_text, tenant_id, chunks_returned, confidence
pii_masked                field_name, mask_type (token, email, etc)
policy_violation          violation_type, remediation
```

### Audit Table Schema

```sql
CREATE TABLE sd_ai_audit_log (
    id UUID PRIMARY KEY,
    ts TIMESTAMP NOT NULL (indexed),
    tenant_id UUID NOT NULL (indexed, RLS),
    actor_user_id UUID,
    event_type VARCHAR(50),           -- llm_call, approval, hallucination, etc
    feature VARCHAR(50),               -- bdd_gen, rca, etc
    resource_id UUID,
    action VARCHAR(100),
    input_text TEXT,                   -- User's prompt (PII masked)
    output_text TEXT,                  -- LLM's response (truncated)
    model VARCHAR(50),
    tokens_input INT,
    tokens_output INT,
    cost_usd NUMERIC(10, 6),
    confidence_score NUMERIC(3, 2),
    approved_by_user_id UUID,
    approval_decision VARCHAR(20),    -- approved, rejected
    error_message TEXT,
    metadata JSONB,                   -- flexible storage
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ai_audit_tenant_ts ON sd_ai_audit_log(tenant_id, ts DESC);
```

---

## 9. Cost Tracking

### Per-Model Pricing

```
Model           Provider    Cost/1K Input   Cost/1K Output
──────────────────────────────────────────────────────────
llama3.1:8b     Ollama      Free (local)
qwen2.5:14b     vLLM        Free (self-hosted)
groq/mixtral    Groq        $0.0002         $0.0006
gpt-4           OpenAI      $0.03           $0.06
claude-opus-4.8 Anthropic   $0.015          $0.045
gemini-pro      Google      $0.0005         $0.0015
```

### Cost Tracking Implementation

```python
class CostTracker:
    def calculate_cost(
        self,
        model: str,
        tokens_input: int,
        tokens_output: int
    ) -> Decimal:
        """Calculate cost for a single LLM call"""
        input_cost = tokens_input * PRICING[model]["input"]
        output_cost = tokens_output * PRICING[model]["output"]
        return input_cost + output_cost
    
    def log_cost(
        self,
        tenant_id: UUID,
        feature: str,
        model: str,
        cost_usd: Decimal,
        timestamp: datetime
    ):
        """Store cost in database"""
        CostLog.create(
            tenant_id=tenant_id,
            feature=feature,
            model=model,
            cost_usd=cost_usd,
            ts=timestamp
        )
    
    def get_tenant_costs(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date
    ) -> Dict[str, Decimal]:
        """Aggregate costs by feature/model"""
```

### Cost Alerts

```
- Daily: Email summary to org admin
- Weekly: Cost trends (↑/↓)
- Monthly: Billing report (for invoice generation)
- Alert: If monthly costs > forecasted budget + 20%
```

---

## 10. Performance & Scalability

### SLA Targets

```
Feature                  P50 Latency   P95 Latency   P99 Latency   Availability
────────────────────────────────────────────────────────────────────────────
BDD Generation           1.5s          3s            5s            99.5%
Test Improvement         2s            4s            6s            99.5%
RCA Analysis             2.5s          5s            8s            99%
Regression Selection     1s            2.5s         4s            99.5%
Release Notes Gen        1.5s          3.5s          5s            99%
Chatbot Response         0.8s          2s            4s            99%
```

### Scaling Considerations

```
Bottleneck 1: RAG Index Latency
└─ Solution: Vector DB with HNSW indexing
   └─ Expected: 50-100ms for semantic search
   └─ Caching: Cache frequently-searched queries (k=5 most common)

Bottleneck 2: LLM Inference Latency
└─ Solution: Model parallelization + batching
   ├─ For Ollama: Run multiple instances (docker-compose)
   ├─ For vLLM: Deploy with tensor parallelism (N GPUs)
   ├─ For cloud: Batch requests (up to 5 at once)
   └─ Estimated: 90% requests complete <5s (with fallback)

Bottleneck 3: Token Budget Overhead
└─ Solution: Prompt caching + context reuse
   ├─ Cache system prompt (included in first request)
   └─ Reuse RAG context across similar users

Bottleneck 4: Database Writes (audit logging)
└─ Solution: Async logging + batch writes
   ├─ Write to buffer (in-memory queue)
   ├─ Flush every 10 seconds or 1000 events
   └─ Expected: <1ms per write (async)
```

### Load Test Targets (MVP)

```
Concurrent Users: 100
Requests/sec: 50
Total Features: 7 (MVP)
Expected QPS per feature: 7-8
Tolerable failure rate: <1%
```

---

## 11. Deployment & CI/CD

### New Docker Services (AI-specific)

```yaml
# docker-compose.override.yml
services:
  ai_gateway:
    image: neurex/ai-gateway:latest
    ports:
      - "8080:8080"
    environment:
      - PROVIDER_ORDER=ollama,vllm,groq,gemini
      - OLLAMA_URL=http://ollama:11434
      - GROQ_API_KEY=${GROQ_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - ollama
  
  ollama:
    image: ollama/ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
  
  vector_db:  # Pinecone or local Weaviate
    image: weaviate/weaviate:latest
    ports:
      - "8081:8080"
    environment:
      - PERSISTENCE_DATA_PATH=/var/lib/weaviate
    volumes:
      - weaviate_data:/var/lib/weaviate

volumes:
  ollama_data:
  weaviate_data:
```

### Migration for AI Audit Table

```bash
# alembic/versions/20260609_0004_ai_audit_log.py
def upgrade():
    op.create_table(
        'sd_ai_audit_log',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('actor_user_id', sa.UUID()),
        sa.Column('event_type', sa.String(50)),
        # ... (other columns)
        sa.ForeignKeyConstraint(['tenant_id'], ['sd_organizations.id']),
        sa.Index('idx_ai_audit_tenant_ts', 'tenant_id', 'ts', postgresql_using='btree')
    )
```

---

## 12. Testing Strategy

### Unit Tests

```python
# backend/tests/unit/test_rag_service.py
def test_mask_pii_in_context():
    """PII masking works correctly"""
    # Test: email → [EMAIL], name → [CUSTOMER]
    
def test_context_stays_within_token_budget():
    """Context respects max tokens"""
    # Test: 5000 token budget, 3 RAG chunks → final context ≤ 1500 tokens
    
def test_hallucination_detection():
    """Hallucination detector identifies ungrounded claims"""
    # Test: "user can reset with SMS" when no SMS in source → flagged

def test_rls_enforced_in_rag():
    """RAG filtering respects tenant_id"""
    # Test: Tenant A cannot access Tenant B's test cases
```

### Integration Tests

```python
# backend/tests/integration/test_llm_flow_e2e.py
def test_bdd_generation_e2e():
    """Full flow: User story → BDD test cases"""
    # 1. Create story
    # 2. Call /api/v1/ai/generate-bdd
    # 3. Validate BDD syntax
    # 4. Check audit log contains entry
    # 5. Validate cost tracking
    # 6. Check test case stored in DB

def test_approval_workflow_e2e():
    """Full flow: Code gen → approval → execution"""
    # 1. Call /api/v1/agents/v2/generate-automation-code
    # 2. Verify ApprovalRequest created
    # 3. Approver approves
    # 4. Code executed
    # 5. Audit log complete

def test_fallback_chain_e2e():
    """If model fails, fallback to next"""
    # 1. Mock Ollama timeout
    # 2. Call LLM with fallback
    # 3. Verify vLLM attempted
    # 4. Return result
```

### QA Tests (Hallucination)

```bash
# backend/tests/qa/test_hallucination_detection.py

Scenario 1: Ungrounded claim
  Input: "Generate test for SMS password reset"
  System: No SMS in requirement docs
  Expected: Hallucination score < 0.7, flagged with warning

Scenario 2: Self-contradiction
  Input: "User is logged in and not logged in"
  Expected: Flagged as inconsistent

Scenario 3: Invalid syntax
  Input: BDD missing "Scenario:" keyword
  Expected: Syntax error caught

Scenario 4: Variable undefined
  Input: Automation code with undefined variable `page`
  Expected: Caught by linter before deployment
```

---

## 13. Security Hardening Checklist

- [ ] **Input Validation:** All user inputs sanitized (prompt injection defense)
- [ ] **PII Masking:** Automatic in RAG pipeline (names, emails, tokens)
- [ ] **RLS Enforcement:** All queries filtered by tenant_id
- [ ] **Rate Limiting:** Token budgets + per-user request limits
- [ ] **Audit Logging:** Complete trail (input → approval → output → action)
- [ ] **Approval Workflows:** Code gen, defect creation, tool calls
- [ ] **Confidence Thresholds:** Hallucination < 0.7 → block or warn
- [ ] **Encryption:** RAG index, conversations encrypted at rest
- [ ] **Credentials:** Never logged; no secrets in embeddings
- [ ] **Access Control:** Tool calls validated against user permissions + RLS
- [ ] **Monitoring:** Cost anomalies, failure rate spikes, latency

---

## 14. Success Metrics

### Adoption Metrics
- LLM features used by >70% of active users (MVP)
- Feature-specific: 50%+ of BDD generation using AI
- Cost-per-feature trending down (better models, less hallucinations)

### Quality Metrics
- Hallucination detection rate ≥85%
- User-approved code defect rate <2% (post-execution)
- Test case quality improvement ≥40%
- RCA suggestion accuracy ≥80%

### Business Metrics
- ARR: $300K Y1 → $1.2M Y2 → $5M+ Y3
- CAC payback: 8 months
- Churn: <10% (LLM features drive retention)

---

**Document Owner:** Backend Architecture Team  
**Last Updated:** 2026-06-09  
**Next Review:** 2026-07-09 (post-MVP deployment)
