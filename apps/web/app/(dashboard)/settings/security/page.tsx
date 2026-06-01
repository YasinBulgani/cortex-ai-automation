"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface MfaStatus {
  mfa_enabled: boolean;
  backup_codes_remaining: number | null;
}

interface MfaSetupResponse {
  secret: string;
  provisioning_uri: string;
  backup_codes: string[];
}

// ── API hooks ─────────────────────────────────────────────────────────────────

const MFA_BASE = "/api/v1/auth/mfa";

function useMfaStatus() {
  return useQuery({
    queryKey: ["mfa-status"],
    queryFn: () => apiFetch<MfaStatus>(`${MFA_BASE}/status`),
    staleTime: 30_000,
  });
}

function useMfaSetup() {
  return useMutation({
    mutationFn: () => apiFetch<MfaSetupResponse>(`${MFA_BASE}/setup`, { method: "POST" }),
  });
}

function useMfaVerify() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code: string) =>
      apiFetch(`${MFA_BASE}/verify`, { method: "POST", json: { code } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["mfa-status"] }),
  });
}

function useMfaDisable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ password, code }: { password: string; code: string }) =>
      apiFetch(`${MFA_BASE}/disable`, { method: "POST", json: { password, code } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["mfa-status"] }),
  });
}

function useMfaRegenerateBackupCodes() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code: string) =>
      apiFetch<{ backup_codes: string[] }>(`${MFA_BASE}/backup-codes/regenerate`, {
        method: "POST",
        json: { code },
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["mfa-status"] }),
  });
}

// ── QR Code component (renders otpauth:// URI via Canvas) ─────────────────────

function QrCodeDisplay({ uri }: { uri: string }) {
  // Simple visual: just show the URI + note. Real apps would render a QR via a library.
  // Since we don't want to add a dependency, we show the secret prominently with a note.
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 text-center">
      <p className="text-xs text-slate-400 mb-3">
        Authenticator uygulamanızda (Google Authenticator, Authy, 1Password, vb.) "QR kodu tara" yerine
        "kurulum anahtarını gir" seçeneğini kullanın veya aşağıdaki URI'yi kopyalayın.
      </p>
      <div className="rounded-lg bg-slate-900 border border-slate-700 p-3 mb-2">
        <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1">otpauth:// URI</p>
        <code className="break-all text-xs text-violet-300 font-mono">{uri}</code>
      </div>
      <button
        onClick={() => navigator.clipboard.writeText(uri)}
        className="text-xs text-slate-400 hover:text-white underline"
      >
        URI'yi kopyala
      </button>
    </div>
  );
}

// ── MFA Setup flow ────────────────────────────────────────────────────────────

function MfaSetupFlow({ onCancel }: { onCancel: () => void }) {
  const [step, setStep] = useState<"qr" | "verify" | "done">("qr");
  const [code, setCode] = useState("");
  const setupMutation = useMfaSetup();
  const verifyMutation = useMfaVerify();

  // Trigger setup on mount
  const setup = setupMutation.data;

  const handleInit = () => {
    if (!setup) setupMutation.mutate();
  };

  const handleVerify = () => {
    verifyMutation.mutate(code, {
      onSuccess: () => setStep("done"),
    });
  };

  if (step === "done") {
    return (
      <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-6 text-center space-y-3">
        <div className="text-4xl">🔐</div>
        <p className="font-semibold text-emerald-400">MFA başarıyla etkinleştirildi!</p>
        <p className="text-sm text-slate-400">
          Hesabınız artık iki faktörlü kimlik doğrulama ile korunmaktadır.
        </p>
        <button
          onClick={onCancel}
          className="mt-2 rounded-lg bg-slate-800 px-4 py-2 text-sm text-white hover:bg-slate-700"
        >
          Kapat
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Step 1: Scan/enter secret */}
      {!setup ? (
        <div className="text-center py-4">
          <button
            onClick={handleInit}
            disabled={setupMutation.isPending}
            className="rounded-lg bg-violet-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-40"
          >
            {setupMutation.isPending ? "Hazırlanıyor…" : "MFA Kurulumunu Başlat"}
          </button>
        </div>
      ) : (
        <>
          {/* Secret display */}
          <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 space-y-2">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Kurulum Anahtarı</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded-lg bg-slate-900 px-3 py-2 font-mono text-sm text-violet-300 break-all">
                {setup.secret}
              </code>
              <button
                onClick={() => navigator.clipboard.writeText(setup.secret)}
                className="flex-shrink-0 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-400 hover:bg-slate-800"
              >
                Kopyala
              </button>
            </div>
          </div>

          <QrCodeDisplay uri={setup.provisioning_uri} />

          {/* Backup codes */}
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
            <p className="text-xs font-semibold text-amber-400 mb-2">
              ⚠️ Yedek Kodlar — Yalnızca bir kez gösterilir, şimdi kaydedin!
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {setup.backup_codes.map((c) => (
                <code key={c} className="rounded-lg bg-slate-950 border border-slate-700 px-2 py-1.5 text-center text-xs font-mono text-white">
                  {c}
                </code>
              ))}
            </div>
            <button
              onClick={() => navigator.clipboard.writeText(setup.backup_codes.join("\n"))}
              className="mt-2 text-xs text-amber-400 underline"
            >
              Tümünü kopyala
            </button>
          </div>

          {/* Verification input */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-slate-300">
              Authenticator Kodu (kurulumu doğrula)
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                inputMode="numeric"
                pattern="\d{6}"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                placeholder="000000"
                className="w-36 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-center font-mono text-lg text-white tracking-widest focus:border-violet-500/50 focus:outline-none"
              />
              <button
                onClick={handleVerify}
                disabled={code.length !== 6 || verifyMutation.isPending}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
              >
                {verifyMutation.isPending ? "Doğrulanıyor…" : "Doğrula & Etkinleştir"}
              </button>
              <button
                onClick={onCancel}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:bg-slate-800"
              >
                İptal
              </button>
            </div>
            {verifyMutation.isError && (
              <p className="text-xs text-rose-400">Geçersiz kod. Lütfen tekrar deneyin.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ── MFA Disable flow ──────────────────────────────────────────────────────────

function MfaDisableFlow({ onCancel }: { onCancel: () => void }) {
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const disableMutation = useMfaDisable();

  const handleDisable = () => {
    disableMutation.mutate({ password, code }, { onSuccess: onCancel });
  };

  return (
    <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 space-y-3">
      <p className="text-sm font-semibold text-rose-400">MFA Devre Dışı Bırak</p>
      <p className="text-xs text-slate-400">Onaylamak için mevcut parolanızı ve TOTP kodunuzu girin.</p>
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Mevcut parola"
        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
      />
      <input
        type="text"
        inputMode="numeric"
        maxLength={8}
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="TOTP kodu veya yedek kod"
        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white focus:border-violet-500/50 focus:outline-none"
      />
      <div className="flex gap-2">
        <button
          onClick={handleDisable}
          disabled={!password || code.length < 6 || disableMutation.isPending}
          className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-500 disabled:opacity-40"
        >
          {disableMutation.isPending ? "Devre Dışı Bırakılıyor…" : "MFA'yı Devre Dışı Bırak"}
        </button>
        <button onClick={onCancel} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:bg-slate-800">
          İptal
        </button>
      </div>
      {disableMutation.isError && (
        <p className="text-xs text-rose-400">Hata: Parola veya kod yanlış.</p>
      )}
    </div>
  );
}

// ── Backup code regeneration ──────────────────────────────────────────────────

function RegenerateBackupCodesFlow({ onCancel }: { onCancel: () => void }) {
  const [code, setCode] = useState("");
  const regenMutation = useMfaRegenerateBackupCodes();

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 p-4 space-y-3">
      <p className="text-sm font-semibold text-white">Yedek Kodları Yenile</p>
      <p className="text-xs text-slate-400">Mevcut tüm yedek kodlar silinecek. Onaylamak için TOTP kodunuzu girin.</p>
      <input
        type="text"
        inputMode="numeric"
        maxLength={6}
        value={code}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
        placeholder="000000"
        className="w-36 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-center font-mono text-sm text-white focus:border-violet-500/50 focus:outline-none"
      />
      {regenMutation.data && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">
          <p className="text-xs text-amber-400 mb-2">⚠️ Yeni yedek kodlarınız — şimdi kaydedin!</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {regenMutation.data.backup_codes.map((c) => (
              <code key={c} className="rounded-lg bg-slate-950 border border-slate-700 px-2 py-1.5 text-center text-xs font-mono text-white">
                {c}
              </code>
            ))}
          </div>
        </div>
      )}
      <div className="flex gap-2">
        <button
          onClick={() => regenMutation.mutate(code)}
          disabled={code.length !== 6 || regenMutation.isPending}
          className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-500 disabled:opacity-40"
        >
          {regenMutation.isPending ? "Yenileniyor…" : "Yedek Kodları Yenile"}
        </button>
        <button onClick={onCancel} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:bg-slate-800">
          Kapat
        </button>
      </div>
    </div>
  );
}

// ── Main security settings page ───────────────────────────────────────────────

type ActivePanel = "none" | "setup" | "disable" | "regen-codes";

export default function SecuritySettingsPage() {
  const statusQuery = useMfaStatus();
  const [activePanel, setActivePanel] = useState<ActivePanel>("none");

  const status = statusQuery.data;
  const isEnabled = status?.mfa_enabled ?? false;

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100">
      {/* Header */}
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-violet-300">Ayarlar</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-white">Güvenlik</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
          Hesabınızın güvenlik ayarlarını yönetin. İki faktörlü kimlik doğrulama (2FA) ile hesabınızı daha güvenli hale getirin.
        </p>
      </div>

      {/* MFA section */}
      <div className="max-w-2xl space-y-6">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <span>İki Faktörlü Kimlik Doğrulama (2FA)</span>
                {statusQuery.isLoading ? (
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-violet-400" />
                ) : isEnabled ? (
                  <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-400">
                    Etkin
                  </span>
                ) : (
                  <span className="rounded-full bg-slate-700 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                    Devre Dışı
                  </span>
                )}
              </h2>
              <p className="mt-1 text-sm text-slate-400">
                TOTP tabanlı kimlik doğrulama uygulaması (Google Authenticator, Authy, 1Password) ile
                hesabınızı ekstra bir güvenlik katmanıyla koruyun.
              </p>
              {isEnabled && status?.backup_codes_remaining !== null && (
                <p className="mt-2 text-xs text-slate-500">
                  Kalan yedek kod: <span className="font-semibold text-slate-300">{status?.backup_codes_remaining}</span>
                </p>
              )}
            </div>
            {!isEnabled && activePanel === "none" && (
              <button
                onClick={() => setActivePanel("setup")}
                className="flex-shrink-0 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500"
              >
                Etkinleştir
              </button>
            )}
            {isEnabled && activePanel === "none" && (
              <div className="flex gap-2 flex-shrink-0">
                <button
                  onClick={() => setActivePanel("regen-codes")}
                  className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-400 hover:bg-slate-800"
                >
                  Yedek Kodlar
                </button>
                <button
                  onClick={() => setActivePanel("disable")}
                  className="rounded-lg border border-rose-500/30 px-3 py-2 text-xs text-rose-400 hover:bg-rose-500/10"
                >
                  Devre Dışı Bırak
                </button>
              </div>
            )}
          </div>

          {/* Active panel */}
          {activePanel !== "none" && (
            <div className="mt-5 border-t border-slate-800 pt-5">
              {activePanel === "setup" && <MfaSetupFlow onCancel={() => setActivePanel("none")} />}
              {activePanel === "disable" && <MfaDisableFlow onCancel={() => setActivePanel("none")} />}
              {activePanel === "regen-codes" && <RegenerateBackupCodesFlow onCancel={() => setActivePanel("none")} />}
            </div>
          )}
        </div>

        {/* Info box */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <h3 className="text-sm font-semibold text-white mb-3">Neden 2FA kullanmalıyım?</h3>
          <ul className="space-y-1.5 text-sm text-slate-400">
            <li className="flex gap-2">
              <span className="text-violet-400 flex-shrink-0">→</span>
              Parolanız ele geçirilse bile hesabınıza erişilemez.
            </li>
            <li className="flex gap-2">
              <span className="text-violet-400 flex-shrink-0">→</span>
              Kimlik avı (phishing) saldırılarına karşı ek koruma sağlar.
            </li>
            <li className="flex gap-2">
              <span className="text-violet-400 flex-shrink-0">→</span>
              Kurumsal güvenlik politikaları genellikle 2FA zorunlu kılar.
            </li>
            <li className="flex gap-2">
              <span className="text-violet-400 flex-shrink-0">→</span>
              Yedek kodlarınızı güvenli bir yerde saklayın — cihazınızı kaybettiğinizde işinize yarar.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
