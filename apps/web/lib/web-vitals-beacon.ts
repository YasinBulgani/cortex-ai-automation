/**
 * Bağımlılıksız Core Web Vitals RUM beacon.
 *
 * Native PerformanceObserver ile LCP / CLS / FCP / INP(yaklaşık) toplar ve
 * sayfa gizlenince tek batch olarak `POST /api/v1/products/web/vitals`'a yollar.
 * Backend bu örneklerden sayfa-başı p75 hesaplar (Products → Web → Perf paneli).
 *
 * Tasarım:
 *  - Yalnızca tarayıcıda ve geçerli oturum (token) varken çalışır.
 *  - Dev/localhost'ta varsayılan kapalı (NEXT_PUBLIC_RUM_ENABLED=1 ile açılır).
 *  - Sayfa yaşam döngüsü başına bir kez gönderir (visibilitychange→hidden).
 *  - Unload sırasında fetch keepalive kullanır (Authorization header taşır;
 *    sendBeacon header taşıyamadığı için tercih edilmez).
 *  - page_url = pathname (query string'i atar — PII/yüksek kardinalite önler).
 *
 * TBT alan-ortamında ölçülemez (lab metriği) — null bırakılır.
 */

import { getToken, API_BASE } from "@/lib/api-client";

type VitalsSample = {
  page_url: string;
  page_label?: string;
  lcp?: number | null;
  inp?: number | null;
  cls?: number | null;
  fcp?: number | null;
  tbt?: number | null;
};

let _started = false;

function isEnabled(): boolean {
  if (typeof window === "undefined") return false;
  if (typeof PerformanceObserver === "undefined") return false;
  const host = window.location.hostname;
  const isDev =
    process.env.NODE_ENV === "development" ||
    host === "localhost" ||
    host.startsWith("127.");
  if (isDev && process.env.NEXT_PUBLIC_RUM_ENABLED !== "1") return false;
  return true;
}

/**
 * Mevcut sayfa için CWV toplamaya başlar. Idempotent — birden fazla çağrı
 * tek bir gözlemci kümesi kurar. Cleanup fonksiyonu döndürür.
 */
export function startWebVitalsBeacon(): () => void {
  // NOT: getToken()'a bağlama — uygulama httpOnly cookie auth kullanıyor ve
  // getToken() yeni oturumlarda null döner. Auth credentials:include ile cookie
  // üzerinden taşınır; Bearer yalnızca legacy localStorage token'ı varsa eklenir.
  if (_started || !isEnabled()) return () => {};
  _started = true;

  let lcp: number | null = null;
  let cls = 0;
  let fcp: number | null = null;
  let inp: number | null = null;
  let sent = false;

  const observers: PerformanceObserver[] = [];

  const observe = (
    type: string,
    cb: (entries: PerformanceEntryList) => void,
    extra?: PerformanceObserverInit,
  ) => {
    try {
      const po = new PerformanceObserver((list) => cb(list.getEntries()));
      po.observe({ type, buffered: true, ...extra } as PerformanceObserverInit);
      observers.push(po);
    } catch {
      /* tarayıcı bu entry tipini desteklemiyor — sessizce atla */
    }
  };

  // LCP — en son largest-contentful-paint girişinin zamanı
  observe("largest-contentful-paint", (entries) => {
    const last = entries[entries.length - 1] as PerformanceEntry & { renderTime?: number; loadTime?: number };
    if (last) lcp = last.renderTime || last.loadTime || last.startTime || null;
  });

  // CLS — son kullanıcı girdisi olmayan layout-shift'lerin kümülatif toplamı
  observe("layout-shift", (entries) => {
    for (const e of entries as unknown as Array<PerformanceEntry & { value: number; hadRecentInput: boolean }>) {
      if (!e.hadRecentInput) cls += e.value;
    }
  });

  // FCP — paint timing
  observe("paint", (entries) => {
    for (const e of entries) {
      if (e.name === "first-contentful-paint") fcp = e.startTime;
    }
  });

  // INP (yaklaşık) — en uzun etkileşim event süresi
  observe(
    "event",
    (entries) => {
      for (const e of entries as unknown as Array<PerformanceEntry & { duration: number }>) {
        if (inp === null || e.duration > inp) inp = e.duration;
      }
    },
    { durationThreshold: 40 } as PerformanceObserverInit,
  );

  const send = () => {
    if (sent) return;
    sent = true;
    observers.forEach((po) => {
      try {
        po.takeRecords();
        po.disconnect();
      } catch {
        /* ignore */
      }
    });

    const round = (v: number | null) => (v === null ? null : Math.round(v));
    const sample: VitalsSample = {
      page_url: window.location.pathname,
      page_label: document.title || undefined,
      lcp: round(lcp),
      inp: round(inp),
      cls: cls > 0 ? Number(cls.toFixed(4)) : null,
      fcp: round(fcp),
      tbt: null,
    };

    // Hiçbir metrik toplanmadıysa gönderme
    if (sample.lcp === null && sample.fcp === null && sample.cls === null && sample.inp === null) return;

    const headers: Record<string, string> = { "Content-Type": "application/json" };
    // Legacy (cookie-öncesi) oturumlar için Bearer ekle; cookie-auth'ta token null
    // olur ve credentials:include zaten httpOnly cookie'yi taşır.
    const legacyToken = getToken();
    if (legacyToken) headers.Authorization = `Bearer ${legacyToken}`;

    try {
      void fetch(`${API_BASE}/api/v1/products/web/vitals`, {
        method: "POST",
        headers,
        body: JSON.stringify({ samples: [sample] }),
        keepalive: true,
        credentials: "include",
      }).catch(() => {});
    } catch {
      /* unload sırasında hata — yut */
    }
  };

  const onHidden = () => {
    if (document.visibilityState === "hidden") send();
  };
  document.addEventListener("visibilitychange", onHidden);
  window.addEventListener("pagehide", send);

  return () => {
    document.removeEventListener("visibilitychange", onHidden);
    window.removeEventListener("pagehide", send);
    observers.forEach((po) => {
      try {
        po.disconnect();
      } catch {
        /* ignore */
      }
    });
    _started = false;
  };
}
