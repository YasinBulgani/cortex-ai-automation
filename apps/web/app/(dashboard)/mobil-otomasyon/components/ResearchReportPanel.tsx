"use client";

export interface ResearchReportPanelProps {
  onClose: () => void;
}

export function ResearchReportPanel({ onClose }: ResearchReportPanelProps) {
  return (
    <section className="rounded-lg border border-blue-500/30 bg-blue-500/5 p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-blue-300">Araştırma Raporu — Özet</h2>
        <button type="button" onClick={onClose} className="text-xs text-slate-400 hover:text-white">
          ✕ Kapat
        </button>
      </div>
      <p className="text-xs text-slate-300 leading-relaxed">
        Neurex QA için <b>Appium 2.x + LLM</b> üçlü katmanlı mimari önerilir: (1) NL→Appium stepper, (2) self-healing
        locator, (3) multimodal görsel doğrulayıcı. Şu an 10 sanal cihaz (6 Android AVD, 4 iOS Sim);
        fiziksel geçiş için Mac Mini M2 + USB-Hub15 + 10 telefon (~464K ₺ CAPEX).
        Rakiplerden (BrowserStack, Kobiton, Sofy) farkınız: <b>on-prem + KVKK + Türkçe + sentetik veri entegre</b>.
      </p>
      <div className="flex flex-wrap gap-2 pt-1">
        {[
          ["Mimari", "Appium 2 + Device Broker + LLM Gateway"],
          ["LLM 1", "Senaryo Yazıcı (NL→Gherkin→Appium)"],
          ["LLM 2", "Self-Healing Locator"],
          ["LLM 3", "Görsel Doğrulayıcı (GPT-4o/Gemini)"],
          ["Faz 1", "4 hafta — 10 sanal cihaz MVP"],
          ["Faz 3", "6 hafta — 10 fiziksel cihaz"],
          ["Maliyet/1K test", "~$10 (Gemini Flash)"],
        ].map(([k, v]) => (
          <div key={k} className="rounded border border-slate-800 bg-slate-950/40 px-3 py-1.5">
            <span className="block text-[10px] uppercase tracking-wide text-slate-500">{k}</span>
            <span className="block text-[11px] text-slate-200">{v}</span>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-4 pt-2 border-t border-slate-800/50">
        <a
          href="/docs/mobil-otomasyon-rapor"
          className="text-xs text-blue-400 hover:underline"
          onClick={(e) => {
            e.preventDefault();
            window.open("/docs/MOBIL_OTOMASYON_ARASTIRMA_RAPORU.md", "_blank");
          }}
        >
          📖 Tam Raporu Aç (18 bölüm, ~9K kelime)
        </a>
        <span className="text-[11px] text-slate-500">
          • Dosya: <code className="font-mono">docs/MOBIL_OTOMASYON_ARASTIRMA_RAPORU.md</code>
        </span>
      </div>
    </section>
  );
}
