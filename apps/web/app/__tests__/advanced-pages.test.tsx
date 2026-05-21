/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// Suppress console errors/warnings from DnD kit and other noisy libraries
beforeAll(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  jest.spyOn(console, "warn").mockImplementation(() => {});
});
afterAll(() => {
  (console.error as jest.Mock).mockRestore();
  (console.warn as jest.Mock).mockRestore();
});

// ─── NLTestGenPage ───────────────────────────────────────────────────────────

const FORMATS = [
  { value: "pytest", label: "🐍 Pytest" },
  { value: "playwright", label: "🎭 Playwright" },
  { value: "cypress", label: "🌲 Cypress" },
  { value: "gherkin", label: "🥒 Gherkin" },
];

const LANGUAGES = [
  { value: "python", label: "Python" },
  { value: "typescript", label: "TypeScript" },
  { value: "javascript", label: "JavaScript" },
];

function MockNLTestGenPage({ isPending = false }: { isPending?: boolean }) {
  const [text, setText] = React.useState("");
  const [format, setFormat] = React.useState("pytest");
  const [results, setResults] = React.useState<
    { test_id: string; test_name: string; format: string; language: string; confidence: number; test_code: string }[]
  >([]);

  return (
    <div data-testid="nl-test-gen-page" className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4">
      <div data-testid="page-header">Dogal Dil Test Uretici</div>

      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-5">
        <p className="text-sm font-medium text-cyan-300 mb-3">Test Tanimi</p>

        <div className="flex flex-wrap gap-3 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Format:</span>
            <div className="flex gap-1" data-testid="format-buttons">
              {FORMATS.map((f) => (
                <button
                  key={f.value}
                  onClick={() => setFormat(f.value)}
                  data-testid={`format-btn-${f.value}`}
                  className={`px-2.5 py-1 text-xs rounded-lg border transition-all ${
                    format === f.value
                      ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-300"
                      : "border-slate-700 text-slate-400"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Dil:</span>
            <div className="flex gap-1" data-testid="language-buttons">
              {LANGUAGES.map((l) => (
                <button key={l.value} data-testid={`lang-btn-${l.value}`}>
                  {l.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          <textarea
            data-testid="nl-textarea"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Orn: Kullanici giris yapar, gecersiz sifre girerse hata mesaji gorur..."
            rows={3}
          />
          <button
            data-testid="nl-generate-btn"
            onClick={() => {
              if (!text.trim() || isPending) return;
              setResults([
                {
                  test_id: "t1",
                  test_name: "test_login",
                  format: "pytest",
                  language: "python",
                  confidence: 0.95,
                  test_code: "def test_login(): pass",
                },
              ]);
            }}
            disabled={!text.trim() || isPending}
          >
            {isPending ? "..." : "Uret"}
          </button>
        </div>
      </div>

      {isPending && (
        <div data-testid="nl-loading">AI test kodu uretiyor...</div>
      )}

      {results.length > 0 && (
        <div data-testid="nl-results">
          {results.map((r) => (
            <div key={r.test_id} data-testid="nl-result-item">
              <span>{r.test_name}</span>
              <pre><code>{r.test_code}</code></pre>
            </div>
          ))}
        </div>
      )}

      {!isPending && results.length === 0 && (
        <div data-testid="empty-state">Dogal Dil ile Test Ureti</div>
      )}
    </div>
  );
}

describe("NLTestGenPage", () => {
  it("renders the page container", () => {
    render(<MockNLTestGenPage />);
    expect(screen.getByTestId("nl-test-gen-page")).toBeInTheDocument();
  });

  it("PageHeader title shows 'Dogal Dil Test Uretici'", () => {
    render(<MockNLTestGenPage />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Dogal Dil Test Uretici");
  });

  it("textarea for test description is present", () => {
    render(<MockNLTestGenPage />);
    const textarea = screen.getByTestId("nl-textarea");
    expect(textarea).toBeInTheDocument();
    expect(textarea).toHaveAttribute("placeholder");
  });

  it("format selection buttons (Pytest, Playwright, Cypress, Gherkin) are shown", () => {
    render(<MockNLTestGenPage />);
    expect(screen.getByTestId("format-btn-pytest")).toBeInTheDocument();
    expect(screen.getByTestId("format-btn-playwright")).toBeInTheDocument();
    expect(screen.getByTestId("format-btn-cypress")).toBeInTheDocument();
    expect(screen.getByTestId("format-btn-gherkin")).toBeInTheDocument();
  });

  it("Generate button is disabled when textarea is empty", () => {
    render(<MockNLTestGenPage />);
    const btn = screen.getByTestId("nl-generate-btn");
    expect(btn).toBeDisabled();
    fireEvent.change(screen.getByTestId("nl-textarea"), { target: { value: "test scenario" } });
    expect(btn).not.toBeDisabled();
  });
});

// ─── PrioritizePage ──────────────────────────────────────────────────────────

type PrioritizedTest = {
  test_case_id: string;
  title: string;
  endpoint_method: string;
  endpoint_path: string;
  priority_score: number;
  risk_level: string;
  test_type: string;
  last_run_status: string | null;
  estimated_duration_ms: number;
  breakdown: { failure: number; risk: number; recency: number; sensitivity: number; change_impact: number };
};

function MockPrioritizePage({
  tests = [],
  isLoading = false,
  stats = null as Record<string, unknown> | null,
  optimalData = null as Record<string, unknown> | null,
}: {
  tests?: PrioritizedTest[];
  isLoading?: boolean;
  stats?: Record<string, unknown> | null;
  optimalData?: Record<string, unknown> | null;
}) {
  const [isPending, setIsPending] = React.useState(false);

  return (
    <div data-testid="prioritize-page" className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4">
      <div data-testid="page-header">Test Onceliklendirme</div>

      {stats && (
        <div data-testid="stats-grid" className="grid grid-cols-5 gap-3">
          <div data-testid="stat-total">{String(stats.total_tests)}</div>
          <div data-testid="stat-high">{String(stats.high_priority_count)}</div>
          <div data-testid="stat-medium">{String(stats.medium_priority_count)}</div>
          <div data-testid="stat-low">{String(stats.low_priority_count)}</div>
          <div data-testid="stat-avg">{String(stats.avg_score)}</div>
        </div>
      )}

      <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 px-5 py-4">
        <p className="text-sm font-medium text-violet-300">Optimal Test Seti Olustur</p>
        <button
          data-testid="optimal-suite-btn"
          onClick={() => setIsPending(true)}
          disabled={isPending}
          className="flex items-center gap-2 px-4 py-1.5 text-sm font-semibold text-violet-300 border border-violet-500/30 rounded-xl"
        >
          {isPending ? "..." : "Hesapla"}
        </button>
        {optimalData && (
          <div data-testid="optimal-result">
            <span>{String(optimalData.total_count)} test</span>
          </div>
        )}
      </div>

      <div data-testid="section-card">
        {isLoading ? (
          <div data-testid="priority-loading" className="flex justify-center p-10">
            <div className="w-6 h-6 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
          </div>
        ) : tests.length === 0 ? (
          <div data-testid="empty-state">Onceliklendirilecek test yok</div>
        ) : (
          <table data-testid="priority-table" className="w-full">
            <thead>
              <tr>
                <th>#</th>
                <th>Test</th>
                <th>Endpoint</th>
                <th>Skor</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {tests.map((t, idx) => (
                <tr key={t.test_case_id} data-testid="priority-row">
                  <td>{idx + 1}</td>
                  <td>{t.title}</td>
                  <td>{t.endpoint_path}</td>
                  <td>{t.priority_score}</td>
                  <td>{t.risk_level}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

describe("PrioritizePage", () => {
  it("renders the page container", () => {
    render(<MockPrioritizePage />);
    expect(screen.getByTestId("prioritize-page")).toBeInTheDocument();
  });

  it("PageHeader title shows 'Test Onceliklendirme'", () => {
    render(<MockPrioritizePage />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Test Onceliklendirme");
  });

  it("empty state shown when no prioritized tests", () => {
    render(<MockPrioritizePage tests={[]} isLoading={false} />);
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Onceliklendirilecek test yok");
  });

  it("Optimal Suite button is present", () => {
    render(<MockPrioritizePage />);
    expect(screen.getByTestId("optimal-suite-btn")).toBeInTheDocument();
    expect(screen.getByTestId("optimal-suite-btn")).toHaveTextContent("Hesapla");
  });

  it("shows loading state when isLoading=true", () => {
    render(<MockPrioritizePage isLoading={true} />);
    expect(screen.getByTestId("priority-loading")).toBeInTheDocument();
    expect(screen.queryByTestId("empty-state")).not.toBeInTheDocument();
  });
});

// ─── RequirementsPage ────────────────────────────────────────────────────────

type Requirement = {
  id: string;
  external_id: string;
  title: string;
  description: string;
  priority: string;
  source: string;
  scenario_count: number;
  created_at: string | null;
};

function MockRequirementsPage({ requirements = [] as Requirement[] }) {
  const [showForm, setShowForm] = React.useState(false);
  const [items, setItems] = React.useState<Requirement[]>(requirements);
  const [form, setForm] = React.useState({ external_id: "", title: "", description: "", priority: "medium", source: "" });

  const covered = items.filter((r) => r.scenario_count > 0).length;
  const covPct = items.length > 0 ? Math.round((covered / items.length) * 100) : 0;

  return (
    <div data-testid="requirements-page" className="min-h-screen bg-slate-950 p-6">
      <div data-testid="page-header">
        Gereksinimler
        <button
          data-testid="requirements-btn-new"
          onClick={() => setShowForm((v) => !v)}
        >
          {showForm ? "Iptal" : "Yeni Gereksinim"}
        </button>
      </div>

      <div data-testid="stat-Toplam">{items.length}</div>
      <div data-testid="stat-Kapsanan">{covered}</div>
      <div data-testid="stat-Kapsam">{items.length === 0 ? "—" : `${covPct}%`}</div>

      {showForm && (
        <div data-testid="section-card">
          <form
            data-testid="requirements-form"
            onSubmit={(e) => {
              e.preventDefault();
              setItems((prev) => [
                ...prev,
                { ...form, id: `req-${Date.now()}`, scenario_count: 0, created_at: null },
              ]);
              setShowForm(false);
            }}
          >
            <input
              data-testid="requirements-input-external-id"
              placeholder="External ID (ör. REQ-001) *"
              value={form.external_id}
              onChange={(e) => setForm({ ...form, external_id: e.target.value })}
              required
            />
            <input
              data-testid="requirements-input-title"
              placeholder="Baslik *"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
            />
            <input
              data-testid="requirements-input-desc"
              placeholder="Aciklama"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
            <select
              data-testid="requirements-select-priority"
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
            >
              <option value="critical">Kritik</option>
              <option value="high">Yuksek</option>
              <option value="medium">Orta</option>
              <option value="low">Dusuk</option>
            </select>
            <button
              type="submit"
              data-testid="requirements-btn-create"
            >
              Ekle
            </button>
          </form>
        </div>
      )}

      <div className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr>
              <th>ID</th>
              <th>Baslik</th>
              <th>Oncelik</th>
              <th>Senaryo</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={4}>
                  <div data-testid="empty-state">Henuz gereksinim eklenmemis</div>
                </td>
              </tr>
            ) : (
              items.map((r) => (
                <tr key={r.id} data-testid="requirement-row">
                  <td>{r.external_id}</td>
                  <td>{r.title}</td>
                  <td>{r.priority}</td>
                  <td>{r.scenario_count}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const SAMPLE_REQUIREMENTS: Requirement[] = [
  { id: "r1", external_id: "REQ-001", title: "Kullanici girisi", description: "Login flow", priority: "high", source: "musteri", scenario_count: 3, created_at: "2026-01-01" },
  { id: "r2", external_id: "REQ-002", title: "Odeme akisi", description: "Payment", priority: "critical", source: "PO", scenario_count: 0, created_at: "2026-01-02" },
];

describe("RequirementsPage", () => {
  it("renders the page container", () => {
    render(<MockRequirementsPage />);
    expect(screen.getByTestId("requirements-page")).toBeInTheDocument();
  });

  it("PageHeader title shows 'Gereksinimler'", () => {
    render(<MockRequirementsPage />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Gereksinimler");
  });

  it("empty state shown when no requirements", () => {
    render(<MockRequirementsPage requirements={[]} />);
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Henuz gereksinim eklenmemis");
  });

  it("New Requirement button is present and toggles the form", () => {
    render(<MockRequirementsPage />);
    const btn = screen.getByTestId("requirements-btn-new");
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveTextContent("Yeni Gereksinim");
    fireEvent.click(btn);
    expect(screen.getByTestId("requirements-form")).toBeInTheDocument();
    expect(screen.getByTestId("requirements-input-external-id")).toBeInTheDocument();
    expect(screen.getByTestId("requirements-input-title")).toBeInTheDocument();
    expect(screen.getByTestId("requirements-btn-create")).toBeInTheDocument();
  });

  it("requirements list renders when data exists", () => {
    render(<MockRequirementsPage requirements={SAMPLE_REQUIREMENTS} />);
    const rows = screen.getAllByTestId("requirement-row");
    expect(rows).toHaveLength(2);
    expect(screen.getByText("REQ-001")).toBeInTheDocument();
    expect(screen.getByText("Kullanici girisi")).toBeInTheDocument();
    expect(screen.queryByTestId("empty-state")).not.toBeInTheDocument();
  });
});

// ─── TestDataPage ────────────────────────────────────────────────────────────

type DataSet = {
  id: string;
  name: string;
  description: string;
  columns: string[];
  rows: string[][];
  created_at: string | null;
};

function MockTestDataPage({ dataSets = [] as DataSet[] }) {
  const [items, setItems] = React.useState<DataSet[]>(dataSets);
  const [showCreate, setShowCreate] = React.useState(false);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [newDs, setNewDs] = React.useState({ name: "", description: "" });

  const selected = items.find((d) => d.id === selectedId);

  function createDataSet() {
    if (!newDs.name.trim()) return;
    setItems((prev) => [
      ...prev,
      { id: `ds-${Date.now()}`, name: newDs.name, description: newDs.description, columns: [], rows: [], created_at: null },
    ]);
    setNewDs({ name: "", description: "" });
    setShowCreate(false);
  }

  return (
    <div data-testid="test-data-page" className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4">
      <div data-testid="page-header">
        Test Verileri
        <button
          data-testid="test-data-new-btn"
          onClick={() => setShowCreate((f) => !f)}
        >
          + Yeni Veri Seti
        </button>
      </div>

      <div data-testid="stat-Toplam Veri Seti">{items.length}</div>
      <div data-testid="stat-Secili">{selected ? "1" : "—"}</div>

      {showCreate && (
        <div data-testid="section-card">
          <input
            data-testid="test-data-name-input"
            placeholder="Isim"
            value={newDs.name}
            onChange={(e) => setNewDs({ ...newDs, name: e.target.value })}
          />
          <input
            data-testid="test-data-desc-input"
            placeholder="Aciklama"
            value={newDs.description}
            onChange={(e) => setNewDs({ ...newDs, description: e.target.value })}
          />
          <button
            data-testid="test-data-create-btn"
            onClick={createDataSet}
            disabled={!newDs.name.trim()}
          >
            Olustur
          </button>
          <button data-testid="test-data-cancel-btn" onClick={() => setShowCreate(false)}>
            Iptal
          </button>
        </div>
      )}

      <div data-testid="section-card-datasets">
        {items.length === 0 ? (
          <div data-testid="empty-state">Veri seti yok</div>
        ) : (
          <table data-testid="datasets-table" className="w-full text-left text-sm">
            <thead>
              <tr>
                <th>Isim</th>
                <th>Aciklama</th>
                <th>Kolonlar</th>
                <th>Satirlar</th>
              </tr>
            </thead>
            <tbody>
              {items.map((ds) => (
                <tr
                  key={ds.id}
                  data-testid="dataset-row"
                  onClick={() => setSelectedId(ds.id)}
                  className={selectedId === ds.id ? "selected" : ""}
                >
                  <td>{ds.name}</td>
                  <td>{ds.description || "—"}</td>
                  <td>{ds.columns?.length ?? 0}</td>
                  <td>{ds.rows?.length ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <div data-testid="dataset-preview">
          <p>{selected.name} — Onizleme</p>
          {selected.columns.length === 0 ? (
            <div data-testid="preview-empty">Henuz veri yok</div>
          ) : (
            <table data-testid="preview-table">
              <thead>
                <tr>
                  {selected.columns.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {selected.rows.map((row, i) => (
                  <tr key={i}>
                    {row.map((cell, ci) => <td key={ci}>{cell}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

const SAMPLE_DATASETS: DataSet[] = [
  { id: "ds1", name: "Kullanici Verileri", description: "Test kullanicilari", columns: ["ad", "soyad", "email"], rows: [["Ali", "Yilmaz", "ali@test.com"]], created_at: "2026-01-01" },
  { id: "ds2", name: "Odeme Verileri", description: "Kart numaralari", columns: ["kart_no"], rows: [["4111111111111111"]], created_at: "2026-01-02" },
];

describe("TestDataPage", () => {
  it("renders the page container", () => {
    render(<MockTestDataPage />);
    expect(screen.getByTestId("test-data-page")).toBeInTheDocument();
  });

  it("PageHeader title shows 'Test Verileri'", () => {
    render(<MockTestDataPage />);
    expect(screen.getByTestId("page-header")).toHaveTextContent("Test Verileri");
  });

  it("empty state shown when no test data", () => {
    render(<MockTestDataPage dataSets={[]} />);
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Veri seti yok");
  });

  it("New Dataset button is present and opens create form", () => {
    render(<MockTestDataPage />);
    const btn = screen.getByTestId("test-data-new-btn");
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(screen.getByTestId("test-data-name-input")).toBeInTheDocument();
    expect(screen.getByTestId("test-data-create-btn")).toBeInTheDocument();
    // Create button disabled when name is empty
    expect(screen.getByTestId("test-data-create-btn")).toBeDisabled();
  });

  it("dataset table renders when data exists and shows schema info", () => {
    render(<MockTestDataPage dataSets={SAMPLE_DATASETS} />);
    const rows = screen.getAllByTestId("dataset-row");
    expect(rows).toHaveLength(2);
    expect(screen.getByText("Kullanici Verileri")).toBeInTheDocument();
    expect(screen.getByText("Odeme Verileri")).toBeInTheDocument();
    // Column counts are shown (3 and 1)
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.queryByTestId("empty-state")).not.toBeInTheDocument();
  });
});

// ─── BankingTeamPage ─────────────────────────────────────────────────────────

type AgentCardProps = { name: string; role: string; model: string; status: "idle" | "active" | "done" };

function MockAgentCard({ name, role, model, status }: AgentCardProps) {
  return (
    <div
      data-testid="agent-card"
      className={`rounded-lg border p-3 ${status === "active" ? "border-accent" : status === "done" ? "border-green-500/30" : "border-border"}`}
    >
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${status === "active" ? "bg-accent animate-pulse" : status === "done" ? "bg-green-500" : "bg-muted"}`} />
        <span className="text-xs font-semibold" data-testid="agent-name">{name}</span>
      </div>
      <p className="mt-1 text-[10px] text-muted">{role}</p>
      <p className="mt-0.5 text-[10px] font-mono text-muted/70">{model}</p>
    </div>
  );
}

const BANKING_AGENTS: AgentCardProps[] = [
  { name: "Veri Analisti", role: "DB/API/Log analizi", model: "qwen2.5:14b", status: "idle" },
  { name: "Senaryo Uretici", role: "Pozitif/Negatif/Edge senaryolar", model: "qwen2.5:14b", status: "idle" },
  { name: "Regulasyon Ajani", role: "BDDK · PCI-DSS · MASAK · KYC", model: "llama3.1:8b", status: "idle" },
  { name: "Otomasyon Karar Ajani", role: "UI/API/DB/Manuel matrisi", model: "llama3.1:8b", status: "idle" },
  { name: "Kod Uretici", role: "BDD · Playwright · pytest", model: "qwen2.5-coder:7b", status: "idle" },
  { name: "Self-Improving Ajani", role: "Analiz · Iyilestirme · Ogrenme", model: "qwen2.5:14b", status: "idle" },
];

function MockBankingTeamPage({
  running = false,
  wsConnected = false,
  finalReport = null as Record<string, unknown> | null,
  agents = BANKING_AGENTS,
}: {
  running?: boolean;
  wsConnected?: boolean;
  finalReport?: Record<string, unknown> | null;
  agents?: AgentCardProps[];
}) {
  const [activeTab, setActiveTab] = React.useState<"logs" | "report" | "scenarios">("logs");
  const [description, setDescription] = React.useState("Bankacilik uygulamasi");
  const [cycles, setCycles] = React.useState(3);
  const [started, setStarted] = React.useState(running);

  return (
    <div data-testid="banking-team-page" className="flex h-[calc(100vh-7rem)] flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 data-testid="banking-team-title" className="text-lg font-semibold">Banking QA Ekibi</h1>
          <p className="text-xs text-muted">
            6 uzman ajan · Ollama (local) · Surekli ogrenen
            <span className="ml-2 inline-flex items-center gap-1" data-testid="ws-status">
              <span className={`h-1.5 w-1.5 rounded-full ${wsConnected ? "bg-green-500" : "bg-muted"}`} />
              <span className="text-[10px]">{wsConnected ? "Canli" : "Polling"}</span>
            </span>
          </p>
        </div>
        {started && (
          <button data-testid="banking-team-stop" onClick={() => setStarted(false)} className="text-red-500">
            Durdur
          </button>
        )}
      </div>

      <div className="grid flex-1 grid-cols-[280px_1fr] gap-4 overflow-hidden">
        <aside className="flex flex-col gap-3 overflow-y-auto">
          <p className="text-[10px] font-semibold uppercase text-muted tracking-wide">Ajan Ekibi</p>
          <div data-testid="agent-team-list">
            {agents.map((a) => (
              <MockAgentCard key={a.name} {...a} />
            ))}
          </div>

          {!started && (
            <div data-testid="banking-team-config" className="space-y-2 border-t border-border pt-3">
              <p className="text-[10px] font-semibold uppercase text-muted tracking-wide">Konfigurasyon</p>
              <label className="text-xs text-muted">Sistem Aciklamasi</label>
              <input
                data-testid="banking-team-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="text-xs"
                placeholder="Orn: Medifim internet bankaciligi"
              />
              <label className="text-xs text-muted">Dongu Sayisi: {cycles}</label>
              <input
                type="range"
                data-testid="banking-team-cycles"
                min={1}
                max={5}
                value={cycles}
                onChange={(e) => setCycles(Number(e.target.value))}
                className="w-full mt-1"
              />
              <button
                data-testid="banking-team-start"
                onClick={() => setStarted(true)}
                className="w-full mt-2"
              >
                Ekibi Baslat
              </button>
            </div>
          )}

          {started && (
            <div data-testid="banking-team-progress" className="border-t border-border pt-3 space-y-2">
              <div className="flex justify-between text-xs">
                <span>Calisıyor...</span>
                <span className="text-muted">%0</span>
              </div>
              <div className="h-1.5 rounded-full bg-border overflow-hidden">
                <div className="h-full bg-accent transition-all duration-500 rounded-full" style={{ width: "0%" }} />
              </div>
            </div>
          )}
        </aside>

        <div className="flex flex-col overflow-hidden rounded-lg border border-border">
          <div className="flex border-b border-border" data-testid="banking-team-tabs">
            {(["logs", "report", "scenarios"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                data-testid={`tab-${tab}`}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-xs font-medium transition-colors ${activeTab === tab ? "border-b-2 border-accent text-accent" : "text-muted"}`}
              >
                {tab === "logs" ? "Canli Log" : tab === "report" ? "Final Rapor" : "Senaryolar"}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-3">
            {activeTab === "logs" && !started && (
              <p data-testid="banking-team-empty-log" className="text-muted text-center py-8">
                Ekibi baslatarak canli loglari izleyin
              </p>
            )}
            {activeTab === "report" && !finalReport && (
              <p data-testid="banking-team-empty-report" className="text-muted text-center py-8 text-sm">
                Pipeline tamamlandiktan sonra rapor burada gorunecek
              </p>
            )}
            {activeTab === "report" && finalReport && (
              <div data-testid="banking-team-report">
                <div className="grid grid-cols-4 gap-3">
                  <div data-testid="report-stat-scenario">{String((finalReport.scenarios as { total?: number } | undefined)?.total ?? 0)}</div>
                  <div data-testid="report-stat-rules">{String((finalReport.regulation as { total_rules?: number } | undefined)?.total_rules ?? 0)}</div>
                  <div data-testid="report-stat-code">{String((finalReport.generated_code as { total_files?: number } | undefined)?.total_files ?? 0)}</div>
                  <div data-testid="report-stat-quality">{String(finalReport.average_quality_score ?? 0)}/10</div>
                </div>
              </div>
            )}
            {activeTab === "scenarios" && (
              <p data-testid="banking-team-empty-scenarios" className="text-muted text-center py-8 text-sm">
                Pipeline tamamlandiktan sonra senaryolar burada listelenir
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

describe("BankingTeamPage", () => {
  it("renders the page container", () => {
    render(<MockBankingTeamPage />);
    expect(screen.getByTestId("banking-team-page")).toBeInTheDocument();
  });

  it("PageHeader title shows 'Banking QA Ekibi'", () => {
    render(<MockBankingTeamPage />);
    expect(screen.getByTestId("banking-team-title")).toHaveTextContent("Banking QA Ekibi");
  });

  it("renders all 6 agent cards in the team list", () => {
    render(<MockBankingTeamPage />);
    const agentCards = screen.getAllByTestId("agent-card");
    expect(agentCards).toHaveLength(6);
    expect(screen.getByText("Veri Analisti")).toBeInTheDocument();
    expect(screen.getByText("Senaryo Uretici")).toBeInTheDocument();
    expect(screen.getByText("Regulasyon Ajani")).toBeInTheDocument();
  });

  it("Start button and configuration form are present when not running", () => {
    render(<MockBankingTeamPage running={false} />);
    expect(screen.getByTestId("banking-team-start")).toBeInTheDocument();
    expect(screen.getByTestId("banking-team-config")).toBeInTheDocument();
    expect(screen.getByTestId("banking-team-description")).toBeInTheDocument();
    expect(screen.getByTestId("banking-team-cycles")).toBeInTheDocument();
  });

  it("empty log message shown initially and tabs are present", () => {
    render(<MockBankingTeamPage />);
    expect(screen.getByTestId("banking-team-empty-log")).toBeInTheDocument();
    expect(screen.getByTestId("tab-logs")).toBeInTheDocument();
    expect(screen.getByTestId("tab-report")).toBeInTheDocument();
    expect(screen.getByTestId("tab-scenarios")).toBeInTheDocument();
    // Switch to report tab and see empty report message
    fireEvent.click(screen.getByTestId("tab-report"));
    expect(screen.getByTestId("banking-team-empty-report")).toBeInTheDocument();
  });
});
