import { NextResponse } from "next/server";
import { runServiceAction, SERVICE_NAMES } from "@/lib/dev-services";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST() {
  try {
    const status = await runServiceAction("restart", [...SERVICE_NAMES]);
    return NextResponse.json({
      ok: true,
      mode: "restart",
      services: SERVICE_NAMES,
      message: "Docker servisleri yeniden başlatıldı ve sağlık kontrolleri geçti.",
      status,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Servisler yeniden başlatılamadı.";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
