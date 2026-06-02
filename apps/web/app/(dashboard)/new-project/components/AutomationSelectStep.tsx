"use client";

import type { SavedScenario } from "../types";
import type { ProductFamilyId } from "@/lib/product";
import { getProductFamilyMember } from "@/lib/product";

interface WizardProfile {
  automationPrimary: boolean;
  automationNote: string;
  analysisSeed: string;
  analysisFocus: string[];
}

interface AutomationSelectStepProps {
  savedScenarios: SavedScenario[];
  selectedIds: Set<string>;
  wizardProfile: WizardProfile;
  selectedProductId: ProductFamilyId;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onToggle: (id: string) => void;
  onGoToMaviyaka: () => void;
  onSkipToFinish: () => void;
}

export function AutomationSelectStep({
  savedScenarios,
  selectedIds,
  wizardProfile,
  selectedProductId,
  onSelectAll,
  onDeselectAll,
  onToggle,
  onGoToMaviyaka,
  onSkipToFinish,
}: AutomationSelectStepProps) {
  const selectedProduct = getProductFamilyMember(selectedProductId);

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold">Otomasyona Alınacakları Seç</h2>
        <p className="mt-1 text-sm text-slate-400">
          {wizardProfile.automationPrimary
            ? "Hangi senaryolar için otomasyon kodu üretilsin? Sec ve devam et."
            : wizardProfile.automationNote}
        </p>
      </div>
      {!wizardProfile.automationPrimary && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-100">
          Bu adım seçili urunde opsiyonel. Istersen dogrudan kurulumu tamamlayip daha sonra web otomasyonu ekleyebilirsin.
        </div>
      )}
      <div className="flex gap-3">
        <button onClick={onSelectAll} className="text-xs text-blue-400 hover:underline">Tümünü Seç</button>
        <button onClick={onDeselectAll} className="text-xs text-slate-500 hover:underline">Tümünü Kaldır</button>
        <span className="text-xs text-slate-600">{selectedIds.size} / {savedScenarios.length} seçili</span>
      </div>
      <div className="space-y-2 rounded-2xl border border-slate-800 bg-slate-900 p-4">
        {savedScenarios.map((s) => {
          const isSelected = selectedIds.has(s.id);
          return (
            <button
              key={s.id}
              onClick={() => onToggle(s.id)}
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition
                ${isSelected ? "bg-blue-950/40 text-white" : "text-slate-400 hover:bg-slate-800"}`}
            >
              <div className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition
                ${isSelected ? "border-blue-500 bg-blue-500" : "border-slate-600"}`}>
                {isSelected && (
                  <svg className="h-2.5 w-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              {s.title}
            </button>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-3">
        {!wizardProfile.automationPrimary && (
          <button
            onClick={onSkipToFinish}
            className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
          >
            {selectedProduct.shortName} odagiyla kurulumu tamamla →
          </button>
        )}
        <button
          onClick={onGoToMaviyaka}
          disabled={selectedIds.size === 0}
          className="flex items-center gap-2 rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-semibold text-white transition hover:border-blue-500 hover:text-blue-300 disabled:opacity-40 disabled:hover:border-slate-700 disabled:hover:text-white"
        >
          🚀 Web otomasyonuna gec ({selectedIds.size} senaryo)
        </button>
      </div>
    </div>
  );
}
