"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/nexus/PageHeader";

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
      .catch(() => {});
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
    </div>
  );
}
