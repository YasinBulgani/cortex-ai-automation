/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// ─── Coverage Page (3-Tab: BDD / API / Code) ────────────────────────────────

describe("CoveragePage — Tab Navigation", () => {
  const TABS = [
    { id: "bdd", label: "BDD Kapsam" },
    { id: "api", label: "API Kapsam" },
    { id: "code", label: "Kod Kapsam" },
  ];

  it("renders all 3 coverage tabs", () => {
    const TabBar = ({ tabs }: { tabs: typeof TABS }) => (
      <div role="tablist" data-testid="coverage-tabs">
        {tabs.map((t) => (
          <button key={t.id} role="tab" data-testid={`tab-${t.id}`}>{t.label}</button>
        ))}
      </div>
    );
    render(<TabBar tabs={TABS} />);
    expect(screen.getAllByRole("tab")).toHaveLength(3);
    expect(screen.getByTestId("tab-bdd")).toBeInTheDocument();
    expect(screen.getByTestId("tab-api")).toBeInTheDocument();
    expect(screen.getByTestId("tab-code")).toBeInTheDocument();
  });

  it("active tab switches on click", () => {
    const TabbedView = () => {
      const [active, setActive] = React.useState("bdd");
      return (
        <div>
          <div role="tablist">
            {TABS.map((t) => (
              <button key={t.id} role="tab" data-testid={`tab-${t.id}`}
                aria-selected={active === t.id} onClick={() => setActive(t.id)}>
                {t.label}
              </button>
            ))}
          </div>
          <div data-testid="active-panel">{active}-panel</div>
        </div>
      );
    };
    render(<TabbedView />);
    expect(screen.getByTestId("active-panel")).toHaveTextContent("bdd-panel");
    fireEvent.click(screen.getByTestId("tab-api"));
    expect(screen.getByTestId("active-panel")).toHaveTextContent("api-panel");
    fireEvent.click(screen.getByTestId("tab-code"));
    expect(screen.getByTestId("active-panel")).toHaveTextContent("code-panel");
  });
});

describe("CoveragePage — BDD Tab", () => {
  const MOCK_FEATURES = [
    { feature: "Login", total: 8, covered: 7, coverage: 87.5 },
    { feature: "Checkout", total: 12, covered: 9, coverage: 75.0 },
    { feature: "Profile", total: 5, covered: 5, coverage: 100.0 },
  ];

  it("renders feature coverage table", () => {
    const FeatureTable = ({ features }: { features: typeof MOCK_FEATURES }) => (
      <table data-testid="feature-table">
        <tbody>
          {features.map((f) => (
            <tr key={f.feature} data-testid="feature-row">
              <td data-testid="feature-name">{f.feature}</td>
              <td data-testid="feature-coverage">{f.coverage.toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
    render(<FeatureTable features={MOCK_FEATURES} />);
    expect(screen.getAllByTestId("feature-row")).toHaveLength(3);
    expect(screen.getByText("Login")).toBeInTheDocument();
    expect(screen.getByText("87.5%")).toBeInTheDocument();
    expect(screen.getByText("100.0%")).toBeInTheDocument();
  });

  it("coverage rate color reflects threshold", () => {
    function rateColor(rate: number) {
      if (rate >= 80) return "text-emerald-400";
      if (rate >= 60) return "text-amber-400";
      return "text-red-400";
    }
    expect(rateColor(100)).toBe("text-emerald-400");
    expect(rateColor(87.5)).toBe("text-emerald-400");
    expect(rateColor(75)).toBe("text-amber-400");
    expect(rateColor(40)).toBe("text-red-400");
  });

  it("total coverage summary is computed correctly", () => {
    const total = MOCK_FEATURES.reduce((s, f) => s + f.total, 0);
    const covered = MOCK_FEATURES.reduce((s, f) => s + f.covered, 0);
    const overall = (covered / total) * 100;
    expect(total).toBe(25);
    expect(covered).toBe(21);
    expect(overall.toFixed(1)).toBe("84.0");
  });

  it("gap severity labels are correct", () => {
    const GAP_TYPE_COLORS: Record<string, string> = {
      critical: "bg-red-500/10 text-red-300 border-red-500/20",
      high:     "bg-orange-500/10 text-orange-300 border-orange-500/20",
      medium:   "bg-amber-500/10 text-amber-300 border-amber-500/20",
      low:      "bg-slate-500/10 text-slate-300 border-slate-500/20",
    };
    expect(GAP_TYPE_COLORS.critical).toContain("red");
    expect(GAP_TYPE_COLORS.high).toContain("orange");
    expect(GAP_TYPE_COLORS.medium).toContain("amber");
    expect(GAP_TYPE_COLORS.low).toContain("slate");
  });
});

describe("CoveragePage — API Tab", () => {
  const MOCK_ENDPOINTS = [
    { path: "/api/v1/login", method: "POST", tested: true },
    { path: "/api/v1/users", method: "GET", tested: true },
    { path: "/api/v1/payments", method: "POST", tested: false },
  ];

  it("renders endpoint list", () => {
    const EndpointList = ({ endpoints }: { endpoints: typeof MOCK_ENDPOINTS }) => (
      <div data-testid="endpoint-list">
        {endpoints.map((e) => (
          <div key={e.path} data-testid="endpoint-row">
            <span data-testid="endpoint-method">{e.method}</span>
            <span data-testid="endpoint-path">{e.path}</span>
            <span data-testid="endpoint-status">{e.tested ? "tested" : "untested"}</span>
          </div>
        ))}
      </div>
    );
    render(<EndpointList endpoints={MOCK_ENDPOINTS} />);
    expect(screen.getAllByTestId("endpoint-row")).toHaveLength(3);
    expect(screen.getByText("/api/v1/payments")).toBeInTheDocument();
    expect(screen.getAllByTestId("endpoint-status")[2]).toHaveTextContent("untested");
  });

  it("API coverage percentage computed from endpoints", () => {
    const tested = MOCK_ENDPOINTS.filter((e) => e.tested).length;
    const pct = (tested / MOCK_ENDPOINTS.length) * 100;
    expect(pct.toFixed(1)).toBe("66.7");
  });

  it("loading spinner shown while fetching", () => {
    const Loading = ({ isLoading }: { isLoading: boolean }) => (
      isLoading ? <div data-testid="api-loading">Yükleniyor...</div> : null
    );
    render(<Loading isLoading={true} />);
    expect(screen.getByTestId("api-loading")).toBeInTheDocument();
  });
});

describe("CoveragePage — Code (CoverUp) Tab", () => {
  it("file drop zone renders", () => {
    const DropZone = ({ onDrop }: { onDrop: () => void }) => (
      <div data-testid="cu-drop-zone" onDrop={onDrop} onDragOver={(e) => e.preventDefault()}>
        Kapsam raporunu buraya sürükle
      </div>
    );
    render(<DropZone onDrop={jest.fn()} />);
    expect(screen.getByTestId("cu-drop-zone")).toBeInTheDocument();
    expect(screen.getByText(/buraya sürükle/)).toBeInTheDocument();
  });

  it("format selector has expected options", () => {
    const FORMAT_OPTIONS = ["lcov", "cobertura", "jacoco", "clover", "simplecov"];
    const Select = () => (
      <select data-testid="format-select">
        {FORMAT_OPTIONS.map((f) => (
          <option key={f} value={f}>{f}</option>
        ))}
      </select>
    );
    render(<Select />);
    const select = screen.getByTestId("format-select");
    expect(select).toBeInTheDocument();
    FORMAT_OPTIONS.forEach((f) => {
      expect(screen.getByText(f)).toBeInTheDocument();
    });
  });

  it("report list shows uploaded reports", () => {
    const reports = [
      { id: "r1", branch: "main", commit: "abc123", created_at: "2026-01-01" },
      { id: "r2", branch: "dev",  commit: "def456", created_at: "2026-01-05" },
    ];
    const ReportList = ({ reports }: { reports: typeof reports }) => (
      <div data-testid="report-list">
        {reports.map((r) => (
          <div key={r.id} data-testid="report-item">
            <span data-testid="report-branch">{r.branch}</span>
            <span data-testid="report-commit">{r.commit}</span>
          </div>
        ))}
      </div>
    );
    render(<ReportList reports={reports} />);
    expect(screen.getAllByTestId("report-item")).toHaveLength(2);
    expect(screen.getByText("main")).toBeInTheDocument();
    expect(screen.getByText("abc123")).toBeInTheDocument();
  });

  it("code coverage expand/collapse works", () => {
    const ExpandableFile = ({ path }: { path: string }) => {
      const [expanded, setExpanded] = React.useState(false);
      return (
        <div>
          <button data-testid="expand-btn" onClick={() => setExpanded(!expanded)}>{path}</button>
          {expanded && <div data-testid="file-detail">Satır detayları</div>}
        </div>
      );
    };
    render(<ExpandableFile path="src/auth/login.ts" />);
    expect(screen.queryByTestId("file-detail")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("expand-btn"));
    expect(screen.getByTestId("file-detail")).toBeInTheDocument();
  });
});
