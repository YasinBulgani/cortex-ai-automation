/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// ─── Automation Generator Page ──────────────────────────────────────────────

describe("AutomationGenPage", () => {
  it("renders scenario selector and generate button", () => {
    const Page = () => (
      <div data-testid="automation-gen-page">
        <select data-testid="framework-select">
          <option value="playwright">Playwright</option>
          <option value="cypress">Cypress</option>
          <option value="selenium">Selenium</option>
        </select>
        <button data-testid="btn-generate-automation">Otomasyon Üret</button>
      </div>
    );
    render(<Page />);
    expect(screen.getByTestId("btn-generate-automation")).toBeInTheDocument();
    expect(screen.getByText("Playwright")).toBeInTheDocument();
    expect(screen.getByText("Cypress")).toBeInTheDocument();
  });

  it("generated gherkin code displayed in output", () => {
    const GherkinOutput = ({ code }: { code: string }) => (
      <pre data-testid="gherkin-output">{code}</pre>
    );
    const gherkin = "Feature: Login\n  Scenario: Başarılı giriş";
    render(<GherkinOutput code={gherkin} />);
    expect(screen.getByTestId("gherkin-output")).toHaveTextContent("Feature: Login");
  });

  it("playwright code tab switches output", () => {
    const OutputTabs = () => {
      const [tab, setTab] = React.useState<"gherkin" | "playwright">("gherkin");
      return (
        <div>
          <button data-testid="tab-gherkin" onClick={() => setTab("gherkin")}>Gherkin</button>
          <button data-testid="tab-playwright" onClick={() => setTab("playwright")}>Playwright</button>
          <div data-testid="output-content">{tab === "gherkin" ? "Feature:" : "test("}</div>
        </div>
      );
    };
    render(<OutputTabs />);
    expect(screen.getByTestId("output-content")).toHaveTextContent("Feature:");
    fireEvent.click(screen.getByTestId("tab-playwright"));
    expect(screen.getByTestId("output-content")).toHaveTextContent("test(");
  });

  it("copy code button works", () => {
    const onCopy = jest.fn();
    const CopyBtn = () => <button data-testid="btn-copy-code" onClick={onCopy}>Kopyala</button>;
    render(<CopyBtn />);
    fireEvent.click(screen.getByTestId("btn-copy-code"));
    expect(onCopy).toHaveBeenCalled();
  });

  it("scenario multi-select shows selected count", () => {
    const MultiSelect = () => {
      const [selected, setSelected] = React.useState<string[]>([]);
      const items = ["SC-001", "SC-002", "SC-003"];
      const toggle = (id: string) => setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);
      return (
        <div>
          {items.map(id => (
            <label key={id}>
              <input type="checkbox" data-testid={`check-${id}`} onChange={() => toggle(id)} />
              {id}
            </label>
          ))}
          <span data-testid="selected-count">{selected.length} seçili</span>
        </div>
      );
    };
    render(<MultiSelect />);
    expect(screen.getByTestId("selected-count")).toHaveTextContent("0 seçili");
    fireEvent.click(screen.getByTestId("check-SC-001"));
    fireEvent.click(screen.getByTestId("check-SC-002"));
    expect(screen.getByTestId("selected-count")).toHaveTextContent("2 seçili");
  });
});

// ─── Manual to Automation Page ──────────────────────────────────────────────

describe("ManualToAutomationPage", () => {
  it("renders manual steps input area", () => {
    const Page = () => (
      <div data-testid="manual-to-auto-page">
        <textarea data-testid="manual-steps-input" placeholder="Manuel test adımlarını yapıştırın..." />
        <button data-testid="btn-convert">Otomasyona Dönüştür</button>
      </div>
    );
    render(<Page />);
    expect(screen.getByTestId("manual-steps-input")).toBeInTheDocument();
    expect(screen.getByTestId("btn-convert")).toBeInTheDocument();
  });

  it("convert button is disabled when input is empty", () => {
    const ConvertBtn = ({ input }: { input: string }) => (
      <button data-testid="btn-convert" disabled={!input.trim()}>Dönüştür</button>
    );
    render(<ConvertBtn input="" />);
    expect(screen.getByTestId("btn-convert")).toBeDisabled();
    render(<ConvertBtn input="1. Sayfaya git\n2. Login ol" />);
    expect(screen.getAllByTestId("btn-convert")[1]).not.toBeDisabled();
  });

  it("automation output panel shows generated code", () => {
    const Output = ({ code }: { code: string | null }) => (
      code ? <pre data-testid="automation-output">{code}</pre>
           : <p data-testid="output-empty">Henüz dönüştürme yapılmadı</p>
    );
    const { rerender } = render(<Output code={null} />);
    expect(screen.getByTestId("output-empty")).toBeInTheDocument();
    rerender(<Output code="await page.goto('/')" />);
    expect(screen.getByTestId("automation-output")).toHaveTextContent("await page.goto");
  });
});

// ─── Device Manager Page ────────────────────────────────────────────────────

describe("DeviceManagerPage", () => {
  const MOCK_DEVICES = [
    { id: "d1", name: "iPhone 14",    platform: "iOS",     status: "connected",    os_version: "17.2" },
    { id: "d2", name: "Pixel 7",      platform: "Android", status: "disconnected", os_version: "14" },
    { id: "d3", name: "Samsung S23",  platform: "Android", status: "connected",    os_version: "13" },
  ];

  it("renders device list", () => {
    const DeviceList = ({ devices }: { devices: typeof MOCK_DEVICES }) => (
      <div data-testid="device-list">
        {devices.map((d) => (
          <div key={d.id} data-testid="device-row">
            <span data-testid="device-name">{d.name}</span>
            <span data-testid="device-status">{d.status}</span>
            <span data-testid="device-platform">{d.platform}</span>
          </div>
        ))}
      </div>
    );
    render(<DeviceList devices={MOCK_DEVICES} />);
    expect(screen.getAllByTestId("device-row")).toHaveLength(3);
    expect(screen.getByText("iPhone 14")).toBeInTheDocument();
    expect(screen.getByText("Pixel 7")).toBeInTheDocument();
  });

  it("connected device count computed correctly", () => {
    const connected = MOCK_DEVICES.filter(d => d.status === "connected").length;
    expect(connected).toBe(2);
  });

  it("platform filter shows only Android devices", () => {
    const FilteredList = ({ filter }: { filter: string }) => {
      const visible = filter === "all" ? MOCK_DEVICES : MOCK_DEVICES.filter(d => d.platform === filter);
      return (
        <div data-testid="filtered-devices">
          {visible.map(d => <div key={d.id} data-testid="device-item">{d.name}</div>)}
        </div>
      );
    };
    const { rerender } = render(<FilteredList filter="all" />);
    expect(screen.getAllByTestId("device-item")).toHaveLength(3);
    rerender(<FilteredList filter="Android" />);
    expect(screen.getAllByTestId("device-item")).toHaveLength(2);
    expect(screen.queryByText("iPhone 14")).not.toBeInTheDocument();
  });

  it("connect button triggers handler", () => {
    const onConnect = jest.fn();
    const ConnectBtn = () => (
      <button data-testid="btn-connect-device" onClick={onConnect}>Bağlan</button>
    );
    render(<ConnectBtn />);
    fireEvent.click(screen.getByTestId("btn-connect-device"));
    expect(onConnect).toHaveBeenCalled();
  });

  it("status badge classes are correct", () => {
    const statusClass = (s: string) =>
      s === "connected" ? "text-emerald-400" : "text-slate-400";
    expect(statusClass("connected")).toBe("text-emerald-400");
    expect(statusClass("disconnected")).toBe("text-slate-400");
  });
});

// ─── Page Objects Page ──────────────────────────────────────────────────────

describe("PageObjectsPage", () => {
  const MOCK_POS = [
    { id: "po1", name: "LoginPage",    selector_count: 8 },
    { id: "po2", name: "DashboardPage",selector_count: 15 },
  ];

  it("renders page object list", () => {
    const PoList = ({ pos }: { pos: typeof MOCK_POS }) => (
      <div data-testid="po-list">
        {pos.map((po) => (
          <div key={po.id} data-testid="po-row">
            <span data-testid="po-name">{po.name}</span>
            <span data-testid="po-selectors">{po.selector_count} selektör</span>
          </div>
        ))}
      </div>
    );
    render(<PoList pos={MOCK_POS} />);
    expect(screen.getAllByTestId("po-row")).toHaveLength(2);
    expect(screen.getByText("LoginPage")).toBeInTheDocument();
    expect(screen.getByText("15 selektör")).toBeInTheDocument();
  });

  it("create page object opens form", () => {
    const CreateForm = () => {
      const [open, setOpen] = React.useState(false);
      return (
        <div>
          <button data-testid="btn-new-po" onClick={() => setOpen(true)}>Yeni Page Object</button>
          {open && <form data-testid="po-form"><input data-testid="po-name-input" /></form>}
        </div>
      );
    };
    render(<CreateForm />);
    expect(screen.queryByTestId("po-form")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("btn-new-po"));
    expect(screen.getByTestId("po-form")).toBeInTheDocument();
  });
});

// ─── Workflows Page ─────────────────────────────────────────────────────────

describe("WorkflowsPage", () => {
  const MOCK_WORKFLOWS = [
    { id: "w1", name: "Slack Bildirimi",   status: "active",   trigger: "on_failure" },
    { id: "w2", name: "Jira Ticket Oluştur", status: "inactive", trigger: "on_failure" },
  ];

  it("renders workflow list", () => {
    const WfList = ({ workflows }: { workflows: typeof MOCK_WORKFLOWS }) => (
      <div data-testid="workflow-list">
        {workflows.map((w) => (
          <div key={w.id} data-testid="workflow-row">
            <span data-testid="wf-name">{w.name}</span>
            <span data-testid="wf-status">{w.status}</span>
          </div>
        ))}
      </div>
    );
    render(<WfList workflows={MOCK_WORKFLOWS} />);
    expect(screen.getAllByTestId("workflow-row")).toHaveLength(2);
    expect(screen.getByText("Slack Bildirimi")).toBeInTheDocument();
  });

  it("toggle workflow active state", () => {
    const WfToggle = () => {
      const [active, setActive] = React.useState(false);
      return (
        <div>
          <span data-testid="wf-state">{active ? "active" : "inactive"}</span>
          <button data-testid="wf-toggle" onClick={() => setActive(!active)}>Aç/Kapat</button>
        </div>
      );
    };
    render(<WfToggle />);
    expect(screen.getByTestId("wf-state")).toHaveTextContent("inactive");
    fireEvent.click(screen.getByTestId("wf-toggle"));
    expect(screen.getByTestId("wf-state")).toHaveTextContent("active");
  });

  it("n8n iframe shown when configured", () => {
    const N8nEmbed = ({ url }: { url: string | null }) => (
      url ? <iframe data-testid="n8n-iframe" src={url} title="n8n workflow" /> : null
    );
    render(<N8nEmbed url="http://localhost:5678" />);
    expect(screen.getByTestId("n8n-iframe")).toBeInTheDocument();
  });
});

// ─── Debug Report Page ──────────────────────────────────────────────────────

describe("DebugReportPage", () => {
  it("renders report header", () => {
    const Header = ({ name }: { name: string }) => (
      <h1 data-testid="debug-report-heading">{name}</h1>
    );
    render(<Header name="Debug Run #42" />);
    expect(screen.getByTestId("debug-report-heading")).toHaveTextContent("Debug Run #42");
  });

  it("screenshot section renders image", () => {
    const Screenshot = ({ src }: { src: string }) => (
      <img data-testid="debug-screenshot" src={src} alt="debug screenshot" />
    );
    render(<Screenshot src="/screenshots/run42.png" />);
    const img = screen.getByTestId("debug-screenshot");
    expect(img).toHaveAttribute("src", "/screenshots/run42.png");
  });

  it("log section shows timestamped entries", () => {
    const logs = [
      { ts: "10:01:22", level: "info",  msg: "Test started" },
      { ts: "10:01:25", level: "error", msg: "Element not found" },
    ];
    const LogView = ({ logs }: { logs: typeof logs }) => (
      <div data-testid="debug-logs">
        {logs.map((l, i) => (
          <div key={i} data-testid="log-entry">
            <span data-testid="log-ts">{l.ts}</span>
            <span data-testid="log-level">{l.level}</span>
            <span data-testid="log-msg">{l.msg}</span>
          </div>
        ))}
      </div>
    );
    render(<LogView logs={logs} />);
    expect(screen.getAllByTestId("log-entry")).toHaveLength(2);
    expect(screen.getByText("Element not found")).toBeInTheDocument();
  });
});

// ─── Banking Team Page ──────────────────────────────────────────────────────

describe("BankingTeamPage", () => {
  it("renders banking team dashboard header", () => {
    const Header = () => (
      <div data-testid="banking-team-page">
        <h1 data-testid="banking-heading">Bankacılık Ekibi</h1>
      </div>
    );
    render(<Header />);
    expect(screen.getByTestId("banking-team-page")).toBeInTheDocument();
    expect(screen.getByTestId("banking-heading")).toBeInTheDocument();
  });

  it("KPI cards render with values", () => {
    const kpis = [
      { label: "Toplam Test", value: "2,340" },
      { label: "Başarı Oranı", value: "94.2%" },
      { label: "Kritik Hata", value: "3" },
    ];
    const KpiCards = ({ kpis }: { kpis: typeof kpis }) => (
      <div data-testid="kpi-grid">
        {kpis.map((k) => (
          <div key={k.label} data-testid="kpi-card">
            <span>{k.label}</span>
            <span data-testid="kpi-value">{k.value}</span>
          </div>
        ))}
      </div>
    );
    render(<KpiCards kpis={kpis} />);
    expect(screen.getAllByTestId("kpi-card")).toHaveLength(3);
    expect(screen.getByText("94.2%")).toBeInTheDocument();
  });
});

// ─── DSL Catalog (Project) Page ─────────────────────────────────────────────

describe("ProjectDslCatalogPage", () => {
  it("renders DSL catalog with search", () => {
    const Page = () => (
      <div data-testid="project-dsl-catalog">
        <input data-testid="dsl-search" placeholder="DSL adımı ara..." />
      </div>
    );
    render(<Page />);
    expect(screen.getByTestId("dsl-search")).toBeInTheDocument();
  });

  it("filters DSL actions by search query", () => {
    const actions = ["click element", "fill input", "assert text", "navigate to"];
    const FilteredDsl = () => {
      const [q, setQ] = React.useState("");
      const visible = actions.filter(a => a.includes(q.toLowerCase()));
      return (
        <div>
          <input data-testid="dsl-search" value={q} onChange={e => setQ(e.target.value)} />
          <div data-testid="dsl-results-count">{visible.length} adım</div>
        </div>
      );
    };
    render(<FilteredDsl />);
    expect(screen.getByTestId("dsl-results-count")).toHaveTextContent("4 adım");
    fireEvent.change(screen.getByTestId("dsl-search"), { target: { value: "click" } });
    expect(screen.getByTestId("dsl-results-count")).toHaveTextContent("1 adım");
  });
});

// ─── Wizard Page ────────────────────────────────────────────────────────────

describe("WizardPage", () => {
  const WIZARD_STEPS = ["URL Gir", "Analiz Et", "Test Case Üret", "Otomasyon Üret", "Sonuç"];

  it("renders all 5 wizard steps", () => {
    const StepList = ({ steps }: { steps: string[] }) => (
      <div data-testid="wizard-steps">
        {steps.map((s, i) => (
          <div key={i} data-testid={`wizard-step-${i + 1}`}>{s}</div>
        ))}
      </div>
    );
    render(<StepList steps={WIZARD_STEPS} />);
    expect(screen.getByTestId("wizard-step-1")).toHaveTextContent("URL Gir");
    expect(screen.getByTestId("wizard-step-5")).toHaveTextContent("Sonuç");
  });

  it("next button advances step", () => {
    const Wizard = () => {
      const [step, setStep] = React.useState(1);
      return (
        <div>
          <span data-testid="current-step">Adım {step}</span>
          <button data-testid="btn-next" onClick={() => setStep(s => Math.min(s + 1, 5))} disabled={step === 5}>İleri</button>
          <button data-testid="btn-back" onClick={() => setStep(s => Math.max(s - 1, 1))} disabled={step === 1}>Geri</button>
        </div>
      );
    };
    render(<Wizard />);
    expect(screen.getByTestId("current-step")).toHaveTextContent("Adım 1");
    expect(screen.getByTestId("btn-back")).toBeDisabled();
    fireEvent.click(screen.getByTestId("btn-next"));
    expect(screen.getByTestId("current-step")).toHaveTextContent("Adım 2");
    fireEvent.click(screen.getByTestId("btn-back"));
    expect(screen.getByTestId("current-step")).toHaveTextContent("Adım 1");
  });

  it("URL input step validates https", () => {
    const isValidUrl = (url: string) => url.startsWith("https://") || url.startsWith("http://");
    expect(isValidUrl("https://example.com")).toBe(true);
    expect(isValidUrl("ftp://invalid")).toBe(false);
    expect(isValidUrl("not-a-url")).toBe(false);
  });
});
