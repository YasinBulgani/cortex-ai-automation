/**
 * Sıfır Bilgi — Zero-Knowledge Test Generation Sayfası
 *
 * Kullanıcı sadece URL, PDF, Swagger, Jira veya metin verir;
 * AI 9 ajanlı pipeline otomatik çalışır ve test paketi üretir.
 *
 * Akış:
 *  1. Kullanıcı kaynak seçer + yükler
 *  2. Backend'e POST /api/v1/agents/v2/run → run_id + stream_url
 *  3. EventSource ile SSE bağlan → her ajan eventini canlı göster
 *  4. Bitiminde özet + üretilen senaryolar + kod path'leri + raporlar
 */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";

import {
  startAgentRun,
  getAgentRun,
  subscribeAgentRun,
  cancelAgentRun,
  type AgentStreamEvent,
  type InputSource,
  type RunV2Status,
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


export default function SifirBilgiPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params?.projectId || "default";

  const [sourceMode, setSourceMode] = useState<SourceMode>("url");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [swaggerUrl, setSwaggerUrl] = useState("");
  const [extraContext, setExtraContext] = useState("");
  const [maxPages, setMaxPages] = useState(15);
  const [enableAiXpath, setEnableAiXpath] = useState(false);

  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string>("idle");
  const [agents, setAgents] = useState<AgentStatus[]>(makeInitialAgents());
  const [events, setEvents] = useState<AgentStreamEvent[]>([]);
  const [finalStatus, setFinalStatus] = useState<RunV2Status | null>(null);
  const [error, setError] = useState<string | null>(null);

  const unsubRef = useRef<(() => void) | null>(null);

  useEffect(() => () => {
    unsubRef.current?.();
  }, []);

  const handleStart = async () => {
    setError(null);
    setEvents([]);
    setAgents(makeInitialAgents());
    setFinalStatus(null);
    setRunStatus("queued");

    try {
      const body = {
        project_id: projectId,
        input_source: (sourceMode === "file" ? "pdf" : sourceMode) as InputSource,
        url: sourceMode === "url" ? url : undefined,
        text: sourceMode === "text" ? text : undefined,
        swagger_url: sourceMode === "swagger" ? swaggerUrl : undefined,
        extra_context: extraContext || undefined,
        max_pages: maxPages,
        enable_ai_xpath: enableAiXpath,
      };
      const resp = await startAgentRun(body);
      setRunId(resp.run_id);
      setRunStatus(resp.status);

      // SSE
      const unsub = subscribeAgentRun(
        resp.run_id,
        (evt) => {
          setEvents((prev) => [...prev, evt]);

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
            void refreshFinalStatus(resp.run_id);
          } else if (evt.event_type === "failed") {
            setRunStatus("failed");
            setError(evt.message || "Bilinmeyen hata");
            void refreshFinalStatus(resp.run_id);
          } else if (evt.event_type === "final") {
            // Son state
            const asStatus = evt as unknown as { data?: RunV2Status };
            // final event JSON yapıyı `data` değil doğrudan body olarak döndürür
            // bu event için server farklı formatlama yapıyor; tekrar GET ile netleştir
            void refreshFinalStatus(resp.run_id);
          }
        },
        (err) => {
          setError("SSE bağlantı hatası");
          unsub();
        },
      );
      unsubRef.current = unsub;
    } catch (e) {
      setError(String(e));
      setRunStatus("failed");
    }
  };

  const refreshFinalStatus = useCallback(async (rid: string) => {
    try {
      const status = await getAgentRun(rid);
      setFinalStatus(status);
    } catch (e) {
      // ignore
    }
  }, []);

  const handleCancel = async () => {
    if (!runId) return;
    try {
      await cancelAgentRun(runId);
      setRunStatus("cancelled");
    } catch (e) {
      setError(String(e));
    }
  };

  const canStart =
    (sourceMode === "url" && url.trim()) ||
    (sourceMode === "text" && text.trim()) ||
    (sourceMode === "swagger" && swaggerUrl.trim());

  const isRunning = runStatus === "queued" || runStatus === "running";

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
              disabled={isRunning}
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
            disabled={isRunning}
            style={inputStyle}
          />
        )}
        {sourceMode === "text" && (
          <textarea
            placeholder="Gereksinim metnini buraya yapıştırın (min 100 karakter)..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={isRunning}
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
            disabled={isRunning}
            style={inputStyle}
          />
        )}
        {sourceMode === "file" && (
          <div style={{ padding: "12px", background: "#fff3cd", borderRadius: "6px", color: "#856404" }}>
            Dosya yükleme yakında — şimdilik metin veya URL kullanın.
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
                disabled={isRunning}
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
                disabled={isRunning}
                style={{ width: "80px", padding: "6px", border: "1px solid #ccc", borderRadius: "4px" }}
              />
              Max sayfa (crawl)
            </label>
            <label style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
              <input
                type="checkbox"
                checked={enableAiXpath}
                onChange={(e) => setEnableAiXpath(e.target.checked)}
                disabled={isRunning}
              />
              AI XPath üretimi (vision model — daha yavaş, daha güçlü)
            </label>
          </div>
        </details>

        <div style={{ marginTop: "20px", display: "flex", gap: "12px" }}>
          <button
            type="button"
            onClick={handleStart}
            disabled={!canStart || isRunning}
            style={{
              padding: "12px 24px",
              background: canStart && !isRunning ? "#1976d2" : "#aaa",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: canStart && !isRunning ? "pointer" : "not-allowed",
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
          <FinalSummary status={finalStatus} />
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


function FinalSummary({ status }: { status: RunV2Status }) {
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
    </div>
  );
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
