"use client";

// ── Types (copied from parent — kept local to avoid circular imports) ─────────

type ActionType =
  | "click"
  | "input"
  | "scroll"
  | "navigate"
  | "resize"
  | "keypress";

type SessionConfig = {
  targetUrl: string;
  actionCount: number;
  seed: string;
  actionTypes: ActionType[];
};

type AuthConfig = {
  login_url: string;
  username_selector: string;
  password_selector: string;
  submit_selector: string;
  username: string;
  password: string;
};

// ── Constants ─────────────────────────────────────────────────────────────────

const ACTION_LABELS: Record<ActionType, string> = {
  click: "Rastgele Tıklama",
  input: "Rastgele Yazma",
  scroll: "Kaydırma",
  navigate: "Geri/İleri Gezinme",
  resize: "Pencere Boyutu Değiştirme",
  keypress: "Rastgele Tuş Basma",
};

// ── Helper ────────────────────────────────────────────────────────────────────

function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

// ── Props ─────────────────────────────────────────────────────────────────────

export interface MonkeyConfigPanelProps {
  config: SessionConfig;
  onConfigChange: (updater: (c: SessionConfig) => SessionConfig) => void;

  auth: AuthConfig;
  onAuthChange: (updater: (a: AuthConfig) => AuthConfig) => void;

  authOpen: boolean;
  onAuthOpenToggle: () => void;

  recordVideo: boolean;
  onRecordVideoChange: (checked: boolean) => void;

  liveRunning: boolean;
  liveProgress: number;
  liveFinished: boolean;
  probing: boolean;
  liveError: string | null;
  liveStatus: string;

  onRunLive: () => void;
  onProbe: () => void;
  onAbort: () => void;
  onExportReport: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function MonkeyConfigPanel({
  config,
  onConfigChange,
  auth,
  onAuthChange,
  authOpen,
  onAuthOpenToggle,
  recordVideo,
  onRecordVideoChange,
  liveRunning,
  liveProgress,
  liveFinished,
  probing,
  liveError,
  liveStatus,
  onRunLive,
  onProbe,
  onAbort,
  onExportReport,
}: MonkeyConfigPanelProps) {
  const toggleActionType = (type: ActionType) => {
    onConfigChange((c) => ({
      ...c,
      actionTypes: c.actionTypes.includes(type)
        ? c.actionTypes.filter((t) => t !== type)
        : [...c.actionTypes, type],
    }));
  };

  return (
    <>
      {/* Config card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 flex flex-col gap-4">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-400">
          Test Yapılandırması
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-[11px] font-semibold uppercase tracking-widest text-slate-400">
              Hedef URL
            </label>
            <input
              value={config.targetUrl}
              onChange={(e) => onConfigChange((c) => ({ ...c, targetUrl: e.target.value }))}
              placeholder="https://cortex-test.bgtsai.com"
              className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-xs font-mono text-slate-200 focus:border-orange-400/50 focus:outline-none focus:ring-1 focus:ring-orange-400/30"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-semibold uppercase tracking-widest text-slate-400">
              Eylem Sayısı: {config.actionCount}
            </label>
            <input
              type="range"
              min={10}
              max={200}
              step={10}
              value={config.actionCount}
              onChange={(e) =>
                onConfigChange((c) => ({ ...c, actionCount: parseInt(e.target.value) }))
              }
              className="w-full accent-orange-400 mt-1"
            />
          </div>
        </div>

        {/* Action types */}
        <div>
          <label className="mb-2 block text-[11px] font-semibold uppercase tracking-widest text-slate-400">
            Eylem Türleri
          </label>
          <div className="flex flex-wrap gap-2">
            {(Object.keys(ACTION_LABELS) as ActionType[]).map((type) => {
              const active = config.actionTypes.includes(type);
              return (
                <button
                  key={type}
                  type="button"
                  onClick={() => toggleActionType(type)}
                  className={cn(
                    "rounded-md border px-2.5 py-1 text-[11px] font-medium transition-all",
                    active
                      ? "border-orange-400/40 bg-orange-500/15 text-orange-200"
                      : "border-slate-700 bg-slate-800/50 text-slate-500 hover:border-slate-600"
                  )}
                >
                  {ACTION_LABELS[type]}
                </button>
              );
            })}
          </div>
        </div>

        {/* Auth & Options */}
        <div className="rounded-lg border border-slate-700/80 bg-slate-900/40">
          <button
            type="button"
            onClick={onAuthOpenToggle}
            className="flex w-full items-center justify-between px-3 py-2 text-[11px] font-semibold uppercase tracking-widest text-slate-300 hover:bg-slate-800/30"
          >
            <span>
              🔑 Login &amp; Gelişmiş Ayarlar{" "}
              {auth.login_url ? "(aktif)" : "(opsiyonel)"}
            </span>
            <span className="text-slate-500">{authOpen ? "−" : "+"}</span>
          </button>
          {authOpen && (
            <div className="border-t border-slate-700/80 p-3 flex flex-col gap-2 text-[11px]">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <input
                  value={auth.login_url}
                  onChange={(e) => onAuthChange((a) => ({ ...a, login_url: e.target.value }))}
                  placeholder="Login URL (örn: https://app.com/login)"
                  className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-1.5 font-mono text-slate-200"
                />
                <input
                  value={auth.submit_selector}
                  onChange={(e) => onAuthChange((a) => ({ ...a, submit_selector: e.target.value }))}
                  placeholder='Submit selector (örn: button[type="submit"])'
                  className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-1.5 font-mono text-slate-200"
                />
                <input
                  value={auth.username_selector}
                  onChange={(e) => onAuthChange((a) => ({ ...a, username_selector: e.target.value }))}
                  placeholder='Username selector (örn: input[name="email"])'
                  className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-1.5 font-mono text-slate-200"
                />
                <input
                  value={auth.password_selector}
                  onChange={(e) => onAuthChange((a) => ({ ...a, password_selector: e.target.value }))}
                  placeholder='Password selector (örn: input[type="password"])'
                  className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-1.5 font-mono text-slate-200"
                />
                <input
                  value={auth.username}
                  onChange={(e) => onAuthChange((a) => ({ ...a, username: e.target.value }))}
                  placeholder="Kullanıcı adı"
                  className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-1.5 text-slate-200"
                />
                <input
                  type="password"
                  value={auth.password}
                  onChange={(e) => onAuthChange((a) => ({ ...a, password: e.target.value }))}
                  placeholder="Şifre"
                  className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-1.5 text-slate-200"
                />
              </div>
              <label className="flex items-center gap-2 mt-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={recordVideo}
                  onChange={(e) => onRecordVideoChange(e.target.checked)}
                  className="accent-orange-400"
                />
                <span className="text-slate-300">📹 Video kayıt (WebM)</span>
              </label>
              <p className="text-[10px] text-slate-500">
                Şifre, sunucudan diğer kullanıcılar tarafından erişilmez; sadece Playwright login
                formuna yazılır.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onRunLive}
          disabled={liveRunning || !config.targetUrl || config.actionTypes.length === 0}
          className={cn(
            "flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold transition-all",
            liveRunning || !config.targetUrl || config.actionTypes.length === 0
              ? "cursor-not-allowed border-slate-700 bg-slate-900/40 text-slate-500"
              : "border-orange-300/40 bg-orange-500/20 text-orange-50 hover:bg-orange-500/30"
          )}
        >
          {liveRunning ? (
            <span>⏳ Tarayıcı testi çalışıyor… {liveProgress}%</span>
          ) : (
            <>
              <span>🌐</span>
              <span>Canlı Tarayıcı Testi Başlat</span>
            </>
          )}
        </button>

        {/* Pre-flight URL probe button */}
        <button
          type="button"
          onClick={onProbe}
          disabled={!config.targetUrl || probing || liveRunning}
          className={cn(
            "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-semibold transition-all",
            !config.targetUrl || probing || liveRunning
              ? "cursor-not-allowed border-slate-700 bg-slate-900/40 text-slate-500"
              : "border-sky-400/30 bg-sky-500/15 text-sky-100 hover:bg-sky-500/25"
          )}
          title="Başlatmadan önce URL'in erişilebilir olduğunu kontrol et"
        >
          {probing ? "Test ediliyor…" : "🔍 URL'i Test Et"}
        </button>

        {liveRunning && (
          <button
            type="button"
            onClick={onAbort}
            className="rounded-lg border border-red-400/30 bg-red-500/15 px-3 py-2 text-xs font-semibold text-red-200 hover:bg-red-500/25"
          >
            ⏹ İptal
          </button>
        )}

        {liveFinished && (
          <button
            type="button"
            onClick={onExportReport}
            className="flex items-center gap-1.5 rounded-lg border border-emerald-400/25 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-200 hover:bg-emerald-500/20"
          >
            ↓ Rapor (.md)
          </button>
        )}
      </div>

      {/* Status + Progress */}
      {(liveRunning || liveStatus) && (
        <div className="flex flex-col gap-1">
          <div className="text-xs text-slate-300">{liveStatus}</div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-300",
                liveError ? "bg-red-500" : "bg-orange-400"
              )}
              style={{ width: `${liveProgress}%` }}
            />
          </div>
        </div>
      )}
    </>
  );
}
