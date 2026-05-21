"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useProductTelemetry } from "@/lib/products/useProductTelemetry";
import { PRODUCT_BRAND } from "@/lib/products/brand";
import { LiveStatsBar } from "./_shared/LiveStatsBar";
import { AiInsightFeed } from "./_shared/AiInsightFeed";
import { RecentActivity } from "./_shared/RecentActivity";
import { OnboardingChecklist } from "./_shared/OnboardingChecklist";

const brand = PRODUCT_BRAND["nexus-code"];

// ─── Analyzer Console ─────────────────────────────────────────────────────

const CONSOLE_LINES = [
  { t: 0,    text: "$ neurex-code analyze https://checkout.example.com/payment",  color: "text-cyan-400" },
  { t: 400,  text: "→ Fetching DOM structure...",                                  color: "text-slate-400" },
  { t: 800,  text: "→ Analyzing 847 DOM elements",                                color: "text-slate-400" },
  { t: 1200, text: "→ Mapping 23 user interaction flows",                         color: "text-slate-400" },
  { t: 1600, text: "→ Scanning for PII exposure in URL params...",                color: "text-amber-400" },
  { t: 2000, text: "⚠ Found: email in query string (?user=test@mail.com)",        color: "text-rose-400" },
  { t: 2400, text: "→ Generating test scenarios with Ollama llama3...",           color: "text-slate-400" },
  { t: 2800, text: "✓ Generated 34 test scenarios",                               color: "text-emerald-400" },
  { t: 3200, text: "✓ Identified 12 bug risk areas",                              color: "text-emerald-400" },
  { t: 3600, text: "→ Analysis complete. Quality score: 67/100",                  color: "text-cyan-400" },
];

function AnalyzerConsole() {
  const [visibleLines, setVisibleLines] = useState<number>(0);

  useEffect(() => {
    setVisibleLines(0);
    const timers = CONSOLE_LINES.map((line, i) =>
      setTimeout(() => setVisibleLines(i + 1), line.t)
    );
    // Loop after 5s
    const resetTimer = setTimeout(() => setVisibleLines(0), 5000);
    return () => {
      timers.forEach(clearTimeout);
      clearTimeout(resetTimer);
    };
  }, []);

  // Re-run animation on loop
  useEffect(() => {
    if (visibleLines === 0 && visibleLines !== undefined) {
      const timers = CONSOLE_LINES.map((line, i) =>
        setTimeout(() => setVisibleLines(i + 1), line.t)
      );
      return () => timers.forEach(clearTimeout);
    }
  }, [visibleLines]);

  return (
    <div className="font-mono text-xs bg-[#080a0f] rounded-xl border border-slate-800 p-4 h-52 overflow-y-auto">
      {CONSOLE_LINES.slice(0, visibleLines).map((line, i) => (
        <div key={i} className={`leading-relaxed ${line.color}`}>
          {line.text}
          {i === visibleLines - 1 && (
            <span className="inline-block w-1.5 h-3.5 bg-cyan-400 ml-1 animate-pulse align-middle" />
          )}
        </div>
      ))}
    </div>
  );
}

// ─── Analysis Timeline ────────────────────────────────────────────────────

const ANALYSES = [
  { url: "checkout.example.com/payment", type: "URL",  scenarios: 34, bugs: 12, privacy: 2, score: 67, time: "2 dk önce" },
  { url: "github.com/my-app/src/cart",   type: "Repo", scenarios: 28, bugs: 6,  privacy: 0, score: 81, time: "1 sa önce" },
  { url: "example.com/login",            type: "URL",  scenarios: 19, bugs: 3,  privacy: 1, score: 89, time: "3 sa önce" },
  { url: "github.com/my-app/src/auth",   type: "Repo", scenarios: 41, bugs: 8,  privacy: 0, score: 74, time: "5 sa önce" },
];

function scoreColor(s: number): string {
  if (s >= 85) return "text-emerald-400";
  if (s >= 70) return "text-amber-400";
  return "text-rose-400";
}

function AnalysisTimeline() {
  return (
    <div className="space-y-2.5">
      {ANALYSES.map((a, i) => (
        <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800 hover:bg-slate-800/60 transition-colors cursor-pointer group">
          <div className={`flex-shrink-0 mt-0.5 w-8 h-6 rounded flex items-center justify-center text-xs font-bold ${a.type === "URL" ? "bg-cyan-500/20 text-cyan-400" : "bg-purple-500/20 text-purple-400"}`}>
            {a.type}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-mono text-white truncate">{a.url}</p>
            <div className="flex items-center gap-3 mt-1 text-xs text-slate-400 flex-wrap">
              <span className="text-emerald-400">{a.scenarios} senaryo</span>
              <span className="text-rose-400">{a.bugs} bug</span>
              {a.privacy > 0 && <span className="text-amber-400">{a.privacy} PII</span>}
            </div>
          </div>
          <div className="flex-shrink-0 text-right">
            <p className={`text-lg font-bold tabular-nums ${scoreColor(a.score)}`}>{a.score}</p>
            <p className="text-xs text-slate-400">{a.time}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Bug Heatmap ──────────────────────────────────────────────────────────

const BUG_AREAS = [
  { area: "Ödeme Formu",    critical: 4, high: 3, medium: 2, low: 1 },
  { area: "Login Akışı",    critical: 1, high: 2, medium: 3, low: 2 },
  { area: "Sepet",          critical: 0, high: 3, medium: 4, low: 3 },
  { area: "Arama",          critical: 0, high: 1, medium: 2, low: 5 },
  { area: "Profil",         critical: 0, high: 0, medium: 3, low: 4 },
];

function BugHeatmap() {
  return (
    <div className="space-y-2.5">
      {BUG_AREAS.map((area) => {
        const total = area.critical + area.high + area.medium + area.low;
        return (
          <div key={area.area}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-400">{area.area}</span>
              <span className="text-xs text-slate-400">{total} toplam</span>
            </div>
            <div className="flex h-3 rounded-full overflow-hidden gap-px">
              {area.critical > 0 && (
                <div style={{ flex: area.critical }} className="bg-rose-600" title={`${area.critical} kritik`} />
              )}
              {area.high > 0 && (
                <div style={{ flex: area.high }} className="bg-orange-500" title={`${area.high} yüksek`} />
              )}
              {area.medium > 0 && (
                <div style={{ flex: area.medium }} className="bg-amber-400" title={`${area.medium} orta`} />
              )}
              {area.low > 0 && (
                <div style={{ flex: area.low }} className="bg-emerald-500" title={`${area.low} düşük`} />
              )}
            </div>
          </div>
        );
      })}
      <div className="flex items-center gap-4 pt-1">
        {[["Kritik", "bg-rose-600"], ["Yüksek", "bg-orange-500"], ["Orta", "bg-amber-400"], ["Düşük", "bg-emerald-500"]].map(([l, c]) => (
          <div key={l} className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-sm ${c}`} />
            <span className="text-xs text-slate-400">{l}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Privacy Boundary ─────────────────────────────────────────────────────

const PRIVACY_FINDINGS = [
  { url: "/checkout/payment", type: "URL param", field: "email", severity: "high",     page: "Ödeme" },
  { url: "/search",          type: "URL param", field: "user_id", severity: "medium",  page: "Arama" },
  { url: "/profile",        type: "localStorage", field: "auth_token", severity: "critical", page: "Profil" },
  { url: "/analytics",      type: "3rd party", field: "full_name", severity: "medium", page: "Analytics" },
];

function PrivacyBoundary() {
  return (
    <div className="space-y-2">
      {PRIVACY_FINDINGS.map((f, i) => (
        <div key={i} className={`flex items-start gap-2 p-3 rounded-xl border ${f.severity === "critical" ? "bg-rose-500/8 border-rose-500/20" : f.severity === "high" ? "bg-orange-500/8 border-orange-500/20" : "bg-amber-500/6 border-amber-500/15"}`}>
          <span className={`flex-shrink-0 mt-0.5 text-xs font-bold ${f.severity === "critical" ? "text-rose-400" : f.severity === "high" ? "text-orange-400" : "text-amber-400"}`}>
            {f.severity === "critical" ? "🔴" : f.severity === "high" ? "🟠" : "🟡"}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium text-white">{f.page} — <span className="font-mono">{f.field}</span></p>
            <p className="text-xs text-slate-400">{f.type} · <span className="font-mono truncate">{f.url}</span></p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Quick Start Panel ────────────────────────────────────────────────────

function QuickStartPanel() {
  const [url, setUrl] = useState("");

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          type="url"
          className="flex-1 bg-white/5 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder:text-slate-400 focus:outline-none focus:border-cyan-500/40"
          placeholder="https://your-app.com/page veya github.com/org/repo"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <Link
          href="/nexus-code"
          className="flex-shrink-0 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs font-semibold hover:opacity-90 transition-opacity"
        >
          Analiz Et →
        </Link>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {[
          { label: "URL Analizi",    desc: "Web sayfası DOM", icon: "🌐" },
          { label: "Repo Analizi",   desc: "GitHub/Bitbucket", icon: "💻" },
          { label: "Test Üretimi",   desc: "AI senaryolar", icon: "🧪" },
          { label: "Gizlilik Tara", desc: "PII & KVKK", icon: "🔒" },
        ].map((item) => (
          <Link key={item.label} href="/nexus-code" className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:bg-slate-800 transition-colors">
            <span className="text-lg">{item.icon}</span>
            <div>
              <p className="text-xs font-medium text-white">{item.label}</p>
              <p className="text-xs text-slate-400">{item.desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────

export function NexusCodeProductPage() {
  const { telemetry, loading, isDemo } = useProductTelemetry("nexus-code");

  return (
    <div className="flex flex-col gap-6 p-6 pb-12">
      {/* ── Hero ─────────────────────────────────────── */}
      <section className="relative overflow-hidden rounded-3xl border border-cyan-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-cyan-950/30 p-8 lg:p-10">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-24 -right-24 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
          <div className="absolute -bottom-12 -left-12 h-48 w-48 rounded-full bg-cyan-500/8 blur-2xl" />
        </div>
        <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          {/* left: title + CTA */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <span className={`text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-full border ${brand.badge}`}>
                QA + Kod + Web Analiz Agent'ı
              </span>
              {isDemo && <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25">Demo Data</span>}
            </div>
            <h1 className="text-4xl lg:text-5xl font-extrabold text-white mb-4 leading-tight">
              Neurex{" "}
              <span className="bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">Code</span>
              <br />
              Analiz Agent'ı
            </h1>
            <p className="text-lg text-slate-400 mb-8 leading-relaxed">
              URL veya repo ver — sayfa yapısı, bug tahminleri, test senaryoları ve
              gizlilik analizi tek seferde. Lokal Ollama, veri dışarı çıkmaz.
            </p>
          </div>

          {/* right: Analyzer Console visualization */}
          <div className="w-full">
            <AnalyzerConsole />
          </div>
        </div>
      </section>

      {/* ── Stats ──────────────────────────────────── */}
      <section>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Analiz Metrikleri</p>
        <LiveStatsBar stats={telemetry?.stats ?? []} loading={loading} brandText={brand.text} />
      </section>

      {/* ── Quick Start + Timeline ──────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-white mb-5">Hızlı Analiz Başlat</h2>
          <QuickStartPanel />
        </div>

        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Analiz Geçmişi</h2>
            <Link href="/nexus-code" className={`text-xs ${brand.text} hover:underline`}>Tümü →</Link>
          </div>
          <AnalysisTimeline />
        </div>
      </div>

      {/* ── Bug Heatmap + Privacy ──────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Bug Risk Isı Haritası</h2>
            <span className="text-xs text-slate-400">5 alan · 19 toplam bug</span>
          </div>
          <BugHeatmap />
        </div>

        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Gizlilik Sınırı</h2>
            <span className="text-xs text-rose-400">4 ihlal</span>
          </div>
          <PrivacyBoundary />
        </div>
      </div>

      {/* ── Insights + Activity + Onboarding ─────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-white mb-5">AI Öngörüleri</h2>
          <AiInsightFeed insights={telemetry?.aiInsights ?? []} brandBorder={brand.border} brandText={brand.text} loading={loading} />
        </div>
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-white mb-5">Son Analizler</h2>
          <RecentActivity events={telemetry?.recentActivity ?? []} brandText={brand.text} loading={loading} />
        </div>
        <OnboardingChecklist steps={telemetry?.onboarding ?? []} brandGradient={brand.gradient} brandText={brand.text} loading={loading} />
      </div>
    </div>
  );
}
