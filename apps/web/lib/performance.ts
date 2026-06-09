/**
 * Performance Monitoring & Web Vitals
 *
 * - LCP (Largest Contentful Paint)
 * - FID (First Input Delay) / INP (Interaction to Next Paint)
 * - CLS (Cumulative Layout Shift)
 * - FCP (First Contentful Paint)
 * - TTFB (Time to First Byte)
 */

export interface WebVitalsMetrics {
  name: string;
  value: number;
  delta?: number;
  id: string;
  entries: PerformanceEntry[];
  navigationType: string;
  rating: "good" | "needs-improvement" | "poor";
}

export interface MetricsCallback {
  (metric: WebVitalsMetrics): void;
}

// Thresholds for rating (milliseconds)
const THRESHOLDS = {
  LCP: { good: 2500, poor: 4000 },
  FID: { good: 100, poor: 300 },
  INP: { good: 200, poor: 500 },
  CLS: { good: 0.1, poor: 0.25 },
  FCP: { good: 1800, poor: 3000 },
  TTFB: { good: 600, poor: 1200 },
};

function getRating(metricName: string, value: number): "good" | "needs-improvement" | "poor" {
  const threshold = THRESHOLDS[metricName as keyof typeof THRESHOLDS];
  if (!threshold) return "needs-improvement";

  if (value <= threshold.good) return "good";
  if (value <= threshold.poor) return "needs-improvement";
  return "poor";
}

// ────────────────────────────────────────────────────────────
// Web Vitals Observation
// ────────────────────────────────────────────────────────────

/**
 * Observe Largest Contentful Paint (LCP)
 */
export function onLCP(callback: MetricsCallback): void {
  if (!("PerformanceObserver" in window)) return;

  try {
    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1];

      const metric: WebVitalsMetrics = {
        name: "LCP",
        value: lastEntry.renderTime || lastEntry.loadTime,
        id: `lcp-${Date.now()}`,
        entries,
        navigationType: (performance as any).navigation?.type || "navigate",
        rating: getRating("LCP", lastEntry.renderTime || lastEntry.loadTime),
      };

      callback(metric);
    });

    observer.observe({ type: "largest-contentful-paint", buffered: true });
  } catch (err) {
    console.error("LCP observation failed:", err);
  }
}

/**
 * Observe First Input Delay (FID) / Interaction to Next Paint (INP)
 */
export function onINP(callback: MetricsCallback): void {
  if (!("PerformanceObserver" in window)) return;

  try {
    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();

      for (const entry of entries) {
        const processingDuration = (entry as any).processingDuration || 0;
        const presentationDelay = entry.startTime + (entry as any).duration - entry.startTime;
        const value = Math.max(processingDuration, presentationDelay);

        const metric: WebVitalsMetrics = {
          name: "INP",
          value,
          id: `inp-${entry.startTime}`,
          entries: [entry],
          navigationType: (performance as any).navigation?.type || "navigate",
          rating: getRating("INP", value),
        };

        callback(metric);
      }
    });

    observer.observe({ type: "event", buffered: true, durationThreshold: 40 });
  } catch (err) {
    console.error("INP observation failed:", err);
  }
}

/**
 * Observe Cumulative Layout Shift (CLS)
 */
export function onCLS(callback: MetricsCallback): void {
  if (!("PerformanceObserver" in window)) return;

  let clsValue = 0;
  let clsEntries: PerformanceEntry[] = [];

  try {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!(entry as any).hadRecentInput) {
          clsValue += (entry as any).value;
          clsEntries.push(entry);
        }
      }

      const metric: WebVitalsMetrics = {
        name: "CLS",
        value: clsValue,
        id: `cls-${Date.now()}`,
        entries: clsEntries,
        navigationType: (performance as any).navigation?.type || "navigate",
        rating: getRating("CLS", clsValue),
      };

      callback(metric);
    });

    observer.observe({ type: "layout-shift", buffered: true });
  } catch (err) {
    console.error("CLS observation failed:", err);
  }
}

/**
 * Observe First Contentful Paint (FCP)
 */
export function onFCP(callback: MetricsCallback): void {
  if (!("PerformanceObserver" in window)) return;

  try {
    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1];

      const metric: WebVitalsMetrics = {
        name: "FCP",
        value: lastEntry.startTime,
        id: `fcp-${Date.now()}`,
        entries,
        navigationType: (performance as any).navigation?.type || "navigate",
        rating: getRating("FCP", lastEntry.startTime),
      };

      callback(metric);
    });

    observer.observe({ type: "paint", buffered: true });
  } catch (err) {
    console.error("FCP observation failed:", err);
  }
}

/**
 * Get Time to First Byte (TTFB)
 */
export function getTTFB(): number | null {
  if (!performance || !performance.timing) {
    return null;
  }

  const { navigationStart, responseStart } = performance.timing;
  if (!navigationStart || !responseStart) {
    return null;
  }

  return responseStart - navigationStart;
}

/**
 * Observe TTFB
 */
export function onTTFB(callback: MetricsCallback): void {
  if (!performance || !performance.timing) return;

  const ttfb = getTTFB();
  if (ttfb !== null) {
    const metric: WebVitalsMetrics = {
      name: "TTFB",
      value: ttfb,
      id: `ttfb-${Date.now()}`,
      entries: [],
      navigationType: (performance as any).navigation?.type || "navigate",
      rating: getRating("TTFB", ttfb),
    };

    callback(metric);
  }
}

// ────────────────────────────────────────────────────────────
// Consolidated Web Vitals
// ────────────────────────────────────────────────────────────

/**
 * Observe all Web Vitals with single callback
 */
export function observeWebVitals(callback: MetricsCallback): () => void {
  const unsubscribers: (() => void)[] = [];

  // Observe key metrics
  onTTFB(callback);
  onFCP(callback);
  onLCP(callback);
  onINP(callback);
  onCLS(callback);

  return () => {
    // No direct unsubscribe available for PerformanceObserver
    // in most browsers, but this structure allows for cleanup
    unsubscribers.forEach((fn) => fn());
  };
}

// ────────────────────────────────────────────────────────────
// Resource Timing Analysis
// ────────────────────────────────────────────────────────────

export interface ResourceMetrics {
  name: string;
  type: string;
  duration: number;
  size: number | null;
  cached: boolean;
  priority: "high" | "low" | "medium";
}

/**
 * Get all resource timings
 */
export function getResourceMetrics(): ResourceMetrics[] {
  if (!performance || !performance.getEntriesByType) {
    return [];
  }

  const resources = performance.getEntriesByType("resource") as PerformanceResourceTiming[];

  return resources.map((resource) => ({
    name: resource.name,
    type: resource.initiatorType,
    duration: Math.round(resource.duration),
    size: resource.transferSize || null,
    cached: resource.transferSize === 0 && resource.encodedBodySize > 0,
    priority: getPriorityByType(resource.initiatorType),
  }));
}

function getPriorityByType(
  initiatorType: string
): "high" | "low" | "medium" {
  switch (initiatorType) {
    case "script":
    case "link":
      return "high";
    case "img":
    case "media":
    case "iframe":
      return "low";
    default:
      return "medium";
  }
}

// ────────────────────────────────────────────────────────────
// Long Tasks Detection
// ────────────────────────────────────────────────────────────

/**
 * Observe Long Tasks (> 50ms)
 */
export function observeLongTasks(
  callback: (duration: number, name: string) => void
): void {
  if (!("PerformanceObserver" in window)) return;

  try {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        callback((entry as any).duration, entry.name);
      }
    });

    observer.observe({ type: "longtask", buffered: true });
  } catch (err) {
    console.error("Long tasks observation failed:", err);
  }
}

// ────────────────────────────────────────────────────────────
// Custom Metrics
// ────────────────────────────────────────────────────────────

/**
 * Mark performance checkpoint
 */
export function mark(name: string): void {
  if (performance && performance.mark) {
    performance.mark(name);
  }
}

/**
 * Measure time between two marks
 */
export function measure(name: string, startMark: string, endMark: string): number {
  if (!performance || !performance.measure) {
    return 0;
  }

  try {
    const measure = performance.measure(name, startMark, endMark);
    return measure.duration;
  } catch {
    return 0;
  }
}

/**
 * Report custom metric
 */
export function reportMetric(name: string, value: number, labels?: Record<string, string>): void {
  // Could be extended to send metrics to analytics service
  if (window.gtag) {
    (window as any).gtag?.event("page_view", {
      metric_name: name,
      metric_value: value,
      ...labels,
    });
  }
}

// ────────────────────────────────────────────────────────────
// Bundle Size Analysis
// ────────────────────────────────────────────────────────────

/**
 * Analyze script sizes
 */
export function analyzeScriptSizes(): Array<{
  url: string;
  size: number;
  compressed: boolean;
}> {
  if (!performance || !performance.getEntriesByType) {
    return [];
  }

  const scripts = performance.getEntriesByType("resource") as PerformanceResourceTiming[];

  return scripts
    .filter((r) => r.initiatorType === "script")
    .map((r) => ({
      url: r.name,
      size: r.transferSize || r.decodedBodySize || 0,
      compressed: (r.transferSize || 0) < (r.decodedBodySize || 0),
    }))
    .sort((a, b) => b.size - a.size);
}

// ────────────────────────────────────────────────────────────
// Memory Usage (Chrome only)
// ────────────────────────────────────────────────────────────

export interface MemoryMetrics {
  jsHeapSizeLimit: number;
  totalJSHeapSize: number;
  usedJSHeapSize: number;
  percentUsed: number;
}

/**
 * Get memory metrics (Chrome only)
 */
export function getMemoryMetrics(): MemoryMetrics | null {
  if (!(performance as any).memory) {
    return null;
  }

  const { jsHeapSizeLimit, totalJSHeapSize, usedJSHeapSize } = (performance as any).memory;

  return {
    jsHeapSizeLimit,
    totalJSHeapSize,
    usedJSHeapSize,
    percentUsed: (usedJSHeapSize / jsHeapSizeLimit) * 100,
  };
}
