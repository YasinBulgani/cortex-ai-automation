# Neurex Web Improvements — Implementation Roadmap & Tech Deep Dive
**Document:** WEB_IMPROVEMENTS_IMPLEMENTATION_ROADMAP_2026_06_09.md  
**Generated:** 2026-06-09  
**Scope Reference:** WEB_IMPROVEMENTS_SCOPE_2026_06_09.md

---

## Feature 1: PWA Support — Detailed Implementation Roadmap

### Week 1: Service Worker & Cache Strategy

#### Day 1–2: Service Worker Foundation
**Owner:** Dev 1  
**Tasks:**
```typescript
// /app/sw.ts (refactor from public/sw.js)
const CACHE_VERSION = "neurex-v1";
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const PAGE_CACHE = `${CACHE_VERSION}-pages`;
const API_CACHE = `${CACHE_VERSION}-api-readonly`; // NEW: read-only API cache (15min TTL)

// Cache versioning: bump CACHE_VERSION on each release
// Deletion: oldVersion → new version auto-cleanup in activate event

// Strategies:
// 1. HTML (navigate): network-first, fallback to PAGE_CACHE, then /offline
// 2. Assets (_next/static, /icon-*, /manifest.json): cache-first with network fallback
// 3. API (/api/v1/*): network-only (auth + freshness critical)
// 4. Images (/*.{png,jpg,webp}): cache-first (expires after 24h)
```

**Deliverable:** Public Service Worker with 3+ cache strategies, 0 console errors

#### Day 3–4: Background Sync Registration
**Owner:** Dev 1  
**Tasks:**
```typescript
// /lib/sync/background-sync.ts (NEW)
export class BackgroundSyncManager {
  async registerSync(tag: 'mutations' | 'reports') {
    if (!('serviceWorker' in navigator)) return false;
    try {
      const registration = await navigator.serviceWorker.ready;
      await registration.sync.register(tag);
      return true;
    } catch (e) {
      console.error('Sync registration failed:', e);
      return false;
    }
  }

  // Listen for sync events in component
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return;
    const handler = async (event: SyncEvent) => {
      if (event.tag === 'mutations') {
        await syncPendingMutations(); // IndexedDB-based queue
      }
    };
    navigator.serviceWorker.addEventListener('sync', handler);
    return () => navigator.serviceWorker.removeEventListener('sync', handler);
  }, []);
}
```

**Deliverable:** SW can register background sync, fallback to manual trigger

#### Day 5: Install Prompt & Splash Screen
**Owner:** Dev 1  
**Tasks:**
- Detect `beforeinstallprompt` event in component
- Show custom "Add to Home Screen" banner (2-3 seconds, dismissible)
- iOS fallback: modal with screenshot + instructions ("Share → Add to Home Screen")
- Splash screen: white/dark logo on solid background (matches theme_color)
- CSS: `@media (display-mode: standalone)` for app-only styling

**Code Example:**
```typescript
// /components/PWAInstallPrompt.tsx (NEW)
export function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [canInstall, setCanInstall] = useState(false);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setCanInstall(true);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    analytics.track('pwa_install', { outcome });
    setDeferredPrompt(null);
    setCanInstall(false);
  };

  return canInstall ? (
    <Toast variant="info" onDismiss={() => setCanInstall(false)}>
      Install Neurex on your device <Button onClick={handleInstall}>Add</Button>
    </Toast>
  ) : null;
}
```

**Deliverable:** Install prompt on Chrome, Edge; iOS fallback instructions; splash screen CSS

### Week 2: IndexedDB & Sync Queue

#### Day 6–7: IndexedDB Schema & Manager
**Owner:** Dev 2  
**Tasks:**
```typescript
// /lib/db/index-db.ts (NEW)
import { openDB, DBSchema, IDBPDatabase } from 'idb';

interface NeurexDB extends DBSchema {
  sync_queue: {
    key: string; // UUID
    value: {
      id: string;
      domain: 'cases' | 'defects' | 'settings';
      action: 'create' | 'update' | 'delete';
      endpoint: string;
      payload: Record<string, any>;
      retryCount: number;
      maxRetries: number;
      enqueuedAt: number;
      attempts: Array<{ timestamp: number; error?: string }>;
    };
    indexes: { 'by-domain': 'domain'; 'by-status': 'domain'; };
  };
  offline_pages: {
    key: string; // URL
    value: {
      url: string;
      html: string;
      timestamp: number;
    };
  };
}

export class OfflineDB {
  private db: IDBPDatabase<NeurexDB> | null = null;

  async init() {
    this.db = await openDB<NeurexDB>('neurex', 1, {
      upgrade(db) {
        db.createObjectStore('sync_queue', { keyPath: 'id' });
        db.createObjectStore('offline_pages', { keyPath: 'url' });
      },
    });
  }

  async addToQueue(mutation: SyncMutation) {
    return this.db?.add('sync_queue', {
      id: crypto.randomUUID(),
      ...mutation,
      retryCount: 0,
      maxRetries: 5,
      enqueuedAt: Date.now(),
      attempts: [],
    });
  }

  async syncAll() {
    const queue = await this.db?.getAll('sync_queue');
    return Promise.all(queue?.map(item => this.syncItem(item)) ?? []);
  }

  private async syncItem(item: any) {
    try {
      const response = await fetch(item.endpoint, {
        method: 'POST',
        body: JSON.stringify(item.payload),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await this.db?.delete('sync_queue', item.id);
    } catch (error) {
      item.retryCount++;
      item.attempts.push({ timestamp: Date.now(), error: String(error) });
      if (item.retryCount < item.maxRetries) {
        await this.db?.put('sync_queue', item);
      } else {
        // Move to dead-letter or notify user
        console.error('Sync failed after retries:', item);
      }
    }
  }
}
```

**Deliverable:** IndexedDB schema initialized, queue manager with retry logic

#### Day 8–9: Offline UI & Sync Status Indicator
**Owner:** Dev 2  
**Tasks:**
```typescript
// /components/SyncStatusIndicator.tsx (NEW)
export function SyncStatusIndicator() {
  const [syncStatus, setSyncStatus] = useState<'online' | 'offline' | 'syncing' | 'error'>('online');
  const [queueCount, setQueueCount] = useState(0);
  const offlineDB = useOfflineDB();

  useEffect(() => {
    const handleOnline = () => setSyncStatus('online');
    const handleOffline = () => setSyncStatus('offline');

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Poll queue count every 2s
    const interval = setInterval(async () => {
      const db = await offlineDB.init();
      const count = await db.countQueue();
      setQueueCount(count);
    }, 2000);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearInterval(interval);
    };
  }, [offlineDB]);

  if (syncStatus === 'online' && queueCount === 0) return null;

  return (
    <div className="fixed bottom-4 left-4 bg-slate-900 text-white px-3 py-2 rounded-lg flex items-center gap-2">
      {syncStatus === 'offline' && (
        <>
          <WifiOff size={16} />
          <span className="text-sm">Offline ({queueCount} pending)</span>
          <Button size="sm" onClick={() => offlineDB.syncAll()}>Sync Now</Button>
        </>
      )}
      {syncStatus === 'syncing' && (
        <>
          <Loader size={16} className="animate-spin" />
          <span className="text-sm">Syncing...</span>
        </>
      )}
      {syncStatus === 'error' && (
        <>
          <AlertCircle size={16} />
          <span className="text-sm">Sync error (will retry)</span>
        </>
      )}
    </div>
  );
}
```

**Deliverable:** Offline indicator with queue count + manual sync button

#### Day 10: Offline Routing & Fallback Pages
**Owner:** Dev 1  
**Tasks:**
- Create `/app/offline/page.tsx` with offline status + retry CTA
- Add offline fallback to SW for unhandled routes
- Update Service Worker activate/fetch events for graceful degradation
- Test: simulate offline (DevTools → Network → Offline)

**Deliverable:** `/offline` page accessible, SW returns cached page or /offline

### Week 3: Push Notifications & E2E Testing

#### Day 11–12: Push Notification Handler
**Owner:** Dev 2  
**Tasks:**
```typescript
// /lib/push-notifications.ts (NEW)
export class PushNotificationManager {
  async requestPermission(): Promise<boolean> {
    if (!('Notification' in window)) return false;
    if (Notification.permission === 'granted') return true;
    if (Notification.permission !== 'denied') {
      const permission = await Notification.requestPermission();
      return permission === 'granted';
    }
    return false;
  }

  async setupPushHandler() {
    if (!('serviceWorker' in navigator)) return;
    const registration = await navigator.serviceWorker.ready;
    
    registration.addEventListener('push', (event: PushEvent) => {
      const data = event.data?.json() ?? {};
      const options: NotificationOptions = {
        body: data.body,
        icon: '/icon-192.svg',
        badge: '/icon-192.svg',
        tag: data.tag ?? 'notification', // Grouping
        data: { url: data.url ?? '/' },
      };
      event.waitUntil(
        self.registration.showNotification(data.title ?? 'Neurex', options)
      );
    });

    registration.addEventListener('notificationclick', (event: NotificationEvent) => {
      event.notification.close();
      const url = event.notification.data.url;
      event.waitUntil(
        clients.matchAll({ type: 'window' }).then((windows) => {
          const existing = windows.find(w => new URL(w.url).pathname === new URL(url, self.location.origin).pathname);
          return existing ? existing.focus() : clients.openWindow(url);
        })
      );
    });
  }

  async subscribeToPush(endpoint: string): Promise<void> {
    const registration = await navigator.serviceWorker.ready;
    if (!registration.pushManager) return;
    
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY,
    });
    
    // Send subscription to backend
    await fetch(endpoint, {
      method: 'POST',
      body: JSON.stringify(subscription),
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
```

**Deliverable:** Push handler, notification click navigation, subscription to backend

#### Day 13–15: E2E Tests & QA
**Owner:** Dev 1 + QA  
**Tasks:**
```typescript
// /e2e/pwa.spec.ts (NEW)
import { test, expect } from '@playwright/test';

test.describe('PWA Functionality', () => {
  test('offline page loads when service worker installed', async ({ browser, page }) => {
    // Install SW
    await page.goto('http://localhost:3000');
    await page.waitForFunction(() => {
      return navigator.serviceWorker.controller;
    });
    
    // Go offline
    await page.context().setOffline(true);
    await page.goto('http://localhost:3000/portfolio'); // Cached route
    
    // Should load
    await expect(page.locator('text=Projeler')).toBeVisible();
    
    // Try uncached route
    await page.goto('http://localhost:3000/unknown-route');
    await expect(page.locator('text=Offline')).toBeVisible();
  });

  test('background sync resumes after reconnect', async ({ page }) => {
    // Queue mutation while offline
    await page.context().setOffline(true);
    await page.goto('http://localhost:3000');
    await page.click('button:has-text("New Defect")');
    await page.fill('[aria-label="Title"]', 'Test Defect');
    await page.click('button:has-text("Save")'); // Should queue
    
    // Go online
    await page.context().setOffline(false);
    await page.waitForFunction(
      () => document.querySelector('[data-testid="sync-status"]')?.textContent === 'Synced'
    );
  });

  test('push notification received and navigates on click', async ({ page, context }) => {
    // Subscribe to push
    await page.goto('http://localhost:3000');
    await page.click('button:has-text("Enable Notifications")');
    
    // Simulate backend push
    const wsServer = new WebSocketServer({ port: 8081 });
    // ... send push event
    
    // Verify notification shown
    const notification = await context.waitForEvent('notification');
    expect(notification.title).toContain('Neurex');
  });
});
```

**Deliverable:** 8+ E2E tests (offline, sync, push), all green

### Acceptance Gate
- [ ] Service Worker cache strategies verified (DevTools → Application → Cache Storage)
- [ ] Install prompt appears on Chrome/Edge (not on iOS Safari)
- [ ] Offline page accessible at `/offline`
- [ ] Background sync tag registered (`navigator.serviceWorker.ready.sync`)
- [ ] Push notifications received (simulated via backend)
- [ ] All E2E tests passing
- [ ] Lighthouse PWA score ≥ 90

---

## Feature 2: Mobile Optimization — Implementation Roadmap

### Week 1: Responsive Design & Touch Targets

#### Day 1–2: Responsive Grid Audit
**Owner:** Dev 1  
**Tasks:**
- Audit current layout: CSS Grid, Flexbox usage
- Identify tablet breakpoints: 768px (iPad), 1024px (iPad Pro), 1440px (desktop)
- Create Tailwind config breakpoints:
  ```javascript
  // tailwind.config.js
  module.exports = {
    theme: {
      extend: {
        screens: {
          'sm': '320px',    // mobile
          'md': '640px',    // mobile landscape
          'lg': '768px',    // tablet
          'xl': '1024px',   // tablet landscape
          '2xl': '1440px',  // desktop
        },
      },
    },
  };
  ```
- Refactor components: use `md:grid-cols-2` for tablet+, `grid-cols-1` for mobile
- Test: Playwright viewport mocking (320px, 768px, 1024px, 1440px)

**Deliverable:** Responsive grid defined, 0 horizontal scroll on 320px

#### Day 3–4: Safe Area & Notch Handling
**Owner:** Dev 1  
**Tasks:**
```css
/* /app/globals.css - add safe area support */
html {
  --safe-top: env(safe-area-inset-top, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --safe-left: env(safe-area-inset-left, 0px);
  --safe-right: env(safe-area-inset-right, 0px);
}

body {
  padding-top: var(--safe-top);
  padding-bottom: var(--safe-bottom);
}

.sidebar { padding-left: var(--safe-left); }
.header { padding-top: calc(var(--safe-top) + 1rem); } /* 1rem extra for title */
```

Apply safe area insets to:
- Header/nav (top inset)
- Bottom sheets (bottom inset)
- Side drawers (left/right insets)

**Deliverable:** Notch/dynamic island detected, content not overlapped

#### Day 5: Touch Target Audit & Fix
**Owner:** Dev 1  
**Tasks:**
- Use axe DevTools to audit touch targets (min 44×44px)
- Update button component: ensure all buttons ≥ 44px height
- Update link styling: add padding if text-only link
- Test command: `npx axe-core test --rules 'touch-target-size'`

**Code Example:**
```typescript
// /components/Button.tsx (update)
export function Button({ children, size = 'md', ...props }) {
  const sizeMap = {
    sm: 'px-2 py-1.5', // 32px min height
    md: 'px-3 py-2.5', // 40px min height - increase to 44px
    lg: 'px-4 py-3',   // 48px min height
  };
  
  return (
    <button className={`${sizeMap[size]} min-h-[2.75rem]`} {...props}>
      {children}
    </button>
  );
}
```

**Deliverable:** All interactive elements ≥ 44×44px (verified via axe)

### Week 2: Touch Gestures & Bottom Sheet

#### Day 6–7: Touch Gesture Library
**Owner:** Dev 2  
**Tasks:**
```typescript
// /lib/use-touch-gestures.ts (NEW)
import { useRef } from 'react';

export function useSwipeGesture(onSwipeLeft: () => void, onSwipeRight: () => void) {
  const touchStart = useRef<number | null>(null);
  const touchEnd = useRef<number | null>(null);

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStart.current = e.targetTouches[0].clientX;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    touchEnd.current = e.changedTouches[0].clientX;
    handleSwipe();
  };

  const handleSwipe = () => {
    if (!touchStart.current || !touchEnd.current) return;
    const distance = touchStart.current - touchEnd.current;
    const isLeftSwipe = distance > 50;
    const isRightSwipe = distance < -50;

    if (isLeftSwipe) onSwipeLeft();
    if (isRightSwipe) onSwipeRight();
  };

  return { onTouchStart: handleTouchStart, onTouchEnd: handleTouchEnd };
}

export function useLongPress(onLongPress: () => void, delay = 500) {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleMouseDown = () => {
    timeoutRef.current = setTimeout(onLongPress, delay);
  };

  const handleMouseUp = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
  };

  return { onMouseDown: handleMouseDown, onMouseUp: handleMouseUp };
}

export function usePullToRefresh(onRefresh: () => void) {
  const [pulled, setPulled] = useState(false);
  const startY = useRef<number | null>(null);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current) return;

    const handleTouchStart = (e: TouchEvent) => {
      startY.current = e.touches[0].clientY;
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (!startY.current || container.current!.scrollTop !== 0) return;
      const diff = e.touches[0].clientY - startY.current;
      if (diff > 100) {
        setPulled(true);
      }
    };

    const handleTouchEnd = async () => {
      if (pulled) {
        setPulled(false);
        await onRefresh();
      }
      startY.current = null;
    };

    container.current.addEventListener('touchstart', handleTouchStart);
    container.current.addEventListener('touchmove', handleTouchMove);
    container.current.addEventListener('touchend', handleTouchEnd);

    return () => {
      container.current?.removeEventListener('touchstart', handleTouchStart);
      container.current?.removeEventListener('touchmove', handleTouchMove);
      container.current?.removeEventListener('touchend', handleTouchEnd);
    };
  }, [pulled, onRefresh]);

  return { container, pulled };
}
```

**Deliverable:** 3 gesture hooks (swipe, long-press, pull-to-refresh) with tests

#### Day 8–9: Bottom Sheet Component
**Owner:** Dev 2  
**Tasks:**
```typescript
// /components/BottomSheet.tsx (NEW)
import { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';

export function BottomSheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}) {
  const sheetRef = useRef<HTMLDivElement>(null);
  const [dragOffset, setDragOffset] = useState(0);
  const startY = useRef<number | null>(null);

  useEffect(() => {
    const handleDragStart = (e: TouchEvent) => {
      startY.current = e.touches[0].clientY;
    };

    const handleDragMove = (e: TouchEvent) => {
      if (!startY.current) return;
      const diff = e.touches[0].clientY - startY.current;
      if (diff > 0) setDragOffset(diff);
    };

    const handleDragEnd = () => {
      if (dragOffset > 100) {
        onClose();
      }
      setDragOffset(0);
      startY.current = null;
    };

    if (!open || !sheetRef.current) return;

    sheetRef.current.addEventListener('touchstart', handleDragStart);
    sheetRef.current.addEventListener('touchmove', handleDragMove);
    sheetRef.current.addEventListener('touchend', handleDragEnd);

    return () => {
      sheetRef.current?.removeEventListener('touchstart', handleDragStart);
      sheetRef.current?.removeEventListener('touchmove', handleDragMove);
      sheetRef.current?.removeEventListener('touchend', handleDragEnd);
    };
  }, [dragOffset, onClose, open]);

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
      <div
        ref={sheetRef}
        className="fixed bottom-0 left-0 right-0 max-h-[90vh] bg-white dark:bg-slate-900 rounded-t-2xl shadow-lg z-50 transform transition-transform"
        style={{ transform: `translateY(${dragOffset}px)` }}
      >
        {/* Handle bar */}
        <div className="h-1 w-12 bg-slate-300 rounded-full mx-auto mt-2" />

        {/* Header */}
        {title && (
          <div className="flex justify-between items-center p-4 border-b">
            <h2 className="text-lg font-semibold">{title}</h2>
            <button onClick={onClose} className="p-1">
              <X size={20} />
            </button>
          </div>
        )}

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-4rem)]">{children}</div>
      </div>
    </>
  );
}
```

**Deliverable:** Bottom sheet component with swipe-down dismiss

#### Day 10: Mobile Navigation Refactor
**Owner:** Dev 2  
**Tasks:**
- Create mobile nav component: hamburger → bottom sheet (mobile), side nav (tablet+)
- Use Tailwind conditional: `md:flex hidden` (desktop) vs `flex md:hidden` (mobile)
- Bottom sheet menu items with swipe up/down
- Persist menu state in localStorage

**Deliverable:** Mobile menu functional, no layout shift

### Week 3: Performance on 4G & Orientation

#### Day 11–12: 4G Performance Baseline
**Owner:** Dev 2 + QA  
**Tasks:**
- Establish Lighthouse baseline with 4G throttling:
  ```bash
  npx lighthouse https://localhost:3000 --throttle-method=devtools --emulate-mobile-device
  ```
- Current estimate: FCP ~3–4s, LCP ~4–5s (target: FCP < 2s, LCP < 3s)
- Identify bottlenecks: JS bundle, images, third-party scripts
- Implement route-based code splitting:
  ```typescript
  // /app/(dashboard)/test-runs/page.tsx
  const TestRunsChart = dynamic(() => import('./components/TestRunsChart'), {
    loading: () => <Skeleton className="h-64" />,
  });
  ```

**Deliverable:** 4G baseline established, code splitting in place

#### Day 13–15: Orientation & Responsive Testing
**Owner:** Dev 2 + QA  
**Tasks:**
- Detect orientation change:
  ```typescript
  useEffect(() => {
    const handleOrientationChange = () => {
      setOrientation(window.innerWidth < window.innerHeight ? 'portrait' : 'landscape');
    };
    window.addEventListener('orientationchange', handleOrientationChange);
    return () => window.removeEventListener('orientationchange', handleOrientationChange);
  }, []);
  ```
- Persist scroll position on rotate (use `sessionStorage`)
- Landscape mode: full-screen modals, minimized chrome
- Test on:
  - iPhone 12 (portrait + landscape)
  - iPad (portrait + landscape)
  - Android (portrait + landscape)
  - Foldable (folded + unfolded, if emulator available)

**Deliverable:** Orientation changes handled smoothly, Lighthouse mobile ≥ 90

### Acceptance Gate
- [ ] All touch targets ≥ 44×44px (axe verified)
- [ ] Tablet layout works (768px–1024px)
- [ ] Swipe gestures: left/right on case list, up/down on lists
- [ ] Long-press: context menu on rows
- [ ] Pull-to-refresh: visual spinner, lists refresh
- [ ] Bottom sheet: smooth open/close, swipe-down dismisses
- [ ] Mobile menu: hamburger → bottom sheet (mobile), side nav (tablet+)
- [ ] 4G: FCP < 2s, LCP < 3s
- [ ] Landscape rotation: layout reflows, scroll position preserved
- [ ] Lighthouse mobile ≥ 90

---

## Feature 3: Performance Tuning — Implementation Roadmap

### Week 1: Lighthouse Audit & Bundle Analysis

#### Day 1–2: Lighthouse Baseline
**Owner:** Dev 1 + QA  
**Tasks:**
```bash
# Run Lighthouse on main routes
npx lighthouse https://localhost:3000 --output=html --output-path=./lighthouse-reports/home.html
npx lighthouse https://localhost:3000/portfolio
npx lighthouse https://localhost:3000/ide
npx lighthouse https://localhost:3000/test-runs
# With 4G throttling
npx lighthouse https://localhost:3000 --throttle-method=devtools --emulate-mobile-device
```

Record baseline:
- Performance, Accessibility, Best Practices, SEO scores
- LCP, FID, CLS metrics
- Bundle size (main, vendor, app chunks)
- Identify red flags (unused JS, large images, render-blocking resources)

**Deliverable:** Baseline report (estimated: Performance 85–87, A11y 92–94)

#### Day 3–4: Bundle Analysis
**Owner:** Dev 1  
**Tasks:**
```javascript
// next.config.mjs (add)
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

export default withBundleAnalyzer(nextConfig);
```

Run analysis:
```bash
ANALYZE=true npm run build
# Opens browser with interactive bundle tree
```

Identify large packages:
- `recharts`: ~250KB (tree-shaking)
- `framer-motion`: ~60KB (check if all features used)
- Lucide icons: ~120KB (tree-shake unused icons)
- Radix UI: ~50KB (check imports)

**Deliverable:** Bundle analysis report, recommendations for tree-shaking

#### Day 5: Code Splitting Plan
**Owner:** Dev 1  
**Tasks:**
- Create code-split map:
  ```typescript
  // /lib/dynamic-imports.ts (NEW)
  export const TestRunsChart = dynamic(
    () => import('@/components/test-runs/TestRunsChart'),
    { loading: () => <Skeleton /> }
  );
  export const IDEEditor = dynamic(
    () => import('@/components/ide/Editor'),
    { loading: () => <Skeleton /> }
  );
  export const AgentFlow = dynamic(
    () => import('@/components/agents/Flow'),
    { loading: () => <Skeleton /> }
  );
  ```
- Identify routes to lazy-load: `/ide`, `/agents`, `/analytics`
- Create Skeleton components for each dynamic import
- Update routes to use dynamic imports

**Deliverable:** 10+ dynamic imports planned

### Week 2: Image & Font Optimization

#### Day 6–7: Image Optimization
**Owner:** Dev 2  
**Tasks:**
```typescript
// Audit: find all <img> tags, replace with <Image>
// Example before:
// <img src="/logo.png" alt="Logo" />

// Example after:
import Image from 'next/image';

export function Logo() {
  return (
    <Image
      src="/logo.png"
      alt="Logo"
      width={64}
      height={64}
      priority={true} // for LCP images
      sizes="(max-width: 640px) 48px, 64px"
    />
  );
}
```

- Convert all PNG/JPEG to WebP (use tinypng.com or squoosh)
- Set explicit width/height for all images
- Lazy-load below-fold images (`loading="lazy"`)
- Srcset for 1x/2x/3x density:
  ```typescript
  <Image
    src="/case-icon.webp"
    alt="Case"
    width={32}
    height={32}
    priority={false}
  />
  ```
- Audit: ensure all user-uploaded images optimized

**Deliverable:** 95%+ images using next/image, WebP enabled

#### Day 8–9: Font Optimization
**Owner:** Dev 2  
**Tasks:**
- Current fonts: Inter (400/500/600/700), JetBrains Mono (400/500/700)
- Evaluate variable fonts: can combine weights into 1 file
  ```typescript
  // /app/layout.tsx (update)
  const inter = Inter({
    subsets: ["latin", "latin-ext"],
    display: "swap",
    variable: "--font-sans",
    // Consider variable font:
    // weight: ["100", "200", "300", ..., "900"],
  });
  ```
- Remove unused font weights/subsets
- Preload critical fonts:
  ```html
  <link rel="preload" as="font" href="/fonts/inter-500.woff2" type="font/woff2" />
  ```

**Deliverable:** Font bundle optimized, preload tags added

#### Day 10: Core Web Vitals Monitoring
**Owner:** Dev 1  
**Tasks:**
```typescript
// /lib/web-vitals.ts (NEW)
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

export function setupWebVitalsReporting() {
  getCLS(metric => console.log('CLS:', metric.value));
  getFID(metric => console.log('FID:', metric.value));
  getFCP(metric => console.log('FCP:', metric.value));
  getLCP(metric => console.log('LCP:', metric.value));
  getTTFB(metric => console.log('TTFB:', metric.value));

  // Send to Sentry
  if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
    getCLS(metric => Sentry.captureMessage(`CLS: ${metric.value}`));
    // ... etc
  }
}

// Call in /app/layout.tsx
useEffect(() => {
  setupWebVitalsReporting();
}, []);
```

**Deliverable:** Web Vitals tracking integrated, Sentry reporting enabled

### Acceptance Gate
- [ ] Lighthouse Performance ≥ 90 (all pages)
- [ ] Bundle size ≤ 200KB gzip (main chunk)
- [ ] 95%+ images use next/image
- [ ] LCP < 2.5s (desktop), < 3s (4G)
- [ ] CLS < 0.1
- [ ] FID < 100ms
- [ ] Code splitting: 15+ dynamic imports
- [ ] Web Vitals integrated with Sentry

---

## Features 4 & 5: Advanced Features & Accessibility

*(Implementation roadmaps for Features 4 & 5 follow similar structure; abbreviated for brevity)*

### Feature 4: Advanced Features (Filters, Export, Widgets, Analytics)

**Week 1–2: Filters & Saved Views**
- Filter builder component (status, assignee, tags, date range)
- Backend API: `POST /api/v1/saved-filters`, `GET /api/v1/saved-filters`
- URL encoding for shareable filter links
- Tests: 20+ filter combinations

**Week 2–3: Export Features**
- CSV export: TanStack React Table integration
- Excel export: `xlsx` library (already in deps)
- PDF export: `pdfkit` or `react-pdf` for server-side rendering
- Tests: 50K+ row exports

**Week 3–4: Dashboard Widgets**
- 8+ widget types: case count, coverage %, test trends, defect trends
- Drag-and-drop layout (dnd-kit, already in deps)
- Persistence: backend API for widget state
- Real-time updates via WebSocket (optional)

**Week 4–5: Analytics Dashboard**
- KPI cards: test execution, coverage, defect velocity
- Trend lines (Recharts)
- Date range picker
- Export report (PDF)

### Feature 5: Accessibility (WCAG 2.1 AAA)

**Week 1–2: Audit & Color Contrast**
- Comprehensive audit: all 35+ pages
- Color contrast fixes: 7:1 ratio required
- Update design tokens for WCAG AAA compliance

**Week 2–3: ARIA Labels & Keyboard Navigation**
- 80+ ARIA label updates
- Tab order verification
- Focus trapping in modals/drawers
- Escape key handling

**Week 3–4: Screen Reader Testing & Automation**
- Manual testing: NVDA (Windows), VoiceOver (Mac)
- Automated axe tests in CI/CD
- Lighthouse accessibility ≥ 95

---

## Testing Strategy (All Features)

### Unit Tests (Jest)
- Utility functions (sync queue logic, gesture detection)
- Component rendering (PWA prompt, bottom sheet)
- Target: 85%+ coverage

### Integration Tests (Playwright)
- PWA offline navigation
- Mobile gesture handling
- Performance baseline
- Accessibility compliance

### E2E Tests (Playwright)
- Full user flows (offline → online → sync)
- Multi-device testing (mobile, tablet, desktop)
- Cross-browser (Chrome, Edge, Firefox, Safari)

### Performance Tests (Lighthouse CI)
- Automated Lighthouse runs on every PR
- Performance regression gate (±5% allowed)
- Bundle size tracking

### A11y Tests (@axe-core/playwright)
- Automated axe audit on all pages
- Manual screen reader testing (NVDA, VoiceOver)
- WCAG AAA compliance verification

---

## CI/CD Integration

### New GitHub Actions Workflows

```yaml
# .github/workflows/lighthouse.yml
name: Lighthouse CI
on: [pull_request]
jobs:
  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci && npm run build
      - uses: treosh/lighthouse-ci-action@v10
        with:
          configPath: './lighthouse.config.js'
          
# .github/workflows/a11y.yml
name: Accessibility Tests
on: [pull_request]
jobs:
  a11y:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npx playwright test --project=axe-tests
```

### Bundle Size Monitoring

```json
// .github/checks/bundle-size.json
{
  "maxSize": "200kb",
  "targets": {
    "main": "150kb",
    "vendor": "100kb"
  }
}
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-09  
**Next: Start Week 0 Planning Session**
