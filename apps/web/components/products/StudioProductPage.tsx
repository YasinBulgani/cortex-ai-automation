"use client";

import { useState } from "react";
import Link from "next/link";
import { useProductTelemetry } from "@/lib/products/useProductTelemetry";
import { PRODUCT_BRAND } from "@/lib/products/brand";
import { LiveStatsBar } from "./_shared/LiveStatsBar";
import { AiInsightFeed } from "./_shared/AiInsightFeed";
import { RecentActivity } from "./_shared/RecentActivity";
import { OnboardingChecklist } from "./_shared/OnboardingChecklist";

const brand = PRODUCT_BRAND.studio;

// ─── Coverage Wheel ───────────────────────────────────────────────────────

const COVERAGE_SEGMENTS = [
  { label: "UI Flow",      pct: 78, color: "#8b5cf6" },
  { label: "API Test",     pct: 64, color: "#7c3aed" },
  { label: "Güvenlik",     pct: 45, color: "#6d28d9" },
  { label: "Erişilebilirlik", pct: 52, color: "#5b21b6" },
  { label: "Edge Case",    pct: 31, color: "#4c1d95" },
];

function CoverageWheel() {
  const [hovered, setHovered] = useState<number | null>(null);
  const cx = 50, cy = 50, r = 35, stroke = 8;
  const circumference = 2 * Math.PI * r;

  return (
    <div className="flex items-center gap-6">
      <div className="relative flex-shrink-0">
        <svg viewBox="0 0 100 100" width="140" height="140">
          <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={stroke} />
          {COVERAGE_SEGMENTS.map((seg, idx) => {
            const totalAngle = (seg.pct / 100) * 360;
            const startAngle = -90 + idx * 72;
            const dashArr = (totalAngle / 360) * circumference;
            const offset = circumference * (1 - startAngle / 360);
            return (
              <circle
                key={seg.label}
                cx={cx} cy={cy} r={r - idx * 1.5}
                fill="none"
                stroke={seg.color}
                strokeWidth={stroke - idx * 0.5}
                strokeDasharray={`${dashArr} ${circumference}`}
                strokeDashoffset={-offset}
                strokeLinecap="round"
                opacity={hovered === null || hovered === idx ? 1 : 0.3}
                style={{ transition: "opacity 0.2s", cursor: "pointer" }}
                onMouseEnter={() => setHovered(idx)}
                onMouseLeave={() => setHovered(null)}
              />
            );
          })}
          <text x={cx} y={cy - 4} textAnchor="middle" fontSize="10" fontWeight="700" fill="white">
            {hovered !== null ? `${COVERAGE_SEGMENTS[hovered].pct}%` : "54%"}
          </text>
          <text x={cx} y={cy + 8} textAnchor="middle" fontSize="4.5" fill="rgba(255,255,255,0.5)">
            {hovered !== null ? COVERAGE_SEGMENTS[hovered].label : "Ort. Kapsam"}
          </text>
        </svg>
      </div>
      <div className="flex-1 space-y-2">
        {COVERAGE_SEGMENTS.map((seg, idx) => (
          <div
            key={seg.label}
            className="flex items-center gap-2 cursor-pointer"
            onMouseEnter={() => setHovered(idx)}
            onMouseLeave={() => setHovered(null)}
          >
            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: seg.color }} />
            <span className="text-xs text-slate-400 flex-1">{seg.label}</span>
            <span className="text-xs font-medium tabular-nums text-white">{seg.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Kanban Board (lightweight) ───────────────────────────────────────────

const KANBAN_COLS = [
  {
    id: "backlog", label: "Backlog", color: "text-slate-400", count: 28,
    cards: [
      { id: "k1", title: "Kayıt formu validasyon testleri", priority: "medium", tag: "UI" },
      { id: "k2", title: "Ödeme gateway timeout senaryosu", priority: "high", tag: "API" },
    ],
  },
  {
    id: "inprogress", label: "İncelemede", color: "text-violet-400", count: 12,
    cards: [
      { id: "k3", title: "Login — E2E Güvenlik Testi", priority: "critical", tag: "Güvenlik" },
      { id: "k4", title: "Profil güncelleme akışı", priority: "medium", tag: "UI" },
    ],
  },
  {
    id: "approved", label: "Onaylandı", color: "text-emerald-400", count: 187,
    cards: [
      { id: "k5", title: "Sepet boş durumu testi", priority: "low", tag: "UI" },
      { id: "k6", title: "API rate limit senaryosu", priority: "high", tag: "API" },
    ],
  },
];

const PRIORITY_STYLE = {
  critical: "bg-rose-500/20 text-rose-300",
  high:     "bg-amber-500/20 text-amber-300",
  medium:   "bg-sky-500/20 text-sky-300",
  low:      "bg-white/10 text-slate-400",
};

function KanbanBoard() {
  return (
    <div className="grid grid-cols-3 gap-3">
      {KANBAN_COLS.map((col) => (
        <div key={col.id} className="flex flex-col gap-2">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-semibold ${col.color}`}>{col.label}</span>
            <span className="text-xs text-slate-400">({col.count})</span>
          </div>
          {col.cards.map((card) => (
            <div key={card.id} className="rounded-xl bg-white/5 border border-slate-800 p-3 hover:bg-slate-800 transition-colors cursor-grab">
              <p className="text-xs font-medium text-white mb-2 leading-snug">{card.title}</p>
              <div className="flex items-center gap-1.5">
                <span className={`text-xs px-1.5 py-0.5 rounded-md font-medium ${PRIORITY_STYLE[card.priority as keyof typeof PRIORITY_STYLE]}`}>
                  {card.priority}
                </span>
                <span className="text-xs px-1.5 py-0.5 rounded-md bg-violet-500/15 text-violet-300">{card.tag}</span>
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ─── Coverage Heatmap ─────────────────────────────────────────────────────

const HEATMAP_MODULES = ["Auth", "Ödeme", "Sepet", "Profil", "Arama", "Raporlar"];
const HEATMAP_TYPES   = ["Smoke", "Regression", "E2E", "API", "Güvenlik"];

function heatmapVal(mod: number, type: number): number {
  const vals = [
    [95, 88, 72, 64, 41],
    [92, 78, 68, 91, 55],
    [78, 65, 82, 55, 28],
    [88, 74, 59, 62, 38],
    [65, 48, 71, 43, 22],
    [72, 56, 44, 38, 18],
  ];
  return vals[mod]?.[type] ?? 50;
}

function heatColor(v: number): string {
  if (v >= 90) return "#059669";
  if (v >= 70) return "#10b981";
  if (v >= 50) return "#f59e0b";
  if (v >= 30) return "#ef4444";
  return "#991b1b";
}

function CoverageHeatmap() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="text-left text-slate-400 font-normal pb-2 pr-3">Modül</th>
            {HEATMAP_TYPES.map((t) => (
              <th key={t} className="text-center text-slate-400 font-normal pb-2 px-1 min-w-[50px]">{t}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {HEATMAP_MODULES.map((mod, mi) => (
            <tr key={mod}>
              <td className="py-1 pr-3 text-slate-400">{mod}</td>
              {HEATMAP_TYPES.map((_, ti) => {
                const v = heatmapVal(mi, ti);
                return (
                  <td key={ti} className="py-1 px-1 text-center">
                    <div
                      className="inline-flex items-center justify-center w-10 h-7 rounded-lg text-white font-semibold"
                      style={{ backgroundColor: heatColor(v) + "33", border: `1px solid ${heatColor(v)}44` }}
                      title={`${v}%`}
                    >
                      <span style={{ color: heatColor(v) }}>{v}</span>
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── AI Scenario Generator ────────────────────────────────────────────────

const AI_SUGGESTIONS = [
  { id: "ai1", title: "3D Secure redirect akışı", module: "Ödeme", priority: "critical", confidence: 91 },
  { id: "ai2", title: "Kart reddi → yeniden deneme akışı", module: "Ödeme", priority: "high", confidence: 88 },
  { id: "ai3", title: "Oturum zaman aşımı güvenlik testi", module: "Auth", priority: "high", confidence: 85 },
  { id: "ai4", title: "Arama sıfırlama edge case", module: "Arama", priority: "medium", confidence: 79 },
  { id: "ai5", title: "Rapor dışa aktarma — büyük veri", module: "Raporlar", priority: "medium", confidence: 74 },
];

function AiScenarioPanel() {
  const [approved, setApproved] = useState<Set<string>>(new Set());

  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-400 mb-3">AI, gereksinim analizinden 5 eksik senaryo tespit etti</p>
      {AI_SUGGESTIONS.map((s) => (
        <div key={s.id} className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${approved.has(s.id) ? "bg-emerald-500/10 border-emerald-500/25 opacity-60" : "bg-slate-900/60 border-slate-800 hover:bg-slate-800/60"}`}>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-white">{s.title}</p>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-violet-400">{s.module}</span>
              <span className={`text-xs ${PRIORITY_STYLE[s.priority as keyof typeof PRIORITY_STYLE]} px-1.5 py-0.5 rounded`}>{s.priority}</span>
              <span className="text-xs text-slate-400">%{s.confidence} güven</span>
            </div>
          </div>
          <button
            className={`flex-shrink-0 text-xs px-2.5 py-1 rounded-lg font-medium transition-colors ${approved.has(s.id) ? "bg-emerald-500/20 text-emerald-300 cursor-default" : "bg-violet-500/20 text-violet-300 hover:bg-violet-500/30"}`}
            onClick={() => !approved.has(s.id) && setApproved((prev) => new Set(prev).add(s.id))}
          >
            {approved.has(s.id) ? "✓ Onaylandı" : "Onayla"}
          </button>
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────

export function StudioProductPage() {
  const { telemetry, loading, isDemo } = useProductTelemetry("studio");

  return (
    <div className="flex flex-col gap-6 p-6 pb-12">
      {/* ── Hero ─────────────────────────────────────── */}
      <section className="relative overflow-hidden rounded-3xl border border-violet-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-violet-950/30 p-8 lg:p-10">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-24 -right-24 h-72 w-72 rounded-full bg-violet-500/10 blur-3xl" />
          <div className="absolute -bottom-12 -left-12 h-48 w-48 rounded-full bg-violet-500/8 blur-2xl" />
        </div>
        <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          {/* left: title + CTA */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <span className={`text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-full border ${brand.badge}`}>
                Test Tasarımı
              </span>
              {isDemo && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25">Demo Data</span>
              )}
            </div>
            <h1 className="text-4xl lg:text-5xl font-extrabold text-white mb-4 leading-tight">
              Neurex{" "}
              <span className="bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
                Studio
              </span>
              <br />
              Test Tasarım Atölyesi
            </h1>
            <p className="text-lg text-slate-400 mb-8 leading-relaxed">
              Gereksinimden senaryoya, taslaktan onaylı test paketine.
              AI destekli senaryo üretimi ve kapsam analizi tek çalışma alanında.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/task-drafts" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-violet-500 to-purple-600 text-white font-semibold text-sm hover:opacity-90 transition-opacity shadow-lg shadow-violet-500/25">
                Senaryo Oluştur →
              </Link>
              <Link href="/portfolio" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 text-white border border-slate-800 font-medium text-sm hover:bg-slate-700 transition-colors">
                Tüm Senaryolar
              </Link>
            </div>
          </div>

          {/* right: Coverage Wheel visualization */}
          <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-5">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-4">Kapsam Dağılımı</p>
            <CoverageWheel />
          </div>
        </div>
      </section>

      {/* ── Stats ─────────────────────────────────── */}
      <section>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Studio Metrikleri</p>
        <LiveStatsBar stats={telemetry?.stats ?? []} loading={loading} brandText={brand.text} />
      </section>

      {/* ── Kanban + AI ──────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Senaryo Pipeline</h2>
            <Link href="/portfolio" className={`text-xs ${brand.text} hover:underline`}>Tam görünüm →</Link>
          </div>
          <KanbanBoard />
        </div>

        <div className="lg:col-span-2 rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">AI Senaryo Önerileri</h2>
            <span className={`text-xs px-2 py-0.5 rounded-full ${brand.badge} border`}>5 bekleyen</span>
          </div>
          <AiScenarioPanel />
        </div>
      </div>

      {/* ── Coverage Heatmap ───────────────────────── */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-semibold text-white">Kapsam Isı Haritası</h2>
          <span className="text-xs text-slate-400">6 modül × 5 test tipi</span>
        </div>
        <CoverageHeatmap />
      </div>

      {/* ── Insights + Activity + Onboarding ─────── */}
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
