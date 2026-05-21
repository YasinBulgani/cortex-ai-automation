/**
 * Sıfır Bilgi — Zero-Knowledge Test Generation Sayfası
 *
 * Kullanıcı sadece URL, PDF, Swagger, Jira veya metin verir;
 * AI 9 ajanlı pipeline otomatik çalışır ve test paketi üretir.
 *
 * Akış:
 *  1. Kullanıcı kaynak seçer + yükler
 *  2. Backend'e POST /api/v1/ai/workflows → workflow_id + stream_url
 *  3. EventSource ile SSE bağlan → her ajan eventini canlı göster
 *  4. Bitiminde özet + üretilen senaryolar + kod path'leri + raporlar
 */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";

import {
  createAIWorkflow,
  downloadAIWorkflowArtifact,
  getAIWorkflow,
  getAIWorkflowArtifacts,
  approveAIWorkflow,
  subscribeAgentRun,
  cancelAIWorkflow,
  uploadSourceFile,
  type AIWorkflowArtifact,
  type AIWorkflowStatus,
  type AgentStreamEvent,
  type InputSource,
  type UploadSourceFileResponse,
} from "@/lib/agents-v2-api";

type SourceMode = "url" | "text" | "swagger" | "file";

interface AgentStatus {
  name: string;
  label: string;
  status: "pending" | "running" | "done" | "error";
  startedAt?: string;
  endedAt?: string;
  costSoFar?: number;
  tokensSoFar?: number;
  errorMessage?: string;
}

const AGENT_ORDER: { name: string; label: string }[] = [
  { name: "analyst", label: "1 — Analyst (Dokümanı analiz ediyor)" },
  { name: "explorer", label: "2 — Explorer (Uygulamayı geziyor)" },
  { name: "locator", label: "3 — Locator (Seçicileri üretiyor)" },
  { name: "scenario", label: "4 — Scenario (Gherkin yazıyor)" },
  { name: "coder", label: "5 — Coder (Playwright kodu üretiyor)" },
  { name: "runner", label: "6 — Runner (Testleri koşturuyor)" },
  { name: "healer", label: "7 — Healer (Kırıkları onarıyor)" },
  { name: "reviewer", label: "8 — Reviewer (Kaliteyi değerlendiriyor)" },
  { name: "reporter", label: "9 — Reporter (Yönetim raporu)" },
];

function makeInitialAgents(): AgentStatus[] {
  return AGENT_ORDER.map((a) => ({ ...a, status: "pending" }));
}


export default function SıfırBilgiPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params?.projectId || "default";

  const [sourceMode, setSourceMode] = useState<SourceMode>("url");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [swaggerUrl, setSwaggerUrl] = useState("");
  const [extraContext, setExtraContext] = useState("");
  const [maxPages, setMaxPages] = useState(15);
  const [enableAiXpath, setEnableAiXpath] = useState(false);
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<UploadSourceFileResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [approvalBusy, setApprovalBusy] = useState(false);

  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string>("idle");
  const [agents, setAgents] = useState<AgentStatus[]>(makeInitialAgents());
  const [events, setEvents] = useState<AgentStreamEvent[]>([]);
  const [finalStatus, setFinalStatus] = useState<AIWorkflowStatus | null>(null);
  const [artifacts, setArtifacts] = useState<AIWorkflowArtifact[]>([]);
  const [error, setError] = useState<string | null>(null);

  const unsubRef = useRef<(() => void) | null>(null);

  useEffect(() => () => {
    unsubRef.current?.();
  }, []);

  const refreshFinalStatus = useCallback(async (workflowId: string) => {
    try {
      const [status, artifactList] = await Promise.all([
        getAIWorkflow(workflowId),
        getAIWorkflowArtifacts(workflowId),
      ]);
      setRunStatus(status.status);
      setArtifacts(artifactList.artifacts);
      if (["completed", "failed", "failed_validation", "cancelled"].includes(status.status)) {
        setFinalStatus(status);
      }
    } catch (e) {
      // ignore
    }
  }, []);

  const attachWorkflowStream = useCallback((workflowId: string) => {
    unsubRef.current?.();
    const unsub = subscribeAgentRun(
      workflowId,
      (evt) => {
        setEvents((prev) => [...prev, evt]);

        if (evt.event_type === "started" || evt.event_type === "progress") {
          setRunStatus("running");
        }

        if (evt.event_type === "agent_started" && evt.agent_name) {
          setAgents((prev) =>
            prev.map((a) =>
              a.name === evt.agent_name
                ? { ...a, status: "running", startedAt: evt.timestamp }
                : a,
            ),
          );
        } else if (evt.event_type === "agent_finished" && evt.agent_name) {
          setAgents((prev) =>
            prev.map((a) =>
              a.name === evt.agent_name
                ? {
                    ...a,
                    status: "done",
                    endedAt: evt.timestamp,
                    costSoFar: (evt.data?.cost_so_far as number) ?? a.costSoFar,
                    tokensSoFar: (evt.data?.tokens_so_far as number) ?? a.tokensSoFar,
                  }
                : a,
            ),
          );
        } else if (evt.event_type === "error" && evt.agent_name) {
          setAgents((prev) =>
            prev.map((a) =>
              a.name === evt.agent_name
                ? { ...a, status: "error", errorMessage: evt.message }
                : a,
            ),
          );
        } else if (evt.event_type === "completed") {
          setRunStatus("completed");
          void refreshFinalStatus(workflowId);
        } else if (evt.event_type === "failed") {
          setRunStatus("failed");
          setError(evt.message || "Bilinmeyen hata");
          void refreshFinalStatus(workflowId);
        } else if (evt.event_type === "final") {
          void refreshFinalStatus(workflowId);
        }
      },
      (err) => {
        setError("SSE bağlantı hatası");
        unsub();
      },
    );
    unsubRef.current = unsub;
  }, [refreshFinalStatus]);

  const handleStart = async () => {
    setError(null);
    setEvents([]);
    setAgents(makeInitialAgents());
    setFinalStatus(null);
    setArtifacts([]);
    setRunStatus("queued");

    try {
      if (sourceMode === "file" && !uploadedFile) {
        throw new Error("Önce bir dosya yükleyin.");
      }

      // Uzantıya göre input_source tipini belirle (pdf / docx / text fallback)
      const inferInputSource = (suffix: string): InputSource => {
        const s = suffix.toLowerCase();
        if (s === ".pdf") return "pdf";
        if (s === ".docx") return "docx";
        return "text";
      };

      const body = {
        project_id: projectId,
        input_source:
          sourceMode === "file"
            ? inferInputSource(uploadedFile!.suffix)
            : (sourceMode as InputSource),
        url: sourceMode === "url" ? url : undefined,
        text: sourceMode === "text" ? text : undefined,
        swagger_url: sourceMode === "swagger" ? swaggerUrl : undefined,
        file_path: sourceMode === "file" ? uploadedFile!.file_path : undefined,
        extra_context: extraContext || undefined,
        max_pages: maxPages,
        enable_ai_xpath: enableAiXpath,
        workflow_type: "test_generation" as const,
        dry_run: dryRun,
        requires_approval: requiresApproval,
      };
      const resp = await createAIWorkflow(body);
      setRunId(resp.workflow_id);
      setRunStatus(resp.status);
      if (resp.status !== "pending_approval") {
        attachWorkflowStream(resp.workflow_id);
      }
    } catch (e) {
      setError(String(e));
      setRunStatus("failed");
    }
  };

  const handleCancel = async () => {
    if (!runId) return;
    try {
      const resp = await cancelAIWorkflow(runId);
      setRunStatus(resp.status);
      void refreshFinalStatus(runId);
    } catch (e) {
      setError(String(e));
    }
  };

  const handleApproval = async (decision: "approved" | "rejected") => {
    if (!runId) return;
    setApprovalBusy(true);
    setError(null);
    try {
      const resp = await approveAIWorkflow(
        runId,
        decision,
        decision === "approved" ? "UI approval" : "UI rejection",
      );
      setRunStatus(resp.status);
      if (decision === "approved" && resp.status !== "pending_approval") {
        attachWorkflowStream(runId);
      } else {
        void refreshFinalStatus(runId);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setApprovalBusy(false);
    }
  };

  const canStart = Boolean(
    (sourceMode === "url" && url.trim()) ||
    (sourceMode === "text" && text.trim()) ||
    (sourceMode === "swagger" && swaggerUrl.trim()) ||
    (sourceMode === "file" && uploadedFile),
  );

  const isRunning = runStatus === "queued" || runStatus === "running";
  const inputsLocked = isRunning || runStatus === "pending_approval";

  return (
    <div style={{ padding: "24px", maxWidth: "1200px", margin: "0 auto" }}>
      <header style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: 700, marginBottom: "8px" }}>
          Sıfır Bilgi — AI Destekli Test Üretimi
        </h1>
        <p style={{ color: "#666", fontSize: "14px" }}>
          Gereksinim dokümanınızı, URL&apos;nizi veya API spec&apos;inizi verin; AI otomatik
          olarak analiz eder, senaryolar yazar, kod üretir ve testleri koşturur.
        </p>
      </header>

      {/* ── Input Form ─────────────────────────────────────────────── */}
      <section
        style={{
          border: "1px solid #e0e0e0",
          borderRadius: "8px",
          padding: "20px",
          marginBottom: "20px",
          background: "#fff",
        }}
      >
        <h2 style={{ fontSize: "18px", fontWeight: 600, marginBottom: "16px" }}>
          1. Kaynak Seçin
        </h2>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "12px",
            marginBottom: "20px",
          }}
        >
          {[
            { id: "url", label: "URL'den", desc: "Web sayfasını analiz et" },
            { id: "text", label: "Metinden", desc: "Gereksinim yapıştır" },
            { id: "swagger", label: "Swagger", desc: "OpenAPI URL" },
            { id: "file", label: "Dosya", desc: "PDF / DOCX yükle" },
          ].map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => setSourceMode(opt.id as SourceMode)}
              style={{
                padding: "14px",
                borderRadius: "6px",
                border:
                  sourceMode === opt.id
                    ? "2px solid #1976d2"
                    : "1px solid #ccc",
                background: sourceMode === opt.id ? "#e3f2fd" : "#fff",
                cursor: "pointer",
                textAlign: "left",
              }}
              disabled={inputsLocked}
            >
              <div style={{ fontWeight: 600, marginBottom: "4px" }}>
                {opt.label}
              </div>
              <div style={{ fontSize: "12px", color: "#666" }}>{opt.desc}</div>
            </button>
          ))}
        </div>

        {sourceMode === "url" && (
          <input
            type="url"
            placeholder="https://staging.banka-ornek.com.tr/kredi-basvurusu"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={inputsLocked}
            style={inputStyle}
          />
        )}
        {sourceMode === "text" && (
          <textarea
            placeholder="Gereksinim metnini buraya yapıştırın (min 100 karakter)..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={inputsLocked}
            rows={8}
            style={{ ...inputStyle, fontFamily: "inherit" }}
          />
        )}
        {sourceMode === "swagger" && (
          <input
            type="url"
            placeholder="https://api.banka-ornek.com.tr/openapi.json"
            value={swaggerUrl}
            onChange={(e) => setSwaggerUrl(e.target.value)}
            disabled={inputsLocked}
            style={inputStyle}
          />
        )}
        {sourceMode === "file" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <label
              htmlFor="sıfır-bilgi-file-input"
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "20px",
                border: "2px dashed #cbd5e1",
                borderRadius: "8px",
                cursor: uploading || inputsLocked ? "not-allowed" : "pointer",
                opacity: uploading || inputsLocked ? 0.6 : 1,
                color: "#475569",
              }}
            >
              <span style={{ fontSize: "14px", fontWeight: 600 }}>
                {uploading
                  ? "Yükleniyor…"
                  : uploadedFile
                    ? `✓ ${uploadedFile.original_name}`
                    : "Dosya seç veya buraya bırak"}
              </span>
              <span style={{ fontSize: "12px", marginTop: "4px", color: "#94a3b8" }}>
                PDF, DOCX, MD, TXT, CSV, JSON — en fazla 20 MB
              </span>
              <input
                id="sıfır-bilgi-file-input"
                data-testid="sifir-bilgi-file-input"
                type="file"
                accept=".pdf,.docx,.md,.txt,.csv,.json"
                disabled={uploading || inputsLocked}
                style={{ display: "none" }}
                onChange={async (e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  setUploading(true);
                  setError(null);
                  try {
                    const uploaded = await uploadSourceFile(f);
                    setUploadedFile(uploaded);
                  } catch (err: unknown) {
                    const msg =
                      err instanceof Error ? err.message : String(err);
                    setError(msg);
                    setUploadedFile(null);
                  } finally {
                    setUploading(false);
                    // Aynı dosya tekrar seçilebilsin diye input'u temizle
                    e.target.value = "";
                  }
                }}
              />
            </label>
            {uploadedFile && (
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  fontSize: "12px",
                  color: "#475569",
                }}
              >
                <span>
                  {(uploadedFile.size_bytes / 1024).toFixed(1)} KB · {uploadedFile.suffix}
                </span>
                <button
                  type="button"
                  onClick={() => setUploadedFile(null)}
                  disabled={inputsLocked}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#dc2626",
                    cursor: "pointer",
                    textDecoration: "underline",
                  }}
                >
                  Kaldır
                </button>
              </div>
            )}
          </div>
        )}

        <details style={{ marginTop: "16px" }}>
          <summary style={{ cursor: "pointer", fontSize: "14px", color: "#1976d2" }}>
            Gelişmiş ayarlar
          </summary>
          <div style={{ marginTop: "12px", display: "grid", gap: "8px" }}>
            <label style={{ fontSize: "13px" }}>
              Ek bağlam:
              <textarea
                value={extraContext}
                onChange={(e) => setExtraContext(e.target.value)}
                disabled={inputsLocked}
                rows={3}
                placeholder="AI'a ek talimat (örn: 'Sadece happy-path', 'KVKK odaklı')"
                style={{ ...inputStyle, marginTop: "4px" }}
              />
            </label>
            <label style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
              <input
                type="number"
                min={1}
                max={50}
                value={maxPages}
                onChange={(e) => setMaxPages(Number(e.target.value))}
                disabled={inputsLocked}
                style={{ width: "80px", padding: "6px", border: "1px solid #ccc", borderRadius: "4px" }}
              />
              Max sayfa (crawl)
            </label>
            <label style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
              <input
                type="checkbox"
                checked={enableAiXpath}
                onChange={(e) => setEnableAiXpath(e.target.checked)}
                disabled={inputsLocked}
              />
              AI XPath üretimi (vision model — daha yavaş, daha güçlü)
            </label>
            <label style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
              <input
                type="checkbox"
                checked={requiresApproval}
                onChange={(e) => setRequiresApproval(e.target.checked)}
                disabled={inputsLocked}
              />
              Human approval zorunlu
            </label>
            <label style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
                disabled={inputsLocked}
              />
              Dry-run modunda planla
            </label>
          </div>
        </details>

        <div style={{ marginTop: "20px", display: "flex", gap: "12px" }}>
          <button
            type="button"
            onClick={handleStart}
            disabled={!canStart || inputsLocked}
            style={{
              padding: "12px 24px",
              background: canStart && !inputsLocked ? "#1976d2" : "#aaa",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: canStart && !inputsLocked ? "pointer" : "not-allowed",
              fontWeight: 600,
              fontSize: "14px",
            }}
          >
            {isRunning ? "Çalışıyor..." : "Pipeline'ı Başlat"}
          </button>
          {isRunning && runId && (
            <button
              type="button"
              onClick={handleCancel}
              style={{
                padding: "12px 24px",
                background: "#fff",
                color: "#d32f2f",
                border: "1px solid #d32f2f",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              İptal
            </button>
          )}
          {runStatus === "pending_approval" && runId && (
            <>
              <button
                type="button"
                onClick={() => void handleApproval("approved")}
                disabled={approvalBusy}
                style={{
                  padding: "12px 24px",
                  background: approvalBusy ? "#aaa" : "#2e7d32",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: approvalBusy ? "not-allowed" : "pointer",
                  fontWeight: 600,
                }}
              >
                Onayla ve Kuyruğa Al
              </button>
              <button
                type="button"
                onClick={() => void handleApproval("rejected")}
                disabled={approvalBusy}
                style={{
                  padding: "12px 24px",
                  background: "#fff",
                  color: "#d32f2f",
                  border: "1px solid #d32f2f",
                  borderRadius: "6px",
                  cursor: approvalBusy ? "not-allowed" : "pointer",
                }}
              >
                Reddet
              </button>
            </>
          )}
        </div>

        {error && (
          <div
            style={{
              marginTop: "12px",
              padding: "12px",
              background: "#ffebee",
              color: "#c62828",
              borderRadius: "4px",
              fontSize: "13px",
            }}
          >
            {error}
          </div>
        )}
      </section>

      {/* ── Pipeline Progress ──────────────────────────────────────── */}
      {runId && (
        <section
          style={{
            border: "1px solid #e0e0e0",
            borderRadius: "8px",
            padding: "20px",
            marginBottom: "20px",
            background: "#fff",
          }}
        >
          <h2 style={{ fontSize: "18px", fontWeight: 600, marginBottom: "8px" }}>
            2. Pipeline İlerlemesi
          </h2>
          <div style={{ fontSize: "13px", color: "#666", marginBottom: "16px" }}>
            Run ID: <code>{runId.slice(0, 8)}</code> · Durum: <strong>{runStatus}</strong>
          </div>

          <div style={{ display: "grid", gap: "8px" }}>
            {agents.map((a) => (
              <AgentStatusRow key={a.name} agent={a} />
            ))}
          </div>
        </section>
      )}

      {/* ── Final Result ───────────────────────────────────────────── */}
      {finalStatus && (
        <section
          style={{
            border: "1px solid #e0e0e0",
            borderRadius: "8px",
            padding: "20px",
            background: "#fff",
          }}
        >
          <h2 style={{ fontSize: "18px", fontWeight: 600, marginBottom: "16px" }}>
            3. Nihai Özet
          </h2>
          <FinalSummary workflowId={runId} status={finalStatus} artifacts={artifacts} />
        </section>
      )}
    </div>
  );
}


const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px",
  border: "1px solid #ccc",
  borderRadius: "4px",
  fontSize: "14px",
};


function AgentStatusRow({ agent }: { agent: AgentStatus }) {
  const colors: Record<AgentStatus["status"], string> = {
    pending: "#eee",
    running: "#fff3e0",
    done: "#e8f5e9",
    error: "#ffebee",
  };
  const icons: Record<AgentStatus["status"], string> = {
    pending: "○",
    running: "◌",
    done: "✓",
    error: "✗",
  };
  const iconColors: Record<AgentStatus["status"], string> = {
    pending: "#bbb",
    running: "#f57c00",
    done: "#2e7d32",
    error: "#c62828",
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        padding: "10px 14px",
        background: colors[agent.status],
        borderRadius: "6px",
        fontSize: "14px",
      }}
    >
      <span
        style={{
          display: "inline-block",
          width: "28px",
          height: "28px",
          lineHeight: "28px",
          textAlign: "center",
          color: iconColors[agent.status],
          fontWeight: 700,
          fontSize: "18px",
          marginRight: "12px",
        }}
      >
        {icons[agent.status]}
      </span>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600 }}>{agent.label}</div>
        {agent.errorMessage && (
          <div style={{ fontSize: "12px", color: "#c62828" }}>
            {agent.errorMessage}
          </div>
        )}
      </div>
      {agent.status === "done" && (
        <div style={{ fontSize: "12px", color: "#666", textAlign: "right" }}>
          {agent.tokensSoFar !== undefined && <div>{agent.tokensSoFar} token</div>}
          {agent.costSoFar !== undefined && <div>${agent.costSoFar.toFixed(4)}</div>}
        </div>
      )}
    </div>
  );
}


function FinalSummary({
  workflowId,
  status,
  artifacts,
}: {
  workflowId: string | null;
  status: AIWorkflowStatus;
  artifacts: AIWorkflowArtifact[];
}) {
  const intent = status.intent_graph as Record<string, unknown> | null;
  const runResult = status.run_result as Record<string, number | string> | null;
  const review = status.review as Record<string, unknown> | null;
  const report = status.report as { summary_tr?: string } | null;

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
        <Stat label="Geçen" value={runResult?.passed_count ?? 0} color="#2e7d32" />
        <Stat label="Kalan" value={runResult?.failed_count ?? 0} color="#c62828" />
        <Stat label="Token" value={status.tokens_used} />
        <Stat label="Maliyet" value={`$${status.cost_usd.toFixed(3)}`} />
      </div>

      {intent && (
        <div>
          <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "6px" }}>
            Intent Graph
          </h3>
          <div style={{ fontSize: "13px", color: "#555" }}>
            Domain: <code>{String(intent.domain)}</code>
            {" · "}
            Feature: <code>{String(intent.feature_area)}</code>
            {" · "}
            Risk: <strong>{String(intent.risk_level)}</strong>
          </div>
        </div>
      )}

      {status.scenarios.length > 0 && (
        <div>
          <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "6px" }}>
            Üretilen Senaryolar
          </h3>
          <ul style={{ fontSize: "13px", paddingLeft: "18px", color: "#333" }}>
            {status.scenarios.map((s, i) => {
              const obj = s as Record<string, unknown>;
              return (
                <li key={i}>
                  <strong>{String(obj.name || "(isimsiz)")}</strong>
                  {" — "}
                  {String(obj.scenario_count ?? 0)} senaryo
                  {obj.feature_path ? (
                    <>
                      {" · "}
                      <code style={{ fontSize: "11px" }}>{String(obj.feature_path)}</code>
                    </>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {review && (
        <div>
          <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "6px" }}>
            Reviewer Kararı
          </h3>
          <div style={{ fontSize: "13px", color: "#555" }}>
            Kalite: <strong>{((review.code_quality_score as number) * 100).toFixed(0)}%</strong>
            {" · "}
            Aksiyon: <code>{String(review.recommended_action)}</code>
          </div>
        </div>
      )}

      {report?.summary_tr && (
        <div>
          <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "6px" }}>
            Yönetim Raporu
          </h3>
          <pre
            style={{
              fontSize: "13px",
              background: "#f5f5f5",
              padding: "12px",
              borderRadius: "4px",
              whiteSpace: "pre-wrap",
              fontFamily: "inherit",
            }}
          >
            {report.summary_tr}
          </pre>
        </div>
      )}

      {artifacts.length > 0 && (
        <div>
          <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "6px" }}>
            Artefact Çıktıları
          </h3>
          <ul style={{ fontSize: "13px", paddingLeft: "18px", color: "#333" }}>
            {artifacts.map((artifact) => {
              const openable =
                artifact.storage_path.startsWith("http://") ||
                artifact.storage_path.startsWith("https://");
              return (
                <li key={artifact.artifact_id}>
                  <strong>{artifact.name}</strong>
                  {" · "}
                  <span>{artifact.kind}</span>
                  {" · "}
                  <span>{formatBytes(artifact.size_bytes)}</span>
                  {" · "}
                  {openable ? (
                    <a
                      href={artifact.storage_path}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: "#1976d2" }}
                    >
                      Aç
                    </a>
                  ) : (
                    <>
                      {workflowId ? (
                        <button
                          type="button"
                          onClick={async () => {
                            try {
                              await downloadAIWorkflowArtifact(workflowId, artifact);
                            } catch (err) {
                              window.alert(err instanceof Error ? err.message : String(err));
                            }
                          }}
                          style={{
                            background: "none",
                            border: "none",
                            color: "#1976d2",
                            cursor: "pointer",
                            padding: 0,
                            font: "inherit",
                            textDecoration: "underline",
                          }}
                        >
                          İndir
                        </button>
                      ) : null}
                      {" · "}
                      <code style={{ fontSize: "11px" }}>{artifact.storage_path}</code>
                    </>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}


function formatBytes(bytes: number) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}


function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: number | string;
  color?: string;
}) {
  return (
    <div
      style={{
        padding: "12px",
        background: "#f5f5f5",
        borderRadius: "4px",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: "12px", color: "#666" }}>{label}</div>
      <div
        style={{
          fontSize: "24px",
          fontWeight: 700,
          marginTop: "4px",
          color: color || "#333",
        }}
      >
        {value}
      </div>
    </div>
  );
}
