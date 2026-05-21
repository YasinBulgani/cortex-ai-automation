/**
 * TestwrightAI Enhanced API Client — Refresh Token + TanStack Query Entegrasyonu
 *
 * Özellikler:
 *   - Access + Refresh token yonetimi (localStorage)
 *   - Otomatik token yenileme (401 → refresh → retry)
 *   - Concurrent request deduplication (ayni anda birden fazla 401 gelirse tek refresh)
 *   - Token rotation (her refresh'te yeni access + refresh token)
 */

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/$/, "");

export function getSafeNextPath(candidate: string | null): string {
  if (!candidate) return "";
  const trimmed = candidate.trim();
  if (
    !trimmed.startsWith("/")
    || trimmed.startsWith("//")
    || trimmed === "/login"
    || trimmed.startsWith("/login/")
  ) return "";
  if (trimmed.includes("\\") || trimmed.includes("\r") || trimmed.includes("\n")) return "";
  return trimmed;
}

function getLoginRedirectUrl() {
  if (typeof window === "undefined") return "/login";

  const currentPath = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  const safePath = getSafeNextPath(currentPath);
  const loginUrl = new URL("/login", window.location.origin);
  if (safePath && safePath !== "/login") {
    loginUrl.searchParams.set("next", safePath);
  }

  return loginUrl.toString();
}

// Frontend defaults to the authenticated backend proxy so browsers do not need
// direct access to the Flask engine host. NEXT_PUBLIC_ENGINE_URL is kept only
// as a backwards-compatible alias while configs migrate to *_BASE.
const ENGINE_BASE = (
  process.env.NEXT_PUBLIC_ENGINE_BASE ??
  process.env.NEXT_PUBLIC_ENGINE_URL ??
  "/api/v1/automation/proxy"
).replace(/\/$/, "");

// ── Token Storage ────────────────────────────────────────────────────
const TOKEN_KEY = "tspm_access_token";
const REFRESH_TOKEN_KEY = "tspm_refresh_token";
const TOKEN_EXPIRES_AT_KEY = "tspm_access_token_expires_at";

/**
 * Next.js middleware token içeriğine erişemez (localStorage server'da yok).
 * Bu yüzden ek bir "session varlığı" cookie'si tutuyoruz.
 *
 * `twai_session=1` → kullanıcının oturumu var (değer opak, yalnızca presence).
 * Gerçek yetki her zaman backend tarafında doğrulanır; cookie yalnızca
 * client-side rota yönlendirmesi için ipucudur.
 */
const SESSION_COOKIE = "twai_session";

function setSessionCookie(expiresIn?: number | null): void {
  if (typeof document === "undefined") return;
  const maxAgeSec =
    typeof expiresIn === "number" && Number.isFinite(expiresIn) && expiresIn > 0
      ? expiresIn
      : 8 * 60 * 60; // default 8 saat
  const parts = [
    `${SESSION_COOKIE}=1`,
    "Path=/",
    `Max-Age=${maxAgeSec}`,
    "SameSite=Lax",
  ];
  if (typeof window !== "undefined" && window.location.protocol === "https:") {
    parts.push("Secure");
  }
  document.cookie = parts.join("; ");
}

function clearSessionCookie(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${SESSION_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
}

/**
 * SECURITY: httpOnly cookie auth migration
 *
 * Artık access_token ve refresh_token httpOnly cookie ile sunucuda saklanır
 * (XSS koruması). localStorage'a yazılmaz. Browser otomatik gönderir
 * (credentials: 'include').
 *
 * Geriye dönük: bazı kod yolları hâlâ getToken() çağırabilir. Mevcut
 * localStorage'da token VARSA döndürür (kademeli geçiş). Yeni login'lerde
 * localStorage'a YAZMAYIZ — cookie üzerinden auth olur.
 */
const COOKIE_AUTH_ENABLED = true;

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  // Mevcut session'lar için backwards compat — yeni login'lerde null kalır
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  // SECURITY: localStorage'a yazma — httpOnly cookie kullanıyoruz
  if (!COOKIE_AUTH_ENABLED) {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string) {
  // SECURITY: refresh token httpOnly cookie'de — localStorage'a yazma
  if (!COOKIE_AUTH_ENABLED) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  }
}

/**
 * Access token'ın ne zaman biteceğini (ms epoch) döndürür; bilinmiyorsa null.
 * Proaktif refresh için kullanılır.
 */
export function getTokenExpiresAt(): number | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(TOKEN_EXPIRES_AT_KEY);
  if (!raw) return null;
  const v = Number(raw);
  return Number.isFinite(v) ? v : null;
}

/**
 * Token'ları kaydeder.
 * @param access        JWT access token (zorunlu)
 * @param refresh       Refresh token (opsiyonel)
 * @param expiresIn     Access token ömrü, saniye (opsiyonel — /auth/login'in döndüğü expires_in)
 */
export function setTokens(
  access: string,
  refresh?: string | null,
  expiresIn?: number | null,
) {
  // SECURITY: httpOnly cookie üzerinden auth — token'ları localStorage'a yazma.
  // Backend `Set-Cookie` header'ı ile zaten cookie set etti.
  if (!COOKIE_AUTH_ENABLED) {
    setToken(access);
    if (refresh) setRefreshToken(refresh);
    if (typeof expiresIn === "number" && Number.isFinite(expiresIn) && expiresIn > 0) {
      localStorage.setItem(
        TOKEN_EXPIRES_AT_KEY,
        String(Date.now() + expiresIn * 1000),
      );
    }
  }
  // Presence cookie middleware için zorunlu (twai_session)
  setSessionCookie(expiresIn);
}

/**
 * Migration helper: eski localStorage token'larını temizler.
 * Login sonrası bir kez çağrılır.
 */
export function migrateToCookieAuth() {
  if (typeof window === "undefined" || !COOKIE_AUTH_ENABLED) return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(TOKEN_EXPIRES_AT_KEY);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(TOKEN_EXPIRES_AT_KEY);
  clearSessionCookie();
}

/** @deprecated Eski API uyumlulugu — clearTokens() tercih edin */
export const clearToken = clearTokens;

// ── Refresh Token Mekanizmasi ────────────────────────────────────────
let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({}),
    });

    if (!res.ok) {
      clearTokens();
      return false;
    }

    const data = await res.json();
    // Backend bazen 200 ama error body döner (revoked token vb.) — access_token yoksa başarısız say.
    if (!data?.access_token) {
      clearTokens();
      return false;
    }
    setTokens(data.access_token, data.refresh_token, data.expires_in);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

/**
 * Deduplicated refresh — birden fazla 401 ayni anda gelirse
 * tek bir refresh istegi gonderir, diger request'ler bekler.
 *
 * @public SSE/raw-fetch sayfalarında stream başlamadan önce çağırın.
 */
export async function ensureValidToken(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = refreshAccessToken().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

// ── API Errors ───────────────────────────────────────────────────────
export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function extractApiErrorMessage(body: unknown, fallback: string): string {
  if (typeof body === "string" && body) return body;
  if (!body || typeof body !== "object") return fallback;

  const detail = "detail" in body ? (body as { detail?: unknown }).detail : body;
  if (typeof detail === "string" && detail) return detail;
  if (!detail || typeof detail !== "object") return fallback;

  const message = (detail as { message?: unknown }).message;
  if (typeof message === "string" && message) {
    const details = (detail as { details?: unknown }).details;
    return typeof details === "string" && details ? `${message}: ${details}` : message;
  }

  return fallback;
}

// ── Core Fetch ───────────────────────────────────────────────────────
export type ApiFetchOptions = RequestInit & {
  json?: unknown;
  /**
   * Public/auth endpoints for login/reset flows.
   * noAuth=true skips refresh + automatic login redirect on 401.
   */
  noAuth?: boolean;
  /**
   * Optional override for retry behavior after a 401.
   * Defaults to `!noAuth`.
   */
  retryOnUnauthorized?: boolean;
};

export async function apiFetch<T>(
  path: string,
  init: RequestInit & { json?: unknown; skipAuthRedirect?: boolean; retryOnUnauthorized?: boolean; noAuth?: boolean } = {},
): Promise<T> {
  const {
    json,
    headers,
    skipAuthRedirect = false,
    noAuth = false,
    // noAuth=true is the documented opt-out for public/auth flows — it must skip the refresh+retry
    retryOnUnauthorized = !skipAuthRedirect && !noAuth,
    ...rest
  } = init;
  const token = getToken();
  const h = new Headers(headers);

  if (json !== undefined) {
    h.set("Content-Type", "application/json");
  }

  let res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    credentials: "include",
    headers: h,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });

  // 401 → refresh token ile yenileme dene
  if (res.status === 401 && retryOnUnauthorized) {
    const refreshed = await ensureValidToken();
    if (refreshed) {
      const h2 = new Headers(headers);
      if (json !== undefined) h2.set("Content-Type", "application/json");

      res = await fetch(`${API_BASE}${path}`, {
        ...rest,
        credentials: "include",
        headers: h2,
        body: json !== undefined ? JSON.stringify(json) : rest.body,
      });
    }
  }

  if (!res.ok) {
    const text = await res.text();
    let body: unknown;
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
    let detail =
      typeof body === "object" && body !== null && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : text || res.statusText;

    // HTML response gelirse (404 sayfa gibi) ham HTML'i error message yapma —
    // sayfaların onu render etmesini önler.
    if (typeof detail === "string" && detail.trim().startsWith("<")) {
      detail = `HTTP ${res.status} ${res.statusText || "Error"} — endpoint bulunamadı veya HTML yanıt döndü`;
    }

    // Auth akışı:
    //  - Login ekranı kapalı olduğu için 401 durumunda /login'e yönlendirme yapma.
    //  - Token geçersiz/expire ise local auth state'i temizle; hata çağrı yerinde yönetilsin.
    //  - 403 = kimlik doğru ama yetki yok ⇒ token silme;
    //          çağrı yerindeki hata handler kullanıcıya "yetkiniz yok" diyebilir.
    //  - Auth endpoint'lerinde (/auth/*) state temizleme yapma ki sayfa kendi hatasını göstersin.
    const isAuthPath = path.startsWith("/api/v1/auth/");
    // Dev'de `AuthBootstrap` arka planda oturum açıyor olabilir. O sırada
    // 401 gelip token temizlersek flash ve istenmeyen auth state kaybı
    // oluşur; bootstrap bitince reload zaten doğru sayfayı getirecek.
    const bootstrapping =
      typeof window !== "undefined" &&
      (window as unknown as { __bgtsAuthBootstrapping?: boolean }).__bgtsAuthBootstrapping === true;
    if (res.status === 401 && !isAuthPath && !bootstrapping && !skipAuthRedirect && typeof window !== "undefined") {
      clearTokens();
    }

    throw new ApiError(res.status, detail, body);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Dogrudan Flask motoruna istek — proxy tercih edin. */
export async function engineFetch<T>(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const { json, headers, ...rest } = init;
  const h = new Headers(headers);
  if (json !== undefined) {
    h.set("Content-Type", "application/json");
  }
  const res = await fetch(`${ENGINE_BASE}${path}`, {
    ...rest,
    headers: h,
    credentials: "include",
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/**
 * Returns true if a session presence cookie exists.
 * Cookie auth modunda getToken() her zaman null döndüğü için
 * useCurrentUser() gibi hook'larda `enabled` condition olarak kullan.
 */
export function hasSession(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie
    .split(";")
    .some((c) => c.trim().startsWith(`${SESSION_COOKIE}=`));
}

export { API_BASE, ENGINE_BASE };
