# Neurex Mobile MVP - Architecture Documentation

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      NEUREX MOBILE APP                      │
├─────────────────────────────────────────────────────────────┤
│                     Presentation Layer                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Screens (Auth, Dashboard, Tests, Execution, etc)   │   │
│  └─────────────────┬──────────────────────────────────┘   │
│                    │                                       │
│  ┌─────────────────▼──────────────────────────────────┐   │
│  │         Navigation (React Navigation)              │   │
│  │  ┌─────────┬──────────┬──────┬───────────┐        │   │
│  │  │ Auth    │ Dashboard│ Tests│ Execution │        │   │
│  │  │ Stack   │  Tab     │Stack │  Stack    │        │   │
│  │  └─────────┴──────────┴──────┴───────────┘        │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    Business Logic Layer                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Redux State Management (RTK)                        │   │
│  │  ┌──────────┬──────────┬──────────┬────────────┐    │   │
│  │  │ Auth     │Test Cases│Execution │ Defects   │    │   │
│  │  │ Slice    │ Slice    │ Slice    │ Slice     │    │   │
│  │  └──────────┴──────────┴──────────┴────────────┘    │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    Service Layer                           │
│  ┌─────────────┬──────────────┬───────────┬────────────┐   │
│  │ API Client  │ Auth Service │ Database  │ WebSocket  │   │
│  │ (Axios)     │ (Biometric)  │ (SQLite)  │ (Real-time)│   │
│  └─────────────┴──────────────┴───────────┴────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    Data Layer                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  AsyncStorage | Secure Storage | SQLite | Cache    │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                External Services                            │
│  ┌──────────────┬────────────┬─────────────┬───────────┐   │
│  │ Neurex API   │ OAuth 2.0  │ WebSocket   │ Analytics │   │
│  │              │            │             │           │   │
│  └──────────────┴────────────┴─────────────┴───────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Component Architecture

### App Root Component
```
App.tsx
├── Redux Provider
├── Query Client Provider
└── Navigation Container
    ├── RootNavigator
    │   ├── AuthStack (Pre-login)
    │   │   └── LoginScreen
    │   └── AppTabs (Post-login)
    │       ├── DashboardNavigator
    │       ├── TestCasesNavigator
    │       ├── ExecutionNavigator
    │       ├── DefectsNavigator
    │       └── SettingsScreen
    └── SplashScreen (Initial load)
```

## Data Flow Architecture

### Authentication Flow
```
LoginScreen
    ↓
    ├─ Email/Password Login
    │   └─ authService.login()
    │       └─ apiClient.post('/auth/login')
    │           └─ SecureStore.setItem(tokens)
    │               └─ Redux: authSlice.loginSuccess
    │
    ├─ OAuth Login
    │   └─ authService.loginWithOAuth()
    │       └─ AuthSession.promptAsync()
    │           └─ apiClient.post('/auth/oauth/callback')
    │               └─ SecureStore + Redux
    │
    └─ Biometric Login
        └─ authService.loginWithBiometrics()
            └─ ReactNativeBiometrics.simplePrompt()
                └─ Retrieve stored credentials
                    └─ authService.login()
                        └─ Redux: authSlice.loginSuccess
```

### Test Case CRUD Flow
```
TestCasesScreen
    ↓
    ├─ Fetch (componentDidMount)
    │   └─ Redux: fetchTestCases()
    │       └─ apiClient.get('/projects/:id/test-cases')
    │           └─ Redux: testCaseSlice.setTestCases()
    │               └─ Component: render testCases
    │
    ├─ Create/Update
    │   └─ TestCaseDetailScreen
    │       └─ Redux: createTestCase() or updateTestCase()
    │           └─ apiClient.post/put()
    │               └─ Redux: testCaseSlice updated
    │
    └─ Delete
        └─ Redux: deleteTestCase()
            └─ apiClient.delete()
                └─ Redux: testCaseSlice.removeTestCase()
```

### Execution Flow
```
ExecutionScreen
    ↓
    ├─ Select Test Cases
    │   └─ Modal: checkboxes for selection
    │
    ├─ Start Execution
    │   └─ Redux: startExecution()
    │       └─ apiClient.post('/executions/start')
    │           └─ WebSocket connection
    │               └─ Real-time updates
    │                   └─ Redux: updateExecutionStatus()
    │
    └─ View Results
        └─ ExecutionResultScreen
            └─ Display: logs, screenshots, status
```

### Offline Sync Flow
```
App Initialization
    ↓
    └─ appInitializer.ts
        ├─ initDatabase() → Create SQLite tables
        ├─ setupSyncManager() → Queue processor
        └─ syncQueue.process()
            ├─ Get pending operations from sync_queue table
            ├─ Post to API endpoint
            │   ├─ Success: Mark as synced
                ├─ Error: Retry with exponential backoff
                └─ Offline: Keep in queue
```

## State Management Schema

### Auth Slice
```typescript
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

// Async Thunks
- loginWithCredentials(email, password)
- loginWithOAuth()
- loginWithBiometrics()
- logout()
```

### Test Cases Slice
```typescript
interface TestCaseState {
  items: TestCase[];
  selectedTestCase: TestCase | null;
  isLoading: boolean;
  error: string | null;
  pagination: { page, pageSize, total };
}

// Async Thunks
- fetchTestCases(projectId, page, pageSize)
- createTestCase(projectId, data)
- updateTestCase(projectId, testCaseId, data)
- deleteTestCase(projectId, testCaseId)
```

### Execution Slice
```typescript
interface ExecutionState {
  results: ExecutionResult[];
  activeExecution: ExecutionResult | null;
  isRunning: boolean;
  isLoading: boolean;
  error: string | null;
  wsConnected: boolean;
}

// Async Thunks
- startExecution(projectId, testCaseIds)
- fetchExecutionResults(projectId, limit)
- stopExecution(projectId, executionId)

// Sync Actions
- updateExecutionStatus(id, status)
- addExecutionLog(id, log)
- addScreenshot(id, screenshot)
- setWsConnected(boolean)
```

## API Client Architecture

### Request Interceptor
```typescript
// Adds Authorization header with Bearer token
const token = await SecureStore.getItemAsync('access_token');
if (token) {
  config.headers.Authorization = `Bearer ${token}`;
}
```

### Response Interceptor
```typescript
// Handles 401 errors with token refresh
if (error.response?.status === 401 && !originalRequest._retry) {
  originalRequest._retry = true;
  const newToken = await refreshAccessToken();
  originalRequest.headers.Authorization = `Bearer ${newToken}`;
  return apiClient(originalRequest);
}
```

## Database Schema (SQLite)

### Tables

#### test_cases
```sql
CREATE TABLE test_cases (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'draft',
  tags TEXT (JSON),
  steps TEXT (JSON),
  created_at TEXT,
  updated_at TEXT,
  synced BOOLEAN DEFAULT 0
);
```

#### execution_results
```sql
CREATE TABLE execution_results (
  id TEXT PRIMARY KEY,
  test_case_id TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  duration_seconds INTEGER,
  started_at TEXT,
  completed_at TEXT,
  error_message TEXT,
  screenshots TEXT (JSON),
  logs TEXT (JSON),
  synced BOOLEAN DEFAULT 0
);
```

#### defects
```sql
CREATE TABLE defects (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  test_case_id TEXT,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'new',
  severity TEXT,
  assignee_id TEXT,
  created_at TEXT,
  updated_at TEXT,
  synced BOOLEAN DEFAULT 0
);
```

#### sync_queue
```sql
CREATE TABLE sync_queue (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT,
  data TEXT (JSON),
  created_at TEXT,
  synced BOOLEAN DEFAULT 0
);
```

## WebSocket Integration

### Real-time Execution Updates
```typescript
// Connect to WebSocket
const ws = new WebSocket(WSS_URL);

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch(message.type) {
    case 'execution:update':
      dispatch(updateExecutionStatus(message.payload));
      break;
    case 'execution:log':
      dispatch(addExecutionLog(message.payload));
      break;
    case 'execution:screenshot':
      dispatch(addScreenshot(message.payload));
      break;
  }
};
```

## Error Handling Strategy

### Client-side Errors
```typescript
try {
  const response = await apiClient.post(...);
  dispatch(successAction(response.data));
} catch (error) {
  if (error.response?.status === 401) {
    // Handle unauthorized
    dispatch(logout());
  } else if (error.response?.status === 400) {
    // Handle validation errors
    dispatch(setError(error.response.data.message));
  } else if (error.message === 'Network Error') {
    // Handle offline
    dispatch(setOfflineMode(true));
    // Queue request for sync
    queueSyncOperation({...});
  }
}
```

## Performance Optimization

### Code Splitting
- Lazy load screens with React.lazy()
- Dynamic imports for heavy libraries

### Memory Optimization
- Remove WebSocket listeners on unmount
- Clear timers and intervals
- Use useMemo for expensive computations

### Network Optimization
- API request batching
- Response caching (TanStack Query)
- Image compression and lazy loading

## Security Architecture

### Token Management
```typescript
// Secure storage in encrypted keychain/keystore
SecureStore.setItemAsync('access_token', token);
SecureStore.setItemAsync('refresh_token', refreshToken);

// Auto-refresh on 401
// Logout on refresh failure
```

### Biometric Security
```typescript
// Encrypted local storage of credentials
await SecureStore.setItemAsync('biometric_email', email);
// Never stored in plain AsyncStorage
```

### Network Security
```typescript
// HTTPS only
// Certificate pinning (optional)
// Content Security Policy headers
```

## Testing Architecture

### Unit Tests
- Redux slices (actions, reducers, selectors)
- Service layer (auth, API client)
- Utility functions
- Custom hooks

### Component Tests
- Screen components with mock Redux store
- Navigation between screens
- User interactions (button clicks, form submissions)

### E2E Tests (Detox)
- Full user flows (login, create test, run execution)
- Cross-platform consistency
- Performance regression detection

## Deployment Architecture

### Build Pipeline
```
Source Code
    ↓
GitHub Actions
    ├─ Install Dependencies
    ├─ Lint & Type Check
    ├─ Unit Tests
    ├─ Build APK/IPA
    ├─ E2E Tests
    └─ Code Coverage
    ↓
Artifacts
    ├─ iOS: .ipa → TestFlight → App Store
    └─ Android: .aab → Play Store Console
```

## Monitoring & Analytics

### Client-side Tracking
- Crash reporting (Sentry)
- Performance monitoring (custom)
- Event tracking (Mixpanel/Amplitude)
- User funnels and retention

### Server-side Integration
- API call logging
- Execution metrics
- Test coverage trends
- Defect analytics

## Roadmap (Post-MVP)

### Phase 1 (Week 13-16)
- Push notifications
- Offline sync manager
- Image/video attachments
- Advanced filtering and sorting

### Phase 2 (Week 17-20)
- AI-powered test suggestions
- Integration with CI/CD pipelines
- Team collaboration features
- Advanced analytics dashboard

### Phase 3 (Week 21-24)
- Native module bridges (camera, files)
- Platform-specific optimizations
- Enterprise features (SAML, MFA)
- White-label customization
