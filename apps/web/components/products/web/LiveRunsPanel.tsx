"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useToast } from "@/components/ui/toast";

interface RunningTest {
  id: string;
  scenario: string;
  browser: string;
  startedBy: string;
  startedAt: number; // epoch ms
  totalSteps: number;
  doneSteps: number;
}

interface LastFailure {
  id: string;
  scenario: string;
  browser: string;
  failedAt: string;
  errorType: string;
  errorMessage: string;
  failedStep: string;
  traceUrl?: string;
}

function makeDemoRunning(now: number): RunningTest[] {
  return [
    { id: "r1", scenario: "Checkout · happy path",  browser: "Chrome 124",  startedBy: "Can A.",     startedAt: now - 47_000,  totalSteps: 18, doneSteps: 11 },
    { id: "r2", scenario: "Login · invalid creds",   browser: "Firefox 125", startedBy: "CI pipeline", startedAt: now - 12_000,  totalSteps: 8,  doneSteps: 3  },
    { id: "r3", scenario: "Profile · avatar upload", browser: "Safari 17.4", startedBy: "Selin K.",    startedAt: now - 124_000, totalSteps: 24, doneSteps: 22 },
  ];
}

const DEMO_FAILURE: LastFailure = {
  id: "run-1284",
  scenario: "Checkout · kart ile ödeme",
  browser: "Safari 17.4",
  failedAt: "8 dk önce",
  errorType: "TypeError",
  errorMessage: "Cannot read 'token' of undefined",
  failedStep: "Adım 14/18 — Ödeme butonu tıklanıyor",
  traceUrl: "#trace-1284",
};

function elapsed(ms: number): string {
  const s = Math.floor((Date.now() - ms) / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  return `${m}dk ${s % 60}s`;
}

function ProgressBar({ done, total }: { done: number; total: number }) {
  const pct = Math.round((done / total) * 100);
  return (
    <div className="w-full h-1 rounded-full bg-slate-800 overflow-hidden">
      <div className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function LiveRunsPanel() {
  const { toast } = useToast();
  const [running, setRunning] = useState<RunningTest[]>([]);
  const [tick, setTick] = useState(0);

  // İlk render client-side: SSR/CSR mismatch'i engellemek için demo veriyi
  // mount sonrası set ediyoruz.
  useEffect(() => {
    setRunning(makeDemoRunning(Date.now()));
  }, []);

  const stopRun = (id: string) => {
    const r = running.find((x) => x.id === id);
    setRunning((rs) => rs.filter((x) => x.id !== id));
    toast(`Koşu durduruldu: ${r?.scenario ?? id}`, "warning");
  };

  const reproduce = () => {
    toast("Lokalde reproduce komutu panoya kopyalandı", "info");
    void navigator.clipboard?.writeText(`npx playwright test --grep "${DEMO_FAILURE.scenario}" --headed`);
  };

  // Canlı sayaç + ilerleme simülasyonu (gerçek implementasyonda WS / SSE)
  useEffect(() => {
    const t = setInterval(() => {
      setTick((x) => x + 1);
      setRunning((rs) =>
        rs.map((r) =>
          r.doneSteps < r.totalSteps && Math.random() > 0.6
            ? { ...r, doneSteps: r.doneSteps + 1 }
            : r,
        ),
      );
    }, 1500);
    return () => clearInterval(t);
  }, []);

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <p className="text-xs font-semibold text-rose-400 uppercase tracking-widest">⚡ Şu An Koşuyor &amp; Son Fail</p>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25">
            Demo
          </span>
        </div>
        <span className="text-[11px] text-slate-500">Canlı · {tick}. tik</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Now Running */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-ping" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              </span>
              <h3 className="text-sm font-semibold text-white">Şu An Koşuyor</h3>
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">
                {running.length} aktif
              </span>
            </div>
            <Link href="#runs" className="text-[11px] text-emerald-400 hover:underline">Tümü →</Link>
          </div>

          {running.length === 0 ? (
            <div className="px-5 py-10 text-center text-sm text-slate-500">
              Şu an koşan bir test yok.
            </div>
          ) : (
            <ul className="divide-y divide-slate-800/60">
              {running.map((r) => (
                <li key={r.id} className="px-5 py-3 flex items-center gap-3 hover:bg-slate-800/30 transition-colors">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-white truncate">{r.scenario}</p>
                    <p className="text-[11px] text-slate-500 truncate">
                      {r.browser} · {r.startedBy} · {elapsed(r.startedAt)} koşuyor
                    </p>
                    <div className="mt-1.5">
                      <ProgressBar done={r.doneSteps} total={r.totalSteps} />
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs font-mono tabular-nums text-slate-300">{r.doneSteps}/{r.totalSteps}</p>
                    <button
                      onClick={() => stopRun(r.id)}
                      className="text-[10px] text-rose-400 hover:underline mt-1"
                    >
                      Durdur
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Last Failed Run */}
        <div className="rounded-2xl bg-slate-900 border border-rose-500/25 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-rose-500" />
              <h3 className="text-sm font-semibold text-white">Son Kırılan Koşu</h3>
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/25">
                #{DEMO_FAILURE.id}
              </span>
            </div>
            <span className="text-[11px] text-slate-500">{DEMO_FAILURE.failedAt}</span>
          </div>

          <div className="p-5 flex-1 flex flex-col gap-3">
            <div>
              <p className="text-sm font-semibold text-white">{DEMO_FAILURE.scenario}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">{DEMO_FAILURE.browser}</p>
            </div>

            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2.5">
              <p className="text-[10px] uppercase tracking-wider text-rose-300 font-bold mb-1">{DEMO_FAILURE.errorType}</p>
              <p className="text-xs font-mono text-rose-200 break-all">{DEMO_FAILURE.errorMessage}</p>
            </div>

            <div className="text-[11px] text-slate-400">
              <span className="text-slate-500">Kırıldığı yer: </span>
              {DEMO_FAILURE.failedStep}
            </div>

            <div className="mt-auto flex flex-wrap gap-2 pt-2">
              <button
                onClick={reproduce}
                className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-500 text-white text-xs font-semibold hover:bg-emerald-400 shadow-lg shadow-emerald-500/20"
              >
                ▶ Lokalde Reproduce
              </button>
              <button
                onClick={() => toast("Trace görüntüleyici açılıyor…", "info")}
                className="px-3 py-2 rounded-lg bg-slate-800 text-slate-200 text-xs font-medium border border-slate-700 hover:bg-slate-700"
              >
                Trace
              </button>
              <button
                onClick={() => toast("Bug tracker'da yeni issue açıldı", "success")}
                className="px-3 py-2 rounded-lg bg-slate-800 text-slate-200 text-xs font-medium border border-slate-700 hover:bg-slate-700"
              >
                Bug aç
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
