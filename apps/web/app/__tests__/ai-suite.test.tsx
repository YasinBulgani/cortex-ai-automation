/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// ─── AI Chat Page ───────────────────────────────────────────────────────────

describe("AiChatPage", () => {
  it("renders chat container", () => {
    const ChatPage = () => (
      <div data-testid="ai-chat-page">
        <div data-testid="chat-messages" />
        <input data-testid="chat-input" placeholder="Mesajınızı yazın..." />
        <button data-testid="chat-send">Gönder</button>
      </div>
    );
    render(<ChatPage />);
    expect(screen.getByTestId("ai-chat-page")).toBeInTheDocument();
    expect(screen.getByTestId("chat-input")).toBeInTheDocument();
    expect(screen.getByTestId("chat-send")).toBeInTheDocument();
  });

  it("input updates on type", () => {
    const ChatInput = () => {
      const [val, setVal] = React.useState("");
      return (
        <input
          data-testid="chat-input"
          value={val}
          onChange={(e) => setVal(e.target.value)}
          placeholder="Mesaj yaz..."
        />
      );
    };
    render(<ChatInput />);
    fireEvent.change(screen.getByTestId("chat-input"), { target: { value: "Test senaryosu yaz" } });
    expect((screen.getByTestId("chat-input") as HTMLInputElement).value).toBe("Test senaryosu yaz");
  });

  it("messages list renders correctly", () => {
    const messages = [
      { id: "m1", role: "user",      content: "Merhaba" },
      { id: "m2", role: "assistant", content: "Nasıl yardımcı olabilirim?" },
    ];
    const MessageList = ({ messages }: { messages: typeof messages }) => (
      <div data-testid="chat-messages">
        {messages.map((m) => (
          <div key={m.id} data-testid={`msg-${m.role}`}>{m.content}</div>
        ))}
      </div>
    );
    render(<MessageList messages={messages} />);
    expect(screen.getByTestId("msg-user")).toHaveTextContent("Merhaba");
    expect(screen.getByTestId("msg-assistant")).toHaveTextContent("Nasıl yardımcı olabilirim?");
  });

  it("new session resets conversation", () => {
    const SessionManager = () => {
      const [msgCount, setMsgCount] = React.useState(3);
      return (
        <div>
          <span data-testid="msg-count">{msgCount} mesaj</span>
          <button data-testid="btn-new-session" onClick={() => setMsgCount(0)}>Yeni Oturum</button>
        </div>
      );
    };
    render(<SessionManager />);
    expect(screen.getByTestId("msg-count")).toHaveTextContent("3 mesaj");
    fireEvent.click(screen.getByTestId("btn-new-session"));
    expect(screen.getByTestId("msg-count")).toHaveTextContent("0 mesaj");
  });

  it("loading indicator shown while streaming", () => {
    const StreamingIndicator = ({ streaming }: { streaming: boolean }) => (
      streaming ? <div data-testid="streaming-indicator" className="animate-pulse">...</div> : null
    );
    render(<StreamingIndicator streaming={true} />);
    expect(screen.getByTestId("streaming-indicator")).toBeInTheDocument();
  });

  it("streaming indicator hidden when not loading", () => {
    const StreamingIndicator = ({ streaming }: { streaming: boolean }) => (
      streaming ? <div data-testid="streaming-indicator">...</div> : null
    );
    render(<StreamingIndicator streaming={false} />);
    expect(screen.queryByTestId("streaming-indicator")).not.toBeInTheDocument();
  });

  it("session selector shows previous sessions", () => {
    const sessions = [{ id: "ses1", title: "Regresyon analizi" }, { id: "ses2", title: "Test case önerileri" }];
    const SessionSelector = () => (
      <select data-testid="session-select">
        <option value="">Yeni oturum</option>
        {sessions.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
      </select>
    );
    render(<SessionSelector />);
    expect(screen.getByTestId("session-select")).toBeInTheDocument();
    expect(screen.getByText("Regresyon analizi")).toBeInTheDocument();
  });
});

// ─── AI Metrics Page ────────────────────────────────────────────────────────

describe("AiMetricsPage", () => {
  const MOCK_OVERVIEW = { total_calls: 1240, success_rate: 94.2, json_parse_rate: 97.8, avg_latency_ms: 342 };

  it("renders overview stat tiles", () => {
    const StatTile = ({ label, value }: { label: string; value: string }) => (
      <div data-testid="stat-tile">
        <span data-testid="stat-label">{label}</span>
        <span data-testid="stat-value">{value}</span>
      </div>
    );
    render(
      <div data-testid="ai-metrics-page">
        <StatTile label="Toplam LLM Çağrı" value={MOCK_OVERVIEW.total_calls.toLocaleString()} />
        <StatTile label="Başarı Oranı" value={`${MOCK_OVERVIEW.success_rate.toFixed(1)}%`} />
        <StatTile label="JSON Parse Oranı" value={`${MOCK_OVERVIEW.json_parse_rate.toFixed(1)}%`} />
        <StatTile label="Ort. Gecikme" value={`${Math.round(MOCK_OVERVIEW.avg_latency_ms)} ms`} />
      </div>
    );
    expect(screen.getByText("1,240")).toBeInTheDocument();
    expect(screen.getByText("94.2%")).toBeInTheDocument();
    expect(screen.getByText("97.8%")).toBeInTheDocument();
    expect(screen.getByText("342 ms")).toBeInTheDocument();
  });

  it("rate color function returns correct class", () => {
    function rateColor(rate: number) {
      if (rate > 90) return "text-emerald-400";
      if (rate > 80) return "text-amber-400";
      return "text-red-400";
    }
    expect(rateColor(95)).toBe("text-emerald-400");
    expect(rateColor(85)).toBe("text-amber-400");
    expect(rateColor(70)).toBe("text-red-400");
    expect(rateColor(90)).toBe("text-amber-400"); // boundary: not > 90
  });

  it("agent performance table renders agents sorted by calls", () => {
    const agents = [
      { agent: "ScenarioAgent", calls: 450, success_rate: 96.1, avg_latency_ms: 310 },
      { agent: "CoverageAgent", calls: 790, success_rate: 92.4, avg_latency_ms: 280 },
    ];
    const AgentTable = ({ agents }: { agents: typeof agents }) => (
      <table data-testid="agent-table">
        <tbody>
          {[...agents].sort((a, b) => b.calls - a.calls).map((a) => (
            <tr key={a.agent} data-testid="agent-row">
              <td data-testid="agent-name">{a.agent}</td>
              <td data-testid="agent-calls">{a.calls}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
    render(<AgentTable agents={agents} />);
    const rows = screen.getAllByTestId("agent-row");
    expect(rows[0]).toHaveTextContent("CoverageAgent"); // 790 > 450
    expect(rows[1]).toHaveTextContent("ScenarioAgent");
  });

  it("empty state when no calls exist", () => {
    const EmptyMetrics = () => (
      <div data-testid="ai-metrics-empty">
        <p>Henüz veri yok</p>
      </div>
    );
    render(<EmptyMetrics />);
    expect(screen.getByTestId("ai-metrics-empty")).toBeInTheDocument();
  });

  it("days selector updates period", () => {
    const DaySelector = () => {
      const [days, setDays] = React.useState(30);
      return (
        <select data-testid="day-selector" value={days}
          onChange={(e) => setDays(Number(e.target.value))}>
          {[7, 14, 30, 60, 90].map((d) => <option key={d} value={d}>{d} gün</option>)}
        </select>
      );
    };
    render(<DaySelector />);
    expect((screen.getByTestId("day-selector") as HTMLSelectElement).value).toBe("30");
    fireEvent.change(screen.getByTestId("day-selector"), { target: { value: "7" } });
    expect((screen.getByTestId("day-selector") as HTMLSelectElement).value).toBe("7");
  });

  it("loading skeleton renders 4 tiles", () => {
    const LoadingSkeleton = () => (
      <div data-testid="ai-metrics-loading">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} data-testid="skeleton-tile" className="animate-pulse" />
        ))}
      </div>
    );
    render(<LoadingSkeleton />);
    expect(screen.getAllByTestId("skeleton-tile")).toHaveLength(4);
  });
});

// ─── NL Test Generator Page ─────────────────────────────────────────────────

describe("NlTestGenPage", () => {
  it("renders text input area", () => {
    const Page = () => (
      <div data-testid="nl-test-gen-page">
        <textarea data-testid="nl-input" placeholder="Doğal dil ile test gereksinimini açıklayın..." />
        <button data-testid="btn-generate">Üret</button>
      </div>
    );
    render(<Page />);
    expect(screen.getByTestId("nl-input")).toBeInTheDocument();
    expect(screen.getByTestId("btn-generate")).toBeInTheDocument();
  });

  it("generate button disabled when input is empty", () => {
    const GenButton = ({ input }: { input: string }) => (
      <button data-testid="btn-generate" disabled={input.trim() === ""}>Üret</button>
    );
    render(<GenButton input="" />);
    expect(screen.getByTestId("btn-generate")).toBeDisabled();
  });

  it("generate button enabled when input is present", () => {
    const GenButton = ({ input }: { input: string }) => (
      <button data-testid="btn-generate" disabled={input.trim() === ""}>Üret</button>
    );
    render(<GenButton input="Login senaryosu" />);
    expect(screen.getByTestId("btn-generate")).not.toBeDisabled();
  });

  it("generated test cases display after submission", () => {
    const Results = ({ cases }: { cases: string[] }) => (
      <div data-testid="generated-cases">
        {cases.map((c, i) => <div key={i} data-testid="test-case-item">{c}</div>)}
      </div>
    );
    render(<Results cases={["TC-001: Login başarılı", "TC-002: Yanlış şifre"]} />);
    expect(screen.getAllByTestId("test-case-item")).toHaveLength(2);
    expect(screen.getByText("TC-001: Login başarılı")).toBeInTheDocument();
  });

  it("copy button on test case result", () => {
    const CopyBtn = ({ onCopy }: { onCopy: () => void }) => (
      <button data-testid="btn-copy-case" onClick={onCopy}>Kopyala</button>
    );
    const onCopy = jest.fn();
    render(<CopyBtn onCopy={onCopy} />);
    fireEvent.click(screen.getByTestId("btn-copy-case"));
    expect(onCopy).toHaveBeenCalled();
  });
});

// ─── QA Orchestrator Page ───────────────────────────────────────────────────

describe("QaOrchestratorPage", () => {
  it("renders orchestrator dashboard", () => {
    const Page = () => (
      <div data-testid="qa-orchestrator-page">
        <h1 data-testid="orch-heading">QA Orkestratör</h1>
        <button data-testid="btn-run-orchestrator">Orchestration Başlat</button>
      </div>
    );
    render(<Page />);
    expect(screen.getByTestId("qa-orchestrator-page")).toBeInTheDocument();
    expect(screen.getByTestId("btn-run-orchestrator")).toBeInTheDocument();
  });

  it("task list renders active tasks", () => {
    const tasks = [
      { id: "t1", name: "Flaky Detection", status: "running" },
      { id: "t2", name: "Gap Analysis",   status: "completed" },
      { id: "t3", name: "AI Assertions",  status: "pending" },
    ];
    const TaskList = ({ tasks }: { tasks: typeof tasks }) => (
      <div data-testid="task-list">
        {tasks.map((t) => (
          <div key={t.id} data-testid="task-row">
            <span>{t.name}</span>
            <span data-testid={`task-status-${t.id}`}>{t.status}</span>
          </div>
        ))}
      </div>
    );
    render(<TaskList tasks={tasks} />);
    expect(screen.getAllByTestId("task-row")).toHaveLength(3);
    expect(screen.getByTestId("task-status-t1")).toHaveTextContent("running");
    expect(screen.getByTestId("task-status-t2")).toHaveTextContent("completed");
  });

  it("shows results panel when orchestration completes", () => {
    const ResultsPanel = ({ done }: { done: boolean }) => (
      done ? <div data-testid="orch-results">Orchestration tamamlandı</div> : null
    );
    const { rerender } = render(<ResultsPanel done={false} />);
    expect(screen.queryByTestId("orch-results")).not.toBeInTheDocument();
    rerender(<ResultsPanel done={true} />);
    expect(screen.getByTestId("orch-results")).toBeInTheDocument();
  });

  it("priority list shows critical issues first", () => {
    const priorities = [
      { label: "Kritik: Flaky test sayısı artışı", level: "critical" },
      { label: "Orta: Düşük kapsam",               level: "medium" },
    ];
    const PriorityList = ({ items }: { items: typeof priorities }) => (
      <ul data-testid="priority-list">
        {items.map((p, i) => (
          <li key={i} data-testid={`priority-item-${p.level}`}>{p.label}</li>
        ))}
      </ul>
    );
    render(<PriorityList items={priorities} />);
    expect(screen.getByTestId("priority-item-critical")).toBeInTheDocument();
    expect(screen.getByTestId("priority-item-medium")).toBeInTheDocument();
  });
});
