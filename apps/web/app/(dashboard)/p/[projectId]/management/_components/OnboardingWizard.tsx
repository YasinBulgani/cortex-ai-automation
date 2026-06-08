"use client";

import { useState } from "react";
import Link from "next/link";

interface OnboardingWizardProps {
  projectId: string;
  onCreateWorkspace: () => void;
  isCreating: boolean;
}

const STEPS = [
  {
    id: 1,
    icon: "🏗️",
    title: "Workspace Oluştur",
    description: "Test repository, plan ve run verilerinin tutulacağı workspace'i başlat.",
    action: "workspace",
  },
  {
    id: 2,
    icon: "📥",
    title: "Case'leri İçe Aktar",
    description: "Excel/CSV'den mevcut test case'lerini yükle ya da sıfırdan yaz.",
    action: "import",
  },
  {
    id: 3,
    icon: "📋",
    title: "Test Planı Oluştur",
    description: "Hangi case'lerin, hangi döngüde çalışacağını planla.",
    action: "plan",
  },
  {
    id: 4,
    icon: "▶️",
    title: "İlk Koşumu Başlat",
    description: "Tester'lara ata, execution moduna gir, sonuçları kaydet.",
    action: "run",
  },
];

const ACTION_HREF: Record<string, string> = {
  import: "management/import-export",
  plan:   "management/plans",
  run:    "management/runs",
};

export function OnboardingWizard({ projectId, onCreateWorkspace, isCreating }: OnboardingWizardProps) {
  const [activeStep, setActiveStep] = useState(1);

  return (
    <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
      {/* Başlık */}
      <div className="bg-teal-500/10 border-b border-border px-6 py-5">
        <h2 className="text-lg font-bold text-white">Management Workspace Kurulumu</h2>
        <p className="text-sm text-fg-muted mt-1">
          4 adımda QA yönetim platformunuzu hazırlayın.
        </p>
        {/* İlerleme çizgisi */}
        <div className="mt-4 flex items-center gap-2">
          {STEPS.map((step, i) => (
            <div key={step.id} className="flex items-center gap-2 flex-1">
              <button
                onClick={() => setActiveStep(step.id)}
                className={`w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center transition-all ${
                  activeStep === step.id
                    ? "bg-brand text-white scale-110"
                    : activeStep > step.id
                    ? "bg-brand text-white"
                    : "bg-surface-accent text-fg-muted"
                }`}
              >
                {activeStep > step.id ? "✓" : step.id}
              </button>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-0.5 rounded ${activeStep > step.id ? "bg-brand" : "bg-surface-accent"}`} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Adım içeriği */}
      <div className="p-6">
        {STEPS.map((step) => step.id === activeStep && (
          <div key={step.id} className="space-y-5">
            <div className="flex items-start gap-4">
              <span className="text-4xl">{step.icon}</span>
              <div>
                <h3 className="text-white font-semibold text-base">{step.title}</h3>
                <p className="text-fg-muted text-sm mt-1">{step.description}</p>
              </div>
            </div>

            {/* Adım aksiyonu */}
            {step.action === "workspace" ? (
              <div className="space-y-3">
                <div className="rounded-lg border border-border bg-surface-overlay p-4 space-y-2">
                  <p className="text-xs text-fg-muted">Workspace oluşturulunca:</p>
                  <ul className="text-xs text-fg space-y-1">
                    <li>✅ Test repository hazır olacak</li>
                    <li>✅ Plan ve run yönetimi aktif olacak</li>
                    <li>✅ Tüm veri bu proje altında izole tutulacak</li>
                  </ul>
                </div>
                <button
                  onClick={() => { onCreateWorkspace(); setActiveStep(2); }}
                  disabled={isCreating}
                  className="flex items-center gap-2 rounded-xl bg-brand hover:brightness-105 disabled:opacity-50 px-5 py-2.5 text-sm font-bold text-white transition-colors"
                >
                  {isCreating && (
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  )}
                  {isCreating ? "Oluşturuluyor…" : "Workspace Oluştur"}
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Link
                  href={`/p/${projectId}/${ACTION_HREF[step.action]}`}
                  className="rounded-xl bg-brand hover:brightness-105 px-5 py-2.5 text-sm font-bold text-white transition-colors"
                >
                  {step.title} →
                </Link>
                <button
                  onClick={() => setActiveStep((s) => Math.min(4, s + 1))}
                  className="text-sm text-fg-muted hover:text-white transition-colors"
                >
                  Sonraki adım
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Navigasyon */}
      <div className="border-t border-border px-6 py-3 flex justify-between">
        <button
          onClick={() => setActiveStep((s) => Math.max(1, s - 1))}
          disabled={activeStep === 1}
          className="text-xs text-fg-subtle hover:text-white disabled:opacity-30 transition-colors"
        >
          ← Önceki
        </button>
        <span className="text-xs text-fg-subtle">Adım {activeStep} / {STEPS.length}</span>
        <button
          onClick={() => setActiveStep((s) => Math.min(4, s + 1))}
          disabled={activeStep === 4}
          className="text-xs text-fg-subtle hover:text-white disabled:opacity-30 transition-colors"
        >
          Sonraki →
        </button>
      </div>
    </div>
  );
}
