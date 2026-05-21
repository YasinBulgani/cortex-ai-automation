"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { setTokens, migrateToCookieAuth, API_BASE } from "@/lib/api-client";

/**
 * Dev otomatik oturum bootstrap'i (Cookie Auth uyumlu).
 *
 * httpOnly cookie auth migration sonrası:
 *   - Access/refresh token httpOnly cookie'de (JS okuyamaz)
 *   - localStorage'da token YOK
 *   - Presence cookie `twai_session` middleware için
 *
 * Bu component her route değişiminde:
 *   1. Presence cookie var mı kontrol eder
 *   2. Yoksa dev credentials ile login (cookie set olur)
 *   3. State guard ile loop önler (`window.__bgtsAuthBootstrapping`)
 *   4. `reload()` YERINE soft refresh — loop'a yol açmamak için
 *
 * Production build'de no-op.
 */

const DEV_EMAIL = "test@test.com";
const DEV_PASSWORD = "test";

type WinWithFlags = {
  __bgtsAuthBootstrapping?: boolean;
  __bgtsAuthBootstrapped?: boolean;
};

function hasSessionCookie(): boolean {
  if (typeof document === "undefined") return false;
  // Presence cookie middleware tarafından kontrol edilir
  return document.cookie.split(";").some(c => c.trim().startsWith("twai_session="));
}

export default function AuthBootstrap(): null {
  const pathname = usePathname();

  useEffect(() => {
    if (process.env.NODE_ENV !== "development") return;
    if (typeof window === "undefined") return;

    const win = window as unknown as WinWithFlags;

    // Session cookie varsa hiçbir şey yapma
    if (hasSessionCookie()) return;

    // Bu page render'da zaten bootstrap'lediysek tekrar deneme
    if (win.__bgtsAuthBootstrapped) return;

    // Eş zamanlı bootstrap girişimlerini önle
    if (win.__bgtsAuthBootstrapping) return;
    win.__bgtsAuthBootstrapping = true;

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",  // httpOnly cookie almak için
          body: JSON.stringify({ email: DEV_EMAIL, password: DEV_PASSWORD }),
          signal: AbortSignal.timeout(5000),
        });
        if (!res.ok) {
          win.__bgtsAuthBootstrapping = false;
          return;
        }
        const data = await res.json();
        if (!data?.access_token) {
          win.__bgtsAuthBootstrapping = false;
          return;
        }

        // setTokens artık COOKIE_AUTH_ENABLED ise sadece presence cookie set ediyor
        setTokens(data.access_token, data.refresh_token, data.expires_in);
        migrateToCookieAuth();

        win.__bgtsAuthBootstrapping = false;
        win.__bgtsAuthBootstrapped = true;

        // ÖNEMLİ: window.location.reload() KULLANMA — infinite loop'a yol açar.
        // Bunun yerine Next.js router'ı tetikle veya state hook'ları yenilesin.
        // Cookie set edildi, sonraki render'da middleware geçer.
        // Router refresh ile sayfa yeniden istenir ama HARD reload değil.
        if (typeof window !== "undefined" && hasSessionCookie()) {
          // Soft refresh — Next.js cache'i invalide eder
          window.dispatchEvent(new Event("bgts:auth-bootstrapped"));
          // Eğer login sayfasındaysak ana sayfaya git
          if (window.location.pathname === "/login") {
            const next = new URLSearchParams(window.location.search).get("next") || "/";
            window.location.replace(next);
          }
        }
      } catch {
        win.__bgtsAuthBootstrapping = false;
      }
    })();
  // pathname değişince tekrar kontrol et
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  return null;
}
