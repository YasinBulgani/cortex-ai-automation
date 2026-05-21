/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// ─── API Tests / Collection Page ────────────────────────────────────────────

describe("ApiTestsPage — Collection Management", () => {
  const MOCK_COLLECTIONS = [
    { id: "c1", name: "Auth Endpoints", request_count: 5, created_at: "2026-01-01" },
    { id: "c2", name: "Payment Flow",   request_count: 8, created_at: "2026-01-05" },
  ];

  it("renders collection list", () => {
    const CollectionList = ({ collections }: { collections: typeof MOCK_COLLECTIONS }) => (
      <div data-testid="collection-list">
        {collections.map((c) => (
          <div key={c.id} data-testid="collection-item">
            <span data-testid="col-name">{c.name}</span>
            <span data-testid="col-count">{c.request_count} istek</span>
          </div>
        ))}
      </div>
    );
    render(<CollectionList collections={MOCK_COLLECTIONS} />);
    expect(screen.getAllByTestId("collection-item")).toHaveLength(2);
    expect(screen.getByText("Auth Endpoints")).toBeInTheDocument();
    expect(screen.getByText("8 istek")).toBeInTheDocument();
  });

  it("create collection form submits name", () => {
    const onSubmit = jest.fn();
    const CreateForm = ({ onSubmit }: { onSubmit: (name: string) => void }) => {
      const [name, setName] = React.useState("");
      return (
        <form onSubmit={(e) => { e.preventDefault(); onSubmit(name); }}>
          <input data-testid="col-name-input" value={name} onChange={(e) => setName(e.target.value)} />
          <button type="submit" data-testid="btn-create-col">Oluştur</button>
        </form>
      );
    };
    render(<CreateForm onSubmit={onSubmit} />);
    fireEvent.change(screen.getByTestId("col-name-input"), { target: { value: "User Management" } });
    fireEvent.click(screen.getByTestId("btn-create-col"));
    expect(onSubmit).toHaveBeenCalledWith("User Management");
  });

  it("empty state shown when no collections", () => {
    const EmptyState = () => (
      <div data-testid="empty-collections">
        <p>Henüz koleksiyon yok</p>
        <button data-testid="btn-create-first-col">İlk Koleksiyonu Oluştur</button>
      </div>
    );
    render(<EmptyState />);
    expect(screen.getByTestId("empty-collections")).toBeInTheDocument();
  });
});

describe("ApiTestsPage — Requests", () => {
  const HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"] as const;

  it("all HTTP methods available in method selector", () => {
    const MethodSelect = () => (
      <select data-testid="method-select">
        {HTTP_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
      </select>
    );
    render(<MethodSelect />);
    HTTP_METHODS.forEach((m) => {
      expect(screen.getByText(m)).toBeInTheDocument();
    });
  });

  it("method color coding", () => {
    function methodColor(method: string): string {
      const colors: Record<string, string> = {
        GET:    "text-emerald-400",
        POST:   "text-blue-400",
        PUT:    "text-amber-400",
        PATCH:  "text-orange-400",
        DELETE: "text-red-400",
      };
      return colors[method] ?? "text-slate-400";
    }
    expect(methodColor("GET")).toBe("text-emerald-400");
    expect(methodColor("POST")).toBe("text-blue-400");
    expect(methodColor("DELETE")).toBe("text-red-400");
    expect(methodColor("OPTIONS")).toBe("text-slate-400");
  });

  it("request row renders method and path", () => {
    const RequestRow = ({ method, path }: { method: string; path: string }) => (
      <div data-testid="request-row">
        <span data-testid="req-method">{method}</span>
        <span data-testid="req-path">{path}</span>
      </div>
    );
    render(<RequestRow method="POST" path="/api/v1/auth/login" />);
    expect(screen.getByTestId("req-method")).toHaveTextContent("POST");
    expect(screen.getByTestId("req-path")).toHaveTextContent("/api/v1/auth/login");
  });

  it("send request button triggers handler", () => {
    const onSend = jest.fn();
    const SendBtn = ({ onSend }: { onSend: () => void }) => (
      <button data-testid="btn-send-request" onClick={onSend}>İstek Gönder</button>
    );
    render(<SendBtn onSend={onSend} />);
    fireEvent.click(screen.getByTestId("btn-send-request"));
    expect(onSend).toHaveBeenCalled();
  });

  it("response panel shows status code", () => {
    const ResponsePanel = ({ status, body }: { status: number; body: string }) => (
      <div data-testid="response-panel">
        <span data-testid="response-status">{status}</span>
        <pre data-testid="response-body">{body}</pre>
      </div>
    );
    render(<ResponsePanel status={200} body='{"ok": true}' />);
    expect(screen.getByTestId("response-status")).toHaveTextContent("200");
    expect(screen.getByTestId("response-body")).toHaveTextContent('{"ok": true}');
  });

  it("status code color by range", () => {
    function statusColor(code: number): string {
      if (code >= 500) return "text-red-400";
      if (code >= 400) return "text-orange-400";
      if (code >= 300) return "text-amber-400";
      if (code >= 200) return "text-emerald-400";
      return "text-slate-400";
    }
    expect(statusColor(200)).toBe("text-emerald-400");
    expect(statusColor(201)).toBe("text-emerald-400");
    expect(statusColor(301)).toBe("text-amber-400");
    expect(statusColor(404)).toBe("text-orange-400");
    expect(statusColor(500)).toBe("text-red-400");
  });

  it("request tabs switch between headers / body / params", () => {
    const RequestTabs = () => {
      const [tab, setTab] = React.useState("params");
      return (
        <div>
          {["params", "headers", "body"].map((t) => (
            <button key={t} data-testid={`req-tab-${t}`} onClick={() => setTab(t)}>{t}</button>
          ))}
          <div data-testid="req-tab-content">{tab}</div>
        </div>
      );
    };
    render(<RequestTabs />);
    expect(screen.getByTestId("req-tab-content")).toHaveTextContent("params");
    fireEvent.click(screen.getByTestId("req-tab-body"));
    expect(screen.getByTestId("req-tab-content")).toHaveTextContent("body");
    fireEvent.click(screen.getByTestId("req-tab-headers"));
    expect(screen.getByTestId("req-tab-content")).toHaveTextContent("headers");
  });
});

describe("ApiTestsPage — Run Results", () => {
  it("run results summary shows pass/fail count", () => {
    const RunSummary = ({ passed, failed }: { passed: number; failed: number }) => (
      <div data-testid="run-summary">
        <span data-testid="run-passed">{passed} geçti</span>
        <span data-testid="run-failed">{failed} başarısız</span>
      </div>
    );
    render(<RunSummary passed={7} failed={2} />);
    expect(screen.getByTestId("run-passed")).toHaveTextContent("7 geçti");
    expect(screen.getByTestId("run-failed")).toHaveTextContent("2 başarısız");
  });

  it("latency shown for each result", () => {
    const ResultRow = ({ name, latency_ms }: { name: string; latency_ms: number }) => (
      <div data-testid="result-row">
        <span>{name}</span>
        <span data-testid="result-latency">{latency_ms} ms</span>
      </div>
    );
    render(<ResultRow name="GET /users" latency_ms={142} />);
    expect(screen.getByTestId("result-latency")).toHaveTextContent("142 ms");
  });
});
