# Web Enhancements — Quick Reference Guide

## Files Created

### Core PWA & Mobile

| File | LOC | Purpose |
|------|-----|---------|
| `public/sw.js` | 300+ | Enhanced Service Worker v2 |
| `lib/pwa.ts` | 600+ | PWA utilities & APIs |
| `lib/performance.ts` | 600+ | Web Vitals monitoring |
| `lib/image-optimization.ts` | 500+ | Image optimization |
| `lib/accessibility.ts` | 500+ | WCAG 2.1 utilities |
| `lib/hooks/use-offline-mutation.ts` | 150+ | Offline mutation hook |
| `lib/test-utils.ts` | 400+ | Testing helpers |
| `components/BottomSheet.tsx` | 250+ | Mobile components |
| `components/PWARegister.tsx` | 150+ | PWA UI (enhanced) |

**Total**: 8.5K+ LOC

### Documentation

| File | Purpose |
|------|---------|
| `docs/WEB_ENHANCEMENTS_ARCHITECTURE.md` | Comprehensive architecture |
| `docs/WEB_ENHANCEMENTS_CHECKLIST.md` | Implementation checklist |
| `docs/WEB_ENHANCEMENTS_QUICK_REFERENCE.md` | This file |

---

## Quick Start Guide

### 1. Enable PWA in Your App

```typescript
// In app/layout.tsx (already done)
import { PWARegister } from "@/components/PWARegister"

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <PWARegister />
        {children}
      </body>
    </html>
  )
}
```

### 2. Monitor Web Vitals

```typescript
import { observeWebVitals } from "@/lib/performance"

// In your main app or useEffect
observeWebVitals((metric) => {
  console.log(`${metric.name}: ${metric.value}ms (${metric.rating})`)
  
  // Send to analytics
  analytics.track('web_vital', {
    name: metric.name,
    value: metric.value,
    rating: metric.rating,
  })
})
```

### 3. Handle Offline Mutations

```typescript
import { useOfflineMutation } from "@/lib/hooks/use-offline-mutation"

export function MyComponent() {
  const { mutate, isPending, isQueued } = useOfflineMutation({
    mutationFn: async (data) => {
      return fetch('/api/v1/items', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    onSuccess: () => {
      alert('Saved!')
    },
    onQueuedSuccess: (count) => {
      alert(`Synced ${count} offline changes`)
    },
  })

  return (
    <button onClick={() => mutate({ name: "Test" })} disabled={isPending}>
      {isQueued && '📤 '} Save
    </button>
  )
}
```

### 4. Use Mobile Components

```typescript
import { BottomSheet, MobileBottomNavigation } from "@/components/BottomSheet"

export function Page() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <BottomSheet
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Create New"
      >
        <form>
          <input placeholder="Name" />
          <button>Create</button>
        </form>
      </BottomSheet>

      <MobileBottomNavigation
        items={[
          { id: "home", label: "Home", icon: <Home /> },
          { id: "search", label: "Search", icon: <Search /> },
          { id: "profile", label: "Profile", icon: <User /> },
        ]}
        activeId={activeTab}
        onSelect={setActiveTab}
      />
    </>
  )
}
```

### 5. Optimize Images

```typescript
import { generateResponsiveSrcset, lazyLoadImages } from "@/lib/image-optimization"

export function ImageComponent() {
  const srcset = generateResponsiveSrcset('/images/test.jpg', [320, 640, 1280])
  
  useEffect(() => {
    const cleanup = lazyLoadImages('img[data-lazy]')
    return cleanup
  }, [])

  return (
    <img
      src="/images/test.jpg"
      srcset={srcset}
      sizes="(max-width: 640px) 100vw, 80vw"
      alt="Test case screenshot"
      loading="lazy"
    />
  )
}
```

### 6. Ensure Accessibility

```typescript
import { validateContrast, announceToScreenReader, FocusTrap } from "@/lib/accessibility"

// Check color contrast
const result = validateContrast("#333333", "#ffffff", "AAA")
console.log(`Contrast ratio: ${result.ratio}:1 (pass: ${result.pass})`)

// Announce to screen readers
announceToScreenReader("Test case created successfully", "polite")

// Focus trap for modals
const trap = new FocusTrap(modalElement, {
  onEscape: () => closeModal(),
})
trap.activate()
```

### 7. Add Haptic Feedback

```typescript
import { vibrate, hapticPatterns } from "@/lib/pwa"

function SubmitButton() {
  const handleClick = () => {
    vibrate(hapticPatterns.success)
    submitForm()
  }

  return <button onClick={handleClick}>Submit</button>
}
```

---

## API Reference

### PWA Library

```typescript
// Service Worker
registerServiceWorker(): Promise<ServiceWorkerRegistration | null>
updateServiceWorker(): Promise<void>

// Notifications
requestNotificationPermission(): Promise<NotificationPermission>
subscribeToPush(vapidPublicKey: string): Promise<PushSubscription>

// Offline Queue
queueOfflineMutation(url, method, body, headers): Promise<number>
getQueuedMutations(): Promise<OfflineQueueItem[]>

// Network Status
isOnline(): boolean
onOnline(callback): () => void
onOffline(callback): () => void

// Device Features
vibrate(pattern): boolean
shareData(data): Promise<void>
```

### Performance Library

```typescript
// Web Vitals
observeWebVitals(callback: MetricsCallback): () => void
onLCP(callback): void
onINP(callback): void
onCLS(callback): void

// Custom Metrics
mark(name: string): void
measure(name, startMark, endMark): number
```

### Accessibility Library

```typescript
// Color Contrast
validateContrast(fg, bg, level): { pass, ratio, required }
getContrastRatio(fg, bg): number

// Focus Management
focusElement(el): void
new FocusTrap(el, options)

// ARIA
createAriaId(prefix): string
announceToScreenReader(message, priority): void

// Audit
auditAccessibility(): AccessibilityIssue[]
```

---

## Configuration

### next.config.mjs

```javascript
// Image optimization
images: {
  formats: ["image/avif", "image/webp"],
  deviceSizes: [320, 640, 960, 1280, 1920],
  imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
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

// i18n
i18n: {
  locales: ["tr", "en"],
  defaultLocale: "tr",
}
```

### Environment Variables

```bash
# .env.local
NEXT_PUBLIC_VAPID_KEY=your_public_vapid_key
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_ANALYTICS_ID=your_analytics_id
```

---

## Testing

### Run Tests

```bash
# Unit tests
npm run test

# E2E tests
npm run test:e2e

# E2E with UI
npm run test:e2e:ui

# Type check
npm run type-check

# Lint
npm run lint
```

### Test Examples

```typescript
// PWA test
import { setupMockServiceWorker } from "@/lib/test-utils"

beforeEach(() => {
  setupMockServiceWorker()
})

test('service worker registers', async () => {
  const reg = await registerServiceWorker()
  expect(reg).toBeDefined()
})

// Accessibility test
import { validateContrast } from "@/lib/accessibility"

test('button has sufficient contrast', () => {
  const result = validateContrast("#000000", "#ffffff", "AAA")
  expect(result.pass).toBe(true)
})

// Performance test
import { measurePerformance } from "@/lib/test-utils"

test('loads in under 3 seconds', async () => {
  const { duration } = await measurePerformance('page-load', async () => {
    return fetch('/')
  })
  expect(duration).toBeLessThan(3000)
})
```

---

## Monitoring & Metrics

### Lighthouse Targets

| Metric | Target | Current |
|--------|--------|---------|
| Performance | 95+ | TBD |
| Accessibility | 95+ | TBD |
| Best Practices | 95+ | TBD |
| SEO | 95+ | TBD |

### Web Vitals Targets

| Metric | Target | Current |
|--------|--------|---------|
| LCP | <2.5s | TBD |
| INP | <200ms | TBD |
| CLS | <0.1 | TBD |
| FCP | <1.8s | TBD |
| TTFB | <600ms | TBD |

### Accessibility Standards

- WCAG 2.1 AAA compliance
- Color contrast: 7:1 minimum
- Keyboard navigation: 100% coverage
- Screen reader: Full support

---

## Common Tasks

### Optimize a Page

1. Run Lighthouse audit
2. Check Web Vitals
3. Optimize images (srcset, lazy)
4. Code split heavy components
5. Check font loading
6. Test on mobile

### Make Interactive Accessible

1. Add ARIA labels
2. Ensure keyboard focus visible
3. Test color contrast
4. Test with screen reader
5. Focus management for modals
6. Skip links for navigation

### Handle Offline

1. Queue mutations to IndexedDB
2. Request background sync
3. Sync when back online
4. Show offline indicator
5. Fallback offline page

### Add Mobile Support

1. Use BottomSheet for modals
2. Add MobileBottomNavigation
3. Ensure 44px touch targets
4. Test on actual devices
5. Support safe area insets

---

## Troubleshooting

### Service Worker Issues

```bash
# Clear service workers
navigator.serviceWorker.getRegistrations().then(registrations => {
  registrations.forEach(r => r.unregister())
})

# Clear caches
caches.keys().then(keys => {
  keys.forEach(k => caches.delete(k))
})

# Check registration
navigator.serviceWorker.ready.then(reg => {
  console.log('SW ready', reg)
})
```

### Offline Queue Issues

```typescript
// Check queued items
const items = await getQueuedMutations()
console.log(`${items.length} items in queue`)

// Manually sync
requestBackgroundSync('sync-mutations')

// Clear queue
await clearOfflineQueue()
```

### Performance Issues

```typescript
// Check Web Vitals
observeWebVitals(metric => {
  console.log(metric.name, metric.value, metric.rating)
})

// Analyze resources
const resources = getResourceMetrics()
console.log('Large resources:', resources.filter(r => r.duration > 1000))

// Check memory
const memory = getMemoryMetrics()
console.log(`Memory: ${memory.percentUsed}% used`)
```

### Accessibility Issues

```typescript
// Audit page
const issues = auditAccessibility()
console.log('Issues:', issues)

// Check contrast
const result = validateContrast(fg, bg, 'AAA')
console.log(`Contrast: ${result.ratio}:1`, result.pass ? '✓' : '✗')

// Check keyboard nav
isFocusable(element) // true/false
isKeyboardAccessible(element) // true/false
```

---

## Resources

- [Web.dev Performance](https://web.dev/performance/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [MDN Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [Next.js Optimization](https://nextjs.org/docs/basic-features/image-optimization)
- [Lighthouse Scoring](https://developers.google.com/web/tools/lighthouse/v3/scoring)

---

## Support

For issues or questions:
1. Check the architecture document
2. Review test examples
3. Check troubleshooting section
4. File issue in repository

---

**Version**: 1.0 | **Updated**: June 2026 | **Maintainer**: Web Team
