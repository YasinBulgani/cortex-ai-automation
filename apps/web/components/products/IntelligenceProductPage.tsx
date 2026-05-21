"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useProductTelemetry } from "@/lib/products/useProductTelemetry";
import { PRODUCT_BRAND } from "@/lib/products/brand";
import { LiveStatsBar } from "./_shared/LiveStatsBar";
import { AiInsightFeed } from "./_shared/AiInsightFeed";
import { RecentActivity } from "./_shared/RecentActivity";
import { OnboardingChecklist } from "./_shared/OnboardingChecklist";
import { CortexAutomationPanel } from "./_shared/CortexAutomationPanel";

const brand = PRODUCT_BRAND.intelligence;

// ─── Living Brain (CSS neuron animation) ─────────────────────────────────

const NEURONS = Array.from({ length: 12 }, (_, i) => ({
  id: i,
  x: 10 + ((i * 37) % 80),
  y: 10 + ((i * 23) % 80),
  delay: i * 0.4,
}));

const SYNAPSES = [
  [0, 3], [3, 7], [7, 11], [0, 5], [5, 9], [2, 6], [6, 10], [1, 4], [4, 8], [8, 11], [2, 9], [1, 7],
];

function LivingBrain() {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setActive((a) => (a + 1) % NEURONS.length), 800);
    return () => clearInterval(id);
  }, []);

  return (
    <svg viewBox="0 0 100 100" className="w-full" style={{ maxHeight: 200 }}>
      {/* Synapses */}
      {SYNAPSES.map(([a, b], i) => {
        const na = NEURONS[a], nb = NEURONS[b];
        const isActive = active === a || active === b;
        return (
          <line key={i}
            x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
            stroke={isActive ? "#d946ef" : "rgba(217,70,239,0.12)"}
            strokeWidth={isActive ? "0.8" : "0.3"}
            style={{ transition: "stroke 0.3s, stroke-width 0.3s" }}
          />
        );
      })}
      {/* Neurons */}
      {NEURONS.map((n) => {
        const isActive = active === n.id;
        return (
          <g key={n.id}>
            {isActive && (
              <circle cx={n.x} cy={n.y} r="6" fill="#d946ef" fillOpacity="0.15">
                <animate attributeName="r" values="4;10;4" dur="0.8s" fill="freeze" />
                <animate attributeName="fill-opacity" values="0.15;0.05;0.15" dur="0.8s" fill="freeze" />
              </circle>
            )}
            <circle
              cx={n.x} cy={n.y} r={isActive ? "3.5" : "2.5"}
              fill={isActive ? "#d946ef" : "rgba(217,70,239,0.6)"}
              style={{ filter: isActive ? "drop-shadow(0 0 4px #d946ef)" : "none", transition: "all 0.3s" }}
            />
          </g>
        );
      })}
      {/* Center label */}
      <text x="50" y="97" textAnchor="middle" fontSize="3.5" fill="rgba(217,70,239,0.5)">
        Neural Activity — Realtime
      </text>
    </svg>
  );
}

// ─── Provider Race Track ──────────────────────────────────────────────────

const PROVIDERS = [
  { name: "Groq llama3-70b",  latency: 420,  success: 97.2, status: "degraded", calls: 8421  },
  { name: "Gemini Flash",     latency: 680,  success: 99.1, status: "active",   calls: 6284  },
  { name: "Ollama llama3",    latency: 1240, success: 94.8, status: "active",   calls: 2156  },
  { name: "GPT-4o mini",      latency: 890,  success: 98.7, status: "active",   calls: 1893  },
  { name: "g4f fallback",     latency: 2100, success: 78.3, status: "standby",  calls: 312   },
];

const maxCalls = Math.max(...PROVIDERS.map((p) => p.calls));

function ProviderRaceTrack() {
  return (
    <div className="space-y-3">
      {PROVIDERS.map((p) => (
        <div key={p.name} className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full flex-shrink-0 mt-0.5"
            style={{ backgroundColor: p.status === "active" ? "#10b981" : p.status === "degraded" ? "#f59e0b" : "#6b7280" }} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-white truncate pr-2">{p.name}</span>
              <div className="flex items-center gap-2 text-xs text-slate-400 flex-shrink-0">
                <span className={p.success >= 95 ? "text-emerald-400" : p.success >= 85 ? "text-amber-400" : "text-rose-400"}>{p.success}%</span>
                <span>{p.latency}ms</span>
              </div>
            </div>
            <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${(p.calls / maxCalls) * 100}%`,
                  backgroundColor: p.status === "active" ? "#d946ef" : p.status === "degraded" ? "#f59e0b" : "#4b5563",
                }}
              />
            </div>
          </div>
          <span className="text-xs text-slate-400 flex-shrink-0 w-12 text-right tabular-nums">{p.calls.toLocaleString()}</span>
        </div>
      ))}
      <p className="text-xs text-slate-400 text-center pt-1">Groq → Gemini → Ollama → g4f fallback zinciri aktif</p>
    </div>
  );
}

// ─── LLM-as-Judge Studio ─────────────────────────────────────────────────

const JUDGE_RESULTS = [
  { scenario: "Login E2E Güvenlik Testi",  score: 92, verdict: "approved", issues: 0 },
  { scenario: "Checkout 3D Secure Akışı",  score: 87, verdict: "approved", issues: 1 },
  { scenario: "Profil Güncelleme",         score: 71, verdict: "review",   issues: 3 },
  { scenario: "Arama Öneriler Testi",      score: 43, verdict: "rejected", issues: 7 },
  { scenario: "Ödeme Hata Senaryosu",      score: 88, verdict: "approved", issues: 0 },
];

const VERDICT = {
  approved: { color: "text-emerald-400", bg: "bg-emerald-500/15 border-emerald-500/25", label: "Onaylı" },
  review:   { color: "text-amber-400",   bg: "bg-amber-500/15 border-amber-500/25",   label: "İncelemede" },
  rejected: { color: "text-rose-400",    bg: "bg-rose-500/15 border-rose-500/25",     label: "Reddedildi" },
};

function JudgeStudio() {
  return (
    <div className="space-y-2.5">
      {JUDGE_RESULTS.map((r) => {
        const v = VERDICT[r.verdict as keyof typeof VERDICT];
        return (
          <div key={r.scenario} className={`flex items-center gap-3 p-3 rounded-xl border ${v.bg}`}>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">{r.scenario}</p>
              {r.issues > 0 && (
                <p className="text-xs text-slate-400 mt-0.5">{r.issues} sorun tespit edildi</p>
              )}
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <div className="w-10 h-10 relative">
                <svg viewBox="0 0 40 40" className="w-full h-full -rotate-90">
                  <circle cx="20" cy="20" r="16" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="4" />
                  <circle
                    cx="20" cy="20" r="16" fill="none"
                    stroke={r.score >= 85 ? "#10b981" : r.score >= 60 ? "#f59e0b" : "#ef4444"}
                    strokeWidth="4"
                    strokeDasharray={`${(r.score / 100) * 100.5} 100.5`}
                    strokeLinecap="round"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white">{r.score}</span>
              </div>
              <span className={`text-xs font-medium ${v.color}`}>{v.label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Token Economy ────────────────────────────────────────────────────────

const TOKEN_DAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];
const TOKEN_DATA = [42000, 58000, 51000, 67000, 74000, 28000, 31000];
const maxTokens = Math.max(...TOKEN_DATA);

function TokenEconomy() {
  return (
    <div>
      <div className="flex items-end gap-1.5 h-24 mb-2">
        {TOKEN_DATA.map((v, i) => (
          <div key={i} className="flex-1 flex flex-col items-center justify-end gap-1">
            <div
              className="w-full rounded-t-sm transition-all"
              style={{
                height: `${(v / maxTokens) * 80}px`,
                background: `linear-gradient(to top, #d946ef, #a21caf)`,
                opacity: 0.7,
              }}
            />
            <span className="text-xs text-slate-400">{TOKEN_DAYS[i]}</span>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3 mt-3">
        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-xs text-slate-400">Bu Ay</p>
          <p className="text-lg font-bold text-fuchsia-400 tabular-nums">351K</p>
          <p className="text-xs text-slate-400">token</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-xs text-slate-400">Maliyet</p>
          <p className="text-lg font-bold text-fuchsia-400 tabular-nums">$12.40</p>
          <p className="text-xs text-slate-400">USD</p>
        </div>
      </div>
    </div>
  );
}

// ─── Prompt Lab ───────────────────────────────────────────────────────────

const PROMPT_PRESETS = [
  { id: "p1", name: "E2E Senaryo Üretimi",  provider: "Groq",   tokens: 847,  quality: 91 },
  { id: "p2", name: "Bug Risk Analizi",     provider: "Gemini", tokens: 1204, quality: 88 },
  { id: "p3", name: "Gereksinim Çıkarımı",  provider: "Groq",   tokens: 623,  quality: 85 },
];

function PromptLab() {
  const [selected, setSelected] = useState("p1");
  const [input, setInput] = useState("");

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        {PROMPT_PRESETS.map((p) => (
          <button
            key={p.id}
            className={`flex-1 text-xs px-2 py-1.5 rounded-lg border transition-colors ${selected === p.id ? "bg-fuchsia-500/15 border-fuchsia-500/40 text-fuchsia-300" : "bg-slate-900/60 border-slate-800 text-slate-400 hover:bg-slate-800"}`}
            onClick={() => setSelected(p.id)}
          >
            {p.name}
          </button>
        ))}
      </div>
      {(() => {
        const preset = PROMPT_PRESETS.find((p) => p.id === selected)!;
        return (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span>Provider: <span className="text-fuchsia-400">{preset.provider}</span></span>
              <span>·</span>
              <span>~{preset.tokens} token</span>
              <span>·</span>
              <span>Kalite: <span className="text-emerald-400">{preset.quality}%</span></span>
            </div>
            <textarea
              className="w-full bg-white/5 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder:text-slate-400 focus:outline-none focus:border-fuchsia-500/40 resize-none"
              rows={3}
              placeholder="Senaryo açıklaması veya gereksinim girin..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button className="w-full px-4 py-2 rounded-xl bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white text-xs font-semibold hover:opacity-90 transition-opacity">
              AI ile Üret →
            </button>
          </div>
        );
      })()}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────

export function IntelligenceProductPage() {
  const { telemetry, loading, isDemo } = useProductTelemetry("intelligence");

  return (
    <div className="flex flex-col gap-6 p-6 pb-12">
      {/* ── Hero ─────────────────────────────────────── */}
      <section className="relative overflow-hidden rounded-3xl border border-fuchsia-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-fuchsia-950/30 p-8 lg:p-10">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-24 -right-24 h-72 w-72 rounded-full bg-fuchsia-500/10 blur-3xl" />
          <div className="absolute -bottom-12 -left-12 h-48 w-48 rounded-full bg-fuchsia-500/8 blur-2xl" />
        </div>
        <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          {/* left: title + CTA */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <span className={`text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-full border ${brand.badge}`}>
                Neurex AI
              </span>
              {isDemo && <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25">Demo Data</span>}
            </div>
            <h1 className="text-4xl lg:text-5xl font-extrabold text-white mb-4 leading-tight">
              Neurex{" "}
              <span className="bg-gradient-to-r from-fuchsia-400 to-purple-400 bg-clip-text text-transparent">Intelligence</span>
              <br />
              AI Kalite Katmanı
            </h1>
            <p className="text-lg text-slate-400 mb-8 leading-relaxed">
              LLM görünürlüğü, provider yönetimi, senaryo üretimi ve
              otomatik kalite denetimi. AI'ı test sürecinin merkezine al.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/task-drafts" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white font-semibold text-sm hover:opacity-90 transition-opacity shadow-lg shadow-fuchsia-500/25">
                AI ile Senaryo Üret →
              </Link>
              <Link href="/ai-agents" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 text-white border border-slate-800 font-medium text-sm hover:bg-slate-700 transition-colors">
                AI Agents
              </Link>
            </div>
          </div>

          {/* right: Living Brain visualization */}
          <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-5">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Neural Activity</p>
            <LivingBrain />
          </div>
        </div>
      </section>

      {/* ── Stats ──────────────────────────────────── */}
      <section>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">AI Metrikleri</p>
        <LiveStatsBar stats={telemetry?.stats ?? []} loading={loading} brandText={brand.text} />
      </section>

      {/* ── Provider + Token ──────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Provider Race Track</h2>
            <span className="text-xs text-slate-400">Groq → Gemini → Ollama fallback aktif</span>
          </div>
          <ProviderRaceTrack />
        </div>

        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-white mb-5">Token Ekonomisi</h2>
          <TokenEconomy />
        </div>
      </div>

      {/* ── Judge + Prompt Lab ────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">LLM-as-Judge Denetimi</h2>
            <span className="text-xs text-slate-400">5 senaryo incelendi</span>
          </div>
          <JudgeStudio />
        </div>

        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold text-white">Prompt Lab</h2>
            <Link href="/task-drafts" className={`text-xs ${brand.text} hover:underline`}>Task Drafts →</Link>
          </div>
          <PromptLab />
        </div>
      </div>

      {/* ── Cortex Otomasyon (Java framework live status) ──────── */}
      <section>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">
          Cortex Otomasyon · Java Framework
        </p>
        <CortexAutomationPanel />
      </section>

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
