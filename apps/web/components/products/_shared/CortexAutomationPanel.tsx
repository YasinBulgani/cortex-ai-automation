"use client";

/**
 * Cortex Otomasyon panel — Java-based test framework status widget.
 *
 * Lives inside Intelligence product page. Pulls live data from the Flask
 * dashboard (frameworks/cortex-java/python_server/flask_api.py, port 5001).
 *
 * Graceful degradation: when the Flask dashboard is down, shows an
 * "offline" state with a one-line how-to-start hint instead of crashing.
 */

import { useEffect, useState } from "react";
import { CortexScenarioAuthor } from "./CortexScenarioAuthor";

const DASHBOARD_URL = process.env.NEXT_PUBLIC_CORTEX_DASHBOARD_URL || "http://localhost:5001";

type Health = { ok: boolean; model_loaded: boolean; active_runs: number; suggestions_count: number; version: string };
type Summary = { total: number; passed: number; failed: number; skipped: number; pass_rate: number; duration_seconds: number };

export function CortexAutomationPanel() {
  const [health, setHealth]   = useState<Health | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [featuresCount, setFeaturesCount] = useState<number | null>(null);
  const [shotsCount, setShotsCount]       = useState<number | null>(null);
  const [error, setError]                 = useState<string | null>(null);
  const [loading, setLoading]             = useState(true);
  const [authorOpen, setAuthorOpen]       = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [h, r, f, s] = await Promise.all([
          fetch(`${DASHBOARD_URL}/api/health`).then((r) => r.json()),
          fetch(`${DASHBOARD_URL}/api/results`).then((r) => r.json()),
          fetch(`${DASHBOARD_URL}/api/features`).then((r) => r.json()),
          fetch(`${DASHBOARD_URL}/api/screenshots`).then((r) => r.json()),
        ]);
        if (cancelled) return;
        setHealth(h);
        setSummary(r?.summary ?? null);
        setFeaturesCount(Array.isArray(f) ? f.length : 0);
        setShotsCount(Array.isArray(s) ? s.length : 0);
        setError(null);
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Connection failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 10_000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  const isOffline = !!error || !health?.ok;
  const passRate = summary?.pass_rate ?? 0;
  const passColor = passRate >= 80 ? "text-emerald-400" : passRate >= 50 ? "text-amber-400" : "text-rose-400";

  return (
    <div className="rounded-2xl bg-gradient-to-br from-slate-900 to-purple-950/40 border border-fuchsia-500/20 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-fuchsia-500 to-purple-700 grid place-items-center font-bold text-white shadow-lg shadow-fuchsia-500/30">
            C
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Cortex Otomasyon</h2>
            <p className="text-xs text-slate-400">
              Java · Playwright · Cucumber {health?.version ? `· v${health.version}` : ""}
            </p>
          </div>
        </div>
        <CortexStatusPill loading={loading} isOffline={isOffline} activeRuns={health?.active_runs ?? 0} />
      </div>

      {isOffline ? (
        <OfflineHint error={error} />
      ) : (
        <>
          {/* Live metrics grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
            <MetricCard label="Toplam Senaryo"   value={summary?.total ?? 0} accent="text-white" />
            <MetricCard label="Başarı Oranı"     value={`${passRate.toFixed(0)}%`} accent={passColor} />
            <MetricCard label="Feature Sayısı"   value={featuresCount ?? 0} accent="text-fuchsia-400" />
            <MetricCard label="Screenshot"       value={shotsCount ?? 0} accent="text-purple-300" />
          </div>

          {/* Pass/fail/skip breakdown */}
          {summary && summary.total > 0 && (
            <div className="mb-5">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                <span>Sonuç Dağılımı</span>
                <span>{summary.duration_seconds.toFixed(1)}s</span>
              </div>
              <div className="flex h-2 rounded-full overflow-hidden bg-slate-800">
                <div className="bg-emerald-500" style={{ width: `${(summary.passed / summary.total) * 100}%` }} />
                <div className="bg-rose-500"    style={{ width: `${(summary.failed / summary.total) * 100}%` }} />
                <div className="bg-amber-500"   style={{ width: `${(summary.skipped / summary.total) * 100}%` }} />
              </div>
              <div className="flex justify-between mt-2 text-xs">
                <span className="text-emerald-400">✓ {summary.passed} geçti</span>
                <span className="text-rose-400">✗ {summary.failed} başarısız</span>
                <span className="text-amber-400">— {summary.skipped} atlandı</span>
              </div>
            </div>
          )}

          {/* AI status mini-row */}
          <div className="grid grid-cols-2 gap-3 mb-5">
            <MiniStat
              icon="🧠"
              label="ML Model"
              value={health?.model_loaded ? "Yüklü" : "Hata"}
              ok={!!health?.model_loaded}
            />
            <MiniStat
              icon="💡"
              label="AI Önerileri"
              value={`${health?.suggestions_count ?? 0} kategori`}
              ok={(health?.suggestions_count ?? 0) > 0}
            />
          </div>

          {/* Actions */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <button
              onClick={() => setAuthorOpen(true)}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white text-sm font-semibold hover:opacity-90 transition-opacity shadow-lg shadow-fuchsia-500/25"
            >
              + Yeni Senaryo Yaz
            </button>
            <a
              href={DASHBOARD_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 text-white text-sm font-medium border border-slate-700 hover:bg-slate-700 transition-colors"
            >
              Dashboard'u Aç →
            </a>
            <a
              href="https://cortex-test.bgtsai.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 text-white text-sm font-medium border border-slate-700 hover:bg-slate-700 transition-colors"
            >
              Cortex Test Ortamı
            </a>
          </div>

          {/* Author modal */}
          <CortexScenarioAuthor open={authorOpen} onClose={() => setAuthorOpen(false)} />

          {/* Quick CLI hint */}
          <div className="mt-4 pt-4 border-t border-slate-800">
            <p className="text-xs text-slate-500 mb-2 font-semibold uppercase tracking-wide">Hızlı Komutlar</p>
            <div className="space-y-1 font-mono text-xs">
              <div className="text-slate-400">$ <span className="text-fuchsia-300">make cortex-smoke</span><span className="text-slate-600"> # @smoke suite</span></div>
              <div className="text-slate-400">$ <span className="text-fuchsia-300">make cortex-parallel</span><span className="text-slate-600"> # 4-thread paralel</span></div>
              <div className="text-slate-400">$ <span className="text-fuchsia-300">make cortex-record</span><span className="text-slate-600"> # IntelliJ recorder</span></div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/* ───── Sub-components ───── */

function CortexStatusPill({ loading, isOffline, activeRuns }: { loading: boolean; isOffline: boolean; activeRuns: number }) {
  if (loading) {
    return <span className="text-xs px-2 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700">…</span>;
  }
  if (isOffline) {
    return (
      <span className="text-xs px-2 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
        Offline
      </span>
    );
  }
  if (activeRuns > 0) {
    return (
      <span className="text-xs px-2 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
        {activeRuns} koşum
      </span>
    );
  }
  return (
    <span className="text-xs px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
      Aktif
    </span>
  );
}

function OfflineHint({ error }: { error: string | null }) {
  return (
    <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4">
      <p className="text-sm text-rose-300 mb-2">
        ⚠ Cortex Dashboard erişilemiyor
      </p>
      <p className="text-xs text-slate-400 mb-3">
        Flask sunucusu kapalı veya port {DASHBOARD_URL.replace(/^https?:\/\/[^:]+:?/, "")} bloklu.
        {error && <span className="block mt-1 font-mono opacity-60">{error}</span>}
      </p>
      <div className="rounded-lg bg-black/40 border border-slate-800 p-3 font-mono text-xs">
        <div className="text-slate-500"># Başlatmak için:</div>
        <div className="text-fuchsia-300">$ make cortex-dashboard</div>
        <div className="text-slate-500 mt-2"># veya IntelliJ Run &gt; "Cortex - Dashboard (Flask)"</div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, accent }: { label: string; value: string | number; accent: string }) {
  return (
    <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-3">
      <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-2xl font-bold ${accent}`}>{value}</div>
    </div>
  );
}

function MiniStat({ icon, label, value, ok }: { icon: string; label: string; value: string; ok: boolean }) {
  return (
    <div className="rounded-xl bg-slate-900/60 border border-slate-800 px-3 py-2 flex items-center gap-2">
      <span className="text-lg">{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-slate-500 truncate">{label}</div>
        <div className={`text-sm font-semibold ${ok ? "text-emerald-300" : "text-rose-300"}`}>{value}</div>
      </div>
    </div>
  );
}
