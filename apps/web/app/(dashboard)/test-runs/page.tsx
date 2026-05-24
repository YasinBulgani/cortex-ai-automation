"use client";

/**
 * E18 — Test Sonuç Dashboard sayfası.
 *
 * Backend: Flask /api/cortex/test-runs/*
 *   - GET /list — sıralı run listesi
 *   - GET /<id> — tek run detayı + screenshot listesi
 *   - GET /<id>/screenshot/<file> — PNG serve
 *
 * Veri kaynağı: PwHooks.@AfterStep + @After her scenario için
 *   target/test-runs/<timestamp>_<safe-name>_<uid>/
 *     ├── step-001_*.png
 *     ├── step-002_*.png
 *     ├── FAILURE_fullpage.png (varsa)
 *     └── result.json { passed, duration_ms, steps, scenario }
 */

import { useState, useEffect, useCallback } from "react";

const DASHBOARD_URL =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_FLASK_URL) ||
  "http://127.0.0.1:5001";

type TestRun = {
  id: string;
  scenario: string;
  passed: boolean | null;
  duration_ms: number;
  steps: number;
  screenshot_count: number;
  screenshots?: string[];
  mtime: number;
  in_progress?: boolean;
};

type RunDetail = {
  ok: boolean;
  id: string;
  scenario: string;
  passed: boolean | null;
  duration_ms: number;
  steps: number;
  screenshots: { name: string; path: string; size_bytes: number }[];
  mtime: number;
};

type StatusFilter = "all" | "passed" | "failed";

function fmtDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}sn`;
  const m = Math.floor(ms / 60_000);
  const s = Math.floor((ms % 60_000) / 1000);
  return `${m}d ${s}sn`;
}

function fmtRelativeDate(mtime: number): string {
  const ms = Date.now() - mtime * 1000;
  if (ms < 60_000) return "şimdi";
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}dk önce`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}sa önce`;
  return `${Math.floor(ms / 86_400_000)}g önce`;
}

export default function TestRunsPage() {
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRun, setSelectedRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = new URL(`${DASHBOARD_URL}/api/cortex/test-runs/list`);
      url.searchParams.set("limit", "100");
      url.searchParams.set("status", statusFilter);
      const r = await fetch(url.toString(), { cache: "no-store" });
      const j = await r.json();
      if (!j.ok) throw new Error(j.error || "Liste alınamadı");
      setRuns(j.runs || []);
      setTotal(j.total || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  const openRunDetail = async (id: string) => {
    setSelectedRun(null);
    try {
      const r = await fetch(`${DASHBOARD_URL}/api/cortex/test-runs/${encodeURIComponent(id)}`);
      const j = await r.json();
      if (!j.ok) throw new Error(j.error || "Detay alınamadı");
      setSelectedRun(j);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const filteredRuns = runs.filter((r) =>
    !searchQuery ||
    r.scenario.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const stats = {
    total: runs.length,
    passed: runs.filter((r) => r.passed === true).length,
    failed: runs.filter((r) => r.passed === false).length,
    inProgress: runs.filter((r) => r.in_progress).length,
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-1">📊 Test Koşumları</h1>
        <p className="text-sm text-slate-400">
          PwHooks tarafından üretilen test run sonuçları — her senaryo bir klasör, her step bir screenshot.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-3 mb-4">
        <StatCard label="Toplam Run" value={stats.total} color="slate" />
        <StatCard label="✅ Passed" value={stats.passed} color="emerald" />
        <StatCard label="❌ Failed" value={stats.failed} color="rose" />
        <StatCard label="⏳ Devam Eden" value={stats.inProgress} color="amber" />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-4">
        <div className="inline-flex bg-slate-900 border border-slate-800 rounded-lg p-1">
          {(["all", "passed", "failed"] as StatusFilter[]).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                statusFilter === s
                  ? "bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-500/40"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {s === "all" ? "Tümü" : s === "passed" ? "✅ Geçti" : "❌ Başarısız"}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="🔍 Scenario adı veya run ID..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:border-fuchsia-500 focus:outline-none"
        />
        <button
          onClick={fetchRuns}
          disabled={loading}
          className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium border border-slate-700 disabled:opacity-50"
        >
          {loading ? "Yükleniyor..." : "🔄 Yenile"}
        </button>
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">
          ✗ {error}
        </div>
      )}

      {/* Table */}
      <div className="rounded-xl bg-black/40 border border-slate-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-900/60 border-b border-slate-800">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">Status</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">Scenario</th>
              <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-400">Steps</th>
              <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-400">Süre</th>
              <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-400">📷</th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-400">Tarih</th>
            </tr>
          </thead>
          <tbody>
            {filteredRuns.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-slate-500 text-sm">
                  {loading ? "Yükleniyor..." : total === 0
                    ? "Henüz test koşumu yok. Bir senaryo çalıştır → otomatik burada görünür."
                    : "Filtre eşleşmesi yok."}
                </td>
              </tr>
            ) : (
              filteredRuns.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => openRunDetail(r.id)}
                  className="border-t border-slate-800 hover:bg-slate-900/50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    {r.in_progress ? (
                      <span className="inline-flex items-center gap-1 text-amber-400">
                        <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                        Devam
                      </span>
                    ) : r.passed ? (
                      <span className="text-emerald-400 font-semibold">✅ Geçti</span>
                    ) : (
                      <span className="text-rose-400 font-semibold">❌ Başarısız</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-200 font-medium">
                    {r.scenario}
                    <div className="text-[10px] text-slate-600 font-mono mt-0.5">{r.id}</div>
                  </td>
                  <td className="px-4 py-3 text-center text-slate-300 tabular-nums">{r.steps}</td>
                  <td className="px-4 py-3 text-center text-slate-300 tabular-nums">{fmtDuration(r.duration_ms)}</td>
                  <td className="px-4 py-3 text-center text-slate-400 tabular-nums">{r.screenshot_count}</td>
                  <td className="px-4 py-3 text-right text-slate-400 text-xs">{fmtRelativeDate(r.mtime)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Detail modal */}
      {selectedRun && (
        <RunDetailModal run={selectedRun} onClose={() => setSelectedRun(null)} />
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colorClass: Record<string, string> = {
    slate: "text-slate-300",
    emerald: "text-emerald-400",
    rose: "text-rose-400",
    amber: "text-amber-400",
  };
  return (
    <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">{label}</div>
      <div className={`text-2xl font-bold tabular-nums ${colorClass[color]}`}>{value}</div>
    </div>
  );
}

function RunDetailModal({ run, onClose }: { run: RunDetail; onClose: () => void }) {
  const [activeShot, setActiveShot] = useState<string | null>(null);
  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-slate-950 border border-fuchsia-500/40 rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-3 border-b border-slate-800 flex items-start justify-between">
          <div>
            <h3 className="font-bold text-white text-base">
              {run.passed ? "✅" : "❌"} {run.scenario}
            </h3>
            <p className="text-xs text-slate-400 mt-1 font-mono">{run.id}</p>
            <p className="text-xs text-slate-500 mt-1">
              {run.steps} step · {fmtDuration(run.duration_ms)} · {run.screenshots.length} screenshot
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-2xl">×</button>
        </div>

        <div className="flex-1 overflow-auto p-4">
          {run.screenshots.length === 0 ? (
            <div className="text-slate-500 text-sm italic">Bu run için screenshot yok.</div>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
              {run.screenshots.map((s) => (
                <div
                  key={s.name}
                  onClick={() => setActiveShot(s.name)}
                  className="cursor-pointer rounded-lg border border-slate-800 hover:border-fuchsia-500/50 transition-colors overflow-hidden bg-slate-900"
                >
                  <img
                    src={`${DASHBOARD_URL}/api/cortex/test-runs/${encodeURIComponent(run.id)}/screenshot/${encodeURIComponent(s.name)}`}
                    alt={s.name}
                    className="w-full h-48 object-cover object-top"
                    loading="lazy"
                  />
                  <div className="p-2">
                    <div className="text-[11px] text-slate-300 font-mono truncate" title={s.name}>
                      {s.name}
                    </div>
                    <div className="text-[10px] text-slate-500">
                      {(s.size_bytes / 1024).toFixed(0)}KB
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Full-size screenshot overlay */}
      {activeShot && (
        <div
          className="fixed inset-0 z-[60] bg-black/90 flex items-center justify-center p-8"
          onClick={() => setActiveShot(null)}
        >
          <img
            src={`${DASHBOARD_URL}/api/cortex/test-runs/${encodeURIComponent(run.id)}/screenshot/${encodeURIComponent(activeShot)}`}
            alt={activeShot}
            className="max-w-full max-h-full object-contain"
          />
          <div className="absolute top-4 right-4 text-white text-3xl cursor-pointer">×</div>
        </div>
      )}
    </div>
  );
}
