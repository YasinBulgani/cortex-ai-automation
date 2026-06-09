/**
 * Testing Utilities — PWA, Accessibility, Performance
 */

// ────────────────────────────────────────────────────────────
// Mock Service Worker Setup (for testing SW)
// ────────────────────────────────────────────────────────────

export interface MockSWConfig {
  version?: string;
  caches?: Record<string, string[]>;
}

/**
 * Setup mock service worker for testing
 */
export function setupMockServiceWorker(config: MockSWConfig = {}): void {
  if (typeof window === "undefined") return;

  const { version = "neurex-v1", caches: cachesConfig = {} } = config;

  // Mock navigator.serviceWorker
  const mockRegistration = {
    scope: "/",
    active: { postMessage: jest.fn() },
    installing: null,
    waiting: null,
    updateViaCache: "imports",
    unregister: jest.fn().mockResolvedValue(true),
    update: jest.fn().mockResolvedValue(undefined),
    pushManager: {
      subscribe: jest.fn(),
      getSubscription: jest.fn(),
      permissionState: jest.fn(),
    },
    sync: {
      register: jest.fn().mockResolvedValue(undefined),
      getTags: jest.fn().mockResolvedValue([]),
    },
  };

  Object.defineProperty(navigator, "serviceWorker", {
    value: {
      ready: Promise.resolve(mockRegistration),
      controller: null,
      oncontrollerchange: null,
      register: jest.fn().mockResolvedValue(mockRegistration),
      getRegistrations: jest.fn().mockResolvedValue([mockRegistration]),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    },
    configurable: true,
  });

  // Mock caches API
  Object.defineProperty(window, "caches", {
    value: {
      open: jest.fn().mockResolvedValue({
        add: jest.fn().mockResolvedValue(undefined),
        addAll: jest.fn().mockResolvedValue(undefined),
        put: jest.fn().mockResolvedValue(undefined),
        delete: jest.fn().mockResolvedValue(true),
        match: jest.fn().mockResolvedValue(undefined),
        matchAll: jest.fn().mockResolvedValue([]),
        keys: jest.fn().mockResolvedValue([]),
      }),
      delete: jest.fn().mockResolvedValue(true),
      has: jest.fn().mockResolvedValue(false),
      keys: jest.fn().mockResolvedValue(Object.keys(cachesConfig)),
      match: jest.fn().mockResolvedValue(undefined),
    },
    configurable: true,
  });

  // Mock IndexedDB
  const mockDB = {
    transaction: jest.fn().mockReturnValue({
      objectStore: jest.fn().mockReturnValue({
        get: jest.fn(),
        getAll: jest.fn().mockReturnValue({ result: [] }),
        add: jest.fn(),
        put: jest.fn(),
        delete: jest.fn(),
        clear: jest.fn(),
        createIndex: jest.fn(),
      }),
    }),
    objectStoreNames: {
      contains: jest.fn().mockReturnValue(true),
    },
    createObjectStore: jest.fn(),
  };

  Object.defineProperty(window, "indexedDB", {
    value: {
      open: jest.fn().mockReturnValue({
        onsuccess: function () {
          this.result = mockDB;
          if (typeof this.onsuccess === "function") {
            this.onsuccess();
          }
        },
        onerror: null,
        onupgradeneeded: null,
        result: mockDB,
      }),
      deleteDatabase: jest.fn(),
    },
    configurable: true,
  });
}

// ────────────────────────────────────────────────────────────
// Accessibility Testing Helpers
// ────────────────────────────────────────────────────────────

/**
 * Check if element has accessible name
 */
export function hasAccessibleName(element: Element): boolean {
  const ariaLabel = element.getAttribute("aria-label");
  const ariaLabelledBy = element.getAttribute("aria-labelledby");

  if (ariaLabel || ariaLabelledBy) return true;

  // Check for alt text (images)
  if (element.tagName === "IMG") {
    return !!element.getAttribute("alt");
  }

  // Check for text content
  if (element.textContent?.trim()) return true;

  // Check for label (form fields)
  if (
    element.tagName === "INPUT" ||
    element.tagName === "TEXTAREA" ||
    element.tagName === "SELECT"
  ) {
    const id = element.id;
    if (id && document.querySelector(`label[for="${id}"]`)) return true;
  }

  return false;
}

/**
 * Check if element is keyboard accessible
 */
export function isKeyboardAccessible(element: Element): boolean {
  if (element.tagName === "BUTTON") return true;
  if (element.tagName === "A" && element.hasAttribute("href")) return true;
  if (element.hasAttribute("tabindex")) {
    const tabindex = parseInt(element.getAttribute("tabindex") || "0");
    return tabindex >= 0;
  }

  return false;
}

/**
 * Get all accessibility issues in container
 */
export function getAccessibilityIssues(container: HTMLElement = document.body): string[] {
  const issues: string[] = [];

  // Check images
  container.querySelectorAll("img").forEach((img, idx) => {
    if (!img.hasAttribute("alt")) {
      issues.push(`Image ${idx}: missing alt attribute`);
    }
  });

  // Check form labels
  container.querySelectorAll("input, textarea, select").forEach((field, idx) => {
    const id = field.id;
    if (!id || !document.querySelector(`label[for="${id}"]`)) {
      if (!field.hasAttribute("aria-label")) {
        issues.push(`Form field ${idx}: missing label`);
      }
    }
  });

  // Check headings
  const headings = Array.from(container.querySelectorAll("h1, h2, h3, h4, h5, h6"));
  let prevLevel = 0;
  headings.forEach((h) => {
    const level = parseInt(h.tagName[1]);
    if (level - prevLevel > 1) {
      issues.push(`Heading: skipped from h${prevLevel} to h${level}`);
    }
    prevLevel = level;
  });

  return issues;
}

// ────────────────────────────────────────────────────────────
// Performance Testing Helpers
// ────────────────────────────────────────────────────────────

/**
 * Mock Web Vitals metrics
 */
export function mockWebVitals(): void {
  if (typeof window === "undefined") return;

  // Mock PerformanceObserver
  const mockEntries: PerformanceEntry[] = [];

  class MockPerformanceObserver {
    constructor(public callback: (list: any) => void) {}

    observe(): void {
      // Simulate metrics after a delay
      setTimeout(() => {
        this.callback({ getEntries: () => mockEntries });
      }, 100);
    }

    disconnect(): void {}
  }

  Object.defineProperty(window, "PerformanceObserver", {
    value: MockPerformanceObserver,
    writable: true,
  });

  // Mock performance.measure
  if (!performance.measure) {
    Object.defineProperty(performance, "measure", {
      value: jest.fn().mockReturnValue({ duration: 100 }),
      writable: true,
    });
  }
}

/**
 * Measure operation performance
 */
export async function measurePerformance<T>(
  name: string,
  fn: () => Promise<T>
): Promise<{ result: T; duration: number }> {
  const start = performance.now();
  const result = await fn();
  const duration = performance.now() - start;

  return { result, duration };
}

// ────────────────────────────────────────────────────────────
// PWA Testing Helpers
// ────────────────────────────────────────────────────────────

/**
 * Simulate offline/online state
 */
export function setOnlineStatus(isOnline: boolean): void {
  Object.defineProperty(navigator, "onLine", {
    writable: true,
    value: isOnline,
  });

  const event = new Event(isOnline ? "online" : "offline");
  window.dispatchEvent(event);
}

/**
 * Mock Notification API
 */
export function mockNotificationAPI(): void {
  const mockNotification = {
    permission: "default" as NotificationPermission,
    requestPermission: jest.fn().mockResolvedValue("granted"),
  };

  Object.defineProperty(window, "Notification", {
    value: mockNotification,
    writable: true,
  });
}

/**
 * Mock Push API
 */
export function mockPushAPI(): void {
  const mockSubscription = {
    endpoint: "https://example.com/push",
    getKey: jest.fn(),
    unsubscribe: jest.fn().mockResolvedValue(true),
    toJSON: jest.fn().mockReturnValue({}),
  };

  const mockPushManager = {
    subscribe: jest.fn().mockResolvedValue(mockSubscription),
    getSubscription: jest.fn().mockResolvedValue(mockSubscription),
    permissionState: jest.fn().mockResolvedValue("granted"),
  };

  Object.defineProperty(navigator, "serviceWorker", {
    value: {
      ready: Promise.resolve({
        pushManager: mockPushManager,
      }),
    },
    configurable: true,
  });
}

/**
 * Mock Screen Orientation API
 */
export function mockScreenOrientationAPI(): void {
  const mockOrientation = {
    type: "portrait-primary" as OrientationType,
    angle: 0,
    lock: jest.fn().mockResolvedValue(undefined),
    unlock: jest.fn(),
  };

  Object.defineProperty(screen, "orientation", {
    value: mockOrientation,
    writable: true,
    configurable: true,
  });
}

// ────────────────────────────────────────────────────────────
// E2E Testing Helpers
// ────────────────────────────────────────────────────────────

/**
 * Wait for element to have text
 */
export function waitForText(
  container: HTMLElement,
  text: string,
  timeout: number = 1000
): Promise<Element | null> {
  return new Promise((resolve) => {
    const start = Date.now();

    const check = () => {
      const element = Array.from(container.querySelectorAll("*")).find(
        (el) => el.textContent === text
      );

      if (element) {
        resolve(element);
      } else if (Date.now() - start > timeout) {
        resolve(null);
      } else {
        requestAnimationFrame(check);
      }
    };

    check();
  });
}

/**
 * Simulate slow network
 */
export function simulateSlowNetwork(delay: number = 2000): void {
  const originalFetch = window.fetch;

  Object.defineProperty(window, "fetch", {
    value: async (...args: any[]) => {
      await new Promise((resolve) => setTimeout(resolve, delay));
      return originalFetch(...args);
    },
    writable: true,
  });
}

/**
 * Cleanup test utilities
 */
export function cleanupTestUtils(): void {
  // Restore original fetch
  delete (window as any).fetch;

  // Clear mocks
  jest.clearAllMocks();

  // Reset online status
  setOnlineStatus(true);
}
