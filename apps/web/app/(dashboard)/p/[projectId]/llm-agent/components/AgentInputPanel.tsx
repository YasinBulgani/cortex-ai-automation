"use client";

// ─── Types ────────────────────────────────────────────────────────────────────

export type AgentConfig = {
  targetUrl: string;
  maxSteps: number;
  loginUrl: string;
  username: string;
  password: string;
  usernameSelector: string;
  passwordSelector: string;
  submitSelector: string;
  testFocus: string;
  dryRun: boolean;
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function cn(...cls: (string | false | null | undefined)[]) {
  return cls.filter(Boolean).join(" ");
}

const FOCUS_OPTIONS = [
  { value: "", label: "Genel keşif" },
  { value: "login_auth", label: "Login & Kimlik doğrulama" },
  { value: "forms", label: "Form validasyonları" },
  { value: "navigation", label: "Navigasyon & Routing" },
  { value: "errors", label: "Hata senaryoları" },
  { value: "accessibility", label: "Erişilebilirlik" },
  { value: "performance", label: "Performans" },
];

// ─── Props ────────────────────────────────────────────────────────────────────

export interface AgentInputPanelProps {
  config: AgentConfig;
  advOpen: boolean;
  onConfigChange: (patch: Partial<AgentConfig>) => void;
  onAdvToggle: () => void;
  onStart: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * AgentInputPanel
 *
 * The configuration bar displayed at the top of the LLM Agent page when the
 * agent is idle or in an error state. Contains the target URL input, max steps
 * counter, test-focus selector, dry-run toggle, start button and the
 * collapsible advanced login settings section.
 *
 * All state is owned by the parent (LlmAgentPage). This component only
 * calls the provided callbacks on user interaction.
 */
export function AgentInputPanel({
  config,
  advOpen,
  onConfigChange,
  onAdvToggle,
  onStart,
}: AgentInputPanelProps) {
  return (
    <div className="border-b border-slate-800 bg-slate-900/60 px-5 py-4">
      {/* ── Main config row ── */}
      <div className="flex flex-wrap items-end gap-3 max-w-5xl">
        {/* Target URL */}
        <div className="flex-1 min-w-[260px]">
          <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-slate-400">
            Hedef URL
          </label>
          <input
            value={config.targetUrl}
            onChange={(e) => onConfigChange({ targetUrl: e.target.value })}
            placeholder="https://example.com"
            className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-mono text-slate-200 focus:border-violet-500/50 focus:outline-none focus:ring-1 focus:ring-violet-500/25"
          />
        </div>

        {/* Max steps */}
        <div className="w-36">
          <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-slate-400">
            Max Adım
          </label>
          <input
            type="number"
            min={3}
            max={20}
            value={config.maxSteps}
            onChange={(e) =>
              onConfigChange({ maxSteps: parseInt(e.target.value) || 10 })
            }
            className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-violet-500/50 focus:outline-none"
          />
        </div>

        {/* Test focus */}
        <div className="w-52">
          <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-slate-400">
            Test Odağı
          </label>
          <select
            value={config.testFocus}
            onChange={(e) => onConfigChange({ testFocus: e.target.value })}
            className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-violet-500/50 focus:outline-none"
          >
            {FOCUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        {/* Dry-run toggle */}
        <div className="flex items-center gap-2">
          <label className="relative inline-flex cursor-pointer items-center">
            <input
              type="checkbox"
              checked={config.dryRun}
              onChange={(e) => onConfigChange({ dryRun: e.target.checked })}
              className="peer sr-only"
            />
            <div className="h-5 w-9 rounded-full bg-slate-700 peer-checked:bg-violet-600 transition-colors after:absolute after:left-[2px] after:top-[2px] after:h-4 after:w-4 after:rounded-full after:bg-white after:transition-transform peer-checked:after:translate-x-4" />
          </label>
          <span
            className="text-[11px] text-slate-400"
            title="Tarayıcı aksiyonu olmadan sadece hipotez planı üretir"
          >
            Dry Run (önizleme)
          </span>
        </div>

        {/* Start button */}
        <button
          onClick={onStart}
          disabled={!config.targetUrl}
          className={cn(
            "flex items-center gap-2 rounded-lg border px-5 py-2 text-sm font-bold transition-all disabled:opacity-40 disabled:cursor-not-allowed",
            config.dryRun
              ? "border-amber-500/40 bg-amber-500/20 text-amber-100 hover:bg-amber-500/30"
              : "border-violet-500/40 bg-violet-500/20 text-violet-100 hover:bg-violet-500/30"
          )}
        >
          <span className="text-base">{config.dryRun ? "🔍" : "🤖"}</span>
          {config.dryRun ? "Plan Önizle" : "Ajanı Başlat"}
        </button>
      </div>

      {/* ── Advanced login settings ── */}
      <div className="mt-3 max-w-5xl">
        <button
          type="button"
          onClick={onAdvToggle}
          className="text-[11px] text-slate-500 hover:text-slate-300"
        >
          🔑 Login ayarları {advOpen ? "▲" : "▼"}
        </button>

        {advOpen && (
          <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {(
              [
                { key: "loginUrl", label: "Login URL", placeholder: "https://…/login" },
                { key: "username", label: "Kullanıcı adı", placeholder: "admin" },
                { key: "password", label: "Şifre", placeholder: "••••••", type: "password" },
                { key: "usernameSelector", label: "Username Selector", placeholder: "#username" },
                { key: "passwordSelector", label: "Password Selector", placeholder: "#password" },
                { key: "submitSelector", label: "Submit Selector", placeholder: "button[type=submit]" },
              ] as Array<{
                key: keyof AgentConfig;
                label: string;
                placeholder: string;
                type?: string;
              }>
            ).map(({ key, label, placeholder, type }) => (
              <div key={key}>
                <label className="mb-1 block text-[10px] text-slate-500">{label}</label>
                <input
                  type={type ?? "text"}
                  value={config[key] as string}
                  onChange={(e) => onConfigChange({ [key]: e.target.value })}
                  placeholder={placeholder}
                  className="w-full rounded-lg border border-slate-700/60 bg-slate-900/80 px-2.5 py-1.5 text-xs font-mono text-slate-300 focus:border-violet-500/40 focus:outline-none"
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
