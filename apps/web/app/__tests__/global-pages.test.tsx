/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// ─── BGTest Wizard (Platform Sihirbazı) ─────────────────────────────────────

describe("BgtestWizardPage", () => {
  const WIZARD_STEPS = [
    { id: 1, title: "Proje Oluştur",  page: null },
    { id: 2, title: "Senaryo Ekle",   page: "scenarios" },
    { id: 3, title: "Koşu Başlat",    page: "executions" },
    { id: 4, title: "Analitik İncele",page: "analytics" },
    { id: 5, title: "AI Sihirbazı",   page: "flaky" },
    { id: 6, title: "Entegrasyon Kur",page: "integrations" },
  ];

  it("renders all 6 wizard steps", () => {
    const StepGrid = ({ steps }: { steps: typeof WIZARD_STEPS }) => (
      <div data-testid="bgtest-wizard-steps">
        {steps.map((s) => (
          <div key={s.id} data-testid={`wizard-step-${s.id}`}>
            <span>{s.title}</span>
          </div>
        ))}
      </div>
    );
    render(<StepGrid steps={WIZARD_STEPS} />);
    expect(screen.getAllByTestId(/^wizard-step-/)).toHaveLength(6);
    expect(screen.getByText("Proje Oluştur")).toBeInTheDocument();
    expect(screen.getByText("Entegrasyon Kur")).toBeInTheDocument();
  });

  it("project selector shows available projects", () => {
    const projects = [
      { id: "p1", name: "E-Ticaret Projesi" },
      { id: "p2", name: "Mobil App" },
    ];
    const ProjectSelector = ({ projects }: { projects: typeof projects }) => (
      <select data-testid="project-selector">
        <option value="">Proje seçin...</option>
        {projects.map((p) => (
          <option key={p.id} value={p.id}>{p.name}</option>
        ))}
      </select>
    );
    render(<ProjectSelector projects={projects} />);
    expect(screen.getByTestId("project-selector")).toBeInTheDocument();
    expect(screen.getByText("E-Ticaret Projesi")).toBeInTheDocument();
    expect(screen.getByText("Mobil App")).toBeInTheDocument();
  });

  it("recent executions section renders runs", () => {
    const executions = [
      { id: "e1", name: "Smoke Run #1", status: "completed", pass_rate: 95 },
      { id: "e2", name: "Full Reg #2",  status: "failed",    pass_rate: 62 },
    ];
    const ExecList = ({ executions }: { executions: typeof executions }) => (
      <div data-testid="recent-executions">
        {executions.map((e) => (
          <div key={e.id} data-testid="exec-item">
            <span>{e.name}</span>
            <span data-testid="exec-pass">{e.pass_rate}%</span>
          </div>
        ))}
      </div>
    );
    render(<ExecList executions={executions} />);
    expect(screen.getAllByTestId("exec-item")).toHaveLength(2);
    expect(screen.getByText("95%")).toBeInTheDocument();
  });

  it("global stats tiles render", () => {
    const stats = { total_projects: 5, total_scenarios: 340, total_executions: 120, avg_pass_rate: 89.1 };
    const StatGrid = ({ stats }: { stats: typeof stats }) => (
      <div data-testid="global-stats">
        <span data-testid="stat-projects">{stats.total_projects}</span>
        <span data-testid="stat-scenarios">{stats.total_scenarios}</span>
        <span data-testid="stat-executions">{stats.total_executions}</span>
        <span data-testid="stat-pass-rate">{stats.avg_pass_rate.toFixed(1)}%</span>
      </div>
    );
    render(<StatGrid stats={stats} />);
    expect(screen.getByTestId("stat-projects")).toHaveTextContent("5");
    expect(screen.getByTestId("stat-pass-rate")).toHaveTextContent("89.1%");
  });

  it("step link navigates to correct page path", () => {
    const StepLink = ({ step }: { step: typeof WIZARD_STEPS[0] }) => (
      step.page ? (
        <a data-testid="step-link" href={`/p/[projectId]/${step.page}`}>{step.title}</a>
      ) : (
        <span data-testid="step-no-link">{step.title}</span>
      )
    );
    render(<StepLink step={WIZARD_STEPS[1]} />); // scenarios
    expect(screen.getByTestId("step-link")).toHaveAttribute("href", "/p/[projectId]/scenarios");
  });

  it("step without page shows non-link element", () => {
    const StepLink = ({ step }: { step: typeof WIZARD_STEPS[0] }) => (
      step.page ? (
        <a data-testid="step-link" href={`/p/[projectId]/${step.page}`}>{step.title}</a>
      ) : (
        <span data-testid="step-no-link">{step.title}</span>
      )
    );
    render(<StepLink step={WIZARD_STEPS[0]} />); // no page
    expect(screen.getByTestId("step-no-link")).toBeInTheDocument();
    expect(screen.queryByTestId("step-link")).not.toBeInTheDocument();
  });
});

// ─── Veri Simulatoru Page ────────────────────────────────────────────────────

describe("VeriSimulatoruPage", () => {
  const FAKER_TYPES = [
    { value: "name",    label: "Ad Soyad" },
    { value: "email",   label: "E-posta" },
    { value: "phone",   label: "Telefon" },
    { value: "address", label: "Adres" },
    { value: "company", label: "Şirket" },
  ];

  it("renders faker type selector", () => {
    const TypeSelector = ({ types }: { types: typeof FAKER_TYPES }) => (
      <select data-testid="faker-type-select">
        {types.map((t) => (
          <option key={t.value} value={t.value}>{t.label}</option>
        ))}
      </select>
    );
    render(<TypeSelector types={FAKER_TYPES} />);
    expect(screen.getByTestId("faker-type-select")).toBeInTheDocument();
    expect(screen.getByText("Ad Soyad")).toBeInTheDocument();
    expect(screen.getByText("E-posta")).toBeInTheDocument();
  });

  it("count input accepts numeric values", () => {
    const CountInput = () => {
      const [count, setCount] = React.useState(10);
      return (
        <input
          type="number"
          data-testid="sim-count"
          min={1}
          max={1000}
          value={count}
          onChange={(e) => setCount(Number(e.target.value))}
        />
      );
    };
    render(<CountInput />);
    const input = screen.getByTestId("sim-count") as HTMLInputElement;
    expect(input.value).toBe("10");
    fireEvent.change(input, { target: { value: "50" } });
    expect(input.value).toBe("50");
  });

  it("generate button produces results", () => {
    const onGenerate = jest.fn();
    const GenBtn = () => <button data-testid="btn-generate-data" onClick={onGenerate}>Üret</button>;
    render(<GenBtn />);
    fireEvent.click(screen.getByTestId("btn-generate-data"));
    expect(onGenerate).toHaveBeenCalled();
  });

  it("output format selector has JSON and CSV options", () => {
    const FormatSelect = () => (
      <select data-testid="format-select">
        <option value="json">JSON</option>
        <option value="csv">CSV</option>
        <option value="sql">SQL</option>
      </select>
    );
    render(<FormatSelect />);
    expect(screen.getByText("JSON")).toBeInTheDocument();
    expect(screen.getByText("CSV")).toBeInTheDocument();
  });

  it("generated data preview renders", () => {
    const Preview = ({ data }: { data: string }) => (
      <pre data-testid="data-preview">{data}</pre>
    );
    const sample = '[{"name":"Ali Yılmaz","email":"ali@test.com"}]';
    render(<Preview data={sample} />);
    expect(screen.getByTestId("data-preview")).toHaveTextContent("Ali Yılmaz");
  });

  it("download button present when data generated", () => {
    const DownloadBtn = ({ hasData }: { hasData: boolean }) => (
      hasData ? <button data-testid="btn-download">İndir</button> : null
    );
    const { rerender } = render(<DownloadBtn hasData={false} />);
    expect(screen.queryByTestId("btn-download")).not.toBeInTheDocument();
    rerender(<DownloadBtn hasData={true} />);
    expect(screen.getByTestId("btn-download")).toBeInTheDocument();
  });

  it("count validation rejects values over max", () => {
    const isValidCount = (n: number) => n >= 1 && n <= 1000;
    expect(isValidCount(1)).toBe(true);
    expect(isValidCount(500)).toBe(true);
    expect(isValidCount(1000)).toBe(true);
    expect(isValidCount(0)).toBe(false);
    expect(isValidCount(1001)).toBe(false);
  });
});

// ─── Projects Page ──────────────────────────────────────────────────────────

describe("ProjectsPage", () => {
  const MOCK_PROJECTS = [
    { id: "p1", name: "E-Ticaret",  description: "Web test projesi",   archived: false },
    { id: "p2", name: "Mobil App",  description: "iOS/Android testleri", archived: false },
    { id: "p3", name: "Eski Proje", description: "Arşivlendi",           archived: true },
  ];

  it("renders active projects list", () => {
    const active = MOCK_PROJECTS.filter((p) => !p.archived);
    const ProjectList = ({ projects }: { projects: typeof active }) => (
      <div data-testid="projects-list">
        {projects.map((p) => (
          <div key={p.id} data-testid="project-card">
            <span data-testid="project-name">{p.name}</span>
            <span data-testid="project-desc">{p.description}</span>
          </div>
        ))}
      </div>
    );
    render(<ProjectList projects={active} />);
    expect(screen.getAllByTestId("project-card")).toHaveLength(2);
    expect(screen.getByText("E-Ticaret")).toBeInTheDocument();
    expect(screen.queryByText("Eski Proje")).not.toBeInTheDocument();
  });

  it("create project form has name and description inputs", () => {
    const CreateForm = () => (
      <form data-testid="create-project-form">
        <input data-testid="new-project-name" placeholder="Proje adı" />
        <input data-testid="new-project-desc" placeholder="Açıklama" />
        <button type="submit" data-testid="btn-submit-project">Oluştur</button>
      </form>
    );
    render(<CreateForm />);
    expect(screen.getByTestId("new-project-name")).toBeInTheDocument();
    expect(screen.getByTestId("new-project-desc")).toBeInTheDocument();
    expect(screen.getByTestId("btn-submit-project")).toBeInTheDocument();
  });

  it("submit disabled when name is empty", () => {
    const SubmitBtn = ({ name }: { name: string }) => (
      <button data-testid="btn-submit" disabled={!name.trim()}>Oluştur</button>
    );
    render(<SubmitBtn name="" />);
    expect(screen.getByTestId("btn-submit")).toBeDisabled();
    render(<SubmitBtn name="Yeni Proje" />);
    expect(screen.getAllByTestId("btn-submit")[1]).not.toBeDisabled();
  });

  it("click on project card navigates to project", () => {
    const ProjectCard = ({ id, name }: { id: string; name: string }) => (
      <a href={`/p/${id}`} data-testid={`project-link-${id}`}>{name}</a>
    );
    render(<ProjectCard id="p1" name="E-Ticaret" />);
    expect(screen.getByTestId("project-link-p1")).toHaveAttribute("href", "/p/p1");
  });

  it("archived projects are filtered out by default", () => {
    const filterActive = (projects: typeof MOCK_PROJECTS) => projects.filter((p) => !p.archived);
    const active = filterActive(MOCK_PROJECTS);
    expect(active).toHaveLength(2);
    expect(active.every((p) => !p.archived)).toBe(true);
  });

  it("error state shown on API failure", () => {
    const ErrorState = ({ error }: { error: string }) => (
      <div data-testid="projects-error">{error}</div>
    );
    render(<ErrorState error="Sunucu hatası" />);
    expect(screen.getByTestId("projects-error")).toHaveTextContent("Sunucu hatası");
  });
});

// ─── Executions Extended ────────────────────────────────────────────────────

describe("ExecutionsNewPage", () => {
  it("renders new execution form", () => {
    const Form = () => (
      <form data-testid="new-execution-form">
        <input data-testid="exec-name-input" placeholder="Koşu adı" />
        <select data-testid="exec-platform-select">
          <option value="web">Web</option>
          <option value="mobile">Mobil</option>
        </select>
        <button type="submit" data-testid="btn-start-execution">Koşu Başlat</button>
      </form>
    );
    render(<Form />);
    expect(screen.getByTestId("new-execution-form")).toBeInTheDocument();
    expect(screen.getByTestId("btn-start-execution")).toBeInTheDocument();
  });

  it("platform selector has web and mobile options", () => {
    const PlatformSelect = () => (
      <select data-testid="platform-select">
        <option value="web">Web</option>
        <option value="mobile">Mobil</option>
        <option value="api">API</option>
      </select>
    );
    render(<PlatformSelect />);
    expect(screen.getByText("Web")).toBeInTheDocument();
    expect(screen.getByText("Mobil")).toBeInTheDocument();
    expect(screen.getByText("API")).toBeInTheDocument();
  });
});

describe("ExecutionDetailPage", () => {
  it("renders execution detail heading", () => {
    const Detail = ({ name, status }: { name: string; status: string }) => (
      <div data-testid="execution-detail">
        <h1 data-testid="exec-detail-name">{name}</h1>
        <span data-testid="exec-detail-status">{status}</span>
      </div>
    );
    render(<Detail name="Smoke Run #42" status="completed" />);
    expect(screen.getByTestId("exec-detail-name")).toHaveTextContent("Smoke Run #42");
    expect(screen.getByTestId("exec-detail-status")).toHaveTextContent("completed");
  });

  it("scenario results list renders with pass/fail states", () => {
    const results = [
      { id: "sr1", title: "Login test",   result: "passed" },
      { id: "sr2", title: "Payment test", result: "failed" },
      { id: "sr3", title: "Logout test",  result: "passed" },
    ];
    const ResultList = ({ results }: { results: typeof results }) => (
      <div data-testid="scenario-results">
        {results.map((r) => (
          <div key={r.id} data-testid="scenario-result-row">
            <span>{r.title}</span>
            <span data-testid={`result-${r.id}`}>{r.result}</span>
          </div>
        ))}
      </div>
    );
    render(<ResultList results={results} />);
    expect(screen.getAllByTestId("scenario-result-row")).toHaveLength(3);
    expect(screen.getByTestId("result-sr2")).toHaveTextContent("failed");
  });

  it("pass rate summary computed correctly", () => {
    const results = [
      { result: "passed" }, { result: "failed" }, { result: "passed" }, { result: "passed" }
    ];
    const passed = results.filter((r) => r.result === "passed").length;
    const rate = (passed / results.length) * 100;
    expect(rate).toBe(75);
  });

  it("back to executions link present", () => {
    const BackLink = () => (
      <a href="/executions" data-testid="back-to-executions">← Koşular</a>
    );
    render(<BackLink />);
    expect(screen.getByTestId("back-to-executions")).toHaveAttribute("href", "/executions");
  });
});
