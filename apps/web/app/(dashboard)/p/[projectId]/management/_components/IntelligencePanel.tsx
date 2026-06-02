"use client";

import { useEffect, useState, useCallback } from "react";

// ── Tip tanımları ────────────────────────────────────────────────────────────

interface ETAPrediction {
  total_cases: number;
  completed_cases: number;
  remaining_cases: number;
  elapsed_hours: number;
  velocity_per_hour: number;
  overall_velocity: number;
  eta_hours: number | null;
  predicted_completion: string | null;
  confidence: number;
  on_track: boolean;
  risk_level: "low" | "medium" | "high" | "critical";
  message: string;
}

interface TesterProfile {
  user_id: string;
  assigned_count: number;
  completed_count: number;
  remaining_count: number;
  avg_duration_seconds: number;
  velocity_per_hour: number;
  pass_rate: number;
  blocked_rate: number;
  is_bottleneck: boolean;
  last_activity_at: string | null;
  inactive_minutes: number;
}

interface Anomaly {
  severity: "warning" | "critical";
  type: string;
  title: string;
  detail: string;
  run_case_id: string | null;
  user_id: string | null;
  suggested_action: string;
}

interface CaseRiskScore {
  case_id: string;
  case_key: string;
  title: string;
  risk_score: number;
  recommendation: "run_first" | "run_normal" | "deprioritize";
  last_status: string | null;
}

interface RunIntelligenceReport {
  run_id: string;
  run_name: string;
  generated_at: string;
  eta: ETAPrediction;
  testers: TesterProfile[];
  anomalies: Anomaly[];
  risk_sorted_remaining: CaseRiskScore[];
  summary_health: "healthy" | "at_risk" | "critical";
  health_score: number;
}

// ── Renk yardımcıları ────────────────────────────────────────────────────────

const riskColor: Record<string, string> = {
  low: "text-emerald-400",
  medium: "text-amber-400",
  high: "text-orange-400",
  critical: "text-rose-400",
};

const healthBg: Record<string, string> = {
  healthy: "bg-emerald-500/15 border-emerald-500/30",
  at_risk: "bg-amber-500/15 border-amber-500/30",
  critical: "bg-rose-500/15 border-rose-500/30",
};

const healthText: Record<string, string> = {
  healthy: "text-emerald-400",
  at_risk: "text-amber-400",
  critical: "text-rose-400",
};

const healthLabel: Record<string, string> = {
  healthy: "SAĞLIKLI",
  at_risk: "RİSKLİ",
  critical: "KRİTİK",
};

// ── Yardımcı bileşenler ──────────────────────────────────────────────────────

function HealthGauge({ score }: { score: number }) {
  const color =
    score >= 75 ? "#10b981" : score >= 45 ? "#f59e0b" : "#f43f5e";
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="100" height="100" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#1e293b" strokeWidth="10" />
        <circle
          cx="50" cy="50" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
        <text x="50" y="54" textAnchor="middle" fill={color} fontSize="18" fontWeight="bold">
          {score.toFixed(0)}
        </text>
      </svg>
      <span className="text-xs text-slate-400">Sağlık Skoru</span>
    </div>
  );
}

function VelocityBar({ current, overall }: { current: number; overall: number }) {
  const max = Math.max(current, overall, 0.1);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-slate-400">
        <span>Anlık hız</span>
        <span className="text-white font-mono">{current.toFixed(1)}/sa</span>
      </div>
      <div className="h-2 rounded-full bg-slate-700 overflow-hidden">
        <div
          className="h-full rounded-full bg-violet-500 transition-all duration-700"
          style={{ width: `${Math.min(100, (current / max) * 100)}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-slate-400">
        <span>Genel ort.</span>
        <span className="font-mono">{overall.toFixed(1)}/sa</span>
      </div>
      <div className="h-2 rounded-full bg-slate-700 overflow-hidden">
        <div
          className="h-full rounded-full bg-slate-500 transition-all duration-700"
          style={{ width: `${Math.min(100, (overall / max) * 100)}%` }}
        />
      </div>
    </div>
  );
}

function TesterRow({ t }: { t: TesterProfile }) {
  const pct = t.assigned_count > 0 ? (t.completed_count / t.assigned_count) * 100 : 0;
  const isUnassigned = t.user_id === "__unassigned__";

  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-xs">
        <span className={`font-medium truncate max-w-[140px] ${t.is_bottleneck ? "text-amber-400" : "text-slate-300"}`}>
          {isUnassigned ? "⚠ Atanmamış" : `${t.user_id.slice(0, 8)}…`}
          {t.is_bottleneck && <span className="ml-1 text-amber-500">⚡</span>}
        </span>
        <span className="text-slate-400 font-mono">{t.completed_count}/{t.assigned_count}</span>
      </div>
      <div className="h-1.5 rounded-full bg-slate-700 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${
            t.is_bottleneck ? "bg-amber-500" : "bg-teal-500"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex gap-3 text-[10px] text-slate-500">
        <span>{t.velocity_per_hour.toFixed(1)}/sa</span>
        <span>pass {(t.pass_rate * 100).toFixed(0)}%</span>
        {t.inactive_minutes > 20 && (
          <span className="text-amber-500">{Math.round(t.inactive_minutes)}dk inaktif</span>
        )}
      </div>
    </div>
  );
}

function AnomalyCard({ a }: { a: Anomaly }) {
  return (
    <div
      className={`rounded-lg border p-3 space-y-1 ${
        a.severity === "critical"
          ? "border-rose-500/40 bg-rose-500/10"
          : "border-amber-500/30 bg-amber-500/10"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className={`text-sm font-semibold ${a.severity === "critical" ? "text-rose-400" : "text-amber-400"}`}>
          {a.severity === "critical" ? "🚨" : "⚠️"} {a.title}
        </span>
      </div>
      <p className="text-xs text-slate-300">{a.detail}</p>
      {a.suggested_action && (
        <p className="text-xs text-slate-400 italic">→ {a.suggested_action}</p>
      )}
    </div>
  );
}

function RiskCaseRow({ c, index }: { c: CaseRiskScore; index: number }) {
  const recBg: Record<string, string> = {
    run_first: "border-l-rose-500",
    run_normal: "border-l-amber-500",
    deprioritize: "border-l-slate-600",
  };
  const recLabel: Record<string, string> = {
    run_first: "Önce çalıştır",
    run_normal: "Normal sıra",
    deprioritize: "Ertelenebilir",
  };

  return (
    <div className={`flex items-center gap-3 py-2 border-l-2 pl-3 ${recBg[c.recommendation]}`}>
      <span className="text-slate-500 text-xs w-4">{index + 1}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-400">{c.case_key}</span>
          <span className="text-xs text-slate-300 truncate">{c.title}</span>
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <div className="h-1 w-16 rounded-full bg-slate-700 overflow-hidden">
            <div
              className="h-full rounded-full bg-rose-500"
              style={{ width: `${c.risk_score * 100}%` }}
            />
          </div>
          <span className="text-[10px] text-slate-400">{(c.risk_score * 100).toFixed(0)}% risk</span>
          <span className="text-[10px] text-slate-500">{recLabel[c.recommendation]}</span>
        </div>
      </div>
      {c.last_status && (
        <span
          className={`text-[10px] px-1.5 py-0.5 rounded font-mono uppercase ${
            c.last_status === "pass"
              ? "bg-emerald-500/20 text-emerald-400"
              : c.last_status === "fail"
              ? "bg-rose-500/20 text-rose-400"
              : "bg-amber-500/20 text-amber-400"
          }`}
        >
          {c.last_status}
        </span>
      )}
    </div>
  );
}

// ── Ana bileşen ──────────────────────────────────────────────────────────────

interface IntelligencePanelProps {
  projectId: string;
  runId: string;
  refreshIntervalMs?: number;
}

export function IntelligencePanel({
  projectId,
  runId,
  refreshIntervalMs = 30_000,
}: IntelligencePanelProps) {
  const [report, setReport] = useState<RunIntelligenceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "testers" | "queue" | "anomalies">(
    "overview"
  );

  const fetchReport = useCallback(async () => {
    try {
      const res = await fetch(
        `/api/v1/test-management/projects/${projectId}/intelligence/runs/${runId}`
      );
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data: RunIntelligenceReport = await res.json();
      setReport(data);
      setLastRefresh(new Date());
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Veri alınamadı");
    } finally {
      setLoading(false);
    }
  }, [projectId, runId]);

  useEffect(() => {
    fetchReport();
    const id = setInterval(fetchReport, refreshIntervalMs);
    return () => clearInterval(id);
  }, [fetchReport, refreshIntervalMs]);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-900 p-6 flex items-center justify-center h-48">
        <div className="flex flex-col items-center gap-2 text-slate-500">
          <div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Zeka motoru analiz ediyor…</span>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-900 p-6 text-center text-slate-500 text-sm">
        {error ?? "Rapor oluşturulamadı"}
      </div>
    );
  }

  const { eta, testers, anomalies, risk_sorted_remaining: riskQueue } = report;
  const criticalAnomalies = anomalies.filter((a) => a.severity === "critical");
  const warnAnomalies = anomalies.filter((a) => a.severity === "warning");

  const tabs = [
    { id: "overview" as const, label: "Genel", badge: null },
    {
      id: "anomalies" as const,
      label: "Anomaliler",
      badge: criticalAnomalies.length > 0 ? criticalAnomalies.length : null,
    },
    { id: "testers" as const, label: "Testerlar", badge: null },
    { id: "queue" as const, label: "Risk Sırası", badge: null },
  ];

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 overflow-hidden">
      {/* Başlık */}
      <div className={`px-5 py-3 border-b border-slate-700 ${healthBg[report.summary_health]}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-slate-200">⚡ Test Zekası</span>
            <span
              className={`text-xs font-bold px-2 py-0.5 rounded-full border ${healthBg[report.summary_health]} ${healthText[report.summary_health]}`}
            >
              {healthLabel[report.summary_health]}
            </span>
            {criticalAnomalies.length > 0 && (
              <span className="text-xs bg-rose-500 text-white px-2 py-0.5 rounded-full font-bold animate-pulse">
                {criticalAnomalies.length} KRİTİK
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {lastRefresh && (
              <span className="text-[10px] text-slate-500">
                {lastRefresh.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
            )}
            <button
              onClick={fetchReport}
              className="text-xs text-slate-400 hover:text-white transition-colors"
              title="Yenile"
            >
              ↺
            </button>
          </div>
        </div>
      </div>

      {/* Sekme navigasyonu */}
      <div className="flex border-b border-slate-700 bg-slate-800/50">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-xs font-medium transition-colors relative ${
              activeTab === tab.id
                ? "text-white border-b-2 border-violet-500"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab.label}
            {tab.badge !== null && (
              <span className="ml-1.5 bg-rose-500 text-white text-[10px] px-1.5 py-0.5 rounded-full">
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* İçerik */}
      <div className="p-4">
        {/* ── Genel Bakış ── */}
        {activeTab === "overview" && (
          <div className="space-y-5">
            {/* ETA + Sağlık */}
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col items-center justify-center bg-slate-800/60 rounded-lg p-4 gap-2">
                <HealthGauge score={report.health_score} />
              </div>
              <div className="bg-slate-800/60 rounded-lg p-4 space-y-3">
                <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">ETA</p>
                {eta.eta_hours !== null ? (
                  <>
                    <p className={`text-2xl font-bold ${riskColor[eta.risk_level]}`}>
                      {eta.eta_hours < 1
                        ? `${Math.round(eta.eta_hours * 60)}dk`
                        : `${eta.eta_hours.toFixed(1)}sa`}
                    </p>
                    <p className="text-xs text-slate-400">{eta.message}</p>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span>Güven: {(eta.confidence * 100).toFixed(0)}%</span>
                      <div className="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-violet-500 rounded-full"
                          style={{ width: `${eta.confidence * 100}%` }}
                        />
                      </div>
                    </div>
                  </>
                ) : (
                  <p className="text-slate-400 text-sm">{eta.message}</p>
                )}
              </div>
            </div>

            {/* İlerleme */}
            <div className="bg-slate-800/60 rounded-lg p-4 space-y-3">
              <div className="flex justify-between text-xs text-slate-400">
                <span>İlerleme</span>
                <span className="font-mono text-white">
                  {eta.completed_cases} / {eta.total_cases}
                </span>
              </div>
              <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-violet-600 to-teal-500 transition-all duration-700"
                  style={{
                    width: `${eta.total_cases > 0 ? (eta.completed_cases / eta.total_cases) * 100 : 0}%`,
                  }}
                />
              </div>
              <VelocityBar current={eta.velocity_per_hour} overall={eta.overall_velocity} />
            </div>

            {/* Özet anomaliler */}
            {anomalies.length > 0 && (
              <div className="space-y-2">
                {criticalAnomalies.slice(0, 2).map((a, i) => (
                  <AnomalyCard key={i} a={a} />
                ))}
                {warnAnomalies.slice(0, 1).map((a, i) => (
                  <AnomalyCard key={`w${i}`} a={a} />
                ))}
                {anomalies.length > 3 && (
                  <button
                    onClick={() => setActiveTab("anomalies")}
                    className="text-xs text-violet-400 hover:text-violet-300"
                  >
                    +{anomalies.length - 3} anomali daha →
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Anomaliler ── */}
        {activeTab === "anomalies" && (
          <div className="space-y-3">
            {anomalies.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-sm">
                ✅ Anomali tespit edilmedi
              </div>
            ) : (
              anomalies.map((a, i) => <AnomalyCard key={i} a={a} />)
            )}
          </div>
        )}

        {/* ── Testerlar ── */}
        {activeTab === "testers" && (
          <div className="space-y-4">
            {testers.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-sm">
                Tester ataması yapılmamış
              </div>
            ) : (
              testers.map((t, i) => <TesterRow key={t.user_id + i} t={t} />)
            )}
          </div>
        )}

        {/* ── Risk Sırası ── */}
        {activeTab === "queue" && (
          <div className="space-y-1">
            <p className="text-xs text-slate-500 mb-3">
              Kalan case'ler: failure geçmişi + önem × yakınlık skoru ile sıralandı
            </p>
            {riskQueue.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-sm">
                Bekleyen case yok
              </div>
            ) : (
              riskQueue.map((c, i) => <RiskCaseRow key={c.case_id} c={c} index={i} />)
            )}
          </div>
        )}
      </div>
    </div>
  );
}
