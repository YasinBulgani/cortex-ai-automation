# Neurex Mobile MVP

## Overview

Neurex Mobile is a comprehensive React Native test automation platform MVP, built to bring powerful QA capabilities to iOS and Android devices. It enables QA teams to manage test cases, execute tests in real-time, track results, and manage defects directly from their mobile devices.

**Platform**: iOS (14+), Android (6+)  
**Technology**: React Native 0.73, Redux Toolkit, TypeScript  
**Status**: MVP (10-12 week implementation)  
**Maturity**: Production-ready architecture, beta features

## Key Features

### Core Capabilities

1. **Authentication** ✓
   - Email/password login with JWT
   - OAuth 2.0 (Google, GitHub, etc.)
   - Biometric auth (Face ID, Touch ID, Fingerprint)
   - Secure token storage and auto-refresh

2. **Test Case Management**
   - Create, view, edit, delete test cases
   - Rich descriptions and step-by-step flows
   - Tag-based organization and search
   - Bulk operations (import/export)

3. **Test Execution**
   - Real-time execution with WebSocket updates
   - Live logs and screenshot capture
   - Performance metrics (duration, memory)
   - Execution history with filtering
   - Stop/pause controls

4. **Results & Analytics**
   - Dashboard with key metrics
   - Pass rate trends and patterns
   - Detailed result reports (PDF export)
   - Screenshot gallery per test
   - Log filtering and search

5. **Defect Management**
   - Create defects from failed tests
   - Severity and status tracking
   - Assignee management
   - Comments and activity timeline
   - Link to test cases

6. **Offline Support**
   - SQLite local caching
   - Offline queue for changes
   - Automatic sync when online
   - Conflict resolution

7. **Settings & Personalization**
   - Dark/light theme
   - Offline mode toggle
   - Biometric preferences
   - Language selection
   - App version management

## Architecture Highlights

### Design Patterns
- **Container/Presentational Pattern**: Separation of concerns
- **Redux with RTK**: Normalized state management
- **Service Layer**: Business logic isolation
- **Custom Hooks**: Reusable logic

### Tech Stack
- **UI Framework**: React Native 0.73.5
- **State Management**: Redux Toolkit + Redux
- **Navigation**: React Navigation 6
- **HTTP Client**: Axios with interceptors
- **Local Storage**: SQLite + AsyncStorage + Secure Storage
- **Real-time**: WebSocket
- **Testing**: Jest + React Native Testing Library + Detox
- **Build**: Turborepo, Metro, Xcode, Gradle

### Project Structure
```
apps/mobile/
├── src/
│   ├── screens/          # 5 feature modules (auth, dashboard, etc)
│   ├── components/       # Reusable UI components
│   ├── services/         # API client, auth, database
│   ├── store/            # Redux state (5 slices)
│   ├── navigation/       # Navigation setup
│   └── hooks/            # Custom React hooks
├── ios/                  # Xcode project
├── android/              # Gradle project
├── __tests__/            # 30+ unit tests
├── e2e/                  # End-to-end tests
├── SETUP_GUIDE.md        # Complete setup instructions
└── ARCHITECTURE.md       # Detailed architecture docs
```

## Quick Start

### Prerequisites
- Node.js 18+ (LTS)
- npm 9+
- Xcode 14+ (for iOS) or Android Studio (for Android)
- CocoaPods (macOS)

### Installation
```bash
# Navigate to mobile directory
cd apps/mobile

# Install dependencies
npm install

# iOS setup
cd ios && pod install && cd ..

# Start development server
npm run dev

# In another terminal, run the app
npm run ios    # or npm run android
```

## Development Workflow

### Running Tests
```bash
npm run test              # Unit tests
npm run test:watch       # Watch mode
npm run test:coverage    # With coverage

npm run test:e2e:build   # E2E setup
npm run test:e2e         # Run E2E tests
```

### Linting & Type Checking
```bash
npm run lint             # Run ESLint
npm run lint:fix         # Fix issues
npm run type-check       # TypeScript check
```

### Building
```bash
npm run build:ios        # Production iOS build
npm run build:android    # Production Android build
npm run build:android:bundle  # Play Store bundle
```

## API Endpoints

All endpoints are relative to `REACT_APP_API_URL` (default: `https://api.neurex.com/api/v1`)

### Authentication
```
POST   /auth/login                    # Email/password login
POST   /auth/oauth/callback           # OAuth callback
POST   /auth/refresh                  # Token refresh
POST   /auth/logout                   # Logout
GET    /auth/biometric/verify         # Biometric verify
```

### Test Cases
```
GET    /projects/:projectId/test-cases
POST   /projects/:projectId/test-cases
PUT    /projects/:projectId/test-cases/:testCaseId
DELETE /projects/:projectId/test-cases/:testCaseId
```

### Execution
```
POST   /projects/:projectId/executions/start
GET    /projects/:projectId/executions
GET    /projects/:projectId/executions/:executionId
POST   /projects/:projectId/executions/:executionId/stop
```

### Defects
```
GET    /projects/:projectId/defects
POST   /projects/:projectId/defects
PUT    /projects/:projectId/defects/:defectId
POST   /projects/:projectId/defects/:defectId/comments
DELETE /projects/:projectId/defects/:defectId
```

## Environment Configuration

Create `.env` file in `apps/mobile/`:
```
REACT_APP_API_URL=https://api.neurex.com/api/v1
REACT_APP_AI_GATEWAY_URL=https://api.neurex.com/api/ai
REACT_APP_ENGINE_URL=https://api.neurex.com/api/engine
REACT_APP_OAUTH_CLIENT_ID=your_client_id
REACT_APP_OAUTH_REDIRECT_URL=neurex://auth/callback
REACT_APP_SENTRY_DSN=https://example@sentry.io/123456
REACT_APP_ENABLE_OFFLINE_MODE=true
REACT_APP_ENABLE_BIOMETRIC_AUTH=true
REACT_APP_ENABLE_PUSH_NOTIFICATIONS=true
NODE_ENV=development
```

## Project Timeline

**Duration**: 10-12 weeks, 4 FTE, ~15,000 LOC

| Week | Phase | Status |
|------|-------|--------|
| 1-2 | Project setup, authentication | ✓ Scaffolded |
| 3-5 | Core features (CRUD, execution) | In Progress |
| 6-8 | Results, offline, notifications | Planned |
| 9-10 | Performance, testing | Planned |
| 11-12 | App Store prep, beta launch | Planned |

## Code Quality

### Testing Coverage
- Unit Tests: 30+ tests (auth, store, services)
- Component Tests: 15+ test cases
- E2E Tests: 20+ critical user flows
- Target Coverage: 70%+ (branches, functions, lines)

### Code Standards
- TypeScript strict mode
- ESLint + Prettier
- Automated CI/CD with GitHub Actions
- Pre-commit hooks for lint/type check

### Performance Metrics
- App startup: <3 seconds
- Navigation transitions: 60 FPS
- API response handling: <1 second

## Deployment

### iOS
1. Build for release: `npm run build:ios`
2. Upload to TestFlight via Xcode or fastlane
3. Distribute to testers
4. Submit to App Store

### Android
1. Build APK/Bundle: `npm run build:android` or `npm run build:android:bundle`
2. Sign with production key
3. Upload to Google Play Console
4. Release to beta/production

## File Structure Summary

### Key Files (25+ implemented)

**Core Setup**
- `src/App.tsx` - Root component with Redux, navigation, queries
- `src/store/index.ts` - Redux store configuration (5 slices)
- `src/navigation/RootNavigator.tsx` - Complete navigation structure
- `index.js` - Entry point for React Native

**Services**
- `src/services/apiClient.ts` - Axios client with interceptors
- `src/services/authService.ts` - Auth logic (OAuth, biometric)
- `src/services/appInitializer.ts` - App startup sequence
- `src/services/database/sqliteManager.ts` - SQLite operations

**Redux Slices** (5)
- `src/store/slices/authSlice.ts` - Authentication state
- `src/store/slices/testCaseSlice.ts` - Test case management
- `src/store/slices/executionSlice.ts` - Execution results
- `src/store/slices/defectSlice.ts` - Defect tracking
- `src/store/slices/uiSlice.ts` - UI state (theme, offline, etc)

**Screens** (8)
- `src/screens/auth/LoginScreen.tsx` - Authentication UI
- `src/screens/SplashScreen.tsx` - Launch screen
- `src/screens/dashboard/DashboardScreen.tsx` - Main dashboard
- `src/screens/testCases/TestCasesScreen.tsx` - Test case list
- `src/screens/testCases/TestCaseDetailScreen.tsx` - Test case editor
- `src/screens/execution/ExecutionScreen.tsx` - Execution control
- `src/screens/execution/ExecutionResultScreen.tsx` - Results viewer
- `src/screens/defects/DefectsScreen.tsx` - Defects list
- `src/screens/defects/DefectDetailScreen.tsx` - Defect editor
- `src/screens/settings/SettingsScreen.tsx` - App settings

**Tests** (10+ files)
- `__tests__/setup.ts` - Jest configuration
- `__tests__/services/authService.test.ts` - Auth service tests
- `__tests__/store/slices/authSlice.test.ts` - Redux tests
- Plus E2E tests for critical flows

**Configuration** (7 files)
- `package.json` - Dependencies and scripts
- `tsconfig.json` - TypeScript configuration
- `babel.config.js` - Babel presets and plugins
- `metro.config.js` - Metro bundler config
- `jest.config.js` - Jest test configuration
- `.eslintrc.js` - ESLint rules
- `.prettierrc.js` - Code formatting

**GitHub Actions** (3 workflows)
- `.github/workflows/mobile-ios-build.yml` - iOS CI/CD
- `.github/workflows/mobile-android-build.yml` - Android CI/CD
- `.github/workflows/mobile-e2e-tests.yml` - E2E test pipeline

**Documentation** (3 guides)
- `SETUP_GUIDE.md` - Complete setup and development guide
- `ARCHITECTURE.md` - System and data flow architecture
- `README.md` - This file

## Common Commands

```bash
# Development
npm run dev                    # Start Metro bundler
npm run ios                    # Run on iOS simulator
npm run android               # Run on Android emulator

# Testing
npm run test                   # Run unit tests
npm run test:watch            # Watch mode
npm run test:coverage         # Coverage report
npm run test:e2e              # End-to-end tests

# Code Quality
npm run lint                   # Run linter
npm run lint:fix              # Fix lint errors
npm run type-check            # TypeScript check

# Building
npm run build:ios             # Production iOS build
npm run build:android         # Production Android APK
npm run build:android:bundle  # Play Store bundle

# Utilities
npm run bundle:ios            # Bundle for iOS
npm run bundle:android        # Bundle for Android
```

## Troubleshooting

### Metro Bundler Issues
```bash
npm run dev -- --reset-cache
watchman watch-del-all
```

### iOS/CocoaPods Issues
```bash
cd ios && rm -rf Pods Podfile.lock && pod install --repo-update && cd ..
```

### Android Gradle Issues
```bash
cd android && ./gradlew clean && ./gradlew assembleDebug && cd ..
```

### TypeScript Errors
```bash
npm run type-check
```

## Resources

- **[React Native Docs](https://reactnative.dev/docs/getting-started)**
- **[Redux Toolkit Guide](https://redux-toolkit.js.org/)**
- **[React Navigation](https://reactnavigation.org/docs/getting-started)**
- **[Detox E2E Testing](https://detoxe2e.com/docs/getting-started)**
- **[TypeScript Handbook](https://www.typescriptlang.org/docs/)**

## Contributing

1. Create feature branch: `git checkout -b feature/name`
2. Make changes and tests
3. Run: `npm run lint && npm run type-check && npm run test`
4. Submit pull request with description

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions:
1. Check [SETUP_GUIDE.md](./SETUP_GUIDE.md) for common issues
2. Review [ARCHITECTURE.md](./ARCHITECTURE.md) for design details
3. Create GitHub issue with reproduction steps
4. Submit pull requests with tests

---

**Last Updated**: 2026-06-09  
**Version**: 0.1.0 (MVP)  
**Maintainer**: Neurex Development Team
