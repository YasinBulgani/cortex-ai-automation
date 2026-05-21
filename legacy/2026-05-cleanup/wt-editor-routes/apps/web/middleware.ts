import { NextResponse, type NextRequest } from "next/server";
import { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE } from "@/lib/auth-cookies";

const LOGIN_PATH = "/login";
const DEFAULT_AUTHENTICATED_PATH = "/projects";
const PUBLIC_PATH_PREFIXES = [
  LOGIN_PATH,
  "/reset-password",
];

function isPublicPath(pathname: string) {
  return PUBLIC_PATH_PREFIXES.some((prefix) =>
    pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

function decodeBase64Url(input: string): string {
  const padded = input.replace(/-/g, "+").replace(/_/g, "/");
  const base64 = `${padded}${"=".repeat((4 - (padded.length % 4)) % 4)}`;
  if (typeof atob !== "function") return "";
  return atob(base64);
}

function decodeJwtPayload(token: string): { exp?: number } | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const parsed = JSON.parse(decodeBase64Url(parts[1])) as { exp?: number };
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

function isUsableJwt(token: string | undefined): boolean {
  if (!token) return false;
  const payload = decodeJwtPayload(token);
  if (!payload) return false;
  if (typeof payload.exp !== "number") return false;
  return payload.exp * 1000 > Date.now() + 5_000;
}

function getSafeNextPath(candidate: string | null): string {
  if (!candidate) return DEFAULT_AUTHENTICATED_PATH;
  const trimmed = candidate.trim();
  if (!trimmed) return DEFAULT_AUTHENTICATED_PATH;
  if (trimmed === LOGIN_PATH || trimmed.startsWith(`${LOGIN_PATH}/`)) return DEFAULT_AUTHENTICATED_PATH;
  if (!trimmed.startsWith("/") || trimmed.startsWith("//")) {
    return DEFAULT_AUTHENTICATED_PATH;
  }
  if (trimmed.includes("\\") || trimmed.includes("\r") || trimmed.includes("\n")) {
    return DEFAULT_AUTHENTICATED_PATH;
  }
  return trimmed;
}

function clearAuthCookies(response: NextResponse) {
  response.cookies.delete({ name: ACCESS_TOKEN_COOKIE, path: "/" });
  response.cookies.delete({ name: REFRESH_TOKEN_COOKIE, path: "/" });
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value;
  const hasAnySessionCookie = Boolean(accessToken) || Boolean(refreshToken);
  const hasUsableSession = isUsableJwt(accessToken) || isUsableJwt(refreshToken);

  if (!isPublicPath(pathname) && !hasUsableSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
    const response = NextResponse.redirect(loginUrl);
    if (hasAnySessionCookie) clearAuthCookies(response);
    return response;
  }

  if (pathname === LOGIN_PATH && hasUsableSession) {
    const nextPath = getSafeNextPath(request.nextUrl.searchParams.get("next"));
    return NextResponse.redirect(new URL(nextPath, request.url));
  }

  // Expired/invalid cookies on public pages can trap users in login loops.
  if (isPublicPath(pathname) && hasAnySessionCookie && !hasUsableSession) {
    const response = NextResponse.next();
    clearAuthCookies(response);
    return response;
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
