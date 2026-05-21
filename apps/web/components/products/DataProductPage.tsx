"use client";

import { useState } from "react";
import Link from "next/link";
import { useProductTelemetry } from "@/lib/products/useProductTelemetry";
import { PRODUCT_BRAND } from "@/lib/products/brand";
import { LiveStatsBar } from "./_shared/LiveStatsBar";
import { AiInsightFeed } from "./_shared/AiInsightFeed";
import { RecentActivity } from "./_shared/RecentActivity";
import { OnboardingChecklist } from "./_shared/OnboardingChecklist";

const brand = PRODUCT_BRAND.data;

// ─── Particle Stream (animated data flow) ─────────────────────────────────

const PIPELINE_NODES = [
  { id: "src",   cx: 60,  label: "Kaynak",     sublabel: "DB / API", color: "#f59e0b", glow: "#f59e0b44" },
  { id: "gen",   cx: 180, label: "Üretici",    sublabel: "AI Model",  color: "#f97316", glow: "#f9731644" },
  { id: "mask",  cx: 300, label: "Maskeleme",  sublabel: "PII / KVKK",color: "#10b981", glow: "#10b98144" },
  { id: "store", cx: 420, label: "Depo",       sublabel: "Dataset",   color: "#34d399", glow: "#34d39944" },
];

function ParticleStream() {
  const cy = 80;
  return (
    <svg viewBox="0 0 480 160" className="w-full" style={{ height: 160 }}>
      <defs>
        {PIPELINE_NODES.map((n) => (
          <radialGradient key={n.id} id={`glow-${n.id}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={n.color} stopOpacity="0.4" />
            <stop offset="100%" stopColor={n.color} stopOpacity="0" />
          </radialGradient>
        ))}
      </defs>

      {/* Glow halos behind nodes */}
      {PIPELINE_NODES.map((n) => (
        <circle key={`h-${n.id}`} cx={n.cx} cy={cy} r="32" fill={`url(#glow-${n.id})`} />
      ))}

      {/* Connector lines */}
      {PIPELINE_NODES.slice(0, -1).map((n, i) => (
        <line
          key={`line-${i}`}
          x1={n.cx + 16} y1={cy}
          x2={PIPELINE_NODES[i + 1].cx - 16} y2={cy}
          stroke="rgba(245,158,11,0.15)" strokeWidth="2.5" strokeLinecap="round"
          strokeDasharray="6 4"
        />
      ))}

      {/* Animated flow particles */}
      {PIPELINE_NODES.slice(0, -1).flatMap((n, i) =>
        [0, 1, 2].map((j) => (
          <circle key={`p-${i}-${j}`} r="3" fill={n.color} fillOpacity="0.9">
            <animateMotion
              dur={`${1.6 + i * 0.2}s`}
              repeatCount="indefinite"
              begin={`${j * 0.5 + i * 0.1}s`}
              path={`M${n.cx + 18},${cy} L${PIPELINE_NODES[i + 1].cx - 18},${cy}`}
            />
            <animate attributeName="opacity" values="0;1;1;0" dur={`${1.6 + i * 0.2}s`} repeatCount="indefinite" begin={`${j * 0.5 + i * 0.1}s`} />
          </circle>
        ))
      )}

      {/* Node circles */}
      {PIPELINE_NODES.map((n) => (
        <g key={n.id}>
          <circle cx={n.cx} cy={cy} r="18" fill={n.color} fillOpacity="0.12" stroke={n.color} strokeWidth="1.5" />
          <circle cx={n.cx} cy={cy} r="9" fill={n.color} />
          <text x={n.cx} y={cy + 32} textAnchor="middle" fontSize="9" fontWeight="600" fill="rgba(255,255,255,0.85)">{n.label}</text>
          <text x={n.cx} y={cy + 44} textAnchor="middle" fontSize="7.5" fill="rgba(255,255,255,0.4)">{n.sublabel}</text>
        </g>
      ))}

      {/* Center counter */}
      <text x="240" y="28" textAnchor="middle" fontSize="18" fontWeight="800" fill="#f59e0b" letterSpacing="-0.5">2.4M</text>
      <text x="240" y="44" textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.4)">kayıt üretildi · bu ay</text>
    </svg>
  );
}

// ─── Schema Universe ──────────────────────────────────────────────────────

const SCHEMAS = [
  { name: "users",           fields: 24, records: "500K", health: 98, pii: 8 },
  { name: "orders",          fields: 18, records: "1.2M", health: 97, pii: 3 },
  { name: "payment_events",  fields: 31, records: "780K", health: 91, pii: 12 },
  { name: "products",        fields: 15, records: "45K",  health: 99, pii: 0 },
  { name: "sessions",        fields: 9,  records: "8.2M", health: 95, pii: 4 },
  { name: "audit_log",       fields: 12, records: "2.1M", health: 96, pii: 1 },
];

function SchemaUniverse() {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="space-y-2">
      {SCHEMAS.map((s) => (
        <div
          key={s.name}
          className={`flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-colors ${selected === s.name ? "bg-amber-500/10 border border-amber-500/25" : "hover:bg-slate-900/60 border border-transparent"}`}
          onClick={() => setSelected(selected === s.name ? null : s.name)}
        >
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${s.health >= 97 ? "bg-emerald-400" : s.health >= 90 ? "bg-amber-400" : "bg-rose-400"}`} />
          <span className="text-xs font-mono text-white flex-1">{s.name}</span>
          <span className="text-xs text-slate-400">{s.fields} alan</span>
          <span className="text-xs text-slate-400">{s.records}</span>
          {s.pii > 0 && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300">{s.pii} PII</span>
          )}
          <span className={`text-xs font-medium ${s.health >= 97 ? "text-emerald-400" : "text-amber-400"}`}>{s.health}%</span>
        </div>
      ))}
    </div>
  );
}

// ─── PII Radar ────────────────────────────────────────────────────────────

const PII_TYPES = [
  { label: "E-posta",     found: 42, masked: 42, color: "#10b981" },
  { label: "Telefon",     found: 28, masked: 27, color: "#34d399" },
  { label: "TC Kimlik",   found: 15, masked: 15, color: "#10b981" },
  { label: "Kredi Kartı", found: 8,  masked: 5,  color: "#ef4444" },
  { label: "IBAN",        found: 6,  masked: 6,  color: "#10b981" },
  { label: "IP Adresi",   found: 31, masked: 28, color: "#f59e0b" },
];

function PiiRadar() {
  return (
    <div className="space-y-2.5">
      {PII_TYPES.map((p) => {
        const rate = Math.round((p.masked / p.found) * 100);
        const danger = rate < 100;
        return (
          <div key={p.label}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-400">{p.label}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">{p.masked}/{p.found}</span>
                <span className={`text-xs font-semibold ${danger ? "text-rose-400" : "text-emerald-400"}`}>
                  {rate}%
                </span>
              </div>
            </div>
            <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
              <div
                className={`h-full rounded-full ${danger ? "bg-rose-500" : "bg-emerald-500"}`}
                style={{ width: `${rate}%` }}
              />
            </div>
          </div>
        );
      })}
      <div className="pt-2 flex items-center justify-between">
        <span className="text-xs text-slate-400">KVKK Uyum Puanı</span>
        <span className="text-sm font-bold text-emerald-400">99.7%</span>
      </div>
    </div>
  );
}

// ─── Quality Gauges ───────────────────────────────────────────────────────

const QUALITY_DIMS = [
  { label: "Tamamlık",    value: 94, color: "#f59e0b" },
  { label: "Tutarlılık",  value: 98, color: "#f97316" },
  { label: "Benzersizlik",value: 99, color: "#10b981" },
  { label: "Dağılım",     value: 91, color: "#34d399" },
];

function qualGaugeArc(pct: number, color: string): string {
  const r = 28;
  const circ = 2 * Math.PI * r;
  return `${(pct / 100) * circ} ${circ}`;
}

function QualityGauges() {
  return (
    <div className="grid grid-cols-2 gap-4">
      {QUALITY_DIMS.map((dim) => {
        const r = 28;
        const circ = 2 * Math.PI * r;
        return (
          <div key={dim.label} className="flex flex-col items-center gap-1">
            <svg viewBox="0 0 70 70" width="80" height="80">
              <circle cx="35" cy="35" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
              <circle
                cx="35" cy="35" r={r}
                fill="none"
                stroke={dim.color}
                strokeWidth="8"
                strokeDasharray={`${(dim.value / 100) * circ} ${circ}`}
                strokeDashoffset={circ * 0.25}
                strokeLinecap="round"
                style={{ filter: `drop-shadow(0 0 4px ${dim.color}66)` }}
              />
              <text x="35" y="38" textAnchor="middle" fontSize="10" fontWeight="700" fill={dim.color}>{dim.value}</text>
            </svg>
            <span className="text-xs text-slate-400">{dim.label}</span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Generation Recipes ───────────────────────────────────────────────────

const RECIPES = [
  { name: "E-Ticaret Kullanıcıları", schema: "users", size: "100K", status: "ready", time: "12s" },
  { name: "Ödeme Eventleri",         schema: "payment_events", size: "50K", status: "running", time: "..." },
  { name: "Ürün Kataloğu",           schema: "products", size: "5K", status: "ready", time: "3s" },
  { name: "Seans Logları",           schema: "sessions", size: "1M", status: "queued", time: "-" },
];

function GenerationRecipes() {
  const [running, setRunning] = useState<Set<string>>(new Set());

  return (
    <div className="space-y-2.5">
      {RECIPES.map((r) => {
        const isRunning = r.status === "running" || running.has(r.name);
        return (
          <div key={r.name} className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800 hover:bg-slate-800/60 transition-colors">
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white">{r.name}</p>
              <p className="text-xs text-slate-400 font-mono">{r.schema} · {r.size} kayıt</p>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full ${isRunning ? "bg-sky-500/15 text-sky-300 animate-pulse" : r.status === "queued" ? "bg-slate-800 text-slate-400" : "bg-emerald-500/15 text-emerald-300"}`}>
              {isRunning ? "üretiliyor..." : r.status === "queued" ? "kuyrukta" : `✓ ${r.time}`}
            </span>
            {!isRunning && r.status !== "running" && (
              <button
                className="text-xs text-amber-400 hover:underline"
                onClick={() => setRunning((prev) => new Set(prev).add(r.name))}
              >
                Çalıştır
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────

export function DataProductPage() {
  const { telemetry, loading, isDemo } = useProductTelemetry("data");

  return (
    <div className="flex flex-col gap-6 p-6 pb-12">

      {/* ── Hero card ────────────────────────────────── */}
      <section className="relative overflow-hidden rounded-3xl border border-amber-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-amber-950/30 p-8 lg:p-10">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-24 -right-24 h-72 w-72 rounded-full bg-amber-500/10 blur-3xl" />
          <div className="absolute -bottom-12 -left-12 h-48 w-48 rounded-full bg-orange-500/8 blur-2xl" />
        </div>
        <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <span className={`text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-full border ${brand.badge}`}>
                Sentetik Veri & Gizlilik
              </span>
              {isDemo && <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25">Demo Data</span>}
            </div>
            <h1 className="text-4xl lg:text-5xl font-extrabold text-white mb-3 leading-tight">
              Neurex{" "}
              <span className="bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">Data</span>
              <br />
              <span className="text-2xl lg:text-3xl font-semibold text-slate-300">Veri Üretim Merkezi</span>
            </h1>
            <p className="text-base text-slate-400 mb-6 leading-relaxed max-w-lg">
              Gerçekçi, KVKK uyumlu test verisi üret. PII tespiti, maskeleme ve
              veri kalitesi görünürlüğü tek panelde.
            </p>
            <div className="flex flex-wrap gap-3 mb-8">
              <Link href="/portfolio" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold text-sm hover:opacity-90 transition-opacity shadow-lg shadow-amber-500/25">
                Veri Üret →
              </Link>
              <Link href="/portfolio" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/8 text-white border border-white/10 font-medium text-sm hover:bg-white/12 transition-colors">
                Gizlilik Taraması
              </Link>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[
                { v: "2.4M", l: "Üretilen kayıt" },
                { v: "99.7%", l: "KVKK uyumu" },
                { v: "6", l: "Aktif şema" },
              ].map(({ v, l }) => (
                <div key={l} className="rounded-xl bg-amber-500/10 border border-amber-500/20 p-3 text-center">
                  <p className="text-xl font-bold text-amber-400 tabular-nums">{v}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">{l}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Particle Stream */}
          <div className="rounded-2xl bg-slate-950/60 border border-amber-500/15 p-6">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Veri Pipeline Akışı</p>
              <span className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-semibold">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                CANLI
              </span>
            </div>
            <ParticleStream />
          </div>
        </div>
      </section>

      {/* ── Stats ────────────────────────────────────── */}
      <section>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Veri Metrikleri</p>
        <LiveStatsBar stats={telemetry?.stats ?? []} loading={loading} brandText={brand.text} />
      </section>

      {/* ── Schema + Quality ─────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Şema Kataloğu</h2>
            <span className="text-xs text-slate-500">6 şema · 127 dataset</span>
          </div>
          <SchemaUniverse />
        </div>
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-white mb-5">Kalite Boyutları</h2>
          <QualityGauges />
        </div>
      </div>

      {/* ── PII + Recipes ────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">PII Radar</h2>
            <span className="text-xs text-slate-500">KVKK · GDPR</span>
          </div>
          <PiiRadar />
        </div>
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Üretim Tarifleri</h2>
            <span className="text-xs text-amber-400">1 aktif</span>
          </div>
          <GenerationRecipes />
        </div>
      </div>

      {/* ── Insights + Activity + Onboarding ─────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-white mb-5">AI Öngörüleri</h2>
          <AiInsightFeed insights={telemetry?.aiInsights ?? []} brandBorder={brand.border} brandText={brand.text} loading={loading} />
        </div>
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-white mb-5">Son Aktiviteler</h2>
          <RecentActivity events={telemetry?.recentActivity ?? []} brandText={brand.text} loading={loading} />
        </div>
        <OnboardingChecklist steps={telemetry?.onboarding ?? []} brandGradient={brand.gradient} brandText={brand.text} loading={loading} />
      </div>
    </div>
  );
}
