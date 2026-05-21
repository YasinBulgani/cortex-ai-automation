"use client";

import { PageFeedbackWidget } from "@/components/PageFeedbackWidget";

import { useState } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import {
  PageHeader,
  SectionCard,
  StatCard,
  EmptyState,
} from "@/components/nexus";
import {
  useFallbackResolve,
  useStabilityAnalysis,
  usePOMGenerate,
  useBreakagePrediction,
  useLocatorTrends,
  type LocatorEntry,
  type FallbackResponse,
  type FallbackResult,
  type StabilityResponse,
  type StabilityDetail,
  type POMResponse,
  type BreakagePrediction,
  type TrendResponse,
} from "@/lib/hooks/use-locator-intelligence";

// ── Types ────────────────────────────────────────────────────────────

type Locator = {
  id: string;
  name: string;
  selector: string;
  type: string;
  page: string;
  status: string;
};

const STATUS_STYLES: Record<string, { color: string; dot: string; label: string }> = {
  healthy: { color: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400", dot: "bg-emerald-400", label: "Saglikli" },
  broken:  { color: "bg-red-500/10 border-red-500/20 text-red-400",            dot: "bg-red-400",     label: "Kırık" },
  warning: { color: "bg-amber-500/10 border-amber-500/20 text-amber-400",      dot: "bg-amber-400",   label: "Uyari" },
};

const TYPE_COLORS: Record<string, string> = {
  css:    "bg-blue-500/10 border-blue-500/20 text-blue-400",
  xpath:  "bg-amber-500/10 border-amber-500/20 text-amber-400",
  testid: "bg-violet-500/10 border-violet-500/20 text-violet-400",
  text:   "bg-slate-800 border-slate-700 text-slate-300",
};

type TabId = "management" | "stability" | "fallback" | "pom" | "breakage";
const TABS = [
  { id: "management" as TabId, label: "Yönetim" },
  { id: "stability" as TabId, label: "Stabilite" },
  { id: "fallback" as TabId, label: "Fallback" },
  { id: "pom" as TabId, label: "POM" },
  { id: "breakage" as TabId, label: "Kırılma" },
];
const BTN_PRIMARY = "inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all";
const INPUT_CLS = "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50";
const TEXTAREA_CLS = "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 resize-none font-mono";

function getScoreColor(score: number): string {
  if (score >= 4) return "bg-emerald-500/10 border-emerald-500/20 text-emerald-400";
  if (score >= 3) return "bg-blue-500/10 border-blue-500/20 text-blue-400";
  if (score >= 2) return "bg-amber-500/10 border-amber-500/20 text-amber-400";
  return "bg-red-500/10 border-red-500/20 text-red-400";
}

function Spinner({ className = "w-5 h-5" }: { className?: string }) {
  return <div className={`border-2 border-slate-700 border-t-blue-400 rounded-full animate-spin ${className}`} />;
}

function ConfidenceBar({ value, max = 1 }: { value: number; max?: number }) {
  const pct = Math.min(100, (value / max) * 100);
  const color = pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="h-1.5 rounded-full bg-slate-700 overflow-hidden">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function RiskBar({ value }: { value: number }) {
  const pct = Math.min(100, value * 100);
  const color = pct >= 70 ? "bg-red-500" : pct >= 40 ? "bg-amber-500" : "bg-emerald-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 rounded-full bg-slate-700 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-400">{(value * 100).toFixed(0)}%</span>
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { void navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      className="rounded p-1 text-slate-400 hover:text-white hover:bg-slate-700 transition-all"
      title="Kopyala"
    >
      {copied ? (
        <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      )}
    </button>
  );
}

function TabManagement({ locators, loading, refresh, projectId }: { locators: Locator[]; loading: boolean; refresh: () => void; projectId: string }) {
  const healthy = locators.filter((l) => l.status === "healthy").length;
  const broken  = locators.filter((l) => l.status === "broken").length;
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", selector: "", page: "", type: "css" });

  async function createLocator(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name || !form.selector) return;
    setCreating(true);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/locators`, { method: "POST", json: form });
      setForm({ name: "", selector: "", page: "", type: "css" });
      setShowForm(false);
      refresh();
    } catch { /* ignore */ } finally {
      setCreating(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Toplam" value={locators.length} />
        <StatCard label="Saglikli" value={healthy} color="emerald" />
        <StatCard label="Kırık" value={broken} color="red" />
      </div>

      {/* Create form */}
      {showForm && (
        <SectionCard
          title="Yeni Locator"
          icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>}
        >
          <form onSubmit={createLocator} className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <input placeholder="Ad (orn. loginButton)" value={form.name} onChange={e => setForm({...form, name: e.target.value})} required className={INPUT_CLS} />
              <input placeholder="Selector (orn. [data-testid='login'])" value={form.selector} onChange={e => setForm({...form, selector: e.target.value})} required className={`${INPUT_CLS} font-mono`} />
              <input placeholder="Sayfa (orn. Login)" value={form.page} onChange={e => setForm({...form, page: e.target.value})} className={INPUT_CLS} />
              <select value={form.type} onChange={e => setForm({...form, type: e.target.value})}
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50">
                <option value="css">CSS</option>
                <option value="xpath">XPath</option>
                <option value="testid">Test ID</option>
                <option value="text">Metin</option>
              </select>
            </div>
            <div className="flex gap-2">
              <button type="submit" disabled={creating || !form.name || !form.selector} className={BTN_PRIMARY}>
                {creating ? "Kaydediliyor..." : "Kaydet"}
              </button>
              <button type="button" onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors">Iptal</button>
            </div>
          </form>
        </SectionCard>
      )}

      {/* Search */}
      <div className="relative">
        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          placeholder="Locator ara..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full max-w-sm rounded-xl border border-slate-700 bg-slate-900/40 pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <h3 className="text-sm font-semibold">Locator Listesi</h3>
          <span className="text-xs text-slate-500">{locators.length} locator</span>
        </div>

        {loading ? (
          <div className="py-16 text-center text-slate-500 text-sm flex items-center justify-center gap-2">
            <Spinner /> Yükleniyor...
          </div>
        ) : locators.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon="🎯"
              title={search ? "Sonuç yok" : "Henuz locator yok"}
              description={search ? "Arama kriterini değiştirin" : "Element konumlandiricilarini ekleyin"}
              action={!search ? (
                <button onClick={() => setShowForm(true)} className={BTN_PRIMARY}>Locator Ekle</button>
              ) : undefined}
            />
          </div>
        ) : (
          <table className="w-full" data-testid="locators-table">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Ad</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Selector</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tip</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Sayfa</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Durum</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {locators.map((l) => {
                const st = STATUS_STYLES[l.status] ?? STATUS_STYLES.warning;
                const tc = TYPE_COLORS[l.type] ?? TYPE_COLORS.text;
                return (
                  <tr key={l.id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                    <td className="px-4 py-3 font-mono text-xs font-medium text-white">{l.name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400 max-w-xs truncate" title={l.selector}>
                      {l.selector}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium ${tc}`}>
                        {l.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-400">{l.page || "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${st.color}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />
                        {st.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// TAB 2: Stabilite Analizi
// ═══════════════════════════════════════════════════════════════════════

function TabStability({ locators }: { locators: Locator[] }) {
  const stability = useStabilityAnalysis();
  const [result, setResult] = useState<StabilityResponse | null>(null);

  function handleAnalyze() {
    if (locators.length === 0) return;
    const entries: LocatorEntry[] = locators.map(l => ({
      id: l.id,
      name: l.name,
      selector: l.selector,
      type: l.type,
      page: l.page,
      status: l.status,
    }));
    stability.mutate({ locators: entries }, {
      onSuccess: (data) => setResult(data),
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">
          Mevcut locator&apos;larinizin stabilite analizini yapin. Kırık ve riskli selector&apos;lar otomatik tespit edilir.
        </p>
        <button
          onClick={handleAnalyze}
          disabled={stability.isPending || locators.length === 0}
          className={BTN_PRIMARY}
        >
          {stability.isPending ? <Spinner className="w-4 h-4" /> : (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          )}
          {stability.isPending ? "Analiz ediliyor..." : "Analiz Et"}
        </button>
      </div>

      {locators.length === 0 && (
        <div className="p-8">
          <EmptyState
            icon="🔍"
            title="Locator bulunamadi"
            description="Once Locator Yonetimi sekmesinden locator ekleyin"
          />
        </div>
      )}

      {stability.isError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          Hata: {stability.error?.message ?? "Bilinmeyen hata"}
        </div>
      )}

      {result && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-5 gap-3">
            <StatCard label="Toplam" value={result.total_locators} />
            <StatCard label="Saglikli" value={result.healthy} color="emerald" />
            <StatCard label="Uyari" value={result.warning} color="amber" />
            <StatCard label="Kritik" value={result.critical} color="red" />
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
              <p className="text-xs text-slate-400 mb-1">Ort. Skor</p>
              <div className="flex items-end gap-2">
                <p className="text-2xl font-bold text-white">{result.avg_score.toFixed(1)}</p>
                <p className="text-xs text-slate-500 mb-1">/ 5</p>
              </div>
              {/* Score gauge */}
              <div className="mt-2 h-2 rounded-full bg-slate-700 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    result.avg_score >= 4 ? "bg-emerald-500" :
                    result.avg_score >= 3 ? "bg-blue-500" :
                    result.avg_score >= 2 ? "bg-amber-500" : "bg-red-500"
                  }`}
                  style={{ width: `${(result.avg_score / 5) * 100}%` }}
                />
              </div>
            </div>
          </div>

          {/* Details table */}
          <SectionCard
            title="Detayli Analiz"
            icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
            right={<span className="text-xs text-slate-500">{result.details.length} locator</span>}
            noPad
          >
            {result.details.length === 0 ? (
              <div className="p-8">
                <EmptyState icon="📊" title="Detay bulunamadi" description="Analiz sonuçu bos dondu" />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-800">
                      <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Selector</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Ad</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Skor</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Risk</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Nedenler</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Oneri</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.details.map((d: StabilityDetail, i: number) => (
                      <tr key={i} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                        <td className="px-4 py-3 font-mono text-xs text-slate-300 max-w-[200px] truncate" title={d.selector}>{d.selector}</td>
                        <td className="px-4 py-3 text-sm text-white">{d.name}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-bold ${getScoreColor(d.score)}`}>
                            {d.score.toFixed(1)}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs font-medium ${
                            d.risk_level === "critical" ? "bg-red-500/10 border-red-500/20 text-red-400" :
                            d.risk_level === "warning" ? "bg-amber-500/10 border-amber-500/20 text-amber-400" :
                            "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                          }`}>
                            {d.risk_level === "critical" ? "Kritik" : d.risk_level === "warning" ? "Uyari" : "Dusuk"}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {d.reasons.map((r, ri) => (
                              <span key={ri} className="inline-flex px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px] text-slate-400">{r}</span>
                            ))}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-400 max-w-[200px]">{d.suggestion ?? "\u2014"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// TAB 3: Fallback Zinciri
// ═══════════════════════════════════════════════════════════════════════

function TabFallback() {
  const resolve = useFallbackResolve();
  const [form, setForm] = useState({
    broken_selector: "",
    dom_snippet: "",
    page_url: "",
    error_message: "",
    session_id: "",
  });
  const [result, setResult] = useState<FallbackResponse | null>(null);

  function handleResolve(e: React.FormEvent) {
    e.preventDefault();
    if (!form.broken_selector) return;
    resolve.mutate({
      broken_selector: form.broken_selector,
      dom_snippet: form.dom_snippet || undefined,
      page_url: form.page_url || undefined,
      error_message: form.error_message || undefined,
      session_id: form.session_id || undefined,
    }, {
      onSuccess: (data) => setResult(data),
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-slate-400">
        Kırık bir selector girip fallback zinciri ile çözüm arayin. AI destekli stratejiler sırası ile denenir.
      </p>

      {/* Input form */}
      <SectionCard
        title="Kırık Selector"
        icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>}
      >
        <form onSubmit={handleResolve} className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              placeholder="Kırık Selector (orn. #old-login-btn)"
              value={form.broken_selector}
              onChange={e => setForm({...form, broken_selector: e.target.value})}
              required
              className={`${INPUT_CLS} font-mono`}
            />
            <input
              placeholder="Sayfa URL (isteğe bağlı)"
              value={form.page_url}
              onChange={e => setForm({...form, page_url: e.target.value})}
              className={INPUT_CLS}
            />
          </div>
          <textarea
            placeholder="DOM Snippet (isteğe bağlı — ilgili HTML blogu)"
            value={form.dom_snippet}
            onChange={e => setForm({...form, dom_snippet: e.target.value})}
            rows={4}
            className={TEXTAREA_CLS}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              placeholder="Hata mesajı (isteğe bağlı)"
              value={form.error_message}
              onChange={e => setForm({...form, error_message: e.target.value})}
              className={INPUT_CLS}
            />
            <input
              placeholder="Session ID (isteğe bağlı)"
              value={form.session_id}
              onChange={e => setForm({...form, session_id: e.target.value})}
              className={INPUT_CLS}
            />
          </div>
          <button type="submit" disabled={resolve.isPending || !form.broken_selector} className={BTN_PRIMARY}>
            {resolve.isPending ? <Spinner className="w-4 h-4" /> : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            )}
            {resolve.isPending ? "Çözümleniyor..." : "Çözümle"}
          </button>
        </form>
      </SectionCard>

      {resolve.isError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          Hata: {resolve.error?.message ?? "Bilinmeyen hata"}
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Success/Fail banner */}
          <div className={`rounded-xl border px-4 py-4 ${
            result.success
              ? "border-emerald-500/30 bg-emerald-500/10"
              : "border-red-500/30 bg-red-500/10"
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {result.success ? (
                  <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                ) : (
                  <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
                <div>
                  <p className={`text-sm font-semibold ${result.success ? "text-emerald-300" : "text-red-300"}`}>
                    {result.success ? "Çözüm bulundu!" : "Çözüm bulunamadi"}
                  </p>
                  {result.best_selector && (
                    <p className="font-mono text-xs text-white mt-1">{result.best_selector}</p>
                  )}
                </div>
              </div>
              {result.best_selector && <CopyButton text={result.best_selector} />}
            </div>
            <div className="mt-3 flex gap-4 text-xs text-slate-400">
              <span>Strateji: <strong className="text-white">{result.strategies_tried}</strong> denendi</span>
              <span>Toplam: <strong className="text-white">{result.total_latency_ms}ms</strong></span>
              {result.best_strategy && <span>Kazanan: <strong className="text-white">{result.best_strategy}</strong></span>}
            </div>
          </div>

          {/* Strategy chain visualization */}
          <SectionCard
            title="Strateji Zinciri"
            icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
          >
            <div className="flex gap-3 overflow-x-auto pb-2">
              {result.all_results.map((r: FallbackResult, i: number) => {
                const isWinner = result.success && r.strategy === result.best_strategy && r.found;
                return (
                  <div
                    key={i}
                    className={`flex-shrink-0 w-56 rounded-xl border p-4 ${
                      isWinner
                        ? "border-emerald-500/40 bg-emerald-500/10 ring-1 ring-emerald-500/30"
                        : r.found
                        ? "border-blue-500/30 bg-blue-500/5"
                        : "border-slate-700 bg-slate-900/40"
                    }`}
                  >
                    {/* Strategy name + found icon */}
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-xs font-bold uppercase tracking-wider ${
                        isWinner ? "text-emerald-400" : "text-slate-300"
                      }`}>
                        {r.strategy}
                      </span>
                      {r.found ? (
                        <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      )}
                    </div>

                    {/* Selector */}
                    <p className="font-mono text-[10px] text-slate-400 truncate mb-2" title={r.selector}>{r.selector}</p>

                    {/* Confidence bar */}
                    <p className="text-[10px] text-slate-500 mb-1">Guven</p>
                    <ConfidenceBar value={r.confidence} />

                    {/* Latency */}
                    <div className="mt-2 flex items-center justify-between text-[10px] text-slate-500">
                      <span>Gecikme</span>
                      <span className="font-mono text-slate-400">{r.latency_ms}ms</span>
                    </div>

                    {/* Reason */}
                    <p className="mt-2 text-[10px] text-slate-500 line-clamp-2">{r.reason}</p>

                    {isWinner && (
                      <div className="mt-2 rounded-full bg-emerald-500/20 px-2 py-0.5 text-center text-[10px] font-bold text-emerald-400 uppercase tracking-wider">
                        Kazanan
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </SectionCard>

          {/* Best result detail */}
          {result.success && result.best_selector && (
            <SectionCard
              title="En Iyi Sonuç"
              icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" /></svg>}
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-xs text-slate-500 mb-1">Selector</p>
                  <div className="flex items-center gap-2">
                    <code className="font-mono text-sm text-emerald-300 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20 flex-1 truncate">{result.best_selector}</code>
                    <CopyButton text={result.best_selector} />
                  </div>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Strateji</p>
                  <p className="text-sm font-medium text-white">{result.best_strategy}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Guven Skoru</p>
                  <ConfidenceBar value={result.best_confidence} />
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Stabilite Skoru</p>
                  <ConfidenceBar value={result.best_stability} max={5} />
                </div>
              </div>
            </SectionCard>
          )}
        </>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// TAB 4: POM Üretici
// ═══════════════════════════════════════════════════════════════════════

function TabPOM({ locators }: { locators: Locator[] }) {
  const pom = usePOMGenerate();
  const [pageName, setPageName] = useState("");
  const [language, setLanguage] = useState<"typescript" | "python">("typescript");
  const [elementsJson, setElementsJson] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [useSession, setUseSession] = useState(false);
  const [result, setResult] = useState<POMResponse | null>(null);

  function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!pageName) return;

    let elements: LocatorEntry[] | undefined;

    if (useSession) {
      // Session ID ile auto-fetch
      elements = undefined;
    } else if (elementsJson.trim()) {
      try {
        elements = JSON.parse(elementsJson) as LocatorEntry[];
      } catch {
        return;
      }
    } else {
      // Tab 1'deki locator'lari kullan
      elements = locators.map(l => ({
        name: l.name,
        selector: l.selector,
        type: l.type,
        page: l.page,
        status: l.status,
      }));
    }

    pom.mutate({
      page_name: pageName,
      language,
      elements,
      session_id: useSession && sessionId ? sessionId : undefined,
    }, {
      onSuccess: (data) => setResult(data),
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-slate-400">
        Page Object Model (POM) sinifi üretin. Element bilgilerini JSON olarak girin, session ID ile otomatik cekin veya mevcut locator&apos;larinizi kullanin.
      </p>

      <SectionCard
        title="POM Ayarlari"
        icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>}
      >
        <form onSubmit={handleGenerate} className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              placeholder="Sayfa Adi (orn. LoginPage)"
              value={pageName}
              onChange={e => setPageName(e.target.value)}
              required
              className={INPUT_CLS}
            />
            <select
              value={language}
              onChange={e => setLanguage(e.target.value as "typescript" | "python")}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50"
            >
              <option value="typescript">TypeScript</option>
              <option value="python">Python</option>
            </select>
          </div>

          {/* Element source toggle */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setUseSession(false)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                !useSession ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              Element JSON / Mevcut Locator&apos;lar
            </button>
            <button
              type="button"
              onClick={() => setUseSession(true)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                useSession ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              Session ID ile Otomatik Cek
            </button>
          </div>

          {useSession ? (
            <input
              placeholder="Playwright MCP Session ID"
              value={sessionId}
              onChange={e => setSessionId(e.target.value)}
              className={INPUT_CLS}
            />
          ) : (
            <div>
              <textarea
                placeholder={`Element JSON (bos birakirsaniz mevcut ${locators.length} locator kullanilir)`}
                value={elementsJson}
                onChange={e => setElementsJson(e.target.value)}
                rows={5}
                className={TEXTAREA_CLS}
              />
              {!elementsJson.trim() && locators.length > 0 && (
                <p className="mt-1 text-[10px] text-slate-500">
                  Mevcut {locators.length} locator otomatik kullanilacak.
                </p>
              )}
            </div>
          )}

          <button type="submit" disabled={pom.isPending || !pageName} className={BTN_PRIMARY}>
            {pom.isPending ? <Spinner className="w-4 h-4" /> : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            )}
            {pom.isPending ? "Üretiliyor..." : "Üret"}
          </button>
        </form>
      </SectionCard>

      {pom.isError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          Hata: {pom.error?.message ?? "Bilinmeyen hata"}
        </div>
      )}

      {/* Generated code */}
      {result && (
        <SectionCard
          title={result.file_name}
          icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
          right={
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-slate-500">{result.element_count} element</span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded border text-[10px] font-medium ${
                result.language === "typescript"
                  ? "bg-blue-500/10 border-blue-500/20 text-blue-400"
                  : "bg-amber-500/10 border-amber-500/20 text-amber-400"
              }`}>
                {result.language}
              </span>
              <CopyButton text={result.code} />
            </div>
          }
          noPad
        >
          <div className="overflow-x-auto">
            <pre className="p-4 text-xs leading-relaxed">
              <code className="font-mono text-slate-300 whitespace-pre">{result.code}</code>
            </pre>
          </div>
        </SectionCard>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// TAB 5: Kirilma Tahmini
// ═══════════════════════════════════════════════════════════════════════

function TabBreakage({ locators }: { locators: Locator[] }) {
  const predict = useBreakagePrediction();
  const trends = useLocatorTrends();
  const [recentChanges, setRecentChanges] = useState("");
  const [predictions, setPredictions] = useState<BreakagePrediction[] | null>(null);

  function handlePredict() {
    if (locators.length === 0) return;
    const entries: LocatorEntry[] = locators.map(l => ({
      id: l.id,
      name: l.name,
      selector: l.selector,
      type: l.type,
      page: l.page,
      status: l.status,
    }));
    predict.mutate({ locators: entries, recent_changes: recentChanges || undefined }, {
      onSuccess: (data) => setPredictions(data),
    });
  }

  const highRisk = predictions?.filter(p => p.risk_score >= 0.7).length ?? 0;
  const mediumRisk = predictions?.filter(p => p.risk_score >= 0.4 && p.risk_score < 0.7).length ?? 0;
  const lowRisk = predictions?.filter(p => p.risk_score < 0.4).length ?? 0;

  const trendData: TrendResponse | undefined = trends.data;

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-slate-400">
        Locator&apos;larinizin kirilma riskini tahmin edin. Git diff yapistirarak son değişikliklere gore analiz yapilabilir.
      </p>

      <SectionCard
        title="Tahmin Ayarlari"
        icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>}
      >
        <div className="space-y-3">
          <textarea
            placeholder="Son değişiklikler (git diff yapistirin — isteğe bağlı)"
            value={recentChanges}
            onChange={e => setRecentChanges(e.target.value)}
            rows={5}
            className={TEXTAREA_CLS}
          />
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500">
              {locators.length} locator analiz edilecek
            </p>
            <button
              onClick={handlePredict}
              disabled={predict.isPending || locators.length === 0}
              className={BTN_PRIMARY}
            >
              {predict.isPending ? <Spinner className="w-4 h-4" /> : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              )}
              {predict.isPending ? "Tahmin ediliyor..." : "Tahmin Et"}
            </button>
          </div>
        </div>
      </SectionCard>

      {locators.length === 0 && (
        <div className="p-8">
          <EmptyState
            icon="🔮"
            title="Locator bulunamadi"
            description="Once Locator Yonetimi sekmesinden locator ekleyin"
          />
        </div>
      )}

      {predict.isError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          Hata: {predict.error?.message ?? "Bilinmeyen hata"}
        </div>
      )}

      {/* Risk summary */}
      {predictions && (
        <>
          <div className="grid grid-cols-3 gap-3">
            <StatCard label="Yuksek Risk" value={highRisk} color="red" />
            <StatCard label="Orta Risk" value={mediumRisk} color="amber" />
            <StatCard label="Dusuk Risk" value={lowRisk} color="emerald" />
          </div>

          {/* Risk table */}
          <SectionCard
            title="Kirilma Risk Tablosu"
            icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
            right={<span className="text-xs text-slate-500">{predictions.length} locator</span>}
            noPad
          >
            {predictions.length === 0 ? (
              <div className="p-8">
                <EmptyState icon="🛡️" title="Risk bulunamadi" description="Locator'lariniz guvenli gorunuyor" />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-800">
                      <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Selector</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Ad</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400 w-40">Risk Skoru</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Risk Faktorleri</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Oneri</th>
                    </tr>
                  </thead>
                  <tbody>
                    {predictions.map((p, i) => (
                      <tr key={i} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                        <td className="px-4 py-3 font-mono text-xs text-slate-300 max-w-[200px] truncate" title={p.selector}>{p.selector}</td>
                        <td className="px-4 py-3 text-sm text-white">{p.name}</td>
                        <td className="px-4 py-3">
                          <RiskBar value={p.risk_score} />
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {p.risk_factors.map((f, fi) => (
                              <span key={fi} className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                p.risk_score >= 0.7
                                  ? "bg-red-500/10 border border-red-500/20 text-red-400"
                                  : p.risk_score >= 0.4
                                  ? "bg-amber-500/10 border border-amber-500/20 text-amber-400"
                                  : "bg-slate-800 border border-slate-700 text-slate-400"
                              }`}>{f}</span>
                            ))}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-400 max-w-[200px]">{p.recommendation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </>
      )}

      {/* Trend section */}
      {trendData && (
        <SectionCard
          title="Locator Trendleri"
          icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>}
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="text-xs text-slate-500 mb-1">Toplam Heal</p>
              <p className="text-xl font-bold text-white">{trendData.total_heals}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 mb-1">Ort. Guven</p>
              <p className="text-xl font-bold text-white">{(trendData.avg_confidence * 100).toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 mb-1">Trend</p>
              <div className="flex items-center gap-1">
                {trendData.trend === "up" ? (
                  <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                  </svg>
                ) : trendData.trend === "down" ? (
                  <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
                  </svg>
                )}
                <span className={`text-sm font-medium ${
                  trendData.trend === "up" ? "text-emerald-400" :
                  trendData.trend === "down" ? "text-red-400" : "text-slate-400"
                }`}>
                  {trendData.trend === "up" ? "Yukseliyor" : trendData.trend === "down" ? "Dusyor" : "Sabit"}
                </span>
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-500 mb-1">Stratejiye Gore</p>
              <div className="space-y-1">
                {Object.entries(trendData.by_strategy).map(([strategy, count]) => (
                  <div key={strategy} className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">{strategy}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 rounded-full bg-slate-700 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-blue-500"
                          style={{ width: `${Math.min(100, (count / Math.max(1, trendData.total_heals)) * 100)}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-slate-400 w-6 text-right">{count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </SectionCard>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ═══════════════════════════════════════════════════════════════════════

export default function LocatorsPage() {
  const projectId = useRouteParam("projectId");
  const [activeTab, setActiveTab] = useState<TabId>("management");
  const queryClient = useQueryClient();

  // Fetch locators using TanStack Query
  const locatorsQuery = useQuery({
    queryKey: ["project-locators", projectId],
    queryFn: () => apiFetch<Locator[]>(`/api/v1/tspm/projects/${projectId}/locators`),
  });

  const locators = locatorsQuery.data ?? [];
  const loading = locatorsQuery.isLoading;
  const refresh = () => { void queryClient.invalidateQueries({ queryKey: ["project-locators", projectId] }); };

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="locators-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
          </svg>
        }
        title="Locator Zekasi"
        description="Element konumlandiricilarini yonetin, stabilite analizi yapin ve AI destekli çözümler kullanin"
        badge={
          <span className="rounded-full border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-[10px] font-semibold text-blue-400 uppercase tracking-wider">
            AI
          </span>
        }
      />

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-800 pb-0 overflow-x-auto">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            data-testid={`tab-${tab.id}`}
            className={`flex-shrink-0 px-4 py-2.5 text-sm font-medium transition-all rounded-t-lg border-b-2 ${
              activeTab === tab.id
                ? "text-blue-400 border-blue-500 bg-blue-500/5"
                : "text-slate-500 border-transparent hover:text-slate-300 hover:bg-slate-800/50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="mt-1">
        {activeTab === "management" && (
          <TabManagement locators={locators} loading={loading} refresh={refresh} projectId={projectId} />
        )}
        {activeTab === "stability" && (
          <TabStability locators={locators} />
        )}
        {activeTab === "fallback" && (
          <TabFallback />
        )}
        {activeTab === "pom" && (
          <TabPOM locators={locators} />
        )}
        {activeTab === "breakage" && (
          <TabBreakage locators={locators} />
        )}
      </div>
      <PageFeedbackWidget />

    </div>
  );
}
