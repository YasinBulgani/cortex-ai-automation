"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useProductTelemetry } from "@/lib/products/useProductTelemetry";
import { PRODUCT_BRAND } from "@/lib/products/brand";
import { LiveStatsBar } from "./_shared/LiveStatsBar";
import { AiInsightFeed } from "./_shared/AiInsightFeed";
import { RecentActivity } from "./_shared/RecentActivity";
import { OnboardingChecklist } from "./_shared/OnboardingChecklist";

const brand = PRODUCT_BRAND.one;

// ─── Constellation SVG ────────────────────────────────────────────────────

const PLANETS = [
  { id: "one",    x: 50,  y: 50, r: 18, label: "One",      color: "#6366f1" },
  { id: "studio", x: 80,  y: 22, r: 10, label: "Studio",   color: "#8b5cf6" },
  { id: "svc",    x: 80,  y: 78, r: 10, label: "Service",  color: "#0ea5e9" },
  { id: "web",    x: 20,  y: 22, r: 10, label: "Web",      color: "#10b981" },
  { id: "mobile", x: 20,  y: 78, r: 10, label: "Mobile",   color: "#f43f5e" },
  { id: "data",   x: 13,  y: 50, r: 8,  label: "Data",     color: "#f59e0b" },
  { id: "intel",  x: 87,  y: 50, r: 8,  label: "AI",       color: "#d946ef" },
  { id: "code",   x: 50,  y: 88, r: 8,  label: "Code",     color: "#06b6d4" },
];

function ConstellationMap() {
  const [pulse, setPulse] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setPulse((p) => (p + 1) % PLANETS.length), 1200);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="relative w-full aspect-square max-w-xs mx-auto">
      <svg viewBox="0 0 100 100" className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
        {/* Connection lines from One to all others */}
        {PLANETS.slice(1).map((p) => (
          <line
            key={p.id}
            x1={PLANETS[0].x} y1={PLANETS[0].y}
            x2={p.x} y2={p.y}
            stroke="rgba(99,102,241,0.25)"
            strokeWidth="0.5"
            strokeDasharray="2 2"
          />
        ))}
        {/* Planets */}
        {PLANETS.map((p, idx) => (
          <g key={p.id}>
            {idx === 0 && (
              <>
                <circle cx={p.x} cy={p.y} r={p.r + 8} fill={p.color} fillOpacity="0.06" />
                <circle cx={p.x} cy={p.y} r={p.r + 4} fill={p.color} fillOpacity="0.12" />
              </>
            )}
            <circle
              cx={p.x} cy={p.y} r={p.r}
              fill={p.color}
              fillOpacity={idx === 0 ? 0.9 : 0.75}
              style={{ filter: `drop-shadow(0 0 ${idx === 0 ? 6 : 3}px ${p.color}88)` }}
            />
            {pulse === idx && (
              <circle
                cx={p.x} cy={p.y} r={p.r + 4}
                fill="none"
                stroke={p.color}
                strokeWidth="0.6"
                strokeOpacity="0.6"
              >
                <animate attributeName="r" values={`${p.r};${p.r + 8}`} dur="1s" fill="freeze" />
                <animate attributeName="stroke-opacity" values="0.6;0" dur="1s" fill="freeze" />
              </circle>
            )}
            <text
              x={p.x}
              y={p.y + p.r + 5}
              textAnchor="middle"
              fontSize={idx === 0 ? "5" : "4"}
              fill="white"
              fillOpacity="0.7"
            >
              {p.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

// ─── Health Grid ──────────────────────────────────────────────────────────

const HEALTH_GRID = [
  { product: "Studio", metrics: [96, 89, 94, 91] },
  { product: "Service", metrics: [98, 96, 88, 95] },
  { product: "Web",    metrics: [91, 85, 93, 78] },
  { product: "Mobile", metrics: [87, 82, 90, 84] },
  { product: "Data",   metrics: [99, 94, 97, 96] },
  { product: "AI",     metrics: [97, 91, 94, 88] },
  { product: "Code",   metrics: [88, 79, 85, 91] },
];
const HEALTH_COLS = ["Pass Rate", "Kapsam", "Sağlık", "Güven"];

function healthColor(v: number): string {
  if (v >= 95) return "bg-emerald-500";
  if (v >= 85) return "bg-emerald-400";
  if (v >= 75) return "bg-amber-400";
  return "bg-rose-500";
}

function HealthGrid() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="text-left text-slate-400 font-normal pb-2 pr-4">Ürün</th>
            {HEALTH_COLS.map((c) => (
              <th key={c} className="text-center text-slate-400 font-normal pb-2 px-2">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {HEALTH_GRID.map((row) => (
            <tr key={row.product} className="hover:bg-white/3">
              <td className="py-1.5 pr-4 text-slate-400">{row.product}</td>
              {row.metrics.map((v, i) => (
                <td key={i} className="py-1.5 px-2 text-center">
                  <div className="flex items-center justify-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${healthColor(v)}`} />
                    <span className="text-white tabular-nums">{v}%</span>
                  </div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── License Forecast ─────────────────────────────────────────────────────

const LICENSE_PRODUCTS = [
  { name: "One",        used: 100, total: 100, color: "#6366f1" },
  { name: "Studio",     used: 28,  total: 50,  color: "#8b5cf6" },
  { name: "Service",    used: 15,  total: 25,  color: "#0ea5e9" },
  { name: "Web",        used: 38,  total: 50,  color: "#10b981" },
  { name: "Mobile",     used: 12,  total: 20,  color: "#f43f5e" },
  { name: "Data",       used: 8,   total: 10,  color: "#f59e0b" },
];

function LicenseForecast() {
  return (
    <div className="space-y-3">
      {LICENSE_PRODUCTS.map((p) => {
        const pct = Math.round((p.used / p.total) * 100);
        const warn = pct >= 90;
        return (
          <div key={p.name}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-400">{p.name}</span>
              <span className={`text-xs font-medium tabular-nums ${warn ? "text-amber-400" : "text-white"}`}>
                {p.used}/{p.total} {warn && "⚠"}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${pct}%`, backgroundColor: p.color, opacity: warn ? 1 : 0.7 }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Integration Matrix ───────────────────────────────────────────────────

const INTEGRATIONS = [
  { name: "GitHub",      status: "active",  icon: "🐙", desc: "Actions webhook aktif" },
  { name: "Jira",        status: "active",  icon: "📋", desc: "Issue sync açık" },
  { name: "Slack",       status: "active",  icon: "💬", desc: "Alert kanalı bağlı" },
  { name: "Jenkins",     status: "idle",    icon: "🔧", desc: "Pipeline bağlı" },
  { name: "Confluence",  status: "active",  icon: "📚", desc: "Doküman senkron" },
  { name: "Datadog",     status: "warning", icon: "📊", desc: "APM bağlantısı kısmi" },
  { name: "Sentry",      status: "active",  icon: "🚨", desc: "Error feed aktif" },
  { name: "Bitbucket",   status: "idle",    icon: "🪣", desc: "Bağlı değil" },
];

const INT_STATUS = {
  active:  "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  idle:    "bg-slate-800/60 text-slate-400 border-slate-800",
  warning: "bg-amber-500/15 text-amber-300 border-amber-500/25",
};

function IntegrationMatrix() {
  return (
    <div className="grid grid-cols-2 gap-2">
      {INTEGRATIONS.map((int) => (
        <div
          key={int.name}
          className={`rounded-xl border p-3 flex items-center gap-2.5 ${INT_STATUS[int.status as keyof typeof INT_STATUS]}`}
        >
          <span className="text-lg leading-none">{int.icon}</span>
          <div className="min-w-0">
            <p className="text-xs font-semibold truncate">{int.name}</p>
            <p className="text-xs opacity-70 truncate">{int.desc}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Top Projects ─────────────────────────────────────────────────────────

const TOP_PROJECTS = [
  { name: "E-Ticaret Platform", product: "Web", passRate: 94, runs: 847, status: "passing" },
  { name: "Mobile Banking App", product: "Mobile", passRate: 87, runs: 521, status: "warning" },
  { name: "Payment Gateway API", product: "Service", passRate: 98, runs: 1204, status: "passing" },
  { name: "Admin Panel",        product: "Web", passRate: 91, runs: 234, status: "passing" },
  { name: "ML Data Pipeline",   product: "Data", passRate: 96, runs: 89, status: "passing" },
];

function TopProjects() {
  return (
    <div className="space-y-2">
      {TOP_PROJECTS.map((p) => (
        <div key={p.name} className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-slate-900/60 transition-colors cursor-pointer">
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${p.status === "passing" ? "bg-emerald-400" : "bg-amber-400"}`} />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{p.name}</p>
            <p className="text-xs text-slate-400">{p.product} · {p.runs} koşu</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
              <div
                className={`h-full rounded-full ${p.passRate >= 95 ? "bg-emerald-500" : p.passRate >= 85 ? "bg-emerald-400" : "bg-amber-400"}`}
                style={{ width: `${p.passRate}%` }}
              />
            </div>
            <span className="text-xs tabular-nums text-slate-400 w-10 text-right">{p.passRate}%</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────

export function OneProductPage() {
  const { telemetry, loading, isDemo } = useProductTelemetry("one");

  return (
    <div className="flex flex-col gap-6 p-6 pb-12">

      {/* ── Hero card ────────────────────────────────── */}
      <section className="relative overflow-hidden rounded-3xl border border-indigo-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/30 p-8 lg:p-10">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-24 -right-24 h-72 w-72 rounded-full bg-indigo-500/10 blur-3xl" />
          <div className="absolute -bottom-12 -left-12 h-48 w-48 rounded-full bg-blue-500/8 blur-2xl" />
          {Array.from({ length: 30 }).map((_, i) => (
            <div
              key={i}
              className="absolute rounded-full bg-indigo-400/15"
              style={{
                width: `${1 + (i % 3)}px`, height: `${1 + (i % 3)}px`,
                left: `${(i * 3.3) % 100}%`, top: `${(i * 3.7) % 100}%`,
                animation: `pulse ${2 + (i % 3)}s ease-in-out infinite ${(i % 4) * 0.5}s`,
              }}
            />
          ))}
        </div>
        <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <span className={`text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-full border ${brand.badge}`}>
                Platform Çekirdeği
              </span>
              {isDemo && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25">
                  Demo Data
                </span>
              )}
            </div>
            <h1 className="text-4xl lg:text-5xl font-extrabold text-white mb-3 leading-tight">
              Neurex{" "}
              <span className="bg-gradient-to-r from-indigo-400 to-blue-400 bg-clip-text text-transparent">One</span>
              <br />
              <span className="text-2xl lg:text-3xl font-semibold text-slate-300">Mission Control</span>
            </h1>
            <p className="text-base text-slate-400 mb-6 leading-relaxed max-w-lg">
              7 ürünü tek orbita'dan izle. Platform sağlığını, lisans kullanımını ve entegrasyon durumunu
              gerçek zamanlı görünür kıl.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/portfolio" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-blue-600 text-white font-semibold text-sm hover:opacity-90 transition-opacity shadow-lg shadow-indigo-500/25">
                Portfolio'ya Git →
              </Link>
              <Link href="/system" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/8 text-white border border-white/10 font-medium text-sm hover:bg-white/12 transition-colors">
                Sistem Sağlık
              </Link>
            </div>
          </div>
          <div className="flex justify-center">
            <ConstellationMap />
          </div>
        </div>
      </section>

      {/* ── Live Stats ───────────────────────────────── */}
      <section>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Platform Metrikleri</p>
        <LiveStatsBar stats={telemetry?.stats ?? []} loading={loading} brandText={brand.text} />
      </section>

      {/* ── Health Matrix + License ───────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Platform Sağlık Matrisi</h2>
            <span className="text-xs text-slate-500">7 ürün · 4 boyut</span>
          </div>
          <HealthGrid />
        </div>
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Lisans Kullanımı</h2>
            <span className="text-xs text-slate-500">Canlı</span>
          </div>
          <LicenseForecast />
        </div>
      </div>

      {/* ── Projects + Insights + Integrations ───────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Öne Çıkan Projeler</h2>
            <Link href="/portfolio" className={`text-xs ${brand.text} hover:underline`}>Tümü →</Link>
          </div>
          <TopProjects />
        </div>
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">AI Öngörüleri</h2>
            <span className="text-xs text-slate-500">{telemetry?.aiInsights?.length ?? 0} öneri</span>
          </div>
          <AiInsightFeed insights={telemetry?.aiInsights ?? []} brandBorder={brand.border} brandText={brand.text} loading={loading} />
        </div>
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Entegrasyonlar</h2>
            <span className="text-xs text-slate-500">8 sistem</span>
          </div>
          <IntegrationMatrix />
        </div>
      </div>

      {/* ── Activity + Onboarding ────────────────────── */}
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
