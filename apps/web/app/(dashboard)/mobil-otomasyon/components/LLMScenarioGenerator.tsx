"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Platform = "android" | "ios";

type AppiumAction = {
  action: "launch" | "find" | "tap" | "sendKeys" | "verifyVisible" | "wait" | "swipe";
  by?: "accessibilityId" | "xpath" | "predicate";
  value?: string;
  text?: string;
  timeout?: number;
  ms?: number;
  direction?: "up" | "down" | "left" | "right";
};

const SAMPLE_PROMPTS = [
  "Uygulamayı aç, Giriş yap butonuna bas, email alanına test@bgts.ai yaz, şifre alanına Test123! yaz, Devam'a bas, ana sayfanın yüklendiğini doğrula.",
  "Onboarding ekranlarını geç, bildirim izinlerini reddet, dil olarak Türkçe seç, hesap oluştur sayfasının açıldığını doğrula.",
  "Ürün arama kutusuna 'kahve' yaz, filtreyi 'fiyat artan' yap, ilk ürünü sepete ekle, sepet sayacının 1 olduğunu doğrula.",
  "Profil sayfasına git, 'Çıkış Yap' butonuna bas, onay dialog'unda 'Evet' seç, login sayfasına döndüğünü doğrula.",
];

export interface LLMScenarioGeneratorProps {
  prompt: string;
  onPromptChange: (v: string) => void;
  scenarioName: string;
  onScenarioNameChange: (v: string) => void;
  targetPlatform: "both" | Platform;
  onTargetPlatformChange: (v: "both" | Platform) => void;
  parallel: number;
  onParallelChange: (v: number) => void;
  passRate: number;
  onPassRateChange: (v: number) => void;
  healRate: number;
  onHealRateChange: (v: number) => void;
  generatedSteps: AppiumAction[] | null;
  onGenerate: () => void;
  onRunSuite: () => void;
}

export function LLMScenarioGenerator({
  prompt,
  onPromptChange,
  scenarioName,
  onScenarioNameChange,
  targetPlatform,
  onTargetPlatformChange,
  parallel,
  onParallelChange,
  passRate,
  onPassRateChange,
  healRate,
  onHealRateChange,
  generatedSteps,
  onGenerate,
  onRunSuite,
}: LLMScenarioGeneratorProps) {
  return (
    <section className="rounded-lg border border-slate-800 overflow-hidden">
      <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-3 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">🧠 LLM Senaryo Üretici</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Doğal dil → Gherkin → Appium aksiyonları. AI Gateway üzerinden GPT-4o / Gemini Flash.
          </p>
        </div>
        <div className="flex items-center gap-1">
          {(["both", "android", "ios"] as const).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => onTargetPlatformChange(p)}
              className={`rounded px-2.5 py-1 text-[11px] font-medium border transition-colors
                ${targetPlatform === p
                  ? "border-blue-500/60 bg-blue-500/10 text-blue-300"
                  : "border-slate-800 text-slate-400 hover:border-slate-600"}`}
            >
              {p === "both" ? "Tümü" : p === "ios" ? "iOS" : "Android"}
            </button>
          ))}
        </div>
      </div>

      <div className="p-4 grid gap-4 lg:grid-cols-[1fr_360px]">
        {/* Prompt alanı */}
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <label className="text-xs text-slate-400">Senaryo Adı</label>
            <div className="flex gap-1.5 flex-wrap">
              {SAMPLE_PROMPTS.map((s, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => {
                    onPromptChange(s);
                    onScenarioNameChange(["Login", "Onboarding", "Arama+Sepet", "Çıkış"][i]);
                  }}
                  className="rounded border border-slate-800 px-2 py-0.5 text-[10px] text-slate-400 hover:border-blue-500/40 hover:text-blue-300"
                >
                  örnek {i + 1}
                </button>
              ))}
            </div>
          </div>
          <Input value={scenarioName} onChange={(e) => onScenarioNameChange(e.target.value)} placeholder="Senaryo adı" />
          <textarea
            rows={5}
            value={prompt}
            onChange={(e) => onPromptChange(e.target.value)}
            placeholder="Örn: Uygulamayı aç, giriş yap butonuna bas, email alanına test@bgts.ai yaz…"
            className="w-full rounded border border-slate-800 bg-slate-900 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Paralel:</span>
              <input
                type="number" min={1} max={10} value={parallel}
                onChange={(e) => onParallelChange(Math.max(1, Math.min(10, Number(e.target.value))))}
                className="h-8 w-16 rounded border border-slate-800 bg-slate-900 px-2 text-xs"
              />
            </div>
            <div className="flex items-center gap-2 min-w-[180px]">
              <span className="text-xs text-slate-400">Başarı %{passRate}</span>
              <input type="range" min={30} max={100} value={passRate} onChange={(e) => onPassRateChange(Number(e.target.value))} className="flex-1 accent-blue-500" />
            </div>
            <div className="flex items-center gap-2 min-w-[180px]">
              <span className="text-xs text-slate-400">Heal %{healRate}</span>
              <input type="range" min={0} max={80} value={healRate} onChange={(e) => onHealRateChange(Number(e.target.value))} className="flex-1 accent-amber-500" />
            </div>
            <div className="flex gap-2 ml-auto">
              <Button type="button" variant="secondary" onClick={onGenerate}>✨ Adımları Üret</Button>
              <Button type="button" onClick={onRunSuite}>🚀 Paralel Koş</Button>
            </div>
          </div>
        </div>

        {/* Üretilen adımlar */}
        <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 max-h-[340px] overflow-y-auto">
          <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-2">Üretilen Appium Adımları</p>
          {!generatedSteps ? (
            <p className="text-xs text-slate-500 italic">Henüz üretilmedi — "Adımları Üret"e basın.</p>
          ) : (
            <ol className="space-y-1">
              {generatedSteps.map((s, i) => (
                <li key={i} className="text-[11px] font-mono flex gap-2">
                  <span className="text-slate-600">{String(i + 1).padStart(2, "0")}</span>
                  <span className="text-blue-300">{s.action}</span>
                  {s.by && <span className="text-slate-500">by={s.by}</span>}
                  {s.value && <span className="text-emerald-300 truncate">"{s.value}"</span>}
                  {s.text && <span className="text-amber-300 truncate">"{s.text}"</span>}
                  {s.ms && <span className="text-slate-500">{s.ms}ms</span>}
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </section>
  );
}
