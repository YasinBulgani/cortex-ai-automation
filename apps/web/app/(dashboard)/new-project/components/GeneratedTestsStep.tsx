"use client";

import type { ManualTest, BddScenario } from "../types";

interface GeneratedTestsStepProps {
  manualTests: ManualTest[];
  bddScenarios: BddScenario[];
  loading: boolean;
  onSaveAll: () => void;
}

export function GeneratedTestsStep({
  manualTests,
  bddScenarios,
  loading,
  onSaveAll,
}: GeneratedTestsStepProps) {
  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-bold">Üretilen Testler</h2>
          <p className="mt-1 text-sm text-slate-400">
            AI <span className="text-blue-400 font-medium">{manualTests.length} manuel test</span> ve{" "}
            <span className="text-purple-400 font-medium">{bddScenarios.length} BDD senaryo</span> üretti.
          </p>
        </div>
        <button
          onClick={onSaveAll}
          disabled={loading}
          className="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-40"
        >
          {loading ? "Kaydediliyor…" : `Tümünü Kaydet (${manualTests.length + bddScenarios.length})`}
        </button>
      </div>

      {/* Manuel testler */}
      {manualTests.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Manuel Testler</h3>
          {manualTests.map((t, i) => (
            <div key={i} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="text-sm font-semibold text-white mb-3">{t.title}</p>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500">
                    <th className="w-6 text-left pb-2">#</th>
                    <th className="text-left pb-2">Aksiyon</th>
                    <th className="text-left pb-2">Beklenen Sonuç</th>
                  </tr>
                </thead>
                <tbody>
                  {t.steps.map((s, j) => (
                    <tr key={j} className="border-t border-slate-800">
                      <td className="py-2 text-slate-600">{j + 1}</td>
                      <td className="py-2 text-slate-300">{s.action}</td>
                      <td className="py-2 text-emerald-400">{s.expected}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {/* BDD Senaryolar */}
      {bddScenarios.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">BDD Senaryolar</h3>
          {bddScenarios.map((s, i) => (
            <div key={i} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="text-sm font-semibold text-white mb-2">{s.title}</p>
              {s.gherkin && (
                <pre className="rounded-lg bg-slate-950 p-3 text-xs text-purple-300 overflow-auto">{s.gherkin}</pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
