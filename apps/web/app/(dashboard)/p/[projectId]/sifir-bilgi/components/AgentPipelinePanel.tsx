"use client";

export interface AgentStatus {
  name: string;
  label: string;
  status: "pending" | "running" | "done" | "error";
  startedAt?: string;
  endedAt?: string;
  costSoFar?: number;
  tokensSoFar?: number;
  errorMessage?: string;
}

export interface AgentPipelinePanelProps {
  runId: string;
  runStatus: string;
  agents: AgentStatus[];
}

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
          {agent.tokensSoFar !== undefined && (
            <div>{agent.tokensSoFar} token</div>
          )}
          {agent.costSoFar !== undefined && (
            <div>${agent.costSoFar.toFixed(4)}</div>
          )}
        </div>
      )}
    </div>
  );
}

export function AgentPipelinePanel({
  runId,
  runStatus,
  agents,
}: AgentPipelinePanelProps) {
  return (
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
      <div
        style={{ fontSize: "13px", color: "#666", marginBottom: "16px" }}
      >
        Run ID: <code>{runId.slice(0, 8)}</code> · Durum:{" "}
        <strong>{runStatus}</strong>
      </div>

      <div style={{ display: "grid", gap: "8px" }}>
        {agents.map((a) => (
          <AgentStatusRow key={a.name} agent={a} />
        ))}
      </div>
    </section>
  );
}
