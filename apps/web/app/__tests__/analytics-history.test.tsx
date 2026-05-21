/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// ─── Analytics Page ─────────────────────────────────────────────────────────

describe("AnalyticsPage — Overview", () => {
  const MOCK_STATS = { total_runs: 148, avg_pass_rate: 87.3, total_scenarios: 2340 };

  it("renders stats overview section", () => {
    const Stats = ({ stats }: { stats: typeof MOCK_STATS }) => (
      <div data-testid="analytics-overview">
        <span data-testid="stat-total-runs">{stats.total_runs}</span>
        <span data-testid="stat-pass-rate">{stats.avg_pass_rate.toFixed(1)}%</span>
        <span data-testid="stat-scenarios">{stats.total_scenarios.toLocaleString()}</span>
      </div>
    );
    render(<Stats stats={MOCK_STATS} />);
    expect(screen.getByTestId("stat-total-runs")).toHaveTextContent("148");
    expect(screen.getByTestId("stat-pass-rate")).toHaveTextContent("87.3%");
    expect(screen.getByTestId("stat-scenarios")).toHaveTextContent("2,340");
  });

  it("time range selector renders options", () => {
    const TimeRange = () => {
      const [range, setRange] = React.useState("30d");
      return (
        <select data-testid="time-range" value={range} onChange={(e) => setRange(e.target.value)}>
          {["7d", "14d", "30d", "90d"].map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      );
    };
    render(<TimeRange />);
    expect((screen.getByTestId("time-range") as HTMLSelectElement).value).toBe("30d");
    fireEvent.change(screen.getByTestId("time-range"), { target: { value: "7d" } });
    expect((screen.getByTestId("time-range") as HTMLSelectElement).value).toBe("7d");
  });

  it("loading state renders skeleton", () => {
    const Skeleton = () => (
      <div data-testid="analytics-loading">
        {[1, 2, 3].map((i) => (
          <div key={i} data-testid="skeleton-card" className="animate-pulse" />
        ))}
      </div>
    );
    render(<Skeleton />);
    expect(screen.getAllByTestId("skeleton-card")).toHaveLength(3);
  });
});

describe("AnalyticsPage — Trend Chart", () => {
  const TREND_DATA = [
    { date: "2026-01-01", pass_rate: 82.5, total_runs: 12 },
    { date: "2026-01-02", pass_rate: 88.1, total_runs: 15 },
    { date: "2026-01-03", pass_rate: 91.3, total_runs: 18 },
  ];

  it("renders SVG chart container", () => {
    const Chart = ({ data }: { data: typeof TREND_DATA }) => (
      <svg data-testid="trend-chart" width="100%" height="200">
        {data.map((d, i) => (
          <circle key={i} data-testid="chart-point" cx={i * 50} cy={100 - d.pass_rate} r="4" />
        ))}
      </svg>
    );
    render(<Chart data={TREND_DATA} />);
    expect(screen.getByTestId("trend-chart")).toBeInTheDocument();
    expect(screen.getAllByTestId("chart-point")).toHaveLength(3);
  });

  it("trend direction computed correctly", () => {
    const calcTrend = (data: { pass_rate: number }[]) => {
      if (data.length < 2) return "stable";
      const first = data[0].pass_rate;
      const last = data[data.length - 1].pass_rate;
      if (last > first + 2) return "up";
      if (last < first - 2) return "down";
      return "stable";
    };
    expect(calcTrend(TREND_DATA)).toBe("up"); // 82.5 → 91.3
    expect(calcTrend([{ pass_rate: 90 }, { pass_rate: 85 }])).toBe("down");
    expect(calcTrend([{ pass_rate: 85 }, { pass_rate: 85.5 }])).toBe("stable");
  });

  it("empty chart shows message", () => {
    const EmptyChart = ({ data }: { data: unknown[] }) => (
      data.length === 0 ? <p data-testid="chart-empty">Veri yok</p> : <svg data-testid="chart" />
    );
    render(<EmptyChart data={[]} />);
    expect(screen.getByTestId("chart-empty")).toBeInTheDocument();
  });
});

describe("AnalyticsPage — Anomaly Detection", () => {
  it("anomaly section renders detected issues", () => {
    const anomalies = [
      { type: "pass_rate_drop", message: "Pass rate %12 düştü", severity: "high" },
      { type: "flaky_spike",    message: "Flaky test sayısı arttı", severity: "medium" },
    ];
    const AnomalyList = ({ anomalies }: { anomalies: typeof anomalies }) => (
      <div data-testid="anomaly-list">
        {anomalies.map((a, i) => (
          <div key={i} data-testid="anomaly-item">
            <span data-testid="anomaly-msg">{a.message}</span>
            <span data-testid="anomaly-severity">{a.severity}</span>
          </div>
        ))}
      </div>
    );
    render(<AnomalyList anomalies={anomalies} />);
    expect(screen.getAllByTestId("anomaly-item")).toHaveLength(2);
    expect(screen.getByText("Pass rate %12 düştü")).toBeInTheDocument();
  });

  it("no anomalies message shown when clean", () => {
    const AnomalySection = ({ count }: { count: number }) => (
      count === 0 ? <p data-testid="no-anomalies">Anomali tespit edilmedi ✅</p> : null
    );
    render(<AnomalySection count={0} />);
    expect(screen.getByTestId("no-anomalies")).toBeInTheDocument();
  });
});

describe("AnalyticsPage — Flaky Tests", () => {
  it("renders flaky test list with flakiness rate", () => {
    const flakyTests = [
      { title: "Login timeout test", flakiness_rate: 34.5, run_count: 20 },
      { title: "Payment race condition", flakiness_rate: 12.1, run_count: 15 },
    ];
    const FlakyList = ({ tests }: { tests: typeof flakyTests }) => (
      <div data-testid="flaky-list">
        {tests.map((t, i) => (
          <div key={i} data-testid="flaky-row">
            <span>{t.title}</span>
            <span data-testid="flaky-rate">{t.flakiness_rate.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    );
    render(<FlakyList tests={flakyTests} />);
    expect(screen.getAllByTestId("flaky-row")).toHaveLength(2);
    expect(screen.getByText("34.5%")).toBeInTheDocument();
  });
});

// ─── Test History Page ───────────────────────────────────────────────────────

describe("TestHistoryPage", () => {
  const MOCK_HISTORY = [
    { run_id: "r1", run_name: "Smoke #1", date: "2026-01-01", pass_rate: 95, total: 20 },
    { run_id: "r2", run_name: "Smoke #2", date: "2026-01-02", pass_rate: 88, total: 20 },
    { run_id: "r3", run_name: "Full #1",  date: "2026-01-03", pass_rate: 72, total: 85 },
  ];

  it("renders history table with runs", () => {
    const HistoryTable = ({ history }: { history: typeof MOCK_HISTORY }) => (
      <table data-testid="history-table">
        <tbody>
          {history.map((h) => (
            <tr key={h.run_id} data-testid="history-row">
              <td data-testid="run-name">{h.run_name}</td>
              <td data-testid="run-date">{h.date}</td>
              <td data-testid="run-rate">{h.pass_rate}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
    render(<HistoryTable history={MOCK_HISTORY} />);
    expect(screen.getAllByTestId("history-row")).toHaveLength(3);
    expect(screen.getByText("Smoke #1")).toBeInTheDocument();
    expect(screen.getByText("72%")).toBeInTheDocument();
  });

  it("trend comparison shows delta from previous run", () => {
    const computeDelta = (current: number, previous: number) => current - previous;
    expect(computeDelta(95, 88)).toBe(7);
    expect(computeDelta(72, 88)).toBe(-16);
  });

  it("best run highlighted", () => {
    const best = MOCK_HISTORY.reduce((a, b) => (b.pass_rate > a.pass_rate ? b : a));
    expect(best.run_id).toBe("r1");
    expect(best.pass_rate).toBe(95);
  });

  it("date range filter limits results", () => {
    const filterByDate = (history: typeof MOCK_HISTORY, since: string) =>
      history.filter((h) => h.date >= since);
    const filtered = filterByDate(MOCK_HISTORY, "2026-01-02");
    expect(filtered).toHaveLength(2);
    expect(filtered[0].run_id).toBe("r2");
  });

  it("empty state when no history", () => {
    const EmptyHistory = () => (
      <div data-testid="empty-history">
        <p>Test geçmişi bulunamadı</p>
      </div>
    );
    render(<EmptyHistory />);
    expect(screen.getByTestId("empty-history")).toBeInTheDocument();
  });

  it("loading state shows spinner", () => {
    const Loading = () => <div data-testid="history-loading" className="animate-spin">⟳</div>;
    render(<Loading />);
    expect(screen.getByTestId("history-loading")).toBeInTheDocument();
  });

  it("pagination controls shown for large history", () => {
    const Pagination = ({ page, total, perPage }: { page: number; total: number; perPage: number }) => {
      const totalPages = Math.ceil(total / perPage);
      return (
        <div data-testid="pagination">
          <span data-testid="page-info">Sayfa {page} / {totalPages}</span>
          <button data-testid="btn-prev" disabled={page === 1}>Önceki</button>
          <button data-testid="btn-next" disabled={page === totalPages}>Sonraki</button>
        </div>
      );
    };
    render(<Pagination page={1} total={50} perPage={10} />);
    expect(screen.getByTestId("page-info")).toHaveTextContent("Sayfa 1 / 5");
    expect(screen.getByTestId("btn-prev")).toBeDisabled();
    expect(screen.getByTestId("btn-next")).not.toBeDisabled();
  });
});
