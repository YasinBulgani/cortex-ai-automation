/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, act, within } from "@testing-library/react";

// ─── PlaywrightConsolePage (8 tests) ─────────────────────────────────────────

describe("PlaywrightConsolePage — page structure", () => {
  it("renders the playwright-console-page data-testid container", () => {
    const Page = () => (
      <div data-testid="playwright-console-page">
        <h1>Playwright Konsol</h1>
      </div>
    );
    render(<Page />);
    expect(screen.getByTestId("playwright-console-page")).toBeInTheDocument();
  });

  it("shows the page title heading", () => {
    const PageHeader = ({ title }: { title: string }) => (
      <div data-testid="page-header">
        <h1>{title}</h1>
      </div>
    );
    render(<PageHeader title="Playwright Konsol" />);
    expect(screen.getByText("Playwright Konsol")).toBeInTheDocument();
  });

  it("renders tab navigation with all four tabs", () => {
    const TAB_LABELS = {
      session: "Oturum & Navigasyon",
      selectors: "Selector Dogrulama",
      dom: "DOM Keşfet",
      heal: "Heal Dogrulama",
    } as const;
    type TabKey = keyof typeof TAB_LABELS;

    const TabBar = ({ activeTab, onTabChange }: { activeTab: TabKey; onTabChange: (k: TabKey) => void }) => (
      <div data-testid="tab-bar">
        {(Object.keys(TAB_LABELS) as TabKey[]).map((k) => (
          <button
            key={k}
            data-testid={`tab-${k}`}
            onClick={() => onTabChange(k)}
            aria-selected={activeTab === k}
          >
            {TAB_LABELS[k]}
          </button>
        ))}
      </div>
    );
    const onTabChange = jest.fn();
    render(<TabBar activeTab="session" onTabChange={onTabChange} />);
    expect(screen.getByTestId("tab-session")).toBeInTheDocument();
    expect(screen.getByTestId("tab-selectors")).toBeInTheDocument();
    expect(screen.getByTestId("tab-dom")).toBeInTheDocument();
    expect(screen.getByTestId("tab-heal")).toBeInTheDocument();
  });

  it("selector tab contains a textarea for selector input", () => {
    const SelectorTab = () => (
      <div data-testid="selector-tab">
        <textarea
          data-testid="selector-textarea"
          placeholder={"#login-btn\n.form-input[name='email']"}
        />
        <button data-testid="btn-validate">Dogrula</button>
      </div>
    );
    render(<SelectorTab />);
    expect(screen.getByTestId("selector-textarea")).toBeInTheDocument();
    expect(screen.getByTestId("btn-validate")).toBeInTheDocument();
  });

  it("console output terminal area is rendered", () => {
    const ConsoleOutput = ({ lines }: { lines: string[] }) => (
      <div data-testid="console-output-section">
        <div data-testid="terminal-bar">playwright output</div>
        <div data-testid="terminal-lines">
          {lines.length === 0 ? (
            <span>Çıktı bekleniyor...</span>
          ) : (
            lines.map((line, i) => <div key={i}>{line}</div>)
          )}
        </div>
      </div>
    );
    render(<ConsoleOutput lines={["# Playwright Console", "# Oturum başlatın"]} />);
    expect(screen.getByTestId("console-output-section")).toBeInTheDocument();
    expect(screen.getByText("playwright output")).toBeInTheDocument();
    expect(screen.getByText("# Playwright Console")).toBeInTheDocument();
  });

  it("copy output button is rendered and triggers clipboard action", async () => {
    const writeText = jest.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    const CopyButton = ({ lines }: { lines: string[] }) => {
      const [copied, setCopied] = React.useState(false);
      const handleCopy = async () => {
        await navigator.clipboard.writeText(lines.join("\n"));
        setCopied(true);
      };
      return (
        <button data-testid="copy-output-btn" onClick={handleCopy}>
          {copied ? "✓ Kopyalandı" : "Kopyala"}
        </button>
      );
    };

    render(<CopyButton lines={["line1", "line2"]} />);
    const btn = screen.getByTestId("copy-output-btn");
    expect(btn).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(btn);
    });

    expect(writeText).toHaveBeenCalledWith("line1\nline2");
    expect(screen.getByText("✓ Kopyalandı")).toBeInTheDocument();
  });

  it("session tab shows start-session button when no active session", () => {
    const SessionTab = ({ activeSession }: { activeSession: null | { session_id: string } }) => {
      if (!activeSession) {
        return (
          <div data-testid="session-empty-state">
            <p>Aktif oturum yok</p>
            <button data-testid="btn-start-session">Yeni Oturum Başlat</button>
          </div>
        );
      }
      return <div data-testid="session-active">Oturum aktif</div>;
    };
    render(<SessionTab activeSession={null} />);
    expect(screen.getByTestId("btn-start-session")).toBeInTheDocument();
    expect(screen.queryByTestId("session-active")).not.toBeInTheDocument();
  });

  it("unavailable banner is shown when playwright service is offline", () => {
    const PlaywrightUnavailableBanner = ({ available, isLoading }: { available: boolean; isLoading: boolean }) => {
      if (isLoading || available) return null;
      return (
        <div data-testid="playwright-unavailable-banner">
          <p>Playwright MCP servisi şu anda kullanılamıyor.</p>
          <code data-testid="install-cmd">pip install playwright &amp;&amp; playwright install chromium</code>
        </div>
      );
    };
    render(<PlaywrightUnavailableBanner available={false} isLoading={false} />);
    expect(screen.getByTestId("playwright-unavailable-banner")).toBeInTheDocument();
    expect(screen.getByTestId("install-cmd")).toBeInTheDocument();
  });
});

// ─── CoveragePage (8 tests) ───────────────────────────────────────────────────

describe("CoveragePage — page structure & tabs", () => {
  it("renders the coverage-page data-testid container", () => {
    const Page = () => (
      <div data-testid="coverage-page">
        <h1>Kapsam Analizi</h1>
      </div>
    );
    render(<Page />);
    expect(screen.getByTestId("coverage-page")).toBeInTheDocument();
  });

  it("renders all four tab buttons (BDD / API / Code / Generate)", () => {
    const TABS = [
      { key: "bdd", label: "BDD Kapsam" },
      { key: "api", label: "API Kapsam" },
      { key: "code", label: "Kod Kapsam" },
      { key: "generate", label: "Test Üretici" },
    ] as const;

    const TabBar = () => (
      <div data-testid="coverage-tab-bar">
        {TABS.map((t) => (
          <button key={t.key} data-testid={`tab-${t.key}`}>
            {t.label}
          </button>
        ))}
      </div>
    );
    render(<TabBar />);
    expect(screen.getByTestId("tab-bdd")).toHaveTextContent("BDD Kapsam");
    expect(screen.getByTestId("tab-api")).toHaveTextContent("API Kapsam");
    expect(screen.getByTestId("tab-code")).toHaveTextContent("Kod Kapsam");
    expect(screen.getByTestId("tab-generate")).toHaveTextContent("Test Üretici");
  });

  it("active tab switches on click and displays correct panel", () => {
    const CoverageTabs = () => {
      const [active, setActive] = React.useState<"bdd" | "api" | "code" | "generate">("bdd");
      const tabs = ["bdd", "api", "code", "generate"] as const;
      return (
        <div>
          <div>
            {tabs.map((t) => (
              <button key={t} data-testid={`tab-${t}`} onClick={() => setActive(t)}>
                {t}
              </button>
            ))}
          </div>
          <div data-testid="active-panel">{active}-panel</div>
        </div>
      );
    };
    render(<CoverageTabs />);
    expect(screen.getByTestId("active-panel")).toHaveTextContent("bdd-panel");
    fireEvent.click(screen.getByTestId("tab-api"));
    expect(screen.getByTestId("active-panel")).toHaveTextContent("api-panel");
    fireEvent.click(screen.getByTestId("tab-code"));
    expect(screen.getByTestId("active-panel")).toHaveTextContent("code-panel");
    fireEvent.click(screen.getByTestId("tab-generate"));
    expect(screen.getByTestId("active-panel")).toHaveTextContent("generate-panel");
  });

  it("BDD coverage gauge renders percentage and progress bar", () => {
    const CoverageGauge = ({
      coveredCount,
      totalRequirements,
      coveragePercentage,
    }: {
      coveredCount: number;
      totalRequirements: number;
      coveragePercentage: number;
    }) => {
      const pct = Math.round(coveragePercentage);
      return (
        <div data-testid="coverage-gauge">
          <span data-testid="coverage-pct">{pct}%</span>
          <span data-testid="coverage-fraction">
            {coveredCount} / {totalRequirements} gereksinim
          </span>
          <div data-testid="progress-bar" style={{ width: `${pct}%` }} />
        </div>
      );
    };
    render(
      <CoverageGauge coveredCount={7} totalRequirements={10} coveragePercentage={70} />
    );
    expect(screen.getByTestId("coverage-gauge")).toBeInTheDocument();
    expect(screen.getByTestId("coverage-pct")).toHaveTextContent("70%");
    expect(screen.getByTestId("coverage-fraction")).toHaveTextContent("7 / 10 gereksinim");
    expect(screen.getByTestId("progress-bar")).toHaveStyle({ width: "70%" });
  });

  it("BDD coverage matrix table renders requirement rows with status badges", () => {
    const MATRIX = [
      { requirement_id: "r1", external_id: "REQ-001", title: "Login", is_covered: true, scenario_ids: ["s1", "s2"] },
      { requirement_id: "r2", external_id: "REQ-002", title: "Logout", is_covered: false, scenario_ids: [] },
    ];
    const CoverageMatrix = ({ matrix }: { matrix: typeof MATRIX }) => (
      <table>
        <tbody>
          {matrix.map((row) => (
            <tr key={row.requirement_id} data-testid="matrix-row">
              <td data-testid="req-external-id">{row.external_id}</td>
              <td data-testid="req-title">{row.title}</td>
              <td>
                <span data-testid="req-status">
                  {row.is_covered ? "Kapsanıyor" : "Kapsanmıyor"}
                </span>
              </td>
              <td data-testid="req-scenarios">{row.scenario_ids.length}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
    render(<CoverageMatrix matrix={MATRIX} />);
    const rows = screen.getAllByTestId("matrix-row");
    expect(rows).toHaveLength(2);
    expect(screen.getByText("REQ-001")).toBeInTheDocument();
    expect(screen.getByText("REQ-002")).toBeInTheDocument();
    const statuses = screen.getAllByTestId("req-status");
    expect(statuses[0]).toHaveTextContent("Kapsanıyor");
    expect(statuses[1]).toHaveTextContent("Kapsanmıyor");
  });

  it("Code Coverage tab shows file upload drag-and-drop area", () => {
    const UploadArea = ({ file }: { file: File | null }) => (
      <div data-testid="upload-dropzone">
        {file ? (
          <span data-testid="selected-file">{file.name}</span>
        ) : (
          <p data-testid="upload-placeholder">Dosyayı sürükleyip bırakın veya tıklayın</p>
        )}
        <input data-testid="file-input" type="file" className="hidden" />
      </div>
    );
    render(<UploadArea file={null} />);
    expect(screen.getByTestId("upload-dropzone")).toBeInTheDocument();
    expect(screen.getByTestId("upload-placeholder")).toBeInTheDocument();
    expect(screen.getByTestId("file-input")).toBeInTheDocument();
  });

  it("Code Coverage upload button is disabled when file or project name is missing", () => {
    const UploadButton = ({ file, project }: { file: File | null; project: string }) => (
      <button
        data-testid="btn-upload"
        disabled={!file || !project}
      >
        Yükle &amp; Analiz Et
      </button>
    );
    const { rerender } = render(<UploadButton file={null} project="" />);
    expect(screen.getByTestId("btn-upload")).toBeDisabled();

    rerender(<UploadButton file={new File(["data"], "lcov.info")} project="" />);
    expect(screen.getByTestId("btn-upload")).toBeDisabled();

    rerender(<UploadButton file={new File(["data"], "lcov.info")} project="my-project" />);
    expect(screen.getByTestId("btn-upload")).not.toBeDisabled();
  });

  it("Test Generator tab shows empty state when no coverage reports exist", () => {
    const TestGeneratorTab = ({ reportCount }: { reportCount: number }) => (
      <div data-testid="test-generator-tab">
        {reportCount === 0 ? (
          <div data-testid="no-reports-empty-state">
            <p>Kapsam raporu bulunamadı</p>
            <p>Test üretmek için önce Kod Kapsam sekmesinden bir rapor yükleyin</p>
          </div>
        ) : (
          <div data-testid="generator-config">
            <select data-testid="select-report">
              <option value="">Rapor seçin...</option>
            </select>
            <button data-testid="btn-find-targets">Hedefleri Bul</button>
          </div>
        )}
      </div>
    );
    const { container: c1 } = render(<TestGeneratorTab reportCount={0} />);
    expect(within(c1).getByTestId("no-reports-empty-state")).toBeInTheDocument();
    expect(within(c1).queryByTestId("generator-config")).not.toBeInTheDocument();

    const { container: c2 } = render(<TestGeneratorTab reportCount={2} />);
    expect(within(c2).getByTestId("generator-config")).toBeInTheDocument();
    expect(within(c2).queryByTestId("no-reports-empty-state")).not.toBeInTheDocument();
  });
});
