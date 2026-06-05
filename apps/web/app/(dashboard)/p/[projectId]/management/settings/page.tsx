"use client";

import { useState, useEffect } from "react";
import { useManagementSettings, useUpdateManagementUserSettings } from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api-client";
import { RoleGuard } from "../_components/RoleGuard";

/* ─────────────────────────── constants ─────────────────────────── */

const TABS = [
  { id: "general",     label: "Genel"              },
  { id: "modules",     label: "Modüller & Etiketler" },
  { id: "roles",       label: "Roller & İzinler"   },
  { id: "notifs",      label: "Bildirimler"         },
  { id: "apikeys",     label: "API Anahtarları"    },
  { id: "danger",      label: "Tehlike Bölgesi"    },
] as const;
type TabId = (typeof TABS)[number]["id"];

const NOTIFICATION_TYPES = [
  // Koşumlar
  { key: "run_started",        label: "Test Koşumu Başladı",    group: "Koşumlar",        desc: "Bir test koşumu başlatıldığında bildir" },
  { key: "run_completed",      label: "Test Koşumu Tamamlandı", group: "Koşumlar",        desc: "Koşum başarıyla tamamlandığında bildir" },
  { key: "run_failed",         label: "Koşum Başarısız",        group: "Koşumlar",        desc: "Koşum hatayla sona erdiğinde bildir" },
  // Case'ler
  { key: "case_assigned",      label: "Case Atandı",            group: "Case'ler",        desc: "Size yeni bir test case atandığında bildir" },
  // Defectler
  { key: "defect_opened",      label: "Yeni Defect Açıldı",     group: "Defectler",       desc: "Projede yeni bir defect oluşturulduğunda bildir" },
  { key: "defect_resolved",    label: "Defect Çözüldü",         group: "Defectler",       desc: "Bir defect çözüme kavuşturulduğunda bildir" },
  { key: "defect_blocker",     label: "Blocker Defect",         group: "Defectler",       desc: "Blocker seviyesinde defect açıldığında hemen bildir" },
  // Sürümler
  { key: "release_signoff",    label: "Sürüm Onayı İstendi",   group: "Sürümler",        desc: "Bir sürüm için onayınız istendiğinde bildir" },
  // Regresyon
  { key: "regression_ready",   label: "Regresyon Seti Hazır",   group: "Regresyon",       desc: "Regresyon test seti çalıştırılmaya hazır olduğunda bildir" },
  // Gereksinimler
  { key: "requirement_stale",  label: "Gereksinim Güncellendi", group: "Gereksinimler",   desc: "Bağlı bir gereksinim değiştiğinde bildir" },
  { key: "coverage_dropped",   label: "Kapsam Düştü",           group: "Gereksinimler",   desc: "Test kapsamı belirlenen eşiğin altına düştüğünde bildir" },
  // Genel
  { key: "standup_reminder",   label: "Stand-up Hatırlatması",  group: "Genel",           desc: "Günlük stand-up toplantısından önce hatırlatma gönder" },
  { key: "weekly_report",      label: "Haftalık Özet",          group: "Genel",           desc: "Her hafta özet rapor e-postası gönder" },
];

const ROLES_TABLE = [
  { role: "Admin",     repository: "✓", runs: "✓", plans: "✓", reports: "✓",         settings: "✓" },
  { role: "Test Lead", repository: "✓", runs: "✓", plans: "✓", reports: "✓",         settings: "—" },
  { role: "Tester",    repository: "✓", runs: "✓", plans: "—", reports: "Görüntüle", settings: "—" },
  { role: "Viewer",    repository: "Görüntüle", runs: "Görüntüle", plans: "—", reports: "Görüntüle", settings: "—" },
];

/* ─────────────────────────── API Key types ─────────────────────────── */

interface ApiKey {
  id: string;
  name: string;
  key?: string;
  maskedKey: string;
  createdAt: string;
  expiresAt: string | null; // ISO string or null = unlimited
  revokedAt?: string | null;
  revealed: boolean; // show full key only at creation time
}

const API_KEY_DURATIONS: { label: string; days: number | null }[] = [
  { label: "30 gün",    days: 30   },
  { label: "90 gün",    days: 90   },
  { label: "1 yıl",     days: 365  },
  { label: "Sınırsız",  days: null },
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
  const updateSettings = useUpdateManagementUserSettings(mpid || "");

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

  // API Keys state
  const [apiKeys, setApiKeys]                 = useState<ApiKey[]>([]);
  const [showKeyModal, setShowKeyModal]       = useState(false);
  const [newKeyName, setNewKeyName]           = useState("");
  const [newKeyDuration, setNewKeyDuration]   = useState<number | null>(365);
  const [copyToast, setCopyToast]             = useState<string | null>(null);
  const [keysLoading, setKeysLoading]         = useState(false);

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

  /* ── load: önce API'dan, fallback localStorage ── */
  useEffect(() => {
    if (!storageKey || loaded) return;

    // API'dan gelen user_settings varsa öncelikli kullan
    const apiSettings = (settings as { user_settings?: StoredSettings } | undefined)?.user_settings;
    if (apiSettings && Object.keys(apiSettings).length > 0) {
      setDefaultPriority(apiSettings.defaultPriority ?? DEFAULT_STORED.defaultPriority);
      setDefaultType(apiSettings.defaultType ?? DEFAULT_STORED.defaultType);
      setCaseKeyPrefix(apiSettings.caseKeyPrefix ?? DEFAULT_STORED.caseKeyPrefix);
      setCaseKeyFormat(apiSettings.caseKeyFormat ?? DEFAULT_STORED.caseKeyFormat);
      setNotifications(apiSettings.notifications ?? {});
      setModules(apiSettings.modules ?? []);
      setTags(apiSettings.tags ?? []);
      setLoaded(true);
      return;
    }

    // Fallback: localStorage
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
  }, [storageKey, settings]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── auto-save reactive fields (localStorage + API) ── */
  useEffect(() => {
    if (!storageKey || !loaded) return;
    persistAll({ notifications });
    if (mpid) void updateSettings.mutateAsync({ notifications });
  }, [notifications]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!storageKey || !loaded) return;
    persistAll({ modules });
    if (mpid) void updateSettings.mutateAsync({ modules });
  }, [modules]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!storageKey || !loaded) return;
    persistAll({ tags });
    if (mpid) void updateSettings.mutateAsync({ tags });
  }, [tags]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!mpid) return;
    setKeysLoading(true);
    apiFetch<Array<{
      id: string;
      name: string;
      masked_key: string;
      created_at: string;
      expires_at: string | null;
      revoked_at?: string | null;
    }>>(`/api/v1/test-management/projects/${mpid}/api-keys`)
      .then(keys => {
        setApiKeys(keys.map(k => ({
          id: k.id,
          name: k.name,
          maskedKey: k.masked_key,
          createdAt: k.created_at,
          expiresAt: k.expires_at,
          revokedAt: k.revoked_at ?? null,
          revealed: false,
        })));
      })
      .finally(() => setKeysLoading(false));
  }, [mpid]);

  /* ── actions ── */
  async function handleSaveGeneral() {
    persistAll({ defaultPriority, defaultType, caseKeyPrefix, caseKeyFormat });
    // Backend'e de kaydet
    if (mpid) {
      await updateSettings.mutateAsync({
        default_priority: defaultPriority,
        default_type: defaultType,
        case_key_prefix: caseKeyPrefix,
        case_key_format: caseKeyFormat,
      });
    }
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

  async function handleReset() {
    if (!storageKey) return;
    localStorage.removeItem(storageKey);
    setDefaultPriority(DEFAULT_STORED.defaultPriority);
    setDefaultType(DEFAULT_STORED.defaultType);
    setCaseKeyPrefix(DEFAULT_STORED.caseKeyPrefix);
    setCaseKeyFormat(DEFAULT_STORED.caseKeyFormat);
    setNotifications({});
    setModules([]);
    setTags([]);
    // Backend'deki ayarları da sıfırla
    if (mpid) {
      await updateSettings.mutateAsync({
        default_priority: DEFAULT_STORED.defaultPriority,
        default_type: DEFAULT_STORED.defaultType,
        case_key_prefix: DEFAULT_STORED.caseKeyPrefix,
        case_key_format: DEFAULT_STORED.caseKeyFormat,
        notifications: {},
        modules: [],
        tags: [],
      });
    }
    setConfirmReset(false);
  }

  /* ── API key actions ── */
  async function handleCreateApiKey() {
    const name = newKeyName.trim();
    if (!name || !mpid) return;
    const expiresAt = newKeyDuration
      ? new Date(Date.now() + newKeyDuration * 24 * 60 * 60 * 1000).toISOString()
      : null;
    const created = await apiFetch<{
      id: string;
      name: string;
      key: string;
      masked_key: string;
      created_at: string;
      expires_at: string | null;
    }>(`/api/v1/test-management/projects/${mpid}/api-keys`, {
      method: "POST",
      json: { name, expires_at: expiresAt },
    });
    const newKey: ApiKey = {
      id: created.id,
      name: created.name,
      key: created.key,
      maskedKey: created.masked_key,
      createdAt: created.created_at,
      expiresAt: created.expires_at,
      revealed: true,
    };
    setApiKeys(prev => [newKey, ...prev]);
    setNewKeyName("");
    setNewKeyDuration(365);
    setShowKeyModal(false);
    // Mark as revealed=false after 60s so next render shows masked version
    setTimeout(() => {
      setApiKeys(prev => prev.map(k => k.id === newKey.id ? { ...k, revealed: false } : k));
    }, 60_000);
  }

  function handleCopyKey(key: string | undefined, id: string) {
    if (!key) return;
    navigator.clipboard.writeText(key).then(() => {
      setCopyToast(id);
      setTimeout(() => setCopyToast(null), 2000);
    });
  }

  async function handleRevokeKey(id: string) {
    if (!window.confirm("Bu API anahtarını iptal etmek istediğinizden emin misiniz?")) return;
    if (!mpid) return;
    await apiFetch<void>(`/api/v1/test-management/projects/${mpid}/api-keys/${id}`, { method: "DELETE" });
    setApiKeys(prev => prev.map(k => k.id === id ? { ...k, revokedAt: new Date().toISOString(), revealed: false, key: undefined } : k));
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
                <RoleGuard minRole="admin" projectId={projectId ?? undefined}>
                  <button
                    onClick={handleSaveGeneral}
                    className="rounded-xl bg-brand px-4 py-1.5 text-[12px] font-semibold text-brand-fg transition-colors hover:brightness-105"
                  >
                    Kaydet
                  </button>
                </RoleGuard>
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
                  className="rounded-xl bg-brand px-3 py-1.5 text-[12px] font-semibold text-brand-fg transition-colors hover:brightness-105"
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
                  className="rounded-xl bg-brand px-3 py-1.5 text-[12px] font-semibold text-brand-fg transition-colors hover:brightness-105"
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
        {activeTab === "notifs" && (() => {
          // group by group field, preserving insertion order
          const groups: Record<string, typeof NOTIFICATION_TYPES> = {};
          for (const n of NOTIFICATION_TYPES) {
            if (!groups[n.group]) groups[n.group] = [];
            groups[n.group].push(n);
          }
          return (
            <section className="rounded-xl border border-border bg-surface-raised p-5">
              <h2 className="mb-1 text-[11px] font-medium uppercase tracking-wider text-slate-500">Bildirimler</h2>
              <p className="mb-4 text-[11px] text-slate-600">Değişiklikler otomatik kaydedilir.</p>
              <div className="space-y-5">
                {Object.entries(groups).map(([groupName, items]) => (
                  <div key={groupName}>
                    <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500 px-3">{groupName}</p>
                    <div className="space-y-0.5">
                      {items.map(({ key, label, desc }) => {
                        const active = !!notifications[key];
                        return (
                          <button
                            key={key}
                            type="button"
                            onClick={() => toggleNotif(key)}
                            className="w-full flex items-center justify-between rounded-lg px-3 py-2.5 hover:bg-white/[0.04] transition-colors text-left gap-4"
                          >
                            <div className="flex-1 min-w-0">
                              <span className="block text-[13px] text-slate-300">{label}</span>
                              <span className="block text-[11px] text-slate-600 mt-0.5">{desc}</span>
                            </div>
                            {/* toggle pill */}
                            <div
                              className={[
                                "relative h-5 w-9 rounded-full transition-colors shrink-0",
                                active ? "bg-brand" : "bg-white/[0.10]",
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
                  </div>
                ))}
              </div>
            </section>
          );
        })()}

        {/* ══════════════ API ANAHTARLARI ══════════════ */}
        {activeTab === "apikeys" && (
          <section className="rounded-xl border border-border bg-surface-raised p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-[11px] font-medium uppercase tracking-wider text-slate-500">API Anahtarları</h2>
                <p className="mt-1 text-[11px] text-slate-600">Tam anahtar yalnız oluşturulduğu anda gösterilir.</p>
              </div>
              <button
                onClick={() => setShowKeyModal(true)}
                disabled={!mpid || keysLoading}
                className="rounded-xl bg-brand px-3 py-1.5 text-[12px] font-semibold text-brand-fg transition-colors hover:brightness-105"
              >
                + Yeni Anahtar Oluştur
              </button>
            </div>

            {keysLoading ? (
              <p className="py-6 text-center text-[12px] text-slate-600">Anahtarlar yükleniyor…</p>
            ) : apiKeys.length === 0 ? (
              <p className="py-6 text-center text-[12px] text-slate-600">Henüz API anahtarı oluşturulmadı.</p>
            ) : (
              <ul className="space-y-2">
                {apiKeys.map(k => {
                  const isExpired = k.expiresAt ? new Date(k.expiresAt) < new Date() : false;
                  const isRevoked = !!k.revokedAt;
                  const expiresLabel = k.expiresAt
                    ? `${new Date(k.expiresAt).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })}'e kadar`
                    : "Sınırsız";
                  const displayKey = k.revealed && k.key ? k.key : k.maskedKey;
                  return (
                    <li
                      key={k.id}
                      className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${
                        isExpired || isRevoked ? "border-red-500/20 bg-red-500/5 opacity-60" : "border-border bg-white/[0.02]"
                      }`}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-[12px] font-medium text-slate-300 truncate">{k.name}</p>
                        <p className="mt-0.5 font-mono text-[11px] text-slate-500 truncate">{displayKey}</p>
                      </div>
                      <span className={`shrink-0 text-[10px] ${isExpired || isRevoked ? "text-red-400" : "text-slate-500"}`}>
                        {isRevoked ? "İptal edildi" : isExpired ? "Süresi doldu" : expiresLabel}
                      </span>
                      <button
                        onClick={() => handleCopyKey(k.key, k.id)}
                        disabled={!k.key || isRevoked}
                        className="shrink-0 rounded-md border border-border px-2 py-1 text-[11px] text-slate-400 transition-colors hover:text-slate-200"
                      >
                        {copyToast === k.id ? "Kopyalandı ✓" : "Kopyala"}
                      </button>
                      <button
                        onClick={() => handleRevokeKey(k.id)}
                        disabled={isRevoked}
                        className="shrink-0 text-[11px] text-slate-600 transition-colors hover:text-red-400"
                      >
                        İptal
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
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

      {/* ══════════════ API KEY MODAL ══════════════ */}
      {showKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl border border-border bg-surface-raised p-6 shadow-2xl">
            <h3 className="mb-4 text-[14px] font-semibold text-slate-200">Yeni API Anahtarı</h3>
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">Anahtar Adı</label>
                <input
                  type="text"
                  value={newKeyName}
                  onChange={e => setNewKeyName(e.target.value)}
                  placeholder="ör. CI/CD Pipeline"
                  className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
                  autoFocus
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">Süre</label>
                <div className="flex gap-2 flex-wrap">
                  {API_KEY_DURATIONS.map(opt => (
                    <button
                      key={opt.label}
                      type="button"
                      onClick={() => setNewKeyDuration(opt.days)}
                      className={`rounded-lg border px-3 py-1.5 text-[11px] font-medium transition-colors ${
                        newKeyDuration === opt.days
                          ? "border-teal-500/50 bg-teal-500/10 text-teal-400"
                          : "border-border text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-6 flex gap-3 justify-end">
              <button
                onClick={() => { setShowKeyModal(false); setNewKeyName(""); }}
                className="rounded-xl border border-border px-4 py-2 text-[12px] text-slate-400 hover:text-slate-200 transition-colors"
              >
                İptal
              </button>
              <button
                onClick={handleCreateApiKey}
                disabled={!newKeyName.trim()}
                className="rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg transition-colors hover:brightness-105 disabled:opacity-40"
              >
                Oluştur
              </button>
            </div>
          </div>
        </div>
      )}

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
