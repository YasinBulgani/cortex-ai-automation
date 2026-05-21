import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const execFileAsync = promisify(execFile);

export type PM2ProcessStatus = "online" | "stopping" | "stopped" | "launching" | "errored" | "one-launch-status" | "unknown";

export type PM2Process = {
  name: string;
  pid: number | null;
  status: PM2ProcessStatus;
  cpu: number;
  memory: number;     // bytes
  restarts: number;
  uptime: number | null; // ms
};

export type PM2StatusResponse = {
  available: boolean;
  error?: string;
  processes: PM2Process[];
};

// PM2 binary yolları (global kurulum)
const PM2_CANDIDATES = [
  "/opt/homebrew/bin/pm2",
  "/usr/local/bin/pm2",
  `${process.env.HOME}/.npm-global/bin/pm2`,
  "pm2",
];

async function findPM2(): Promise<string> {
  for (const bin of PM2_CANDIDATES) {
    try {
      await execFileAsync(bin, ["--version"], { timeout: 3000 });
      return bin;
    } catch {
      continue;
    }
  }
  throw new Error("PM2 bulunamadı");
}

async function getPM2Status(): Promise<PM2StatusResponse> {
  let pm2: string;
  try {
    pm2 = await findPM2();
  } catch {
    return { available: false, error: "PM2 kurulu değil", processes: [] };
  }

  try {
    const { stdout } = await execFileAsync(pm2, ["jlist"], { timeout: 8000 });
    const raw = JSON.parse(stdout) as Array<Record<string, unknown>>;

    const processes: PM2Process[] = raw
      .filter((p) => {
        const name = p.name as string | undefined;
        return name?.startsWith("neurex-");
      })
      .map((p) => {
        const monit = (p.monit ?? {}) as Record<string, number>;
        const pm2Env = (p.pm2_env ?? {}) as Record<string, unknown>;
        return {
          name: p.name as string,
          pid: (p.pid as number) || null,
          status: (pm2Env.status as PM2ProcessStatus) ?? "unknown",
          cpu: monit.cpu ?? 0,
          memory: monit.memory ?? 0,
          restarts: (pm2Env.restart_time as number) ?? 0,
          uptime: (pm2Env.pm_uptime as number) ?? null,
        };
      });

    return { available: true, processes };
  } catch (err) {
    return {
      available: true,
      error: err instanceof Error ? err.message : "PM2 listesi alınamadı",
      processes: [],
    };
  }
}

export async function GET() {
  const result = await getPM2Status();
  return NextResponse.json(result, { status: 200 });
}

// POST: start / stop / restart
export async function POST(request: Request) {
  try {
    const body = (await request.json().catch(() => ({}))) as {
      action?: string;
      name?: string;
    };

    const { action, name } = body;
    if (!action || !name) {
      return NextResponse.json({ ok: false, error: "action ve name gerekli" }, { status: 400 });
    }
    if (!["start", "stop", "restart", "delete"].includes(action)) {
      return NextResponse.json({ ok: false, error: "Geçersiz aksiyon" }, { status: 400 });
    }
    // Güvenlik: sadece neurex- prefix'li servislere izin ver
    if (!name.startsWith("neurex-")) {
      return NextResponse.json({ ok: false, error: "Sadece neurex- servisleri yönetilebilir" }, { status: 403 });
    }

    const pm2 = await findPM2();
    await execFileAsync(pm2, [action, name], { timeout: 30_000 });

    // Güncel listeyi dön
    const status = await getPM2Status();
    return NextResponse.json({ ok: true, ...status });
  } catch (err) {
    return NextResponse.json(
      { ok: false, error: err instanceof Error ? err.message : "İşlem başarısız" },
      { status: 500 },
    );
  }
}
