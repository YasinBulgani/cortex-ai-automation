import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = {
  params: {
    path?: string[];
  };
};

const GATEWAY_BASE = (
  process.env.AI_GATEWAY_BASE_URL ||
  process.env.NEXT_PUBLIC_AI_GATEWAY_BASE ||
  "http://127.0.0.1:8080"
).replace(/\/$/, "");
const BACKEND_BASE = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE ||
  "http://127.0.0.1:8765"
).replace(/\/$/, "");
const MAX_AI_PROXY_BODY_BYTES = Number(process.env.AI_PROXY_MAX_BODY_BYTES || 1024 * 1024);
const AI_PROXY_PERMISSIONS = (
  process.env.AI_PROXY_REQUIRED_PERMISSIONS ||
  "admin.*,ai.gateway.use,ai.workflows.admin"
)
  .split(",")
  .map((item) => item.trim())
  .filter(Boolean);

function gatewayInternalKey(): string {
  return (
    process.env.GATEWAY_INTERNAL_KEY ||
    // Backward compatibility for older local env files. This stays server-side.
    process.env.NEXT_PUBLIC_GATEWAY_KEY ||
    ""
  );
}

type CurrentUser = {
  id?: string;
  email?: string;
  permissions?: string[];
  roles?: string[];
  tenant_id?: string;
};

function requiresInternalKey(path: string[]): boolean {
  const route = path.join("/");
  return (
    route === "complete" ||
    route === "stream" ||
    route === "pipeline" ||
    route === "embed" ||
    route.startsWith("embed/")
  );
}

function isMutatingGatewayRoute(path: string[]): boolean {
  const route = path.join("/");
  return route === "complete" || route === "stream" || route === "pipeline" || route === "embed";
}

function gatewayUrl(request: NextRequest, path: string[]): string {
  const route = path.map((part) => encodeURIComponent(part)).join("/");
  return `${GATEWAY_BASE}/ai/${route}${request.nextUrl.search}`;
}

function responseHeaders(upstream: Response, path: string[]): Headers {
  const headers = new Headers();
  const contentType = upstream.headers.get("content-type");
  const cacheControl = upstream.headers.get("cache-control");
  if (contentType) headers.set("Content-Type", contentType);
  if (cacheControl) headers.set("Cache-Control", cacheControl);
  if (path[0] === "stream" || contentType?.includes("text/event-stream")) {
    headers.set("Cache-Control", "no-cache");
    headers.set("X-Accel-Buffering", "no");
  }
  headers.set("X-AI-Gateway-Proxy", "next");
  return headers;
}

function requestAuthHeaders(request: NextRequest): Headers {
  const headers = new Headers();
  const authorization = request.headers.get("authorization");
  const cookie = request.headers.get("cookie");
  if (authorization) headers.set("Authorization", authorization);
  if (cookie) headers.set("Cookie", cookie);
  return headers;
}

function hasGatewayPermission(user: CurrentUser): boolean {
  const permissions = user.permissions || [];
  return AI_PROXY_PERMISSIONS.some((permission) => permissions.includes(permission));
}

async function requireGatewayUser(request: NextRequest, path: string[]): Promise<CurrentUser | Response> {
  const authHeaders = requestAuthHeaders(request);
  if (!authHeaders.has("Authorization") && !authHeaders.has("Cookie")) {
    return Response.json({ detail: "AI Gateway proxy için oturum gerekli" }, { status: 401 });
  }

  let response: Response;
  try {
    response = await fetch(`${BACKEND_BASE}/api/v1/auth/me`, {
      method: "GET",
      headers: authHeaders,
      cache: "no-store",
    });
  } catch (error) {
    return Response.json(
      {
        detail: "Kullanıcı doğrulaması yapılamadı",
        error: error instanceof Error ? error.message : String(error),
      },
      { status: 502 },
    );
  }

  if (!response.ok) {
    return Response.json({ detail: "AI Gateway proxy için geçerli oturum gerekli" }, { status: 401 });
  }

  const user = (await response.json()) as CurrentUser;
  if (isMutatingGatewayRoute(path) && !hasGatewayPermission(user)) {
    return Response.json(
      { detail: "AI Gateway proxy için yetki gerekli", required_permissions: AI_PROXY_PERMISSIONS },
      { status: 403 },
    );
  }
  return user;
}

function enforceBodyLimit(request: NextRequest): Response | null {
  const rawLength = request.headers.get("content-length");
  if (!rawLength) return null;
  const contentLength = Number(rawLength);
  if (Number.isFinite(contentLength) && contentLength > MAX_AI_PROXY_BODY_BYTES) {
    return Response.json(
      {
        detail: "AI Gateway proxy istek boyutu limiti aşıldı",
        max_bytes: MAX_AI_PROXY_BODY_BYTES,
      },
      { status: 413 },
    );
  }
  return null;
}

async function proxyAi(request: NextRequest, context: RouteContext): Promise<Response> {
  const path = context.params.path ?? [];
  if (path.length === 0) {
    return Response.json({ detail: "AI route path is required" }, { status: 404 });
  }

  const bodyLimit = enforceBodyLimit(request);
  if (bodyLimit) return bodyLimit;

  const userOrResponse = await requireGatewayUser(request, path);
  if (userOrResponse instanceof Response) return userOrResponse;
  const user = userOrResponse;

  const needsInternalKey = requiresInternalKey(path);
  const internalKey = gatewayInternalKey();
  if (needsInternalKey && !internalKey) {
    return Response.json(
      { detail: "GATEWAY_INTERNAL_KEY ortam değişkeni tanımlı değil" },
      { status: 503 },
    );
  }

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  const accept = request.headers.get("accept");
  if (contentType) headers.set("Content-Type", contentType);
  if (accept) headers.set("Accept", accept);
  if (needsInternalKey) headers.set("X-Internal-Key", internalKey);
  if (user.id) headers.set("X-Caller-User-Id", String(user.id));
  if (user.email) headers.set("X-Caller-Email", String(user.email));
  if (user.tenant_id) headers.set("X-Tenant-Id", String(user.tenant_id));

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  try {
    const upstream = await fetch(gatewayUrl(request, path), init);
    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders(upstream, path),
    });
  } catch (error) {
    return Response.json(
      {
        detail: "AI Gateway'e bağlanılamadı",
        error: error instanceof Error ? error.message : String(error),
      },
      { status: 502 },
    );
  }
}

export async function GET(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyAi(request, context);
}

export async function POST(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyAi(request, context);
}
