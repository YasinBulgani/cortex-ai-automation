"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { type CoreServiceStatus, useCoreRuntime } from "@/lib/core-runtime";

type PendingAction = {
  action: "start" | "restart" | "stop";
  services: string[];
} | null;

const ACTION_LABEL: Record<NonNullable<PendingAction>["action"], string> = {
  start: "Başlat",
  restart: "Yeniden başlat",
  stop: "Durdur",
};

const STATE_LABEL: Record<CoreServiceStatus["state"], string> = {
  running: "Çalışıyor",
  starting: "Başlıyor",
  stopped: "Durdu",
  unhealthy: "Sağlıksız",
  unknown: "Bilinmiyor",
};

const STATE_CLASS: Record<CoreServiceStatus["state"], string> = {
  running: "border-emerald-400/20 bg-emerald-500/10 text-emerald-200",
  starting: "border-blue-400/20 bg-blue-500/10 text-blue-200",
  stopped: "border-slate-700 bg-slate-900/70 text-slate-300",
  unhealthy: "border-amber-400/20 bg-amber-500/10 text-amber-200",
  unknown: "border-red-400/20 bg-red-500/10 text-red-200",
};

export default function SystemServicesPage() {
  const runtime = useCoreRuntime();
  const [pending, setPending] = useState<PendingAction>(null);
  const [runningAction, setRunningAction] = useState(false);
  const [lastAction, setLastAction] = useState<string | null>(null);

  const serviceNames = useMemo(
    () => runtime.services.map((service) => service.name),
    [runtime.services],
  );

  useEffect(() => {
    if (!runtime.loading && runtime.services.length === 0) void runtime.refresh();
  }, [runtime]);

  const runAction = async () => {
    if (!pending) return;
    setRunningAction(true);
    setLastAction(null);
    try {
      const response = await fetch(`/api/dev/services/${pending.action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ services: pending.services }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.error || "Servis aksiyonu tamamlanamadı.");
      }
      setLastAction(`${ACTION_LABEL[pending.action]} tamamlandı: ${pending.services.join(", ")}`);
      setPending(null);
      await runtime.refresh();
    } catch (error) {
      setLastAction(error instanceof Error ? error.message : "Servis aksiyonu tamamlanamadı.");
    } finally {
      setRunningAction(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100">
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="flex flex-col gap-4 border-b border-slate-800 pb-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-300/80">Runtime Çekirdeği</p>
            <h1 className="mt-2 text-4xl font-black tracking-tight text-white">System Services</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-400">
              Neurex QA servis omurgasını Docker Compose üzerinden izleyin ve local/dev ortamda kontrollü şekilde yönetin.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void runtime.refresh()}
              className="rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-500"
            >
              Yenile
            </button>
            <Link
              href="/products/one"
              className="rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-500"
            >
              Ürün sayfasına dön
            </Link>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Backend</p>
            <p className={`mt-2 text-lg font-semibold ${runtime.backendReady ? "text-emerald-200" : "text-amber-200"}`}>
              {runtime.backendReady ? "Hazır" : "Hazır değil"}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Son kontrol</p>
            <p className="mt-2 text-lg font-semibold text-white">{runtime.checkedAt ? new Date(runtime.checkedAt).toLocaleTimeString("tr-TR") : "—"}</p>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Servis sayısı</p>
            <p className="mt-2 text-lg font-semibold text-white">{runtime.services.length}</p>
          </div>
        </section>

        {runtime.error && (
          <div className="rounded-2xl border border-amber-400/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            {runtime.error}
          </div>
        )}

        <section className="rounded-[28px] border border-slate-800 bg-slate-950/70 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-semibold text-white">Servisler</h2>
            <div className="flex flex-wrap gap-2">
              <button onClick={() => setPending({ action: "start", services: serviceNames })} className="rounded-xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-100">Start all</button>
              <button onClick={() => setPending({ action: "restart", services: serviceNames })} className="rounded-xl border border-blue-400/20 bg-blue-500/10 px-4 py-2 text-sm font-semibold text-blue-100">Restart all</button>
              <button onClick={() => setPending({ action: "stop", services: serviceNames })} className="rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-2 text-sm font-semibold text-red-100">Stop all</button>
            </div>
          </div>

          <div className="mt-5 grid gap-3 lg:grid-cols-2">
            {runtime.services.map((service) => (
              <div key={service.name} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-semibold text-white">{service.name}</h3>
                    <p className="mt-1 text-xs text-slate-500">{service.healthUrl ?? "Docker service"}</p>
                  </div>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${STATE_CLASS[service.state]}`}>
                    {STATE_LABEL[service.state]}
                  </span>
                </div>
                <p className="mt-3 text-sm text-slate-400">Health: {service.healthDetail}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button onClick={() => setPending({ action: "start", services: [service.name] })} className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200">Start</button>
                  <button onClick={() => setPending({ action: "restart", services: [service.name] })} className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200">Restart</button>
                  <button onClick={() => setPending({ action: "stop", services: [service.name] })} className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200">Stop</button>
                </div>
              </div>
            ))}
          </div>
        </section>

        {lastAction && (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-200">
            {lastAction}
          </div>
        )}
      </main>

      {pending && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
          <div className="w-full max-w-lg rounded-[28px] border border-slate-800 bg-slate-950 p-6 shadow-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-amber-200/80">Onay gerekli</p>
            <h2 className="mt-2 text-2xl font-bold text-white">{ACTION_LABEL[pending.action]} işlemini onayla</h2>
            <p className="mt-3 text-sm leading-7 text-slate-400">
              Bu işlem local Docker Compose üzerinden şu servisleri etkileyecek: {pending.services.join(", ")}.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button disabled={runningAction} onClick={() => setPending(null)} className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-200">Vazgeç</button>
              <button disabled={runningAction} onClick={() => void runAction()} className="rounded-xl border border-violet-300/30 bg-violet-500/15 px-4 py-2 text-sm font-semibold text-violet-50">
                {runningAction ? "Çalışıyor..." : "Onayla"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
