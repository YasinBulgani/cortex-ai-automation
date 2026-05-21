"use client";

import { useCallback, useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { apiFetch } from "@/lib/api";

type Baseline = {
  id: string;
  page: string;
  url?: string;
  created_at: string;
  thumbnail?: string;
};

type CompareResult = {
  page?: string;
  page_name?: string;
  status: "pass" | "fail" | "error";
  diff_percent?: number;
  baseline_image_url?: string;
  current_image_url?: string;
  diff_image_url?: string;
  ai_summary?: string;
};

function StatusBadge({ status }: { status: string }) {
  const cfg =
    status === "pass"
      ? "border-emerald-600/30 bg-emerald-500/10 text-emerald-400"
      : status === "fail"
        ? "border-red-600/30 bg-red-500/10 text-red-400"
        : "border-slate-600/30 bg-slate-700/20 text-slate-400";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${cfg}`}>
      {status === "pass" ? "✓ Pass" : status === "fail" ? "✗ Fail" : status}
    </span>
  );
}

function DiffBar({ pct }: { pct: number }) {
  const color = pct === 0 ? "bg-emerald-500" : pct < 1 ? "bg-yellow-500" : pct < 5 ? "bg-orange-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${Math.min(pct * 10, 100)}%` }} />
      </div>
      <span className={`text-xs font-mono ${pct === 0 ? "text-emerald-400" : pct < 1 ? "text-yellow-400" : "text-red-400"}`}>
        {pct.toFixed(2)}%
      </span>
    </div>
  );
}

export default function VisualRegressionPage() {
  const projectId = useRouteParam("projectId");
  const [baselines, setBaselines] = useState<Baseline[]>([]);
  const [loading, setLoading] = useState(true);
  const [url, setUrl] = useState("");
  const [selectedPage, setSelectedPage] = useState("");
  const [comparing, setComparing] = useState(false);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState("");

  const loadBaselines = useCallback(() => {
    setLoading(true);
    apiFetch<Baseline[]>(`/api/v1/tspm/projects/${projectId}/visual/baselines`)
      .then(data => setBaselines(data || []))
      .catch(() => setBaselines([]))
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => { loadBaselines(); }, [loadBaselines]);

  async function handleCompare() {
    if (!url.trim() || !selectedPage) { setError("URL ve sayfa seçimi gerekli"); return; }
    setComparing(true);
    setError("");
    setResult(null);
    try {
      const res = await apiFetch<CompareResult>(
        `/api/v1/tspm/projects/${projectId}/visual/compare`,
        { method: "POST", json: { url: url.trim(), page_name: selectedPage, threshold: 1.0 } },
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Karşılaştırma hatası");
    } finally {
      setComparing(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/visual/baselines/${id}`, { method: "DELETE" });
      loadBaselines();
    } catch { /* ignore */ }
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="visual-regression-page">
      <PageHeader
        icon={<span className="text-base">👁</span>}
        title="Visual Regression"
        description="Baseline yönetimi ve görsel karşılaştırma"
        right={
          <div className="text-center text-xs text-slate-500">
            <p className="text-base font-bold text-white">{baselines.length}</p>
            <p>Baseline</p>
          </div>
        }
      />

      {/* Compare */}
      <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4 space-y-3">
        <h3 className="text-sm font-semibold text-white">Karşılaştırma</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://uygulama.com/sayfa"
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none" />
          <select value={selectedPage} onChange={e => setSelectedPage(e.target.value)}
            title="Baseline sayfası seçimi"
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none">
            <option value="">— Baseline Seçin —</option>
            {baselines.map(b => <option key={b.id} value={b.page}>{b.page}</option>)}
          </select>
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
        <button onClick={handleCompare} disabled={comparing || !url.trim() || !selectedPage}
          className="w-full rounded-xl py-2.5 text-sm font-semibold transition bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-500 hover:to-purple-500 disabled:opacity-40">
          {comparing ? "Karşılaştırılıyor..." : "🔍 Karşılaştır"}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className={`rounded-xl border p-4 space-y-4 ${result.status === "pass" ? "border-emerald-700/40 bg-emerald-950/20" : "border-red-700/40 bg-red-950/20"}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <StatusBadge status={result.status} />
              <span className="text-sm font-semibold text-white">{result.page || result.page_name || selectedPage}</span>
            </div>
            <div className="w-40"><DiffBar pct={result.diff_percent ?? 0} /></div>
          </div>
          {result.ai_summary && (
            <div className="rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2">
              <p className="text-xs text-slate-300">{result.ai_summary}</p>
            </div>
          )}
          <div className="grid grid-cols-3 gap-3">
            {[
              { src: result.baseline_image_url, label: "Baseline" },
              { src: result.current_image_url, label: "Güncel" },
              { src: result.diff_image_url, label: "Diff" },
            ].map(img => (
              <div key={img.label} className="rounded-xl border border-slate-700 overflow-hidden">
                <div className="bg-slate-800/60 px-3 py-1.5 border-b border-slate-700 text-xs text-slate-400">{img.label}</div>
                {img.src ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={img.src} alt={img.label} className="w-full max-h-48 object-contain bg-slate-950" />
                ) : (
                  <div className="flex items-center justify-center h-32 text-slate-600 text-xs">Görsel yok</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Baselines list */}
      <div className="rounded-xl border border-slate-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700 bg-slate-800/30 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Baseline&apos;lar</h3>
          <span className="text-xs text-slate-500">{baselines.length} kayıt</span>
        </div>
        {loading ? (
          <div className="p-8 text-center text-sm text-slate-500">Yükleniyor...</div>
        ) : baselines.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">Henüz baseline yok</div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-800 bg-slate-900/40">
              <tr>
                <th className="px-4 py-2 text-xs font-medium text-slate-400">Sayfa</th>
                <th className="px-4 py-2 text-xs font-medium text-slate-400">Tarih</th>
                <th className="px-4 py-2 text-xs font-medium text-slate-400 w-16" />
              </tr>
            </thead>
            <tbody>
              {baselines.map(b => (
                <tr key={b.id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                  <td className="px-4 py-2.5 text-white text-xs font-medium">{b.page}</td>
                  <td className="px-4 py-2.5 text-xs text-slate-500">{new Date(b.created_at).toLocaleDateString("tr-TR")}</td>
                  <td className="px-4 py-2.5">
                    <button onClick={() => handleDelete(b.id)}
                      className="text-xs text-red-400 hover:text-red-300 transition">Sil</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
