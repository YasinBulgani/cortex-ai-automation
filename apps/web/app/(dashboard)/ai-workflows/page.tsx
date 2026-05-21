"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  Ban,
  Clock3,
  Database,
  Download,
  FileText,
  Check,
  RefreshCw,
  Search,
  ShieldCheck,
  X,
  WalletCards,
  Workflow,
} from "lucide-react";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import {
  approveAIWorkflow,
  cancelAIWorkflow,
  downloadAIWorkflowArtifact,
  getAIWorkflow,
  getAIWorkflowArtifacts,
  getAIWorkflowEvents,
  getAIWorkflowHealth,
  listAIWorkflowDeadLetters,
  type AIWorkflowArtifact,
  type AIWorkflowHealthSummary,
  type AIWorkflowStatus,
} from "@/lib/agents-v2-api";
import { cn } from "@/lib/utils";

const STATUS_ORDER = [
  "running",
  "queued",
  "pending_approval",
  "failed",
  "failed_validation",
  "completed",
  "cancelled",
];

function statusClass(status: string) {
  if (status === "completed") return "text-emerald-300 bg-emerald-500/10 border-emerald-500/30";
  if (status === "failed" || status === "failed_validation") return "text-red-300 bg-red-500/10 border-red-500/30";
  if (status === "running") return "text-blue-300 bg-blue-500/10 border-blue-500/30";
  if (status === "pending_approval") return "text-amber-300 bg-amber-500/10 border-amber-500/30";
  if (status === "queued") return "text-cyan-300 bg-cyan-500/10 border-cyan-500/30";
  return "text-slate-300 bg-slate-800/60 border-slate-700";
}

function formatNumber(value: number | null | undefined) {
  return new Intl.NumberFormat("tr-TR").format(value ?? 0);
}

function formatCurrency(value: number | null | undefined) {
  return `$${(value ?? 0).toFixed(4)}`;
}

function formatBytes(bytes: number | null | undefined) {
  const value = bytes ?? 0;
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

function formatAge(seconds: number | null | undefined) {
  if (seconds == null) return "-";
  if (seconds < 60) return `${Math.round(seconds)} sn`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} dk`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)} sa`;
  return `${Math.round(seconds / 86400)} gün`;
}

function formatDate(value: unknown) {
  if (typeof value !== "string") return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function readText(value: unknown, fallback = "-") {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number") return String(value);
  return fallback;
}

function evidenceStatusClass(status: string) {
  if (status === "pass" || status === "passed") return "text-emerald-300 bg-emerald-500/10 border-emerald-500/30";
  if (status === "fail" || status === "failed") return "text-red-300 bg-red-500/10 border-red-500/30";
  if (status === "skipped" || status === "pending") return "text-amber-300 bg-amber-500/10 border-amber-500/30";
  return "text-slate-300 bg-slate-800/60 border-slate-700";
}

function releaseDecisionLabel(value: string | undefined) {
  if (value === "ready_for_operator_approval") return "Operator Onayına Hazır";
  if (value === "needs_external_soak_and_dr_signoff") return "External Soak / DR Bekliyor";
  if (value === "needs_remaining_release_gates") return "Kalan Release Gate'leri Var";
  if (value === "fail") return "Fail";
  return "Bilinmiyor";
}

export default function AIWorkflowsPage() {
  const [data, setData] = useState<AIWorkflowHealthSummary | null>(null);
  const [limit, setLimit] = useState(250);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workflowId, setWorkflowId] = useState("");
  const [selectedWorkflow, setSelectedWorkflow] = useState<AIWorkflowStatus | null>(null);
  const [events, setEvents] = useState<Array<Record<string, unknown>>>([]);
  const [artifacts, setArtifacts] = useState<AIWorkflowArtifact[]>([]);
  const [deadLetters, setDeadLetters] = useState<Array<Record<string, unknown>>>([]);
  const [consoleLoading, setConsoleLoading] = useState(false);
  const [consoleMessage, setConsoleMessage] = useState<string | null>(null);
  const [approvalNote, setApprovalNote] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [next, dlq] = await Promise.all([
        getAIWorkflowHealth(limit),
        listAIWorkflowDeadLetters(Math.min(limit, 100)),
      ]);
      setData(next);
      setDeadLetters(dlq.dead_letters);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bilinmeyen hata");
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    void load();
  }, [load]);

  const statusRows = useMemo(() => {
    if (!data) return [];
    const known = STATUS_ORDER.filter((status) => data.by_status[status]);
    const other = Object.keys(data.by_status)
      .filter((status) => !STATUS_ORDER.includes(status))
      .sort();
    return [...known, ...other].map((status) => ({
      status,
      count: data.by_status[status] ?? 0,
      pct: data.runs_total > 0 ? ((data.by_status[status] ?? 0) / data.runs_total) * 100 : 0,
    }));
  }, [data]);

  const loadWorkflow = useCallback(async (id = workflowId) => {
    const cleanId = id.trim();
    if (!cleanId) {
      setConsoleMessage("Workflow ID gerekli.");
      return;
    }
    setConsoleLoading(true);
    try {
      const [workflow, eventList, artifactList] = await Promise.all([
        getAIWorkflow(cleanId),
        getAIWorkflowEvents(cleanId),
        getAIWorkflowArtifacts(cleanId),
      ]);
      setSelectedWorkflow(workflow);
      setEvents(eventList.events);
      setArtifacts(artifactList.artifacts);
      setConsoleMessage(null);
    } catch (err) {
      setConsoleMessage(err instanceof Error ? err.message : "Workflow yüklenemedi.");
    } finally {
      setConsoleLoading(false);
    }
  }, [workflowId]);

  const approveWorkflow = useCallback(async (decision: "approved" | "rejected") => {
    if (!selectedWorkflow) return;
    setConsoleLoading(true);
    try {
      const response = await approveAIWorkflow(selectedWorkflow.workflow_id, decision, approvalNote || undefined);
      setConsoleMessage(`${decision === "approved" ? "Onaylandı" : "Reddedildi"}: ${response.status}`);
      setApprovalNote("");
      await loadWorkflow(selectedWorkflow.workflow_id);
      await load();
    } catch (err) {
      setConsoleMessage(err instanceof Error ? err.message : "Approval işlemi başarısız.");
    } finally {
      setConsoleLoading(false);
    }
  }, [approvalNote, load, loadWorkflow, selectedWorkflow]);

  const cancelWorkflow = useCallback(async () => {
    if (!selectedWorkflow) return;
    setConsoleLoading(true);
    try {
      const response = await cancelAIWorkflow(selectedWorkflow.workflow_id);
      setConsoleMessage(`İptal edildi: ${response.status}`);
      await loadWorkflow(selectedWorkflow.workflow_id);
      await load();
    } catch (err) {
      setConsoleMessage(err instanceof Error ? err.message : "Cancel işlemi başarısız.");
    } finally {
      setConsoleLoading(false);
    }
  }, [load, loadWorkflow, selectedWorkflow]);

  const workflowTypeRows = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.by_workflow_type)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8);
  }, [data]);

  const eventRows = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.event_counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);
  }, [data]);

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100" data-testid="ai-workflow-health-page">
      <PageHeader
        icon={<Workflow className="h-5 w-5" />}
        title="AI Workflow Health"
        description="Queue, durable run, approval, artifact ve DLQ operasyon görünümü"
        right={
          <div className="flex items-center gap-2">
            <select
              value={limit}
              onChange={(event) => setLimit(Number(event.target.value))}
              className="h-9 rounded-lg border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200"
              aria-label="Örneklem"
            >
              {[100, 250, 500, 1000].map((item) => (
                <option key={item} value={item}>
                  Son {item}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => void load()}
              data-testid="ai-workflow-refresh"
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-blue-500/40 bg-blue-500/10 px-3 text-sm font-medium text-blue-200 transition hover:bg-blue-500/20 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={loading}
            >
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
              Yenile
            </button>
          </div>
        }
      />

      {error && (
        <SectionCard title="Bağlantı Hatası" className="mb-4 border-red-500/30">
          <p className="text-sm text-red-300">{error}</p>
        </SectionCard>
      )}

      {loading && !data ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((item) => (
            <div key={item} className="h-24 animate-pulse rounded-lg border border-slate-800 bg-slate-900" />
          ))}
        </div>
      ) : data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <MetricCard
              icon={<Activity />}
              label="Aktif Run"
              value={formatNumber(data.active_runs)}
              tone="blue"
              testId="ai-workflow-metric-active"
            />
            <MetricCard
              icon={<Clock3 />}
              label="En Eski Aktif"
              value={formatAge(data.oldest_active_seconds)}
              tone="amber"
              testId="ai-workflow-metric-oldest"
            />
            <MetricCard
              icon={<Database />}
              label="Queue Derinliği"
              value={data.queue_depth == null ? "-" : formatNumber(data.queue_depth)}
              tone="cyan"
              testId="ai-workflow-metric-queue"
            />
            <MetricCard
              icon={<AlertTriangle />}
              label="DLQ"
              value={formatNumber(data.dead_letters_total)}
              tone={data.dead_letters_total > 0 ? "red" : "emerald"}
              testId="ai-workflow-metric-dlq"
            />
            <MetricCard
              icon={<ShieldCheck />}
              label="Approval"
              value={formatNumber(data.approval_count)}
              tone="emerald"
              testId="ai-workflow-metric-approval"
            />
            <MetricCard
              icon={<FileText />}
              label="Artifact"
              value={`${formatNumber(data.artifact_count)} / ${formatBytes(data.artifact_bytes)}`}
              tone="violet"
              testId="ai-workflow-metric-artifact"
            />
            <MetricCard
              icon={<WalletCards />}
              label="Maliyet"
              value={formatCurrency(data.cost_usd)}
              tone="slate"
              testId="ai-workflow-metric-cost"
            />
            <MetricCard
              icon={<Workflow />}
              label="LLM Çağrısı"
              value={formatNumber(data.llm_calls_count)}
              tone="slate"
              testId="ai-workflow-metric-llm"
            />
          </div>

          <SectionCard
            title="Release Readiness"
            subtitle="External soak, DR drill ve operator signoff checklist görünümü"
          >
            {data.ops_evidence ? (
              <div className="space-y-4" data-testid="ai-workflow-ops-evidence">
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  <MetricCard
                    icon={<ShieldCheck />}
                    label="Release"
                    value={releaseDecisionLabel(data.ops_evidence.release_decision)}
                    tone={data.ops_evidence.release_decision === "ready_for_operator_approval" ? "emerald" : "amber"}
                  />
                  <MetricCard
                    icon={<Check />}
                    label="Checklist"
                    value={`${data.ops_evidence.checklist?.filter((item) => item.status === "pass" || item.status === "passed").length ?? 0}/${data.ops_evidence.checklist?.length ?? 0}`}
                    tone="slate"
                  />
                  <MetricCard
                    icon={<Activity />}
                    label="LLM Skoru"
                    value={data.ops_evidence.llm_quality_score != null ? data.ops_evidence.llm_quality_score.toFixed(2) : "-"}
                    tone="slate"
                  />
                  <MetricCard
                    icon={<Clock3 />}
                    label="Kanıt Zamanı"
                    value={formatDate(data.ops_evidence.generated_at)}
                    tone="slate"
                  />
                </div>

                <div className="grid gap-3 lg:grid-cols-2">
                  <div className="space-y-2">
                    {(data.ops_evidence.checklist ?? []).map((item) => (
                      <div
                        key={item.id}
                        className="flex items-start justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-3"
                      >
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-slate-100">{item.label}</div>
                          <div className="mt-1 text-xs text-slate-400">{item.detail}</div>
                        </div>
                        <span className={cn("shrink-0 rounded-full border px-2 py-1 text-[11px] font-medium uppercase", evidenceStatusClass(item.status))}>
                          {item.status}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="space-y-3">
                    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
                      <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Operator Next Steps</div>
                      <div className="space-y-1 text-sm text-slate-300">
                        {(data.ops_evidence.operator_next_steps ?? []).length > 0 ? (
                          (data.ops_evidence.operator_next_steps ?? []).map((step, index) => (
                            <div key={`${index}-${step}`} className="flex gap-2">
                              <span className="text-slate-500">{index + 1}.</span>
                              <span>{step}</span>
                            </div>
                          ))
                        ) : (
                          <div className="text-slate-500">Ek operator adımı yok.</div>
                        )}
                      </div>
                    </div>

                    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
                      <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Kanıt Dosyası</div>
                      <div className="font-mono text-xs text-slate-400 break-all">
                        {data.ops_evidence.report_path || "-"}
                      </div>
                    </div>

                    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
                      <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Son Soak Kanıtı</div>
                      {data.ops_evidence.soak_report ? (
                        <div className="space-y-1 text-xs text-slate-300">
                          <div>Profil: <span className="font-mono text-slate-100">{data.ops_evidence.soak_report.profile || "-"}</span></div>
                          <div>Run: {formatNumber(data.ops_evidence.soak_report.runs_total)}</div>
                          <div>DLQ: {formatNumber(data.ops_evidence.soak_report.dead_letters_total)}</div>
                          <div>Artifact: {formatNumber(data.ops_evidence.soak_report.artifact_count)}</div>
                          <div>Maliyet: {formatCurrency(data.ops_evidence.soak_report.cost_usd)}</div>
                          <div className="break-all font-mono text-[11px] text-slate-500">{data.ops_evidence.soak_report.path || "-"}</div>
                        </div>
                      ) : (
                        <div className="text-xs text-slate-500">Henüz soak kanıtı yok.</div>
                      )}
                    </div>

                    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
                      <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Son DR Manifest</div>
                      {data.ops_evidence.dr_manifest ? (
                        <div className="space-y-1 text-xs text-slate-300">
                          <div>Zaman: {formatDate(data.ops_evidence.dr_manifest.created_at)}</div>
                          <div>Restore DB: <span className="font-mono text-slate-100">{data.ops_evidence.dr_manifest.restore_db || "-"}</span></div>
                          <div>Run / Event / Artifact: {formatNumber(data.ops_evidence.dr_manifest.runs)} / {formatNumber(data.ops_evidence.dr_manifest.events)} / {formatNumber(data.ops_evidence.dr_manifest.artifacts)}</div>
                          <div>Artifact File: {formatNumber(data.ops_evidence.dr_manifest.artifact_files)}</div>
                          <div className="break-all font-mono text-[11px] text-slate-500">{data.ops_evidence.dr_manifest.path || "-"}</div>
                        </div>
                      ) : (
                        <div className="text-xs text-amber-300">Henüz DR manifest kanıtı yok.</div>
                      )}
                    </div>

                    {data.ops_evidence.failed_required_checks && data.ops_evidence.failed_required_checks.length > 0 && (
                      <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-300">
                        Failed required checks: {data.ops_evidence.failed_required_checks.join(", ")}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                Henüz release evidence pack bulunamadı.
              </div>
            )}
          </SectionCard>

          <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
            <SectionCard
              title="Run Durumları"
              subtitle={`${formatNumber(data.runs_total)} run / ${formatNumber(data.sample_size)} örneklem`}
            >
              <div className="space-y-3">
                {statusRows.length === 0 ? (
                  <p className="text-sm text-slate-500">Run yok.</p>
                ) : (
                  statusRows.map((row) => (
                    <div key={row.status} className="space-y-1.5" data-testid={`ai-workflow-status-${row.status}`}>
                      <div className="flex items-center justify-between gap-3">
                        <span className={cn("rounded-md border px-2 py-1 text-xs font-medium", statusClass(row.status))}>
                          {row.status}
                        </span>
                        <span className="text-sm font-semibold text-white">{formatNumber(row.count)}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                        <div className="h-full rounded-full bg-blue-400" style={{ width: `${Math.max(row.pct, 2)}%` }} />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </SectionCard>

            <SectionCard title="Workflow Tipleri">
              <div className="space-y-2">
                {workflowTypeRows.length === 0 ? (
                  <p className="text-sm text-slate-500">Tip verisi yok.</p>
                ) : (
                  workflowTypeRows.map(([name, count]) => (
                    <div
                      key={name}
                      className="flex items-center justify-between rounded-lg border border-slate-800 px-3 py-2"
                      data-testid={`ai-workflow-type-${name}`}
                    >
                      <span className="font-mono text-xs text-slate-300">{name}</span>
                      <span className="text-sm font-semibold text-white">{formatNumber(count)}</span>
                    </div>
                  ))
                )}
              </div>
            </SectionCard>
          </div>

          <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
            <SectionCard title="Son DLQ Kayıtları" subtitle={`${formatNumber(data.dead_letters_total)} toplam`}>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                    <tr>
                      <th className="px-3 py-2 text-left">Zaman</th>
                      <th className="px-3 py-2 text-left">Queue</th>
                      <th className="px-3 py-2 text-left">Run</th>
                      <th className="px-3 py-2 text-left">Sebep</th>
                    </tr>
                  </thead>
                  <tbody>
                    {deadLetters.length === 0 ? (
                      <tr>
                        <td className="px-3 py-5 text-center text-slate-500" colSpan={4}>
                          DLQ temiz.
                        </td>
                      </tr>
                    ) : (
                      deadLetters.map((item, index) => (
                        <tr
                          key={`${readText(item.dead_letter_id, String(index))}`}
                          className="border-b border-slate-800/70"
                          data-testid="ai-workflow-dlq-row"
                        >
                          <td className="px-3 py-2 text-slate-400">{formatDate(item.created_at)}</td>
                          <td className="px-3 py-2 font-mono text-xs text-slate-300">{readText(item.queue_name)}</td>
                          <td className="px-3 py-2 font-mono text-xs text-slate-400">{readText(item.run_id)}</td>
                          <td className="px-3 py-2 text-slate-300">{readText(item.reason)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </SectionCard>

            <SectionCard title="Olay Yoğunluğu">
              <div className="space-y-2">
                {eventRows.length === 0 ? (
                  <p className="text-sm text-slate-500">Event yok.</p>
                ) : (
                  eventRows.map(([name, count]) => (
                    <div key={name} className="flex items-center justify-between gap-3" data-testid={`ai-workflow-event-${name}`}>
                      <span className="truncate font-mono text-xs text-slate-300">{name}</span>
                      <span className="rounded-md bg-slate-800 px-2 py-1 text-xs font-semibold text-slate-100">
                        {formatNumber(count)}
                      </span>
                    </div>
                  ))
                )}
                <div className="border-t border-slate-800 pt-3 text-xs text-slate-500">
                  Token: {formatNumber(data.tokens_used)} / Güncelleme: {formatDate(data.generated_at)}
                </div>
              </div>
            </SectionCard>
          </div>

          <SectionCard
            title="Workflow Console"
            subtitle="Tekil run detay, approval, cancel ve artifact aksiyonları"
          >
            <div className="space-y-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-center">
                <input
                  value={workflowId}
                  onChange={(event) => setWorkflowId(event.target.value)}
                  placeholder="Workflow ID"
                  className="h-10 min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm text-slate-100 outline-none transition focus:border-blue-500"
                  data-testid="ai-workflow-console-input"
                />
                <button
                  type="button"
                  onClick={() => void loadWorkflow()}
                  disabled={consoleLoading}
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-blue-500/40 bg-blue-500/10 px-3 text-sm font-medium text-blue-200 transition hover:bg-blue-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                  data-testid="ai-workflow-console-load"
                >
                  <Search className="h-4 w-4" />
                  Yükle
                </button>
              </div>

              {consoleMessage && (
                <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200" data-testid="ai-workflow-console-message">
                  {consoleMessage}
                </div>
              )}

              {selectedWorkflow && (
                <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
                  <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4" data-testid="ai-workflow-console-detail">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-mono text-xs text-slate-500">{selectedWorkflow.workflow_id}</p>
                        <h3 className="mt-1 text-base font-semibold text-white">{selectedWorkflow.project_id}</h3>
                      </div>
                      <span className={cn("rounded-md border px-2 py-1 text-xs font-medium", statusClass(selectedWorkflow.status))}>
                        {selectedWorkflow.status}
                      </span>
                    </div>
                    <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                      <Detail label="Input" value={selectedWorkflow.input_source} />
                      <Detail label="Events" value={formatNumber(selectedWorkflow.event_count)} />
                      <Detail label="Artifacts" value={formatNumber(selectedWorkflow.artifact_count)} />
                      <Detail label="Approvals" value={formatNumber(selectedWorkflow.approval_count)} />
                      <Detail label="Cost" value={formatCurrency(selectedWorkflow.cost_usd)} />
                      <Detail label="Tokens" value={formatNumber(selectedWorkflow.tokens_used)} />
                    </div>
                    {selectedWorkflow.error && (
                      <p className="mt-3 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
                        {selectedWorkflow.error}
                      </p>
                    )}
                    <div className="mt-4 space-y-2">
                      <input
                        value={approvalNote}
                        onChange={(event) => setApprovalNote(event.target.value)}
                        placeholder="Approval notu"
                        className="h-9 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 text-sm text-slate-100 outline-none focus:border-blue-500"
                        data-testid="ai-workflow-approval-note"
                      />
                      <div className="grid grid-cols-3 gap-2">
                        <ActionButton
                          onClick={() => void approveWorkflow("approved")}
                          disabled={consoleLoading}
                          tone="green"
                          icon={<Check />}
                          label="Approve"
                          testId="ai-workflow-approve"
                        />
                        <ActionButton
                          onClick={() => void approveWorkflow("rejected")}
                          disabled={consoleLoading}
                          tone="amber"
                          icon={<X />}
                          label="Reject"
                          testId="ai-workflow-reject"
                        />
                        <ActionButton
                          onClick={() => void cancelWorkflow()}
                          disabled={consoleLoading}
                          tone="red"
                          icon={<Ban />}
                          label="Cancel"
                          testId="ai-workflow-cancel"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 lg:grid-cols-2">
                    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
                      <div className="mb-3 flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-white">Artifacts</h3>
                        <span className="text-xs text-slate-500">{formatNumber(artifacts.length)}</span>
                      </div>
                      <div className="max-h-72 space-y-2 overflow-auto pr-1">
                        {artifacts.length === 0 ? (
                          <p className="text-sm text-slate-500">Artifact yok.</p>
                        ) : artifacts.map((artifact) => (
                          <div key={artifact.artifact_id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 px-3 py-2" data-testid="ai-workflow-artifact-row">
                            <div className="min-w-0">
                              <p className="truncate text-sm font-medium text-slate-200">{artifact.name}</p>
                              <p className="font-mono text-xs text-slate-500">{artifact.kind} · {formatBytes(artifact.size_bytes)}</p>
                            </div>
                            <button
                              type="button"
                              aria-label={`${artifact.name} indir`}
                              onClick={() => void downloadAIWorkflowArtifact(selectedWorkflow.workflow_id, artifact)}
                              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700 text-slate-300 transition hover:border-blue-500 hover:text-blue-200"
                              data-testid="ai-workflow-artifact-download"
                            >
                              <Download className="h-4 w-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
                      <div className="mb-3 flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-white">Events</h3>
                        <span className="text-xs text-slate-500">{formatNumber(events.length)}</span>
                      </div>
                      <div className="max-h-72 space-y-2 overflow-auto pr-1">
                        {events.length === 0 ? (
                          <p className="text-sm text-slate-500">Event yok.</p>
                        ) : events.slice(-12).reverse().map((event, index) => (
                          <div key={`${readText(event.event_type, "event")}-${index}`} className="rounded-lg border border-slate-800 px-3 py-2" data-testid="ai-workflow-event-row">
                            <div className="flex items-center justify-between gap-3">
                              <span className="font-mono text-xs text-blue-200">{readText(event.event_type)}</span>
                              <span className="text-xs text-slate-500">{formatDate(event.timestamp)}</span>
                            </div>
                            {event.message ? <p className="mt-1 text-sm text-slate-300">{readText(event.message)}</p> : null}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </SectionCard>
        </div>
      ) : null}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-900/60 px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-slate-100">{value}</p>
    </div>
  );
}

function ActionButton({
  onClick,
  disabled,
  tone,
  icon,
  label,
  testId,
}: {
  onClick: () => void;
  disabled: boolean;
  tone: "green" | "amber" | "red";
  icon: ReactNode;
  label: string;
  testId: string;
}) {
  const toneClass = {
    green: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20",
    amber: "border-amber-500/40 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20",
    red: "border-red-500/40 bg-red-500/10 text-red-200 hover:bg-red-500/20",
  }[tone];

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn("inline-flex h-9 items-center justify-center gap-2 rounded-lg border px-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-60", toneClass)}
      data-testid={testId}
    >
      <span className="[&>svg]:h-4 [&>svg]:w-4">{icon}</span>
      <span className="truncate">{label}</span>
    </button>
  );
}

function MetricCard({
  icon,
  label,
  value,
  tone,
  testId,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  tone: "blue" | "amber" | "cyan" | "red" | "emerald" | "violet" | "slate";
  testId?: string;
}) {
  const toneClass = {
    blue: "border-blue-500/30 text-blue-200 bg-blue-500/10",
    amber: "border-amber-500/30 text-amber-200 bg-amber-500/10",
    cyan: "border-cyan-500/30 text-cyan-200 bg-cyan-500/10",
    red: "border-red-500/30 text-red-200 bg-red-500/10",
    emerald: "border-emerald-500/30 text-emerald-200 bg-emerald-500/10",
    violet: "border-violet-500/30 text-violet-200 bg-violet-500/10",
    slate: "border-slate-700 text-slate-200 bg-slate-900",
  }[tone];

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-4" data-testid={testId}>
      <div className="flex items-center justify-between gap-3">
        <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg border", toneClass)}>
          <span className="[&>svg]:h-4 [&>svg]:w-4">{icon}</span>
        </div>
        <span className="text-right text-2xl font-semibold text-white">{value}</span>
      </div>
      <p className="mt-3 text-xs font-medium uppercase tracking-normal text-slate-500">{label}</p>
    </div>
  );
}
