"use client";

import type { RegSet } from "../types";
import { PRIORITY_COLOR } from "../constants";

interface RegressionSetsStepProps {
  regSets: RegSet[];
  acceptedSets: RegSet[];
  loading: boolean;
  onSuggest: () => void;
  onToggleSet: (set: RegSet) => void;
  onSelectAll: () => void;
  onClearAll: () => void;
  onAccept: () => void;
}

export function RegressionSetsStep({
  regSets,
  acceptedSets,
  loading,
  onSuggest,
  onToggleSet,
  onSelectAll,
  onClearAll,
  onAccept,
}: RegressionSetsStepProps) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold">Regresyon Seti</h2>
        <p className="mt-1 text-sm text-slate-400">
          AI, senaryoları öncelik ve kapsama göre grupluyor. Onaylamak istediklerini seç.
        </p>
      </div>

      {regSets.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 flex flex-col items-center gap-4 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-600/10 text-2xl">🔁</div>
          <div>
            <p className="text-sm font-medium text-white">AI ile Regresyon Seti Öner</p>
            <p className="mt-1 text-xs text-slate-500">Senaryolarını önceliğe göre gruplandırıyor</p>
          </div>
          <button
            onClick={onSuggest}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-40"
          >
            {loading ? (
              <>
                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                AI Gruplandırıyor…
              </>
            ) : "Regresyon Setleri Öner"}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {regSets.map((set, i) => {
            const isSelected = acceptedSets.some((s) => s.name === set.name);
            return (
              <button
                key={i}
                onClick={() => onToggleSet(set)}
                className={`w-full rounded-xl border p-5 text-left transition-all
                  ${isSelected
                    ? "border-blue-500 bg-blue-950/30"
                    : "border-slate-800 bg-slate-900 hover:border-slate-600"}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-white">{set.name}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${PRIORITY_COLOR[set.priority]}`}>
                        {set.priority}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">{set.description}</p>
                    <p className="mt-2 text-xs text-slate-600">{set.scenario_ids.length} senaryo</p>
                  </div>
                  <div className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition
                    ${isSelected ? "border-blue-500 bg-blue-500" : "border-slate-600"}`}>
                    {isSelected && (
                      <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                </div>
              </button>
            );
          })}

          <div className="flex gap-3">
            <button
              onClick={onSelectAll}
              className="text-xs text-blue-400 hover:underline"
            >
              Tümünü Seç
            </button>
            <button
              onClick={onClearAll}
              className="text-xs text-slate-500 hover:underline"
            >
              Tümünü Kaldır
            </button>
          </div>

          <button
            onClick={onAccept}
            disabled={loading || acceptedSets.length === 0}
            className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-40"
          >
            {loading ? "Kaydediliyor…" : `Seçilenleri Kaydet (${acceptedSets.length}) →`}
          </button>
        </div>
      )}
    </div>
  );
}
