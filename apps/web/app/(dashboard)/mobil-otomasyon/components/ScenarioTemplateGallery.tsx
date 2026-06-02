"use client";

type Platform = "android" | "ios";

export type SeedScenario = {
  id: string;
  title: string;
  category: string;
  difficulty: "kolay" | "orta" | "zor";
  platforms: string[];
  description: string;
  prompt: string;
  expected_steps: number;
  tags: string[];
};

export interface ScenarioTemplateGalleryProps {
  seedScenarios: SeedScenario[];
  seedFilter: string;
  onFilterChange: (cat: string) => void;
  onSelectScenario: (scenario: SeedScenario) => void;
}

export function ScenarioTemplateGallery({
  seedScenarios,
  seedFilter,
  onFilterChange,
  onSelectScenario,
}: ScenarioTemplateGalleryProps) {
  if (seedScenarios.length === 0) return null;

  return (
    <section className="rounded-lg border border-slate-800 overflow-hidden">
      <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-3 flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-sm font-semibold">📚 Senaryo Galerisi</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Production-benzeri {seedScenarios.length} hazır senaryo — tıkla, prompt otomatik dolsun
          </p>
        </div>
        <div className="flex gap-1 flex-wrap">
          {["all", ...Array.from(new Set(seedScenarios.map((s) => s.category)))].map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => onFilterChange(cat)}
              className={`rounded-full border px-2.5 py-0.5 text-[10px] font-medium transition-colors
                ${seedFilter === cat
                  ? "border-blue-500/60 bg-blue-500/10 text-blue-300"
                  : "border-slate-800 text-slate-400 hover:border-slate-600"}`}
            >
              {cat === "all" ? "Tümü" : cat}
            </button>
          ))}
        </div>
      </div>
      <div className="p-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {seedScenarios
          .filter((s) => seedFilter === "all" || s.category === seedFilter)
          .map((s) => {
            const diffColor = s.difficulty === "kolay"
              ? "text-emerald-300 border-emerald-500/30 bg-emerald-500/5"
              : s.difficulty === "orta"
                ? "text-amber-300 border-amber-500/30 bg-amber-500/5"
                : "text-red-300 border-red-500/30 bg-red-500/5";
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => onSelectScenario(s)}
                className="group rounded-lg border border-slate-800 bg-slate-900/20 hover:border-blue-500/40 hover:bg-blue-500/5 p-3 text-left transition-colors space-y-1.5"
              >
                <div className="flex items-start justify-between gap-1">
                  <p className="text-[12px] font-semibold truncate group-hover:text-blue-300">{s.title}</p>
                  <span className={`shrink-0 rounded border px-1.5 text-[9px] font-medium ${diffColor}`}>
                    {s.difficulty}
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 leading-snug line-clamp-2">{s.description}</p>
                <div className="flex items-center gap-1 flex-wrap pt-1">
                  <span className="rounded bg-slate-800/60 px-1.5 py-0.5 text-[9px] text-slate-400">{s.category}</span>
                  {s.platforms.map((p) => (
                    <span key={p} className="text-[10px]">{p === "ios" ? "" : "🤖"}</span>
                  ))}
                  <span className="ml-auto text-[9px] text-slate-500">~{s.expected_steps} adım</span>
                </div>
              </button>
            );
          })}
      </div>
    </section>
  );
}
