import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import { NextResponse } from "next/server";

const execFileAsync = promisify(execFile);

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const SERVICES = [
  "postgres",
  "redis",
  "ai-gateway",
  "engine",
  "backend",
  "worker",
] as const;

const PROJECT_ROOT = path.resolve(process.cwd(), "..", "..");

type ComposeCommand = {
  binary: string;
  baseArgs: string[];
  label: string;
};

type HealthCheck = {
  name: string;
  url: string;
  validator?: (payload: unknown) => boolean;
};

const HEALTH_CHECKS: HealthCheck[] = [
  {
    name: "Backend",
    url: "http://127.0.0.1:8000/ready",
    validator: (payload) =>
      typeof payload === "object" &&
      payload !== null &&
      "ready" in payload &&
      (payload as { ready?: boolean }).ready === true,
  },
  {
    name: "Engine",
    url: "http://127.0.0.1:5001/health",
  },
  {
    name: "AI Gateway",
    url: "http://127.0.0.1:8080/ping",
  },
];

function ensureEnabled() {
  if (process.env.NODE_ENV !== "production") return true;
  return process.env.ENABLE_DEV_RESTART === "true";
}

async function runCommand(
  binary: string,
  args: string[],
  cwd: string
): Promise<{ stdout: string; stderr: string }> {
  return execFileAsync(binary, args, {
    cwd,
    timeout: 120_000,
    maxBuffer: 1024 * 1024,
  });
}

async function detectCompose(): Promise<ComposeCommand> {
  const candidates: ComposeCommand[] = [
    { binary: "docker-compose", baseArgs: [], label: "docker-compose" },
    { binary: "docker", baseArgs: ["compose"], label: "docker compose" },
  ];

  let lastError: unknown;
  for (const candidate of candidates) {
    try {
      await runCommand(candidate.binary, [...candidate.baseArgs, "version"], PROJECT_ROOT);
      return candidate;
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError instanceof Error
    ? lastError
    : new Error("Docker Compose bulunamadı.");
}

async function composeExec(
  compose: ComposeCommand,
  args: string[]
): Promise<{ stdout: string; stderr: string }> {
  return runCommand(compose.binary, [...compose.baseArgs, ...args], PROJECT_ROOT);
}

async function shouldRestart(compose: ComposeCommand): Promise<boolean> {
  try {
    const { stdout } = await composeExec(compose, ["ps", "--services"]);
    const activeServices = new Set(
      stdout
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
    );
    return SERVICES.every((service) => activeServices.has(service));
  } catch {
    return false;
  }
}

async function wait(ms: number) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForHealth(check: HealthCheck): Promise<void> {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try {
      const response = await fetch(check.url, { cache: "no-store" });
      if (response.ok) {
        if (!check.validator) return;

        const payload = (await response.json()) as unknown;
        if (check.validator(payload)) return;
      }
    } catch {
      // Service may still be starting.
    }
    await wait(1000);
  }

  throw new Error(`${check.name} sağlık kontrolünden geçemedi.`);
}

export async function POST() {
  if (!ensureEnabled()) {
    return NextResponse.json(
      {
        ok: false,
        error: "Servis yeniden başlatma yalnızca local/dev ortamında açık.",
      },
      { status: 403 }
    );
  }

  try {
    const compose = await detectCompose();
    const restartMode = (await shouldRestart(compose)) ? "restart" : "up";

    if (restartMode === "restart") {
      await composeExec(compose, ["restart", ...SERVICES]);
    } else {
      await composeExec(compose, ["up", "-d", ...SERVICES]);
    }

    for (const healthCheck of HEALTH_CHECKS) {
      await waitForHealth(healthCheck);
    }

    return NextResponse.json({
      ok: true,
      mode: restartMode,
      services: SERVICES,
      message:
        restartMode === "restart"
          ? "Docker servisleri yeniden başlatıldı ve sağlık kontrolleri geçti."
          : "Docker servisleri ayağa kaldırıldı ve sağlık kontrolleri geçti.",
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Servisler yeniden başlatılamadı.";

    return NextResponse.json(
      {
        ok: false,
        error: message,
      },
      { status: 500 }
    );
  }
}
