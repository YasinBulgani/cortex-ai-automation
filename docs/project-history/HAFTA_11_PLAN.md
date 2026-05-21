# Hafta 11 (Week 11) - Plan: Integration Testing & Web Dashboard
## Phase 3 Integration + Faz 4 Foundation

**Status**: 🚀 **STARTING HAFTA 11**
**Date**: 2026-04-04
**Focus**: Real API Testing + Web Dashboard Implementation

---

## 🎯 Hafta 11 Objectives

### Primary Objective 1: Integration Testing ⏳
Create comprehensive integration tests that validate:
1. Real API provider integration (OpenAI, Anthropic, DeepSeek, Ollama)
2. Database persistence and interactions
3. Flask API endpoint functionality
4. End-to-end workflows

### Primary Objective 2: Web Dashboard (Faz 4) ⏳
Begin implementation of:
1. Frontend UI components
2. Real-time test monitoring
3. Test management interface
4. Report visualization

---

## 📋 Hafta 11 Detailed Plan

### Phase A: Integration Test Suite (Days 1-3)

#### A1. API Integration Tests (200+ lines)
**File**: `tests/integration/test_integration_ai_api.py`

**Test Cases**:
1. **OpenAI Integration**
   - [ ] Initialize client with valid API key
   - [ ] Generate test scenarios
   - [ ] Token counting accuracy
   - [ ] Cost calculation
   - [ ] Error handling (rate limits, auth failures)

2. **Anthropic Integration**
   - [ ] Initialize Claude client
   - [ ] Generate test scenarios
   - [ ] Multi-turn conversation support
   - [ ] Token estimation
   - [ ] Fallback behavior

3. **DeepSeek Integration**
   - [ ] Initialize DeepSeek client
   - [ ] Test scenario generation
   - [ ] Cost comparison with OpenAI
   - [ ] Performance metrics

4. **Ollama Local Model**
   - [ ] Local model availability
   - [ ] Fallback from cloud to local
   - [ ] Performance comparison
   - [ ] Memory usage tracking

5. **Multi-Provider Fallback**
   - [ ] Fallback chain on failure
   - [ ] Cost optimization routing
   - [ ] Performance-based selection
   - [ ] Error recovery

#### A2. Database Integration Tests (150+ lines)
**File**: `tests/integration/test_integration_database.py`

**Test Cases**:
1. **SQLite Tests**
   - [ ] Test run persistence
   - [ ] Metrics storage
   - [ ] Query performance
   - [ ] Database locking

2. **PostgreSQL Tests**
   - [ ] Connection pooling
   - [ ] Transaction handling
   - [ ] Concurrent access
   - [ ] Migration support

3. **Data Integrity**
   - [ ] ACID compliance
   - [ ] Constraint validation
   - [ ] Foreign key relationships
   - [ ] Data recovery

4. **Query Performance**
   - [ ] Trend analysis query time
   - [ ] Risk assessment query time
   - [ ] Report generation queries
   - [ ] Index effectiveness

#### A3. Flask API Integration Tests (200+ lines)
**File**: `tests/integration/test_integration_flask_api.py`

**Test Cases**:
1. **AI Routes** (`/api/ai/*`)
   - [ ] Generate scenarios endpoint
   - [ ] Suggest test data endpoint
   - [ ] Analyze coverage endpoint
   - [ ] Debug test endpoint
   - [ ] Statistics endpoint
   - [ ] Configuration endpoint

2. **Reporting Routes** (`/api/reporting/*`)
   - [ ] Generate report endpoint (all formats)
   - [ ] Record test run endpoint
   - [ ] Record failure endpoint
   - [ ] Analytics endpoints (trends, risk, predictions)
   - [ ] Report serving

3. **Visual AI Routes** (`/api/visual-ai/*`)
   - [ ] Analyze image endpoint
   - [ ] Update baseline endpoint
   - [ ] Generate report endpoint
   - [ ] Statistics endpoint

4. **Project Routes** (`/api/projects/*`)
   - [ ] Create project
   - [ ] List projects
   - [ ] Update project
   - [ ] Delete project
   - [ ] Get project details

5. **Error Handling**
   - [ ] 400 Bad Request validation
   - [ ] 401 Unauthorized (if auth)
   - [ ] 404 Not Found
   - [ ] 500 Server errors
   - [ ] Response format validation

#### A4. End-to-End Workflow Tests (200+ lines)
**File**: `tests/integration/test_integration_e2e_workflows.py`

**Test Cases**:
1. **Complete AI Test Generation Workflow**
   - [ ] Receive user story
   - [ ] Extract page elements
   - [ ] Generate test scenarios
   - [ ] Suggest test data
   - [ ] Save to project
   - [ ] Verify in database

2. **Visual Regression Workflow**
   - [ ] Capture baseline image
   - [ ] Run test
   - [ ] Capture new image
   - [ ] Compare visually
   - [ ] Detect anomalies
   - [ ] Update baseline (if valid)
   - [ ] Generate report

3. **Complete Test Run Workflow**
   - [ ] Create project
   - [ ] Add tests to project
   - [ ] Execute all tests
   - [ ] Capture results
   - [ ] Analyze trends
   - [ ] Assess risk
   - [ ] Generate reports (all formats)
   - [ ] Export results

4. **Analytics Workflow**
   - [ ] Record multiple test runs
   - [ ] Analyze trends
   - [ ] Calculate risk scores
   - [ ] Predict failures
   - [ ] Track performance
   - [ ] Identify flaky tests
   - [ ] Generate recommendations

### Phase B: Web Dashboard (Faz 4) Foundation (Days 3-5)

#### B1. Frontend Project Setup
**Location**: `website/frontend/`

**Tasks**:
1. [ ] Setup React/Vue project structure
   ```
   website/frontend/
   ├── public/
   ├── src/
   │   ├── components/
   │   │   ├── Dashboard.tsx
   │   │   ├── TestMonitor.tsx
   │   │   ├── ProjectManager.tsx
   │   │   ├── ReportViewer.tsx
   │   │   └── Analytics.tsx
   │   ├── pages/
   │   ├── services/
   │   ├── utils/
   │   └── App.tsx
   ├── package.json
   ├── tsconfig.json
   └── vite.config.js
   ```

2. [ ] Install dependencies
   - React/Vue, TypeScript
   - UI components (Material-UI, Tailwind)
   - State management (Redux/Vuex)
   - WebSocket support
   - Charting library (Chart.js, Recharts)

3. [ ] Setup WebSocket connection
   - Real-time test event streaming
   - Screenshot updates
   - Progress notifications
   - Error alerts

#### B2. Core Dashboard Components

**1. Main Dashboard** (100 lines)
```tsx
<Dashboard>
  ├── <TestExecutionMonitor /> (real-time test progress)
  ├── <ProjectSelector /> (switch between projects)
  ├── <QuickStats /> (pass/fail rates, avg duration)
  └── <RecentActivity /> (latest test runs)
```

**2. Test Monitor** (150 lines)
```tsx
<TestMonitor>
  ├── <TestProgress /> (progress bar)
  ├── <CurrentTest /> (current test details)
  ├── <Screenshots /> (before/after images)
  ├── <Logs /> (real-time logs)
  └── <Actions /> (pause, stop, replay)
```

**3. Project Manager** (120 lines)
```tsx
<ProjectManager>
  ├── <ProjectList /> (all projects)
  ├── <CreateProject /> (new project form)
  ├── <ProjectSettings /> (environment, config)
  └── <TestLibrary /> (available tests)
```

**4. Report Viewer** (150 lines)
```tsx
<ReportViewer>
  ├── <ReportSelector /> (choose report)
  ├── <Summary /> (metrics summary)
  ├── <TestResults /> (detailed results table)
  ├── <Charts /> (visualization)
  └── <Export /> (download options)
```

**5. Analytics Dashboard** (150 lines)
```tsx
<Analytics>
  ├── <TrendChart /> (success rate trends)
  ├── <RiskGauge /> (risk assessment)
  ├── <FailurePredictor /> (predicted failures)
  ├── <PerformanceChart /> (execution times)
  └── <FlakyTests /> (unstable tests)
```

#### B3. API Integration Layer (100+ lines)
**File**: `website/frontend/src/services/api.ts`

**Services**:
```typescript
class APIClient {
  // AI endpoints
  generateScenarios(userStory: string): Promise<Scenario[]>
  suggestTestData(scenario: Scenario): Promise<TestData>
  analyzeCoverage(tests: Test[]): Promise<Coverage>

  // Reporting endpoints
  generateReport(testRun: TestRun, formats: string[]): Promise<Report>
  recordTestRun(results: TestResults): Promise<void>
  analyzeTrends(hours: number): Promise<Trend[]>
  assessRisk(): Promise<RiskAssessment>

  // Project endpoints
  createProject(name: string, config: Config): Promise<Project>
  listProjects(): Promise<Project[]>
  updateProject(id: string, config: Config): Promise<void>

  // WebSocket for real-time updates
  subscribeToTestEvents(callback: (event: TestEvent) => void): Unsubscribe
}
```

#### B4. WebSocket Implementation (150+ lines)
**File**: `website/frontend/src/services/websocket.ts`

**Features**:
```typescript
interface TestEvent {
  type: 'test_started' | 'test_passed' | 'test_failed' | 'screenshot' | 'log'
  testId: string
  timestamp: number
  data: any
}

class WebSocketClient {
  connect(url: string): Promise<void>
  disconnect(): void
  subscribe(eventType: string, callback: (data: any) => void): void
  unsubscribe(eventType: string): void
}
```

---

## 🛠️ Implementation Details

### Integration Tests - Structure

```python
# tests/integration/conftest.py
@pytest.fixture(scope="session")
def openai_client():
    """Real OpenAI client with API key"""
    pass

@pytest.fixture(scope="session")
def anthropic_client():
    """Real Anthropic client with API key"""
    pass

@pytest.fixture(scope="session")
def db_connection():
    """PostgreSQL connection for testing"""
    pass

@pytest.fixture
def test_project(db_connection):
    """Create temporary test project"""
    pass

@pytest.fixture
def flask_client(db_connection):
    """Flask test client"""
    pass
```

### Dashboard - Component Structure

```tsx
// Website hierarchy
<App>
  <Navigation>
    <Logo />
    <NavLinks />
    <UserMenu />
  </Navigation>
  <Layout>
    <Sidebar>
      <ProjectSelector />
      <Navigation />
    </Sidebar>
    <Main>
      <Breadcrumb />
      <Content>
        <Router>
          <Route path="/" component={<Dashboard />} />
          <Route path="/projects" component={<ProjectManager />} />
          <Route path="/tests/:id" component={<TestMonitor />} />
          <Route path="/reports/:id" component={<ReportViewer />} />
          <Route path="/analytics" component={<Analytics />} />
        </Router>
      </Content>
    </Main>
  </Layout>
  <Footer />
</App>
```

---

## 📊 Expected Deliverables

### Integration Tests
- [ ] `test_integration_ai_api.py` (200+ lines, 30+ tests)
- [ ] `test_integration_database.py` (150+ lines, 20+ tests)
- [ ] `test_integration_flask_api.py` (200+ lines, 40+ tests)
- [ ] `test_integration_e2e_workflows.py` (200+ lines, 20+ tests)
- [ ] Total: 750+ lines, 110+ integration tests

### Web Dashboard
- [ ] Frontend project structure
- [ ] 5 main components (600+ lines TSX)
- [ ] API integration service (100+ lines)
- [ ] WebSocket client (150+ lines)
- [ ] Styling/CSS (300+ lines)
- [ ] Total: 1,150+ lines of frontend code

### Configuration
- [ ] WebSocket server implementation
- [ ] Streaming API endpoints
- [ ] CORS configuration
- [ ] Session management

### Documentation
- [ ] Integration test guide
- [ ] Dashboard usage guide
- [ ] API documentation (updated)
- [ ] WebSocket protocol documentation

---

## ⏱️ Timeline

### Day 1 (Monday)
- [ ] Setup integration test infrastructure
- [ ] Write AI API integration tests
- [ ] Write database integration tests

### Day 2 (Tuesday)
- [ ] Write Flask API integration tests
- [ ] Execute and debug integration tests
- [ ] Fix failing tests

### Day 3 (Wednesday)
- [ ] Write E2E workflow tests
- [ ] Finalize integration tests (100+ passing)
- [ ] Begin dashboard frontend setup

### Day 4 (Thursday)
- [ ] Create React/Vue project structure
- [ ] Build core dashboard components
- [ ] Implement API service layer

### Day 5 (Friday)
- [ ] Complete WebSocket implementation
- [ ] Connect frontend to backend APIs
- [ ] Testing and debugging
- [ ] Documentation

---

## 🧪 Integration Test Requirements

### API Credentials Needed
- [ ] OpenAI API key (`OPENAI_API_KEY`)
- [ ] Anthropic API key (`ANTHROPIC_API_KEY`)
- [ ] DeepSeek API key (`DEEPSEEK_API_KEY`)
- [ ] Ollama running locally (optional)

### Database Requirements
- [ ] PostgreSQL instance (for production-like testing)
- [ ] SQLite (for local testing)
- [ ] Test database with initial schema

### Environment Variables
Create `.env.test` file:
```env
# API Credentials
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
DEEPSEEK_API_KEY=your-key

# Database
DATABASE_URL=postgresql://user:password@localhost/test_bgts
SQLITE_PATH=/tmp/test_bgts.db

# Flask
FLASK_ENV=test
FLASK_DEBUG=true

# Testing
TEST_MODE=true
SKIP_SLOW_TESTS=false
```

---

## 🚀 Success Criteria

### Integration Tests
- [ ] 110+ integration tests created
- [ ] 90%+ pass rate (accounting for optional services)
- [ ] Execution time < 30 seconds
- [ ] All critical paths covered
- [ ] Error handling validated

### Web Dashboard
- [ ] Basic UI functional
- [ ] Real-time test monitoring working
- [ ] All API endpoints connected
- [ ] WebSocket streaming live
- [ ] Report visualization working

### Overall
- [ ] Phase 3 fully integrated and tested
- [ ] Foundation for Faz 4 (Web Dashboard) established
- [ ] Ready for production deployment preparation

---

## 📚 Documentation to Create

1. **Integration Test Guide** (200+ lines)
   - Setup instructions
   - Test execution
   - Debugging tips
   - CI/CD integration

2. **Dashboard User Guide** (150+ lines)
   - Feature overview
   - Usage instructions
   - Keyboard shortcuts
   - Troubleshooting

3. **WebSocket API Documentation** (100+ lines)
   - Protocol specification
   - Event types
   - Connection management
   - Error handling

4. **Deployment Guide** (150+ lines)
   - Docker setup
   - Environment configuration
   - Database initialization
   - Reverse proxy setup

---

## 🔄 Progress Tracking

### Integration Testing
- [ ] Phase A1: AI API tests (Days 1-2)
- [ ] Phase A2: Database tests (Days 1-2)
- [ ] Phase A3: Flask API tests (Day 2-3)
- [ ] Phase A4: E2E tests (Day 3)

### Web Dashboard
- [ ] Phase B1: Project setup (Day 3)
- [ ] Phase B2: Components (Days 4)
- [ ] Phase B3: API layer (Day 4)
- [ ] Phase B4: WebSocket (Day 5)

---

## 📌 Important Notes

1. **API Credentials**: Use environment variables, never commit to git
2. **Test Data**: Use fixtures and factories, not production data
3. **Database**: Use separate test database for integration tests
4. **Performance**: Keep tests fast, mock external services when appropriate
5. **Monitoring**: Track test execution and API costs during testing

---

## 🎯 Next Milestone

After Hafta 11:
- ✅ Complete Phase 3 with integration testing
- ✅ Foundation for Web Dashboard (Faz 4)
- ✅ Production-ready infrastructure

Then Hafta 12:
- Complete Web Dashboard
- Production deployment
- Monitoring and maintenance

---

**Ready to Start Hafta 11**
🚀 **Let's Begin Integration Testing & Dashboard Development!**

