"use client";

type Mode = "code" | "web" | "bitbucket";

const MODE_META: Record<Mode, { label: string; icon: string; desc: string }> = {
  code: { label: "Kod Analizi", icon: "</>", desc: "Yapıştır & analiz et" },
  web: { label: "Web Analizi", icon: "⊕", desc: "URL veya sayfa açıkla" },
  bitbucket: { label: "Bitbucket", icon: "⑃", desc: "Private repo'dan çek" },
};

interface NexusHeroHeaderProps {
  mode: Mode;
  onModeChange: (mode: Mode) => void;
}

export function NexusHeroHeader({ mode, onModeChange }: NexusHeroHeaderProps) {
  return (
    <div className="relative overflow-hidden border-b border-slate-800/70 bg-slate-950/60 px-6 py-8">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(139,92,246,0.12)_0%,transparent_60%)]" />
      <div className="mx-auto max-w-screen-2xl">
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border border-violet-400/30 bg-gradient-to-br from-violet-600/30 to-violet-900/30 shadow-[0_0_40px_rgba(139,92,246,0.25)]">
              <span className="text-xl font-black tracking-tight text-violet-100">N</span>
              <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full border-2 border-slate-950 bg-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-black tracking-tight text-white">Neurex Code</h1>
                <span className="rounded-full border border-violet-400/20 bg-violet-500/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-violet-300">
                  Beta
                </span>
              </div>
              <p className="mt-0.5 text-sm text-slate-400">
                Senior QA · Automation Architect · Product Analyst — Lokal Ollama
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-900/60 px-3 py-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              <span className="text-xs text-slate-300">qwen2.5-coder · local</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-900/60 px-3 py-1.5">
              <span className="h-2 w-2 rounded-full bg-violet-400" />
              <span className="text-xs text-slate-300">Ollama bağlı</span>
            </div>
          </div>
        </div>

        {/* Mode selector */}
        <div className="mt-6 flex flex-wrap gap-2">
          {(Object.keys(MODE_META) as Mode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => onModeChange(m)}
              className={`flex items-center gap-2 rounded-xl border px-5 py-2.5 text-sm font-semibold transition ${
                mode === m
                  ? "border-violet-300/50 bg-violet-500/20 text-violet-50 shadow-[0_0_20px_rgba(139,92,246,0.2)]"
                  : "border-slate-700/80 bg-slate-900/40 text-slate-400 hover:border-slate-600 hover:bg-slate-900/70 hover:text-slate-200"
              }`}
            >
              <span className="font-mono text-base">{MODE_META[m].icon}</span>
              <span>{MODE_META[m].label}</span>
              <span className={`text-[10px] font-normal ${mode === m ? "text-violet-300" : "text-slate-600"}`}>
                {MODE_META[m].desc}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
