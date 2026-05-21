"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/nexus/PageHeader";

// ── Servis Yönetimi tipleri ───────────────────────────────────────────────────
type PM2Status = "online" | "stopping" | "stopped" | "launching" | "errored" | "one-launch-status" | "unknown";

type PM2Process = {
  name: string;
  pid: number | null;
  status: PM2Status;
  cpu: number;
  memory: number;
  restarts: number;
  uptime: number | null;
};

type PM2Response = {
  available: boolean;
  error?: string;
  processes: PM2Process[];
};

type ServiceHealth = {
  name: string;
  port: number;
  healthy: boolean;
  label: string;
};

// ── PM2 yardımcıları ──────────────────────────────────────────────────────────
const PM2_COLOR: Record<PM2Status, string> = {
  online:              "border-emerald-400/20 bg-emerald-500/10 text-emerald-300",
  launching:           "border-blue-400/20 bg-blue-500/10 text-blue-300",
  stopping:            "border-amber-400/20 bg-amber-500/10 text-amber-300",
  stopped:             "border-slate-700 bg-slate-900/70 text-slate-400",
  errored:             "border-red-400/20 bg-red-500/10 text-red-300",
  "one-launch-status": "border-slate-700 bg-slate-800/50 text-slate-400",
  unknown:             "border-slate-700 bg-slate-800/50 text-slate-400",
};

const PM2_LABEL: Record<PM2Status, string> = {
  online:              "Çalışıyor",
  launching:           "Başlıyor",
  stopping:            "Duruyor",
  stopped:             "Durdu",
  errored:             "Hata",
  "one-launch-status": "Bilinmiyor",
  unknown:             "Bilinmiyor",
};

function fmtMemory(bytes: number) {
  if (bytes === 0) return "—";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function fmtUptime(ms: number | null) {
  if (!ms) return "—";
  const s = Math.floor((Date.now() - ms) / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}d`;
  if (s < 86400) return `${Math.floor(s / 3600)}s`;
  return `${Math.floor(s / 86400)}g`;
}

const SERVICE_MAP: Record<string, { label: string; port: number }> = {
  "neurex-backend":  { label: "Backend (FastAPI)",  port: 8000 },
  "neurex-engine":   { label: "Engine (Flask)",     port: 5001 },
  "neurex-watchdog": { label: "Watchdog",           port: 0    },
};

// ── Servis Yönetimi bileşeni ──────────────────────────────────────────────────
function ServiceManagementPanel() {
  const [pm2, setPm2] = useState<PM2Response | null>(null);
  const [health, setHealth] = useState<ServiceHealth[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    try {
      const [pm2Res, healthRes] = await Promise.allSettled([
        fetch("/api/dev/pm2/status").then((r) => r.json() as Promise<PM2Response>),
        fetch("/api/dev/services/status").then((r) => r.json()),
      ]);

      if (pm2Res.status === "fulfilled") setPm2(pm2Res.value);

      if (healthRes.status === "fulfilled") {
        const data = healthRes.value as { services?: Array<{ name: string; state: string; healthUrl?: string }> };
        setHealth(
          (data.services ?? []).map((s) => ({
            name: s.name,
            port: 0,
            healthy: s.state === "running",
            label: s.name,
          })),
        );
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadStatus(); }, [loadStatus]);

  const runAction = async (action: string, name: string) => {
    setActionLoading(`${action}:${name}`);
    setMessage(null);
    try {
      const res = await fetch("/api/dev/pm2/status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, name }),
      });
      const data = (await res.json()) as { ok: boolean; error?: string };
      if (data.ok) {
        setMessage({ type: "ok", text: `${name} → ${action} tamamlandı` });
        void loadStatus();
      } else {
        setMessage({ type: "err", text: data.error ?? "İşlem başarısız" });
      }
    } catch {
      setMessage({ type: "err", text: "Bağlantı hatası" });
    } finally {
      setActionLoading(null);
    }
  };

  // PM2'de olmayan ama healthcheck'te gözüken servisleri de göster
  const allNames = Array.from(new Set([
    ...Object.keys(SERVICE_MAP),
    ...(pm2?.processes ?? []).map((p) => p.name),
  ]));

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 flex flex-col gap-5">
      {/* Başlık */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-white">Servis Yönetimi</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            PM2 üzerinden backend, engine ve watchdog kontrolü
          </p>
        </div>
        <div className="flex items-center gap-2">
          {pm2?.available ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-medium text-emerald-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              PM2 aktif
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/20 bg-amber-500/10 px-2.5 py-0.5 text-[11px] font-medium text-amber-300">
              PM2 pasif
            </span>
          )}
          <button
            type="button"
            onClick={() => void loadStatus()}
            disabled={loading}
            className="rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-600 transition-colors disabled:opacity-50"
          >
            {loading ? "…" : "Yenile"}
          </button>
        </div>
      </div>

      {/* Servis kartları */}
      <div className="grid gap-3 sm:grid-cols-3">
        {allNames.map((name) => {
          const proc = pm2?.processes.find((p) => p.name === name);
          const meta = SERVICE_MAP[name] ?? { label: name, port: 0 };
          const healthEntry = health.find((h) => h.name === name.replace("neurex-", ""));
          const status: PM2Status = proc?.status ?? "unknown";
          const isOnline = status === "online";
          const actionKey = `restart:${name}`;

          return (
            <div
              key={name}
              className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 flex flex-col gap-3"
            >
              {/* İsim + durum */}
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-white">{meta.label}</p>
                  {meta.port > 0 && (
                    <p className="text-[11px] text-slate-500 mt-0.5">:{meta.port}</p>
                  )}
                </div>
                <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-medium ${PM2_COLOR[status]}`}>
                  {PM2_LABEL[status]}
                </span>
              </div>

              {/* Metrikler */}
              {proc && (
                <div className="grid grid-cols-3 gap-1 text-center">
                  <div className="rounded-lg bg-slate-900/60 p-1.5">
                    <p className="text-[10px] text-slate-500">CPU</p>
                    <p className="text-xs font-semibold text-slate-200">%{proc.cpu}</p>
                  </div>
                  <div className="rounded-lg bg-slate-900/60 p-1.5">
                    <p className="text-[10px] text-slate-500">RAM</p>
                    <p className="text-xs font-semibold text-slate-200">{fmtMemory(proc.memory)}</p>
                  </div>
                  <div className="rounded-lg bg-slate-900/60 p-1.5">
                    <p className="text-[10px] text-slate-500">Süre</p>
                    <p className="text-xs font-semibold text-slate-200">{fmtUptime(proc.uptime)}</p>
                  </div>
                </div>
              )}

              {/* Health badge (port varsa) */}
              {meta.port > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${healthEntry?.healthy ? "bg-emerald-400" : "bg-red-400"}`} />
                  <span className="text-[11px] text-slate-500">
                    {healthEntry?.healthy ? "Health OK" : "Health FAIL"}
                  </span>
                  {proc && proc.restarts > 0 && (
                    <span className="ml-auto text-[11px] text-amber-400">{proc.restarts} restart</span>
                  )}
                </div>
              )}

              {/* Aksiyonlar */}
              {pm2?.available && (
                <div className="flex gap-1.5 pt-1">
                  <button
                    type="button"
                    disabled={actionLoading === actionKey || isOnline}
                    onClick={() => void runAction("start", name)}
                    className="flex-1 rounded-lg border border-emerald-400/20 bg-emerald-500/10 py-1.5 text-[11px] font-medium text-emerald-300 disabled:opacity-40 hover:bg-emerald-500/20 transition-colors"
                  >
                    Başlat
                  </button>
                  <button
                    type="button"
                    disabled={actionLoading === actionKey}
                    onClick={() => void runAction("restart", name)}
                    className="flex-1 rounded-lg border border-blue-400/20 bg-blue-500/10 py-1.5 text-[11px] font-medium text-blue-300 disabled:opacity-40 hover:bg-blue-500/20 transition-colors"
                  >
                    {actionLoading === actionKey ? "…" : "Restart"}
                  </button>
                  <button
                    type="button"
                    disabled={actionLoading === actionKey || !isOnline}
                    onClick={() => void runAction("stop", name)}
                    className="flex-1 rounded-lg border border-red-400/20 bg-red-500/10 py-1.5 text-[11px] font-medium text-red-300 disabled:opacity-40 hover:bg-red-500/20 transition-colors"
                  >
                    Durdur
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Mesaj */}
      {message && (
        <div className={`rounded-xl border px-4 py-2.5 text-sm ${
          message.type === "ok"
            ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-200"
            : "border-red-400/20 bg-red-500/10 text-red-200"
        }`}>
          {message.text}
        </div>
      )}

      {/* PM2 kurulu değilse kurulum notu */}
      {pm2 && !pm2.available && (
        <div className="rounded-xl border border-amber-400/20 bg-amber-500/10 px-4 py-3">
          <p className="text-xs font-semibold text-amber-300 mb-1">PM2 Kurulmamış</p>
          <code className="text-[11px] text-amber-200/70 font-mono">
            npm install -g pm2 &amp;&amp; pm2 start ecosystem.config.js
          </code>
        </div>
      )}

      {/* Tam sayfa linki */}
      <div className="border-t border-slate-800 pt-3 flex items-center justify-between">
        <p className="text-xs text-slate-500">
          Otomatik kurtarma: watchdog her 30 sn kontrol eder
        </p>
        <Link
          href="/system/services"
          className="text-xs text-sky-400 hover:text-sky-300 transition-colors"
        >
          Tam servis görünümü →
        </Link>
      </div>
    </div>
  );
}

type LLMProvider = {
  id: string;
  name: string;
  configured: boolean;
};

type ProvidersResponse = {
  providers: LLMProvider[];
  active: string;
};

export default function AdminSettingsPage() {
  const [data, setData] = useState<ProvidersResponse | null>(null);
  const [selected, setSelected] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = useCallback(() => {
    apiFetch<ProvidersResponse>("/api/v1/ai/providers")
      .then((d) => {
        setData(d);
        setSelected(d.active);
      })
      .catch((err) => console.warn("[settings]:", err));
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleSave() {
    if (!selected) return;
    setSaving(true);
    setSaved(false);
    try {
      await apiFetch("/api/v1/ai/providers/active", {
        method: "PUT",
        json: { provider: selected },
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      load();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-6" data-testid="admin-settings-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17H3a2 2 0 01-2-2V5a2 2 0 012-2h14a2 2 0 012 2v10a2 2 0 01-2 2h-2" />
          </svg>
        }
        title="AI Ayarları"
        description="Aktif LLM sağlayıcısını ve model yapılandırmasını yönetin"
        data-testid="admin-settings-heading"
      />

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 flex flex-col gap-4">
        <div>
          <h2 className="text-sm font-semibold text-white">LLM Sağlayıcı</h2>
          <p className="text-xs text-slate-400 mt-0.5">Sistem genelinde kullanılacak AI modelini seçin</p>
        </div>

        {data === null ? (
          <div className="flex flex-col gap-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 animate-pulse rounded-xl border border-slate-800 bg-slate-800/50" />
            ))}
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {data.providers.map((p) => {
              const isSelected = selected === p.id;
              const isActive = data.active === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => p.configured && setSelected(p.id)}
                  disabled={!p.configured}
                  data-testid={`settings-provider-${p.id}`}
                  className={`flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left transition-all ${
                    isSelected
                      ? "border-blue-500/40 bg-blue-500/5 ring-1 ring-blue-500/30"
                      : p.configured
                        ? "border-slate-800 hover:border-slate-700 hover:bg-slate-800/30"
                        : "border-slate-800 opacity-40 cursor-not-allowed"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`h-2.5 w-2.5 rounded-full ${isSelected ? "bg-blue-500" : "bg-slate-600"}`} />
                    <div>
                      <span className="text-sm font-medium text-white capitalize">{p.name}</span>
                      {!p.configured && <span className="ml-2 text-xs text-slate-500">(yapılandırılmamış)</span>}
                    </div>
                  </div>
                  {isActive && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-[11px] font-medium text-blue-400">
                      Aktif
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        <div className="flex items-center gap-3 pt-1">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || !selected || selected === data?.active}
            data-testid="settings-btn-save-provider"
            className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50"
          >
            {saving ? "Kaydediliyor…" : "Kaydet"}
          </button>
          {saved && (
            <span className="text-sm text-emerald-400" data-testid="settings-saved-indicator">
              Kaydedildi
            </span>
          )}
        </div>
      </div>

      {/* ── Servis Yönetimi ────────────────────────────────────────────────── */}
      <ServiceManagementPanel />
    </div>
  );
}
