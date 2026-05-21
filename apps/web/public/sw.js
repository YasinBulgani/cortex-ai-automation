// Neurex QA Service Worker
// Strateji:
//   - HTML navigations: network-first, fallback to offline page
//   - Static assets (_next/static, /icon-*, /manifest.json): cache-first
//   - API calls (/api/v1/...): network-only (auth + freshness kritik)
//
// Versionlama: CACHE_VERSION bump'lanır → eski cache silinir.

const CACHE_VERSION = "neurex-v1";
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const PAGE_CACHE = `${CACHE_VERSION}-pages`;
const OFFLINE_URL = "/offline";

const STATIC_ASSETS = [
  "/manifest.json",
  "/icon-192.svg",
  "/icon-512.svg",
  "/logo.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

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

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Sadece GET cache'lenir; POST/PATCH/DELETE pass-through.
  if (request.method !== "GET") return;

  // Different-origin (CDN, external) — pass-through.
  if (url.origin !== self.location.origin) return;

  // API ve auth — network only, freshness + auth kritik.
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/_next/data")) {
    return;
  }

  // HTML navigations — network-first, offline fallback.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          // Successful navigation → cache copy for offline use
          const copy = res.clone();
          caches.open(PAGE_CACHE).then((cache) => cache.put(request, copy));
          return res;
        })
        .catch(() =>
          caches.match(request).then((hit) => hit || caches.match(OFFLINE_URL))
        )
    );
    return;
  }

  // Static assets — cache-first.
  if (
    url.pathname.startsWith("/_next/static/") ||
    url.pathname.startsWith("/icon-") ||
    url.pathname === "/manifest.json" ||
    url.pathname === "/logo.png"
  ) {
    event.respondWith(
      caches.match(request).then((hit) => {
        if (hit) return hit;
        return fetch(request).then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(STATIC_CACHE).then((cache) => cache.put(request, copy));
          }
          return res;
        });
      })
    );
  }
});
