# NEUREX — Master Roadmap 2026 Q3 → Q2 2027
## Complete Platform Evolution: Mobile, Web, Backend, Enterprise

**Document Date:** 2026-06-09  
**Timeline:** Q3 2026 – Q2 2027 (12 months)  
**Total Investment:** $500K–$650K  
**Team:** 15–17 FTE  
**Status:** Planning Complete, Ready to Execute

---

## EXECUTIVE SUMMARY

Neurex has successfully built a production-ready QA automation platform (web, 56 domains, 698 endpoints, 75%+ test coverage). The next 12 months focus on **mobile expansion, enterprise readiness, and platform consolidation** to reach 50K+ users and $10M+ ARR.

### Key Milestones
- **Q3 2026:** Mobile MVP launch (React Native, iOS/Android)
- **Q4 2026:** Web PWA + Advanced Analytics
- **Q1 2027:** Enterprise SSO + SAML/OIDC
- **Q2 2027:** Advanced Collaboration + Reporting

### Financial Targets
| Metric | Current | Target | Growth |
|--------|---------|--------|--------|
| Users | 10K | 50K | 5x |
| ARR | $2M | $10M+ | 5x |
| Payback Period | — | 12–18 months | ROI-positive |

---

## PHASE 1: MOBILE LAUNCH (Q3 2026)

### Scope & Objectives
- React Native iOS/Android MVP
- Offline-first architecture (SQLite)
- Step recorder + screenshot capture
- Test case editing on-device
- Real-time sync when online

### Deliverables

#### 1.1 Mobile App (React Native)
**Repository:** `apps/mobile/` (new)  
**Team:** 4 FTE (1 lead, 2 senior, 1 junior)  
**Timeline:** 12 weeks  
**Budget:** $180K–$220K

**Core Features:**
- Navigation stack (home, projects, cases, execution, defects)
- Authentication (OAuth2, biometric fallback)
- Dashboard (active runs, recent results, team activity)
- Case detail (steps, attachments, comments)
- Step recorder (tap detection, screenshot, wait times)
- Offline queue (sync-on-reconnect)
- Push notifications (FCM/APNs + fallback polling)

**Technology Stack:**
- React Native 0.73 (Expo managed)
- TypeScript strict
- TanStack Query (offline persistence via AsyncStorage)
- SQLite (WatermelonDB for sync)
- React Navigation (native stack)
- Reanimated (smooth animations)
- NetInfo (connectivity detection)

**CI/CD Pipeline:**
- GitHub Actions workflow
- EAS Build (Expo)
- TestFlight (iOS) / Google Play closed testing (Android)
- Sentry for crash reporting
- App signing + store credentials (1Password)

**Security:**
- OAuth2 with PKCE
- Token encryption in AsyncStorage
- Biometric auth (Face ID, Touch ID, Android)
- TLS 1.3 + cert pinning
- Secrets in 1Password + GitHub Actions

#### 1.2 Backend API Extensions (Mobile-Optimized)
**Team:** 2 FTE  
**Timeline:** 8 weeks  
**Additions:**

**New Endpoints:**
- `POST /api/v1/projects/{id}/runs` — Create quick run from mobile
- `PATCH /api/v1/runs/{id}/steps/{step_id}` — Update step result
- `POST /api/v1/runs/{id}/submit` — Finalize & sync
- `GET /api/v1/runs?limit=50&offset=0` — Paginated with sync state
- `POST /api/v1/offline/queue` — Batch endpoint for offline sync
- `GET /api/v1/projects/{id}/case/{cid}/meta` — Lightweight case metadata
- `POST /api/v1/notifications/register-device` — FCM/APNs token

**Optimizations:**
- Reduce payload sizes (remove unused fields)
- Add ETag support for caching
- Rate limiting (mobile-friendly: 1000/hour vs 10000 for web)
- Compression (gzip by default)
- Pagination (cursor-based for stability)

**Database Migrations:**
- `mobile_device_tokens` (device_id, push_token, platform, registered_at)
- `offline_sync_queue` (id, tenant_id, user_id, endpoint, payload, created_at, synced_at)
- `step_result_mobile` (run_id, step_id, duration_seconds, screenshot_url, metadata)

**Tests:**
- 15+ mobile integration tests
- Offline queue flush test
- Token refresh flow test
- Rate limit test

#### 1.3 Mobile DevOps & Infrastructure
**Team:** 1 FTE  
**Timeline:** 6 weeks

**Infrastructure:**
- Firebase (FCM + Firestore for analytics)
- App signing certificates (Apple Developer, Google Play)
- CDN for image hosting (Cloudflare)
- Monitoring (Sentry, LogRocket)
- Analytics (Mixpanel or custom)

**CI/CD:**
- GitHub Actions workflow (build on every push to main)
- EAS Build (managed cloud builds)
- Staging slot (TestFlight, Play Store internal testing)
- Monitoring dashboard (Sentry, error rate alerts)

**Post-Launch Monitoring:**
- Crash rate < 0.1%
- Session duration > 2 minutes
- Daily active users (DAU)
- Feature adoption tracking
- Network health (connectivity patterns)

### Success Metrics
| Metric | Target | Owner |
|--------|--------|-------|
| App store approval | 100% (iOS/Android) | Mobile Lead |
| First week installs | 100+ | Product |
| Crash-free rate | >99.9% | QA |
| API integration test pass rate | 100% | Backend |
| Offline sync reliability | >99% | Mobile |

### Dependencies
- ✅ Web API stability (completed in Phase 0–3)
- ✅ Design system finalized (completed)
- ✅ Authentication infrastructure (completed)
- ⏳ Firebase project setup (week 1)
- ⏳ App store accounts (week 0)

---

## PHASE 2: WEB ENHANCEMENTS + PWA (Q4 2026)

### Scope & Objectives
- Progressive Web App (offline, install prompt, background sync)
- Advanced Analytics + Insights
- Collaboration features (team chat, @mentions, approval workflows)
- Performance optimization (bundle <200KB, FCP <2s)

### Deliverables

#### 2.1 PWA Implementation
**Team:** 2 FTE  
**Timeline:** 8 weeks  
**Budget:** $80K

**Features:**
- Service Worker (offline-first)
- Web App Manifest
- Install prompt (Android, desktop)
- Background sync (Form submissions, file uploads)
- Offline page (graceful degradation)
- Push notifications (Web Push API)

**Technology:**
- Workbox (Google's SW library)
- next-pwa (Next.js PWA plugin)
- Web Push API + backend push service
- IndexedDB for local cache

**Metrics:**
- Lighthouse PWA score: 90+
- Install CTR: >5%
- Offline functionality: 100% of read routes
- Sync success rate: >98%

#### 2.2 Advanced Analytics Dashboard
**Team:** 3 FTE  
**Timeline:** 10 weeks  
**Budget:** $120K

**Analytics Components:**
1. **Test Execution Trends**
   - Tests run per day/week/month
   - Pass rate over time
   - Flaky test detection rate
   - Execution time trends

2. **Coverage Analytics**
   - Coverage percentage by project
   - Untested areas (gap analysis)
   - Coverage trends (week-over-week)
   - Risk-based coverage (high-risk features)

3. **Team Performance**
   - Tester productivity (cases authored, executed)
   - Bug discovery rate
   - Test quality (bug escape rate)
   - Release readiness score

4. **Defect Analytics**
   - Defect severity distribution
   - Time-to-fix metrics
   - Defect root cause breakdown
   - Prevention insights (testing strategy gaps)

5. **Risk Dashboard**
   - Test execution risk (untested areas)
   - Regression risk (coverage regression)
   - Release risk (uncovered features)
   - Compliance risk (audit trail completeness)

**Backend Support:**
- Data warehouse queries (PostgreSQL analytical views)
- Event streaming (Kafka producers for analytics)
- 30-day rolling aggregates
- Tenant-specific isolation (RLS)

**Frontend Components:**
- Line charts (trends)
- Pie charts (distributions)
- Heatmaps (coverage by module)
- Sparklines (quick metrics)
- Custom date range picker
- Export to PDF/CSV

**Tests:**
- 20+ analytics endpoint tests
- Chart rendering tests (Vitest + React Testing Library)
- Performance tests (large dataset >10K rows)

#### 2.3 Collaboration Features
**Team:** 2 FTE  
**Timeline:** 8 weeks  
**Budget:** $100K

**Features:**
1. **In-App Chat**
   - Per-project channels
   - @mentions (notify team members)
   - Rich text (code blocks, links)
   - Message reactions (emoji)
   - Threading (replies to specific messages)

2. **Approval Workflows**
   - Test plan approval (QA lead)
   - Release sign-off (Project manager)
   - Defect assignment (Team routing)
   - Notification rules (who gets notified)

3. **Comments & Annotations**
   - Case comments (with timestamps)
   - Step-level annotations
   - Screenshot markup (circles, arrows, text)
   - @mentions in comments

4. **Activity Feed**
   - Case created, updated, executed
   - Defect created, assigned, closed
   - Test plan shared
   - Team member joined/left
   - Real-time updates (WebSocket)

**Database Schema:**
- `chat_messages` (id, project_id, channel, author_id, text, thread_id, created_at)
- `chat_channels` (id, project_id, name, description, created_at)
- `approval_requests` (id, resource_type, resource_id, requester_id, approver_id, status, deadline, created_at)
- `activity_log` (id, tenant_id, actor_id, action_type, resource_type, resource_id, created_at)

**Backend Endpoints:**
- `GET /api/v1/projects/{id}/chat/channels` — List channels
- `POST /api/v1/chat/messages` — Send message
- `GET /api/v1/chat/messages?channel=...&limit=50` — Fetch messages
- `POST /api/v1/approvals` — Request approval
- `PATCH /api/v1/approvals/{id}` — Approve/reject
- `GET /api/v1/activity?limit=50` — Activity feed

**Real-time:**
- WebSocket connection (`/ws/project/{id}/activity`)
- Heartbeat every 30s
- Graceful reconnect with exponential backoff
- Message deduplication (id-based)

**Tests:**
- 15+ chat endpoint tests
- Approval workflow tests
- WebSocket connection tests
- Rate limit tests (prevent spam)
- Mention parsing tests

#### 2.4 Performance Optimization
**Team:** 1 FTE  
**Timeline:** 6 weeks  
**Budget:** $50K

**Optimizations:**
1. **Bundle Size**
   - Code splitting by route (dynamic imports)
   - Tree-shaking unused code
   - Image optimization (WebP, AVIF)
   - Compression (gzip, brotli)
   - Target: < 200KB JavaScript

2. **Runtime Performance**
   - Lazy loading images (Intersection Observer)
   - Virtual scrolling for large lists
   - Memoization of expensive components
   - Suspense boundaries for data fetching
   - Target: FCP < 2s, LCP < 3s

3. **Caching Strategy**
   - Service Worker caching (static assets)
   - Browser caching (max-age headers)
   - API response caching (TanStack Query)
   - CDN for images/fonts
   - Database query optimization (indexes, materialized views)

4. **Monitoring**
   - Web Vitals collection (CLS, FID, LCP)
   - Error rate tracking (Sentry)
   - Performance budget enforcement (CI/CD check)
   - User experience metrics (custom events)

**Lighthouse Targets:**
- Performance: 90+
- Accessibility: 95+
- Best Practices: 90+
- SEO: 90+
- PWA: 90+

**Tests:**
- Lighthouse CI checks
- Bundle size budget tests
- Performance regression tests
- Web Vitals collection tests

### Success Metrics
| Metric | Target | Owner |
|--------|--------|-------|
| Lighthouse Performance | 90+ | Frontend Lead |
| PWA install rate | >5% | Product |
| DAU (web) | 20K | Product |
| Chat usage | >80% MAU engage | PM |
| Analytics dashboard load time | <2s | Frontend |

### Dependencies
- ✅ Design system (completed)
- ✅ API stability (Faze 0–3 completed)
- ⏳ Kafka event streaming (needed for analytics)
- ⏳ Data warehouse setup (week 1)
- ⏳ WebSocket infrastructure (week 2)

---

## PHASE 3: ENTERPRISE FEATURES (Q1 2027)

### Scope & Objectives
- Single Sign-On (SSO) — SAML 2.0, OIDC
- Advanced RBAC (role-based access control)
- Audit Logging & Compliance
- Advanced Reporting & BI Integration
- Data Governance (GDPR, HIPAA, SOC 2)

### Deliverables

#### 3.1 SSO & Identity Management
**Team:** 3 FTE  
**Timeline:** 10 weeks  
**Budget:** $120K

**Features:**
1. **SAML 2.0**
   - SP (service provider) implementation
   - IDP-initiated & SP-initiated flows
   - Metadata endpoint (`/saml/metadata`)
   - ACS endpoint (`/saml/acs`)
   - Support: Okta, Azure AD, OneLogin, Google Workspace

2. **OIDC (OpenID Connect)**
   - Authorization code flow with PKCE
   - Token refresh
   - User info endpoint
   - Support: Google, Microsoft, Auth0

3. **Just-In-Time (JIT) Provisioning**
   - Auto-create user on first SAML/OIDC login
   - Map IDP attributes to user profile
   - Auto-assign default role (Tester)
   - De-provision on removal from IDP

4. **Multi-Factor Authentication (MFA)**
   - TOTP (Time-based one-time password) — Google Authenticator, Authy
   - Email verification codes
   - Backup codes (offline)
   - Enforcement per org (admin setting)

5. **Session Management**
   - Session timeout (30 min configurable)
   - Concurrent session limit (1-5 per user, org setting)
   - Device tracking (name, IP, OS, browser)
   - Remote logout (invalidate session)

**Database Schema:**
- `sso_configurations` (id, tenant_id, provider, saml_entity_id, oidc_client_id, metadata_url, enabled, created_at)
- `sso_user_mappings` (id, tenant_id, sso_user_id, local_user_id, provider, created_at)
- `mfa_settings` (id, user_id, mfa_type, secret, backup_codes, enabled, created_at)
- `user_sessions` (id, user_id, token_id, device_name, ip_address, browser, created_at, expires_at)

**Backend Endpoints:**
- `GET /api/v1/auth/saml/metadata` — SAML metadata
- `POST /api/v1/auth/saml/acs` — SAML assertion consumer
- `GET /api/v1/auth/oidc/authorize` — OIDC auth initiation
- `POST /api/v1/auth/oidc/callback` — OIDC callback
- `POST /api/v1/auth/mfa/setup` — Enable TOTP
- `POST /api/v1/auth/mfa/verify` — Verify TOTP
- `GET /api/v1/auth/sessions` — List user sessions
- `DELETE /api/v1/auth/sessions/{id}` — Logout session

**Security:**
- SAML assertions signed + encrypted
- OIDC authorization code rotated after use
- Prevent session fixation (regenerate on login)
- Rate limiting on failed MFA attempts (5 tries → 15 min lockout)

**Tests:**
- 20+ SAML/OIDC flow tests
- JIT provisioning tests
- MFA setup/verification tests
- Session management tests
- Rate limit tests

**Compliance:**
- SOC 2 Type II (SSO logging, audit trail)
- GDPR (user data export, deletion)

#### 3.2 Advanced RBAC
**Team:** 2 FTE  
**Timeline:** 8 weeks  
**Budget:** $100K

**Current State:**
- 6 base roles (Admin, Manager, Tester, Viewer, Guest, Billing)
- Coarse-grained permissions (org level)

**Target State:**
- 8+ custom roles (define per org)
- Fine-grained permissions (project, feature level)
- Role hierarchy (inheritance)
- Time-bound roles (expires after N days)
- Approval workflows (escalation)

**New Roles:**
1. **QA Lead** — Manage team, approve plans, assign tasks
2. **Test Architect** — Design test strategy, coverage planning
3. **Automation Engineer** — Create automation, manage framework
4. **DevOps** — Manage infrastructure, deployments, monitoring
5. **Product Manager** — View analytics, approve releases
6. **Security Auditor** — Audit trails, compliance reports (read-only)
7. **Custom Role** — Admin-defined, mix-and-match permissions

**Permissions Model:**
```
Resource         Permission        Context
────────────────────────────────────────────────────
Project          create, read, update, delete, invite      org
Case             create, read, update, delete, execute     project
Defect           create, read, update, link_to_case        project
Automation       create, read, update, delete, run         project
Reports          view, export, schedule, delete            project
Settings         view, update, manage_team, manage_roles   org/project
Billing          view, manage_subscription, update_payment org
```

**Database Schema:**
- `custom_roles` (id, tenant_id, name, description, created_at, updated_at)
- `role_permissions` (id, role_id, resource, action, context, created_at)
- `user_roles_assignment` (id, user_id, role_id, assigned_by, valid_from, valid_until, created_at)

**Frontend Changes:**
- Role management UI (admin section)
- Permission matrix (grid: roles × permissions)
- Team member role assignment
- Time-bound role picker

**Backend:**
- Extend deps.py to check fine-grained permissions
- Add middleware for context-based authorization
- Update all 698 endpoints to respect new RBAC

**Tests:**
- 30+ RBAC tests (permission checks)
- Role inheritance tests
- Time-bound role tests
- Cross-tenant isolation tests

#### 3.3 Audit Logging & Compliance
**Team:** 2 FTE  
**Timeline:** 8 weeks  
**Budget:** $100K

**Compliance Standards:**
- SOC 2 Type II (audit trails, 1-year retention)
- GDPR (data portability, erasure)
- HIPAA (if healthcare customers exist)
- PCI DSS (if payment data involved, already outsourced to Stripe)

**Audit Log Events:**
```
Category          Event
────────────────────────────────────────
Authentication    login, logout, mfa_setup, mfa_verify, sso_login
Authorization     permission_denied, role_assignment_change
Data Access       resource_viewed, data_exported
Data Modification create, update, delete (with diff)
Admin Action      user_created, user_deleted, org_settings_changed
Compliance        gdpr_export_requested, data_deleted, compliance_report_generated
Security          suspicious_activity_detected, attack_blocked
```

**Database Schema:**
- `audit_log` (id, tenant_id, actor_user_id, action, resource_type, resource_id, before_state, after_state, ip_address, user_agent, created_at)
- `audit_log_retention` (tenant_id, retention_days, last_purged_at) — policy per org

**Endpoints:**
- `GET /api/v1/admin/audit-logs?limit=50&offset=0&action=&resource_type=` — Query logs
- `GET /api/v1/admin/audit-logs/{id}` — Get specific log
- `POST /api/v1/compliance/export-data` — GDPR data export
- `POST /api/v1/compliance/delete-user` — GDPR right to erasure
- `GET /api/v1/compliance/reports` — SOC 2 / HIPAA reports

**Features:**
1. **Audit Dashboard**
   - Filter by action, resource, actor, date range
   - Export to CSV (for auditors)
   - Real-time alerting (suspicious activity)

2. **Data Subject Rights (GDPR)**
   - Export all user data (JSON format)
   - Right to erasure (delete all user data + audit trail)
   - Data portability (export to third-party format)

3. **Compliance Reports**
   - SOC 2 executive summary
   - HIPAA BAA status
   - PCI DSS (N/A — Stripe payment handling)
   - GDPR checklist

**Tests:**
- 15+ audit logging tests
- GDPR export tests (data completeness)
- Erasure tests (verify all data deleted)
- Report generation tests

#### 3.4 Advanced Reporting & BI Integration
**Team:** 2 FTE  
**Timeline:** 8 weeks  
**Budget:** $80K

**Reporting Features:**
1. **Built-in Reports**
   - Test Execution Report (by date, tester, project, status)
   - Coverage Report (code paths, test cases, requirements)
   - Defect Report (severity, status, escape rate)
   - Release Readiness Report (coverage %, bugs found, risks)
   - Compliance Report (audit trail, GDPR/HIPAA checklists)

2. **Report Scheduling**
   - Daily, weekly, monthly delivery
   - Email distribution (team, stakeholders)
   - PDF generation (styled, branded)
   - Webhook integration (send to external system)

3. **BI Integration**
   - Tableau connector (native)
   - Looker connector (LookML)
   - Power BI connector (Direct Query)
   - Redash integration (custom dashboards)
   - JSON API for custom dashboards

**Database Support:**
- Materialized views for analytics queries
- Incremental refresh (hourly)
- Star schema for BI tools
- Data warehouse (optional: Snowflake, BigQuery)

**Endpoints:**
- `GET /api/v1/reports/execution?from=2026-01-01&to=2026-12-31&format=pdf|json|csv`
- `POST /api/v1/reports/schedule` — Create scheduled report
- `GET /api/v1/bi/tableau/metadata` — Tableau WDC
- `GET /api/v1/bi/looker/model` — Looker schema

**Frontend:**
- Report builder (drag-drop filters)
- Schedule UI (cron picker)
- Preview (live data)
- Export options (PDF, CSV, email)

**Tests:**
- 10+ report generation tests
- BI connector tests
- Schedule execution tests
- PDF rendering tests

### Success Metrics
| Metric | Target | Owner |
|--------|--------|-------|
| SSO adoption (% users via SAML/OIDC) | >60% | Identity team |
| Compliance audit pass rate | 100% (SOC 2 Type II) | Security |
| RBAC coverage (% endpoints enforced) | 100% | Backend |
| Audit log retention (days) | 365 | Compliance |
| Custom report generation time | <30s | Analytics |

### Dependencies
- ✅ Multi-tenancy RLS (completed)
- ✅ API infrastructure (completed)
- ⏳ SAML/OIDC testing infrastructure (week 1)
- ⏳ Okta/Azure AD sandbox accounts (week 0)
- ⏳ Data warehouse setup (Q4 2026)

---

## PHASE 4: ADVANCED ANALYTICS & LLM INTEGRATION (Q2 2027)

### Scope & Objectives
- AI-powered test scenario generation
- Intelligent test recommendations
- Advanced analytics (ML-based predictions)
- Chatbot/Copilot for QA tasks
- Agent-based workflow automation

### Deliverables (High-level)

#### 4.1 LLM Integration (MVP + Phase 2-3)
**Team:** 5 FTE  
**Timeline:** 24 weeks (6 months)  
**Budget:** $300K–$400K

**MVP Features (Weeks 1–8):**
1. Test Scenario Generation (BDD)
   - Input: User story, feature description
   - Output: Gherkin scenarios (5-6x faster)
   - LLM: qwen2.5:14b, Claude
   - Confidence scoring + hallucination detection
   - User review + refinement before execution

2. Code Generation (Test Automation)
   - Input: Test case, step description
   - Output: Python/TypeScript automation code
   - 55% cost reduction (vs manual coding)
   - Syntax validation, type checking
   - User approval workflow

3. Regression Suite Recommendation
   - Input: Commit diff, affected modules
   - Output: Top N tests to run (35% CI speedup)
   - ML model: trained on historical data
   - Confidence threshold (>70%)

4. Bug RCA (Root Cause Analysis)
   - Input: Test failure, logs, environment
   - Output: Likely causes + mitigation
   - 3–4 hours → 15 minutes
   - Multi-turn conversation (5 turns max)

5. Release Notes Generation
   - Input: Commits, PRs, issues
   - Output: Customer-facing release notes
   - 6–8 hours → 30 minutes
   - Tone: professional, clear

6. Hallucination Detection Framework
   - Syntax validation (AST parser, Gherkin schema)
   - Source grounding (RAG, similarity > 0.8)
   - Self-consistency check (no contradictions)
   - Confidence score: (syntax + grounded + consistent) / 3
   - Action: < 0.7 warn, < 0.5 block

7. Audit Trail & Cost Tracking
   - Track all LLM calls (timestamp, tokens, cost, approval status)
   - Daily/weekly cost digest
   - Alert on >120% cost forecast
   - Compliance: GDPR + audit logging

**Architecture:**
```
Backend
├─ ai_service/
│  ├─ router.py (8 endpoints)
│  ├─ service.py (generators, validators)
│  ├─ rag_service.py (vector DB, embeddings)
│  ├─ llm_orchestrator.py (model routing, fallback)
│  ├─ approval_service.py (workflow)
│  └─ audit_service.py (logging)
├─ Integrations
│  ├─ Ollama (local, free)
│  ├─ vLLM (open-source)
│  ├─ Groq (fast, cheap)
│  └─ OpenAI/Claude (fallback, expensive)
└─ RAG
   ├─ Vector DB (Pinecone, Weaviate, or local FAISS)
   ├─ Embeddings (text-embedding-3-small)
   ├─ PII masking (names, tokens, IPs)
   └─ Tenant isolation (namespace per org)

Frontend
├─ Chat panel (bottom-right, 5-turn limit)
├─ Approval modals (code gen, defect creation)
├─ Audit dashboard (LLM call history, costs)
└─ Feature toggles (A/B testing)
```

**Financial Projections:**
| Year | ARR | Users | Notes |
|------|-----|-------|-------|
| Y1 (Current) | $2M | 10K | Web-only |
| Y1 + Mobile | $4M–$5M | 25K | Post-mobile launch (9 months) |
| Y1 + LLM | $6M–$8M | 35K | AI features drive adoption |
| Y2 | $12M+ | 60K–80K | Enterprise SSO, LLM expansion |
| Y3 | $25M+ | 100K+ | Advanced analytics, integrations |

**ROI:**
- MVP investment: $235K
- Payback period: 4–6 months (from Phase 2 revenue)
- NPV (5-year): $15M–$20M (10% discount rate)

**Phase 2 Features (Weeks 9–16):** Intelligent test recommendations, screenshot-to-code, API test generation  
**Phase 3 Features:** Fine-tuning on customer data, agent orchestration, advanced chatbot

#### 4.2 ML-Based Analytics
**Team:** 3 FTE  
**Timeline:** 12 weeks  
**Budget:** $120K

**Features:**
1. **Test Failure Prediction**
   - Model: XGBoost, trained on 12+ months historical data
   - Input: Test case properties, environment, recent failures
   - Output: Failure probability (0–100%)
   - Use case: Pre-filter brittle tests, prioritize fixes

2. **Flaky Test Detection**
   - Statistical approach: runs with varying results in 10-run window
   - Quarantine on 3 failures
   - Root cause suggestions (timing, async, mocking, DB)
   - Trend analysis (improving, degrading, stable)

3. **Release Risk Scoring**
   - Factors: coverage %, untested modules, recent defect rate, team velocity
   - Output: Risk score (0–100%) + confidence interval
   - Recommendation: ship/hold/extend testing
   - Historical accuracy tracking

4. **Team Performance Insights**
   - Tester productivity (cases/day, quality/quantity trade-off)
   - Test case defect escapes (quality metric)
   - Time trends (improving, stable, declining)
   - Benchmarking (compare across projects, teams)

5. **Predictive Analytics**
   - When will feature be test-ready? (time-to-readiness model)
   - How many more bugs will be found? (Rayleigh curve)
   - What's the optimal team size for this project? (velocity model)

**Data Pipeline:**
- Events: test_run, defect_created, case_executed, team_action
- Kafka → Data warehouse (daily snapshot)
- ML pipeline (nightly training, weekly retraining)
- Inference API (real-time predictions)

**Endpoints:**
- `GET /api/v1/analytics/test/{id}/failure-prediction`
- `GET /api/v1/analytics/project/{id}/release-risk`
- `GET /api/v1/analytics/team/{id}/performance`
- `GET /api/v1/analytics/predictions` — Batch predictions

**Tests:**
- 10+ analytics tests
- ML model evaluation tests
- Inference latency tests
- Data pipeline tests

#### 4.3 Intelligent Chatbot/Copilot
**Team:** 3 FTE  
**Timeline:** 12 weeks  
**Budget:** $100K

**Features:**
1. **Test Case Chat**
   - Ask: "How many tests cover login?"
   - Get: "15 tests, 92% coverage, 1 flaky test"
   - Multi-turn: refine, drill-down, export

2. **Quick Generate**
   - "Generate 5 scenarios for payment checkout"
   - Outputs: Gherkin with 1-click adoption
   - Review + approve workflow

3. **Help & Guidance**
   - Best practices: "How do I test file upload?"
   - Troubleshooting: "Why is my test failing?"
   - Documentation: In-app help on any feature

4. **Smart Search**
   - Natural language: "Find tests for the mobile app"
   - Semantic search (BERT embeddings)
   - Results ranked by relevance

5. **Context Awareness**
   - Knows: current project, user role, team rules
   - Suggests: next actions, at-risk tests, missing coverage
   - Personalized: based on user history + role

**Architecture:**
- Frontend: Chat component (React)
- Backend: Chat service (streaming endpoint)
- LLM: gpt-4, Claude (multi-turn)
- Context: Project state, user profile, chat history
- Security: 30-min session timeout, encrypted messages

**Endpoints:**
- `POST /api/v1/chat/messages` — Send message (streaming)
- `GET /api/v1/chat/history` — Chat history
- `DELETE /api/v1/chat/sessions/{id}` — Clear session

**Tests:**
- 10+ chatbot conversation tests
- Context extraction tests
- Security tests (no PII leakage, session timeout)

#### 4.4 Agent-Based Automation
**Team:** 4 FTE  
**Timeline:** 16 weeks (Q2 2027)  
**Budget:** $150K

**Features:**
1. **Intelligent Test Execution Agent**
   - Takes instruction: "Run all login tests on mobile, daily"
   - Handles: Scheduling, environment setup, result reporting
   - Learns: Best times to run (off-peak), retry logic

2. **Regression Suite Agent**
   - Auto-selects tests on commit
   - Runs in parallel (maximize CI throughput)
   - Reports: Pass rate, new failures, flakiness detected
   - Recommendation: Ship or investigate

3. **Defect Triage Agent**
   - Receives bug report (description, screenshot, logs)
   - Classifies: Severity, category, assignment
   - Searches: Similar issues, potential duplicates
   - Action: Create case, assign to tester, notify team

4. **Release Readiness Agent**
   - Daily check: coverage %, untested areas, recent defects
   - Dashboard: Risk score, blockers, unresolved issues
   - Recommendation: "Ready to ship" vs "Hold 2 days"

5. **Continuous Learning**
   - Fine-tune models on customer data (with approval)
   - Improve predictions over time
   - A/B test suggestions (measure adoption)

**Architecture:**
- Agent framework: LangChain + custom orchestration
- Tool definitions: 20+ QA tools (create case, run test, get coverage, etc.)
- State machine: planning → execution → reporting
- Safety: Whitelisted actions (no arbitrary code execution)

**Approval Workflow:**
- Auto-approval: Low-risk (run tests, view reports)
- QA Lead approval: Medium-risk (create case, assign task)
- Project Owner approval: High-risk (create defect, extend release)

**Tests:**
- 15+ agent workflow tests
- Tool execution tests
- Safety/whitelist tests
- Approval workflow tests

### Success Metrics
| Metric | Target | Owner |
|--------|--------|-------|
| LLM feature adoption | >50% MAU use LLM | Product |
| Test generation speed | 5–6x faster | LLM team |
| Hallucination rate | <5% | QA |
| Chatbot helpfulness | >4.5/5 (rating) | Support |
| Agent automation coverage | >80% workflows | Automation |

### Dependencies
- ✅ Backend infrastructure (completed)
- ⏳ LLM provider accounts (OpenAI, Anthropic, local Ollama)
- ⏳ Vector DB (Pinecone or self-hosted FAISS)
- ⏳ Fine-tuning infrastructure (optional, Q3 2027)

---

## TOTAL EFFORT ESTIMATION

### Team Composition (15–17 FTE)

#### Mobile Team (4 FTE)
- 1 Lead (iOS/Android expert)
- 2 Senior (React Native, platform-specific)
- 1 Junior (UI/testing)

#### Web Team (5–6 FTE)
- 1 Lead (Frontend architect)
- 2 Senior (core features)
- 2–3 Mid (features, PWA)

#### Backend Team (4–5 FTE)
- 1 Lead (Backend architect)
- 2–3 Mid (API, integrations)
- 1–2 Junior (testing, docs)

#### DevOps/Infrastructure (2 FTE)
- 1 Senior (DevOps, Kubernetes)
- 1 Mid (CI/CD, monitoring)

#### QA (4–5 FTE)
- 1 Lead (QA strategy)
- 2 Mobile testers
- 1–2 Web testers

#### Product/Design (2 FTE)
- 1 Product Manager
- 1 Designer (PWA, mobile, analytics)

### Budget Breakdown

| Phase | Category | Weeks | FTE | Cost |
|-------|----------|-------|-----|------|
| **Phase 1** (Mobile) | Personnel | 12 | 4.0 | $180K |
| | Infrastructure | — | — | $20K |
| | Contingency | — | — | $20K |
| | **Subtotal** | | | **$220K** |
| **Phase 2** (Web+PWA) | Personnel | 10 | 5.0 | $200K |
| | Infrastructure | — | — | $30K |
| | **Subtotal** | | | **$230K** |
| **Phase 3** (Enterprise) | Personnel | 10 | 3.0 | $120K |
| | Infrastructure | — | — | $20K |
| | **Subtotal** | | | **$140K** |
| **Phase 4** (LLM+Analytics) | Personnel | 12 | 5.0 | $200K |
| | Infrastructure | — | — | $40K |
| | **Subtotal** | | | **$240K** |
| | **TOTAL** | 44 | 17 | **$830K** |

**Optimized (Parallel Execution):**
- Timeline: 36–46 weeks (9–11 months, vs 44 weeks sequential)
- Cost: $500K–$650K (15–17 FTE × 9–11 months)
- Parallel phases: Mobile + Web foundations (Q3 2026), Enterprise features (Q4 2026), LLM (Q1–Q2 2027)

---

## MASTER TIMELINE

### Q3 2026 (July – September)

#### Week 1–2: Foundation & Setup
- **Mobile:** Project scaffold, auth integration, CI/CD pipeline
- **Web:** PWA planning, analytics data model design
- **Backend:** Mobile API endpoint planning
- **DevOps:** Firebase setup, app signing certificates

#### Week 3–4: MVP Core
- **Mobile:** Navigation, dashboard, case detail screens
- **Web:** Service Worker implementation, offline mode
- **Backend:** 7 new mobile-optimized endpoints
- **DevOps:** EAS Build, TestFlight setup

#### Week 5–6: Execution
- **Mobile:** Step recorder, screenshot capture, notification setup
- **Web:** Chat messaging backend
- **Backend:** Offline sync queue, notification register endpoint
- **QA:** Mobile integration tests

#### Week 7–8: Offline & Sync
- **Mobile:** SQLite setup, WatermelonDB sync, offline detection
- **Web:** Background sync implementation
- **Backend:** Batch sync endpoint, conflict resolution
- **DevOps:** APNs/FCM certificate management

#### Week 9–10: Polish & Testing
- **Mobile:** Accessibility, performance, crash reporting
- **Web:** Lighthouse optimization, bundle size tuning
- **Backend:** Rate limiting, cache headers
- **QA:** Full mobile + web regression testing

#### Week 11–12: Launch
- **Mobile:** App store submission (iOS/Android)
- **Web:** PWA install UX, marketing materials
- **DevOps:** Production monitoring, rollout plan
- **Product:** Beta user recruitment, announcement

**Q3 Target:** Mobile in app stores, Web PWA live, 100+ iOS/Android installs

---

### Q4 2026 (October – December)

#### Week 1–3: Analytics Foundation
- **Backend:** Data warehouse schema, Kafka producers, analytical views
- **Frontend:** Analytics component library, chart components
- **DevOps:** Data warehouse setup (PostgreSQL analytical views → Snowflake optional)

#### Week 4–6: Advanced Analytics
- **Frontend:** Execution trends, coverage, team performance, defect analytics dashboards
- **Backend:** Query optimization, materialization strategy
- **QA:** Dashboard rendering tests, performance tests

#### Week 7–10: Collaboration Features
- **Backend:** Chat, approval workflows, activity feed endpoints
- **Frontend:** Chat UI, approval modals, real-time updates (WebSocket)
- **DevOps:** WebSocket infrastructure, rate limiting

#### Week 11–12: Performance & Hardening
- **Frontend:** Code splitting, image optimization, lazy loading
- **Backend:** Index optimization, query caching
- **DevOps:** CDN setup, monitoring alerts

**Q4 Target:** Advanced analytics live, 20K DAU, PWA 5%+ adoption, chat engaged 80% MAU

---

### Q1 2027 (January – March)

#### Week 1–2: SSO/OIDC Planning & Setup
- **Backend:** SAML/OIDC library evaluation, architecture design
- **DevOps:** Okta/Azure AD sandbox accounts, metadata setup
- **Security:** SAML assertion validation review

#### Week 3–6: SAML 2.0 Implementation
- **Backend:** SP implementation, IDP-initiated flow, JIT provisioning
- **Frontend:** SSO login UI, account linking
- **DevOps:** SAML metadata endpoint, certificate management
- **QA:** SAML flow tests (Okta, Azure AD)

#### Week 7–10: Advanced RBAC & MFA
- **Backend:** Custom role engine, fine-grained permission checks
- **Frontend:** Role management UI, permission matrix
- **Backend:** TOTP, email verification, backup codes
- **QA:** RBAC tests (30+), MFA flow tests

#### Week 11–12: Audit & Compliance
- **Backend:** Audit log table, GDPR export/erasure endpoints
- **Frontend:** Audit dashboard, report builder
- **DevOps:** Log retention policy, compliance monitoring

**Q1 Target:** SSO >60% adoption, SOC 2 Type II audit-ready, RBAC 100% endpoints covered

---

### Q2 2027 (April – June)

#### Week 1–4: LLM MVP
- **Backend:** ai_service setup, BDD generator, code generator, RAG service
- **Frontend:** Chat component, approval modals
- **DevOps:** LLM provider setup (Ollama, vLLM, Groq, OpenAI)
- **QA:** LLM output validation tests (Gherkin, syntax, hallucination detection)

#### Week 5–8: LLM Expansion & Approval Workflows
- **Backend:** RCA service, release notes generator, audit logging, cost tracking
- **Frontend:** Chat history, cost dashboard
- **DevOps:** Kafka event streaming (for audit logging), cost monitoring alerts

#### Week 9–12: ML Analytics & Chatbot
- **Backend:** ML pipeline (failure prediction, flaky detection, release risk)
- **Frontend:** Chatbot/copilot UI, prediction dashboard, context-aware suggestions
- **DevOps:** ML model training infrastructure (nightly), inference API

**Q2 Target:** LLM adoption >50%, Release notes generated in 30 min (vs 6–8 hours), Chatbot >4.5/5 rating

---

## GO-TO-MARKET STRATEGY

### Pre-Launch (Weeks 1–6, Phase 1)

#### Customer Validation
- 20 customer phone calls (mobile use-case urgency)
- Feature prioritization survey (top 10 requests)
- Beta tester recruitment (50 customers, 2-week window)

#### Marketing Prep
- Press release draft (tech angle: React Native, offline-first)
- Blog post (technical deep-dive on mobile architecture)
- Social campaign outline (Twitter, LinkedIn)
- Email campaign (500+ web users)
- Landing page (mobile features, video demo)

### Launch (Week 11–12, Phase 1)

#### Launch Day
- App store submission (iOS TestFlight, Android closed testing)
- Press release published (TechCrunch, Product Hunt if eligible)
- Email announcement (all users)
- Social announcement (Twitter thread, LinkedIn post)
- In-app notification (web users)

#### Beta Phase (Weeks 1–4, Phase 2)
- Closed testing (50 beta testers)
- Weekly feedback collection (NPS, feature requests)
- Bug fixes (priority: crashes, data loss, usability)
- Telemetry monitoring (session duration, feature adoption)

#### General Availability (Weeks 5–8, Phase 2)
- App store release (iOS, Android)
- Marketing push (ads, partnerships)
- Webinar (mobile features overview)
- Customer success calls (top 20 accounts)

### Post-Launch Monitoring

#### KPIs
- **Week 1:** 100+ iOS/Android installs
- **Week 2–4:** 500–1K installs
- **Month 2–3:** 5K MAU
- **Month 6:** 20K MAU
- **Year 1:** 50K+ MAU (from 10K web users)

#### Engagement Metrics
- Session duration: >2 minutes
- Daily active: 20% of MAU
- Test execution on mobile: >30% of total runs
- Feature adoption: >60% use step recorder

#### Churn & Retention
- Churn (mobile): <5%/month
- Retention (30-day): >70%
- Retention (90-day): >50%

#### Support & Issue Response
- Support ticket volume: expect 2–3x spike post-launch
- Response SLA: <4 hours
- Resolution rate: >80% within 48 hours

---

## RISK ASSESSMENT & MITIGATION

### High-Risk Items

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| React Native performance on Android | Features lag, crashes | Medium | Early performance testing, profiling |
| Mobile app store approval delays | Launch slip 2–4 weeks | Medium | Early submission (week 10), compliance review |
| Scaling to 50K+ users | DB bottleneck, API latency | Low | Connection pooling (completed Phase 3), read-replica (completed) |
| LLM hallucination rate >10% | Adoption drops | Medium | Confidence scoring, user review workflow, fine-tuning |
| Data warehouse complexity | Analytics queries slow, costs high | Medium | Start with PostgreSQL views, evaluate Snowflake Q4 2026 |

### Medium-Risk Items

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Third-party library maintenance (RN) | Security vulnerabilities, incompatibility | Low | Automated dependency updates, security scanning |
| WebSocket scaling (real-time chat) | Connection drops, latency | Low | Load testing, connection pooling, fallback to polling |
| SAML/OIDC implementation complexity | SSO delays, customer frustration | Medium | Early Okta/Azure AD testing, reference implementation |
| Team hiring delays | Schedule slip | High | Start recruiting Q2 2026 (8 weeks lead time) |

### Low-Risk Items

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Web improvements (PWA, analytics) | Minor feature delays | Low | Proven technologies, modular design |
| Backend API changes | Mobile client incompatibility | Low | Versioning strategy (/api/v1/ and /api/v2/), feature flags |
| Compliance (SOC 2, GDPR) | Audit delays | Low | Document as you build, external audit firm Q4 2026 |

---

## DEPENDENCIES & BLOCKERS

### Critical Path
1. ✅ Multi-tenancy RLS (completed Phase 0)
2. ✅ Async architecture (completed Phase 1–3)
3. ✅ API stability (698 endpoints, 100% test coverage)
4. ⏳ Firebase project (week 1, Phase 1)
5. ⏳ App store accounts (week 0, Phase 1)
6. ⏳ Kafka event streaming (Q4 2026 analytics)
7. ⏳ LLM provider accounts (Q2 2027)

### External Dependencies
- **Apple Developer:** $99/year, approval SLA 24–48 hours
- **Google Play:** $25 one-time, approval SLA 2–4 hours
- **Firebase:** $0–$100/month (usage-based)
- **Stripe:** Already in place (payment processing)
- **Okta/Azure AD:** Sandbox accounts for testing (free tier)
- **LLM Providers:** OpenAI (paid), Anthropic (paid), Ollama/vLLM (free, self-hosted)

### Internal Dependencies
- **Design System:** ✅ Complete (Phase 0)
- **Design Tokens:** ✅ Complete (Phase 0)
- **API Documentation:** ✅ Partial (to be expanded Phase 1–2)
- **Test Framework:** ✅ Complete (Level 4 maturity)
- **CI/CD Pipeline:** ✅ Complete (GitHub Actions)

---

## SUCCESS CRITERIA & MILESTONES

### Phase 1 (Mobile) — Success Metrics
| Metric | Target | Definition |
|--------|--------|------------|
| App Store Approval | 100% (iOS, Android) | Both platforms released, not rejected |
| Installation Rate | 100+ week 1, 1K+ month 1 | Growth adoption |
| Crash Rate | <0.1% | Stability |
| Session Duration | >2 min | Engagement |
| Test Execution on Mobile | >30% of total | Feature usage |
| API Integration Tests | 100% pass | Backend compatibility |
| Offline Sync Reliability | >99% | Core feature quality |

### Phase 2 (Web+PWA) — Success Metrics
| Metric | Target | Definition |
|--------|--------|------------|
| DAU (Web) | 20K (from 10K) | Retention + growth |
| PWA Install Rate | >5% of sessions | Adoption |
| Lighthouse Score | 90+ (all categories) | Performance |
| Chat Engagement | >80% MAU | Feature usage |
| Analytics Dashboard Load | <2s | Performance |
| Approval Workflow Success | >95% completion | UX quality |

### Phase 3 (Enterprise) — Success Metrics
| Metric | Target | Definition |
|--------|--------|------------|
| SSO Adoption | >60% of users | Enterprise demand |
| SOC 2 Type II | Pass audit | Compliance |
| RBAC Coverage | 100% of endpoints | Security |
| Audit Log Retention | 365+ days | Compliance |
| Custom Role Creation | >10 per tenant | Adoption |
| GDPR Export Time | <5 min | UX quality |

### Phase 4 (LLM+Analytics) — Success Metrics
| Metric | Target | Definition |
|--------|--------|------------|
| LLM Feature Adoption | >50% MAU | Product value |
| Test Generation Speed | 5–6x faster | Cost reduction |
| Hallucination Rate | <5% | Quality |
| Chatbot Rating | >4.5/5 stars | Satisfaction |
| Release Risk Prediction | >80% accuracy | Value |
| Agent Automation Coverage | >80% workflows | Efficiency |

---

## DEPLOYMENT & ROLLOUT STRATEGY

### Mobile Rollout

#### Phase 1a: TestFlight (Week 11, Phase 1)
- Internal team (10 users)
- Smoke tests (navigation, auth, case detail)
- Performance profiling (battery, memory)
- Crash reporting validation

#### Phase 1b: Closed Testing (Week 12–2, Phase 2)
- 50 beta users (from web base)
- Weekly feedback collection
- Bug fixes (priority: P0 crashes, P1 data loss, P2 usability)
- Telemetry monitoring

#### Phase 1c: General Availability (Week 4, Phase 2)
- App store release (iOS, Android)
- Monitoring: crash rate, session duration, feature adoption
- Rollout plan: 10% → 50% → 100% over 2 weeks (via feature flags if needed)

### Web Rollout

#### Canary (Week 1, Phase 2)
- PWA, chat, analytics: 10% of traffic
- Monitor: errors, performance, engagement
- Rollback plan: feature flags

#### Beta (Week 2–3)
- 50% of traffic
- Gather feedback, monitor metrics

#### General Availability (Week 4)
- 100% rollout
- Monitor SLAs

### Backend Rollout (Coordinated)

#### API Versioning
- `/api/v1/*` — Current (stable)
- `/api/v2/*` — New features (6-month transition period)
- Deprecation warnings in headers

#### Migration Strategy
- v1 → v2 migration period: 6 months
- v1 EOL: Month 7
- Customers notified 3 months before EOL

#### Database Migrations
- Zero-downtime deployments (Alembic strategies)
- Rollback plan: Revert migration, revert code deployment
- Testing: Dry-run on staging environment

---

## TEAM HIRING & ONBOARDING

### Timeline (6-month lead time)

#### Q2 2026 (Start Recruiting)
- 4 Mobile engineers (4 weeks interview → 4 weeks notice from previous job)
- 2 DevOps engineers (6-week process)
- 2 Backend engineers (6-week process)

#### Q3 2026 (Week 1)
- Onboarding starts
- Week 1–2: Environment setup, codebase deep-dive, architecture overview
- Week 3–4: First ticket (documentation, small bug fix)
- Week 5+: Feature development

### Onboarding Plan

#### Day 1
- Welcome, access to repos, Slack, JIRA
- Architecture overview (30 min)
- Codebase walkthrough (1 hour)
- Environment setup (Docker, dependencies)

#### Week 1
- Backend architecture (30 min)
- Test suite overview (30 min)
- Mobile architecture (for mobile hires)
- Pair programming on small issue

#### Week 2
- First PR review
- Code quality standards
- Testing best practices

#### Week 3–4
- Assigned feature from backlog
- Shadowing senior engineer (code review)

#### Week 5+
- Independent feature development
- Mentoring relationship established

---

## FINANCIAL PROJECTIONS

### Revenue Model (Current)

**Current SaaS Pricing:**
- Starter: $99/month (10 team members, limited projects)
- Professional: $299/month (unlimited team, advanced features)
- Enterprise: Custom (SSO, SAML, audit logging, SLA)

**Current Base:**
- 10,000 users
- Average: $200/month per organization
- $2M ARR

### Projected Growth (Post-Mobile, LLM, Enterprise)

#### Year 1 (Current + Mobile)
- Users: 25K (+150%)
- Pricing: $250/month average (mobile premium)
- ARR: $4M–$5M (2–2.5x)

#### Year 2 (LLM, Enterprise, Analytics)
- Users: 60K–80K
- Pricing: $300/month average (enterprise features, AI)
- ARR: $12M–$20M (6–10x)

#### Year 3 (Consolidation, Marketplace)
- Users: 100K+
- Pricing: $400/month average
- ARR: $25M–$40M (12.5–20x)

### Unit Economics

| Metric | Year 1 | Year 2 | Year 3 |
|--------|--------|---------|---------|
| CAC | $50 | $40 | $30 |
| LTV | $3,000 | $5,000 | $8,000 |
| LTV/CAC | 60x | 125x | 267x |
| Gross Margin | 75% | 78% | 80% |
| Net Margin | (30%) | 10% | 25% |
| Payback Period | 12 months | 6 months | 3 months |

### Investment Allocation

**Total Investment: $500K–$650K**

| Category | Allocation | Amount |
|----------|-----------|--------|
| Personnel (15-17 FTE, 9-11 months) | 70% | $350K–$455K |
| Infrastructure & Tools | 15% | $75K–$98K |
| Contingency (10%) | 10% | $50K–$65K |
| Marketing & Go-to-Market | 5% | $25K–$33K |
| **Total** | | **$500K–$650K** |

### ROI Analysis

**Conservative Case (Year 1 end):**
- Investment: $600K
- Revenue (Year 1): $4.5M
- Gross profit: $3.4M
- Payback period: 2 months
- ROI: 467% (Year 1)

**Realistic Case (Year 2):**
- Cumulative investment: $600K + $400K = $1M
- Year 2 revenue: $16M
- Year 2 gross profit: $12.5M
- Payback period: ~1 month (post-Year 1)
- 3-year NPV: $35M+ (10% discount)

---

## MONTHLY MILESTONE BREAKDOWN

### Month 1 (July 2026)
- **Mobile:** Scaffold, navigation, auth
- **Web:** PWA research, chat design
- **Backend:** Mobile API planning
- **DevOps:** Firebase, app signing certs
- **Hiring:** 4 mobile engineers offer round

### Month 2 (August 2026)
- **Mobile:** Dashboard, case detail, step recorder
- **Backend:** Mobile endpoints (50% done)
- **Web:** Service Worker MVP
- **DevOps:** EAS Build setup
- **Hiring:** Mobile engineers start (first 2)

### Month 3 (September 2026)
- **Mobile:** Offline sync, notifications
- **Backend:** Mobile endpoints (100% done)
- **Web:** Chat backend, analytics data model
- **DevOps:** TestFlight, APNs certs
- **QA:** Mobile integration tests
- **Launch:** App store submission

### Month 4 (October 2026)
- **Mobile:** App store approval, beta testing
- **Web:** Analytics frontend (40%)
- **Backend:** Analytics queries, Kafka producers
- **DevOps:** Data warehouse setup
- **Launch:** Closed beta, 50 testers

### Month 5 (November 2026)
- **Mobile:** General availability (iOS, Android)
- **Web:** Analytics frontend (100%), chat frontend
- **Backend:** Chat endpoints, approval workflows
- **Marketing:** Launch announcement, blog posts
- **Milestone:** 500+ mobile installs, 15K DAU web

### Month 6 (December 2026)
- **Mobile:** Bug fixes, Polish (90%+ ratings)
- **Web:** PWA install UX, performance optimization
- **Backend:** Collaboration features (100% done)
- **DevOps:** Production monitoring, analytics dashboard
- **Milestone:** 5K mobile MAU, 20K web DAU

### Month 7 (January 2027)
- **Backend:** SSO/OIDC planning, SAML implementation
- **Frontend:** SSO login UI
- **DevOps:** Okta/Azure AD sandbox setup
- **Security:** SAML review, certificate planning

### Month 8 (February 2027)
- **Backend:** SAML (100%), JIT provisioning
- **Frontend:** Role management UI
- **Backend:** MFA setup (TOTP, email)
- **QA:** SSO flow tests (Okta, Azure AD)

### Month 9 (March 2027)
- **Backend:** Audit logging, GDPR export
- **Frontend:** Audit dashboard, compliance reports
- **DevOps:** Log retention policy, monitoring
- **Milestone:** SOC 2 Type II audit-ready

### Month 10 (April 2027)
- **Backend:** LLM MVP (BDD gen, code gen, RAG)
- **Frontend:** Chat component, approval modals
- **DevOps:** Ollama, vLLM, LLM provider setup
- **QA:** Hallucination detection tests

### Month 11 (May 2027)
- **Backend:** RCA, release notes, audit logging
- **Frontend:** Chat history, cost dashboard
- **Backend:** ML pipeline (failure prediction, flaky detection)
- **Milestone:** LLM adoption >30%

### Month 12 (June 2027)
- **Backend:** Chatbot/copilot service
- **Frontend:** Chatbot UI, predictions dashboard
- **Backend:** Agent framework, workflow automation
- **Milestone:** 50K+ users, $10M+ ARR, LLM >50% adoption

---

## APPENDIX A: TECHNOLOGY STACK SUMMARY

### Mobile
- **Framework:** React Native 0.73 (Expo managed)
- **Language:** TypeScript
- **State:** TanStack Query + AsyncStorage
- **Local DB:** SQLite (WatermelonDB)
- **Navigation:** React Navigation (native stack)
- **Animations:** React Native Reanimated
- **Networking:** axios + interceptors
- **CI/CD:** GitHub Actions + EAS Build
- **Monitoring:** Sentry

### Web
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **State:** TanStack Query + localStorage
- **Styling:** Tailwind CSS + custom design tokens
- **UI Components:** Shadcn/ui + custom
- **PWA:** Workbox + next-pwa
- **Real-time:** WebSocket + reconnection logic
- **Monitoring:** Sentry + Web Vitals
- **Analytics:** Mixpanel (custom events)

### Backend
- **Framework:** FastAPI (Python 3.11)
- **Async:** SQLAlchemy 2.0 async, asyncio
- **Database:** PostgreSQL 14+
- **Caching:** Redis (in-memory)
- **Queue:** Celery (optional, for async jobs)
- **API Versioning:** /api/v1/ and /api/v2/
- **Auth:** OAuth2 + JWT (RS256 signing)
- **Validation:** Pydantic v2
- **Documentation:** OpenAPI/Swagger
- **Testing:** pytest + pytest-asyncio
- **ORM:** SQLAlchemy 2.0 (async mode)

### LLM Services
- **Frameworks:** LangChain + custom orchestration
- **Local Models:** Ollama, vLLM
- **Providers:** OpenAI, Anthropic, Groq, Gemini
- **Vector DB:** Pinecone / Weaviate / FAISS
- **Embeddings:** text-embedding-3-small
- **Token counting:** tiktoken
- **Monitoring:** Custom audit service

### Infrastructure
- **Containerization:** Docker + Docker Compose
- **Orchestration:** Kubernetes (optional, Phase 3)
- **CI/CD:** GitHub Actions
- **Monitoring:** Prometheus + Grafana + Sentry
- **Logging:** ELK Stack (optional)
- **Secrets:** 1Password + GitHub Actions
- **CDN:** Cloudflare
- **Push Notifications:** Firebase (FCM/APNs)

### Data & Analytics
- **Data Warehouse:** PostgreSQL (analytical views) → Snowflake (optional)
- **Event Streaming:** Kafka (optional, Phase 2)
- **BI Tools:** Tableau, Looker, Power BI (connectors)
- **ML Framework:** scikit-learn, XGBoost
- **Experiment:** Optional A/B testing platform (Optimizely)

---

## APPENDIX B: ASSUMPTIONS & CONSTRAINTS

### Assumptions
1. Team hiring on schedule (Q2 2026 start)
2. No major technology shifts (React Native stable, PostgreSQL scales)
3. Customer demand for mobile >$200K revenue within 12 months
4. LLM hallucination detection achievable (>95% accuracy)
5. No major security breaches or compliance failures

### Constraints
1. Budget cap: $650K (hard limit)
2. Timeline: 12 months (must ship mobile in Q3 2026)
3. Technical debt: Async migration must complete by end of Phase 1
4. Resource allocation: Max 17 FTE (hiring, retention constraints)
5. Compliance: SOC 2 Type II must pass by end of Q1 2027

### Exit Criteria (Pause/Pivot Points)
1. **Mobile launch delay >4 weeks:** Evaluate React Native alternatives
2. **LLM hallucination rate >15%:** Increase user review workflow / defer Phase 4
3. **Mobile DAU <1K at month 2:** Evaluate market fit, pivot to web
4. **SSO adoption <30%:** May indicate lack of enterprise demand, defer Phase 3

---

## APPENDIX C: COMMUNICATION PLAN

### Stakeholder Updates
- **Weekly:** Team standup (15 min, Mondays)
- **Bi-weekly:** Steering committee (Executives, Product, Engineering lead)
- **Monthly:** Board/Investor update (KPIs, risks, milestones)
- **Quarterly:** All-hands (progress, roadmap, celebrations)

### Internal Communication
- **Slack:** #neurex-mobile, #neurex-web, #neurex-backend, #neurex-llm
- **GitHub:** Issues, PRs, milestones (tracked in project board)
- **Docs:** Shared in Confluence (engineering wiki)
- **Design:** Figma (shared library, component updates)

### Customer Communication
- **Blog:** Monthly updates (features, case studies)
- **Email:** Launch announcements, beta invites, new features
- **Social:** Twitter threads (technical deep-dives), LinkedIn posts
- **Support:** In-app messaging, email support

---

## CONCLUSION

This roadmap outlines a comprehensive 12-month plan to evolve Neurex from a web-only QA platform ($2M ARR) to a multi-platform, AI-powered automation leader ($10M+ ARR). By executing Phases 1–4 in parallel where possible, we can achieve aggressive growth targets while maintaining product quality and team sustainability.

**Key Success Factors:**
1. Early hiring (Q2 2026, 6-week lead time)
2. Parallel execution (mobile + web + backend concurrent)
3. Customer feedback loops (beta testing, NPS surveys)
4. Infrastructure readiness (Firebase, Kafka, data warehouse)
5. Quality focus (75%+ test coverage, SOC 2 readiness)

**Next Steps:**
1. Secure board approval for $500K–$650K investment
2. Begin hiring (Q2 2026): 4 mobile, 2 backend, 2 DevOps engineers
3. Finalize technical architecture (LLM choice, data warehouse evaluation)
4. Kick-off Phase 1 (Week 1, July 2026)
5. Monthly progress tracking (KPIs vs. milestones)

---

**Document Prepared By:** AI Architecture Team  
**Approved By:** [Executive Name]  
**Last Updated:** 2026-06-09  
**Next Review:** 2026-07-09
