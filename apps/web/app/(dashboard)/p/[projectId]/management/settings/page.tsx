"use client";

import { useState } from "react";
import { useManagementSettings } from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

const NOTIFICATION_TYPES = [
  { key: "run_completed",   label: "Run tamamlandı"       },
  { key: "run_failed",      label: "Run başarısız"         },
  { key: "defect_created",  label: "Yeni defect eklendi"   },
  { key: "case_updated",    label: "Case güncellendi"      },
  { key: "plan_created",    label: "Yeni plan oluşturuldu" },
  { key: "report_ready",    label: "Rapor hazır"           },
];

export default function ManagementSettingsPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  const { data: settings, isLoading } = useManagementSettings(mpid || undefined);

  const [defaultPriority, setDefaultPriority] = useState("P2");
  const [defaultType, setDefaultType]         = useState("manual");
  const [notifications, setNotifications]     = useState<Record<string, boolean>>({});
  const [confirmReset, setConfirmReset]        = useState(false);

  const toggleNotif = (key: string) => {
    setNotifications(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="min-h-[calc(100vh-88px)] bg-[#0a0f1e] text-slate-200">
      {/* Header */}
      <div className="border-b border-white/[0.06] bg-[#0d1221] px-6 py-4">
        <h1 className="text-[13px] font-semibold text-slate-200">Ayarlar</h1>
      </div>

      <div className="mx-auto max-w-2xl p-6 space-y-6">
        {/* Workspace Bilgileri */}
        <section className="rounded-xl border border-white/[0.06] bg-[#0d1221] p-5">
          <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-slate-500">Workspace Bilgileri</h2>
          {isLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2].map(i => <div key={i} className="h-8 rounded bg-white/[0.04]" />)}
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">Project ID</label>
                <div className="rounded-md border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-[13px] text-slate-400 font-mono">
                  {mpid || "—"}
                </div>
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">İzinler</label>
                <div className="flex flex-wrap gap-1.5">
                  {(settings?.permissions ?? []).map(p => (
                    <span key={p} className="rounded bg-white/[0.04] px-2 py-0.5 text-[10px] text-slate-400">{p}</span>
                  ))}
                  {!settings?.permissions?.length && (
                    <span className="text-[11px] text-slate-600">—</span>
                  )}
                </div>
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">Custom Field Kullanımı</label>
                <p className="text-[13px] text-slate-300">
                  {settings?.custom_field_usage?.cases_with_custom_fields ?? 0} /{" "}
                  {settings?.custom_field_usage?.case_count ?? 0} case
                </p>
              </div>
            </div>
          )}
        </section>

        {/* Varsayılan Değerler */}
        <section className="rounded-xl border border-white/[0.06] bg-[#0d1221] p-5">
          <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-slate-500">Varsayılan Değerler</h2>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">Varsayılan Öncelik</label>
              <select
                value={defaultPriority}
                onChange={e => setDefaultPriority(e.target.value)}
                className="w-full rounded-md border border-white/[0.08] bg-[#0a0f1e] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-blue-500/50"
              >
                {["P0", "P1", "P2", "P3"].map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">Varsayılan Tip</label>
              <select
                value={defaultType}
                onChange={e => setDefaultType(e.target.value)}
                className="w-full rounded-md border border-white/[0.08] bg-[#0a0f1e] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-blue-500/50"
              >
                {["manual", "exploratory", "regression", "smoke", "uat"].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <p className="mt-3 text-[10px] text-slate-600">Bu değerler yeni case oluştururken varsayılan olarak atanır.</p>
        </section>

        {/* Bildirimler */}
        <section className="rounded-xl border border-white/[0.06] bg-[#0d1221] p-5">
          <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-slate-500">Bildirimler</h2>
          <div className="space-y-2">
            {NOTIFICATION_TYPES.map(({ key, label }) => (
              <label key={key} className="flex items-center gap-3 cursor-pointer rounded-md px-2 py-2 hover:bg-white/[0.04] transition-colors">
                <div
                  className={[
                    "h-4 w-4 rounded border flex items-center justify-center transition-colors",
                    notifications[key]
                      ? "border-blue-500 bg-blue-500/20"
                      : "border-white/[0.12] bg-white/[0.02]",
                  ].join(" ")}
                  onClick={() => toggleNotif(key)}
                >
                  {notifications[key] && (
                    <svg className="h-3 w-3 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
                <span className="text-[13px] text-slate-300">{label}</span>
              </label>
            ))}
          </div>
        </section>

        {/* Tehlikeli Alan */}
        <section className="rounded-xl border border-red-500/20 bg-red-500/[0.03] p-5">
          <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-red-500/70">Tehlikeli Alan</h2>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[13px] text-slate-300">Workspace&apos;i Sıfırla</p>
              <p className="mt-0.5 text-[11px] text-slate-500">Tüm case, run, plan ve defect verilerini siler. Bu işlem geri alınamaz.</p>
            </div>
            {!confirmReset ? (
              <button
                onClick={() => setConfirmReset(true)}
                className="shrink-0 rounded-md border border-red-500/30 px-4 py-2 text-[11px] font-medium text-red-400 hover:bg-red-500/10 transition-colors"
              >
                Sıfırla
              </button>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={() => setConfirmReset(false)}
                  className="rounded-md border border-white/[0.08] px-3 py-2 text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
                >
                  İptal
                </button>
                <button
                  className="rounded-md bg-red-600 px-3 py-2 text-[11px] font-medium text-white hover:bg-red-500 transition-colors"
                >
                  Evet, sıfırla
                </button>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* suppress unused warnings */}
      <span className="hidden">{defaultPriority}{defaultType}</span>
    </div>
  );
}
