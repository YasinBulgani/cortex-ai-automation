"use client";

import { useState } from "react";
import Link from "next/link";
import { useProductTelemetry } from "@/lib/products/useProductTelemetry";
import { PRODUCT_BRAND } from "@/lib/products/brand";
import { LiveStatsBar } from "./_shared/LiveStatsBar";
import { AiInsightFeed } from "./_shared/AiInsightFeed";
import { RecentActivity } from "./_shared/RecentActivity";
import { OnboardingChecklist } from "./_shared/OnboardingChecklist";

const brand = PRODUCT_BRAND.service;

// ─── Service Mesh Graph (SVG) ─────────────────────────────────────────────

const SERVICES = [
  { id: "gateway", x: 50,  y: 15, label: "API Gateway", status: "ok",      color: "#0ea5e9" },
  { id: "auth",    x: 20,  y: 42, label: "Auth Service", status: "ok",      color: "#06b6d4" },
  { id: "order",   x: 50,  y: 42, label: "Order API",    status: "ok",      color: "#0ea5e9" },
  { id: "payment", x: 80,  y: 42, label: "Payment API",  status: "warning", color: "#f59e0b" },
  { id: "notify",  x: 20,  y: 72, label: "Notify",       status: "ok",      color: "#06b6d4" },
  { id: "inventory",x: 50, y: 72, label: "Inventory",    status: "ok",      color: "#0ea5e9" },
  { id: "mock",    x: 80,  y: 72, label: "Mock Bank",    status: "mock",    color: "#8b5cf6" },
];

const CONNECTIONS = [
  ["gateway", "auth"], ["gateway", "order"], ["gateway", "payment"],
  ["order", "inventory"], ["order", "notify"], ["payment", "mock"],
];

const STATUS_COLOR = { ok: "#10b981", warning: "#f59e0b", error: "#ef4444", mock: "#8b5cf6" };

function ServiceMeshGraph() {
  const [active, setActive] = useState<string | null>(null);

  return (
    <div className="relative">
      <svg viewBox="0 0 100 90" className="w-full" style={{ maxHeight: 220 }}>
        {CONNECTIONS.map(([from, to], i) => {
          const s = SERVICES.find((sv) => sv.id === from)!;
          const t = SERVICES.find((sv) => sv.id === to)!;
          const isActive = active === from || active === to;
          return (
            <g key={i}>
              <line x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                stroke={isActive ? "#0ea5e9" : "rgba(255,255,255,0.12)"}
                strokeWidth={isActive ? "0.8" : "0.4"}
                strokeDasharray={isActive ? "none" : "2 2"}
                style={{ transition: "all 0.2s" }}
              />
              {isActive && (
                <circle r="0.8" fill="#0ea5e9">
                  <animateMotion dur="1s" repeatCount="indefinite" path={`M${s.x},${s.y} L${t.x},${t.y}`} />
                </circle>
              )}
            </g>
          );
        })}
        {SERVICES.map((svc) => {
          const sc = STATUS_COLOR[svc.status as keyof typeof STATUS_COLOR];
          const isAct = active === svc.id;
          return (
            <g key={svc.id} style={{ cursor: "pointer" }} onMouseEnter={() => setActive(svc.id)} onMouseLeave={() => setActive(null)}>
              {isAct && <circle cx={svc.x} cy={svc.y} r="8" fill={svc.color} fillOpacity="0.15" />}
              <circle cx={svc.x} cy={svc.y} r="5" fill={svc.color} fillOpacity="0.85"
                style={{ filter: `drop-shadow(0 0 4px ${svc.color}88)` }} />
              <circle cx={svc.x + 3.5} cy={svc.y - 3.5} r="1.5" fill={sc} />
              <text x={svc.x} y={svc.y + 9} textAnchor="middle" fontSize="3.5" fill="rgba(255,255,255,0.65)">
                {svc.label}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="flex items-center gap-4 mt-2">
        {Object.entries(STATUS_COLOR).map(([k, c]) => (
          <div key={k} className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: c }} />
            <span className="text-xs text-slate-400 capitalize">{k}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Latency Heatstrip ────────────────────────────────────────────────────

const LATENCY_ENDPOINTS = [
  { name: "POST /auth/token",        p50: 45,  p95: 120,  p99: 890, status: "critical" },
  { name: "GET /orders",             p50: 82,  p95: 210,  p99: 450, status: "warning" },
  { name: "POST /orders",            p50: 140, p95: 380,  p99: 720, status: "warning" },
  { name: "GET /inventory/:id",      p50: 28,  p95: 65,   p99: 130, status: "ok" },
  { name: "POST /payments/process",  p50: 210, p95: 520,  p99: 1100, status: "critical" },
  { name: "GET /users/:id",          p50: 35,  p95: 88,   p99: 160, status: "ok" },
];

function latColor(ms: number): string {
  if (ms < 100) return "#10b981";
  if (ms < 300) return "#f59e0b";
  if (ms < 600) return "#f97316";
  return "#ef4444";
}

function LatencyTable() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-slate-400">
            <th className="text-left font-normal pb-2 pr-4">Endpoint</th>
            <th className="text-center font-normal pb-2 px-3">P50</th>
            <th className="text-center font-normal pb-2 px-3">P95</th>
            <th className="text-center font-normal pb-2 px-3">P99</th>
            <th className="text-center font-normal pb-2 pl-3">Durum</th>
          </tr>
        </thead>
        <tbody>
          {LATENCY_ENDPOINTS.map((ep) => (
            <tr key={ep.name} className="hover:bg-white/3 group">
              <td className="py-2 pr-4 font-mono text-white truncate max-w-[180px]">{ep.name}</td>
              {([ep.p50, ep.p95, ep.p99] as number[]).map((v, i) => (
                <td key={i} className="py-2 px-3 text-center">
                  <span className="font-medium tabular-nums" style={{ color: latColor(v) }}>{v}ms</span>
                </td>
              ))}
              <td className="py-2 pl-3 text-center">
                <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${
                  ep.status === "ok" ? "bg-emerald-500/15 text-emerald-300" :
                  ep.status === "warning" ? "bg-amber-500/15 text-amber-300" :
                  "bg-rose-500/15 text-rose-300"
                }`}>
                  {ep.status === "ok" ? "●" : ep.status === "warning" ? "▲" : "✕"} {ep.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Contract Drift ───────────────────────────────────────────────────────

const CONTRACTS = [
  { api: "Payment API v2", field: "response.status",    expected: "string",  actual: "number",  drift: "breaking" },
  { api: "Order API v3",   field: "order.items[].price", expected: "number", actual: "string",  drift: "breaking" },
  { api: "Auth API",       field: "token.expires_in",    expected: "integer", actual: "float",  drift: "minor" },
];

function ContractDrift() {
  return (
    <div className="space-y-3">
      {CONTRACTS.map((c, i) => (
        <div key={i} className={`rounded-xl border p-3 ${c.drift === "breaking" ? "bg-rose-500/8 border-rose-500/20" : "bg-amber-500/8 border-amber-500/20"}`}>
          <div className="flex items-center gap-2 mb-2">
            <span className={`text-xs font-bold ${c.drift === "breaking" ? "text-rose-400" : "text-amber-400"}`}>
              {c.drift === "breaking" ? "⚠ Breaking" : "Minor"}
            </span>
            <span className="text-xs text-white font-medium">{c.api}</span>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="text-slate-400 font-mono">{c.field}</span>
            <span className="text-rose-300 bg-rose-500/15 px-1.5 rounded">{c.actual}</span>
            <span className="text-slate-400">→ beklenen:</span>
            <span className="text-emerald-300 bg-emerald-500/15 px-1.5 rounded">{c.expected}</span>
          </div>
        </div>
      ))}
      <button className="w-full mt-2 text-xs text-sky-400 hover:underline text-center">
        Tüm kontrat durumunu gör →
      </button>
    </div>
  );
}

// ─── Security Radar ───────────────────────────────────────────────────────

const SECURITY_CHECKS = [
  { name: "SQL Injection",       passed: true,  endpoints: 156 },
  { name: "CSRF Koruması",       passed: true,  endpoints: 156 },
  { name: "Rate Limiting",       passed: false, endpoints: 12 },
  { name: "Input Sanitization",  passed: false, endpoints: 8 },
  { name: "Auth Header Check",   passed: true,  endpoints: 156 },
  { name: "CORS Policy",         passed: true,  endpoints: 156 },
];

function SecurityRadar() {
  return (
    <div className="space-y-2.5">
      {SECURITY_CHECKS.map((check) => (
        <div key={check.name} className="flex items-center gap-3">
          <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${check.passed ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"}`}>
            {check.passed ? "✓" : "✕"}
          </span>
          <span className="text-xs text-white flex-1">{check.name}</span>
          <span className="text-xs text-slate-400">{check.endpoints} endpoint</span>
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────

export function ServiceProductPage() {
  const { telemetry, loading, isDemo } = useProductTelemetry("service");

  return (
    <div className="flex flex-col gap-6 p-6 pb-12">
      {/* ── Hero ─────────────────────────────────────── */}
      <section className="relative overflow-hidden rounded-3xl border border-sky-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-sky-950/30 p-8 lg:p-10">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-24 -right-24 h-72 w-72 rounded-full bg-sky-500/10 blur-3xl" />
          <div className="absolute -bottom-12 -left-12 h-48 w-48 rounded-full bg-sky-500/8 blur-2xl" />
        </div>
        <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          {/* left: title + CTA */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <span className={`text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-full border ${brand.badge}`}>
                Servis Kalitesi
              </span>
              {isDemo && <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25">Demo Data</span>}
            </div>
            <h1 className="text-4xl lg:text-5xl font-extrabold text-white mb-4 leading-tight">
              Neurex{" "}
              <span className="bg-gradient-to-r from-sky-400 to-cyan-400 bg-clip-text text-transparent">Service</span>
              <br />
              API Kalite Merkezi
            </h1>
            <p className="text-lg text-slate-400 mb-8 leading-relaxed">
              API testing, servis mesh görünürlüğü, kontrat doğrulama ve güvenlik taramasını
              tek yüzeyde yönet.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/portfolio" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-sky-500 to-cyan-600 text-white font-semibold text-sm hover:opacity-90 transition-opacity shadow-lg shadow-sky-500/25">
                API Test Başlat →
              </Link>
              <Link href="/portfolio" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 text-white border border-slate-800 font-medium text-sm hover:bg-slate-700 transition-colors">
                Chain Builder
              </Link>
            </div>
          </div>

          {/* right: Service Mesh visualization */}
          <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-5">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Servis Mesh</p>
            <ServiceMeshGraph />
          </div>
        </div>
      </section>

      {/* ── Stats ──────────────────────────────────── */}
      <section>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Servis Metrikleri</p>
        <LiveStatsBar stats={telemetry?.stats ?? []} loading={loading} brandText={brand.text} />
      </section>

      {/* ── Latency Table + Security ──────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Endpoint Latency Analizi</h2>
            <span className="text-xs text-slate-400">P50 / P95 / P99</span>
          </div>
          <LatencyTable />
        </div>

        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Güvenlik Kontrolü</h2>
            <span className="text-xs text-slate-400">6 kural</span>
          </div>
          <SecurityRadar />
        </div>
      </div>

      {/* ── Contract + Insights + Activity ─────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-white mb-5">Kontrat Drift</h2>
          <ContractDrift />
        </div>
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-white mb-5">AI Öngörüleri</h2>
          <AiInsightFeed insights={telemetry?.aiInsights ?? []} brandBorder={brand.border} brandText={brand.text} loading={loading} />
        </div>
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-white mb-5">Son Aktiviteler</h2>
          <RecentActivity events={telemetry?.recentActivity ?? []} brandText={brand.text} loading={loading} />
        </div>
      </div>

      {/* ── Onboarding ──────────────────────────────── */}
      <OnboardingChecklist steps={telemetry?.onboarding ?? []} brandGradient={brand.gradient} brandText={brand.text} loading={loading} />
    </div>
  );
}
