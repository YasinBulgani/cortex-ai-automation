import { NextResponse } from "next/server";
import { parseServicesBody, runServiceAction } from "@/lib/dev-services";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}));
    const status = await runServiceAction("stop", parseServicesBody(body));
    return NextResponse.json({ action: "stop", ...status, ok: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Servisler durdurulamadı.";
    const status = message.includes("local/dev") ? 403 : 500;
    return NextResponse.json({ ok: false, error: message }, { status });
  }
}
