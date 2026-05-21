/** @jest-environment node */

import { NextRequest } from "next/server";

import { middleware } from "@/middleware";
import { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE } from "@/lib/auth-cookies";

function base64UrlEncode(value: string): string {
  const encoded =
    typeof btoa === "function"
      ? btoa(value)
      : Buffer.from(value, "utf-8").toString("base64");
  return encoded.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function makeJwt(expEpochSeconds: number): string {
  const header = base64UrlEncode(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = base64UrlEncode(JSON.stringify({ sub: "user-1", exp: expEpochSeconds }));
  return `${header}.${payload}.signature`;
}

function makeJwtWithoutExp(): string {
  const header = base64UrlEncode(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = base64UrlEncode(JSON.stringify({ sub: "user-1" }));
  return `${header}.${payload}.signature`;
}

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

  it("clears stale cookies when redirecting protected routes", () => {
    const expired = makeJwt(Math.floor(Date.now() / 1000) - 60);
    const req = requestWithCookies("http://localhost/projects", {
      [ACCESS_TOKEN_COOKIE]: expired,
      [REFRESH_TOKEN_COOKIE]: expired,
    });
    const res = middleware(req);

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/login?next=%2Fprojects");
    const setCookie = res.headers.get("set-cookie") ?? "";
    expect(setCookie).toContain(`${ACCESS_TOKEN_COOKIE}=`);
    expect(setCookie).toContain(`${REFRESH_TOKEN_COOKIE}=`);
  });

  it("redirects authenticated users away from login", () => {
    const valid = makeJwt(Math.floor(Date.now() / 1000) + 300);
    const req = requestWithCookies("http://localhost/login?next=%2Fp%2Fproj-1", {
      [ACCESS_TOKEN_COOKIE]: valid,
    });
    const res = middleware(req);

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/p/proj-1");
  });

  it("keeps login accessible but clears expired cookies", () => {
    const expired = makeJwt(Math.floor(Date.now() / 1000) - 60);
    const req = requestWithCookies("http://localhost/login", {
      [ACCESS_TOKEN_COOKIE]: expired,
    });
    const res = middleware(req);

    expect(res.headers.get("location")).toBeNull();
    const setCookie = res.headers.get("set-cookie") ?? "";
    expect(setCookie).toContain(`${ACCESS_TOKEN_COOKIE}=`);
  });

  it("treats JWT without exp as unusable and redirects", () => {
    const noExpToken = makeJwtWithoutExp();
    const req = requestWithCookies("http://localhost/projects", {
      [ACCESS_TOKEN_COOKIE]: noExpToken,
    });
    const res = middleware(req);

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/login?next=%2Fprojects");
  });
});
