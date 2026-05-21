"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

type ProjectOut = { id: string; name: string };

// ── Step definitions ──────────────────────────────────────────────────────────
const STEPS = [
  { id: 1, title: "Profil", icon: "👤" },
  { id: 2, title: "İlk Proje", icon: "📁" },
  { id: 3, title: "API Spec", icon: "📄" },
  { id: 4, title: "AI Tercih", icon: "🤖" },
  { id: 5, title: "Hazır!", icon: "🚀" },
];

const TEAM_ROLES = [
  { value: "qa-engineer", label: "QA Mühendisi", emoji: "🧪" },
  { value: "developer", label: "Geliştirici", emoji: "💻" },
  { value: "manager", label: "Yönetici", emoji: "📊" },
  { value: "team-lead", label: "Takım Lideri", emoji: "🎯" },
];

const TEAM_SIZES = ["1-5", "6-15", "16-50", "50+"];

const DOMAINS = [
  { value: "banking", label: "Bankacılık & Fintech" },
  { value: "ecommerce", label: "E-Ticaret" },
  { value: "healthcare", label: "Sağlık" },
  { value: "general", label: "Genel" },
];

const AI_PROVIDERS = [
  { value: "groq", label: "Groq (Llama 3.3)", fast: true },
  { value: "gemini", label: "Google Gemini", fast: false },
  { value: "ollama", label: "Ollama (Yerel)", fast: false },
  { value: "any", label: "Otomatik Seç", fast: true },
];

interface WizardState {
  role: string;
  teamSize: string;
  projectName: string;
  projectUrl: string;
  projectDomain: string;
  specUrl: string;
  specSkipped: boolean;
  aiProvider: string;
}

// ── Progress indicator ────────────────────────────────────────────────────────
function StepProgress({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-2 mb-8">
      {STEPS.map((s, i) => (
        <div key={s.id} className="flex items-center gap-2 flex-1 last:flex-none">
          <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-all ${
            s.id < current ? "bg-emerald-500 text-white" :
            s.id === current ? "bg-violet-600 text-white ring-4 ring-violet-500/30" :
            "bg-slate-800 text-slate-500"
          }`}>
            {s.id < current ? "✓" : s.id}
          </div>
          {i < STEPS.length - 1 && (
            <div className={`h-0.5 flex-1 rounded-full transition-all ${s.id < current ? "bg-emerald-500" : "bg-slate-800"}`} />
          )}
        </div>
      ))}
    </div>
  );
}

// ── Step 1: Profile ───────────────────────────────────────────────────────────
function StepProfile({ state, setState, onNext }: { state: WizardState; setState: (s: Partial<WizardState>) => void; onNext: () => void }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-bold text-white">Rolünüz nedir?</h2>
        <p className="text-sm text-slate-400 mt-1">En uygun özellikleri gösterelim</p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {TEAM_ROLES.map((r) => (
          <button
            key={r.value}
            onClick={() => setState({ role: r.value })}
            className={`flex items-center gap-3 rounded-xl border p-3.5 text-left transition-all ${
              state.role === r.value
                ? "border-violet-500/60 bg-violet-500/10 text-white"
                : "border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-600 hover:text-slate-200"
            }`}
          >
            <span className="text-xl">{r.emoji}</span>
            <span className="text-sm font-medium">{r.label}</span>
          </button>
        ))}
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-400 mb-2">Takım Büyüklüğü</label>
        <div className="flex gap-2">
          {TEAM_SIZES.map((s) => (
            <button
              key={s}
              onClick={() => setState({ teamSize: s })}
              className={`flex-1 rounded-lg border py-2 text-xs font-semibold transition-all ${
                state.teamSize === s
                  ? "border-violet-500/60 bg-violet-500/10 text-violet-200"
                  : "border-slate-700 bg-slate-800/50 text-slate-400 hover:text-slate-200"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={onNext}
        disabled={!state.role}
        className="w-full rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 py-3 text-sm font-semibold text-white disabled:opacity-40 hover:opacity-90 transition-opacity"
      >
        Devam →
      </button>
    </div>
  );
}

// ── Step 2: First Project ─────────────────────────────────────────────────────
function StepProject({ state, setState, onNext, onBack }: { state: WizardState; setState: (s: Partial<WizardState>) => void; onNext: () => void; onBack: () => void }) {
  const inputCls = "w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white placeholder-slate-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500";

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold text-white">İlk projenizi oluşturun</h2>
        <p className="text-sm text-slate-400 mt-1">Test otomasyonuna başlamak için en az bir proje gereklidir</p>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1.5">Proje Adı *</label>
        <input
          type="text"
          value={state.projectName}
          onChange={(e) => setState({ projectName: e.target.value })}
          placeholder="Örn: Ödeme API v2"
          className={inputCls}
          autoFocus
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1.5">Hedef URL</label>
        <input
          type="url"
          value={state.projectUrl}
          onChange={(e) => setState({ projectUrl: e.target.value })}
          placeholder="https://api.example.com"
          className={inputCls}
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-400 mb-2">Domain</label>
        <div className="grid grid-cols-2 gap-2">
          {DOMAINS.map((d) => (
            <button
              key={d.value}
              onClick={() => setState({ projectDomain: d.value })}
              className={`rounded-lg border py-2 px-3 text-xs font-medium text-left transition-all ${
                state.projectDomain === d.value
                  ? "border-violet-500/60 bg-violet-500/10 text-violet-200"
                  : "border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-200"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-2 pt-2">
        <button onClick={onBack} className="flex-1 rounded-xl border border-slate-700 py-3 text-sm text-slate-400 hover:text-white transition-colors">
          ← Geri
        </button>
        <button
          onClick={onNext}
          disabled={!state.projectName.trim()}
          className="flex-1 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 py-3 text-sm font-semibold text-white disabled:opacity-40 hover:opacity-90 transition-opacity"
        >
          Devam →
        </button>
      </div>
    </div>
  );
}

// ── Step 3: API Spec ──────────────────────────────────────────────────────────
function StepSpec({ state, setState, onNext, onBack }: { state: WizardState; setState: (s: Partial<WizardState>) => void; onNext: () => void; onBack: () => void }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold text-white">API Spec bağlayın</h2>
        <p className="text-sm text-slate-400 mt-1">Swagger/OpenAPI URL'si verirseniz testler otomatik üretilir</p>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1.5">Swagger / OpenAPI URL</label>
        <input
          type="url"
          value={state.specUrl}
          onChange={(e) => setState({ specUrl: e.target.value, specSkipped: false })}
          placeholder="https://api.example.com/openapi.json"
          className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white placeholder-slate-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
        />
      </div>

      <div className="rounded-xl border border-blue-400/20 bg-blue-500/5 p-4">
        <p className="text-xs text-blue-200 font-semibold mb-1">💡 Ne işe yarar?</p>
        <p className="text-xs text-slate-400">Spec dosyası yüklendikten sonra AI, endpointleri analiz eder ve test senaryoları önerir. Daha sonra da ekleyebilirsiniz.</p>
      </div>

      <div className="flex gap-2 pt-2">
        <button onClick={onBack} className="flex-1 rounded-xl border border-slate-700 py-3 text-sm text-slate-400 hover:text-white transition-colors">
          ← Geri
        </button>
        <button
          onClick={() => { setState({ specSkipped: true }); onNext(); }}
          className="rounded-xl border border-slate-700 px-4 py-3 text-sm text-slate-400 hover:text-white transition-colors"
        >
          Atla
        </button>
        <button
          onClick={onNext}
          className="flex-1 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 py-3 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
        >
          Devam →
        </button>
      </div>
    </div>
  );
}

// ── Step 4: AI Preferences ────────────────────────────────────────────────────
function StepAI({ state, setState, onNext, onBack }: { state: WizardState; setState: (s: Partial<WizardState>) => void; onNext: () => void; onBack: () => void }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold text-white">AI sağlayıcı tercih</h2>
        <p className="text-sm text-slate-400 mt-1">Ayarları daha sonra değiştirebilirsiniz</p>
      </div>

      <div className="space-y-2">
        {AI_PROVIDERS.map((p) => (
          <button
            key={p.value}
            onClick={() => setState({ aiProvider: p.value })}
            className={`flex w-full items-center justify-between rounded-xl border p-3.5 text-left transition-all ${
              state.aiProvider === p.value
                ? "border-violet-500/60 bg-violet-500/10"
                : "border-slate-700 bg-slate-800/50 hover:border-slate-600"
            }`}
          >
            <div>
              <p className={`text-sm font-medium ${state.aiProvider === p.value ? "text-white" : "text-slate-300"}`}>{p.label}</p>
            </div>
            <div className="flex items-center gap-2">
              {p.fast && <span className="rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] text-emerald-400">Hızlı</span>}
              {state.aiProvider === p.value && <span className="text-violet-400 text-sm">✓</span>}
            </div>
          </button>
        ))}
      </div>

      <div className="flex gap-2 pt-2">
        <button onClick={onBack} className="flex-1 rounded-xl border border-slate-700 py-3 text-sm text-slate-400 hover:text-white transition-colors">
          ← Geri
        </button>
        <button
          onClick={onNext}
          className="flex-1 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 py-3 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
        >
          Devam →
        </button>
      </div>
    </div>
  );
}

// ── Step 5: Launch ────────────────────────────────────────────────────────────
function StepLaunch({ state, onLaunch, loading, error, onBack }: {
  state: WizardState;
  onLaunch: () => void;
  loading: boolean;
  error: string;
  onBack: () => void;
}) {
  const roleLabel = TEAM_ROLES.find((r) => r.value === state.role)?.label ?? state.role;
  const aiLabel = AI_PROVIDERS.find((p) => p.value === state.aiProvider)?.label ?? "Otomatik";

  return (
    <div className="space-y-5">
      <div className="text-center">
        <div className="text-4xl mb-2">🚀</div>
        <h2 className="text-xl font-bold text-white">Her şey hazır!</h2>
        <p className="text-sm text-slate-400 mt-1">Aşağıdaki özet doğruysa başlayabilirsiniz</p>
      </div>

      <div className="rounded-xl border border-slate-700 bg-slate-800/50 divide-y divide-slate-700">
        {[
          { label: "Rol", value: roleLabel },
          { label: "Proje", value: state.projectName },
          state.projectUrl ? { label: "Hedef URL", value: state.projectUrl } : null,
          { label: "Domain", value: (DOMAINS.find((d) => d.value === state.projectDomain)?.label ?? state.projectDomain) || "Genel" },
          !state.specSkipped && state.specUrl ? { label: "API Spec", value: "Bağlanacak" } : null,
          { label: "AI Sağlayıcı", value: aiLabel },
        ].filter(Boolean).map((row) => row && (
          <div key={row.label} className="flex items-center justify-between px-4 py-3">
            <span className="text-xs text-slate-500">{row.label}</span>
            <span className="text-sm font-medium text-white truncate max-w-[200px]">{row.value}</span>
          </div>
        ))}
      </div>

      {error && (
        <p className="rounded-lg border border-red-400/20 bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</p>
      )}

      <div className="flex gap-2">
        <button onClick={onBack} className="flex-1 rounded-xl border border-slate-700 py-3 text-sm text-slate-400 hover:text-white transition-colors">
          ← Geri
        </button>
        <button
          onClick={onLaunch}
          disabled={loading}
          className="flex-1 rounded-xl bg-gradient-to-r from-violet-600 to-emerald-600 py-3 text-sm font-bold text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
        >
          {loading ? "Oluşturuluyor…" : "🚀 Başla!"}
        </button>
      </div>
    </div>
  );
}

// ── Main wizard ───────────────────────────────────────────────────────────────
export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [state, setStateRaw] = useState<WizardState>({
    role: "",
    teamSize: "1-5",
    projectName: "",
    projectUrl: "",
    projectDomain: "general",
    specUrl: "",
    specSkipped: false,
    aiProvider: "any",
  });

  const setState = (patch: Partial<WizardState>) => setStateRaw((prev) => ({ ...prev, ...patch }));

  async function handleLaunch() {
    setLoading(true);
    setError("");
    try {
      const p = await apiFetch<ProjectOut>("/api/v1/tspm/projects", {
        method: "POST",
        json: {
          name: state.projectName.trim(),
          base_url: state.projectUrl.trim() || undefined,
          description: `${state.projectDomain} · ${state.role}`,
        },
      });

      // Import spec if provided
      if (!state.specSkipped && state.specUrl.trim()) {
        try {
          await apiFetch(`/api/v1/tspm/projects/${p.id}/api-specs/import`, {
            method: "POST",
            json: { source_url: state.specUrl.trim() },
          });
        } catch {
          // non-fatal
        }
      }

      if (typeof window !== "undefined") {
        localStorage.setItem("onboarded", "true");
        localStorage.setItem("nexus_onboarding_role", state.role);
        localStorage.setItem("nexus_ai_provider", state.aiProvider);
      }
      router.push(`/p/${p.id}/scenarios`);
    } catch (e: unknown) {
      setError((e instanceof Error ? e.message : null) ?? "Proje oluşturulamadı.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center px-4 py-12" data-testid="onboarding-page">
      {/* Logo */}
      <div className="mb-8 text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl border border-violet-400/30 bg-violet-500/10 text-3xl mb-4">
          ⚡
        </div>
        <h1 className="text-2xl font-bold text-white tracking-tight">
          <span className="text-violet-400">Neurex</span> QA
        </h1>
        <p className="text-slate-400 text-sm mt-1">İlk kurulumu tamamlayın — yalnızca 2 dakika</p>
      </div>

      <div className="w-full max-w-md">
        {/* Step indicator */}
        <StepProgress current={step} />

        {/* Step label */}
        <div className="mb-5 text-center">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-600">
            Adım {step} / {STEPS.length} — {STEPS[step - 1].icon} {STEPS[step - 1].title}
          </span>
        </div>

        {/* Step content */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
          {step === 1 && <StepProfile state={state} setState={setState} onNext={() => setStep(2)} />}
          {step === 2 && <StepProject state={state} setState={setState} onNext={() => setStep(3)} onBack={() => setStep(1)} />}
          {step === 3 && <StepSpec state={state} setState={setState} onNext={() => setStep(4)} onBack={() => setStep(2)} />}
          {step === 4 && <StepAI state={state} setState={setState} onNext={() => setStep(5)} onBack={() => setStep(3)} />}
          {step === 5 && <StepLaunch state={state} onLaunch={handleLaunch} loading={loading} error={error} onBack={() => setStep(4)} />}
        </div>

        {/* Skip onboarding link */}
        <div className="mt-4 text-center">
          <button
            onClick={() => {
              if (typeof window !== "undefined") localStorage.setItem("onboarded", "true");
              router.push("/portfolio");
            }}
            className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
          >
            Atla, direkt giriş yap →
          </button>
        </div>
      </div>
    </div>
  );
}
