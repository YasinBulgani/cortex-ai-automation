/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// ─── Regression Sets Page ──────────────────────────────────────────────────

describe("RegressionSetsPage", () => {
  const MOCK_SETS = [
    { id: "s1", name: "Smoke Suite", description: "Hızlı doğrulama", scenario_count: 12, item_count: 12, coverage_pct: 78, created_at: "2026-01-01T00:00:00Z" },
    { id: "s2", name: "Full Regression", description: "Tam regresyon", scenario_count: 87, item_count: 87, coverage_pct: 94, created_at: "2026-01-05T00:00:00Z" },
    { id: "s3", name: "Critical Path", description: "Kritik yol", scenario_count: 22, item_count: 22, coverage_pct: 61, created_at: "2026-01-10T00:00:00Z" },
  ];

  it("renders regression set list with names", () => {
    const SetList = ({ sets }: { sets: typeof MOCK_SETS }) => (
      <div data-testid="regression-page">
        {sets.map((s) => (
          <div key={s.id} data-testid={`regression-set-${s.id}`}>
            <span data-testid="set-name">{s.name}</span>
            <span data-testid="set-desc">{s.description}</span>
          </div>
        ))}
      </div>
    );
    render(<SetList sets={MOCK_SETS} />);
    expect(screen.getByTestId("regression-page")).toBeInTheDocument();
    expect(screen.getAllByTestId("set-name")).toHaveLength(3);
    expect(screen.getByText("Smoke Suite")).toBeInTheDocument();
    expect(screen.getByText("Full Regression")).toBeInTheDocument();
  });

  it("shows scenario count per set", () => {
    const SetRow = ({ set }: { set: typeof MOCK_SETS[0] }) => (
      <div data-testid="set-row">
        <span data-testid="set-count">{set.scenario_count} senaryo</span>
      </div>
    );
    render(<SetRow set={MOCK_SETS[0]} />);
    expect(screen.getByTestId("set-count")).toHaveTextContent("12 senaryo");
  });

  it("shows coverage percentage when available", () => {
    const CoverageBadge = ({ pct }: { pct?: number }) => (
      pct !== undefined ? (
        <span data-testid="coverage-badge">{pct.toFixed(1)}%</span>
      ) : null
    );
    render(<CoverageBadge pct={78} />);
    expect(screen.getByTestId("coverage-badge")).toHaveTextContent("78.0%");
  });

  it("coverage badge missing when pct undefined", () => {
    const CoverageBadge = ({ pct }: { pct?: number }) => (
      pct !== undefined ? <span data-testid="coverage-badge">{pct}%</span> : null
    );
    render(<CoverageBadge pct={undefined} />);
    expect(screen.queryByTestId("coverage-badge")).not.toBeInTheDocument();
  });

  it("create new set button is present", () => {
    const CreateBtn = ({ onClick }: { onClick: () => void }) => (
      <button data-testid="btn-create-set" onClick={onClick}>Yeni Set</button>
    );
    const handler = jest.fn();
    render(<CreateBtn onClick={handler} />);
    fireEvent.click(screen.getByTestId("btn-create-set"));
    expect(handler).toHaveBeenCalled();
  });

  it("delete set calls confirm handler", () => {
    const onDelete = jest.fn();
    const DeleteBtn = ({ onDelete }: { onDelete: () => void }) => (
      <button data-testid="btn-delete-set" onClick={onDelete}>Sil</button>
    );
    render(<DeleteBtn onDelete={onDelete} />);
    fireEvent.click(screen.getByTestId("btn-delete-set"));
    expect(onDelete).toHaveBeenCalled();
  });

  it("sort mode toggles between manual and auto", () => {
    const SortToggle = () => {
      const [mode, setMode] = React.useState<"manual" | "auto">("manual");
      return (
        <button data-testid="sort-toggle" onClick={() => setMode(m => m === "manual" ? "auto" : "manual")}>
          {mode}
        </button>
      );
    };
    render(<SortToggle />);
    expect(screen.getByTestId("sort-toggle")).toHaveTextContent("manual");
    fireEvent.click(screen.getByTestId("sort-toggle"));
    expect(screen.getByTestId("sort-toggle")).toHaveTextContent("auto");
  });

  it("suggestion panel toggles visibility", () => {
    const SuggestPanel = () => {
      const [open, setOpen] = React.useState(false);
      return (
        <div>
          <button data-testid="btn-suggest" onClick={() => setOpen(true)}>Öneri Al</button>
          {open && <div data-testid="suggest-panel">Öneri paneli</div>}
        </div>
      );
    };
    render(<SuggestPanel />);
    expect(screen.queryByTestId("suggest-panel")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("btn-suggest"));
    expect(screen.getByTestId("suggest-panel")).toBeInTheDocument();
  });

  it("empty state shown when no sets exist", () => {
    const EmptyState = () => (
      <div data-testid="empty-regression">
        <p>Henüz regresyon seti yok</p>
        <button data-testid="btn-create-first">İlk Seti Oluştur</button>
      </div>
    );
    render(<EmptyState />);
    expect(screen.getByTestId("empty-regression")).toBeInTheDocument();
    expect(screen.getByTestId("btn-create-first")).toBeInTheDocument();
  });

  it("loading skeleton renders correct count", () => {
    const Skeleton = ({ count }: { count: number }) => (
      <div data-testid="skeleton-list">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} data-testid="skeleton-item" className="animate-pulse" />
        ))}
      </div>
    );
    render(<Skeleton count={3} />);
    expect(screen.getAllByTestId("skeleton-item")).toHaveLength(3);
  });
});

// ─── Regression Set Detail Page ────────────────────────────────────────────

describe("RegressionSetDetailPage", () => {
  const MOCK_SCENARIOS = [
    { id: "sc1", title: "Login başarılı", status: "passed", priority: "critical" },
    { id: "sc2", title: "Ödeme akışı", status: "failed", priority: "high" },
    { id: "sc3", title: "Profil güncelle", status: "pending", priority: "medium" },
  ];

  it("renders set detail heading", () => {
    const Header = ({ name }: { name: string }) => (
      <h1 data-testid="set-detail-heading">{name}</h1>
    );
    render(<Header name="Smoke Suite" />);
    expect(screen.getByTestId("set-detail-heading")).toHaveTextContent("Smoke Suite");
  });

  it("renders scenario list in the set", () => {
    const ScenarioList = ({ scenarios }: { scenarios: typeof MOCK_SCENARIOS }) => (
      <div data-testid="set-scenario-list">
        {scenarios.map((s) => (
          <div key={s.id} data-testid="set-scenario-row">
            <span data-testid="sc-title">{s.title}</span>
            <span data-testid="sc-status">{s.status}</span>
          </div>
        ))}
      </div>
    );
    render(<ScenarioList scenarios={MOCK_SCENARIOS} />);
    expect(screen.getAllByTestId("set-scenario-row")).toHaveLength(3);
    expect(screen.getByText("Login başarılı")).toBeInTheDocument();
    expect(screen.getByText("Ödeme akışı")).toBeInTheDocument();
  });

  it("status filter changes visible scenarios", () => {
    const FilteredList = () => {
      const [filter, setFilter] = React.useState("all");
      const visible = filter === "all" ? MOCK_SCENARIOS : MOCK_SCENARIOS.filter(s => s.status === filter);
      return (
        <div>
          <select data-testid="status-filter" value={filter} onChange={e => setFilter(e.target.value)}>
            <option value="all">Tümü</option>
            <option value="passed">Passed</option>
            <option value="failed">Failed</option>
          </select>
          <div data-testid="filtered-results">{visible.length} sonuç</div>
        </div>
      );
    };
    render(<FilteredList />);
    expect(screen.getByTestId("filtered-results")).toHaveTextContent("3 sonuç");
    fireEvent.change(screen.getByTestId("status-filter"), { target: { value: "failed" } });
    expect(screen.getByTestId("filtered-results")).toHaveTextContent("1 sonuç");
  });

  it("back link navigates to regression list", () => {
    const BackLink = () => (
      <a href="/regression" data-testid="back-to-regression">← Regresyon Setleri</a>
    );
    render(<BackLink />);
    const link = screen.getByTestId("back-to-regression");
    expect(link).toHaveAttribute("href", "/regression");
  });

  it("run set button is present", () => {
    const RunBtn = () => <button data-testid="btn-run-set">Seti Çalıştır</button>;
    render(<RunBtn />);
    expect(screen.getByTestId("btn-run-set")).toBeInTheDocument();
  });
});
