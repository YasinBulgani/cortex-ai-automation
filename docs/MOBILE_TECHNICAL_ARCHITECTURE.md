# Neurex Mobile (React Native)
## Technical Architecture & Implementation Guide

**Status:** Ready for development  
**Framework:** React Native (Expo or bare)  
**Target:** iOS 14+, Android 8+  
**Estimated LOC:** 14,000 (6K frontend, 2K backend, 3K tests, 1.5K docs)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Neurex Mobile (RN)                       │
│  ┌────────────────┬──────────────┬──────────────────────┐   │
│  │  Presentation  │   Business   │   Data & Sync        │   │
│  ├────────────────┼──────────────┼──────────────────────┤   │
│  │ • Screens      │ • API Client │ • SQLite (local)     │   │
│  │ • Components   │ • Auth Flow  │ • Offline Queue      │   │
│  │ • Navigation   │ • State Mgmt │ • Sync Manager       │   │
│  │ • UI Kit       │ • Validation │ • Encryption Layer   │   │
│  └────────────────┴──────────────┴──────────────────────┘   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
        ┌───────▼────────┐          ┌────────▼─────────┐
        │  Neurex API    │          │ FCM / APNs       │
        │  /api/v1/*     │          │ (Notifications)  │
        │ (REST + OAuth2)│          │                  │
        └────────────────┘          └──────────────────┘
```

---

## Frontend Architecture

### Project Structure
```
neurex-mobile/
├── app/
│   ├── screens/
│   │   ├── auth/
│   │   │   ├── SignInScreen.tsx
│   │   │   ├── MFAScreen.tsx
│   │   │   └── SplashScreen.tsx
│   │   ├── dashboard/
│   │   │   ├── DashboardScreen.tsx (case list)
│   │   │   ├── CaseDetailScreen.tsx
│   │   │   └── FilterModal.tsx
│   │   ├── execution/
│   │   │   ├── ExecutionScreen.tsx (step recorder)
│   │   │   ├── ScreenshotScreen.tsx
│   │   │   └── RunSubmitScreen.tsx
│   │   ├── defects/
│   │   │   ├── DefectListScreen.tsx
│   │   │   ├── DefectDetailScreen.tsx
│   │   │   └── CommentThread.tsx
│   │   └── profile/
│   │       ├── ProfileScreen.tsx
│   │       └── SettingsScreen.tsx
│   │
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   └── Toast.tsx
│   │   ├── case/
│   │   │   ├── CaseRow.tsx
│   │   │   ├── CaseFilter.tsx
│   │   │   └── CaseMetadata.tsx
│   │   ├── execution/
│   │   │   ├── StepForm.tsx
│   │   │   ├── StepList.tsx
│   │   │   └── ScreenshotAnnotator.tsx
│   │   └── sync/
│   │       ├── OfflineIndicator.tsx
│   │       └── SyncStatus.tsx
│   │
│   ├── hooks/
│   │   ├── useAuth.ts (OAuth2, token refresh)
│   │   ├── useQueryClient.ts (TanStack Query)
│   │   ├── useOfflineQueue.ts (sync manager)
│   │   ├── useCases.ts (case list, filters)
│   │   ├── useExecution.ts (step recorder)
│   │   └── useNotifications.ts (push, deep-link)
│   │
│   ├── lib/
│   │   ├── api-client.ts (axios, retry, interceptors)
│   │   ├── auth.ts (OAuth2, token storage)
│   │   ├── db.ts (SQLite schema, migrations)
│   │   ├── sync.ts (offline queue, conflict resolution)
│   │   ├── encryption.ts (AES-256 sensitive data)
│   │   ├── notification.ts (FCM/APNs setup)
│   │   └── utils.ts (helpers)
│   │
│   ├── store/
│   │   ├── authStore.ts (Zustand: user, tokens, MFA)
│   │   ├── uiStore.ts (notifications, loading)
│   │   └── syncStore.ts (queue status, conflicts)
│   │
│   ├── types/
│   │   ├── index.ts (global types)
│   │   ├── api.ts (REST schema)
│   │   └── db.ts (SQLite schema)
│   │
│   ├── Navigation.tsx (React Navigation config)
│   └── App.tsx (root component)
│
├── app.json (Expo config)
├── package.json
├── tsconfig.json
├── jest.config.js
└── README.md
```

### Key Technologies
| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **UI** | React Native Paper | Material Design, 50+ components, active maintenance |
| **State** | Zustand | Simple, lightweight, no boilerplate vs Redux |
| **Forms** | React Hook Form + Zod | Zero-dependency, TypeScript-first validation |
| **Data fetch** | TanStack Query + axios | Caching, background sync, retry logic |
| **Navigation** | React Navigation 6 | Tab, stack, drawer patterns; handles deep-linking |
| **Local storage** | SQLite (expo-sqlite) | Reliable, ACID, encrypted via realm-web-crypto |
| **Push notif** | Firebase Cloud Messaging | Cross-platform, reliable delivery, deep-link support |
| **Analytics** | Amplitude | Mobile SDK, cohort analysis, funnels |
| **Error tracking** | Sentry | Crash reporting, source maps, session replay |

---

## Backend API Changes

### New Endpoints (Mobile-optimized)

#### 1. Authentication (OAuth2)
```
POST /api/v1/auth/token
  client_id, client_secret, grant_type=refresh_token
  → { access_token, refresh_token, expires_in, user }

POST /api/v1/auth/mfa/verify
  mfa_code, session_id
  → { access_token, expires_in }
```

#### 2. Sync Queue
```
POST /api/v1/mobile/sync
  [{ op: "POST", path: "/runs", body: {...} }, ...]
  → { success: true, failures: [], results: [...] }

GET /api/v1/mobile/delta?since=2026-06-09T10:00:00Z
  → { cases: [...], defects: [...], runs: [...] }
```

#### 3. Cases (Mobile view)
```
GET /api/v1/cases?limit=20&cursor=<id>
  Mobile pagination: cursor-based vs offset
  → { data: [...], next_cursor: "xyz" }

GET /api/v1/cases/:id/runs?limit=10
  Runs for a single case (mobile detail view)
  → { data: [...], total_count }
```

#### 4. Execution (Screenshots)
```
POST /api/v1/runs/:run_id/screenshots
  multipart/form-data: image, annotations, metadata
  → { screenshot_id, url, processing_status }
```

#### 5. Notifications (FCM)
```
POST /api/v1/notifications/subscribe
  { device_token, platform: "ios|android" }
  → { subscription_id }

GET /api/v1/notifications?limit=20&cursor=<id>
  Fetch notification history (fallback if FCM fails)
```

### API Compatibility Layer
- **Backwards compatible:** All existing web endpoints unchanged
- **Mobile flag:** Optional `?platform=mobile` for lightweight responses
- **Versioning:** v1 immutable for 2 years (no breaking changes)

---

## Data Synchronization Architecture

### Offline Queue Flow
```
User action (offline)
  ↓
Write to SQLite + queue
  ↓
Show "offline" badge
  ↓
[Network restored]
  ↓
Background sync task starts
  ↓
POST /api/v1/mobile/sync (idempotent)
  ↓
Merge responses
  ↓
Fetch delta (since last sync)
  ↓
Toast: "Synced 5 items"
```

### SQLite Schema
```sql
-- Core tables (synced from backend)
CREATE TABLE cases (
  id TEXT PRIMARY KEY,
  title TEXT,
  status TEXT,
  priority TEXT,
  tags TEXT,
  created_at TEXT,
  updated_at TEXT,
  _synced_at TEXT,
  _local_modified BOOLEAN DEFAULT FALSE
);

CREATE TABLE runs (
  id TEXT PRIMARY KEY,
  case_id TEXT,
  status TEXT,
  duration_seconds INTEGER,
  result TEXT,
  created_at TEXT,
  _synced_at TEXT
);

CREATE TABLE defects (
  id TEXT PRIMARY KEY,
  title TEXT,
  status TEXT,
  assignee TEXT,
  created_at TEXT,
  updated_at TEXT,
  _synced_at TEXT
);

-- Offline queue (local only)
CREATE TABLE sync_queue (
  id TEXT PRIMARY KEY,
  operation TEXT, -- "POST", "PATCH", "DELETE"
  endpoint TEXT,
  payload JSON,
  created_at TEXT,
  retry_count INTEGER DEFAULT 0,
  last_error TEXT,
  synced_at TEXT
);

-- Comments (local while offline, synced on reconnect)
CREATE TABLE comments (
  id TEXT PRIMARY KEY,
  defect_id TEXT,
  text TEXT,
  author_id TEXT,
  created_at TEXT,
  _local_id TEXT, -- temp ID until synced
  _synced_at TEXT
);

-- Local attachments (screenshot metadata)
CREATE TABLE attachments (
  id TEXT PRIMARY KEY,
  run_id TEXT,
  local_path TEXT,
  file_size INTEGER,
  mime_type TEXT,
  upload_status TEXT, -- "pending", "uploading", "done"
  remote_url TEXT,
  created_at TEXT
);
```

### Conflict Resolution
- **Strategy:** Server wins (optimistic local, sync to server)
- **Detection:** Compare `updated_at` timestamps
- **Resolution:** If local > server: log warning, overwrite with server
- **User notification:** Toast "synced; your recent change overwritten" (rare)

---

## Authentication & Security

### OAuth2 Flow
```
1. User taps "Sign in"
2. App opens browser (OAuth redirect)
3. User authenticates (email + password, MFA if enabled)
4. Callback: app receives auth code
5. App exchanges code for access_token (backend)
6. Token stored in secure enclave (iOS) / Keystore (Android)
7. Token auto-refreshed on expiry
```

### Token Management
- **Storage:** Encrypted keychain (iOS) / Keystore (Android) via `expo-secure-store`
- **Refresh:** Automatic on 401, exponential backoff (1s, 2s, 4s)
- **Expiry:** 1 hour access token, 30-day refresh token
- **Logout:** Delete from secure storage + revoke refresh token

### Security Headers
```
Authorization: Bearer {access_token}
X-Tenant-ID: {org_id}
X-Platform: mobile
X-App-Version: 1.0.0
X-Device-Id: {uuid}
```

### Encryption at Rest
```typescript
// Sensitive data: comments, drafts, attachments
import * as Crypto from 'expo-crypto';
const encrypted = await Crypto.digestStringAsync(
  Crypto.CryptoDigestAlgorithm.SHA256,
  sensitiveData + salt
);
// SQLite: AES-256 via realm-web-crypto
```

---

## Notification Architecture

### FCM/APNs Setup
```
Backend → Firebase Cloud Messaging (FCM)
        → Apple Push Notification service (APNs)
        → Mobile app receives notification

Notification types:
- "test.assigned" → Deep link to case detail
- "run.completed" → Deep link to run results
- "defect.commented" → Deep link to comment thread
- "team.invite" → Deep link to onboarding
```

### Deep-Linking
```
neurex://app/cases/{case_id}
neurex://app/runs/{run_id}
neurex://app/defects/{defect_id}
neurex://app/comments/{defect_id}?scroll_to={comment_id}
```

### Fallback: Polling
If FCM fails, client polls `/api/v1/notifications?since=<last_check>` every 30 sec.

---

## Performance Optimization

### Cold Start (<2 sec)
- **Lazy load domains:** Navigator stack screens loaded on-demand
- **Code splitting:** Use `React.lazy` for heavy screens (ExecutionScreen)
- **Hermes engine:** Compile JavaScript to bytecode (30% faster start)

### Memory Management
- **FlatList:** Virtual scrolling for 10K+ case lists
- **Image caching:** React Native Image Cache
- **Query client:** Automatic cache eviction (5MB limit)

### Battery Optimization
- **Background sync:** Use `expo-background-fetch` (batch uploads)
- **Location:** Only request when user opens field-based features
- **Bluetooth:** Defer to Y2 (device farm integration)

### Analytics Instrumentation
```typescript
import Analytics from '@react-native-firebase/analytics';

// Every screen view
useEffect(() => {
  Analytics.logScreenView({
    screen_name: 'case_detail',
    screen_class: 'CaseDetailScreen'
  });
}, []);

// Key interactions
const submitRun = async () => {
  Analytics.logEvent('run_submitted', {
    case_id,
    step_count: steps.length,
    has_screenshots: screenshots.length > 0
  });
  // ...
};
```

---

## Testing Strategy

### Unit Tests (30% coverage)
```typescript
// __tests__/lib/auth.test.ts
describe('OAuth2 refresh', () => {
  it('should refresh token on 401', async () => {
    const { refreshToken } = await mockApiClient.refreshAuth();
    expect(refreshToken).toBe('new_token');
  });
  
  it('should retry 3 times on network error', async () => {
    // exponential backoff test
  });
});
```

### Integration Tests (40% coverage)
```typescript
// __tests__/sync-queue.integration.test.ts
describe('Offline sync', () => {
  it('should queue POST when offline, sync when online', async () => {
    await db.insertRun(mockRun);
    expect(syncQueue).toHaveLength(1);
    
    await network.connect();
    await syncManager.sync();
    expect(await api.runs.list()).toContain(mockRun);
  });
});
```

### E2E Tests (15% coverage, critical flows)
```typescript
// e2e/auth-and-execution.e2e.ts
describe('Auth + Execute flow', () => {
  it('should sign in, view case, record steps, submit', async () => {
    await authFlow.signIn(email, password);
    await screen.expectVisible('DashboardScreen');
    
    await actions.tapCase(0);
    await screen.expectVisible('CaseDetailScreen');
    
    await actions.tapExecute();
    await recordSteps(['Open app', 'Tap button']);
    await recordScreenshot();
    await submitRun();
    
    expect(await api.runs.list()).toHaveLength(1);
  });
});
```

### Performance Tests
```typescript
// __tests__/performance.test.ts
it('should render 1K cases in FlatList without lag', async () => {
  const { getByTestId } = render(<CaseList cases={largeCaseList} />);
  const fps = measureFPS();
  expect(fps).toBeGreaterThan(50); // 50+ FPS
});
```

---

## Deployment Pipeline

### GitHub Actions CI/CD
```yaml
name: Mobile CI/CD

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm install
      - run: npm run lint
  
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm test -- --coverage
      - uses: codecov/codecov-action@v3

  build-ios:
    runs-on: macos-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - run: npm install
      - run: eas build --platform ios --non-interactive
      - run: eas submit --platform ios --non-interactive

  build-android:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - run: npm install
      - run: eas build --platform android --non-interactive
      - run: eas submit --platform android --non-interactive
```

### Versioning & Release
- **Semver:** MAJOR.MINOR.PATCH (e.g., 1.0.0)
- **Release notes:** Auto-generated from git commits
- **OTA updates:** EAS Updates for non-store-blocking changes
- **Rollback:** 1-click via EAS dashboard

---

## Monitoring & Observability

### Sentry Configuration
```typescript
import * as Sentry from 'sentry-expo';

Sentry.init({
  dsn: 'https://...@sentry.io/...',
  environment: __DEV__ ? 'development' : 'production',
  tracesSampleRate: 0.5,
  integrations: [
    new Sentry.Replay({
      maskAllText: true,
      blockAllMedia: true
    })
  ]
});
```

### Metrics Dashboard
- **Crashes:** Daily crash-free rate (target: 99.5%)
- **Performance:** P50/P95/P99 cold start, screen render time
- **Engagement:** DAU, session length, feature adoption
- **Errors:** Top 10 errors, error rate trend

---

## Migration Path (Y2)

### If Flutter Considered
- **API client:** Extract to pure Dart (70% reusable)
- **UI:** Rebuild in Flutter widgets (20% time savings vs native)
- **Database:** Switch to Hive (similar sync logic)
- **Timeline:** 8-10 weeks (vs 12 for RN from scratch)

### If Native (iOS/Android)
- **API client:** Extract to Swift/Kotlin shared library
- **UI:** Native SwiftUI/Compose
- **Database:** Realm (mobile-native ORM)
- **Timeline:** 16+ weeks (parallel iOS + Android)

---

## Appendix: Environment Variables

```env
# .env.local (development)
API_BASE_URL=http://localhost:8000/api/v1
AI_GATEWAY_URL=http://localhost:8080/api
FCM_SERVER_KEY=xxx
SENTRY_DSN=https://...
AMPLITUDE_API_KEY=xxx

# .env.staging
API_BASE_URL=https://staging-api.neurex.ai/api/v1
AI_GATEWAY_URL=https://staging-ai.neurex.ai/api
FCM_SERVER_KEY=yyy
SENTRY_DSN=https://...
AMPLITUDE_API_KEY=yyy

# .env.production
API_BASE_URL=https://api.neurex.ai/api/v1
AI_GATEWAY_URL=https://ai.neurex.ai/api
FCM_SERVER_KEY=zzz
SENTRY_DSN=https://...
AMPLITUDE_API_KEY=zzz
```

---

**Document Owner:** Mobile Tech Lead  
**Last Updated:** 2026-06-09  
**Review:** Weekly architecture sync
