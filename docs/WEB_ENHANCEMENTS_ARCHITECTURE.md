# Neurex Web Enhancements Architecture

## Overview

Comprehensive implementation of PWA, mobile optimization, performance tuning, and accessibility enhancements for Neurex QA platform. This 10-14 week roadmap covers 8.5K LOC across core features.

**Project Timeline**: 10-14 weeks | **Team**: 5-6 FTE | **Target**: Lighthouse 95+

---

## 1. PWA Support (Weeks 1-4)

### 1.1 Service Worker Infrastructure

**File**: `apps/web/public/sw.js` (v2.0 - 300+ LOC)

Core features:
- **Cache Strategies**
  - Static assets: cache-first (CSS, JS, images, fonts)
  - HTML pages: network-first with offline fallback
  - API calls: network-only (auth + freshness critical)
  
- **Background Sync**
  - Offline mutation queue → IndexedDB
  - Automatic sync when back online
  - Retry logic with exponential backoff

- **Push Notifications**
  - Message handling
  - Notification click/dismiss tracking
  - Action button support

- **Versioning**
  - `CACHE_VERSION` bumping triggers cleanup
  - Old caches automatically deleted

### 1.2 PWA Library

**File**: `apps/web/lib/pwa.ts` (600+ LOC)

Key exports:

```typescript
// Service Worker Management
registerServiceWorker()
getServiceWorkerRegistration()
updateServiceWorker()
unregisterServiceWorker()

// Push Notifications
requestNotificationPermission()
subscribeToPush(vapidPublicKey)
getPushSubscription()
unsubscribeFromPush()

// Background Sync
requestBackgroundSync(tag)
getPendingSyncTags()

// Offline Queue (IndexedDB)
openOfflineDB()
queueOfflineMutation(url, method, body, headers)
getQueuedMutations()
removeQueuedMutation(id)
clearOfflineQueue()

// Network Status
isOnline()
onOnline(callback)
onOffline(callback)

// Installation
isAppInstalled()
onAppInstalled(callback)

// Screen & Fullscreen
lockScreenOrientation(orientation)
unlockScreenOrientation()
requestFullscreen(element)
exitFullscreen()

// Web Share API
share(data)
canShare()

// Haptic Feedback
vibrate(pattern)
hapticPatterns // { tap, success, warning, error, notify }
```

### 1.3 Enhanced PWARegister Component

**File**: `apps/web/components/PWARegister.tsx` (150+ LOC)

Features:
- Install prompt UI with dismiss preference
- Push notification subscription prompt
- Service worker controller change detection
- Notification permission check

```typescript
<PWARegister />
```

### 1.4 Web App Manifest

**File**: `apps/web/public/manifest.json`

```json
{
  "name": "Neurex QA",
  "short_name": "Neurex",
  "start_url": "/",
  "display": "standalone",
  "icons": [{ "src": "/icon-192.svg", "sizes": "192x192", "purpose": "any maskable" }],
  "screenshots": [
    { "src": "/screenshot-mobile.png", "sizes": "540x720", "form_factor": "narrow" },
    { "src": "/screenshot-desktop.png", "sizes": "1280x720", "form_factor": "wide" }
  ],
  "shortcuts": [
    { "name": "Activity Monitor", "url": "/", "icons": [...] },
    { "name": "Projects", "url": "/portfolio" },
    { "name": "Scenario IDE", "url": "/ide" }
  ],
  "categories": ["productivity", "developer"],
  "orientation": "any",
  "theme_color": "#6366f1",
  "background_color": "#0c0e14"
}
```

---

## 2. Mobile Optimization (Weeks 3-6)

### 2.1 Responsive Design System

**CSS-Grid + Flexbox patterns** for responsive layouts:

```css
/* Mobile-first base */
@media (max-width: 640px) {
  /* sm: single column, full width */
}

@media (min-width: 641px) and (max-width: 1024px) {
  /* md: 2 columns, padding */
}

@media (min-width: 1025px) {
  /* lg: grid layout */
}
```

**Safe Area Insets** for notch support:
```css
padding: max(1rem, env(safe-area-inset-top)) 
         max(1rem, env(safe-area-inset-right)) 
         max(1rem, env(safe-area-inset-bottom)) 
         max(1rem, env(safe-area-inset-left));
```

### 2.2 Mobile Components

**File**: `apps/web/components/BottomSheet.tsx` (250+ LOC)

- **BottomSheet**: Slide-up modal for mobile
  - Snap points configuration
  - Swipe-to-dismiss with threshold
  - Focus trap + Escape key handling

- **MobileBottomNavigation**: Tab bar for mobile navigation
  - Touch-friendly 44px minimum touch target
  - Active state indicators

- **TouchButton**: Enhanced button with haptic feedback
  - Minimum 44x44px touch target (WCAG)
  - Haptic patterns (tap, success, warning, error)

- **Swipeable**: Container for swipe gesture detection
  - Configurable threshold
  - Directional callbacks

### 2.3 Touch Gestures

Implemented via native touch events:

```typescript
// Long-press
onTouchStart() -> setTimeout() -> onLongPress()

// Swipe detection
onTouchStart() -> track coordinates
onTouchEnd() -> calculate distance & direction

// Pinch (via 2-touch tracking)
onTouchStart() -> calculate distance
onTouchMove() -> track scale changes
```

### 2.4 Safe Area Handling

```typescript
// CSS env() variables
safe-area-inset-top
safe-area-inset-right
safe-area-inset-bottom
safe-area-inset-left

// Used in viewport meta tag
viewport-fit=cover
```

---

## 3. Performance Tuning (Weeks 5-10)

### 3.1 Core Web Vitals Monitoring

**File**: `apps/web/lib/performance.ts` (600+ LOC)

Metrics tracked:

```typescript
// LCP: Largest Contentful Paint (target: <2.5s)
onLCP(callback: MetricsCallback)

// INP: Interaction to Next Paint (target: <200ms)
onINP(callback: MetricsCallback)

// CLS: Cumulative Layout Shift (target: <0.1)
onCLS(callback: MetricsCallback)

// FCP: First Contentful Paint (target: <1.8s)
onFCP(callback: MetricsCallback)

// TTFB: Time to First Byte (target: <600ms)
getTTFB()
onTTFB(callback: MetricsCallback)

// Consolidated observer
observeWebVitals(callback: MetricsCallback)
```

**Rating System**:
- Good: meets target
- Needs Improvement: between target and poor threshold
- Poor: exceeds poor threshold

### 3.2 Code Splitting Strategy

**Next.js Dynamic Imports**:

```typescript
// Route-based splitting
const Dashboard = dynamic(() => import('./dashboard'), { 
  loading: () => <Skeleton />,
  ssr: false // Optional: disable SSR
})

// Component splitting
const HeavyEditor = dynamic(() => import('@/components/Editor'))

// Conditional splitting
const HeavyChart = process.env.NEXT_PUBLIC_CHARTS === 'true' 
  ? dynamic(() => import('@/components/Chart'))
  : null
```

**tree-shaking Configuration** (next.config.mjs):

```javascript
experimental: {
  optimizePackageImports: [
    "lucide-react",      // Icons
    "framer-motion",     // Animations
    "recharts",          // Charts
    "@radix-ui/*",       // UI components
    "@tanstack/*",       // Query/Virtual
    "@dnd-kit/*",        // Drag-drop
  ]
}
```

### 3.3 Image Optimization

**File**: `apps/web/lib/image-optimization.ts` (500+ LOC)

Features:

```typescript
// WebP format detection
checkWebPSupport(): Promise<boolean>
getPreferredImageFormat(): Promise<'webp' | 'png' | 'jpg'>

// Responsive image generation
getOptimizedImageUrl(src, width, format)
generateResponsiveSrcset(src, widths, format)
generateSizes(breakpoints)

// Picture element generation
createPictureElement(src, alt, options)

// Lazy loading
lazyLoadImages(selector)

// Image preloading
preloadImage(src)
preloadImages(srcs)

// Critical images
addImagePreload(src, imagesrcset)
prefetchImages(srcs)

// Compression analysis
analyzeImage(file)
```

**Next.js Image Component Configuration**:

```javascript
images: {
  formats: ["image/avif", "image/webp"],
  deviceSizes: [320, 375, 425, 640, 768, 1024, 1280, 1536],
  imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  minimumCacheTTL: 60 * 60 * 24 * 365, // 1 year
}
```

### 3.4 Font Optimization

**In layout.tsx**:

```typescript
const inter = Inter({
  subsets: ["latin", "latin-ext"],
  display: "swap",        // Use system font until loaded
  variable: "--font-sans",
  weight: ["400", "500", "600", "700", "800"],
})

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
  weight: ["400", "500", "700"],
})
```

**CSS Optimization**:
- Variable fonts reduce file size
- `font-display: swap` prevents FOUT (Flash of Unstyled Text)
- Preload critical fonts via `<link rel="preload">`

### 3.5 Resource Hints

```html
<!-- DNS Prefetch -->
<link rel="dns-prefetch" href="https://api.example.com">

<!-- Preconnect -->
<link rel="preconnect" href="https://api.example.com">

<!-- Prefetch (low priority) -->
<link rel="prefetch" href="next-page.html">

<!-- Preload (critical) -->
<link rel="preload" href="critical-font.woff2" as="font" type="font/woff2" crossorigin>
```

### 3.6 Bundle Analysis

```bash
# Analyze bundle size
npm install -D @next/bundle-analyzer

# In next.config.mjs
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
})

export default withBundleAnalyzer(nextConfig)

# Run analysis
ANALYZE=true npm run build
```

---

## 4. Advanced Features (Weeks 7-12)

### 4.1 Real-time Collaboration

**Tech Stack**: WebSocket + Operational Transform (OT) library

```typescript
// Usage
const collaboration = new Collaboration({
  documentId: "doc-123",
  userId: currentUser.id,
  onRemoteChange: (delta) => applyDelta(delta),
})

// Local change
collaboration.localChange({ type: 'insert', pos: 10, text: 'hello' })

// Listen to remote changes
collaboration.on('remoteChange', (delta) => {
  editor.applyDelta(delta)
})
```

**Libraries**:
- `yjs` or `automerge` for OT/CRDT
- `y-websocket` for WebSocket sync
- `y-monaco` or `y-codemirror` for editor bindings

### 4.2 Saved Filters + Shared Views

**Backend API**:
```typescript
POST /api/v1/filters
{
  name: "My Filter",
  query: { status: "active" },
  shared: true,
  sharedWith: ["user-2", "team-3"]
}

GET /api/v1/filters/shared
GET /api/v1/views/{id}/share?token=xyz
```

**Frontend**:
- Save filter state to backend
- Restore on page reload
- Share via URL token
- Collaborative editing of shared filters

### 4.3 Custom Dashboard (React Grid Layout)

```typescript
import GridLayout from 'react-grid-layout'

export function CustomDashboard() {
  const [layout, setLayout] = useState(initialLayout)

  return (
    <GridLayout
      layout={layout}
      cols={12}
      rowHeight={30}
      onLayoutChange={(newLayout) => {
        setLayout(newLayout)
        saveLayout(newLayout) // Backend
      }}
    >
      {layout.map(item => (
        <div key={item.i} className="grid-item">
          <Widget id={item.i} />
        </div>
      ))}
    </GridLayout>
  )
}
```

**Libraries**:
- `react-grid-layout` for drag-drop grid
- `react-resizable` for resize handles

### 4.4 Export Functionality

**CSV Export**:
```typescript
function exportToCSV(data: any[], filename: string) {
  const csv = [
    Object.keys(data[0]).join(','),
    ...data.map(row => Object.values(row).join(','))
  ].join('\n')

  downloadFile(csv, `${filename}.csv`, 'text/csv')
}
```

**PDF Export** (via `pdfkit`):
```typescript
import PDFDocument from 'pdfkit'

function exportToPDF(data: any, filename: string) {
  const doc = new PDFDocument()
  doc.text(JSON.stringify(data, null, 2))
  doc.pipe(fs.createWriteStream(`${filename}.pdf`))
  doc.end()
}
```

**Excel Export** (via `xlsx`):
```typescript
import XLSX from 'xlsx'

function exportToExcel(data: any[], filename: string) {
  const worksheet = XLSX.utils.json_to_sheet(data)
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, "Sheet1")
  XLSX.writeFile(workbook, `${filename}.xlsx`)
}
```

### 4.5 Analytics Integration

**Mixpanel**:
```typescript
import mixpanel from 'mixpanel-browser'

mixpanel.init(MIXPANEL_TOKEN)

// Track event
mixpanel.track('test_case_created', {
  caseId: 'case-123',
  duration: 120,
  platform: 'web'
})
```

**Amplitude**:
```typescript
import * as amplitude from '@amplitude/analytics-browser'

amplitude.init(AMPLITUDE_TOKEN)

// Track with properties
amplitude.track('scenario_executed', {
  scenarioId: 'scenario-123',
  status: 'passed',
  executionTime: 45000
})
```

---

## 5. Accessibility (WCAG 2.1 AAA) (Weeks 9-13)

### 5.1 Color Contrast Validation

**File**: `apps/web/lib/accessibility.ts` (500+ LOC)

```typescript
// Check contrast ratio
validateContrast("#000000", "#ffffff", "AAA")
// { pass: true, ratio: 21, required: 7 }

// Get luminance
getContrastRatio("#333333", "#cccccc") // 4.67:1
```

**WCAG Standards**:
- AA: 4.5:1 (normal text), 3:1 (large text)
- AAA: 7:1 (normal text), 4.5:1 (large text)

### 5.2 Focus Management

```typescript
// Focus trap for modals
const trap = new FocusTrap(modalElement, {
  initialFocus: submitButton,
  restoreFocus: true,
  onEscape: onClose,
})

trap.activate()
// ... modal is open
trap.deactivate()

// Check focus visibility
isFocusVisible(element) // true/false
focusElement(element) // Cross-browser focus
```

### 5.3 Keyboard Navigation

```typescript
// Skip to main content link
const skipLink = createSkipLink("main-content")
document.body.insertBefore(skipLink, document.body.firstChild)

// Get focusable elements
const focusables = getFocusableElements(container)

// Check if focusable
isFocusable(element) // true/false
```

### 5.4 ARIA Labels & Descriptions

```typescript
// Create unique ARIA ID
const id = createAriaId("panel") // "aria-panel-xyz123"

// Live region announcements
announceToScreenReader("Test case created successfully", "assertive")

// Make div a button
makeAccessibleButton(element, () => {
  // Handle activation
})
```

### 5.5 Screen Reader Testing

**Testing Matrix**:
| Browser | Screen Reader | Desktop | Mobile |
|---------|---------------|---------|--------|
| Firefox | NVDA          | Yes     | No     |
| Chrome  | JAWS          | Yes     | No     |
| Safari  | VoiceOver     | Yes     | Yes    |
| Edge    | Narrator      | Yes     | No     |

**Test Coverage**:
- [ ] Page title and headings
- [ ] Form labels and error messages
- [ ] Button and link purposes
- [ ] Navigation landmarks
- [ ] Dynamic content updates (aria-live)
- [ ] Images and icons (alt text)

### 5.6 Accessibility Audit

```typescript
// Run automated audit
const issues = auditAccessibility()
// [
//   { type: "missing-alt", severity: "error", element: img, message: "..." },
//   { type: "low-contrast", severity: "warning", ... }
// ]
```

### 5.7 Reduced Motion Support

```typescript
// Check if user prefers reduced motion
if (prefersReducedMotion()) {
  // Disable animations
  animation: none
}

// Listen for changes
onReducedMotionChange((prefersReduced) => {
  element.style.animation = prefersReduced ? 'none' : 'fadeIn 0.3s'
})
```

### 5.8 High Contrast Mode

```typescript
// Detect high contrast preference
if (prefersHighContrast()) {
  // Use high-contrast colors
  borderWidth: 2px // thicker borders
  color: black // stronger colors
}

// Dark mode preference
if (prefersDarkMode()) {
  // Apply dark theme
  backgroundColor: '#0c0e14'
}
```

---

## 6. Testing Strategy (Weeks 11-14)

### 6.1 PWA Testing

**Playwright E2E Tests**:

```typescript
// test/pwa.spec.ts
test('install prompt shows on first visit', async ({ page }) => {
  await page.goto('/')
  const installPrompt = page.getByTestId('pwa-install-prompt')
  await expect(installPrompt).toBeVisible()
})

test('service worker caches static assets', async ({ page }) => {
  await page.goto('/')
  // Go offline
  await page.context().setOffline(true)
  // Should still work due to cache
  await expect(page.locator('body')).toBeVisible()
})

test('background sync queues mutation when offline', async ({ page }) => {
  await page.context().setOffline(true)
  await page.getByRole('button', { name: 'Save' }).click()
  // Should queue
  const queuedCount = await page.evaluate(() => {
    return new Promise(resolve => {
      indexedDB.open('neurex_offline').onsuccess = (e) => {
        const tx = e.target.transaction('offline_queue')
        const store = tx.objectStore('offline_queue')
        store.getAll().onsuccess = () => resolve(store.getAll().result.length)
      }
    })
  })
  expect(queuedCount).toBeGreaterThan(0)
})
```

### 6.2 Accessibility Testing

**Jest Component Tests**:

```typescript
// test/accessibility.test.ts
describe('Accessibility', () => {
  test('button has accessible name', () => {
    const { container } = render(
      <button aria-label="Create test case">+</button>
    )
    expect(hasAccessibleName(container.firstChild)).toBe(true)
  })

  test('form field has associated label', () => {
    const { container } = render(
      <>
        <label htmlFor="name">Name</label>
        <input id="name" />
      </>
    )
    expect(hasAccessibleName(container.querySelector('input'))).toBe(true)
  })

  test('focus trap works', () => {
    const { container } = render(<Modal />)
    const trap = new FocusTrap(container)
    trap.activate()
    expect(document.activeElement).toBeInTheDocument()
  })
})
```

**Automated Audits** (axe):

```typescript
import { axe } from 'jest-axe'

test('no accessibility violations', async () => {
  const { container } = render(<App />)
  const results = await axe(container)
  expect(results).toHaveNoViolations()
})
```

### 6.3 Performance Testing

**Lighthouse CI**:

```bash
# lighthouse.json
{
  "ci": {
    "collect": {
      "url": ["http://localhost:3000"],
      "numberOfRuns": 3
    },
    "upload": {
      "target": "temporary-public-storage"
    },
    "assert": {
      "preset": "lighthouse:recommended",
      "assertions": {
        "categories:performance": ["error", { "minScore": 0.95 }],
        "categories:accessibility": ["error", { "minScore": 0.95 }],
        "categories:best-practices": ["error", { "minScore": 0.95 }]
      }
    }
  }
}
```

**Bundle Size Testing**:

```bash
# Jest budget test
test('bundle size is under budget', async () => {
  const stats = await getWebpackStats()
  expect(stats.totalSize).toBeLessThan(250 * 1024) // 250KB
})
```

### 6.4 Test Coverage Goals

| Category | Target | Current |
|----------|--------|---------|
| Component tests | 80+ new | 0 |
| E2E tests (PWA) | 15+ new | 0 |
| Accessibility tests | 20+ new | 0 |
| Performance tests | 10+ new | 0 |
| **Total** | **125+** | **0** |

---

## 7. Infrastructure & DevOps

### 7.1 Environment Variables

```bash
# .env.local (development)
NEXT_PUBLIC_VAPID_KEY=your_public_key
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_ANALYTICS_ID=analytics_key

# .env.production
NEXT_PUBLIC_VAPID_KEY=prod_public_key
NEXT_PUBLIC_API_BASE=https://api.neurex.io
NEXT_PUBLIC_ANALYTICS_ID=prod_analytics_key
```

### 7.2 Build Optimization

**next.config.mjs**:

```javascript
// Enable SWC minification (faster builds)
swcMinify: true

// Disable source maps in production
productionBrowserSourceMaps: false

// Image optimization
images: {
  formats: ["image/avif", "image/webp"],
  deviceSizes: [320, 640, 960, 1280, 1920],
}

// Tree-shaking
experimental: {
  optimizePackageImports: [
    "lucide-react",
    "framer-motion",
    "@radix-ui/*",
    "@tanstack/*",
  ]
}
```

### 7.3 CI/CD Pipeline

```yaml
# .github/workflows/web.yml
name: Web Build & Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      
      - name: Install dependencies
        run: npm ci
      
      - name: Type check
        run: npm run type-check
      
      - name: Lint
        run: npm run lint
      
      - name: Build
        run: npm run build
      
      - name: Run tests
        run: npm run test
      
      - name: Run E2E tests
        run: npm run test:e2e
      
      - name: Lighthouse CI
        run: npm install -g @lhci/cli@* && lhci autorun
```

---

## 8. Migration & Rollout Plan

### 8.1 Phase 1: PWA Foundation (Weeks 1-4)

- [ ] Implement Service Worker v2
- [ ] Add PWA library utilities
- [ ] Update manifest.json
- [ ] Create PWARegister component
- [ ] Test offline functionality
- [ ] Push notification setup (backend support needed)

**Deliverables**:
- Service worker with offline support
- PWA installability
- 50+ test cases

### 8.2 Phase 2: Mobile & Responsive (Weeks 3-6)

- [ ] Mobile components (BottomSheet, NavBar, TouchButton)
- [ ] Responsive breakpoints
- [ ] Touch gesture handling
- [ ] Safe area support
- [ ] Mobile navigation

**Deliverables**:
- 100% responsive layout
- Mobile-optimized components
- 30+ mobile-specific tests

### 8.3 Phase 3: Performance (Weeks 5-10)

- [ ] Web Vitals monitoring
- [ ] Code splitting implementation
- [ ] Image optimization
- [ ] Font optimization
- [ ] Bundle analysis

**Deliverables**:
- Lighthouse 95+ on all pages
- <3.0s LCP target
- <0.1s CLS target
- 20+ performance tests

### 8.4 Phase 4: Advanced Features (Weeks 7-12)

- [ ] Real-time collaboration
- [ ] Saved filters backend support
- [ ] Custom dashboard
- [ ] Export functionality
- [ ] Analytics integration

**Deliverables**:
- Collaboration API integration
- 4 export formats (CSV, PDF, Excel, JSON)
- Custom dashboard working

### 8.5 Phase 5: Accessibility (Weeks 9-13)

- [ ] Color contrast audit & fixes
- [ ] Keyboard navigation full coverage
- [ ] ARIA labels comprehensive
- [ ] Screen reader testing
- [ ] Accessibility audit CI/CD

**Deliverables**:
- WCAG 2.1 AAA compliance
- Zero critical violations
- 20+ accessibility tests

### 8.6 Phase 6: Testing & Launch (Weeks 11-14)

- [ ] Comprehensive test suite (125+ tests)
- [ ] Lighthouse CI setup
- [ ] Performance budget enforcement
- [ ] Production deployment
- [ ] Monitoring setup

**Deliverables**:
- 125+ new tests (all passing)
- 95+ Lighthouse score maintained
- Zero critical bugs in production

---

## 9. File Structure

```
apps/web/
├── public/
│   ├── sw.js                 # Service Worker (v2)
│   ├── manifest.json         # PWA Manifest
│   ├── icon-192.svg
│   ├── icon-512.svg
│   └── offline.html          # Offline fallback page
│
├── app/
│   ├── layout.tsx            # Updated with PWA bootstrap
│   ├── offline/
│   │   └── page.tsx          # Offline page
│   └── globals.css           # Updated with safe-area
│
├── lib/
│   ├── pwa.ts                # PWA utilities (600 LOC)
│   ├── performance.ts        # Web Vitals (600 LOC)
│   ├── image-optimization.ts # Image utilities (500 LOC)
│   ├── accessibility.ts      # A11y utilities (500 LOC)
│   ├── test-utils.ts         # Testing helpers (400 LOC)
│   └── hooks/
│       └── use-offline-mutation.ts  # Offline mutations hook
│
├── components/
│   ├── PWARegister.tsx       # PWA UI (150 LOC)
│   ├── BottomSheet.tsx       # Mobile components (250 LOC)
│   └── OptimizedImage.tsx    # Lazy-loaded images
│
├── app/__tests__/
│   ├── pwa.test.tsx          # PWA tests
│   ├── accessibility.test.tsx # A11y tests
│   ├── performance.test.tsx   # Perf tests
│   ├── mobile.test.tsx        # Mobile tests
│   └── offline.test.tsx       # Offline tests
│
├── e2e/
│   ├── pwa.spec.ts           # PWA E2E
│   ├── offline.spec.ts        # Offline E2E
│   ├── mobile.spec.ts         # Mobile E2E
│   └── accessibility.spec.ts  # A11y E2E
│
├── next.config.mjs           # Updated with PWA config
├── package.json              # Updated dependencies
└── tsconfig.json             # TypeScript config
```

---

## 10. Key Metrics & Success Criteria

### 10.1 Performance Targets

| Metric | Target | Success |
|--------|--------|---------|
| LCP | <2.5s | <2.0s |
| INP | <200ms | <100ms |
| CLS | <0.1 | <0.05 |
| FCP | <1.8s | <1.5s |
| TTFB | <600ms | <400ms |
| Lighthouse | 90+ | 95+ |

### 10.2 Accessibility Targets

| Aspect | Target |
|--------|--------|
| WCAG Level | 2.1 AAA |
| Color Contrast | 7:1 minimum |
| Keyboard Coverage | 100% |
| Screen Reader | Fully tested |
| Critical Issues | 0 |

### 10.3 PWA Targets

| Feature | Target |
|---------|--------|
| Service Worker | 100% routes |
| Offline Support | Key pages |
| Installability | 100% score |
| Push Notifications | Opt-in |
| Background Sync | Enabled |

### 10.4 Testing Targets

| Category | Target |
|----------|--------|
| Unit Tests | 80+ new |
| Component Tests | 30+ new |
| E2E Tests | 15+ new |
| Accessibility Tests | 20+ new |
| Total Coverage | 125+ tests |

---

## 11. Dependencies to Add

```json
{
  "dependencies": {
    "yjs": "^13.6.0",
    "y-websocket": "^1.5.0",
    "pdfkit": "^0.13.0",
    "xlsx": "^0.18.5",
    "react-grid-layout": "^1.3.4",
    "react-resizable": "^3.0.1",
    "mixpanel-browser": "^2.49.0",
    "@amplitude/analytics-browser": "^1.10.0"
  },
  "devDependencies": {
    "@next/bundle-analyzer": "^14.0.0",
    "@lhci/cli": "^0.9.0",
    "jest-axe": "^8.0.0"
  }
}
```

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| LCP | Largest Contentful Paint - largest visual element |
| INP | Interaction to Next Paint - responsiveness metric |
| CLS | Cumulative Layout Shift - visual stability |
| FCP | First Contentful Paint - first content render |
| TTFB | Time to First Byte - backend response time |
| PWA | Progressive Web App - installable web experience |
| WCAG | Web Content Accessibility Guidelines |
| AAA | Highest accessibility conformance level |
| ARIA | Accessible Rich Internet Applications |
| OT | Operational Transform - concurrent editing |
| LQIP | Low Quality Image Placeholder |
| Safe Area | Device notch + home indicator space |

---

## 13. References & Resources

- [Web.dev - Performance](https://web.dev/performance/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [PWA Checklist](https://web.dev/pwa/)
- [MDN - Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [Next.js Image Optimization](https://nextjs.org/docs/basic-features/image-optimization)
- [Lighthouse Scoring](https://developers.google.com/web/tools/lighthouse/v3/scoring)

---

**Last Updated**: June 2026 | **Status**: Architecture Ready | **Owner**: Web Engineering Team
