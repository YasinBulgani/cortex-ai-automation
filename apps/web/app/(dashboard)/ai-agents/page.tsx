"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AGENT_CATEGORIES, AGENTS_BY_CATEGORY, type AIAgent } from "./agents-data";
import { useAgentRecentRuns, useRunAgentV2, useAgentsCatalog } from "@/lib/hooks/use-agents";

const AVAILABILITY_META = {
  active: { label: "Active", className: "border-emerald-400/20 bg-emerald-500/10 text-emerald-200" },
  beta: { label: "Beta", className: "border-amber-400/20 bg-amber-500/10 text-amber-200" },
  experimental: { label: "Deneysel", className: "border-violet-400/20 bg-violet-500/10 text-violet-200" },
} as const;

// ── Quick Run Modal (Nexus Code Agent v2) ────────────────────────────────────
interface RunModalProps {
  agent: AIAgent;
  onClose: () => void;
}

function RunModal({ agent, onClose }: RunModalProps) {
  const [inputSource, setInputSource] = useState<"url" | "text">("url");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [projectId] = useState("default");
  const { mutateAsync, isPending, data, isSuccess, isError, error } = useRunAgentV2();

  async function handleRun() {
    await mutateAsync({
      project_id: projectId,
      input_source: inputSource,
      url: inputSource === "url" ? url : undefined,
      text: inputSource === "text" ? text : undefined,
    });
  }

  return (
    <>
      <div className="fixed inset-0 z-[9998] bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 z-[9999] w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
        <div className="mb-4 flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-violet-400/30 bg-violet-500/10 text-xl">
            {agent.emoji}
          </span>
          <div>
            <h2 className="text-base font-semibold text-white">{agent.name} — Hızlı Çalıştır</h2>
            <p className="text-xs text-slate-400">{agent.tagline}</p>
          </div>
          <button onClick={onClose} className="ml-auto text-slate-500 hover:text-slate-300">✕</button>
        </div>

        {!isSuccess ? (
          <div className="space-y-4">
            {/* Input source tabs */}
            <div className="flex gap-1 rounded-lg border border-slate-700 bg-slate-800/50 p-1">
              {(["url", "text"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setInputSource(s)}
                  className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${inputSource === s ? "bg-violet-600 text-white" : "text-slate-400 hover:text-slate-200"}`}
                >
                  {s === "url" ? "🌐 URL" : "📝 Metin"}
                </button>
              ))}
            </div>

            {inputSource === "url" ? (
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Sayfa URL'si</label>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com/login"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
            ) : (
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Analiz metni / bağlam</label>
                <textarea
                  rows={4}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Analiz edilmesini istediğiniz metni buraya yapıştırın..."
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
            )}

            {isError && (
              <p className="rounded-lg border border-red-400/20 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                {(error as Error)?.message ?? "Çalıştırma başlatılamadı."}
              </p>
            )}

            <div className="flex justify-end gap-2">
              <button onClick={onClose} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-600 hover:text-white">
                İptal
              </button>
              <button
                onClick={handleRun}
                disabled={isPending || (inputSource === "url" ? !url : !text)}
                className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isPending ? "Başlatılıyor…" : "Çalıştır →"}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="rounded-lg border border-emerald-400/20 bg-emerald-500/10 p-4">
              <p className="text-sm font-semibold text-emerald-300">✓ Pipeline kuyruğa eklendi</p>
              <p className="mt-1 text-xs text-slate-400">Run ID: <code className="font-mono text-slate-300">{data?.run_id}</code></p>
              <p className="text-xs text-slate-400">Durum: <span className="capitalize text-slate-300">{data?.status}</span></p>
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={onClose} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:text-white">
                Kapat
              </button>
              <Link
                href="/nexus-code"
                className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500"
              >
                Nexus Code'da Takip Et →
              </Link>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function AIAgentsHubPage() {
  const router = useRouter();
  const [runModalAgent, setRunModalAgent] = useState<AIAgent | null>(null);
  const { data: runsData } = useAgentRecentRuns(5);
  const { agents: liveAgents, isLive } = useAgentsCatalog();

  const totalRuns = runsData?.total ?? 0;
  const totalAgents = isLive ? liveAgents.length : AGENTS_BY_CATEGORY.reduce((sum, c) => sum + c.agents.length, 0);

  function handleAgentAction(agent: AIAgent) {
    if (agent.globalHref) {
      if (agent.id === "code-analyzer") {
        setRunModalAgent(agent);
      } else {
        router.push(agent.globalHref);
      }
    } else {
      router.push(`/ai-agents/${agent.id}`);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6">
      {runModalAgent && (
        <RunModal agent={runModalAgent} onClose={() => setRunModalAgent(null)} />
      )}

      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <header className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl border border-violet-400/30 bg-violet-500/10 text-2xl">🤖</span>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-white">Neurex AI Ajanları</h1>
              <p className="mt-1 text-sm text-slate-400">
                Test kalitesi, kod analizi, gözlemleme ve veri için akıllı ajanlar — tek katalogda
              </p>
            </div>
          </div>
          <div className="flex gap-2 flex-wrap">
            <span className="rounded-full border border-violet-400/20 bg-violet-500/10 px-3 py-1.5 text-xs font-medium text-violet-100">
              {totalAgents} Ajan
            </span>
            <span className={`rounded-full border px-3 py-1.5 text-xs font-medium ${isLive ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-300" : "border-slate-700 bg-slate-800 text-slate-400"}`}>
              {isLive ? "🟢 Canlı" : "⚪ Demo"}
            </span>
            {totalRuns > 0 && (
              <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-200">
                {totalRuns} Toplam Çalıştırma
              </span>
            )}
            <Link
              href="/portfolio"
              className="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-slate-500"
            >
              📊 Portföy
            </Link>
          </div>
        </header>

        {/* Recent runs strip */}
        {runsData && runsData.runs.length > 0 && (
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Son Çalıştırmalar</p>
            <div className="flex gap-2 flex-wrap">
              {runsData.runs.map((run) => (
                <div
                  key={run.run_id}
                  className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-1.5"
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${
                    run.status === "completed" ? "bg-emerald-400" :
                    run.status === "failed" ? "bg-red-400" :
                    run.status === "running" ? "bg-blue-400 animate-pulse" :
                    "bg-amber-400"
                  }`} />
                  <span className="text-xs text-slate-300 font-mono">{run.run_id.slice(0, 8)}</span>
                  <span className="text-[10px] text-slate-500">{run.input_source}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Categories */}
        {AGENTS_BY_CATEGORY.filter((c) => c.agents.length > 0).map((cat) => (
          <section key={cat.key} className="rounded-2xl border border-slate-800 bg-slate-950/65 p-6">
            <div className="mb-4 flex items-center gap-2">
              <span className="text-xl">{cat.meta.emoji}</span>
              <h2 className="text-lg font-semibold text-white">{cat.meta.label}</h2>
              <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${cat.meta.color}`}>
                {cat.agents.length} ajan
              </span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {cat.agents.map((agent) => {
                const href = agent.globalHref ?? `/ai-agents/${agent.id}`;
                const isGlobal = !!agent.globalHref;
                return (
                  <div
                    key={agent.id}
                    className="group rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition hover:border-violet-400/40 hover:bg-violet-500/5 relative flex flex-col"
                    data-testid={`agent-card-${agent.id}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">{agent.emoji}</span>
                        <p className="text-sm font-semibold text-white group-hover:text-violet-100">{agent.name}</p>
                      </div>
                      <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[9px] font-semibold ${AVAILABILITY_META[agent.availability].className}`}>
                        {AVAILABILITY_META[agent.availability].label}
                      </span>
                    </div>
                    <p className="mt-2 flex-1 text-xs leading-5 text-slate-400">{agent.tagline}</p>
                    <div className="mt-3 flex items-center justify-between gap-2">
                      <span className={`text-[10px] ${isGlobal ? "text-emerald-300" : "text-amber-300"}`}>
                        {isGlobal ? "🌐 Genel araç" : "📁 Proje gerekli"}
                      </span>
                      <div className="flex gap-1.5">
                        <Link
                          href={href}
                          className="rounded-md border border-slate-700 px-2 py-1 text-[10px] font-medium text-slate-400 hover:border-slate-500 hover:text-slate-200 transition-colors"
                        >
                          Detay
                        </Link>
                        <button
                          onClick={() => handleAgentAction(agent)}
                          className="rounded-md bg-violet-600/80 px-2 py-1 text-[10px] font-semibold text-white hover:bg-violet-600 transition-colors"
                        >
                          {isGlobal ? (agent.id === "code-analyzer" ? "Çalıştır" : "Aç →") : "Seç →"}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ))}

        {/* Footer info */}
        <div className="rounded-2xl border border-blue-400/20 bg-blue-500/5 p-4 text-sm text-blue-100/90">
          <p className="font-semibold">ℹ️ Ajan Türleri</p>
          <p className="mt-1 text-xs leading-5 text-blue-100/70">
            🌐 <strong>Genel araçlar</strong> proje seçmeden kullanılır. 📁 <strong>Proje gerektiren ajanlar</strong> proje bağlamında çalışır — ajan detay sayfasından proje seçebilirsiniz.
          </p>
        </div>
      </div>
    </div>
  );
}
