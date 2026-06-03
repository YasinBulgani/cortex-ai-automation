"use client";

import { useState, useRef } from "react";

interface SimilarCase {
  case_id: string;
  case_key: string;
  title: string;
  similarity: number;
  suite_name?: string;
  status?: string;
  last_run_status?: string;
}

interface AISimilaritySearchProps {
  projectId: string;
  onSelectCase?: (caseId: string) => void;
}

export function AISimilaritySearch({ projectId, onSelectCase }: AISimilaritySearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SimilarCase[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSearch = async () => {
    if (!query.trim() || query.trim().length < 3) return;
    setLoading(true);
    setError("");
    setSearched(false);
    try {
      const res = await fetch(
        `/api/v1/test-management/projects/${projectId}/cases/search-similar`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ query: query.trim(), limit: 10 }),
        }
      );
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      setResults(Array.isArray(data) ? data : data.results ?? []);
      setSearched(true);
    } catch {
      setError("Arama başarısız. Backend bağlantısını kontrol edin.");
    } finally {
      setLoading(false);
    }
  };

  const similarityColor = (s: number) =>
    s >= 0.85 ? "text-emerald-400" :
    s >= 0.65 ? "text-amber-400" :
    "text-slate-400";

  const similarityLabel = (s: number) =>
    s >= 0.85 ? "Çok benzer" :
    s >= 0.65 ? "Benzer" :
    "Kısmen benzer";

  if (!open) {
    return (
      <button
        onClick={() => { setOpen(true); setTimeout(() => inputRef.current?.focus(), 50); }}
        className="flex items-center gap-2 rounded-xl border border-violet-500/30 bg-violet-500/10 hover:bg-violet-500/20 px-4 py-2 text-sm font-medium text-violet-300 transition-colors"
      >
        ✨ AI ile Benzer Case Bul
      </button>
    );
  }

  return (
    <div className="rounded-xl border border-violet-500/30 bg-surface-raised overflow-hidden">
      {/* Arama başlığı */}
      <div className="flex items-center gap-3 border-b border-border px-4 py-3">
        <span className="text-violet-400 text-lg">✨</span>
        <span className="text-sm font-semibold text-white">AI Semantic Arama</span>
        <span className="text-xs text-slate-500 flex-1">Doğal dilde tanımla, benzer case'leri bul</span>
        <button onClick={() => setOpen(false)} className="text-slate-500 hover:text-white text-sm">✕</button>
      </div>

      {/* Input */}
      <div className="p-4 space-y-3">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder='Örnek: "ödeme sayfası kart doğrulama" veya "login başarısız senaryo"'
            className="flex-1 rounded-lg bg-surface-overlay border border-border px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500 transition-colors"
          />
          <button
            onClick={handleSearch}
            disabled={loading || query.trim().length < 3}
            className="rounded-lg bg-violet-600 hover:bg-violet-700 disabled:opacity-40 px-4 py-2 text-sm font-semibold text-white transition-colors whitespace-nowrap"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Arıyor…
              </span>
            ) : "Ara"}
          </button>
        </div>

        {error && <p className="text-xs text-red-400">{error}</p>}

        {/* Sonuçlar */}
        {searched && results.length === 0 && (
          <div className="py-6 text-center text-slate-500 text-sm">
            Benzer case bulunamadı. Farklı bir ifade deneyin.
          </div>
        )}

        {results.length > 0 && (
          <div className="space-y-2 max-h-72 overflow-y-auto">
            <p className="text-xs text-slate-500">{results.length} benzer case bulundu:</p>
            {results.map((c) => (
              <div
                key={c.case_id}
                className="flex items-center gap-3 rounded-lg border border-border bg-surface-overlay px-3 py-2.5 hover:border-violet-500/30 transition-colors group"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    {c.case_key && (
                      <span className="text-xs font-mono text-slate-500 shrink-0">{c.case_key}</span>
                    )}
                    <span className="text-sm text-white truncate">{c.title}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-1">
                    <span className={`text-xs font-medium ${similarityColor(c.similarity)}`}>
                      {similarityLabel(c.similarity)} ({(c.similarity * 100).toFixed(0)}%)
                    </span>
                    {c.suite_name && (
                      <span className="text-xs text-slate-500 truncate">{c.suite_name}</span>
                    )}
                    {c.last_run_status && (
                      <span className={`text-xs ${
                        c.last_run_status === "pass" ? "text-emerald-400" :
                        c.last_run_status === "fail" ? "text-red-400" : "text-slate-400"
                      }`}>
                        {c.last_run_status}
                      </span>
                    )}
                  </div>
                  {/* Benzerlik çubuğu */}
                  <div className="mt-1.5 h-1 rounded-full bg-slate-700 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-violet-500 transition-all"
                      style={{ width: `${c.similarity * 100}%` }}
                    />
                  </div>
                </div>
                {onSelectCase && (
                  <button
                    onClick={() => onSelectCase(c.case_id)}
                    className="shrink-0 opacity-0 group-hover:opacity-100 rounded-lg bg-violet-600 hover:bg-violet-700 px-2.5 py-1 text-xs font-medium text-white transition-all"
                  >
                    Seç
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
