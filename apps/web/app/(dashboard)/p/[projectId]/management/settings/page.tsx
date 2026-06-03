"use client";

import { useState, useEffect } from "react";
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

const ROLES_TABLE = [
  { role: "Admin",     repository: "✓", runs: "✓", plans: "✓", reports: "✓",          settings: "✓" },
  { role: "Test Lead", repository: "✓", runs: "✓", plans: "✓", reports: "✓",          settings: "—" },
  { role: "Tester",    repository: "✓", runs: "✓", plans: "—", reports: "Görüntüle",  settings: "—" },
  { role: "Viewer",    repository: "Görüntüle", runs: "Görüntüle", plans: "—", reports: "Görüntüle", settings: "—" },
];

interface StoredSettings {
  defaultPriority: string;
  defaultType: string;
  notifications: Record<string, boolean>;
  modules: string[];
  tags: string[];
}

const DEFAULT_STORED: StoredSettings = {
  defaultPriority: "P2",
  defaultType: "manual",
  notifications: {},
  modules: [],
  tags: [],
};

export default function ManagementSettingsPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  const { data: settings, isLoading } = useManagementSettings(mpid || undefined);

  const [defaultPriority, setDefaultPriority] = useState("P2");
  const [defaultType, setDefaultType]         = useState("manual");
  const [notifications, setNotifications]     = useState<Record<string, boolean>>({});
  const [modules, setModules]                 = useState<string[]>([]);
  const [tags, setTags]                       = useState<string[]>([]);
  const [newModule, setNewModule]             = useState("");
  const [newTag, setNewTag]                   = useState("");
  const [confirmReset, setConfirmReset]       = useState(false);
  const [saveToast, setSaveToast]             = useState(false);
  const [loaded, setLoaded]                   = useState(false);

  const storageKey = mpid ? `mgmt-settings-${mpid}` : null;

  // Load from localStorage on mount
  useEffect(() => {
    if (!storageKey) return;
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const parsed: StoredSettings = JSON.parse(raw);
        setDefaultPriority(parsed.defaultPriority ?? DEFAULT_STORED.defaultPriority);
        setDefaultType(parsed.defaultType ?? DEFAULT_STORED.defaultType);
        setNotifications(parsed.notifications ?? {});
        setModules(parsed.modules ?? []);
        setTags(parsed.tags ?? []);
      }
    } catch {
      // ignore parse errors
    }
    setLoaded(true);
  }, [storageKey]);

  // Persist notifications on change (auto-save)
  useEffect(() => {
    if (!storageKey || !loaded) return;
    persistAll({ notifications });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notifications]);

  // Persist modules on change
  useEffect(() => {
    if (!storageKey || !loaded) return;
    persistAll({ modules });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modules]);

  // Persist tags on change
  useEffect(() => {
    if (!storageKey || !loaded) return;
    persistAll({ tags });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tags]);

  function persistAll(overrides: Partial<StoredSettings> = {}) {
    if (!storageKey) return;
    const current: StoredSettings = {
      defaultPriority,
      defaultType,
      notifications,
      modules,
      tags,
      ...overrides,
    };
    localStorage.setItem(storageKey, JSON.stringify(current));
  }

  function handleSaveDefaults() {
    persistAll({ defaultPriority, defaultType });
    setSaveToast(true);
    setTimeout(() => setSaveToast(false), 2000);
  }

  const toggleNotif = (key: string) => {
    setNotifications(prev => ({ ...prev, [key]: !prev[key] }));
  };

  function addModule() {
    const trimmed = newModule.trim();
    if (!trimmed || modules.includes(trimmed)) return;
    setModules(prev => [...prev, trimmed]);
    setNewModule("");
  }

  function removeModule(name: string) {
    setModules(prev => prev.filter(m => m !== name));
  }

  function addTag() {
    const trimmed = newTag.trim();
    if (!trimmed || tags.includes(trimmed)) return;
    setTags(prev => [...prev, trimmed]);
    setNewTag("");
  }

  function removeTag(name: string) {
    setTags(prev => prev.filter(t => t !== name));
  }

  function handleReset() {
    if (!storageKey) return;
    localStorage.removeItem(storageKey);
    setDefaultPriority(DEFAULT_STORED.defaultPriority);
    setDefaultType(DEFAULT_STORED.defaultType);
    setNotifications({});
    setModules([]);
    setTags([]);
    setConfirmReset(false);
  }

  return (
    <div className="min-h-[calc(100vh-88px)] bg-bg text-slate-200">
      {/* Header */}
      <div className="border-b border-border bg-surface-raised px-6 py-4">
        <h1 className="text-[13px] font-semibold text-slate-200">Ayarlar</h1>
      </div>

      <div className="mx-auto max-w-2xl p-6 space-y-6">
        {/* Workspace Bilgileri */}
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-slate-500">Workspace Bilgileri</h2>
          {isLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2].map(i => <div key={i} className="h-8 rounded bg-white/[0.04]" />)}
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">Project ID</label>
                <div className="rounded-md border border-border bg-white/[0.02] px-3 py-2 text-[13px] text-slate-400 font-mono">
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
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-slate-500">Varsayılan Değerler</h2>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">Varsayılan Öncelik</label>
              <select
                value={defaultPriority}
                onChange={e => setDefaultPriority(e.target.value)}
                className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/50"
              >
                {["P0", "P1", "P2", "P3"].map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">Varsayılan Tip</label>
              <select
                value={defaultType}
                onChange={e => setDefaultType(e.target.value)}
                className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/50"
              >
                {["manual", "exploratory", "regression", "smoke", "uat"].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={handleSaveDefaults}
              className="rounded-xl bg-teal-600 px-3 py-1.5 text-[12px] font-medium text-white hover:bg-teal-700 transition-colors"
            >
              Kaydet
            </button>
            {saveToast && (
              <span className="animate-pulse text-[12px] text-teal-400">Kaydedildi ✓</span>
            )}
          </div>
          <p className="mt-3 text-[10px] text-slate-600">Bu değerler yeni case oluştururken varsayılan olarak atanır.</p>
        </section>

        {/* Bildirimler */}
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-slate-500">Bildirimler</h2>
          <p className="mb-3 text-[11px] text-slate-600">Değişiklikler otomatik kaydedilir.</p>
          <div className="space-y-2">
            {NOTIFICATION_TYPES.map(({ key, label }) => (
              <label key={key} className="flex items-center gap-3 cursor-pointer rounded-md px-2 py-2 hover:bg-white/[0.04] transition-colors">
                <div
                  className={[
                    "h-4 w-4 rounded border flex items-center justify-center transition-colors",
                    notifications[key]
                      ? "border-teal-500 bg-teal-500/20"
                      : "border-white/[0.12] bg-white/[0.02]",
                  ].join(" ")}
                  onClick={() => toggleNotif(key)}
                >
                  {notifications[key] && (
                    <svg className="h-3 w-3 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
                <span className="text-[13px] text-slate-300">{label}</span>
              </label>
            ))}
          </div>
        </section>

        {/* Modüller */}
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-slate-500">Modüller</h2>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={newModule}
              onChange={e => setNewModule(e.target.value)}
              onKeyDown={e => e.key === "Enter" && addModule()}
              placeholder="Modül adı..."
              className="flex-1 rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
            />
            <button
              onClick={addModule}
              className="rounded-xl bg-teal-600 px-3 py-1.5 text-[12px] font-medium text-white hover:bg-teal-700 transition-colors"
            >
              Ekle
            </button>
          </div>
          {modules.length === 0 ? (
            <p className="text-[11px] text-slate-600">Henüz modül eklenmedi.</p>
          ) : (
            <ul className="space-y-1.5">
              {modules.map(mod => (
                <li key={mod} className="flex items-center justify-between rounded-lg border border-border bg-white/[0.02] px-3 py-2">
                  <span className="text-[13px] text-slate-300">{mod}</span>
                  <button
                    onClick={() => removeModule(mod)}
                    className="text-[11px] text-slate-500 hover:text-red-400 transition-colors"
                  >
                    Kaldır
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Etiketler */}
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-slate-500">Etiketler</h2>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={newTag}
              onChange={e => setNewTag(e.target.value)}
              onKeyDown={e => e.key === "Enter" && addTag()}
              placeholder="Etiket adı..."
              className="flex-1 rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
            />
            <button
              onClick={addTag}
              className="rounded-xl bg-teal-600 px-3 py-1.5 text-[12px] font-medium text-white hover:bg-teal-700 transition-colors"
            >
              Ekle
            </button>
          </div>
          {tags.length === 0 ? (
            <p className="text-[11px] text-slate-600">Henüz etiket eklenmedi.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {tags.map(tag => (
                <span
                  key={tag}
                  className="flex items-center gap-1.5 rounded-full border border-border bg-white/[0.04] px-3 py-1 text-[12px] text-slate-300"
                >
                  {tag}
                  <button
                    onClick={() => removeTag(tag)}
                    className="text-slate-500 hover:text-red-400 transition-colors leading-none"
                    aria-label={`Etiketi kaldır: ${tag}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </section>

        {/* Roller ve Yetkiler */}
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-slate-500">Roller ve Yetkiler</h2>
          <div className="overflow-x-auto">
            <table className="w-full border border-border text-[12px]">
              <thead>
                <tr className="bg-surface-overlay text-slate-400">
                  <th className="border border-border px-3 py-2 text-left font-medium">Rol</th>
                  <th className="border border-border px-3 py-2 text-center font-medium">Repository</th>
                  <th className="border border-border px-3 py-2 text-center font-medium">Runs</th>
                  <th className="border border-border px-3 py-2 text-center font-medium">Plans</th>
                  <th className="border border-border px-3 py-2 text-center font-medium">Reports</th>
                  <th className="border border-border px-3 py-2 text-center font-medium">Ayarlar</th>
                </tr>
              </thead>
              <tbody>
                {ROLES_TABLE.map((row, idx) => (
                  <tr
                    key={row.role}
                    className={idx % 2 === 0 ? "bg-white/[0.00]" : "bg-white/[0.02]"}
                  >
                    <td className="border border-border px-3 py-2 font-medium text-slate-300">{row.role}</td>
                    <td className={`border border-border px-3 py-2 text-center ${row.repository === "✓" ? "text-teal-400" : row.repository === "—" ? "text-slate-600" : "text-slate-400"}`}>{row.repository}</td>
                    <td className={`border border-border px-3 py-2 text-center ${row.runs === "✓" ? "text-teal-400" : row.runs === "—" ? "text-slate-600" : "text-slate-400"}`}>{row.runs}</td>
                    <td className={`border border-border px-3 py-2 text-center ${row.plans === "✓" ? "text-teal-400" : row.plans === "—" ? "text-slate-600" : "text-slate-400"}`}>{row.plans}</td>
                    <td className={`border border-border px-3 py-2 text-center ${row.reports === "✓" ? "text-teal-400" : row.reports === "—" ? "text-slate-600" : "text-slate-400"}`}>{row.reports}</td>
                    <td className={`border border-border px-3 py-2 text-center ${row.settings === "✓" ? "text-teal-400" : row.settings === "—" ? "text-slate-600" : "text-slate-400"}`}>{row.settings}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-[10px] text-slate-600">Bu tablo salt okunurdur. Rol atamaları proje üyeleri bölümünden yönetilir.</p>
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
                  className="rounded-md border border-border px-3 py-2 text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
                >
                  İptal
                </button>
                <button
                  onClick={handleReset}
                  className="rounded-md bg-red-600 px-3 py-2 text-[11px] font-medium text-white hover:bg-red-500 transition-colors"
                >
                  Evet, sıfırla
                </button>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
