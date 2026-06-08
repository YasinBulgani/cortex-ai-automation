import "@testing-library/jest-dom";

// jsdom AbortSignal.timeout'u desteklemez (yeni API) — bileşenler
// fetch(url, { signal: AbortSignal.timeout(ms) } kullanıyor. Test ortamı
// için polyfill ekle (yoksa "AbortSignal.timeout is not a function").
if (typeof AbortSignal !== "undefined" && typeof (AbortSignal as any).timeout !== "function") {
  (AbortSignal as any).timeout = (ms: number): AbortSignal => {
    const controller = new AbortController();
    setTimeout(() => controller.abort(new DOMException("TimeoutError", "TimeoutError")), ms);
    return controller.signal;
  };
}
