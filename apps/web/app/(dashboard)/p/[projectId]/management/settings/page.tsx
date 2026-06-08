"use client";

import { useState, useEffect } from "react";
import { useManagementSettings, useUpdateManagementUserSettings } from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api-client";
import { RoleGuard } from "../_components/RoleGuard";

/* ─────────────────────────── constants ─────────────────────────── */

const TABS = [
  { id: "general",      label: "Genel"                },
  { id: "modules",      label: "Modüller & Etiketler"  },
  { id: "environments", label: "Ortamlar"              },
  { id: "roles",        label: "Roller & İzinler"     },
  { id: "notifs",       label: "Bildirimler"           },
  { id: "apikeys",      label: "API Anahtarları"       },
  { id: "danger",       label: "Tehlike Bölgesi"       },
] as const;
type TabId = (typeof TABS)[number]["id"];

// ─── Environment types ────────────────────────────────────────────────────────

interface Environment {
  id: string;
  name: string;
  slug: string;
  baseUrl: string;
  description: string;
  color: string;
  active: boolean;
}

const DEFAULT_ENVIRONMENTS: Environment[] = [
  { id: "dev",  name: "Development", slug: "DEV",  baseUrl: "http://localhost:3000",  description: "Geliştirme ortamı — yerel makine",            color: "text-blue-400   border-blue-500/30  bg-blue-500/10",   active: true },
  { id: "test", name: "Test",        slug: "TEST", baseUrl: "https://test.example.com",  description: "Test/QA ortamı — manuel ve otomatik testler", color: "text-amber-400  border-amber-500/30 bg-amber-500/10",  active: true },
  { id: "uat",  name: "UAT",         slug: "UAT",  baseUrl: "https://uat.example.com",   description: "Kullanıcı Kabul Testi ortamı",                 color: "text-purple-400 border-purple-500/30 bg-purple-500/10", active: true },
  { id: "prod", name: "Production",  slug: "PROD", baseUrl: "https://app.example.com",   description: "Canlı ortam — yalnızca onaylı release",        color: "text-red-400    border-red-500/30   bg-red-500/10",    active: false },
];

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

// ── Comprehensive RBAC Matrix ─────────────────────────────────────────────────

type PermLevel = "full" | "view" | "limited" | "none";

interface RbacRow {
  module: string;
  group: string;
  admin: PermLevel;
  test_lead: PermLevel;
  qa_engineer: PermLevel;
  developer: PermLevel;
  business_analyst: PermLevel;
  viewer: PermLevel;
  critical?: boolean; // marks security-sensitive permissions
}

const RBAC_MATRIX: RbacRow[] = [
  // Test Cases
  { module: "Test Case — Görüntüle",      group: "Test Case Yönetimi",  admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "view",    business_analyst: "view",    viewer: "view"    },
  { module: "Test Case — Oluştur",         group: "Test Case Yönetimi",  admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "none",    business_analyst: "none",    viewer: "none"    },
  { module: "Test Case — Düzenle",         group: "Test Case Yönetimi",  admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "none",    business_analyst: "none",    viewer: "none"    },
  { module: "Test Case — Arşivle/Sil",     group: "Test Case Yönetimi",  admin: "full",    test_lead: "full",    qa_engineer: "none",    developer: "none",    business_analyst: "none",    viewer: "none",    critical: true },
  { module: "Test Case — İncele/Onayla",   group: "Test Case Yönetimi",  admin: "full",    test_lead: "full",    qa_engineer: "none",    developer: "none",    business_analyst: "none",    viewer: "none",    critical: true },
  { module: "Test Case — AI Üret",         group: "Test Case Yönetimi",  admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "none",    business_analyst: "none",    viewer: "none"    },
  // Test Runs
  { module: "Test Koşumu — Görüntüle",     group: "Test Koşumu",         admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "view",    business_analyst: "view",    viewer: "view"    },
  { module: "Test Koşumu — Oluştur",       group: "Test Koşumu",         admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "none",    business_analyst: "none",    viewer: "none"    },
  { module: "Test Koşumu — Çalıştır",      group: "Test Koşumu",         admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "none",    business_analyst: "none",    viewer: "none"    },
  { module: "Test Koşumu — Sonuç Gir",     group: "Test Koşumu",         admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "none",    business_analyst: "none",    viewer: "none"    },
  { module: "Test Koşumu — Sil",           group: "Test Koşumu",         admin: "full",    test_lead: "none",    qa_engineer: "none",    developer: "none",    business_analyst: "none",    viewer: "none",    critical: true },
  // Defects
  { module: "Defect — Görüntüle",          group: "Defect Yönetimi",     admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "full",    business_analyst: "view",    viewer: "view"    },
  { module: "Defect — Oluştur",            group: "Defect Yönetimi",     admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "none",    business_analyst: "none",    viewer: "none"    },
  { module: "Defect — Kapat/Çöz",          group: "Defect Yönetimi",     admin: "full",    test_lead: "full",    qa_engineer: "none",    developer: "full",    business_analyst: "none",    viewer: "none"    },
  { module: "Defect — Sil",                group: "Defect Yönetimi",     admin: "full",    test_lead: "none",    qa_engineer: "none",    developer: "none",    business_analyst: "none",    viewer: "none",    critical: true },
  // Plans & Regression
  { module: "Test Planı — Görüntüle",      group: "Planlama",            admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "view",    business_analyst: "view",    viewer: "view"    },
  { module: "Test Planı — Oluştur/Düzenle",group: "Planlama",            admin: "full",    test_lead: "full",    qa_engineer: "none",    developer: "none",    business_analyst: "none",    viewer: "none"    },
  { module: "Regresyon Seti — Yönet",      group: "Planlama",            admin: "full",    test_lead: "full",    qa_engineer: "limited", developer: "none",    business_analyst: "none",    viewer: "none"    },
  { module: "Sürüm Onayı",                 group: "Planlama",            admin: "full",    test_lead: "full",    qa_engineer: "none",    developer: "none",    business_analyst: "none",    viewer: "none",    critical: true },
  // Requirements
  { module: "Gereksinim — Görüntüle",      group: "Gereksinimler",       admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "full",    business_analyst: "full",    viewer: "view"    },
  { module: "Gereksinim — Oluştur/Düzenle",group: "Gereksinimler",       admin: "full",    test_lead: "full",    qa_engineer: "none",    developer: "none",    business_analyst: "full",    viewer: "none"    },
  { module: "Gereksinim — TC Bağla",       group: "Gereksinimler",       admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "none",    business_analyst: "limited", viewer: "none"    },
  // Reports
  { module: "Raporlar — Görüntüle",        group: "Raporlama",           admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "full",    business_analyst: "full",    viewer: "view"    },
  { module: "Raporlar — Export (PDF/XLS)", group: "Raporlama",           admin: "full",    test_lead: "full",    qa_engineer: "full",    developer: "none",    business_analyst: "full",    viewer: "none"    },
  { module: "Audit Log — Görüntüle",       group: "Raporlama",           admin: "full",    test_lead: "view",    qa_engineer: "none",    developer: "none",    business_analyst: "none",    viewer: "none",    critical: true },
  // Admin
  { module: "Proje Üyeleri — Yönet",       group: "Yönetim",             admin: "full",    test_lead: "none",    qa_engineer: "none",    developer: "none",    business_analyst: "none",    viewer: "none",    critical: true },
  { module: "Proje Ayarları",              group: "Yönetim",             admin: "full",    test_lead: "limited", qa_engineer: "none",    developer: "none",    business_analyst: "none",    viewer: "none",    critical: true },
  { module: "API Anahtarları — Yönet",     group: "Yönetim",             admin: "full",    test_lead: "none",    qa_engineer: "none",    developer: "none",    business_analyst: "none",    viewer: "none",    critical: true },
  { module: "Webhook — Yönet",             group: "Yönetim",             admin: "full",    test_lead: "none",    qa_engineer: "none",    developer: "none",    business_analyst: "none",    viewer: "none",    critical: true },
];

const RBAC_ROLES: { key: keyof Omit<RbacRow, "module" | "group" | "critical">; label: string; color: string }[] = [
  { key: "admin",            label: "Admin",             color: "text-amber-400"  },
  { key: "test_lead",        label: "Test Lead",         color: "text-purple-400" },
  { key: "qa_engineer",      label: "QA Engineer",       color: "text-teal-400"   },
  { key: "developer",        label: "Developer",         color: "text-blue-400"   },
  { key: "business_analyst", label: "Business Analyst",  color: "text-indigo-400" },
  { key: "viewer",           label: "Viewer",            color: "text-fg-muted"  },
];

function PermBadge({ level, critical }: { level: PermLevel; critical?: boolean }) {
  if (level === "full")    return <span className={`inline-flex items-center gap-1 text-teal-400 font-medium ${critical ? "text-amber-400" : ""}`}><span className="text-[11px]">✓</span><span className="hidden sm:inline text-[10px]">Tam</span></span>;
  if (level === "view")    return <span className="inline-flex items-center gap-1 text-fg-muted"><span className="text-[11px]">◎</span><span className="hidden sm:inline text-[10px]">Görüntüle</span></span>;
  if (level === "limited") return <span className="inline-flex items-center gap-1 text-blue-400"><span className="text-[11px]">◐</span><span className="hidden sm:inline text-[10px]">Kısıtlı</span></span>;
  return <span className="text-fg-disabled text-[11px]">—</span>;
}

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
  const [saveError, setSaveError]             = useState<string | null>(null);
  const [keyError, setKeyError]               = useState<string | null>(null);
  const [revokeError, setRevokeError]         = useState<string | null>(null);
  const [confirmRevokeId, setConfirmRevokeId] = useState<string | null>(null);
  const [createdKey, setCreatedKey]           = useState<ApiKey | null>(null); // one-time reveal

  // Environments state
  const envStorageKey = mpid ? `mgmt-environments-${mpid}` : null;
  const [environments, setEnvironments] = useState<Environment[]>(() => {
    if (typeof window === "undefined") return DEFAULT_ENVIRONMENTS;
    try {
      const raw = envStorageKey ? localStorage.getItem(envStorageKey) : null;
      if (raw) return JSON.parse(raw) as Environment[];
    } catch { /* ignore */ }
    return DEFAULT_ENVIRONMENTS;
  });
  const [editingEnvId, setEditingEnvId]   = useState<string | null>(null);
  const [newEnvName,   setNewEnvName]     = useState("");
  const [newEnvSlug,   setNewEnvSlug]     = useState("");
  const [newEnvUrl,    setNewEnvUrl]      = useState("");
  const [newEnvDesc,   setNewEnvDesc]     = useState("");
  const [envSaved,     setEnvSaved]       = useState(false);

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
    // API hâlâ yükleniyorsa bekle — erken fallback engellemek için
    if (isLoading) return;

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

    // Fallback: localStorage (sadece API boş döndüğünde)
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
  }, [storageKey, settings, isLoading]); // eslint-disable-line react-hooks/exhaustive-deps

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
    setSaveError(null);
    if (mpid) {
      try {
        await updateSettings.mutateAsync({
          default_priority: defaultPriority,
          default_type: defaultType,
          case_key_prefix: caseKeyPrefix,
          case_key_format: caseKeyFormat,
        });
        setSaveToast(true);
        setTimeout(() => setSaveToast(false), 2500);
      } catch (err) {
        setSaveError(err instanceof Error ? err.message : "Kaydetme başarısız oldu.");
      }
    } else {
      setSaveToast(true);
      setTimeout(() => setSaveToast(false), 2500);
    }
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
      try {
        await updateSettings.mutateAsync({
          default_priority: DEFAULT_STORED.defaultPriority,
          default_type: DEFAULT_STORED.defaultType,
          case_key_prefix: DEFAULT_STORED.caseKeyPrefix,
          case_key_format: DEFAULT_STORED.caseKeyFormat,
          notifications: {},
          modules: [],
          tags: [],
        });
      } catch {
        // Backend sıfırlama başarısız olsa da local state temizlendi
      }
    }
    setConfirmReset(false);
  }

  /* ── Environment actions ── */
  function saveEnvironments(envs: Environment[]) {
    setEnvironments(envs);
    if (envStorageKey) localStorage.setItem(envStorageKey, JSON.stringify(envs));
    setEnvSaved(true);
    setTimeout(() => setEnvSaved(false), 2000);
  }

  function toggleEnvActive(id: string) {
    saveEnvironments(environments.map(e => e.id === id ? { ...e, active: !e.active } : e));
  }

  function updateEnvField(id: string, field: keyof Environment, value: string | boolean) {
    saveEnvironments(environments.map(e => e.id === id ? { ...e, [field]: value } : e));
  }

  function addCustomEnv() {
    const name = newEnvName.trim();
    const slug = newEnvSlug.trim().toUpperCase();
    if (!name || !slug) return;
    const newEnv: Environment = {
      id: `custom-${Date.now()}`,
      name,
      slug,
      baseUrl: newEnvUrl.trim(),
      description: newEnvDesc.trim(),
      color: "text-fg border-border bg-surface-overlay",
      active: true,
    };
    saveEnvironments([...environments, newEnv]);
    setNewEnvName(""); setNewEnvSlug(""); setNewEnvUrl(""); setNewEnvDesc("");
  }

  function removeEnv(id: string) {
    if (DEFAULT_ENVIRONMENTS.some(e => e.id === id)) return; // can't delete defaults
    saveEnvironments(environments.filter(e => e.id !== id));
  }

  /* ── API key actions ── */
  async function handleCreateApiKey() {
    const name = newKeyName.trim();
    if (!name || !mpid) return;
    setKeyError(null);
    const expiresAt = newKeyDuration
      ? new Date(Date.now() + newKeyDuration * 24 * 60 * 60 * 1000).toISOString()
      : null;
    try {
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
      // Show one-time reveal modal — key is cleared from state after user dismisses
      setCreatedKey(newKey);
    } catch (err) {
      setKeyError(err instanceof Error ? err.message : "Anahtar oluşturulamadı.");
    }
  }

  function handleCopyKey(key: string | undefined, id: string) {
    if (!key) return;
    navigator.clipboard.writeText(key).then(() => {
      setCopyToast(id);
      setTimeout(() => setCopyToast(null), 2000);
    });
  }

  async function handleRevokeKey(id: string) {
    if (confirmRevokeId !== id) {
      setConfirmRevokeId(id);
      return;
    }
    setConfirmRevokeId(null);
    if (!mpid) return;
    setRevokeError(null);
    try {
      await apiFetch<void>(`/api/v1/test-management/projects/${mpid}/api-keys/${id}`, { method: "DELETE" });
      setApiKeys(prev => prev.map(k => k.id === id ? { ...k, revokedAt: new Date().toISOString(), revealed: false, key: undefined } : k));
    } catch (err) {
      setRevokeError(err instanceof Error ? err.message : "Anahtar iptal edilemedi.");
    }
  }

  /* ── preview key ── */
  const previewKey = caseKeyFormat
    .replace("PREFIX", caseKeyPrefix || "TC")
    .replace(/#+/, (m) => String(1).padStart(m.length, "0"));

  /* ─────────────────────────────── render ─────────────────────────────── */
  return (
    <div className="min-h-[calc(100vh-88px)] bg-bg text-fg">

      {/* ── page header ── */}
      <div className="border-b border-border bg-surface-raised px-6 py-4">
        <h1 className="text-[13px] font-semibold text-fg">Ayarlar</h1>
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
                  : "border-transparent text-fg-subtle hover:text-fg",
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
              <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Workspace Bilgileri</h2>
              {isLoading ? (
                <div className="animate-pulse space-y-2">
                  {[1, 2].map(i => <div key={i} className="h-8 rounded bg-surface-overlay" />)}
                </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <label className="mb-1 block text-[11px] text-fg-subtle">Project ID</label>
                    <div className="rounded-md border border-border bg-surface-overlay/30 px-3 py-2 text-[13px] text-fg-muted font-mono">
                      {mpid || "—"}
                    </div>
                  </div>
                  <div>
                    <label className="mb-1 block text-[11px] text-fg-subtle">İzinler</label>
                    <div className="flex flex-wrap gap-1.5">
                      {(settings?.permissions ?? []).map((p: string) => (
                        <span key={p} className="rounded bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-muted">{p}</span>
                      ))}
                      {!settings?.permissions?.length && <span className="text-[11px] text-fg-disabled">—</span>}
                    </div>
                  </div>
                  <div>
                    <label className="mb-1 block text-[11px] text-fg-subtle">Custom Field Kullanımı</label>
                    <p className="text-[13px] text-fg">
                      {settings?.custom_field_usage?.cases_with_custom_fields ?? 0} /{" "}
                      {settings?.custom_field_usage?.case_count ?? 0} case
                    </p>
                  </div>
                </div>
              )}
            </section>

            {/* Varsayılan değerler */}
            <section className="rounded-xl border border-border bg-surface-raised p-5">
              <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Varsayılan Değerler</h2>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-[11px] text-fg-subtle">Varsayılan Öncelik</label>
                    <select
                      value={defaultPriority}
                      onChange={e => setDefaultPriority(e.target.value)}
                      className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/50"
                    >
                      {["P0", "P1", "P2", "P3"].map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-[11px] text-fg-subtle">Varsayılan Test Tipi</label>
                    <select
                      value={defaultType}
                      onChange={e => setDefaultType(e.target.value)}
                      className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/50"
                    >
                      {["manual", "exploratory", "regression", "smoke", "uat"].map(t => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Case key prefix / format */}
                <div className="rounded-lg border border-border bg-surface-overlay/30 p-4 space-y-3">
                  <p className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Case Key Formatı</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1 block text-[11px] text-fg-subtle">Key Prefix</label>
                      <input
                        type="text"
                        value={caseKeyPrefix}
                        onChange={e => setCaseKeyPrefix(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))}
                        maxLength={6}
                        placeholder="TC"
                        className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-fg placeholder:text-fg-disabled outline-none focus:border-teal-500/50 font-mono"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-[11px] text-fg-subtle">Format</label>
                      <select
                        value={caseKeyFormat}
                        onChange={e => setCaseKeyFormat(e.target.value)}
                        className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/50"
                      >
                        {KEY_FORMAT_OPTIONS.map(o => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-fg-subtle">
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
                {saveError && (
                  <span className="text-[12px] text-red-400">{saveError}</span>
                )}
              </div>
              <p className="mt-3 text-[10px] text-fg-disabled">Bu değerler yeni case oluştururken varsayılan olarak atanır.</p>
            </section>
          </>
        )}

        {/* ══════════════ MODÜLLER & ETİKETLER ══════════════ */}
        {activeTab === "modules" && (
          <>
            {/* Modüller */}
            <section className="rounded-xl border border-border bg-surface-raised p-5">
              <h2 className="mb-1 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Modüller</h2>
              <p className="mb-4 text-[11px] text-fg-disabled">Değişiklikler otomatik kaydedilir.</p>
              <div className="flex gap-2 mb-3">
                <input
                  type="text"
                  value={newModule}
                  onChange={e => setNewModule(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && addModule()}
                  placeholder="Modül adı..."
                  className="flex-1 rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-fg placeholder:text-fg-disabled outline-none focus:border-teal-500/50"
                />
                <button
                  onClick={addModule}
                  className="rounded-xl bg-brand px-3 py-1.5 text-[12px] font-semibold text-brand-fg transition-colors hover:brightness-105"
                >
                  Ekle
                </button>
              </div>
              {modules.length === 0 ? (
                <p className="text-[11px] text-fg-disabled">Henüz modül eklenmedi.</p>
              ) : (
                <ul className="space-y-1.5">
                  {modules.map(mod => (
                    <li key={mod} className="flex items-center justify-between rounded-lg border border-border bg-surface-overlay/30 px-3 py-2">
                      <span className="text-[13px] text-fg">{mod}</span>
                      <button
                        onClick={() => removeModule(mod)}
                        className="text-[11px] text-fg-subtle hover:text-red-400 transition-colors"
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
              <h2 className="mb-1 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Etiketler</h2>
              <p className="mb-4 text-[11px] text-fg-disabled">Değişiklikler otomatik kaydedilir.</p>
              <div className="flex gap-2 mb-3">
                <input
                  type="text"
                  value={newTag}
                  onChange={e => setNewTag(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && addTag()}
                  placeholder="Etiket adı..."
                  className="flex-1 rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-fg placeholder:text-fg-disabled outline-none focus:border-teal-500/50"
                />
                <button
                  onClick={addTag}
                  className="rounded-xl bg-brand px-3 py-1.5 text-[12px] font-semibold text-brand-fg transition-colors hover:brightness-105"
                >
                  Ekle
                </button>
              </div>
              {tags.length === 0 ? (
                <p className="text-[11px] text-fg-disabled">Henüz etiket eklenmedi.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {tags.map(tag => (
                    <span
                      key={tag}
                      className="flex items-center gap-1.5 rounded-full border border-border bg-surface-overlay px-3 py-1 text-[12px] text-fg"
                    >
                      {tag}
                      <button
                        onClick={() => removeTag(tag)}
                        className="text-fg-subtle hover:text-red-400 transition-colors leading-none"
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
        {activeTab === "roles" && (() => {
          // Group rows by module group
          const groups: Record<string, RbacRow[]> = {};
          for (const row of RBAC_MATRIX) {
            if (!groups[row.group]) groups[row.group] = [];
            groups[row.group].push(row);
          }
          return (
            <div className="space-y-5">
              {/* Legend */}
              <section className="rounded-xl border border-border bg-surface-raised p-5">
                <h2 className="mb-1 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Roller ve Yetki Matrisi</h2>
                <p className="mb-4 text-[11px] text-fg-disabled">
                  Her rolün modüllere erişim düzeyi aşağıda tanımlanmıştır. Rol atamaları
                  <a href="../members" className="ml-1 text-brand hover:underline">Üyeler</a> bölümünden yapılır.
                </p>
                {/* Role chips */}
                <div className="mb-4 flex flex-wrap gap-2">
                  {RBAC_ROLES.map(r => (
                    <span key={r.key} className={`rounded-full border border-border bg-surface-overlay px-3 py-1 text-[11px] font-medium ${r.color}`}>
                      {r.label}
                    </span>
                  ))}
                </div>
                {/* Legend icons */}
                <div className="flex flex-wrap gap-4 text-[11px] text-fg-subtle">
                  <span><span className="text-teal-400 mr-1">✓ Tam</span> — tam erişim</span>
                  <span><span className="text-amber-400 mr-1">✓ Tam*</span> — kritik işlem, dikkatli kullanın</span>
                  <span><span className="text-blue-400 mr-1">◐ Kısıtlı</span> — kısmi erişim</span>
                  <span><span className="text-fg-muted mr-1">◎ Görüntüle</span> — salt okunur</span>
                  <span><span className="text-fg-disabled mr-1">—</span> — erişim yok</span>
                </div>
              </section>

              {/* Matrix per group */}
              {Object.entries(groups).map(([groupName, rows]) => (
                <section key={groupName} className="rounded-xl border border-border bg-surface-raised overflow-hidden">
                  <div className="border-b border-border bg-surface-overlay px-4 py-2.5">
                    <h3 className="text-[11px] font-semibold uppercase tracking-wider text-fg-muted">{groupName}</h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-[11px]">
                      <thead>
                        <tr className="border-b border-border bg-surface-overlay/30">
                          <th className="px-4 py-2 text-left font-medium text-fg-subtle min-w-[200px]">Yetki</th>
                          {RBAC_ROLES.map(r => (
                            <th key={r.key} className={`px-3 py-2 text-center font-medium min-w-[90px] ${r.color}`}>
                              {r.label}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/50">
                        {rows.map((row, i) => (
                          <tr key={row.module} className={i % 2 === 0 ? "" : "bg-surface-overlay/30"}>
                            <td className="px-4 py-2 text-fg">
                              {row.module}
                              {row.critical && (
                                <span className="ml-2 rounded px-1 py-0.5 text-[9px] bg-amber-500/10 text-amber-500 border border-amber-500/20">
                                  KRİTİK
                                </span>
                              )}
                            </td>
                            {RBAC_ROLES.map(r => (
                              <td key={r.key} className="px-3 py-2 text-center">
                                <PermBadge level={row[r.key] as PermLevel} critical={row.critical && row[r.key] === "full"} />
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              ))}

              <p className="text-[10px] text-fg-disabled px-1">
                * Kritik işlemler audit log&apos;a kaydedilir ve geri alınamaz. Dikkatli kullanın.
              </p>
            </div>
          );
        })()}

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
              <h2 className="mb-1 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Bildirimler</h2>
              <p className="mb-4 text-[11px] text-fg-disabled">Değişiklikler otomatik kaydedilir.</p>
              <div className="space-y-5">
                {Object.entries(groups).map(([groupName, items]) => (
                  <div key={groupName}>
                    <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-fg-subtle px-3">{groupName}</p>
                    <div className="space-y-0.5">
                      {items.map(({ key, label, desc }) => {
                        const active = !!notifications[key];
                        return (
                          <button
                            key={key}
                            type="button"
                            onClick={() => toggleNotif(key)}
                            className="w-full flex items-center justify-between rounded-lg px-3 py-2.5 hover:bg-surface-overlay transition-colors text-left gap-4"
                          >
                            <div className="flex-1 min-w-0">
                              <span className="block text-[13px] text-fg">{label}</span>
                              <span className="block text-[11px] text-fg-disabled mt-0.5">{desc}</span>
                            </div>
                            {/* toggle pill */}
                            <div
                              className={[
                                "relative h-5 w-9 rounded-full transition-colors shrink-0",
                                active ? "bg-brand" : "bg-surface-accent",
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
                <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">API Anahtarları</h2>
                <p className="mt-1 text-[11px] text-fg-disabled">Tam anahtar yalnız oluşturulduğu anda gösterilir.</p>
              </div>
              <button
                onClick={() => setShowKeyModal(true)}
                disabled={!mpid || keysLoading}
                className="rounded-xl bg-brand px-3 py-1.5 text-[12px] font-semibold text-brand-fg transition-colors hover:brightness-105"
              >
                + Yeni Anahtar Oluştur
              </button>
            </div>

            {revokeError && (
              <p className="mb-3 text-[12px] text-red-400">{revokeError}</p>
            )}
            {keysLoading ? (
              <p className="py-6 text-center text-[12px] text-fg-disabled">Anahtarlar yükleniyor…</p>
            ) : apiKeys.length === 0 ? (
              <p className="py-6 text-center text-[12px] text-fg-disabled">Henüz API anahtarı oluşturulmadı.</p>
            ) : (
              <ul className="space-y-2">
                {apiKeys.map(k => {
                  const isExpired = k.expiresAt ? new Date(k.expiresAt) < new Date() : false;
                  const isRevoked = !!k.revokedAt;
                  const expiresLabel = k.expiresAt
                    ? `${new Date(k.expiresAt).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })}'e kadar`
                    : "Sınırsız";
                  const displayKey = k.revealed && k.key ? k.key : k.maskedKey;
                  const pendingRevoke = confirmRevokeId === k.id;
                  return (
                    <li
                      key={k.id}
                      className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${
                        isExpired || isRevoked ? "border-red-500/20 bg-red-500/5 opacity-60" : "border-border bg-surface-overlay/30"
                      }`}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-[12px] font-medium text-fg truncate">{k.name}</p>
                        <p className="mt-0.5 font-mono text-[11px] text-fg-subtle truncate">{displayKey}</p>
                      </div>
                      <span className={`shrink-0 text-[10px] ${isExpired || isRevoked ? "text-red-400" : "text-fg-subtle"}`}>
                        {isRevoked ? "İptal edildi" : isExpired ? "Süresi doldu" : expiresLabel}
                      </span>
                      <button
                        onClick={() => handleCopyKey(k.key, k.id)}
                        disabled={!k.key || isRevoked}
                        className="shrink-0 rounded-md border border-border px-2 py-1 text-[11px] text-fg-muted transition-colors hover:text-fg"
                      >
                        {copyToast === k.id ? "Kopyalandı ✓" : "Kopyala"}
                      </button>
                      {pendingRevoke ? (
                        <>
                          <button
                            onClick={() => handleRevokeKey(k.id)}
                            className="shrink-0 rounded-md border border-red-500/40 px-2 py-1 text-[11px] font-medium text-red-400 transition-colors hover:bg-red-500/10"
                          >
                            Onayla
                          </button>
                          <button
                            onClick={() => setConfirmRevokeId(null)}
                            className="shrink-0 text-[11px] text-fg-subtle transition-colors hover:text-fg"
                          >
                            Vazgec
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => handleRevokeKey(k.id)}
                          disabled={isRevoked}
                          className="shrink-0 text-[11px] text-fg-disabled transition-colors hover:text-red-400"
                        >
                          İptal
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        )}

        {/* ══════════════ ORTAMLAR ══════════════ */}
        {activeTab === "environments" && (
          <section className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-[13px] font-semibold text-fg">Test Ortamları</h2>
                <p className="mt-0.5 text-[11px] text-fg-muted">
                  Projenizin test ortamlarını tanımlayın. Aktif ortamlar test koşumu oluştururken seçilebilir.
                </p>
              </div>
              {envSaved && (
                <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[11px] text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  Kaydedildi
                </span>
              )}
            </div>

            {/* Environment list */}
            <div className="space-y-3">
              {environments.map(env => (
                <div
                  key={env.id}
                  className={`rounded-xl border p-4 transition-all ${env.active ? env.color : "border-border bg-surface-overlay text-fg-muted opacity-60"}`}
                >
                  {editingEnvId === env.id ? (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="mb-1 block text-[10px] uppercase tracking-widest text-fg-disabled">Ad</label>
                          <input
                            defaultValue={env.name}
                            onBlur={e => updateEnvField(env.id, "name", e.target.value)}
                            className="w-full rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-[12px] text-fg outline-none focus:border-brand/50"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-[10px] uppercase tracking-widest text-fg-disabled">Kısa Ad (ör. DEV)</label>
                          <input
                            defaultValue={env.slug}
                            onBlur={e => updateEnvField(env.id, "slug", e.target.value.toUpperCase())}
                            className="w-full rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-[12px] font-mono text-fg outline-none focus:border-brand/50"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="mb-1 block text-[10px] uppercase tracking-widest text-fg-disabled">Base URL</label>
                        <input
                          defaultValue={env.baseUrl}
                          onBlur={e => updateEnvField(env.id, "baseUrl", e.target.value)}
                          className="w-full rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-[12px] font-mono text-fg outline-none focus:border-brand/50"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-[10px] uppercase tracking-widest text-fg-disabled">Açıklama</label>
                        <input
                          defaultValue={env.description}
                          onBlur={e => updateEnvField(env.id, "description", e.target.value)}
                          className="w-full rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-[12px] text-fg outline-none focus:border-brand/50"
                        />
                      </div>
                      <button
                        onClick={() => setEditingEnvId(null)}
                        className="rounded-lg bg-brand px-4 py-1.5 text-[11px] font-semibold text-brand-fg hover:brightness-105"
                      >
                        Tamam
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-mono text-[11px] font-bold tracking-widest">{env.slug}</span>
                          <span className={`rounded px-1.5 py-0.5 text-[9px] font-medium border ${env.active ? "border-current/20 bg-current/5" : "border-border bg-surface-overlay text-fg-disabled"}`}>
                            {env.active ? "Aktif" : "Pasif"}
                          </span>
                        </div>
                        <p className="text-[13px] font-medium text-fg">{env.name}</p>
                        {env.baseUrl && (
                          <p className="mt-0.5 font-mono text-[10px] text-fg-muted truncate">{env.baseUrl}</p>
                        )}
                        {env.description && (
                          <p className="mt-0.5 text-[11px] text-fg-subtle">{env.description}</p>
                        )}
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <button
                          onClick={() => setEditingEnvId(env.id)}
                          className="rounded-lg border border-border bg-surface-raised px-2.5 py-1 text-[10px] text-fg-muted hover:text-fg transition-colors"
                        >
                          Düzenle
                        </button>
                        <button
                          onClick={() => toggleEnvActive(env.id)}
                          className={`rounded-lg border px-2.5 py-1 text-[10px] font-medium transition-colors ${env.active ? "border-amber-500/30 text-amber-400 hover:bg-amber-500/10" : "border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"}`}
                        >
                          {env.active ? "Pasif Et" : "Etkinleştir"}
                        </button>
                        {!DEFAULT_ENVIRONMENTS.some(d => d.id === env.id) && (
                          <button
                            onClick={() => removeEnv(env.id)}
                            className="rounded-lg border border-red-500/20 px-2 py-1 text-[10px] text-red-400 hover:bg-red-500/10 transition-colors"
                          >
                            Sil
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Add custom environment */}
            <div className="rounded-xl border border-dashed border-border p-4">
              <p className="mb-3 text-[11px] font-semibold text-fg">Yeni Ortam Ekle</p>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="mb-1 block text-[10px] uppercase tracking-widest text-fg-disabled">Ad *</label>
                  <input
                    value={newEnvName}
                    onChange={e => setNewEnvName(e.target.value)}
                    placeholder="ör. Staging"
                    className="w-full rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-[12px] text-fg outline-none focus:border-brand/50 placeholder:text-fg-disabled"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[10px] uppercase tracking-widest text-fg-disabled">Kısa Ad *</label>
                  <input
                    value={newEnvSlug}
                    onChange={e => setNewEnvSlug(e.target.value.toUpperCase())}
                    placeholder="ör. STG"
                    maxLength={8}
                    className="w-full rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-[12px] font-mono text-fg outline-none focus:border-brand/50 placeholder:text-fg-disabled"
                  />
                </div>
              </div>
              <div className="mb-3">
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-fg-disabled">Base URL</label>
                <input
                  value={newEnvUrl}
                  onChange={e => setNewEnvUrl(e.target.value)}
                  placeholder="https://staging.example.com"
                  className="w-full rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-[12px] font-mono text-fg outline-none focus:border-brand/50 placeholder:text-fg-disabled"
                />
              </div>
              <div className="mb-3">
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-fg-disabled">Açıklama</label>
                <input
                  value={newEnvDesc}
                  onChange={e => setNewEnvDesc(e.target.value)}
                  placeholder="Bu ortamın amacı…"
                  className="w-full rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-[12px] text-fg outline-none focus:border-brand/50 placeholder:text-fg-disabled"
                />
              </div>
              <button
                onClick={addCustomEnv}
                disabled={!newEnvName.trim() || !newEnvSlug.trim()}
                className="rounded-lg bg-surface-overlay border border-border px-4 py-1.5 text-[11px] font-semibold text-fg-muted hover:text-fg hover:bg-surface-accent disabled:opacity-40 transition-colors"
              >
                + Ortam Ekle
              </button>
            </div>

            {/* Usage hint */}
            <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 px-4 py-3">
              <p className="text-[11px] text-blue-400/90">
                <strong>İpucu:</strong> Aktif ortamlar, test koşumu oluştururken "Ortam" seçim listesinde görünür. PROD ortamını pasif bırakarak yalnızca yetkili kullanıcıların canlı ortamda test yapmasını engelleyebilirsiniz.
              </p>
            </div>
          </section>
        )}

        {/* ══════════════ TEHLİKE BÖLGESİ ══════════════ */}
        {activeTab === "danger" && (
          <section className="rounded-xl border border-red-500/20 bg-red-500/[0.03] p-5">
            <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-red-500/70">Tehlike Bölgesi</h2>

            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[13px] text-fg">Ayarları Sıfırla</p>
                <p className="mt-0.5 text-[11px] text-fg-subtle">
                  Tüm proje ayarlarını (modüller, etiketler, bildirimler, varsayılan değerler) fabrika ayarlarına döndürür. Bu işlem geri alınamaz.
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
            <h3 className="mb-4 text-[14px] font-semibold text-fg">Yeni API Anahtarı</h3>
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-[11px] text-fg-subtle">Anahtar Adı</label>
                <input
                  type="text"
                  value={newKeyName}
                  onChange={e => setNewKeyName(e.target.value)}
                  placeholder="ör. CI/CD Pipeline"
                  className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-fg placeholder:text-fg-disabled outline-none focus:border-teal-500/50"
                  autoFocus
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-fg-subtle">Süre</label>
                <div className="flex gap-2 flex-wrap">
                  {API_KEY_DURATIONS.map(opt => (
                    <button
                      key={opt.label}
                      type="button"
                      onClick={() => setNewKeyDuration(opt.days)}
                      className={`rounded-lg border px-3 py-1.5 text-[11px] font-medium transition-colors ${
                        newKeyDuration === opt.days
                          ? "border-teal-500/50 bg-teal-500/10 text-teal-400"
                          : "border-border text-fg-muted hover:text-fg"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            {keyError && (
              <p className="mt-3 text-[12px] text-red-400">{keyError}</p>
            )}
            <div className="mt-6 flex gap-3 justify-end">
              <button
                onClick={() => { setShowKeyModal(false); setNewKeyName(""); setKeyError(null); }}
                className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted hover:text-fg transition-colors"
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

      {/* ══════════════ API KEY ONE-TIME REVEAL MODAL ══════════════ */}
      {createdKey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-teal-500/30 bg-surface-raised p-6 shadow-2xl">
            <div className="mb-3 flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-teal-500/10">
                <svg className="h-5 w-5 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
              </div>
              <h3 className="text-[14px] font-semibold text-fg">API Anahtarı Oluşturuldu</h3>
            </div>
            <p className="mb-3 text-[12px] text-amber-400/90 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
              Bu anahtar yalnizca bir kez goruntulenir. Simdi kopyalamazsiniz bir daha erisemezsiniz.
            </p>
            <p className="mb-1 text-[11px] text-fg-subtle">Anahtar: <span className="text-fg">{createdKey.name}</span></p>
            <div className="flex items-center gap-2 mt-2">
              <code className="flex-1 break-all rounded-lg border border-border bg-surface-overlay px-3 py-2 font-mono text-[12px] text-teal-300 select-all">
                {createdKey.key}
              </code>
              <button
                onClick={() => {
                  if (createdKey.key) {
                    navigator.clipboard.writeText(createdKey.key).then(() => {
                      setCopyToast(createdKey.id);
                      setTimeout(() => setCopyToast(null), 2000);
                    });
                  }
                }}
                className="shrink-0 rounded-lg border border-border px-3 py-2 text-[12px] text-fg-muted hover:text-fg transition-colors"
              >
                {copyToast === createdKey.id ? "Kopyalandi ✓" : "Kopyala"}
              </button>
            </div>
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => {
                  // Clear full key from state — only masked key remains
                  setApiKeys(prev => prev.map(k =>
                    k.id === createdKey.id ? { ...k, revealed: false, key: undefined } : k
                  ));
                  setCreatedKey(null);
                }}
                className="rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg transition-colors hover:brightness-105"
              >
                Kopyaladim, kapat
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
              <h3 className="text-[14px] font-semibold text-fg">Ayarları Sıfırla</h3>
            </div>
            <p className="mb-6 text-[13px] text-fg-muted">
              Bu işlem tüm proje ayarlarını (modüller, etiketler, bildirimler, varsayılan değerler) fabrika ayarlarına döndürür.
              Devam etmek istediğinizden emin misiniz?
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmReset(false)}
                className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted hover:text-fg transition-colors"
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
