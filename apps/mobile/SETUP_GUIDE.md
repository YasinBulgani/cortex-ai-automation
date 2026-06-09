# Neurex Mobile MVP - Setup Guide

## Project Overview

Neurex Mobile is a React Native test automation platform MVP built with:
- **Framework**: React Native 0.73.5
- **Build System**: Turborepo (monorepo)
- **State Management**: Redux Toolkit + Redux
- **Navigation**: React Navigation 6
- **API Client**: Axios with interceptors
- **Offline Storage**: SQLite + AsyncStorage
- **Testing**: Jest + React Native Testing Library + Detox (E2E)
- **CI/CD**: GitHub Actions

## Timeline

**Total Duration**: 10-12 weeks, 4 FTE, 15K LOC

- Week 1-2: Project setup, authentication (Completed)
- Week 3-5: Core features (CRUD, execution, real-time WebSocket)
- Week 6-8: Results, offline sync, push notifications
- Week 9-10: Performance optimization, comprehensive testing
- Week 11-12: App Store/Play Store preparation, beta launch

## Prerequisites

### System Requirements
- macOS 12+ (for iOS development)
- Ubuntu 20+ or macOS (for Android)
- Node.js 18+ (LTS)
- npm 9+
- Xcode 14+ (for iOS)
- Android Studio 2021+ (for Android)
- CocoaPods (for iOS dependencies)
- Gradle 7+ (for Android dependencies)

### Installation

```bash
# Install Node.js (using nvm recommended)
nvm install 18
nvm use 18

# Install Xcode Command Line Tools (macOS)
xcode-select --install

# Install CocoaPods
sudo gem install cocoapods

# Install Android SDK, NDK, and emulator
# Use Android Studio: Settings → SDK Manager
```

## Project Setup

### 1. Clone and Navigate

```bash
cd apps/mobile
```

### 2. Install Dependencies

```bash
npm install
# or
npm ci  # for exact dependency versions
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Update .env with your API endpoints
REACT_APP_API_URL=https://api.neurex.com/api/v1
REACT_APP_AI_GATEWAY_URL=https://api.neurex.com/api/ai
REACT_APP_OAUTH_CLIENT_ID=your_client_id
```

### 4. iOS Setup

```bash
cd ios

# Install CocoaPods dependencies
pod install --repo-update

# Return to mobile directory
cd ..
```

### 5. Android Setup

```bash
# Ensure Android SDK is properly configured
export ANDROID_SDK_ROOT=$HOME/Library/Android/sdk
export ANDROID_HOME=$ANDROID_SDK_ROOT

# Verify setup
npx react-native doctor
```

## Running the Application

### Development Server

```bash
# Start Metro bundler
npm run dev

# In another terminal, run on iOS
npm run ios

# Or run on Android
npm run android
```

### iOS Build

```bash
# Development build
npm run ios

# Production build
npm run build:ios

# Custom Xcode build
cd ios
xcodebuild -scheme NeurexMobile -configuration Release
```

### Android Build

```bash
# Development build
npm run android

# Production APK
npm run build:android

# Production Bundle (Google Play)
npm run build:android:bundle
```

## Testing

### Unit Tests

```bash
# Run all unit tests
npm run test

# Watch mode
npm run test:watch

# With coverage report
npm run test:coverage
```

### E2E Tests (Detox)

```bash
# Build test framework and app (iOS)
npm run test:e2e:build

# Run E2E tests
npm run test:e2e

# Run specific test file
npm run test:e2e -- e2e/auth.e2e.ts
```

### Linting and Type Checking

```bash
# Run ESLint
npm run lint

# Fix lint errors
npm run lint:fix

# TypeScript type checking
npm run type-check
```

## Architecture

### Directory Structure

```
apps/mobile/
├── src/
│   ├── App.tsx                 # Root component
│   ├── components/             # Reusable UI components
│   ├── screens/                # Screen components
│   │   ├── auth/               # Authentication screens
│   │   ├── dashboard/          # Dashboard
│   │   ├── testCases/          # Test case management
│   │   ├── execution/          # Test execution
│   │   ├── defects/            # Defect management
│   │   └── settings/           # Settings
│   ├── navigation/             # Navigation setup
│   ├── services/               # Business logic
│   │   ├── apiClient.ts        # HTTP client
│   │   ├── authService.ts      # Authentication
│   │   ├── appInitializer.ts   # Startup logic
│   │   └── database/           # SQLite management
│   ├── store/                  # Redux state management
│   │   ├── index.ts            # Store configuration
│   │   └── slices/             # Redux slices
│   │       ├── authSlice.ts
│   │       ├── testCaseSlice.ts
│   │       ├── executionSlice.ts
│   │       ├── defectSlice.ts
│   │       └── uiSlice.ts
│   ├── hooks/                  # Custom React hooks
│   ├── utils/                  # Utility functions
│   ├── constants/              # Application constants
│   └── types/                  # TypeScript type definitions
├── ios/                        # iOS native code (Xcode project)
├── android/                    # Android native code (Gradle project)
├── __tests__/                  # Test files
├── e2e/                        # E2E tests
├── package.json
├── tsconfig.json
├── babel.config.js
├── metro.config.js
├── jest.config.js
└── SETUP_GUIDE.md
```

### Key Architectural Patterns

1. **Container/Presentational Pattern**
   - Screens: Container components (state management, data fetching)
   - Components: Presentational components (UI logic only)

2. **Redux State Management**
   - Slices for domain features (auth, testCases, execution, defects)
   - Async thunks for API calls
   - Normalized state structure

3. **Service Layer**
   - `apiClient.ts`: Centralized HTTP client with interceptors
   - `authService.ts`: Authentication logic (OAuth, biometrics)
   - `database/`: Offline storage management

4. **Navigation Structure**
   - Stack Navigator for auth flow
   - Tab Navigator for main app (Dashboard, Tests, Execution, Defects, Settings)
   - Nested stacks within tabs for detailed views

## Key Features

### 1. Authentication (Week 1-2)
- Email/password login with JWT tokens
- OAuth 2.0 integration (Google, GitHub, etc.)
- Biometric authentication (Face ID, Touch ID, Fingerprint)
- Secure token storage (Keychain, Keystore)
- Automatic token refresh

### 2. Test Case Management (Week 3-4)
- Create, read, update, delete test cases
- Rich text descriptions
- Step-by-step test flow definition
- Tag-based organization
- Full-text search and filtering

### 3. Test Execution (Week 5-6)
- Real-time test execution via WebSocket
- Live logs and screenshots
- Performance metrics (duration, pass rate)
- Execution history with filtering
- Stop/pause execution controls

### 4. Results & Analytics (Week 6-7)
- Comprehensive result dashboard
- Charts: Pass rate, test distribution, trend analysis
- Exportable reports (PDF, CSV)
- Screenshot gallery per test
- Detailed logs and error messages

### 5. Defect Management (Week 7-8)
- Create defects from failed tests
- Severity levels (critical, high, medium, low)
- Status tracking (new, assigned, in progress, resolved)
- Assignee management
- Comments and attachments

### 6. Offline Support (Week 8)
- SQLite local database
- Offline queue for pending changes
- Sync manager with conflict resolution
- Cache invalidation strategies

### 7. Push Notifications (Week 8)
- Execution completion notifications
- Defect assignment alerts
- Test failure notifications
- Customizable preferences

## API Integration

### Base URL Configuration
```typescript
// environment-dependent base URL
const baseURL = process.env.REACT_APP_API_URL || 'https://api.neurex.com/api/v1';
```

### API Interceptors
- **Request**: Add Authorization header with JWT token
- **Response**: Handle 401 errors with token refresh
- **Error**: Standard error handling with retry logic

### Key Endpoints

```
Authentication
POST   /auth/login
POST   /auth/oauth/callback
POST   /auth/refresh
POST   /auth/logout
GET    /auth/biometric/verify

Test Cases
GET    /projects/:projectId/test-cases
POST   /projects/:projectId/test-cases
PUT    /projects/:projectId/test-cases/:testCaseId
DELETE /projects/:projectId/test-cases/:testCaseId

Execution
POST   /projects/:projectId/executions/start
GET    /projects/:projectId/executions
GET    /projects/:projectId/executions/:executionId
POST   /projects/:projectId/executions/:executionId/stop

Defects
GET    /projects/:projectId/defects
POST   /projects/:projectId/defects
PUT    /projects/:projectId/defects/:defectId
POST   /projects/:projectId/defects/:defectId/comments
```

## State Management with Redux

### Store Structure
```typescript
{
  auth: {
    user: User | null,
    token: string | null,
    isAuthenticated: boolean,
    isLoading: boolean,
    error: string | null,
  },
  testCases: {
    items: TestCase[],
    selectedTestCase: TestCase | null,
    isLoading: boolean,
    error: string | null,
    pagination: { page, pageSize, total }
  },
  execution: {
    results: ExecutionResult[],
    activeExecution: ExecutionResult | null,
    isRunning: boolean,
    isLoading: boolean,
    wsConnected: boolean,
  },
  defects: {
    items: Defect[],
    selectedDefect: Defect | null,
    isLoading: boolean,
    pagination: { page, pageSize, total }
  },
  ui: {
    theme: 'light' | 'dark',
    notifications: Notification[],
    offlineMode: boolean,
    selectedProject: string | null,
  }
}
```

## Performance Optimization

### Code Splitting
- Lazy load screens using React.lazy()
- Dynamic imports for heavy libraries
- Bundle analysis with metro

### Memory Management
- Clean up listeners in useEffect
- Use useMemo for expensive computations
- Proper ref cleanup for WebSocket connections

### Image Optimization
- WebP format for screenshots
- Progressive loading with placeholders
- Image caching with react-native-fast-image

## Deployment

### iOS (TestFlight)
1. Create App ID in Apple Developer
2. Configure provisioning profiles
3. Build and sign using Xcode
4. Upload to TestFlight via Xcode or fastlane
5. Distribute to testers

### Android (Play Store)
1. Create signing key
2. Build signed APK/Bundle
3. Upload to Google Play Console
4. Configure store listing
5. Release to beta/production channel

### Version Management
```
Version Format: MAJOR.MINOR.PATCH
- Update in app.json before each release
- Tag releases in git: v0.1.0
- Maintain CHANGELOG.md
```

## Common Tasks

### Add a New Redux Slice
1. Create `src/store/slices/featureSlice.ts`
2. Define state, reducers, and async thunks
3. Register in `src/store/index.ts`
4. Create tests in `__tests__/store/slices/`

### Add a New Screen
1. Create screen component in `src/screens/{feature}/`
2. Add to navigation in `src/navigation/RootNavigator.tsx`
3. Connect Redux actions as needed
4. Create E2E tests in `e2e/`

### Add a New API Endpoint
1. Define request/response types in types
2. Use apiClient in service layer
3. Create async thunk in relevant slice
4. Handle loading/error states in components
5. Add integration tests

## Troubleshooting

### Metro Bundler Issues
```bash
# Clear cache and rebuild
npm run dev -- --reset-cache
watchman watch-del-all
```

### iOS Pod Issues
```bash
cd ios
rm -rf Pods Podfile.lock
pod install --repo-update
```

### Android Build Issues
```bash
cd android
./gradlew clean
./gradlew assembleDebug
```

### TypeScript Errors
```bash
npm run type-check
# Check for unresolved types in node_modules/@types
```

## Resources

- [React Native Documentation](https://reactnative.dev)
- [Redux Toolkit Guide](https://redux-toolkit.js.org)
- [React Navigation Guide](https://reactnavigation.org)
- [Detox E2E Testing](https://detoxe2e.com)
- [TypeScript Handbook](https://www.typescriptlang.org/docs)

## Support

For issues, questions, or contributions:
1. Check existing issues on GitHub
2. Review documentation
3. Create detailed bug reports
4. Submit pull requests with tests

## License

MIT License - See LICENSE file for details
