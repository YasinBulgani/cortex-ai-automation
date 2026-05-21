"use client";

import { useEffect, useState } from "react";
import { apiFetch, ENGINE_BASE } from "@/lib/api";
import {
  PageHeader,
  SectionCard,
  EmptyState,
} from "@/components/nexus";

type Dataset = {
  id: string;
  name: string;
  emoji: string;
  desc: string;
  tags: string[];
  rows: number;
  cols: number;
  columns: string;
};

export default function SyntheticPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [selectedId, setSelectedId] = useState("");
  const [sampleRows, setSampleRows] = useState(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ csv?: string; columns?: string[]; rows?: number; name?: string } | null>(null);

  useEffect(() => {
    fetch(`${ENGINE_BASE}/api/datasim/datasets`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(d => { setDatasets(Array.isArray(d) ? d : []); setLoadingCatalog(false); })
      .catch(() => setLoadingCatalog(false));
  }, []);

  async function generate() {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${ENGINE_BASE}/api/datasim/datasets/load`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: selectedId, sample_rows: sampleRows }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.error) setError(data.error);
      else setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Engine bağlantı hatası");
    } finally {
      setLoading(false);
    }
  }

  const selected = datasets.find(d => d.id === selectedId);

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="synthetic-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
          </svg>
        }
        title="Sentetik Veri"
        description="Gerçekçi örnek veri üret"
      />

      <SectionCard
        title="Veri Seti Kataloğu"
        right={!loadingCatalog && <span className="text-xs text-slate-500">{datasets.length} veri seti</span>}
      >
        {loadingCatalog ? (
          <div className="flex items-center gap-2 py-4">
            <div className="w-4 h-4 border-2 border-slate-600 border-t-slate-400 rounded-full animate-spin" />
            <span className="text-sm text-slate-400">Katalog yükleniyor…</span>
          </div>
        ) : datasets.length === 0 ? (
          <EmptyState icon="📦" title="Katalog boş" description="Engine bağlantısı kurulamadı veya veri seti bulunamadı" />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {datasets.map(ds => (
              <button
                key={ds.id}
                type="button"
                onClick={() => setSelectedId(ds.id === selectedId ? "" : ds.id)}
                className={`rounded-xl border p-4 text-left transition-all ${
                  selectedId === ds.id
                    ? "border-blue-500/40 bg-blue-500/5 ring-1 ring-blue-500/30"
                    : "border-slate-700 bg-slate-900/40 hover:border-slate-600 hover:bg-slate-800/30"
                }`}
              >
                <div className="flex items-start gap-2">
                  <span className="text-2xl">{ds.emoji}</span>
                  <div className="min-w-0 flex-1">
                    <p className={`font-semibold text-sm ${selectedId === ds.id ? "text-blue-300" : "text-white"}`}>{ds.name}</p>
                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{ds.desc}</p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {ds.tags.slice(0, 3).map(t => (
                        <span key={t} className="px-1.5 py-0.5 rounded border border-slate-700 bg-slate-800 text-[10px] text-slate-400">{t}</span>
                      ))}
                    </div>
                    <p className="mt-1.5 text-[10px] text-slate-600">{ds.rows} satır · {ds.cols} sütun</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </SectionCard>

      {selected && (
        <SectionCard title={selected.name} icon={<span className="text-base">{selected.emoji}</span>}>
          <div className="flex items-end gap-4">
            <div className="flex-1 flex flex-col gap-2">
              <label htmlFor="syn-rows" className="text-sm font-medium text-slate-300">Satır Sayısı ({sampleRows})</label>
              <input id="syn-rows" type="range" min={10} max={300} step={10} value={sampleRows} onChange={e => setSampleRows(Number(e.target.value))} className="accent-blue-500" />
            </div>
            <button
              type="button"
              onClick={generate}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50"
            >
              {loading && <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
              {loading ? "Yükleniyor…" : "Veri Üret"}
            </button>
          </div>
        </SectionCard>
      )}

      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>
      )}

      {result && (
        <SectionCard
          title={result.name ?? "Önizleme"}
          right={<span className="text-xs text-slate-500">{result.rows} satır · {result.columns?.length} sütun</span>}
        >
          <div className="overflow-auto max-h-64 rounded-lg border border-slate-700 bg-slate-900">
            <pre className="p-4 text-xs text-slate-300 whitespace-pre font-mono">
              {result.csv?.split("\n").slice(0, 20).join("\n")}
            </pre>
          </div>
          {(result.csv?.split("\n").length ?? 0) > 20 && (
            <p className="text-xs text-slate-500 mt-2">İlk 20 satır gösteriliyor.</p>
          )}
        </SectionCard>
      )}
    </div>
  );
}
