"use client";

import { useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { EmptyState } from "@/components/nexus/EmptyState";
import {
  useNLGenerate,
  type NLTestResult,
  type NLTestRequest,
} from "@/lib/hooks/use-synthetic-advanced";

const FORMATS: { value: NLTestRequest["format"]; label: string }[] = [
  { value: "pytest", label: "🐍 Pytest" },
  { value: "playwright", label: "🎭 Playwright" },
  { value: "cypress", label: "🌲 Cypress" },
  { value: "gherkin", label: "🥒 Gherkin" },
];

const LANGUAGES: { value: NLTestRequest["language"]; label: string }[] = [
  { value: "python", label: "Python" },
  { value: "typescript", label: "TypeScript" },
  { value: "javascript", label: "JavaScript" },
];

export default function NLTestGenPage() {
  const projectId = useRouteParam("projectId");
  const [text, setText] = useState("");
  const [format, setFormat] = useState<NLTestRequest["format"]>("pytest");
  const [language, setLanguage] = useState<NLTestRequest["language"]>("python");
  const [results, setResults] = useState<NLTestResult[]>([]);
  const [copied, setCopied] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const genMut = useNLGenerate(projectId);

  async function handleGenerate() {
    if (!text.trim()) return;
    try {
      setError(null);
      const result = await genMut.mutateAsync({ text, format, language });
      setResults((prev) => [result, ...prev]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Test uretimi basarisiz oldu.");
    }
  }

  function copyCode(code: string, id: string) {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(id);
      setTimeout(() => setCopied(null), 2000);
    });
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="nl-test-gen-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        }
        title="Dogal Dil Test Uretici"
        description="Turkce veya Ingilizce metin yazin, AI test kodu uretsin"
      />

      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-5">
        <p className="text-sm font-medium text-cyan-300 mb-3">Test Tanimi</p>

        <div className="flex flex-wrap gap-3 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Format:</span>
            <div className="flex gap-1">
              {FORMATS.map((f) => (
                <button
                  key={f.value}
                  onClick={() => setFormat(f.value)}
                  className={`px-2.5 py-1 text-xs rounded-lg border transition-all ${
                    format === f.value
                      ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-300"
                      : "border-slate-700 text-slate-400 hover:text-white"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Dil:</span>
            <div className="flex gap-1">
              {LANGUAGES.map((l) => (
                <button
                  key={l.value}
                  onClick={() => setLanguage(l.value)}
                  className={`px-2.5 py-1 text-xs rounded-lg border transition-all ${
                    language === l.value
                      ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-300"
                      : "border-slate-700 text-slate-400 hover:text-white"
                  }`}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Orn: Kullanici giris yapar, gecersiz sifre girerse hata mesaji gorur..."
            rows={3}
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-500 resize-none"
          />
          <button
            onClick={handleGenerate}
            disabled={!text.trim() || genMut.isPending}
            className="px-5 py-2 text-sm font-semibold text-cyan-300 border border-cyan-500/30 rounded-xl hover:bg-cyan-500/10 transition-all disabled:opacity-50 self-end"
          >
            {genMut.isPending ? (
              <div className="w-4 h-4 border-2 border-cyan-300/30 border-t-cyan-300 rounded-full animate-spin" />
            ) : (
              "Uret"
            )}
          </button>
        </div>
      </div>

      {/* Loading */}
      {genMut.isPending && (
        <div className="rounded-xl border border-cyan-500/20 bg-slate-900/40 p-6 flex items-center justify-center gap-3">
          <div className="w-5 h-5 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
          <span className="text-sm text-cyan-300">AI test kodu uretiyor...</span>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-white">Uretilen Testler ({results.length})</h3>
            <button onClick={() => setResults([])} className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
              Temizle
            </button>
          </div>
          {results.map((r) => (
            <div key={r.test_id} className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-white">{r.test_name}</span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400">{r.format}</span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400">{r.language}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-slate-400">{(r.confidence * 100).toFixed(0)}%</span>
                  <button
                    onClick={() => copyCode(r.test_code, r.test_id)}
                    className="px-2.5 py-1 text-xs border border-slate-700 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-all"
                  >
                    {copied === r.test_id ? "Kopyalandi!" : "Kopyala"}
                  </button>
                </div>
              </div>
              <pre className="p-4 text-xs text-emerald-300 overflow-auto max-h-72 bg-slate-950/50">
                <code>{r.test_code}</code>
              </pre>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!genMut.isPending && results.length === 0 && (
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-16">
          <EmptyState
            icon="✍️"
            title="Dogal Dil ile Test Ureti"
            description="Turkce veya Ingilizce bir test tanimi yazin, AI otomatik olarak calistirabilir test kodu uretsin"
          />
        </div>
      )}
    </div>
  );
}
