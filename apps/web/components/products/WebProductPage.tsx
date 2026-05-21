"use client";

import { useState } from "react";
import Link from "next/link";
import { useProjects } from "@/lib/hooks/use-projects";
import { useProductTelemetry } from "@/lib/products/useProductTelemetry";
import type { BrowserStat } from "@/lib/products/telemetry-types";
import { DEMO_TELEMETRY } from "@/lib/products/demo-data";
import { PRODUCT_BRAND } from "@/lib/products/brand";
import { useProject } from "@/lib/useProject";
import { LiveStatsBar } from "./_shared/LiveStatsBar";
import { AiInsightFeed } from "./_shared/AiInsightFeed";
import { RecentActivity } from "./_shared/RecentActivity";
import { OnboardingChecklist } from "./_shared/OnboardingChecklist";
import { ConversationalTestCreator } from "./web/ConversationalTestCreator";
import { TimeTravelReplay } from "./web/TimeTravelReplay";
import { BrowserExtensionStatus } from "./web/BrowserExtensionStatus";
import { RecorderStudio } from "./web/RecorderStudio";
import { AuthStateManager } from "./web/AuthStateManager";
import { NetworkConsoleInspector } from "./web/NetworkConsoleInspector";
import { ReleaseHealthBanner } from "./web/ReleaseHealthBanner";
import { TodayVsYesterdayStrip } from "./web/TodayVsYesterdayStrip";
import { MyInbox } from "./web/MyInbox";
import { LiveRunsPanel } from "./web/LiveRunsPanel";
import { PerfPanel } from "./web/PerfPanel";

const brand = PRODUCT_BRAND.web;
const ZERO_STATE_TELEMETRY = DEMO_TELEMETRY.web;

// ─── Browser Cockpit ──────────────────────────────────────────────────────

function BrowserCockpit({ browsers }: { browsers: BrowserStat[] }) {
  if (!browsers.length) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 text-center text-sm text-slate-400">
        Browser metrikleri henüz yok. İlk koşudan sonra burada görünür.
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      {browsers.map((b) => (
        <div key={b.name} className={`rounded-xl border p-3 hover:bg-slate-800/60 transition-colors cursor-pointer ${b.status === "passing" ? "bg-slate-900/60 border-slate-800" : "bg-amber-500/6 border-amber-500/20"}`}>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">{b.icon}</span>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-white truncate">{b.name}</p>
              <p className="text-xs text-slate-400">v{b.version}</p>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className={`text-lg font-bold tabular-nums ${b.passRate >= 95 ? "text-emerald-400" : b.passRate >= 88 ? "text-amber-400" : "text-rose-400"}`}>
              {b.passRate}%
            </span>
            <span className="text-xs text-slate-400">{b.runs} koşu</span>
          </div>
          <div className="mt-2 h-1 rounded-full bg-white/10 overflow-hidden">
            <div className={`h-full rounded-full ${b.passRate >= 95 ? "bg-emerald-500" : b.passRate >= 88 ? "bg-amber-400" : "bg-rose-500"}`}
              style={{ width: `${b.passRate}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Visual Regression Wall ───────────────────────────────────────────────

const VISUAL_DIFFS = [
  { page: "Homepage",       status: "changed", severity: "critical", diff: 12.4, baseline: "v2.4.0", current: "v2.5.0" },
  { page: "Checkout Step 2", status: "changed", severity: "major",  diff: 7.8,  baseline: "v2.4.0", current: "v2.5.0" },
  { page: "Login Page",      status: "passed",  severity: "none",   diff: 0,    baseline: "v2.4.0", current: "v2.5.0" },
  { page: "Product Card",    status: "changed", severity: "minor",  diff: 2.1,  baseline: "v2.4.0", current: "v2.5.0" },
  { page: "Cart Drawer",     status: "passed",  severity: "none",   diff: 0,    baseline: "v2.4.0", current: "v2.5.0" },
  { page: "Profile Page",    status: "changed", severity: "major",  diff: 5.3,  baseline: "v2.4.0", current: "v2.5.0" },
];

const SEV = {
  critical: "border-rose-500/40 bg-rose-500/8",
  major:    "border-amber-500/35 bg-amber-500/8",
  minor:    "border-sky-500/30 bg-sky-500/6",
  none:     "border-emerald-500/25 bg-emerald-500/6",
};

function VisualRegressionWall() {
  const [approved, setApproved] = useState<Set<string>>(new Set());

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      {VISUAL_DIFFS.map((item) => {
        const isApproved = approved.has(item.page);
        return (
          <div key={item.page} className={`rounded-xl border p-3 ${SEV[isApproved ? "none" : item.severity as keyof typeof SEV]}`}>
            {/* Fake screenshot placeholder */}
            <div className={`w-full aspect-video rounded-lg mb-2 flex items-center justify-center text-xs font-mono text-slate-400 ${item.status === "passed" || isApproved ? "bg-emerald-500/10" : "bg-slate-800/60"}`}>
              {item.status === "changed" && !isApproved ? (
                <span className="text-amber-400">Δ {item.diff}%</span>
              ) : (
                <span className="text-emerald-400">✓ Pass</span>
              )}
            </div>
            <p className="text-xs font-medium text-white truncate">{item.page}</p>
            <div className="flex items-center justify-between mt-1">
              <span className="text-xs text-slate-400">{item.baseline} → {item.current}</span>
              {item.status === "changed" && !isApproved && (
                <button
                  className="text-xs text-emerald-400 hover:underline"
                  onClick={() => setApproved((prev) => new Set(prev).add(item.page))}
                >
                  Onayla
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Locator Health ───────────────────────────────────────────────────────

const LOCATOR_CATEGORIES = [
  { name: "data-testid",  count: 923,  pct: 50, color: "#10b981", health: "excellent" },
  { name: "aria-label",   count: 412,  pct: 22, color: "#34d399", health: "good" },
  { name: "CSS selector", count: 287,  pct: 16, color: "#f59e0b", health: "fair" },
  { name: "XPath",        count: 124,  pct: 7,  color: "#f97316", health: "poor" },
  { name: "text()",       count: 101,  pct: 5,  color: "#ef4444", health: "critical" },
];

function LocatorHealth() {
  return (
    <div className="space-y-3">
      <div className="flex h-3 rounded-full overflow-hidden gap-px">
        {LOCATOR_CATEGORIES.map((cat) => (
          <div key={cat.name} style={{ width: `${cat.pct}%`, backgroundColor: cat.color }} title={`${cat.name}: ${cat.count}`} />
        ))}
      </div>
      <div className="space-y-2">
        {LOCATOR_CATEGORIES.map((cat) => (
          <div key={cat.name} className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: cat.color }} />
            <span className="text-xs text-white flex-1 font-mono">{cat.name}</span>
            <span className="text-xs text-slate-400">{cat.count}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
              cat.health === "excellent" ? "text-emerald-300 bg-emerald-500/15" :
              cat.health === "good"      ? "text-emerald-300 bg-emerald-500/10" :
              cat.health === "fair"      ? "text-amber-300  bg-amber-500/15" :
              cat.health === "poor"      ? "text-orange-300 bg-orange-500/15" :
              "text-rose-300 bg-rose-500/15"
            }`}>{cat.health}</span>
          </div>
        ))}
      </div>
      <button className="w-full text-center text-xs text-emerald-400 hover:underline mt-1">
        124 XPath locator'ı otomatik dönüştür →
      </button>
    </div>
  );
}

// ─── A11y Summary ─────────────────────────────────────────────────────────

const A11Y_ISSUES = [
  { rule: "color-contrast",      level: "AA", count: 6, severity: "critical" },
  { rule: "label-missing",       level: "A",  count: 4, severity: "critical" },
  { rule: "button-name",         level: "A",  count: 2, severity: "warning" },
  { rule: "img-alt",             level: "A",  count: 2, severity: "warning" },
];

function A11ySummary() {
  return (
    <div className="space-y-2.5">
      <div className="flex items-center gap-3 mb-3">
        <div className="flex-1">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-slate-400">WCAG 2.1 Uyum</span>
            <span className="text-amber-400 font-semibold">%72</span>
          </div>
          <div className="h-2 rounded-full bg-white/10 overflow-hidden">
            <div className="h-full rounded-full bg-gradient-to-r from-amber-500 to-yellow-400" style={{ width: "72%" }} />
          </div>
        </div>
        <span className="text-3xl font-bold text-amber-400 tabular-nums">14</span>
      </div>
      {A11Y_ISSUES.map((issue) => (
        <div key={issue.rule} className="flex items-center gap-3">
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${issue.severity === "critical" ? "bg-rose-500" : "bg-amber-400"}`} />
          <span className="text-xs font-mono text-white flex-1">{issue.rule}</span>
          <span className="text-xs text-slate-400 px-1.5 py-0.5 rounded bg-slate-800/60">{issue.level}</span>
          <span className={`text-xs font-bold ${issue.severity === "critical" ? "text-rose-400" : "text-amber-400"}`}>{issue.count}</span>
        </div>
      ))}
      <button className="w-full text-center text-xs text-emerald-400 hover:underline mt-1">
        Tam erişilebilirlik raporu →
      </button>
    </div>
  );
}

function formatProjectRecency(iso?: string) {
  if (!iso) return "Guncellenme tarihi yok";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${Math.max(1, mins)} dk once guncellendi`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} sa once guncellendi`;
  const days = Math.floor(hrs / 24);
  return `${days} gun once guncellendi`;
}

function WebProjectZeroState() {
  const { setProject } = useProject();
  const { data: projects, isLoading, error } = useProjects();
  const topProjects = [...(projects ?? [])]
    .sort((a, b) => {
      const aTs = new Date(a.updated_at ?? a.created_at ?? 0).getTime();
      const bTs = new Date(b.updated_at ?? b.created_at ?? 0).getTime();
      return bTs - aTs;
    })
    .slice(0, 4);

  const firstPendingStep = ZERO_STATE_TELEMETRY.onboarding.find((step) => !step.done);

  return (
    <div className="flex flex-col gap-6 p-6 pb-12">
      <section className="rounded-[28px] border border-emerald-500/15 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.16),transparent_38%),linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98))] p-6 shadow-[0_32px_120px_rgba(5,150,105,0.12)] lg:p-7">
        <div className="grid gap-6 xl:grid-cols-[1.35fr_0.95fr]">
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.24em] ${brand.badge}`}>
                Web
              </span>
              <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-200">
                Web kalite operasyon merkezi
              </span>
              <span className="rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-1 text-[11px] font-medium text-amber-200">
                Demo onizleme acik
              </span>
            </div>

            <div className="space-y-3">
              <h1 className="max-w-3xl text-3xl font-semibold leading-tight text-white sm:text-[2.2rem]">
                Proje secilmeden bile ne kazanacagini gosteren daha net bir baslangic ekrani.
              </h1>
              <p className="max-w-2xl text-sm leading-6 text-slate-300 sm:text-[15px]">
                Bu ekran secili proje ile canli dashboard'a donusur. Senin icin once
                browser matrix, visual diff, flaky test ve locator sagligi gibi sinyalleri
                tek yerde toplar.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/55 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Visual queue
                </p>
                <p className="mt-2 text-lg font-semibold text-white">Kritik diff'leri ayikla</p>
                <p className="mt-1 text-sm text-slate-400">
                  Checkout, auth ve temel landing akislari tek panoda takip edilir.
                </p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/55 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Locator debt
                </p>
                <p className="mt-2 text-lg font-semibold text-white">Kirilgan secicileri temizle</p>
                <p className="mt-1 text-sm text-slate-400">
                  XPath ve text() kullanimlarini daha stabil data-testid akislariyla degistir.
                </p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/55 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Release radar
                </p>
                <p className="mt-2 text-lg font-semibold text-white">Ship karari icin hizli ozet</p>
                <p className="mt-1 text-sm text-slate-400">
                  Pass rate, a11y blocker ve performans sinyalleri yayin oncesi ayni yerde.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link
                href="/new-project"
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 transition-opacity hover:opacity-90"
              >
                Yeni web projesi olustur
              </Link>
              <Link
                href="/portfolio"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-slate-800"
              >
                Tum projeleri gor
              </Link>
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-800 bg-slate-950/65 p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Hemen basla
                </p>
                <h2 className="mt-2 text-xl font-semibold text-white">Bir proje sec ve dashboard'u ac</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Secimden sonra run listesi, browser cockpit, visual wall ve AI onerileri
                  ayni sayfada canli veriye doner.
                </p>
              </div>
              <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-200">
                1 adim
              </div>
            </div>

            <div className="mt-5 space-y-3">
              {isLoading ? (
                <div className="space-y-3">
                  <div className="h-12 animate-pulse rounded-xl border border-slate-800 bg-slate-900/70" />
                  <div className="grid gap-2">
                    {Array.from({ length: 3 }).map((_, index) => (
                      <div key={index} className="h-16 animate-pulse rounded-xl border border-slate-800 bg-slate-900/60" />
                    ))}
                  </div>
                  <p className="text-sm text-slate-400">Projeler yukleniyor. Son acilanlari hazirliyoruz.</p>
                </div>
              ) : error ? (
                <div className="rounded-2xl border border-rose-500/25 bg-rose-500/10 p-4">
                  <p className="text-sm font-semibold text-rose-200">Projeler su anda alinamadi.</p>
                  <p className="mt-1 text-sm leading-6 text-rose-100/80">
                    Yine de yeni proje olusturabilir veya birazdan tekrar deneyebilirsin.
                  </p>
                  <Link
                    href="/new-project"
                    className="mt-4 inline-flex items-center gap-2 rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm font-medium text-rose-100 transition-colors hover:bg-rose-500/20"
                  >
                    Yeni proje olustur
                  </Link>
                </div>
              ) : !projects || projects.length === 0 ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-900/75 p-4">
                  <p className="text-sm font-semibold text-white">Henuz web projen yok.</p>
                  <p className="mt-1 text-sm leading-6 text-slate-400">
                    Ilk projeni olusturdugunda bu ekran otomatik olarak run, flaky, visual
                    ve locator sinyallerine acilacak.
                  </p>
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    <Link
                      href="/new-project"
                      className="inline-flex items-center justify-center rounded-lg bg-emerald-500 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-400"
                    >
                      Ilk projeyi olustur
                    </Link>
                    <Link
                      href="/portfolio"
                      className="inline-flex items-center justify-center rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-900"
                    >
                      Portfolio'ya git
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <label className="block text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                    Tum projeler
                  </label>
                  <select
                    defaultValue=""
                    onChange={(e) => {
                      const selected = projects.find((item) => item.id === e.target.value);
                      if (selected) setProject({ id: selected.id, name: selected.name });
                    }}
                    className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-3 text-sm text-white focus:border-emerald-500/50 focus:outline-none"
                  >
                    <option value="" disabled>
                      Hedef proje sec...
                    </option>
                    {projects.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>

                  <div className="grid gap-2">
                    {topProjects.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => setProject({ id: item.id, name: item.name })}
                        className="rounded-xl border border-slate-800 bg-slate-900/75 px-4 py-3 text-left transition-colors hover:border-emerald-500/30 hover:bg-slate-900"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-white">{item.name}</p>
                            <p className="mt-1 text-xs text-slate-400 line-clamp-2">
                              {item.description?.trim() || "Web kalite panelini bu proje icin dogrudan ac."}
                            </p>
                          </div>
                          <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-200">
                            Ac
                          </span>
                        </div>
                        <p className="mt-2 text-[11px] text-slate-500">
                          {formatProjectRecency(item.updated_at ?? item.created_at)}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-900/55 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Secince ilk acilacaklar
              </p>
              <div className="mt-3 grid gap-2 text-sm text-slate-300">
                <div className="flex items-start gap-2">
                  <span className="mt-0.5 text-emerald-300">1.</span>
                  <span>Canli release health ve bugun vs dun karsilastirmasi</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="mt-0.5 text-emerald-300">2.</span>
                  <span>Visual diff, flaky test ve browser matrix sinyalleri</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="mt-0.5 text-emerald-300">3.</span>
                  <span>AI onceliklendirme, locator debt ve a11y radar</span>
                </div>
              </div>
              {firstPendingStep && (
                <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-200">
                    Onerilen ilk adim
                  </p>
                  <p className="mt-1 text-sm font-medium text-white">{firstPendingStep.title}</p>
                  <p className="mt-1 text-sm leading-6 text-amber-100/80">
                    {firstPendingStep.description}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <LiveStatsBar stats={ZERO_STATE_TELEMETRY.stats} />

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Browser cockpit onizleme
                </p>
                <h2 className="mt-1 text-lg font-semibold text-white">
                  Hangi tarayicida risk buyuyor, ilk ekranda gor
                </h2>
              </div>
              <span className="rounded-full border border-slate-700 bg-slate-950 px-2.5 py-1 text-[11px] text-slate-300">
                Ornek veri
              </span>
            </div>
            <BrowserCockpit browsers={ZERO_STATE_TELEMETRY.browsers ?? []} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
              <div className="mb-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Visual regression
                </p>
                <h2 className="mt-1 text-lg font-semibold text-white">
                  Kritik diff'leri onay kuyruğunda topla
                </h2>
              </div>
              <VisualRegressionWall />
            </div>

            <div className="space-y-6">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                <div className="mb-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                    Locator health
                  </p>
                  <h2 className="mt-1 text-lg font-semibold text-white">
                    Kirilgan secicileri toplu olarak gor
                  </h2>
                </div>
                <LocatorHealth />
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                <div className="mb-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                    Accessibility radar
                  </p>
                  <h2 className="mt-1 text-lg font-semibold text-white">
                    Yayin oncesi a11y blocker'lari erken yakala
                  </h2>
                </div>
                <A11ySummary />
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                AI insight feed
              </p>
              <h2 className="mt-1 text-lg font-semibold text-white">
                Son deploy sonrasi en onemli sinyalleri ozetle
              </h2>
            </div>
            <AiInsightFeed insights={ZERO_STATE_TELEMETRY.aiInsights} brandBorder={brand.border} brandText={brand.text} />
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Recent activity
              </p>
              <h2 className="mt-1 text-lg font-semibold text-white">
                Takim ve bot'lar son olarak ne yapti
              </h2>
            </div>
            <RecentActivity events={ZERO_STATE_TELEMETRY.recentActivity} brandText={brand.text} />
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Ilk kurulum
              </p>
              <h2 className="mt-1 text-lg font-semibold text-white">
                Secimden sonra seni bekleyen hizli akisi gor
              </h2>
            </div>
            <OnboardingChecklist
              steps={ZERO_STATE_TELEMETRY.onboarding}
              brandGradient={brand.gradient}
              brandText={brand.text}
            />
          </div>
        </div>
      </section>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────

export function WebProductPage() {
  const { telemetry, loading, isDemo } = useProductTelemetry("web");
  const { project, projectId } = useProject();

  if (!projectId) return <WebProjectZeroState />;

  return (
    <div className="flex flex-col gap-6 p-6 pb-12">
      {/* ── Release Sağlığı (en üstte, karar bantı) ─── */}
      <ReleaseHealthBanner />

      {/* ── Slim Hero: proje + CTA'lar ───────────────── */}
      <section className="relative rounded-2xl border border-slate-800 bg-slate-900/60 px-5 py-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-lg shrink-0">📁</div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ${brand.badge}`}>
                  Web
                </span>
                {isDemo && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25">
                    Demo Data
                  </span>
                )}
                <span className="text-[11px] text-slate-500">Aktif proje</span>
              </div>
              <p className="text-base font-semibold text-white truncate">{project?.name ?? "—"}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href={projectId ? `/p/${projectId}/runs` : "/portfolio"}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-semibold text-sm hover:opacity-90 shadow-lg shadow-emerald-500/20"
            >
              Koşuya Başla →
            </Link>
            <Link
              href={projectId ? `/p/${projectId}/recorder` : "/portfolio"}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 text-white border border-slate-700 font-medium text-sm hover:bg-slate-700"
            >
              Recorder
            </Link>
          </div>
        </div>
      </section>

      {/* ── Bugün vs Dün delta şeridi ───────────────── */}
      <TodayVsYesterdayStrip />

      {/* ── My Inbox (sana atanmış işler) ───────────── */}
      <MyInbox />

      {/* ── Şu an koşuyor + son fail ─────────────── */}
      <LiveRunsPanel />

      {/* ── Performance / Core Web Vitals ───────── */}
      <div id="perf">
        <PerfPanel />
      </div>

      {/* ── Browser Matrisi ─────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest">🌐 Browser Matrisi</p>
            <p className="text-xs text-slate-500 mt-0.5">Tarayıcı bazında pass rate ve koşu hacmi</p>
          </div>
          {isDemo && (
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25">
              Demo veri
            </span>
          )}
        </div>
        <BrowserCockpit browsers={telemetry?.browsers ?? []} />
      </section>

      {/* ── QA Cockpit (Konuşan Test + Time-Travel + Eklenti) ── */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-xs font-semibold text-emerald-400 uppercase tracking-widest">⚡ QA Cockpit</p>
            <p className="text-xs text-slate-500 mt-0.5">Konuşan test yazarı · Time-travel replay · Tarayıcı eklentisi — tek panelde</p>
          </div>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-gradient-to-r from-emerald-500/15 to-teal-500/15 text-emerald-300 border border-emerald-500/25">
            Yeni nesil
          </span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <ConversationalTestCreator />
          <TimeTravelReplay />
          <BrowserExtensionStatus />
        </div>
      </section>

      {/* ── Run Diagnostics (Auth State + Network/Console) ── */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-xs font-semibold text-indigo-400 uppercase tracking-widest">🩺 Run Diagnostics</p>
            <p className="text-xs text-slate-500 mt-0.5">Auth state reuse · Network &amp; console inspector — fail neden kırıldı?</p>
          </div>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/25">
            Yeni
          </span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <AuthStateManager />
          <NetworkConsoleInspector />
        </div>
      </section>

      {/* ── Recorder Studio (full width) ─────────── */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-xs font-semibold text-rose-400 uppercase tracking-widest">🎙️ Recorder Studio</p>
            <p className="text-xs text-slate-500 mt-0.5">Kayıtlı oturumları Playwright / Cucumber / POM koduna dönüştür</p>
          </div>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/25">
            Engine bağlı
          </span>
        </div>
        <RecorderStudio />
      </section>

      {/* ── Stats ──────────────────────────────────── */}
      <section>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Web Metrikleri</p>
        <LiveStatsBar stats={telemetry?.stats ?? []} loading={loading} brandText={brand.text} />
      </section>

      {/* ── Visual Regression Wall ──────────────────── */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-semibold text-white">Görsel Regresyon Duvarı</h2>
          <span className="text-xs text-slate-400">4 değişiklik · 2 onaylandı bekleniyor</span>
        </div>
        <VisualRegressionWall />
      </div>

      {/* ── Locator + A11y + Insights ─────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Locator Sağlığı</h2>
            <span className="text-xs text-slate-400">1847 toplam</span>
          </div>
          <LocatorHealth />
        </div>

        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Erişilebilirlik</h2>
            <span className="text-xs text-slate-400">14 ihlal</span>
          </div>
          <A11ySummary />
        </div>

        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-white mb-5">AI Öngörüleri</h2>
          <AiInsightFeed insights={telemetry?.aiInsights ?? []} brandBorder={brand.border} brandText={brand.text} loading={loading} />
        </div>
      </div>

      {/* ── Activity + Onboarding ──────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-white mb-5">Son Aktiviteler</h2>
          <RecentActivity events={telemetry?.recentActivity ?? []} brandText={brand.text} loading={loading} />
        </div>
        <OnboardingChecklist steps={telemetry?.onboarding ?? []} brandGradient={brand.gradient} brandText={brand.text} loading={loading} />
      </div>
    </div>
  );
}
