"use client";

/**
 * MobileProductPage — Neurex Mobile için kapsamlı landing.
 *
 * Bölümler:
 *  1. Hero (cihaz farm visualization + 2 CTA)
 *  2. Live Stats Bar (6 metric, sparkline'lar)
 *  3. Device Matrix (12 cihaz grid)
 *  4. OS Distribution + Run Timeline
 *  5. Modules (gerçek copy, live count)
 *  6. AI Insights (mobile-specific)
 *  7. Recent Activity
 *  8. Get Started (onboarding)
 *
 * Tüm renkler `rose-400/500` (Mobile brand).
 */

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useProject } from "@/lib/useProject";
import { StatCard, Sparkline, Avatar } from "@neurex/design-system";

// ─── Tip tanımları ──────────────────────────────────────────────────────────

type Project = { id: string; name: string; description?: string };

type DeviceStatus = "idle" | "running" | "queued" | "offline";

interface Device {
  id: string;
  name: string;
  os: "iOS" | "Android";
  version: string;
  status: DeviceStatus;
  battery: number;
  lastRun?: string;
}

interface AiInsight {
  id: string;
  type: "flaky" | "slow" | "suggestion" | "warning";
  title: string;
  description: string;
  cta?: string;
}

// ─── Mock data (real API gelene kadar) ──────────────────────────────────────

const DEVICES: Device[] = [
  { id: "ip15p",  name: "iPhone 15 Pro",       os: "iOS",     version: "17.4",   status: "running", battery: 87, lastRun: "şu an" },
  { id: "ip14",   name: "iPhone 14",           os: "iOS",     version: "17.3",   status: "idle",    battery: 100, lastRun: "12 dk önce" },
  { id: "ip13m",  name: "iPhone 13 Mini",      os: "iOS",     version: "16.7",   status: "queued",  battery: 64 },
  { id: "ipsem",  name: "iPhone SE 3",         os: "iOS",     version: "16.5",   status: "idle",    battery: 92, lastRun: "1 sa önce" },
  { id: "ipad",   name: "iPad Pro 12.9",       os: "iOS",     version: "17.4",   status: "offline", battery: 0 },
  { id: "g8",     name: "Pixel 8",             os: "Android", version: "14",     status: "running", battery: 73, lastRun: "şu an" },
  { id: "g7",     name: "Pixel 7",             os: "Android", version: "14",     status: "idle",    battery: 88, lastRun: "8 dk önce" },
  { id: "s24u",   name: "Galaxy S24 Ultra",    os: "Android", version: "14",     status: "queued",  battery: 91 },
  { id: "s23",    name: "Galaxy S23",          os: "Android", version: "13",     status: "idle",    battery: 56 },
  { id: "a54",    name: "Galaxy A54",          os: "Android", version: "13",     status: "running", battery: 45, lastRun: "şu an" },
  { id: "rn12",   name: "Redmi Note 12",       os: "Android", version: "13",     status: "idle",    battery: 100 },
  { id: "pix6",   name: "Pixel 6a",            os: "Android", version: "13",     status: "offline", battery: 0 },
];

const AI_INSIGHTS: AiInsight[] = [
  {
    id: "ins-1",
    type: "flaky",
    title: "3 flaky test tespit edildi",
    description: "Son 14 günde 'Checkout flow' senaryosu iPhone 13 Mini'de %22 fail. Aynı senaryo Pixel 8'de %98 pass. Cihaz-spesifik race condition olabilir.",
    cta: "Detayları gör",
  },
  {
    id: "ins-2",
    type: "slow",
    title: "iPhone SE 3 baseline'dan %34 yavaş",
    description: "Login akışı normalde 1.8s, iPhone SE 3'te 2.4s. Memory pressure veya animasyon işleyiş farkı olabilir.",
    cta: "Performans raporu",
  },
  {
    id: "ins-3",
    type: "suggestion",
    title: "Önerilen 4 yeni mobile senaryo",
    description: "AI, son production crash raporlarını analiz etti. Background → foreground transition'da memory leak testi eksik.",
    cta: "Senaryoları oluştur",
  },
  {
    id: "ins-4",
    type: "warning",
    title: "2 cihaz offline (kritik)",
    description: "Galaxy A14 ve Pixel 6a 4 saattir bağlantısız. Test pipeline'ı etkilenebilir.",
    cta: "Yeniden bağlan",
  },
];

const MODULES = [
  {
    key: "device-matrix",
    title: "Cihaz Matrisi",
    icon: "📱",
    description: "iOS + Android, fiziksel + emülatör. 12 cihaz live. Otomatik dağıtım, paralel koşu.",
    href: "mobile",
    isPrimary: true,
    liveCount: "12 cihaz",
  },
  {
    key: "scenarios",
    title: "Mobile Senaryolar",
    icon: "📝",
    description: "Mobile-first DSL. Touch, swipe, biometric, push notification primitives. Gherkin uyumlu.",
    href: "scenarios",
    liveCount: "247 senaryo",
  },
  {
    key: "recorder",
    title: "Mobile Recorder",
    icon: "🎬",
    description: "Cihazdaki etkileşimleri kaydet → DSL'e çevir. Replay edilebilir, edit edilebilir.",
    href: "recorder",
    liveCount: "32 kayıt",
  },
  {
    key: "visual",
    title: "Visual Diff",
    icon: "👁️",
    description: "Screen-by-screen pixel + semantic diff. Anti-aliasing tolerance, dynamic content masking.",
    href: "visual",
    liveCount: "1.2k baseline",
  },
  {
    key: "runs",
    title: "Test Koşuları",
    icon: "▶️",
    description: "Real-time video, network HAR, console log. Cross-device parallel execution.",
    href: "runs",
    liveCount: "234 bugün",
  },
  {
    key: "reports",
    title: "Raporlar",
    icon: "📊",
    description: "Cihaz başına pass rate, OS version trend, flaky leaderboard. PDF + Slack export.",
    href: "reports",
    liveCount: "47 hafta",
  },
];

// ─── Helper fonksiyonlar ────────────────────────────────────────────────────

function genSparkline(seed: number, length = 7, variance = 5): number[] {
  return Array.from({ length }, (_, i) =>
    Math.max(0, Math.floor(seed * 0.7 + Math.sin(i * 0.8 + seed) * variance + Math.random() * 3))
  );
}

function sanitizeProjectName(name: string): string {
  // SQL injection veya XSS pattern içeren proje adlarını temizle
  if (!name) return "Bilinmeyen Proje";
  if (/['"`]|--|;|<script|drop\s+table/i.test(name)) {
    return "Test Projesi (Güvenlik)";
  }
  return name;
}

// ─── Status renkleri ────────────────────────────────────────────────────────

const STATUS_CLASSES: Record<DeviceStatus, { ring: string; bg: string; dot: string; label: string; text: string }> = {
  running: { ring: "border-emerald-500/40 ring-emerald-500/30", bg: "bg-emerald-500/10", dot: "bg-emerald-400 animate-pulse", label: "Çalışıyor", text: "text-emerald-300" },
  idle:    { ring: "border-slate-700",                          bg: "bg-slate-900",       dot: "bg-slate-500",                 label: "Hazır",      text: "text-slate-400" },
  queued:  { ring: "border-amber-500/30",                       bg: "bg-amber-500/5",     dot: "bg-amber-400",                 label: "Kuyrukta",   text: "text-amber-300" },
  offline: { ring: "border-red-500/30",                         bg: "bg-red-500/5",       dot: "bg-red-500",                   label: "Offline",    text: "text-red-300" },
};

// ─── Ana bileşen ────────────────────────────────────────────────────────────

export function MobileProductPage() {
  const { project, projectId } = useProject();
  const [projects, setProjects] = useState<Project[]>([]);
  const [tick, setTick] = useState(0); // live indicator ticker

  useEffect(() => {
    apiFetch<Project[]>("/api/v1/tspm/projects")
      .then(d => setProjects(Array.isArray(d) ? d : []))
      .catch(() => setProjects([]));
  }, []);

  useEffect(() => {
    const t = setInterval(() => setTick(v => v + 1), 3000);
    return () => clearInterval(t);
  }, []);

  // Device stats
  const stats = useMemo(() => {
    const total = DEVICES.length;
    const running = DEVICES.filter(d => d.status === "running").length;
    const idle = DEVICES.filter(d => d.status === "idle").length;
    const queued = DEVICES.filter(d => d.status === "queued").length;
    const offline = DEVICES.filter(d => d.status === "offline").length;
    const ios = DEVICES.filter(d => d.os === "iOS").length;
    const android = DEVICES.filter(d => d.os === "Android").length;
    return { total, running, idle, queued, offline, ios, android };
  }, []);

  const activeProject = project ?? projects.find(p => p.id === projectId);
  const safeProjectName = activeProject ? sanitizeProjectName(activeProject.name) : null;

  return (
    <div className="flex flex-col gap-8 p-6 pb-12">

      {/* ─── 1. HERO ─────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden rounded-3xl border border-rose-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-rose-950/30 p-8 lg:p-12">
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -right-40 w-96 h-96 bg-gradient-to-br from-rose-500/20 to-pink-500/10 rounded-full blur-3xl" />
          <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-gradient-to-br from-pink-500/10 to-orange-500/10 rounded-full blur-3xl" />
        </div>

        <div className="relative grid gap-8 lg:grid-cols-[1.5fr_1fr] items-center">
          {/* Sol: Başlık + CTA */}
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-xs font-semibold text-rose-300 mb-4">
              <span className="h-1.5 w-1.5 rounded-full bg-rose-400 animate-pulse" />
              MOBİL ORKESTRASYON · BETA
            </div>

            <h1 className="text-3xl lg:text-4xl xl:text-5xl font-bold text-white tracking-tight leading-[1.1] mb-4">
              Cihaz farmınız,{" "}
              <span className="bg-gradient-to-r from-rose-400 via-pink-400 to-orange-400 bg-clip-text text-transparent">
                tek karar yüzeyinde
              </span>
            </h1>

            <p className="text-base lg:text-lg text-slate-300 max-w-xl leading-relaxed mb-6">
              iOS + Android, fiziksel + emülatör, paralel koşu. <strong className="text-white">{stats.total} cihaz</strong>{" "}
              hazır — {stats.running} canlı çalışıyor, {stats.idle} idle. AI flaky test'leri tespit eder, locator'ları onarır,
              cihaz-spesifik regression'ları öngörür.
            </p>

            <div className="flex flex-wrap gap-3">
              <Link
                href={activeProject ? `/p/${activeProject.id}/mobile` : "/portfolio"}
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-rose-500 to-pink-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-rose-500/30 hover:shadow-rose-500/50 transition-all hover:scale-[1.02]"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Mobile Test Başlat
              </Link>

              <Link
                href="/portfolio"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-white/5 px-5 py-3 text-sm font-medium text-slate-200 hover:bg-white/10 transition-colors"
              >
                Tüm Projeler →
              </Link>

              <button
                type="button"
                onClick={() => window.dispatchEvent(new CustomEvent("neurex:open-ai-panel"))}
                className="inline-flex items-center gap-2 rounded-xl border border-violet-500/30 bg-violet-500/10 px-5 py-3 text-sm font-medium text-violet-200 hover:bg-violet-500/20 transition-colors"
                title="AI Mobile asistana sor (Cmd+J)"
              >
                ✨ AI'a Sor
              </button>
            </div>

            {safeProjectName && (
              <p className="mt-4 text-xs text-slate-500">
                Aktif proje: <span className="text-rose-300 font-medium">{safeProjectName}</span>
              </p>
            )}
          </div>

          {/* Sağ: Mini cihaz visualization */}
          <div className="hidden lg:flex flex-col items-center gap-3">
            <div className="grid grid-cols-4 gap-2">
              {DEVICES.slice(0, 12).map((d, i) => {
                const cfg = STATUS_CLASSES[d.status];
                return (
                  <div
                    key={d.id}
                    className={`group flex flex-col items-center justify-center w-14 h-20 rounded-lg border ${cfg.ring} ${cfg.bg} transition-all hover:scale-110`}
                    title={`${d.name} · ${cfg.label}`}
                    style={{ animationDelay: `${i * 50}ms` }}
                  >
                    <span className="text-lg leading-none">{d.os === "iOS" ? "📱" : "🤖"}</span>
                    <span className={`mt-1 h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
                  </div>
                );
              })}
            </div>
            <p className="text-xs text-slate-500">{stats.total} cihaz · {stats.ios} iOS · {stats.android} Android</p>
          </div>
        </div>
      </section>

      {/* ─── 2. LIVE STATS BAR ──────────────────────────────────────────── */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">Canlı Metrikler</h2>
          <span className="text-xs text-slate-600 tabular-nums flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Anlık · son güncelleme: az önce
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <StatCard
            label="Aktif Cihaz"
            value={`${stats.total - stats.offline}/${stats.total}`}
            tone="success"
            sparkline={[10, 11, 12, 12, 11, 12, stats.total - stats.offline]}
            hint={`${stats.offline} offline`}
          />
          <StatCard
            label="Şu an Koşuyor"
            value={stats.running}
            tone="info"
            sparkline={genSparkline(stats.running, 7, 2)}
            trend={+12}
          />
          <StatCard
            label="Kuyrukta"
            value={stats.queued}
            tone="warning"
            hint="ortalama 2dk bekleme"
          />
          <StatCard
            label="Bugün Koşu"
            value={234}
            tone="brand"
            sparkline={[145, 178, 198, 210, 224, 230, 234]}
            trend={+8}
          />
          <StatCard
            label="Pass Rate"
            value="%94"
            tone="success"
            sparkline={[88, 89, 91, 92, 93, 93, 94]}
            trend={+2}
            hint="son 7 gün"
          />
          <StatCard
            label="AI Uyarısı"
            value={AI_INSIGHTS.length}
            tone="ai"
            hint="aksiyon gerek"
          />
        </div>
      </section>

      {/* ─── 3. DEVICE MATRIX + OS DISTRIBUTION ─────────────────────────── */}
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">

        {/* Device Matrix */}
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <span>📱</span> Cihaz Matrisi
                <span className="rounded-full bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 text-[10px] font-semibold text-rose-300">
                  {stats.total} cihaz
                </span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">Live status · 3 saniyede bir güncellenir</p>
            </div>
            <button className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800 transition-colors">
              + Cihaz Ekle
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5">
            {DEVICES.map((d) => {
              const cfg = STATUS_CLASSES[d.status];
              return (
                <div
                  key={d.id}
                  className={`group relative rounded-xl border ${cfg.ring} ${cfg.bg} p-3 transition-all hover:scale-[1.03] hover:border-rose-500/50 cursor-pointer`}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className="text-2xl leading-none">{d.os === "iOS" ? "📱" : "🤖"}</span>
                    <span className={`shrink-0 h-2 w-2 mt-1.5 rounded-full ${cfg.dot}`} />
                  </div>
                  <p className="text-xs font-semibold text-white truncate">{d.name}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5">{d.os} {d.version}</p>
                  <div className="mt-2 flex items-center justify-between text-[10px]">
                    <span className={cfg.text}>{cfg.label}</span>
                    {d.status !== "offline" && (
                      <span className="flex items-center gap-0.5 text-slate-500 tabular-nums">
                        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        {d.battery}%
                      </span>
                    )}
                  </div>
                  {d.lastRun && (
                    <p className="mt-1 text-[9px] text-slate-600 truncate">son: {d.lastRun}</p>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* OS Distribution + Quick Stats */}
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h2 className="text-base font-bold text-white mb-4">OS Dağılımı</h2>

          {/* Donut chart (SVG inline) */}
          <div className="relative flex items-center justify-center mb-5">
            <svg viewBox="0 0 100 100" className="h-32 w-32 -rotate-90">
              <circle cx="50" cy="50" r="40" stroke="#1e293b" strokeWidth="14" fill="none" />
              <circle
                cx="50" cy="50" r="40"
                stroke="#fb7185" strokeWidth="14" fill="none"
                strokeDasharray={`${(stats.ios / stats.total) * 251.3} 251.3`}
                strokeLinecap="round"
              />
              <circle
                cx="50" cy="50" r="40"
                stroke="#34d399" strokeWidth="14" fill="none"
                strokeDasharray={`${(stats.android / stats.total) * 251.3} 251.3`}
                strokeDashoffset={`-${(stats.ios / stats.total) * 251.3}`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-bold text-white tabular-nums">{stats.total}</span>
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">Toplam</span>
            </div>
          </div>

          <div className="space-y-2.5">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-sm bg-rose-400" />
                <span className="text-slate-200">iOS</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-white tabular-nums font-semibold">{stats.ios}</span>
                <span className="text-xs text-slate-500 tabular-nums">%{Math.round((stats.ios / stats.total) * 100)}</span>
              </div>
            </div>
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-sm bg-emerald-400" />
                <span className="text-slate-200">Android</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-white tabular-nums font-semibold">{stats.android}</span>
                <span className="text-xs text-slate-500 tabular-nums">%{Math.round((stats.android / stats.total) * 100)}</span>
              </div>
            </div>
          </div>

          <hr className="border-slate-800 my-5" />

          {/* Run timeline mini */}
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Son 7 gün koşu</h3>
          <Sparkline
            data={[145, 178, 198, 210, 224, 230, 234]}
            variant="area"
            width={220}
            height={40}
            className="text-rose-400 w-full"
          />
          <div className="mt-1 flex justify-between text-[10px] text-slate-600 tabular-nums">
            <span>1.5k</span>
            <span>Toplam: 1,419 koşu</span>
          </div>
        </section>
      </div>

      {/* ─── 4. MODÜLLER ────────────────────────────────────────────────── */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white">Mobile Modülleri</h2>
            <p className="text-xs text-slate-500 mt-0.5">Ekosistemin tüm parçaları, tek yerde</p>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {MODULES.map((m) => (
            <Link
              key={m.key}
              href={activeProject ? `/p/${activeProject.id}/${m.href}` : "/portfolio"}
              className={`group relative rounded-xl border bg-slate-900/60 p-4 transition-all hover:scale-[1.02] ${
                m.isPrimary
                  ? "border-rose-500/40 hover:border-rose-500"
                  : "border-slate-800 hover:border-slate-600"
              }`}
            >
              {m.isPrimary && (
                <span className="absolute -top-2 right-3 rounded-full bg-rose-500 px-2 py-0.5 text-[9px] font-bold text-white shadow-md">
                  İLK DURAK
                </span>
              )}
              <div className="flex items-start gap-3 mb-3">
                <span className="text-2xl leading-none">{m.icon}</span>
                <div className="min-w-0 flex-1">
                  <h3 className={`text-sm font-bold ${m.isPrimary ? "text-rose-300" : "text-white"} group-hover:text-rose-300 transition-colors`}>
                    {m.title}
                  </h3>
                  <p className="text-[10px] text-slate-600 mt-0.5 tabular-nums">{m.liveCount}</p>
                </div>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">{m.description}</p>
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-rose-400 font-medium group-hover:underline">Aç →</span>
                <svg className="h-4 w-4 text-slate-600 group-hover:text-rose-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ─── 5. AI INSIGHTS ─────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-violet-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-violet-950/20 p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-pink-500 text-lg">
              ✨
            </div>
            <div>
              <h2 className="text-base font-bold text-white">AI Mobile Insights</h2>
              <p className="text-xs text-slate-500">Bağlama özel öneriler · {AI_INSIGHTS.length} aktif uyarı</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => window.dispatchEvent(new CustomEvent("neurex:open-ai-panel"))}
            className="rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-1.5 text-xs font-medium text-violet-200 hover:bg-violet-500/20 transition-colors"
          >
            Sohbete Aç
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {AI_INSIGHTS.map((ins) => {
            const cfg = {
              flaky:      { icon: "⚠️", color: "amber-400",    border: "border-amber-500/30 bg-amber-500/5" },
              slow:       { icon: "🐢", color: "orange-400",   border: "border-orange-500/30 bg-orange-500/5" },
              suggestion: { icon: "💡", color: "violet-400",   border: "border-violet-500/30 bg-violet-500/5" },
              warning:    { icon: "🔴", color: "red-400",      border: "border-red-500/30 bg-red-500/5" },
            }[ins.type];

            return (
              <div key={ins.id} className={`rounded-xl border p-4 ${cfg.border} transition-all hover:scale-[1.01]`}>
                <div className="flex items-start gap-2.5 mb-2">
                  <span className="text-lg leading-none">{cfg.icon}</span>
                  <h3 className="text-sm font-semibold text-white flex-1">{ins.title}</h3>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed mb-3">{ins.description}</p>
                {ins.cta && (
                  <button className={`text-xs font-medium text-${cfg.color} hover:underline`}>
                    {ins.cta} →
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* ─── 6. RECENT ACTIVITY + PROJECTS ──────────────────────────────── */}
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">

        {/* Recent Activity Feed */}
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Canlı Aktivite
          </h2>
          <div className="space-y-3">
            {[
              { actor: "Yasin B.", action: "iPhone 15 Pro'da Checkout senaryosu çalıştırdı", time: "az önce", status: "running" },
              { actor: "Ayşe K.",  action: "Pixel 8 için yeni baseline güncelledi", time: "2 dk", status: "passed" },
              { actor: "AI",       action: "Galaxy S24 Ultra'da flaky test tespit etti", time: "8 dk", status: "warning" },
              { actor: "Mehmet D.",action: "23 cihazda parallel regression suite başlattı", time: "14 dk", status: "running" },
              { actor: "Ayşe K.",  action: "iPad Pro 12.9 offline duruma geçti", time: "22 dk", status: "failed" },
              { actor: "Yasin B.", action: "Mobile DSL kataloğuna 4 yeni step ekledi", time: "1 sa", status: "passed" },
            ].map((act, i) => {
              const cfgColor =
                act.status === "running" ? "bg-blue-400 animate-pulse" :
                act.status === "passed"  ? "bg-emerald-400" :
                act.status === "warning" ? "bg-amber-400" :
                                           "bg-red-400";
              return (
                <div key={i} className="flex items-start gap-3 group">
                  <div className="flex flex-col items-center pt-0.5">
                    <Avatar
                      name={act.actor}
                      size="sm"
                      shape="circle"
                      seed={act.actor}
                    />
                    {i < 5 && <div className="w-px flex-1 bg-slate-800 mt-1 -mb-3" />}
                  </div>
                  <div className="min-w-0 flex-1 pb-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-white">{act.actor}</span>
                      <span className={`h-1.5 w-1.5 rounded-full ${cfgColor}`} />
                      <span className="text-xs text-slate-500">{act.time}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{act.action}</p>
                  </div>
                </div>
              );
            })}
          </div>
          <button className="mt-4 w-full text-center text-xs text-slate-500 hover:text-rose-300 transition-colors">
            Tüm aktiviteyi gör →
          </button>
        </section>

        {/* Suggested Projects */}
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h2 className="text-base font-bold text-white mb-1">Önerilen Projeler</h2>
          <p className="text-xs text-slate-500 mb-4">Mobile odaklı projeler</p>

          <div className="space-y-2">
            {projects.slice(0, 5).map((p) => {
              const safe = sanitizeProjectName(p.name);
              return (
                <Link
                  key={p.id}
                  href={`/p/${p.id}/mobile`}
                  className="group flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900 p-3 hover:border-rose-500/40 hover:bg-slate-800/60 transition-all"
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-rose-500 to-pink-600 text-xs font-bold text-white shadow-md">
                    {safe.split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-white truncate group-hover:text-rose-300 transition-colors">{safe}</p>
                    <p className="text-[10px] text-slate-500 truncate">{p.description || "Mobile testleri için yapılandırılmaya hazır"}</p>
                  </div>
                  <svg className="h-3.5 w-3.5 shrink-0 text-slate-600 group-hover:text-rose-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              );
            })}
            {projects.length === 0 && (
              <div className="text-center py-6">
                <p className="text-xs text-slate-500">Proje yükleniyor...</p>
              </div>
            )}
          </div>

          <Link
            href="/portfolio"
            className="mt-4 inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/5 py-2 text-xs font-medium text-rose-300 hover:bg-rose-500/15 transition-colors"
          >
            Tüm Projeleri Gör ({projects.length})
          </Link>
        </section>
      </div>

      {/* ─── 7. GET STARTED ─────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="mb-5 flex items-start justify-between">
          <div>
            <h2 className="text-base font-bold text-white">Hızlı Başlangıç</h2>
            <p className="text-xs text-slate-500 mt-0.5">3 adımda mobile testlerinizi çalıştırın</p>
          </div>
          <span className="text-xs text-slate-500">5 dk</span>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {[
            { step: 1, title: "Proje seç veya oluştur", desc: "Mevcut bir projeyi aç ya da yeni mobile odaklı proje başlat", action: "Projeleri gör", href: "/portfolio" },
            { step: 2, title: "Cihazları doğrula", desc: "12 cihaz hazır. Listeden kontrol et, offline olanları yeniden bağla", action: "Matrise git", href: activeProject ? `/p/${activeProject.id}/mobile` : "/portfolio" },
            { step: 3, title: "İlk senaryoyu çalıştır", desc: "Hazır şablonlardan seç veya AI ile yeni senaryo oluştur", action: "Senaryolar", href: activeProject ? `/p/${activeProject.id}/scenarios` : "/task-drafts" },
          ].map((s) => (
            <div key={s.step} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-rose-500/20 border border-rose-500/40 text-[10px] font-bold text-rose-300">
                  {s.step}
                </span>
                <h3 className="text-sm font-semibold text-white">{s.title}</h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed mb-3">{s.desc}</p>
              <Link
                href={s.href}
                className="text-xs font-medium text-rose-300 hover:text-rose-200 hover:underline"
              >
                {s.action} →
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* ─── Footer / Back ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between pt-4">
        <Link
          href="/portfolio"
          className="text-xs text-slate-500 hover:text-rose-300 transition-colors flex items-center gap-1.5"
        >
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Tüm Ürünler
        </Link>
        <p className="text-xs text-slate-600">
          Neurex Mobile <span className="text-rose-400">·</span> {stats.total} cihaz live <span className="text-rose-400">·</span> {stats.running} çalışıyor şu an
        </p>
      </div>

    </div>
  );
}
