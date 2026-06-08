"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouteParam } from "@/lib/use-route-param";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useManagementRepository } from "@/lib/hooks/use-management";
import { apiFetch } from "@/lib/api-client";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────────

type Platform = "ios" | "android" | "cross";
type DeviceCategory = "phone" | "tablet" | "foldable" | "watch" | "tv";
type MobileResult = "pass" | "fail" | "blocked" | "not_run";

interface MobileTestConfig {
  id: string;
  case_id: string;
  platform: Platform;
  device_category: DeviceCategory;
  device_name: string;
  os_version: string;
  app_version: string;
  screen_size?: string;
  notes?: string;
  created_at: string;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const PLATFORMS: { value: Platform; label: string; icon: string; color: string }[] = [
  { value: "ios",     label: "iOS",     icon: "",  color: "text-fg border-border-strong/30 bg-slate-500/10" },
  { value: "android", label: "Android", icon: "🤖", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" },
  { value: "cross",   label: "Cross-Platform", icon: "🔀", color: "text-blue-400 border-blue-500/30 bg-blue-500/10" },
];

const DEVICE_CATEGORIES: { value: DeviceCategory; label: string; icon: string }[] = [
  { value: "phone",    label: "Telefon",       icon: "📱" },
  { value: "tablet",   label: "Tablet",        icon: "📟" },
  { value: "foldable", label: "Katlanabilir",  icon: "📲" },
  { value: "watch",    label: "Akıllı Saat",   icon: "⌚" },
  { value: "tv",       label: "TV / Büyük Ekran", icon: "📺" },
];

const MOBILE_RESULT_CONFIG: Record<MobileResult, { label: string; color: string }> = {
  pass:    { label: "Geçti",   color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" },
  fail:    { label: "Başarısız", color: "text-red-400 border-red-500/30 bg-red-500/10" },
  blocked: { label: "Engellendi", color: "text-amber-400 border-amber-500/30 bg-amber-500/10" },
  not_run: { label: "Çalıştırılmadı", color: "text-fg-muted border-border bg-surface-overlay" },
};

const IOS_VERSIONS     = ["iOS 17", "iOS 16", "iOS 15", "iOS 14", "iOS 13"];
const ANDROID_VERSIONS = ["Android 14", "Android 13", "Android 12", "Android 11", "Android 10"];

const POPULAR_DEVICES: Record<Platform, string[]> = {
  ios: [
    "iPhone 15 Pro Max", "iPhone 15 Pro", "iPhone 15", "iPhone 14 Pro",
    "iPhone 14", "iPhone SE (3rd gen)", "iPad Pro 12.9\"", "iPad Air (5th gen)",
  ],
  android: [
    "Samsung Galaxy S24 Ultra", "Samsung Galaxy S24+", "Samsung Galaxy A55",
    "Google Pixel 8 Pro", "Google Pixel 8", "OnePlus 12",
    "Xiaomi 14 Pro", "Samsung Galaxy Tab S9",
  ],
  cross: ["Emulator / Simulator"],
};

const TEST_CATEGORIES = [
  "Fonksiyonel Test",
  "UI/UX Testi",
  "Performans Testi",
  "Ağ Koşulu Testi",
  "Batarya Tüketim Testi",
  "Push Bildirim Testi",
  "Kamera/Galeri Testi",
  "Konum Servisi Testi",
  "Erişilebilirlik Testi",
  "Regresyon Testi",
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function PlatformBadge({ platform }: { platform: Platform }) {
  const p = PLATFORMS.find(x => x.value === platform)!;
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium", p.color)}>
      <span>{p.icon}</span>
      <span>{p.label}</span>
    </span>
  );
}

// ── Create Config Modal ───────────────────────────────────────────────────────

function CreateMobileConfigModal({
  caseId,
  caseKey,
  onClose,
}: {
  caseId: string;
  caseKey: string;
  onClose: () => void;
}) {
  const [platform, setPlatform]           = useState<Platform>("ios");
  const [deviceCategory, setDeviceCategory] = useState<DeviceCategory>("phone");
  const [deviceName, setDeviceName]       = useState("");
  const [osVersion, setOsVersion]         = useState("");
  const [appVersion, setAppVersion]       = useState("");
  const [screenSize, setScreenSize]       = useState("");
  const [notes, setNotes]                 = useState("");
  const [category, setCategory]           = useState("");
  const [submitting, setSubmitting]       = useState(false);
  const [error, setError]                 = useState<string | null>(null);

  const osVersions = platform === "ios" ? IOS_VERSIONS : ANDROID_VERSIONS;
  const devices    = POPULAR_DEVICES[platform];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!deviceName || !osVersion || !appVersion) {
      setError("Cihaz adı, OS versiyonu ve uygulama versiyonu zorunludur.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      // Store mobile config in test case custom_fields via PATCH
      await apiFetch(`/api/v1/test-management/cases/${caseId}`, {
        method: "PATCH",
        json: {
          custom_fields: {
            mobile: {
              platform,
              device_category: deviceCategory,
              device_name: deviceName,
              os_version: osVersion,
              app_version: appVersion,
              screen_size: screenSize || undefined,
              notes: notes || undefined,
              test_category: category || undefined,
            },
          },
          change_summary: `Mobil test konfigürasyonu güncellendi (${platform} / ${deviceName})`,
        },
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kaydedilemedi");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-2xl border border-border bg-surface-raised shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <h3 className="text-[13px] font-semibold text-fg">Mobil Test Konfigürasyonu</h3>
            <p className="mt-0.5 text-[11px] text-fg-subtle">{caseKey} için cihaz/platform bilgisi</p>
          </div>
          <button onClick={onClose} className="rounded-md p-1.5 text-fg-subtle hover:text-fg transition-colors">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-5">
          {/* Platform */}
          <div>
            <label className="mb-2 block text-[11px] font-medium text-fg-subtle">Platform</label>
            <div className="flex gap-2">
              {PLATFORMS.map(p => (
                <button
                  key={p.value}
                  type="button"
                  onClick={() => { setPlatform(p.value); setDeviceName(""); setOsVersion(""); }}
                  className={cn(
                    "flex-1 rounded-lg border px-3 py-2 text-[12px] font-medium transition-all",
                    platform === p.value
                      ? p.color + " ring-1 ring-current/30"
                      : "border-border text-fg-muted hover:text-fg"
                  )}
                >
                  {p.icon} {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Device Category */}
          <div>
            <label className="mb-2 block text-[11px] font-medium text-fg-subtle">Cihaz Kategorisi</label>
            <div className="flex gap-2">
              {DEVICE_CATEGORIES.map(c => (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => setDeviceCategory(c.value)}
                  className={cn(
                    "rounded-lg border px-3 py-1.5 text-[12px] transition-colors flex items-center gap-1",
                    deviceCategory === c.value
                      ? "border-brand/40 bg-brand-soft text-brand"
                      : "border-border text-fg-muted hover:text-fg"
                  )}
                >
                  <span>{c.icon}</span> {c.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Device Name */}
            <div>
              <label className="mb-1 block text-[11px] text-fg-subtle">Cihaz Adı *</label>
              <input
                list="device-list"
                value={deviceName}
                onChange={e => setDeviceName(e.target.value)}
                placeholder="Cihaz seçin veya yazın..."
                className="w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[12px] text-fg placeholder:text-fg-disabled outline-none focus:border-brand/50"
              />
              <datalist id="device-list">
                {devices.map(d => <option key={d} value={d} />)}
              </datalist>
            </div>

            {/* OS Version */}
            <div>
              <label className="mb-1 block text-[11px] text-fg-subtle">OS Versiyonu *</label>
              <select
                value={osVersion}
                onChange={e => setOsVersion(e.target.value)}
                className="w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[12px] text-fg outline-none focus:border-brand/50"
              >
                <option value="">Seçin...</option>
                {osVersions.map(v => <option key={v} value={v}>{v}</option>)}
                <option value="Diğer">Diğer</option>
              </select>
            </div>

            {/* App Version */}
            <div>
              <label className="mb-1 block text-[11px] text-fg-subtle">Uygulama Versiyonu *</label>
              <input
                value={appVersion}
                onChange={e => setAppVersion(e.target.value)}
                placeholder="ör. 2.5.1 (build 100)"
                className="w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[12px] text-fg placeholder:text-fg-disabled outline-none focus:border-brand/50"
              />
            </div>

            {/* Screen Size */}
            <div>
              <label className="mb-1 block text-[11px] text-fg-subtle">Ekran Boyutu</label>
              <input
                value={screenSize}
                onChange={e => setScreenSize(e.target.value)}
                placeholder='ör. 6.7"'
                className="w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[12px] text-fg placeholder:text-fg-disabled outline-none focus:border-brand/50"
              />
            </div>
          </div>

          {/* Test Category */}
          <div>
            <label className="mb-1 block text-[11px] text-fg-subtle">Test Kategorisi</label>
            <select
              value={category}
              onChange={e => setCategory(e.target.value)}
              className="w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[12px] text-fg outline-none focus:border-brand/50"
            >
              <option value="">Seçin...</option>
              {TEST_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {/* Notes */}
          <div>
            <label className="mb-1 block text-[11px] text-fg-subtle">Notlar</label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              rows={3}
              placeholder="Özel cihaz koşulları, ağ ayarları, ön koşullar..."
              className="w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[12px] text-fg placeholder:text-fg-disabled outline-none focus:border-brand/50 resize-none"
            />
          </div>

          {error && (
            <p className="rounded-lg bg-red-500/10 px-3 py-2 text-[12px] text-red-400">{error}</p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted hover:text-fg transition-colors"
            >
              İptal
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 disabled:opacity-50 transition-colors"
            >
              {submitting ? "Kaydediliyor…" : "Kaydet"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function MobileTestAreaPage() {
  const projectId = useRouteParam("projectId");
  const mpid      = useManagementProjectId(projectId || undefined);

  const repoQ = useManagementRepository(mpid || undefined);

  const [selectedPlatform, setSelectedPlatform] = useState<Platform | "all">("all");
  const [search, setSearch]                      = useState("");
  const [configTarget, setConfigTarget]          = useState<{ id: string; key: string } | null>(null);
  const [results, setResults]                    = useState<Record<string, MobileResult>>(() => {
    try { return JSON.parse(localStorage.getItem(`mobile-results-${mpid}`) || "{}"); }
    catch { return {}; }
  });

  function setResult(caseId: string, result: MobileResult) {
    setResults(prev => {
      const next = { ...prev, [caseId]: result };
      try { localStorage.setItem(`mobile-results-${mpid}`, JSON.stringify(next)); } catch {}
      return next;
    });
  }

  const cases = repoQ.data?.cases ?? [];

  // Filter cases that have mobile custom_fields, or all cases
  const mobileCases = cases.filter(tc => {
    const hasMobile = !!(tc.custom_fields as Record<string, unknown>)?.mobile;
    const matchesSearch =
      !search ||
      tc.title.toLowerCase().includes(search.toLowerCase()) ||
      tc.case_key.toLowerCase().includes(search.toLowerCase());

    if (selectedPlatform !== "all") {
      const mobile = (tc.custom_fields as Record<string, Record<string, string>>)?.mobile;
      if (!mobile || mobile.platform !== selectedPlatform) return false;
    }

    return matchesSearch;
  });

  const stats = {
    ios:     cases.filter(tc => (tc.custom_fields as Record<string, Record<string, string>>)?.mobile?.platform === "ios").length,
    android: cases.filter(tc => (tc.custom_fields as Record<string, Record<string, string>>)?.mobile?.platform === "android").length,
    cross:   cases.filter(tc => (tc.custom_fields as Record<string, Record<string, string>>)?.mobile?.platform === "cross").length,
    total:   cases.filter(tc => !!(tc.custom_fields as Record<string, unknown>)?.mobile).length,
  };

  const resultStats = {
    pass:    Object.values(results).filter(r => r === "pass").length,
    fail:    Object.values(results).filter(r => r === "fail").length,
    blocked: Object.values(results).filter(r => r === "blocked").length,
    total:   Object.keys(results).length,
  };

  return (
    <div className="min-h-[calc(100vh-88px)] bg-bg">
      {/* ── Header ── */}
      <div className="border-b border-border bg-surface-raised px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg">📱</span>
              <h1 className="text-[15px] font-semibold text-fg">Mobil Test Alanı</h1>
            </div>
            <p className="mt-1 text-[11px] text-fg-subtle">
              iOS ve Android platformlarına özgü test case yönetimi ve cihaz konfigürasyonları
            </p>
          </div>
          <button
            onClick={() => {
              const firstCase = cases[0];
              if (firstCase) setConfigTarget({ id: firstCase.id, key: firstCase.case_key });
            }}
            className="flex items-center gap-1.5 rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 transition-colors"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/>
            </svg>
            Konfigürasyon Ekle
          </button>
        </div>
      </div>

      <div className="p-6 space-y-5">
        {/* ── Stats ── */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Toplam Mobil TC", value: stats.total, icon: "📊", color: "border-border" },
            { label: "iOS", value: stats.ios, icon: "", color: "border-border" },
            { label: "Android", value: stats.android, icon: "🤖", color: "border-emerald-500/20 bg-emerald-500/5" },
            { label: "Cross-Platform", value: stats.cross, icon: "🔀", color: "border-blue-500/20 bg-blue-500/5" },
          ].map(stat => (
            <div key={stat.label} className={cn("rounded-xl border p-4 bg-surface-raised", stat.color)}>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">{stat.icon} {stat.label}</p>
              <p className="mt-2 text-2xl font-semibold text-fg">{stat.value}</p>
            </div>
          ))}
        </div>

        {/* ── Platform guidelines ── */}
        <div className="grid gap-4 xl:grid-cols-2">
          {/* iOS Guidelines */}
          <section className="rounded-xl border border-border bg-surface-raised p-5">
            <h2 className="mb-3 flex items-center gap-2 text-[13px] font-semibold text-fg">
              <span></span> iOS Test Yönergeleri
            </h2>
            <ul className="space-y-1.5 text-[11px] text-fg-subtle">
              {[
                "TestFlight beta dağıtımını doğrulayın",
                "App Store review yönergelerine uygunluk testi yapın",
                "Face ID / Touch ID akışlarını test edin",
                "AirDrop ve iCloud entegrasyonlarını kontrol edin",
                "Farklı ekran boyutlarında (iPhone SE → Pro Max) UI doğrulaması",
                "iOS sürüm geçiş testleri (en az 2 önceki sürüm)",
                "Push notification izinleri ve bölge bildirimleri",
                "Low Power Mode davranışını test edin",
              ].map(item => (
                <li key={item} className="flex items-start gap-2">
                  <span className="mt-0.5 text-teal-500">→</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* Android Guidelines */}
          <section className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5">
            <h2 className="mb-3 flex items-center gap-2 text-[13px] font-semibold text-emerald-400">
              <span>🤖</span> Android Test Yönergeleri
            </h2>
            <ul className="space-y-1.5 text-[11px] text-fg-subtle">
              {[
                "Google Play Store dağıtımını doğrulayın",
                "Farklı OEM skin'lerinde (Samsung One UI, Xiaomi MIUI) test edin",
                "Adaptif layout ve DP/SP bağımsızlığını doğrulayın",
                "Android Runtime izinlerini (runtime permission) test edin",
                "Doze Mode ve App Standby davranışlarını kontrol edin",
                "Google Play Protect uyumluluğunu test edin",
                "Deep link ve intent mekanizmalarını doğrulayın",
                "ProGuard/R8 obfuscation etkisini test edin",
              ].map(item => (
                <li key={item} className="flex items-start gap-2">
                  <span className="mt-0.5 text-emerald-500">→</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>

        {/* ── Filter Bar ── */}
        <div className="flex flex-wrap items-center gap-3">
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Case ara..."
            className="rounded-xl border border-border bg-surface-raised px-3 py-2 text-[12px] text-fg placeholder:text-fg-disabled outline-none focus:border-brand/50 w-52"
          />
          <div className="flex gap-1.5">
            {([{ value: "all", label: "Tümü" }, ...PLATFORMS.map(p => ({ value: p.value, label: p.label }))] as { value: Platform | "all"; label: string }[]).map(p => (
              <button
                key={p.value}
                onClick={() => setSelectedPlatform(p.value)}
                className={cn(
                  "rounded-lg border px-3 py-1.5 text-[11px] font-medium transition-colors",
                  selectedPlatform === p.value
                    ? "border-brand/40 bg-brand-soft text-brand"
                    : "border-border text-fg-muted hover:text-fg"
                )}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* ── Result Summary ── */}
        {resultStats.total > 0 && (
          <div className="flex items-center gap-4 rounded-xl border border-border bg-surface-raised px-4 py-3">
            <p className="text-[11px] font-semibold text-fg-muted">Sonuçlar</p>
            <div className="flex flex-1 items-center gap-3">
              {(["pass", "fail", "blocked"] as MobileResult[]).map(r => {
                const cfg = MOBILE_RESULT_CONFIG[r];
                const cnt = resultStats[r as keyof typeof resultStats] as number;
                return (
                  <span key={r} className={cn("flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-medium", cfg.color)}>
                    <span className="tabular-nums font-semibold">{cnt}</span>
                    <span>{cfg.label}</span>
                  </span>
                );
              })}
              <span className="ml-auto text-[10px] text-fg-disabled">{resultStats.total} / {stats.total} tamamlandı</span>
              <button
                onClick={() => {
                  setResults({});
                  try { localStorage.removeItem(`mobile-results-${mpid}`); } catch {}
                }}
                className="text-[10px] text-fg-disabled hover:text-red-400 transition-colors"
              >Sıfırla</button>
            </div>
          </div>
        )}

        {/* ── Case List ── */}
        <section className="rounded-xl border border-border bg-surface-raised overflow-hidden">
          <div className="border-b border-border bg-surface-overlay px-4 py-3 flex items-center justify-between">
            <h3 className="text-[12px] font-semibold text-fg-muted">
              Mobil Test Case&apos;leri
              <span className="ml-2 text-fg-disabled">({mobileCases.length})</span>
            </h3>
          </div>

          {repoQ.isLoading ? (
            <div className="p-6 space-y-2">
              {[1,2,3,4,5].map(i => (
                <div key={i} className="h-14 animate-pulse rounded-lg bg-surface-overlay" />
              ))}
            </div>
          ) : mobileCases.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <span className="text-4xl">📱</span>
              <div>
                <p className="text-[13px] font-medium text-fg-muted">
                  {search || selectedPlatform !== "all" ? "Filtrelerle eşleşen case bulunamadı" : "Henüz mobil test case yok"}
                </p>
                <p className="mt-1 text-[11px] text-fg-subtle">
                  Test case&apos;lerine mobil konfigürasyon eklemek için &quot;Konfigürasyon Ekle&quot; butonunu kullanın.
                </p>
              </div>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {mobileCases.map(tc => {
                const mobileData = (tc.custom_fields as Record<string, Record<string, string>>)?.mobile;
                return (
                  <div key={tc.id} className="flex items-start gap-4 px-4 py-3 hover:bg-surface-overlay transition-colors">
                    {/* Case info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="shrink-0 font-mono text-[10px] text-fg-disabled">{tc.case_key}</span>
                        <span className="truncate text-[13px] font-medium text-fg">{tc.title}</span>
                      </div>
                      {mobileData && (
                        <div className="mt-1 flex flex-wrap items-center gap-2">
                          <PlatformBadge platform={mobileData.platform as Platform} />
                          {mobileData.device_name && (
                            <span className="text-[11px] text-fg-subtle">{mobileData.device_name}</span>
                          )}
                          {mobileData.os_version && (
                            <span className="rounded border border-border bg-surface-overlay px-1.5 py-0.5 text-[10px] text-fg-subtle">
                              {mobileData.os_version}
                            </span>
                          )}
                          {mobileData.app_version && (
                            <span className="rounded border border-border bg-surface-overlay px-1.5 py-0.5 text-[10px] text-fg-subtle">
                              v{mobileData.app_version}
                            </span>
                          )}
                          {mobileData.test_category && (
                            <span className="rounded border border-brand/20 bg-brand-soft px-1.5 py-0.5 text-[10px] text-brand">
                              {mobileData.test_category}
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Priority */}
                    <span className={cn(
                      "shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium",
                      tc.priority === "P0" ? "border-red-500/30 bg-red-500/10 text-red-400" :
                      tc.priority === "P1" ? "border-orange-500/30 bg-orange-500/10 text-orange-400" :
                      tc.priority === "P2" ? "border-amber-500/30 bg-amber-500/10 text-amber-400" :
                      "border-border bg-surface-overlay text-fg-muted"
                    )}>
                      {tc.priority}
                    </span>

                    {/* Result buttons */}
                    <div className="flex items-center gap-1">
                      {(["pass", "fail", "blocked"] as MobileResult[]).map(r => {
                        const cfg  = MOBILE_RESULT_CONFIG[r];
                        const curr = results[tc.id];
                        return (
                          <button
                            key={r}
                            onClick={() => setResult(tc.id, curr === r ? "not_run" : r)}
                            title={cfg.label}
                            className={cn(
                              "rounded-md border px-2 py-0.5 text-[10px] font-medium transition-colors",
                              curr === r ? cfg.color : "border-border text-fg-disabled hover:text-fg"
                            )}
                          >{cfg.label}</button>
                        );
                      })}
                    </div>

                    {/* Config button */}
                    <button
                      onClick={() => setConfigTarget({ id: tc.id, key: tc.case_key })}
                      className="shrink-0 rounded-lg border border-border px-2.5 py-1 text-[11px] text-fg-muted hover:text-fg hover:border-border-strong transition-colors"
                    >
                      {mobileData ? "Düzenle" : "Konfigüre Et"}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* ── Test Coverage by Platform ── */}
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <h2 className="mb-4 text-[13px] font-semibold text-fg">Platform Kapsam Analizi</h2>
          <div className="space-y-3">
            {PLATFORMS.map(p => {
              const count = p.value === "ios" ? stats.ios : p.value === "android" ? stats.android : stats.cross;
              const total = cases.length || 1;
              const pct   = Math.round((count / total) * 100);
              return (
                <div key={p.value} className="space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-fg-muted">{p.icon} {p.label}</span>
                    <span className="text-fg-subtle tabular-nums">{count} case · %{pct}</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-surface-overlay overflow-hidden">
                    <div
                      className={cn("h-full rounded-full transition-all", {
                        "bg-slate-400": p.value === "ios",
                        "bg-emerald-500": p.value === "android",
                        "bg-blue-500": p.value === "cross",
                      })}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <p className="mt-3 text-[10px] text-fg-disabled">
            Toplam {cases.length} test case içinden {stats.total} tanesi mobil konfigürasyona sahip.
          </p>
        </section>
      </div>

      {/* Config Modal */}
      {configTarget && (
        <CreateMobileConfigModal
          caseId={configTarget.id}
          caseKey={configTarget.key}
          onClose={() => setConfigTarget(null)}
        />
      )}
    </div>
  );
}
