"use client";

import { useEffect, useRef, useState } from "react";
import type { ServiceName } from "@/lib/dev-services";
import {
  CORE_SERVICES,
  getServicesToStart,
  getServicesToStop,
  type ModuleConfig,
} from "./module-service-map";

type ItemPhase = "core" | "idle" | "stopping" | "stopped" | "starting" | "running" | "error";

interface ServiceItem {
  name: ServiceName;
  phase: ItemPhase;
}

const SERVICE_META: Record<string, { icon: string; label: string }> = {
  engine: { icon: "⚙", label: "engine" },
  worker: { icon: "⬡", label: "worker" },
  "ai-gateway": { icon: "◈", label: "ai-gateway" },
  postgres: { icon: "▦", label: "postgres" },
  redis: { icon: "◉", label: "redis" },
  backend: { icon: "▣", label: "backend" },
};

const PHASE_TEXT: Record<ItemPhase, { label: string; color: string }> = {
  core: { label: "çalışıyor", color: "text-emerald-400" },
  idle: { label: "bekliyor…", color: "text-slate-500" },
  stopping: { label: "durduruluyor…", color: "text-amber-400" },
  stopped: { label: "durduruldu", color: "text-slate-600" },
  starting: { label: "başlatılıyor…", color: "text-blue-400" },
  running: { label: "çalışıyor ✓", color: "text-emerald-400" },
  error: { label: "hata ✗", color: "text-red-400" },
};

async function apiCall(action: "start" | "stop", services: ServiceName[]) {
  const res = await fetch(`/api/dev/services/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ services }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

function wait(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
}

interface Props {
  fromModule: ModuleConfig;
  toModule: ModuleConfig;
  onComplete: () => void;
}

export function ServiceLoadingScreen({ fromModule, toModule, onComplete }: Props) {
  const toStop = getServicesToStop(fromModule, toModule);
  const toStart = getServicesToStart(fromModule, toModule);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const initialItems: ServiceItem[] = [
    ...CORE_SERVICES.map((name) => ({ name, phase: "core" as ItemPhase })),
    ...toStop.map((name) => ({ name, phase: "idle" as ItemPhase })),
    ...toStart.filter((s) => !toStop.includes(s)).map((name) => ({ name, phase: "idle" as ItemPhase })),
  ];

  const [items, setItems] = useState<ServiceItem[]>(initialItems);
  const setPhase = (names: ServiceName[], phase: ItemPhase) =>
    setItems((prev) => prev.map((item) => (names.includes(item.name) ? { ...item, phase } : item)));

  const doneRef = useRef(false);

  // Elapsed timer — shows "bu biraz sürüyor…" after 8s
  useEffect(() => {
    const id = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      try {
        if (toStop.length > 0) {
          setPhase(toStop, "stopping");
          await apiCall("stop", toStop);
          if (cancelled) return;
          setPhase(toStop, "stopped");
          await wait(400);
        }

        if (cancelled) return;

        if (toStart.length > 0) {
          // Stagger the "starting" visual one by one
          for (const svc of toStart) {
            if (cancelled) return;
            setPhase([svc], "starting");
            await wait(250);
          }
          await apiCall("start", toStart);
          if (cancelled) return;
          setPhase(toStart, "running");
        }

        await wait(600);
        if (!cancelled) {
          doneRef.current = true;
          setDone(true);
        }
      } catch (err) {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : "Bilinmeyen hata";
          setError(msg);
          const affected = [...toStop, ...toStart];
          setPhase(affected, "error");
        }
      }
    }

    run();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-dismiss 2 s after completion
  useEffect(() => {
    if (!done) return;
    const id = setTimeout(onComplete, 2000);
    return () => clearTimeout(id);
  }, [done, onComplete]);

  const moduleItems = items.filter((i) => i.phase !== "core");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/95 backdrop-blur-sm">
      <div className="w-full max-w-md">
        {/* macOS-style terminal chrome */}
        <div className="flex items-center gap-1.5 rounded-t-xl border border-b-0 border-slate-700 bg-slate-800 px-4 py-3">
          <span className="h-3 w-3 rounded-full bg-red-500/80" />
          <span className="h-3 w-3 rounded-full bg-amber-500/80" />
          <span className="h-3 w-3 rounded-full bg-emerald-500/80" />
          <span className="ml-3 font-mono text-xs text-slate-400">
            neurex — service orchestrator
          </span>
        </div>

        {/* Terminal body */}
        <div className="min-h-48 rounded-b-xl border border-t-0 border-slate-700 bg-slate-900 px-6 py-5">
          {/* Command line */}
          <p className="mb-5 font-mono text-sm text-emerald-400">
            <span className="text-slate-500">$</span>{" "}
            <span className="text-slate-300">neurex</span> switch{" "}
            <span className="text-white">{fromModule.key}</span>
            <span className="text-slate-500"> → </span>
            <span className="text-white">{toModule.key}</span>
          </p>

          {/* Core services */}
          <div className="mb-4 space-y-1.5">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-slate-600">
              # core (her zaman çalışır)
            </p>
            {items
              .filter((i) => i.phase === "core")
              .map((item) => (
                <ServiceRow key={item.name} item={item} />
              ))}
          </div>

          {/* Module-specific services */}
          {moduleItems.length > 0 && (
            <div className="mb-4 space-y-1.5">
              <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-slate-600">
                # modül servisleri
              </p>
              {moduleItems.map((item) => (
                <ServiceRow key={item.name} item={item} />
              ))}
            </div>
          )}

          {/* Status / slow warning */}
          {!done && !error && elapsed >= 8 && (
            <p className="mt-3 font-mono text-xs text-amber-400/70">
              ⏳ Bu biraz sürüyor, lütfen bekleyin…
            </p>
          )}

          {/* Error */}
          {error && (
            <div className="mt-3">
              <p className="font-mono text-xs text-red-400">✗ Hata: {error}</p>
              <button
                type="button"
                onClick={onComplete}
                className="mt-3 rounded-md bg-slate-800 px-3 py-1.5 font-mono text-xs text-slate-300 hover:bg-slate-700"
              >
                Yine de devam et →
              </button>
            </div>
          )}

          {/* Done */}
          {done && (
            <p className="mt-3 font-mono text-sm text-emerald-400 animate-pulse">
              ✓ {toModule.label} modülü hazır.
            </p>
          )}
        </div>

        {/* Footer bar */}
        <div className="mt-2 flex items-center justify-between px-1">
          <span className="font-mono text-[10px] text-slate-600">
            {done ? "tüm servisler hazır" : error ? "bir hata oluştu" : "yapılandırılıyor…"}
          </span>
          {(done || error) && (
            <button
              type="button"
              onClick={onComplete}
              className="rounded-md bg-emerald-700/80 px-3 py-1 font-mono text-xs font-semibold text-white transition-colors hover:bg-emerald-600"
            >
              Devam et →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ServiceRow({ item }: { item: ServiceItem }) {
  const meta = SERVICE_META[item.name] ?? { icon: "○", label: item.name };
  const { label, color } = PHASE_TEXT[item.phase];
  const dotColor =
    item.phase === "running" || item.phase === "core"
      ? "text-emerald-400"
      : item.phase === "stopping" || item.phase === "starting"
        ? "text-amber-400"
        : item.phase === "error"
          ? "text-red-400"
          : "text-slate-600";

  return (
    <div className="flex items-center gap-3 font-mono text-sm">
      <span className={`w-4 text-center ${dotColor}`}>{meta.icon}</span>
      <span className="w-20 text-slate-300">{meta.label}</span>
      <span className="text-slate-600">──</span>
      <span className={color}>{label}</span>
    </div>
  );
}
