import { NextResponse } from "next/server";
import { getServicesStatus } from "@/lib/dev-services";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const status = await getServicesStatus();
  return NextResponse.json(status, { status: status.ok ? 200 : 503 });
}
