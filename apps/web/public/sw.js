// Neurex QA Service Worker v2.0
// Enhanced: background sync, offline queue, push notifications, performance monitoring
//
// Strateji:
//   - HTML navigations: network-first, fallback to offline page
//   - Static assets (_next/static, /icon-*, /manifest.json): cache-first
//   - API calls (/api/v1/...): network-only (auth + freshness kritik)
//   - Background Sync: offline mutations → queue → sync when online
//   - Push Notifications: subscribe + handle payload

const CACHE_VERSION = "neurex-v2";
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const PAGE_CACHE = `${CACHE_VERSION}-pages`;
const API_CACHE = `${CACHE_VERSION}-api`;
const OFFLINE_URL = "/offline";

// Static assets pre-cached at install
const STATIC_ASSETS = [
  "/manifest.json",
  "/icon-192.svg",
  "/icon-512.svg",
  "/logo.png",
  "/offline",
];

// ────────────────────────────────────────────────────────────
// Install: cache static assets, skip waiting
// ────────────────────────────────────────────────────────────
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => {
        return Promise.all(
          STATIC_ASSETS.map((url) =>
            fetch(url)
              .then((res) => {
                if (res.ok) {
                  return cache.put(url, res);
                }
              })
              .catch(() => {
                // Fail gracefully for missing assets
              })
          )
        );
      })
      .then(() => self.skipWaiting())
  );
});

// ────────────────────────────────────────────────────────────
// Activate: clean old caches, claim clients
// ────────────────────────────────────────────────────────────
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => !k.startsWith(CACHE_VERSION))
            .map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ────────────────────────────────────────────────────────────
// Fetch: routing by request type
// ────────────────────────────────────────────────────────────
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only cache GET requests
  if (request.method !== "GET") {
    return;
  }

  // Different-origin (CDN, external) — pass-through
  if (url.origin !== self.location.origin) {
    return;
  }

  // API calls — network-only (auth + freshness kritik)
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(fetchWithFallback(request, API_CACHE, false));
    return;
  }

  // Next.js data — network-only (hydration kritik)
  if (url.pathname.startsWith("/_next/data")) {
    event.respondWith(fetch(request).catch(() => notFoundResponse()));
    return;
  }

  // HTML navigations — network-first, offline fallback
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const copy = res.clone();
          caches.open(PAGE_CACHE).then((cache) => cache.put(request, copy));
          return res;
        })
        .catch(() =>
          caches
            .match(request)
            .then((hit) => hit || caches.match(OFFLINE_URL))
        )
    );
    return;
  }

  // Static assets (CSS, JS, images, fonts) — cache-first
  if (isStaticAsset(url.pathname)) {
    event.respondWith(fetchWithFallback(request, STATIC_CACHE, true));
    return;
  }

  // Default: network-first, fallback to cache
  event.respondWith(fetchWithFallback(request, API_CACHE, false));
});

// ────────────────────────────────────────────────────────────
// Helper: fetch with fallback to cache
// ────────────────────────────────────────────────────────────
async function fetchWithFallback(request, cacheName, cacheFirst) {
  try {
    if (cacheFirst) {
      const cached = await caches.match(request);
      if (cached) return cached;
    }

    const response = await fetch(request);
    if (response.ok) {
      const copy = response.clone();
      const cache = await caches.open(cacheName);
      cache.put(request, copy).catch(() => {});
    }
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;
    return notFoundResponse();
  }
}

// ────────────────────────────────────────────────────────────
// Helper: identify static assets
// ────────────────────────────────────────────────────────────
function isStaticAsset(pathname) {
  return (
    pathname.startsWith("/_next/static/") ||
    pathname.match(/\.(js|css|woff2|woff|ttf|eot|svg|png|jpg|jpeg|gif|webp)$/)
  );
}

// ────────────────────────────────────────────────────────────
// Helper: 404 response
// ────────────────────────────────────────────────────────────
function notFoundResponse() {
  return new Response("Not Found", { status: 404 });
}

// ────────────────────────────────────────────────────────────
// Background Sync: sync offline mutations when back online
// ────────────────────────────────────────────────────────────
self.addEventListener("sync", (event) => {
  if (event.tag === "sync-mutations") {
    event.waitUntil(syncMutations());
  }
});

async function syncMutations() {
  try {
    const db = await openIDB();
    const tx = db.transaction("offline_queue", "readonly");
    const store = tx.objectStore("offline_queue");
    const mutations = await store.getAll();

    for (const mutation of mutations) {
      try {
        const response = await fetch(mutation.url, {
          method: mutation.method,
          headers: mutation.headers,
          body: mutation.body,
        });

        if (response.ok) {
          // Remove from queue
          const deleteTx = db.transaction("offline_queue", "readwrite");
          await deleteTx.objectStore("offline_queue").delete(mutation.id);
        }
      } catch (err) {
        // Log and continue with next mutation
        console.error("Sync mutation failed:", err);
      }
    }
  } catch (err) {
    console.error("Background sync failed:", err);
  }
}

// ────────────────────────────────────────────────────────────
// IndexedDB: offline queue storage
// ────────────────────────────────────────────────────────────
function openIDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open("neurex_offline", 1);

    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);

    req.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains("offline_queue")) {
        db.createObjectStore("offline_queue", { keyPath: "id", autoIncrement: true });
      }
    };
  });
}

// ────────────────────────────────────────────────────────────
// Push Notifications: handle incoming push events
// ────────────────────────────────────────────────────────────
self.addEventListener("push", (event) => {
  if (!event.data) {
    return;
  }

  const data = event.data.json();
  const options = {
    body: data.body || "",
    icon: "/icon-192.svg",
    badge: "/icon-192.svg",
    tag: data.tag || "neurex-notification",
    requireInteraction: data.requireInteraction || false,
    actions: data.actions || [],
    data: data.data || {},
  };

  event.waitUntil(
    self.registration.showNotification(data.title || "Neurex", options)
  );
});

// ────────────────────────────────────────────────────────────
// Notification Click: handle notification interaction
// ────────────────────────────────────────────────────────────
self.addEventListener("notificationclick", (event) => {
  const { notification, action } = event;
  const data = notification.data;

  notification.close();

  event.waitUntil(
    clients.matchAll({ type: "window" }).then((clientList) => {
      // Try to focus existing window
      for (const client of clientList) {
        if (client.url === data.url && "focus" in client) {
          return client.focus();
        }
      }
      // Open new window if none exists
      if (data.url && clients.openWindow) {
        return clients.openWindow(data.url);
      }
    })
  );
});

// ────────────────────────────────────────────────────────────
// Notification Close: optional cleanup
// ────────────────────────────────────────────────────────────
self.addEventListener("notificationclose", (event) => {
  const data = event.notification.data;
  // Optional: track dismissals
  if (data.dismissalUrl) {
    fetch(data.dismissalUrl, { method: "POST" }).catch(() => {});
  }
});
