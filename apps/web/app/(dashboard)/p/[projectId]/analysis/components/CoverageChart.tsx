"use client";

/**
 * CoverageChart — AI analiz sonucu modül kapsama görselleştirmesi.
 *
 * Sorumluluklar:
 *  - Analiz sonucundaki modülleri kart grid olarak gösterir
 *  - Risk seviyesine göre renk kodlaması (high / medium / low)
 *  - Her modül için test alanları ve tahmini test case sayısı
 */

interface AnalysisModule {
  name?: string;
  description?: string;
  risk_level?: string;
  test_areas?: string[];
  estimated_test_cases?: number;
}

interface CoverageChartProps {
  modules: AnalysisModule[];
}

export function CoverageChart({ modules }: CoverageChartProps) {
  if (modules.length === 0) return null;

  return (
    <div
      data-testid="analysis-modules-result"
      className="rounded-lg border border-emerald-700/30 bg-emerald-950/20 p-4 space-y-3"
    >
      <h3 className="text-sm font-semibold text-emerald-200">
        AI Analiz Sonucu — {modules.length} modül tespit edildi
      </h3>
      <div className="grid gap-2 sm:grid-cols-2">
        {modules.map((m, idx) => (
          <div
            key={idx}
            className="rounded border border-emerald-800/30 bg-slate-900/40 p-3 text-xs"
          >
            <div className="flex items-start justify-between gap-2 mb-1">
              <strong className="text-white">{m.name || `Modül ${idx + 1}`}</strong>
              <span
                className={`text-[10px] uppercase px-1.5 py-0.5 rounded ${
                  m.risk_level === "high"
                    ? "bg-red-500/20 text-red-300"
                    : m.risk_level === "medium"
                    ? "bg-amber-500/20 text-amber-300"
                    : "bg-slate-600/30 text-slate-300"
                }`}
              >
                {m.risk_level || "?"}
              </span>
            </div>
            {m.description && (
              <p className="text-slate-300 mb-1.5">{m.description}</p>
            )}
            {Array.isArray(m.test_areas) && m.test_areas.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {m.test_areas.slice(0, 6).map((a, i) => (
                  <span
                    key={i}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300"
                  >
                    {a}
                  </span>
                ))}
              </div>
            )}
            {typeof m.estimated_test_cases === "number" && (
              <p className="text-[10px] text-emerald-300 mt-1.5">
                ≈ {m.estimated_test_cases} test case
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
