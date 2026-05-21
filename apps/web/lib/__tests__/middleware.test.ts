/** @jest-environment node */

import { NextRequest } from "next/server";
import { middleware } from "@/middleware";

// Gerçek middleware implementasyonu `twai_session` cookie'sini kontrol eder.
// JWT tabanlı cookie'ler (bgts_access_token vb.) bu middleware tarafından
// işlenmez; token yönetimi istemci taraflı api-client üzerinden yapılır.

const SESSION_COOKIE = "twai_session";

function requestWithCookies(url: string, cookies: Record<string, string>): NextRequest {
  const cookieHeader = Object.entries(cookies)
    .map(([key, value]) => `${key}=${value}`)
    .join("; ");
  return new NextRequest(url, {
    headers: cookieHeader ? { cookie: cookieHeader } : {},
  });
}

describe("middleware auth routing", () => {
  it("redirects unauthenticated protected routes to login", () => {
    const req = requestWithCookies("http://localhost/projects?tab=1", {});
    const res = middleware(req);

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe(
      "http://localhost/login?next=%2Fprojects%3Ftab%3D1",
    );
  });

  it("passes through protected routes when session cookie is present", () => {
    const req = requestWithCookies("http://localhost/projects", {
      [SESSION_COOKIE]: "valid-session-id",
    });
    const res = middleware(req);

    // Session cookie varsa geç
    expect(res.status).toBe(200);
    expect(res.headers.get("location")).toBeNull();
  });

  it("redirects unauthenticated users with unrecognized cookies", () => {
    // Bilinmeyen cookie'ler session yerine geçmez
    const req = requestWithCookies("http://localhost/projects", {
      some_other_cookie: "some-value",
    });
    const res = middleware(req);

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/login?next=%2Fprojects");
  });

  it("keeps login page accessible without any cookies", () => {
    // /login public path — her zaman erişilebilir
    const req = requestWithCookies("http://localhost/login", {});
    const res = middleware(req);

    expect(res.status).toBe(200);
    expect(res.headers.get("location")).toBeNull();
  });

  it("keeps login page accessible even with session cookie", () => {
    // Middleware /login'i public path olarak işler, redirect yapmaz
    const req = requestWithCookies("http://localhost/login?next=%2Fp%2Fproj-1", {
      [SESSION_COOKIE]: "valid-session-id",
    });
    const res = middleware(req);

    // Middleware authenticated user'ı /login'den yönlendirmez (bu uygulama taraflı)
    expect(res.status).toBe(200);
  });

  it("redirects nested protected route to login with full path", () => {
    const req = requestWithCookies("http://localhost/p/proj-1/scenarios", {});
    const res = middleware(req);

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe(
      "http://localhost/login?next=%2Fp%2Fproj-1%2Fscenarios",
    );
  });

  it("preserves query params in the next redirect parameter", () => {
    const req = requestWithCookies("http://localhost/analytics?range=7d&view=trend", {});
    const res = middleware(req);

    const location = res.headers.get("location") ?? "";
    expect(location).toContain("next=");
    expect(location).toContain("analytics");
  });

  it("allows reset-password without session", () => {
    const req = requestWithCookies("http://localhost/reset-password?token=abc", {});
    const res = middleware(req);

    // reset-password public path
    expect(res.status).toBe(200);
    expect(res.headers.get("location")).toBeNull();
  });
});
