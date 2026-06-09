/**
 * PWA Utilities — Service Worker, Push Notifications, Background Sync, Offline Queue
 */

export interface OfflineQueueItem {
  id?: number;
  url: string;
  method: "POST" | "PATCH" | "PUT" | "DELETE";
  headers: Record<string, string>;
  body: string;
  timestamp: number;
  retries: number;
}

export interface PushNotificationPayload {
  title: string;
  body: string;
  icon?: string;
  badge?: string;
  tag?: string;
  requireInteraction?: boolean;
  url?: string;
  actions?: Array<{ action: string; title: string; icon?: string }>;
  data?: Record<string, unknown>;
}

// ────────────────────────────────────────────────────────────
// Service Worker Management
// ────────────────────────────────────────────────────────────

/**
 * Register service worker in production
 */
export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (typeof window === "undefined") return null;
  if (!("serviceWorker" in navigator)) return null;

  const isDev =
    process.env.NODE_ENV === "development" ||
    window.location.hostname === "localhost" ||
    window.location.hostname.startsWith("127.");

  try {
    if (!isDev) {
      const registration = await navigator.serviceWorker.register("/sw.js", {
        scope: "/",
      });
      return registration;
    }
  } catch (err) {
    console.error("SW registration failed:", err);
  }

  return null;
}

/**
 * Get active service worker registration
 */
export async function getServiceWorkerRegistration(): Promise<ServiceWorkerRegistration | null> {
  if (!("serviceWorker" in navigator)) return null;

  try {
    const registrations = await navigator.serviceWorker.getRegistrations();
    return registrations[0] || null;
  } catch {
    return null;
  }
}

/**
 * Update service worker (check for updates)
 */
export async function updateServiceWorker(): Promise<void> {
  const registration = await getServiceWorkerRegistration();
  if (registration) {
    await registration.update();
  }
}

/**
 * Unregister service worker (for cleanup/testing)
 */
export async function unregisterServiceWorker(): Promise<void> {
  const registration = await getServiceWorkerRegistration();
  if (registration) {
    await registration.unregister();
  }
}

// ────────────────────────────────────────────────────────────
// Push Notifications
// ────────────────────────────────────────────────────────────

/**
 * Request notification permission
 */
export async function requestNotificationPermission(): Promise<NotificationPermission> {
  if (!("Notification" in window)) {
    throw new Error("Notifications not supported");
  }

  if (Notification.permission === "granted" || Notification.permission === "denied") {
    return Notification.permission;
  }

  return Notification.requestPermission();
}

/**
 * Get push subscription
 */
export async function getPushSubscription(): Promise<PushSubscription | null> {
  const registration = await getServiceWorkerRegistration();
  if (!registration) return null;

  return registration.pushManager.getSubscription();
}

/**
 * Subscribe to push notifications
 */
export async function subscribeToPush(vapidPublicKey: string): Promise<PushSubscription> {
  const permission = await requestNotificationPermission();
  if (permission !== "granted") {
    throw new Error("Notification permission denied");
  }

  const registration = await getServiceWorkerRegistration();
  if (!registration) {
    throw new Error("Service worker not registered");
  }

  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
  });

  return subscription;
}

/**
 * Unsubscribe from push notifications
 */
export async function unsubscribeFromPush(): Promise<boolean> {
  const subscription = await getPushSubscription();
  if (!subscription) return false;

  return subscription.unsubscribe();
}

/**
 * Convert VAPID public key to Uint8Array
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, "+")
    .replace(/_/g, "/");

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }

  return outputArray;
}

// ────────────────────────────────────────────────────────────
// Background Sync
// ────────────────────────────────────────────────────────────

/**
 * Request background sync
 */
export async function requestBackgroundSync(tag: string = "sync-mutations"): Promise<void> {
  const registration = await getServiceWorkerRegistration();
  if (!registration || !("sync" in registration)) {
    throw new Error("Background Sync API not supported");
  }

  await registration.sync.register(tag);
}

/**
 * Get all pending sync tags
 */
export async function getPendingSyncTags(): Promise<string[]> {
  const registration = await getServiceWorkerRegistration();
  if (!registration || !("sync" in registration)) {
    return [];
  }

  return registration.sync.getTags();
}

// ────────────────────────────────────────────────────────────
// Offline Queue Management (IndexedDB)
// ────────────────────────────────────────────────────────────

let idbInstance: IDBDatabase | null = null;

/**
 * Open IndexedDB for offline queue
 */
export async function openOfflineDB(): Promise<IDBDatabase> {
  if (idbInstance) return idbInstance;

  return new Promise((resolve, reject) => {
    const req = indexedDB.open("neurex_offline", 1);

    req.onerror = () => reject(req.error);
    req.onsuccess = () => {
      idbInstance = req.result;
      resolve(req.result);
    };

    req.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains("offline_queue")) {
        const store = db.createObjectStore("offline_queue", {
          keyPath: "id",
          autoIncrement: true,
        });
        store.createIndex("timestamp", "timestamp", { unique: false });
        store.createIndex("retries", "retries", { unique: false });
      }
    };
  });
}

/**
 * Add mutation to offline queue
 */
export async function queueOfflineMutation(
  url: string,
  method: "POST" | "PATCH" | "PUT" | "DELETE",
  body?: unknown,
  headers?: Record<string, string>
): Promise<number> {
  const db = await openOfflineDB();
  const tx = db.transaction("offline_queue", "readwrite");
  const store = tx.objectStore("offline_queue");

  const item: OfflineQueueItem = {
    url,
    method,
    headers: headers || {},
    body: typeof body === "string" ? body : JSON.stringify(body),
    timestamp: Date.now(),
    retries: 0,
  };

  return new Promise((resolve, reject) => {
    const req = store.add(item);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result as number);
  });
}

/**
 * Get all queued mutations
 */
export async function getQueuedMutations(): Promise<OfflineQueueItem[]> {
  const db = await openOfflineDB();
  const tx = db.transaction("offline_queue", "readonly");
  const store = tx.objectStore("offline_queue");

  return new Promise((resolve, reject) => {
    const req = store.getAll();
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve((req.result as OfflineQueueItem[]) || []);
  });
}

/**
 * Remove mutation from queue
 */
export async function removeQueuedMutation(id: number): Promise<void> {
  const db = await openOfflineDB();
  const tx = db.transaction("offline_queue", "readwrite");
  const store = tx.objectStore("offline_queue");

  return new Promise((resolve, reject) => {
    const req = store.delete(id);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve();
  });
}

/**
 * Clear all queued mutations
 */
export async function clearOfflineQueue(): Promise<void> {
  const db = await openOfflineDB();
  const tx = db.transaction("offline_queue", "readwrite");
  const store = tx.objectStore("offline_queue");

  return new Promise((resolve, reject) => {
    const req = store.clear();
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve();
  });
}

// ────────────────────────────────────────────────────────────
// Network Status
// ────────────────────────────────────────────────────────────

export function isOnline(): boolean {
  return typeof navigator !== "undefined" && navigator.onLine;
}

export function onOnline(callback: () => void): () => void {
  window.addEventListener("online", callback);
  return () => window.removeEventListener("online", callback);
}

export function onOffline(callback: () => void): () => void {
  window.addEventListener("offline", callback);
  return () => window.removeEventListener("offline", callback);
}

// ────────────────────────────────────────────────────────────
// Installation Check
// ────────────────────────────────────────────────────────────

export function isAppInstalled(): boolean {
  if (typeof window === "undefined") return false;

  // Check display mode (PWA installed)
  if (window.matchMedia("(display-mode: standalone)").matches) {
    return true;
  }

  // iOS check
  return (
    (navigator as any).standalone === true ||
    window.location.search === "?utm_source=web_app_manifest"
  );
}

export function onAppInstalled(callback: () => void): void {
  if (typeof window === "undefined") return;

  window.addEventListener("appinstalled", callback);
}

// ────────────────────────────────────────────────────────────
// Screen Orientation
// ────────────────────────────────────────────────────────────

export async function lockScreenOrientation(
  orientation: "portrait-primary" | "landscape-primary" | "portrait" | "landscape"
): Promise<void> {
  if (!("orientation" in screen)) {
    throw new Error("Screen Orientation API not supported");
  }

  try {
    await (screen.orientation as any).lock(orientation);
  } catch (err) {
    console.error("Failed to lock screen orientation:", err);
  }
}

export async function unlockScreenOrientation(): Promise<void> {
  if (!("orientation" in screen)) {
    throw new Error("Screen Orientation API not supported");
  }

  (screen.orientation as any).unlock();
}

// ────────────────────────────────────────────────────────────
// Full Screen API
// ────────────────────────────────────────────────────────────

export async function requestFullscreen(element: Element = document.documentElement): Promise<void> {
  try {
    if (element.requestFullscreen) {
      await element.requestFullscreen();
    } else if ((element as any).webkitRequestFullscreen) {
      await (element as any).webkitRequestFullscreen();
    }
  } catch (err) {
    console.error("Fullscreen request failed:", err);
  }
}

export async function exitFullscreen(): Promise<void> {
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    }
  } catch (err) {
    console.error("Fullscreen exit failed:", err);
  }
}

// ────────────────────────────────────────────────────────────
// Web Share API
// ────────────────────────────────────────────────────────────

export interface ShareData {
  title?: string;
  text?: string;
  url?: string;
  files?: File[];
}

export async function share(data: ShareData): Promise<void> {
  if (!("share" in navigator)) {
    throw new Error("Web Share API not supported");
  }

  await navigator.share(data);
}

export function canShare(): boolean {
  return typeof navigator !== "undefined" && "share" in navigator;
}

// ────────────────────────────────────────────────────────────
// Haptic Feedback (Vibration API)
// ────────────────────────────────────────────────────────────

export function vibrate(pattern: number | number[]): boolean {
  if (typeof navigator === "undefined" || !("vibrate" in navigator)) {
    return false;
  }

  try {
    (navigator as any).vibrate(pattern);
    return true;
  } catch {
    return false;
  }
}

export const hapticPatterns = {
  tap: 20,
  success: [20, 10, 20],
  warning: [50, 20, 50],
  error: [100, 50, 100],
  notify: [30, 10, 30, 10, 30],
};
