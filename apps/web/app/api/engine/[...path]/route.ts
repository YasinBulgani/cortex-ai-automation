import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = {
  params: { path?: string[] };
};

const ENGINE_BASE = (
  process.env.ENGINE_BASE_URL ||
  process.env.NEXT_PUBLIC_ENGINE_BASE ||
  "http://127.0.0.1:5001"
).replace(/\/$/, "");

function engineKey(): string {
  return process.env.ENGINE_INTERNAL_KEY || "";
}

function targetUrl(request: NextRequest, path: string[]): string {
  // The engine routes live under /api/<segment>/...; we forward "<segment>/..."
  // received from the client as the Engine path verbatim.
  const route = path.map((p) => encodeURIComponent(p)).join("/");
  return `${ENGINE_BASE}/api/${route}${request.nextUrl.search}`;
}

async function proxy(request: NextRequest, context: RouteContext): Promise<Response> {
  const path = context.params.path ?? [];
  if (path.length === 0) {
    return Response.json({ detail: "Engine route path is required" }, { status: 404 });
  }

  const key = engineKey();
  if (!key) {
    return Response.json(
      { detail: "ENGINE_INTERNAL_KEY ortam değişkeni tanımlı değil" },
      { status: 503 },
    );
  }

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  const accept = request.headers.get("accept");
  if (contentType) headers.set("Content-Type", contentType);
  if (accept) headers.set("Accept", accept);
  headers.set("X-Internal-Key", key);

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  let upstream: Response;
  try {
    upstream = await fetch(targetUrl(request, path), init);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Engine bağlantı hatası";
    return Response.json(
      { detail: `Engine'e ulaşılamadı (${ENGINE_BASE}): ${message}` },
      { status: 502 },
    );
  }

  // Forward content-type and any cache-control verbatim
  const respHeaders = new Headers();
  const upCT = upstream.headers.get("content-type");
  const upCC = upstream.headers.get("cache-control");
  if (upCT) respHeaders.set("Content-Type", upCT);
  if (upCC) respHeaders.set("Cache-Control", upCC);
  respHeaders.set("X-Engine-Proxy", "next");

  if (upstream.status === 204) {
    return new Response(null, { status: 204, headers: respHeaders });
  }

  // Use stream when available (Engine SSE / file downloads)
  if (upstream.body) {
    return new Response(upstream.body, { status: upstream.status, headers: respHeaders });
  }

  const text = await upstream.text();
  return new Response(text, { status: upstream.status, headers: respHeaders });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
