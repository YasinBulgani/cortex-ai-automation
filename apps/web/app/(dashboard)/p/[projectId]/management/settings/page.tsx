"use client";

import { useState, useEffect } from "react";
import { useManagementSettings } from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

/* ─────────────────────────── constants ─────────────────────────── */

const TABS = [
  { id: "general",     label: "Genel"              },
  { id: "modules",     label: "Modüller & Etiketler" },
  { id: "roles",       label: "Roller & İzinler"   },
  { id: "notifs",      label: "Bildirimler"         },
  { id: "danger",      label: "Tehlike Bölgesi"    },
] as const;
type TabId = (typeof TABS)[number]["id"];

const NOTIFICATION_TYPES = [
  { key: "run_completed",   label: "Run tamamlandı"       },
  { key: "run_failed",      label: "Run başarısız"         },
  { key: "defect_created",  label: "Yeni defect eklendi"   },
  { key: "case_updated",    label: "Case güncellendi"      },
  { key: "plan_created",    label: "Yeni plan oluşturuldu" },
  { key: "report_ready",    label: "Rapor hazır"           },
];

const ROLES_TABLE = [
  { role: "Admin",     repository: "✓", runs: "✓", plans: "✓", reports: "✓",         settings: "✓" },
  { role: "Test Lead", repository: "✓", runs: "✓", plans: "✓", reports: "✓",         settings: "—" },
  { role: "Tester",    repository: "✓", runs: "✓", plans: "—", reports: "Görüntüle", settings: "—" },
  { role: "Viewer",    repository: "Görüntüle", runs: "Görüntüle", plans: "—", reports: "Görüntüle", settings: "—" },
];

const KEY_FORMAT_OPTIONS = [
  { value: "PREFIX-###",   label: "PREFIX-### (ör. TC-001)"   },
  { value: "PREFIX####",   label: "PREFIX#### (ör. TC0001)"   },
  { value: "###",          label: "### (sadece numara)"        },
];

/* ─────────────────────────── types ─────────────────────────── */

interface StoredSettings {
  defaultPriority: string;
  defaultType: string;
  caseKeyPrefix: string;
  caseKeyFormat: string;
  notifications: Record<string, boolean>;
  modules: string[];
  tags: string[];
}

const DEFAULT_STORED: StoredSettings = {
  defaultPriority: "P2",
  defaultType: "manual",
  caseKeyPrefix: "TC",
  caseKeyFormat: "PREFIX-###",
  notifications: {},
  modules: [],
  tags: [],
};

/* ─────────────────────────── helpers ─────────────────────────── */

function cellClass(val: string) {
  if (val === "✓") return "text-teal-400";
  if (val === "—") return "text-slate-600";
  return "text-slate-400";
}

/* ─────────────────────────── component ─────────────────────────── */

export default function ManagementSettingsPage() {
  const projectId = useRouteParam("projectId");
  const mpid      = useManagementProjectId(projectId || undefined);

  const { data: settings, isLoading } = useManagementSettings(mpid || undefined);

  /* ── state ── */
  const [activeTab, setActiveTab]          = useState<TabId>("general");
  const [defaultPriority, setDefaultPriority] = useState(DEFAULT_STORED.defaultPriority);
  const [defaultType, setDefaultType]         = useState(DEFAULT_STORED.defaultType);
  const [caseKeyPrefix, setCaseKeyPrefix]     = useState(DEFAULT_STORED.caseKeyPrefix);
  const [caseKeyFormat, setCaseKeyFormat]     = useState(DEFAULT_STORED.caseKeyFormat);
  const [notifications, setNotifications]     = useState<Record<string, boolean>>({});
  const [modules, setModules]                 = useState<string[]>([]);
  const [tags, setTags]                       = useState<string[]>([]);
  const [newModule, setNewModule]             = useState("");
  const [newTag, setNewTag]                   = useState("");
  const [confirmReset, setConfirmReset]       = useState(false);
  const [saveToast, setSaveToast]             = useState(false);
  const [loaded, setLoaded]                   = useState(false);

  const storageKey = mpid ? `mgmt-settings-${mpid}` : null;

  /* ── persist helpers ── */
  function persistAll(overrides: Partial<StoredSettings> = {}) {
    if (!storageKey) return;
    const current: StoredSettings = {
      defaultPriority,
      defaultType,
      caseKeyPrefix,
      caseKeyFormat,
      notifications,
      modules,
      tags,
      ...overrides,
    };
    localStorage.setItem(storageKey, JSON.stringify(current));
  }

  /* ── load from localStorage ── */
  useEffect(() => {
    if (!storageKey) return;
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const parsed: StoredSettings = JSON.parse(raw);
        setDefaultPriority(parsed.defaultPriority ?? DEFAULT_STORED.defaultPriority);
        setDefaultType(parsed.defaultType ?? DEFAULT_STORED.defaultType);
        setCaseKeyPrefix(parsed.caseKeyPrefix ?? DEFAULT_STORED.caseKeyPrefix);
        setCaseKeyFormat(parsed.caseKeyFormat ?? DEFAULT_STORED.caseKeyFormat);
        setNotifications(parsed.notifications ?? {});
        setModules(parsed.modules ?? []);
        setTags(parsed.tags ?? []);
      }
    } catch {
      // ignore parse errors
    }
    setLoaded(true);
  }, [storageKey]);

  /* ── auto-save reactive fields ── */
  useEffect(() => { if (storageKey && loaded) persistAll({ notifications }); }, [notifications]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (storageKey && loaded) persistAll({ modules }); }, [modules]);             // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (storageKey && loaded) persistAll({ tags }); }, [tags]);                   // eslint-disable-line react-hooks/exhaustive-deps

  /* ── actions ── */
  function handleSaveGeneral() {
    persistAll({ defaultPriority, defaultType, caseKeyPrefix, caseKeyFormat });
    setSaveToast(true);
    setTimeout(() => setSaveToast(false), 2500);
  }

  const toggleNotif = (key: string) =>
    setNotifications(prev => ({ ...prev, [key]: !prev[key] }));

  function addModule() {
    const t = newModule.trim();
    if (!t || modules.includes(t)) return;
    setModules(prev => [...prev, t]);
    setNewModule("");
  }
  function removeModule(name: string) { setModules(prev => prev.filter(m => m !== name)); }

  function addTag() {
    const t = newTag.trim();
    if (!t || tags.includes(t)) return;
    setTags(prev => [...prev, t]);
    setNewTag("");
  }
  function removeTag(name: string) { setTags(prev => prev.filter(t => t !== name)); }

  function handleReset() {
    if (!storageKey) return;
    localStorage.removeItem(storageKey);
    setDefaultPriority(DEFAULT_STORED.defaultPriority);
    setDefaultType(DEFAULT_STORED.defaultType);
    setCaseKeyPrefix(DEFAULT_STORED.caseKeyPrefix);
    setCaseKeyFormat(DEFAULT_STORED.caseKeyFormat);
    setNotifications({});
    setModules([]);
    setTags([]);
    setConfirmReset(false);
  }

  /* ── preview key ── */
  const previewKey = caseKeyFormat
    .replace("PREFIX", caseKeyPrefix || "TC")
    .replace(/#+/, (m) => String(1).padStart(m.length, "0"));

  /* ─────────────────────────────── render ─────────────────────────────── */
  return (
    <div className="min-h-[calc(100vh-88px)] bg-bg text-slate-200">

      {/* ── page header ── */}
      <div className="border-b border-border bg-surface-raised px-6 py-4">
        <h1 className="text-[13px] font-semibold text-slate-200">Ayarlar</h1>
      </div>

      {/* ── tab bar ── */}
      <div className="border-b border-border bg-surface-raised px-6">
        <nav className="flex gap-1 -mb-px">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={[
                "px-4 py-3 text-[12px] font-medium border-b-2 transition-colors whitespace-nowrap",
                activeTab === tab.id
                  ? "border-teal-500 text-teal-400"
                  : tab.id === "danger"
                  ? "border-transparent text-red-400/60 hover:text-red-400"
                  : "border-transparent text-slate-500 hover:text-slate-300",
              ].join(" ")}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* ── tab content ── */}
      <div className="mx-auto max-w-2xl p-6 space-y-6">

        {/* ══════════════ GENEL ══════════════ */}
        {activeTab === "general" && (
          <>
            {/* Workspace bilgileri */}
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
                      {(settings?.permissions ?? []).map((p: string) => (
                        <span key={p} className="rounded bg-white/[0.04] px-2 py-0.5 text-[10px] text-slate-400">{p}</span>
                      ))}
                      {!settings?.permissions?.length && <span className="text-[11px] text-slate-600">—</span>}
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

            {/* Varsayılan değerler */}
            <section className="rounded-xl border border-border bg-surface-raised p-5">
              <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-slate-500">Varsayılan Değerler</h2>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
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
                    <label className="mb-1 block text-[11px] text-slate-500">Varsayılan Test Tipi</label>
                    <select
                      value={defaultType}
                      onChange={e => setDefaultType(e.target.value)}
                      className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/50"
                    >
                      {["manual", "exploratory", "regression", "smoke", "uat"].map(t => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Case key prefix / format */}
                <div className="rounded-lg border border-border bg-white/[0.02] p-4 space-y-3">
                  <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">Case Key Formatı</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1 block text-[11px] text-slate-500">Key Prefix</label>
                      <input
                        type="text"
                        value={caseKeyPrefix}
                        onChange={e => setCaseKeyPrefix(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))}
                        maxLength={6}
                        placeholder="TC"
                        className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50 font-mono"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-[11px] text-slate-500">Format</label>
                      <select
                        value={caseKeyFormat}
                        onChange={e => setCaseKeyFormat(e.target.value)}
                        className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/50"
                      >
                        {KEY_FORMAT_OPTIONS.map(o => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-slate-500">
                    <span>Önizleme:</span>
                    <span className="font-mono text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded">{previewKey}</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 flex items-center gap-3">
                <button
                  onClick={handleSaveGeneral}
                  className="rounded-xl bg-teal-600 px-4 py-1.5 text-[12px] font-medium text-white hover:bg-teal-700 transition-colors"
                >
                  Kaydet
                </button>
                {saveToast && (
                  <span className="text-[12px] text-teal-400 animate-pulse">Kaydedildi ✓</span>
                )}
              </div>
              <p className="mt-3 text-[10px] text-slate-600">Bu değerler yeni case oluştururken varsayılan olarak atanır.</p>
            </section>
          </>
        )}

        {/* ══════════════ MODÜLLER & ETİKETLER ══════════════ */}
        {activeTab === "modules" && (
          <>
            {/* Modüller */}
            <section className="rounded-xl border border-border bg-surface-raised p-5">
              <h2 className="mb-1 text-[11px] font-medium uppercase tracking-wider text-slate-500">Modüller</h2>
              <p className="mb-4 text-[11px] text-slate-600">Değişiklikler otomatik kaydedilir.</p>
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
              <h2 className="mb-1 text-[11px] font-medium uppercase tracking-wider text-slate-500">Etiketler</h2>
              <p className="mb-4 text-[11px] text-slate-600">Değişiklikler otomatik kaydedilir.</p>
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
          </>
        )}

        {/* ══════════════ ROLLER & İZİNLER ══════════════ */}
        {activeTab === "roles" && (
          <section className="rounded-xl border border-border bg-surface-raised p-5">
            <h2 className="mb-1 text-[11px] font-medium uppercase tracking-wider text-slate-500">Roller ve Yetkiler</h2>
            <p className="mb-4 text-[11px] text-slate-600">
              Her rolün modüllere erişim düzeyi aşağıda tanımlanmıştır.
            </p>
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
                    <tr key={row.role} className={idx % 2 === 0 ? "" : "bg-white/[0.02]"}>
                      <td className="border border-border px-3 py-2 font-medium text-slate-300">{row.role}</td>
                      {(["repository", "runs", "plans", "reports", "settings"] as const).map(col => (
                        <td key={col} className={`border border-border px-3 py-2 text-center ${cellClass(row[col])}`}>
                          {row[col]}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-[10px] text-slate-600">
              Bu tablo salt okunurdur. Rol atamaları proje üyeleri bölümünden yönetilir.
            </p>
          </section>
        )}

        {/* ══════════════ BİLDİRİMLER ══════════════ */}
        {activeTab === "notifs" && (
          <section className="rounded-xl border border-border bg-surface-raised p-5">
            <h2 className="mb-1 text-[11px] font-medium uppercase tracking-wider text-slate-500">Bildirimler</h2>
            <p className="mb-4 text-[11px] text-slate-600">Değişiklikler otomatik kaydedilir.</p>
            <div className="space-y-1">
              {NOTIFICATION_TYPES.map(({ key, label }) => {
                const active = !!notifications[key];
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => toggleNotif(key)}
                    className="w-full flex items-center justify-between rounded-lg px-3 py-2.5 hover:bg-white/[0.04] transition-colors text-left"
                  >
                    <span className="text-[13px] text-slate-300">{label}</span>
                    {/* toggle pill */}
                    <div
                      className={[
                        "relative h-5 w-9 rounded-full transition-colors shrink-0",
                        active ? "bg-teal-600" : "bg-white/[0.10]",
                      ].join(" ")}
                    >
                      <span
                        className={[
                          "absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform",
                          active ? "translate-x-4" : "translate-x-0.5",
                        ].join(" ")}
                      />
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        )}

        {/* ══════════════ TEHLİKE BÖLGESİ ══════════════ */}
        {activeTab === "danger" && (
          <section className="rounded-xl border border-red-500/20 bg-red-500/[0.03] p-5">
            <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-red-500/70">Tehlike Bölgesi</h2>

            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[13px] text-slate-300">Tüm Verileri Temizle</p>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  Tüm case, run, plan ve defect verilerini siler. Bu işlem geri alınamaz.
                </p>
              </div>
              <button
                onClick={() => setConfirmReset(true)}
                className="shrink-0 rounded-md border border-red-500/30 px-4 py-2 text-[11px] font-medium text-red-400 hover:bg-red-500/10 transition-colors"
              >
                Temizle
              </button>
            </div>
          </section>
        )}
      </div>

      {/* ══════════════ ONAY MODAL ══════════════ */}
      {confirmReset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl border border-red-500/20 bg-surface-raised p-6 shadow-2xl">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-red-500/10">
                <svg className="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                </svg>
              </div>
              <h3 className="text-[14px] font-semibold text-slate-200">Tüm Verileri Temizle</h3>
            </div>
            <p className="mb-6 text-[13px] text-slate-400">
              Bu işlem tüm yerel ayarları, modülleri, etiketleri ve tercihlerinizi kalıcı olarak siler.
              Devam etmek istediğinizden emin misiniz?
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmReset(false)}
                className="rounded-xl border border-border px-4 py-2 text-[12px] text-slate-400 hover:text-slate-200 transition-colors"
              >
                İptal
              </button>
              <button
                onClick={handleReset}
                className="rounded-xl bg-red-600 px-4 py-2 text-[12px] font-medium text-white hover:bg-red-500 transition-colors"
              >
                Evet, temizle
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
