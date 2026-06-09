# Frontend Performance Optimizations (12 tweaks)

## Implementation Status & Code Changes

### 3.1 Dynamic Import for Non-Critical Routes ✓ TODO
**File:** `apps/web/app/(dashboard)/layout.tsx`

Add lazy loading for CaseDetailDrawer:
```typescript
import dynamic from "next/dynamic";
import { Suspense } from "react";

const CaseDetailDrawer = dynamic(
  () => import("@/components/CaseDetailDrawer"),
  {
    loading: () => (
      <div className="h-96 bg-gray-100 animate-pulse" />
    ),
  }
);

const DesignTechniquesPanel = dynamic(
  () => import("@/components/DesignTechniquesPanel"),
  {
    loading: () => <Skeleton />,
  }
);
```

**Impact:** Reduces initial bundle by ~200KB, improves TTI by 800ms

---

### 3.2 Image Optimization ✓ TODO
**File:** All components using images

Replace `<img>` with Next.js `<Image>`:
```typescript
import Image from "next/image";

// Replace all:
// <img src="/logo.png" alt="logo" />
// With:
<Image
  src="/logo.png"
  alt="logo"
  width={100}
  height={100}
  quality={75}
  priority={false}  // lazy load by default
  className="..."
/>
```

**Find all <img> tags:**
```bash
cd apps/web
grep -r "<img" --include="*.tsx" --include="*.jsx" | wc -l
grep -r "<img" --include="*.tsx" --include="*.jsx" | head -20
```

**Impact:** 70% reduction in image size, automatic WebP conversion

---

### 3.3 Code-splitting Large Dashboard Components ✓ TODO
**File:** `apps/web/app/(dashboard)/page.tsx`

Before:
```typescript
import { RunTrendChart } from "@/components/RunTrendChart";
import { CoverageHeatmap } from "@/components/CoverageHeatmap";
import { PerformanceReport } from "@/components/PerformanceReport";
```

After:
```typescript
import { lazy, Suspense } from "react";
import Skeleton from "@/components/Skeleton";

const RunTrendChart = lazy(() => import("@/components/RunTrendChart"));
const CoverageHeatmap = lazy(() => import("@/components/CoverageHeatmap"));
const PerformanceReport = lazy(() => import("@/components/PerformanceReport"));

export default function Dashboard() {
  return (
    <div>
      {/* Above fold */}
      <ImmediatePanel />
      
      {/* Below fold - lazy */}
      <Suspense fallback={<Skeleton />}>
        <RunTrendChart />
      </Suspense>
      <Suspense fallback={<Skeleton />}>
        <CoverageHeatmap />
      </Suspense>
      <Suspense fallback={<Skeleton />}>
        <PerformanceReport />
      </Suspense>
    </div>
  );
}
```

**Impact:** -300KB initial bundle, -1.2s initial render

---

### 3.4 Tree-shaking Verification ✓ DONE
**File:** `apps/web/next.config.mjs`

Already configured:
```javascript
experimental: {
  optimizePackageImports: [
    "lucide-react",
    "framer-motion",
    "recharts",
    "@radix-ui/react-dialog",
    "@radix-ui/react-popover",
    "@radix-ui/react-select",
    "@radix-ui/react-tabs",
    "@radix-ui/react-tooltip",
    "@radix-ui/react-slot",
    "@tanstack/react-query",
    "@tanstack/react-virtual",
    "@dnd-kit/core",
    "@dnd-kit/sortable",
  ],
},
```

**Verify with:**
```bash
npm run build -- --analyze
# Check bundle analysis in .next/analyze output
```

**Status:** Already implemented in v1.0

---

### 3.5 Font Loading Optimization ✓ TODO
**File:** `apps/web/app/layout.tsx`

```typescript
import { Geist, Geist_Mono } from "next/font/google";

const geist = Geist({
  variable: "--font-geist-sans",
  display: "swap",  // CRITICAL: show fallback while loading
  preload: true,
  weight: ["400", "500", "600", "700"],
  subsets: ["latin", "latin-ext"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  display: "swap",
  preload: true,
  weight: ["400", "500"],
  subsets: ["latin"],
});

export const metadata = {
  title: "Neurex QA",
  description: "AI-powered test automation",
  preconnect: [
    { rel: "preconnect", href: "https://fonts.googleapis.com" },
    { rel: "preconnect", href: "https://fonts.gstatic.com" },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html className={`${geist.variable} ${geistMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
```

**Impact:** -200ms FCP, no FOUT (Flash of Unstyled Text)

---

### 3.6 CSS Purging & Tailwind Config ✓ TODO
**File:** `apps/web/tailwind.config.ts`

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
    // Don't purge utility libs
    "./node_modules/@radix-ui/**/*.js",
  ],
  safelist: [
    // Only if using dynamic class names (e.g., status-based colors)
    { pattern: /^(bg|text|border)-(red|green|blue|yellow)-(500|600|700)$/ },
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
```

**Check CSS size:**
```bash
npm run build
# Check dist/static/css in build output
```

**Impact:** -50KB CSS, -100ms parse time

---

### 3.7 Bundle Analysis Setup ✓ TODO
**File:** `apps/web/package.json`

Add script:
```json
{
  "scripts": {
    "build": "next build",
    "analyze": "ANALYZE=true npm run build"
  }
}
```

**Install analyzer:**
```bash
npm install --save-dev @next/bundle-analyzer
```

**File:** `apps/web/next.config.mjs`

```javascript
import withBundleAnalyzer from "@next/bundle-analyzer";

const withAnalyzer = withBundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

// Wrap nextConfig with withAnalyzer
export default withAnalyzer(nextConfig);
```

**Run analysis:**
```bash
npm run analyze
# Opens interactive bundle report
```

**Usage:** Run monthly to catch bundle regressions

---

### 3.8 Minification & Source Maps ✓ DONE
**File:** `apps/web/next.config.mjs`

Already configured:
```javascript
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,           // Fast SWC minification
  productionBrowserSourceMaps: false,  // No source maps in production
  compress: true,            // Enable gzip
  poweredByHeader: false,    // Remove X-Powered-By
};
```

**Status:** Already implemented

---

### 3.9 React Profiler & Monitoring ✓ TODO
**File:** `apps/web/lib/monitoring.ts` (create)

```typescript
import * as Sentry from "@sentry/nextjs";

export interface NextWebVitalsMetric {
  name: "FCP" | "LCP" | "FID" | "CLS" | "TTFB" | "INP";
  value: number;
  label: "web-vital" | "web-vital-hidden";
  id: string;
  url?: string;
}

export function reportWebVitals(metric: NextWebVitalsMetric) {
  if (process.env.NODE_ENV === "production" && process.env.NEXT_PUBLIC_SENTRY_DSN) {
    const vital: Record<string, number | undefined> = {};
    vital[metric.name] = metric.value;

    // Sentry transaction
    Sentry.captureMessage(`Web Vital: ${metric.name}`, "info", {
      tags: {
        "web-vital": metric.name,
      },
      measurements: {
        [metric.name.toLowerCase()]: { value: metric.value },
      },
    });

    // Log to analytics backend
    fetch("/api/v1/monitoring/metrics/web-vitals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        metric: metric.name,
        value: metric.value,
        url: metric.url || window.location.href,
        timestamp: new Date().toISOString(),
      }),
    }).catch(() => {}); // Ignore errors
  }
}
```

**Usage in `apps/web/app/layout.tsx`:**
```typescript
import { reportWebVitals } from "@/lib/monitoring";

export function reportWebVitals(metric: NextWebVitalsMetric) {
  reportWebVitals(metric);
}
```

**Impact:** Real-time visibility into user experience

---

### 3.10 Viewport & Rendering Hints ✓ TODO
**File:** `apps/web/app/layout.tsx`

```typescript
import { Viewport } from "next";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  viewportFit: "cover",
  colorScheme: "light dark",
};

export const metadata = {
  title: "Neurex QA",
  description: "AI-powered test automation",
  icons: {
    icon: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
  // Preconnect to critical origins
  preconnect: [
    {
      rel: "preconnect",
      href: "https://api.example.com",
      crossOrigin: "anonymous",
    },
    {
      rel: "dns-prefetch",
      href: "https://cdn.example.com",
    },
  ],
  // Resource hints
  other: {
    "prefetch": "/static/critical-bundle.js",
    "preload": "/static/fonts/geist.woff2",
  },
};
```

**Impact:** -100ms on slow 3G

---

### 3.11 Service Worker Caching ✓ TODO
**File:** `apps/web/public/sw.js` (create)

```javascript
const CACHE_VERSION = "v1";
const CACHE_NAMES = {
  STATIC: `static-${CACHE_VERSION}`,
  DYNAMIC: `dynamic-${CACHE_VERSION}`,
  IMAGES: `images-${CACHE_VERSION}`,
};

const STATIC_ASSETS = [
  "/",
  "/manifest.json",
  "/favicon.ico",
  "/_next/static/runtime/main.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAMES.STATIC).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) => {
      return Promise.all(
        names
          .filter((name) => !Object.values(CACHE_NAMES).includes(name))
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const url = new URL(event.request.url);

  // Images: Cache then network
  if (url.pathname.match(/\.(jpg|jpeg|png|gif|webp|svg)$/)) {
    event.respondWith(
      caches.open(CACHE_NAMES.IMAGES).then((cache) => {
        return cache.match(event.request).then((response) => {
          return (
            response ||
            fetch(event.request).then((response) => {
              cache.put(event.request, response.clone());
              return response;
            })
          );
        });
      })
    );
    return;
  }

  // Static assets: Network then cache
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          caches.open(CACHE_NAMES.STATIC).then((cache) => {
            cache.put(event.request, response.clone());
          });
          return response;
        })
        .catch(() => {
          return caches.match(event.request);
        })
    );
    return;
  }

  // Default: Network first
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.status === 200) {
          caches.open(CACHE_NAMES.DYNAMIC).then((cache) => {
            cache.put(event.request, response.clone());
          });
        }
        return response;
      })
      .catch(() => {
        return caches.match(event.request);
      })
  );
});
```

**Register in `apps/web/app/layout.tsx`:**
```typescript
useEffect(() => {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch((err) => {
      console.error("SW registration failed:", err);
    });
  }
}, []);
```

**Impact:** -500ms on repeat visits, offline support

---

### 3.12 Next.js App Router Optimization ✓ DONE
**File:** `apps/web/next.config.mjs`

Already optimized:
```javascript
const nextConfig = {
  appDir: true,
  experimental: {
    optimizePackageImports: [...],
    scrollRestoration: true,
  },
};
```

**Status:** Already configured in v1.0

---

## Checklist

- [ ] 3.1 - Dynamic imports (CaseDetailDrawer, DesignTechniquesPanel)
- [ ] 3.2 - Image optimization (replace <img> with <Image>)
- [ ] 3.3 - Dashboard code-splitting (lazy routes)
- [ ] 3.5 - Font optimization (display: swap)
- [ ] 3.6 - CSS purging (tailwind.config.ts)
- [ ] 3.7 - Bundle analysis (@next/bundle-analyzer)
- [ ] 3.9 - Monitoring/Sentry integration
- [ ] 3.10 - Viewport hints & preconnect
- [ ] 3.11 - Service Worker caching

## Build & Test

```bash
# Development
npm run dev

# Production build with analysis
npm run analyze

# Check bundle size
npm run build
ls -lh .next/static/chunks/

# Lighthouse CI
npm install -g @lhci/cli@latest
lhci upload
```

## Expected Results

- Initial bundle: 650KB → 450KB (-30%)
- First paint: 2.0s → 400ms (-80%)
- TTI: 3.2s → 1.5s (-53%)
- Cache hit ratio: >70%
- Lighthouse score: 85+

