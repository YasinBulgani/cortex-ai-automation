import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export const SERVICE_NAMES = [
  "postgres",
  "redis",
  "backend",
  "worker",
  "engine",
  "ai-gateway",
] as const;

export type ServiceName = (typeof SERVICE_NAMES)[number];
export type ServiceAction = "start" | "restart" | "stop";
export type ServiceState = "running" | "starting" | "stopped" | "unhealthy" | "unknown";

type ComposeCommand = {
  binary: string;
  baseArgs: string[];
  label: string;
};

type HealthCheck = {
  service: ServiceName;
  url: string;
  validator?: (payload: unknown) => boolean;
};

export type ServiceStatus = {
  name: ServiceName;
  state: ServiceState;
  running: boolean;
  healthUrl?: string;
  healthOk: boolean | null;
  healthDetail: string;
};

export type ServicesStatusResponse = {
  ok: boolean;
  compose: { available: boolean; label: string | null; error?: string };
  checkedAt: string;
  backendReady: boolean;
  services: ServiceStatus[];
};

const PROJECT_ROOT = path.resolve(process.cwd(), "..", "..");
const RUN_TIMEOUT_MS = 120_000;
const HEALTH_TIMEOUT_MS = 2500;

const BACKEND_VALIDATOR = (payload: unknown) =>
  typeof payload === "object" &&
  payload !== null &&
  "ready" in payload &&
  (payload as { ready?: boolean }).ready === true;

const HEALTH_CHECKS: HealthCheck[] = [
  {
    service: "backend",
    url: "http://127.0.0.1:8000/ready",
    validator: BACKEND_VALIDATOR,
  },
  { service: "engine", url: "http://127.0.0.1:5001/health" },
  { service: "ai-gateway", url: "http://127.0.0.1:8080/ping" },
];

// Fallback health checks using Docker-network hostnames for containerised deployments
// where docker-compose is not available inside the container.
const FALLBACK_HEALTH_CHECKS: HealthCheck[] = [
  { service: "backend", url: "http://backend:8000/ready", validator: BACKEND_VALIDATOR },
  { service: "engine", url: "http://engine:5001/health" },
  { service: "ai-gateway", url: "http://ai-gateway:8080/ping" },
];

const HEALTH_BY_SERVICE = new Map(HEALTH_CHECKS.map((check) => [check.service, check]));

function ensureServiceNames(input?: unknown): ServiceName[] {
  if (!Array.isArray(input) || input.length === 0) return [...SERVICE_NAMES];
  const requested = input.map((item) => String(item));
  const invalid = requested.filter((item) => !SERVICE_NAMES.includes(item as ServiceName));
  if (invalid.length) {
    throw new Error(`Bilinmeyen servis: ${invalid.join(", ")}`);
  }
  return [...new Set(requested)] as ServiceName[];
}

export function parseServicesBody(body: unknown): ServiceName[] {
  if (!body || typeof body !== "object") return [...SERVICE_NAMES];
  return ensureServiceNames((body as { services?: unknown }).services);
}

export function ensureMutationEnabled() {
  if (process.env.NODE_ENV !== "production") return;
  if (process.env.ENABLE_DEV_SERVICE_CONTROL === "true") return;
  throw new Error("Servis aksiyonları yalnızca local/dev ortamında açık.");
}

async function runCommand(binary: string, args: string[], cwd: string) {
  return execFileAsync(binary, args, {
    cwd,
    timeout: RUN_TIMEOUT_MS,
    maxBuffer: 1024 * 1024,
  });
}

async function detectCompose(): Promise<ComposeCommand> {
  const candidates: ComposeCommand[] = [
    { binary: "docker", baseArgs: ["compose"], label: "docker compose" },
    { binary: "docker-compose", baseArgs: [], label: "docker-compose" },
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

  const message = lastError instanceof Error ? lastError.message : "Docker Compose bulunamadı.";
  throw new Error(message);
}

async function composeExec(compose: ComposeCommand, args: string[]) {
  return runCommand(compose.binary, [...compose.baseArgs, ...args], PROJECT_ROOT);
}

async function getRunningServices(compose: ComposeCommand): Promise<Set<ServiceName>> {
  try {
    const { stdout } = await composeExec(compose, ["ps", "--services", "--filter", "status=running"]);
    return new Set(
      stdout
        .split("\n")
        .map((line) => line.trim())
        .filter((line): line is ServiceName => SERVICE_NAMES.includes(line as ServiceName)),
    );
  } catch {
    return new Set();
  }
}

async function checkHealth(check: HealthCheck): Promise<{ ok: boolean; detail: string }> {
  try {
    const response = await fetch(check.url, {
      cache: "no-store",
      signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
    });
    if (!response.ok) return { ok: false, detail: `HTTP ${response.status}` };
    if (!check.validator) return { ok: true, detail: "ok" };
    const payload = (await response.json()) as unknown;
    return check.validator(payload) ? { ok: true, detail: "ok" } : { ok: false, detail: "not ready" };
  } catch (error) {
    return { ok: false, detail: error instanceof Error ? error.message : "health check failed" };
  }
}

export async function getServicesStatus(): Promise<ServicesStatusResponse> {
  const checkedAt = new Date().toISOString();
  let compose: ComposeCommand;
  try {
    compose = await detectCompose();
  } catch (error) {
    // Docker Compose unavailable (e.g. containerised production) — fall back to direct health checks.
    const fallbackByService = new Map(FALLBACK_HEALTH_CHECKS.map((c) => [c.service, c]));
    const fallbackResults = new Map<ServiceName, { ok: boolean; detail: string }>();
    await Promise.all(
      FALLBACK_HEALTH_CHECKS.map(async (check) => {
        fallbackResults.set(check.service, await checkHealth(check));
      }),
    );

    const backendOk = fallbackResults.get("backend")?.ok ?? false;
    return {
      ok: backendOk,
      compose: {
        available: false,
        label: null,
        error: error instanceof Error ? error.message : "Docker Compose bulunamadı.",
      },
      checkedAt,
      backendReady: backendOk,
      services: SERVICE_NAMES.map((name) => {
        const check = fallbackByService.get(name);
        const result = fallbackResults.get(name);
        return {
          name,
          state: result?.ok ? "running" : "unknown",
          running: result?.ok ?? false,
          healthUrl: check?.url,
          healthOk: result?.ok ?? null,
          healthDetail: result?.detail ?? "compose unavailable",
        };
      }),
    };
  }

  const running = await getRunningServices(compose);
  const healthResults = new Map<ServiceName, { ok: boolean; detail: string }>();
  await Promise.all(
    HEALTH_CHECKS.map(async (check) => {
      healthResults.set(check.service, await checkHealth(check));
    }),
  );

  const services = SERVICE_NAMES.map<ServiceStatus>((name) => {
    const isRunning = running.has(name);
    const health = HEALTH_BY_SERVICE.get(name);
    const healthResult = healthResults.get(name);
    const healthOk = health ? healthResult?.ok ?? false : null;
    const state: ServiceState = !isRunning
      ? "stopped"
      : health && healthOk === false
        ? "unhealthy"
        : "running";
    return {
      name,
      state,
      running: isRunning,
      healthUrl: health?.url,
      healthOk,
      healthDetail: health ? healthResult?.detail ?? "unknown" : "not applicable",
    };
  });

  return {
    ok: true,
    compose: { available: true, label: compose.label },
    checkedAt,
    backendReady: services.find((service) => service.name === "backend")?.healthOk === true,
    services,
  };
}

async function wait(ms: number) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForAffectedHealth(services: ServiceName[]) {
  const checks = services
    .map((service) => HEALTH_BY_SERVICE.get(service))
    .filter((check): check is HealthCheck => Boolean(check));

  for (const check of checks) {
    for (let attempt = 0; attempt < 30; attempt += 1) {
      const result = await checkHealth(check);
      if (result.ok) break;
      if (attempt === 29) {
        throw new Error(`${check.service} sağlık kontrolünden geçemedi: ${result.detail}`);
      }
      await wait(1000);
    }
  }
}

export async function runServiceAction(action: ServiceAction, services: ServiceName[]) {
  ensureMutationEnabled();
  const compose = await detectCompose();
  if (action === "start") {
    await composeExec(compose, ["up", "-d", ...services]);
    await waitForAffectedHealth(services);
  } else if (action === "restart") {
    await composeExec(compose, ["restart", ...services]);
    await waitForAffectedHealth(services);
  } else if (action === "stop") {
    await composeExec(compose, ["stop", ...services]);
  } else {
    throw new Error(`Bilinmeyen servis aksiyonu: ${action}`);
  }

  return getServicesStatus();
}
