"use client";

import { useEffect, useRef, useState, useCallback } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/lib/api";
import { useWebSocket, type WSMessage } from "@/lib/useWebSocket";

// ── Tipler ───────────────────────────────────────────────────────────────────

type LogEntry = {
  timestamp: string;
  phase: string;
  agent: string;
  message: string;
  level: string;
};

type CycleReport = {
  cycle: number;
  scenario_count: number;
  rule_count: number;
  manual_key_count: number;
  code_generated: number;
  improvement_score: number;
};

type PipelineStatus = {
  run_id: string | null;
  phase: string;
  running: boolean;
  current_cycle: number;
  total_cycles: number;
  progress: number;
  started_at: string | null;
  completed_at: string | null;
  logs: LogEntry[];
  cycle_reports: CycleReport[];
  final_report: Record<string, unknown> | null;
};

// ── Yardımcı Bileşenler ───────────────────────────────────────────────────────

const PHASE_LABELS: Record<string, string> = {
  idle: "Bekliyor",
  data_analysis: "Veri Analizi",
  scenario_generation: "Senaryo Üretimi",
  regulation: "Regülasyon",
  automation_decision: "Otomasyon Kararı",
  code_generation: "Kod Üretimi",
  self_improving: "Self-Improving",
  completed: "Tamamlandı",
  failed: "Hata",
};

const AGENT_COLORS: Record<string, string> = {
  "Veri Analisti": "text-blue-500",
  "Senaryo Üretici": "text-purple-500",
  "Regülasyon Ajanı": "text-orange-500",
  "Otomasyon Karar Ajanı": "text-cyan-500",
  "Kod Üretici": "text-green-500",
  "Self-Improving Ajanı": "text-pink-500",
  "Orkestratör": "text-yellow-500",
};

const LEVEL_STYLES: Record<string, string> = {
  info: "text-foreground",
  success: "text-green-500",
  warning: "text-yellow-500",
  error: "text-red-500",
};

function AgentCard({ name, role, model, status }: { name: string; role: string; model: string; status: string }) {
  const isActive = status === "active";
  const isDone = status === "done";
  return (
    <div className={`rounded-lg border p-3 transition-all ${isActive ? "border-accent bg-accent/5" : isDone ? "border-green-500/30 bg-green-500/5" : "border-border"}`}>
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${isActive ? "bg-accent animate-pulse" : isDone ? "bg-green-500" : "bg-muted"}`} />
        <span className="text-xs font-semibold">{name}</span>
      </div>
      <p className="mt-1 text-[10px] text-muted">{role}</p>
      <p className="mt-0.5 text-[10px] font-mono text-muted/70">{model}</p>
    </div>
  );
}

// ── Ana Sayfa ─────────────────────────────────────────────────────────────────

export default function BankingTeamPage() {
  const projectId = useRouteParam("projectId");

  // Form
  const [description, setDescription] = useState("Bankacılık uygulaması");
  const [dbSchema, setDbSchema] = useState("");
  const [apiDocs, setApiDocs] = useState("");
  const [cycles, setCycles] = useState(3);

  // Pipeline durumu
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [logOffset, setLogOffset] = useState(0);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [activeTab, setActiveTab] = useState<"logs" | "report" | "scenarios">("logs");

  const logsEndRef = useRef<HTMLDivElement>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // ── WebSocket: pipeline olaylarini dinle ──────────────────────────
  const handleWsMessage = useCallback((msg: WSMessage) => {
    if (!msg.type.startsWith("pipeline.")) return;

    const p = msg.payload;

    if (msg.type === "pipeline.phase_change") {
      setStatus((prev) => prev ? {
        ...prev,
        phase: p.phase as string,
        progress: p.progress as number,
        current_cycle: p.cycle as number,
        total_cycles: p.total_cycles as number,
        running: !["completed", "failed"].includes(p.phase as string),
      } : prev);
    }

    if (msg.type === "pipeline.log") {
      const entry: LogEntry = {
        timestamp: msg.timestamp ?? new Date().toISOString(),
        phase: p.phase as string,
        agent: (p.agent as string) ?? "",
        message: p.message as string,
        level: p.level as string,
      };
      setLogs((prev) => [...prev, entry]);
    }

    if (msg.type === "pipeline.completed") {
      setStatus((prev) => prev ? {
        ...prev,
        running: false,
        phase: "completed",
        progress: 100,
      } : prev);
      // Fetch full status with final report
      apiFetch<PipelineStatus>("/api/v1/agents/banking/status").then(setStatus).catch(() => {});
    }

    if (msg.type === "pipeline.failed") {
      setStatus((prev) => prev ? {
        ...prev,
        running: false,
        phase: "failed",
      } : prev);
    }
  }, []);

  const { connected: wsConnected } = useWebSocket(handleWsMessage);

  // Ajan durumlarini cikar
  const activeAgent = status?.running ? PHASE_LABELS[status.phase] ?? status.phase : "";
  const getAgentStatus = (agentPhase: string) => {
    if (!status) return "idle";
    if (!status.running && status.phase === "completed") return "done";
    if (status.phase === agentPhase) return "active";
    const phases = ["data_analysis", "scenario_generation", "regulation", "automation_decision", "code_generation", "self_improving"];
    const currentIdx = phases.indexOf(status.phase);
    const agentIdx = phases.indexOf(agentPhase);
    if (currentIdx > agentIdx) return "done";
    return "idle";
  };

  // Polling — fallback when WebSocket is not connected, slower when WS is active
  useEffect(() => {
    if (status?.running) {
      // WebSocket connected: poll every 10s as safety net; not connected: poll every 1.5s
      const interval = wsConnected ? 10000 : 1500;
      pollingRef.current = setInterval(async () => {
        try {
          const data = await apiFetch<{
            running: boolean; phase: string; progress: number;
            current_cycle: number; total_cycles: number;
            logs: LogEntry[]; total_log_count: number;
          }>(`/api/v1/agents/banking/logs?since=${logOffset}`);

          if (data.logs.length > 0) {
            setLogs((prev) => [...prev, ...data.logs]);
            setLogOffset((prev) => prev + data.logs.length);
          }

          if (!data.running) {
            clearInterval(pollingRef.current!);
            const full = await apiFetch<PipelineStatus>("/api/v1/agents/banking/status");
            setStatus(full);
          } else {
            setStatus((prev) => prev ? {
              ...prev,
              running: data.running,
              phase: data.phase,
              progress: data.progress,
              current_cycle: data.current_cycle,
              total_cycles: data.total_cycles,
            } : prev);
          }
        } catch { /* sessiz hata */ }
      }, interval);
    }
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, [status?.running, logOffset, wsConnected]);

  // Log auto-scroll
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  async function startPipeline() {
    try {
      await apiFetch("/api/v1/agents/banking/run", {
        method: "POST",
        json: {
          description,
          db_schema: dbSchema,
          api_docs: apiDocs,
          total_cycles: cycles,
          regulations: ["BDDK", "PCI-DSS", "MASAK", "KYC", "KVKK"],
        },
      });
      setLogs([]);
      setLogOffset(0);
      const s = await apiFetch<PipelineStatus>("/api/v1/agents/banking/status");
      setStatus({ ...s, running: true });
    } catch (e: unknown) {
      alert(`Hata: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  async function cancelPipeline() {
    await apiFetch("/api/v1/agents/banking/cancel", { method: "POST", json: {} });
    const s = await apiFetch<PipelineStatus>("/api/v1/agents/banking/status");
    setStatus(s);
  }

  const finalReport = status?.final_report as Record<string, unknown> | undefined;
  const scenarioList = (finalReport?.scenarios as { list?: unknown[] } | undefined)?.list ?? [];

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col gap-4" data-testid="banking-team-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Banking QA Ekibi</h1>
          <p className="text-xs text-muted">
            6 uzman ajan · Ollama (local) · Sürekli öğrenen
            <span className="ml-2 inline-flex items-center gap-1">
              <span className={`h-1.5 w-1.5 rounded-full ${wsConnected ? "bg-green-500" : "bg-muted"}`} />
              <span className="text-[10px]">{wsConnected ? "Canli" : "Polling"}</span>
            </span>
          </p>
        </div>
        {status?.running && (
          <Button variant="outline" size="sm" onClick={cancelPipeline} className="text-red-500">
            Durdur
          </Button>
        )}
      </div>

      <div className="grid flex-1 grid-cols-[280px_1fr] gap-4 overflow-hidden">
        {/* ── Sol: Ajan Ekibi + Form ─────────────────────────────────── */}
        <aside className="flex flex-col gap-3 overflow-y-auto">
          {/* Ajan kartları */}
          <div className="space-y-2">
            <p className="text-[10px] font-semibold uppercase text-muted tracking-wide">Ajan Ekibi</p>
            <AgentCard name="Veri Analisti" role="DB/API/Log analizi · Business flow" model="qwen2.5:14b" status={getAgentStatus("data_analysis")} />
            <AgentCard name="Senaryo Üretici" role="Pozitif/Negatif/Edge senaryolar" model="qwen2.5:14b" status={getAgentStatus("scenario_generation")} />
            <AgentCard name="Regülasyon Ajanı" role="BDDK · PCI-DSS · MASAK · KYC" model="llama3.1:8b" status={getAgentStatus("regulation")} />
            <AgentCard name="Otomasyon Karar Ajanı" role="UI/API/DB/Manuel matrisi" model="llama3.1:8b" status={getAgentStatus("automation_decision")} />
            <AgentCard name="Kod Üretici" role="BDD · Playwright · pytest" model="qwen2.5-coder:7b" status={getAgentStatus("code_generation")} />
            <AgentCard name="Self-Improving Ajanı" role="Analiz · İyileştirme · Öğrenme" model="qwen2.5:14b" status={getAgentStatus("self_improving")} />
          </div>

          {/* Konfigürasyon formu */}
          {!status?.running && (
            <div className="space-y-2 border-t border-border pt-3">
              <p className="text-[10px] font-semibold uppercase text-muted tracking-wide">Konfigürasyon</p>
              <div>
                <label className="text-xs text-muted">Sistem Açıklaması</label>
                <Input value={description} onChange={(e) => setDescription(e.target.value)} className="mt-1 text-xs" placeholder="Örn: Medifim internet bankacılığı" />
              </div>
              <div>
                <label className="text-xs text-muted">DB Şeması (opsiyonel)</label>
                <textarea
                  value={dbSchema}
                  onChange={(e) => setDbSchema(e.target.value)}
                  className="mt-1 w-full rounded border border-border bg-transparent p-2 text-xs resize-none h-16"
                  placeholder="Tablo isimleri, kolonlar..."
                />
              </div>
              <div>
                <label className="text-xs text-muted">API Dökümantasyonu (opsiyonel)</label>
                <textarea
                  value={apiDocs}
                  onChange={(e) => setApiDocs(e.target.value)}
                  className="mt-1 w-full rounded border border-border bg-transparent p-2 text-xs resize-none h-16"
                  placeholder="Endpoint listesi..."
                />
              </div>
              <div>
                <label className="text-xs text-muted">Döngü Sayısı: {cycles}</label>
                <input type="range" min={1} max={5} value={cycles} onChange={(e) => setCycles(Number(e.target.value))} className="w-full mt-1" />
                <div className="flex justify-between text-[10px] text-muted"><span>1</span><span>5</span></div>
              </div>
              <Button onClick={startPipeline} className="w-full mt-2" data-testid="banking-team-start">
                Ekibi Başlat
              </Button>
            </div>
          )}

          {/* İlerleme */}
          {status?.running && (
            <div className="border-t border-border pt-3 space-y-2">
              <div className="flex justify-between text-xs">
                <span>{PHASE_LABELS[status.phase] ?? status.phase}</span>
                <span className="text-muted">%{status.progress}</span>
              </div>
              <div className="h-1.5 rounded-full bg-border overflow-hidden">
                <div className="h-full bg-accent transition-all duration-500 rounded-full" style={{ width: `${status.progress}%` }} />
              </div>
              <p className="text-[10px] text-muted">
                Döngü {status.current_cycle}/{status.total_cycles}
              </p>
            </div>
          )}
        </aside>

        {/* ── Sağ: Log + Rapor ──────────────────────────────────────── */}
        <div className="flex flex-col overflow-hidden rounded-lg border border-border">
          {/* Tab başlıkları */}
          <div className="flex border-b border-border">
            {(["logs", "report", "scenarios"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-xs font-medium transition-colors ${activeTab === tab ? "border-b-2 border-accent text-accent" : "text-muted hover:text-foreground"}`}
              >
                {tab === "logs" ? "Canlı Log" : tab === "report" ? "Final Rapor" : "Senaryolar"}
                {tab === "logs" && logs.length > 0 && (
                  <span className="ml-1.5 rounded-full bg-accent/20 px-1.5 py-0.5 text-[10px]">{logs.length}</span>
                )}
                {tab === "scenarios" && scenarioList.length > 0 && (
                  <span className="ml-1.5 rounded-full bg-accent/20 px-1.5 py-0.5 text-[10px]">{scenarioList.length}</span>
                )}
              </button>
            ))}
          </div>

          {/* Tab içerikleri */}
          <div className="flex-1 overflow-y-auto p-3">

            {/* Canlı Log */}
            {activeTab === "logs" && (
              <div className="space-y-0.5 font-mono text-xs">
                {logs.length === 0 && !status?.running && (
                  <p className="text-muted text-center py-8">Ekibi başlatarak canlı logları izleyin</p>
                )}
                {logs.map((log, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-muted/50 shrink-0">
                      {new Date(log.timestamp).toLocaleTimeString("tr-TR")}
                    </span>
                    <span className={`shrink-0 ${AGENT_COLORS[log.agent] ?? "text-muted"}`}>
                      [{log.agent}]
                    </span>
                    <span className={LEVEL_STYLES[log.level] ?? "text-foreground"}>
                      {log.message}
                    </span>
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            )}

            {/* Final Rapor */}
            {activeTab === "report" && (
              <div className="space-y-4">
                {!finalReport ? (
                  <p className="text-muted text-center py-8 text-sm">Pipeline tamamlandıktan sonra rapor burada görünecek</p>
                ) : (
                  <>
                    <div className="grid grid-cols-4 gap-3">
                      {[
                        { label: "Toplam Senaryo", value: (finalReport.scenarios as { total?: number } | undefined)?.total ?? 0 },
                        { label: "Regülasyon Kuralı", value: (finalReport.regulation as { total_rules?: number } | undefined)?.total_rules ?? 0 },
                        { label: "Üretilen Kod", value: (finalReport.generated_code as { total_files?: number } | undefined)?.total_files ?? 0 },
                        { label: "Kalite Skoru", value: `${finalReport.average_quality_score ?? 0}/10` },
                      ].map((stat) => (
                        <div key={stat.label} className="rounded-lg border border-border p-3 text-center">
                          <div className="text-xl font-bold">{stat.value}</div>
                          <div className="text-[10px] text-muted mt-0.5">{stat.label}</div>
                        </div>
                      ))}
                    </div>

                    {/* Döngü raporları */}
                    {status?.cycle_reports && status.cycle_reports.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold mb-2">Döngü Özeti</p>
                        <div className="space-y-1">
                          {status.cycle_reports.map((cr) => (
                            <div key={cr.cycle} className="flex justify-between rounded border border-border px-3 py-1.5 text-xs">
                              <span>Döngü {cr.cycle}</span>
                              <span>{cr.scenario_count} senaryo</span>
                              <span>{cr.rule_count} kural</span>
                              <span>{cr.code_generated} kod</span>
                              <span className="text-green-500">{cr.improvement_score}/10</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Öğrenilenler */}
                    {Array.isArray(finalReport.improvements) && finalReport.improvements.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold mb-2">Öğrenilenler</p>
                        <div className="space-y-1">
                          {(finalReport.improvements as string[]).map((imp, i) => (
                            <div key={i} className="rounded border border-border px-3 py-2 text-xs">{imp}</div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* Senaryolar */}
            {activeTab === "scenarios" && (
              <div className="space-y-2">
                {scenarioList.length === 0 ? (
                  <p className="text-muted text-center py-8 text-sm">Pipeline tamamlandıktan sonra senaryolar burada listelenir</p>
                ) : (
                  (scenarioList as Record<string, unknown>[]).map((s, i) => (
                    <div key={i} className="rounded-lg border border-border p-3 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                          s.type === "positive" ? "bg-green-500/10 text-green-500" :
                          s.type === "negative" ? "bg-red-500/10 text-red-500" :
                          "bg-yellow-500/10 text-yellow-500"
                        }`}>{s.type as string}</span>
                        <span className="text-[10px] text-muted">{s.id as string}</span>
                        <span className={`ml-auto text-[10px] font-mono ${s.priority === "P0" ? "text-red-500" : s.priority === "P1" ? "text-orange-500" : "text-muted"}`}>{s.priority as string}</span>
                      </div>
                      <p className="text-xs font-medium">{s.title as string}</p>
                      {s.module ? <p className="text-[10px] text-muted">{s.module as string}</p> : null}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
