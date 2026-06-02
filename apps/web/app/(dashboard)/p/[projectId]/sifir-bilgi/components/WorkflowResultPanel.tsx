"use client";

import {
  downloadAIWorkflowArtifact,
  type AIWorkflowArtifact,
  type AIWorkflowStatus,
} from "@/lib/agents-v2-api";

// ── Helpers ────────────────────────────────────────────────────────────────

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

// ── FinalSummary (internal) ────────────────────────────────────────────────

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
  const runResult = status.run_result as Record<
    string,
    number | string
  > | null;
  const review = status.review as Record<string, unknown> | null;
  const report = status.report as { summary_tr?: string } | null;

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "12px",
        }}
      >
        <Stat
          label="Geçen"
          value={runResult?.passed_count ?? 0}
          color="#2e7d32"
        />
        <Stat
          label="Kalan"
          value={runResult?.failed_count ?? 0}
          color="#c62828"
        />
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
                      <code style={{ fontSize: "11px" }}>
                        {String(obj.feature_path)}
                      </code>
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
            Kalite:{" "}
            <strong>
              {((review.code_quality_score as number) * 100).toFixed(0)}%
            </strong>
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
                              await downloadAIWorkflowArtifact(
                                workflowId,
                                artifact
                              );
                            } catch (err) {
                              window.alert(
                                err instanceof Error
                                  ? err.message
                                  : String(err)
                              );
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
                      <code style={{ fontSize: "11px" }}>
                        {artifact.storage_path}
                      </code>
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

// ── Exported component ─────────────────────────────────────────────────────

export interface WorkflowResultPanelProps {
  workflowId: string | null;
  status: AIWorkflowStatus;
  artifacts: AIWorkflowArtifact[];
}

export function WorkflowResultPanel({
  workflowId,
  status,
  artifacts,
}: WorkflowResultPanelProps) {
  return (
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
      <FinalSummary
        workflowId={workflowId}
        status={status}
        artifacts={artifacts}
      />
    </section>
  );
}
