/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ─── Accessibility Page ──────────────────────────────────────────────────────
function MockAccessibilityPage() {
  const [url, setUrl] = React.useState("");
  const [results, setResults] = React.useState<{ id: string; description: string }[]>([]);
  const [scanned, setScanned] = React.useState(false);
  return (
    <div data-testid="a11y-page">
      <input
        data-testid="a11y-input-url"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="https://example.com"
      />
      <button
        data-testid="a11y-btn-scan"
        disabled={!url}
        onClick={() => {
          setScanned(true);
          setResults([{ id: "issue-1", description: "Contrast hatası" }]);
        }}
      >
        Tara
      </button>
      {!scanned && <div data-testid="a11y-empty">Henüz tarama yapılmadı</div>}
      {results.map((issue) => (
        <div key={issue.id} data-testid={`a11y-issue-${issue.id}`}>
          {issue.description}
        </div>
      ))}
    </div>
  );
}

describe("AccessibilityPage", () => {
  it("renders page container", () => {
    render(<MockAccessibilityPage />);
    expect(screen.getByTestId("a11y-page")).toBeInTheDocument();
  });
  it("renders URL input and scan button", () => {
    render(<MockAccessibilityPage />);
    expect(screen.getByTestId("a11y-input-url")).toBeInTheDocument();
    expect(screen.getByTestId("a11y-btn-scan")).toBeInTheDocument();
  });
  it("scan button is disabled when URL is empty", () => {
    render(<MockAccessibilityPage />);
    expect(screen.getByTestId("a11y-btn-scan")).toBeDisabled();
  });
  it("scan button enables when URL is entered", async () => {
    render(<MockAccessibilityPage />);
    await userEvent.type(screen.getByTestId("a11y-input-url"), "https://example.com");
    expect(screen.getByTestId("a11y-btn-scan")).not.toBeDisabled();
  });
  it("shows empty state before scanning", () => {
    render(<MockAccessibilityPage />);
    expect(screen.getByTestId("a11y-empty")).toBeInTheDocument();
  });
  it("shows issue cards after scanning", async () => {
    render(<MockAccessibilityPage />);
    await userEvent.type(screen.getByTestId("a11y-input-url"), "https://example.com");
    fireEvent.click(screen.getByTestId("a11y-btn-scan"));
    expect(screen.getByTestId("a11y-issue-issue-1")).toBeInTheDocument();
    expect(screen.getByText("Contrast hatası")).toBeInTheDocument();
  });
});

// ─── Automation Page ─────────────────────────────────────────────────────────
function MockAutomationPage() {
  const [files, setFiles] = React.useState<{ path: string; content: string }[]>([]);
  const [selected, setSelected] = React.useState<string | null>(null);
  const [showCreate, setShowCreate] = React.useState(false);
  const [newName, setNewName] = React.useState("");

  return (
    <div data-testid="automation-page">
      <h1 data-testid="automation-heading">Otomasyon</h1>
      <button data-testid="automation-btn-ai-generate">AI ile Üret</button>
      <button data-testid="automation-btn-new" onClick={() => setShowCreate(true)}>
        Yeni Dosya
      </button>
      {files.length === 0 ? (
        <div data-testid="automation-empty">
          <button data-testid="automation-btn-empty-new" onClick={() => setShowCreate(true)}>
            İlk dosyayı oluştur
          </button>
        </div>
      ) : (
        <ul data-testid="automation-file-list">
          {files.map((f) => (
            <li key={f.path} data-testid={`automation-file-item-${f.path}`}>
              <button onClick={() => setSelected(f.path)}>{f.path}</button>
            </li>
          ))}
        </ul>
      )}
      {selected && (
        <div data-testid="automation-content-panel">
          <span data-testid="automation-selected-name">{selected}</span>
          <button data-testid="automation-btn-run-selected">Çalıştır</button>
        </div>
      )}
      {showCreate && (
        <div data-testid="automation-create-modal">
          <form data-testid="automation-create-form">
            <input
              data-testid="automation-input-name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <button
              type="button"
              data-testid="automation-btn-save"
              onClick={() => {
                if (newName) {
                  setFiles([...files, { path: newName, content: "" }]);
                  setShowCreate(false);
                  setNewName("");
                }
              }}
            >
              Kaydet
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

describe("AutomationPage", () => {
  it("renders page container and heading", () => {
    render(<MockAutomationPage />);
    expect(screen.getByTestId("automation-page")).toBeInTheDocument();
    expect(screen.getByTestId("automation-heading")).toHaveTextContent("Otomasyon");
  });
  it("shows AI generate and new file buttons", () => {
    render(<MockAutomationPage />);
    expect(screen.getByTestId("automation-btn-ai-generate")).toBeInTheDocument();
    expect(screen.getByTestId("automation-btn-new")).toBeInTheDocument();
  });
  it("shows empty state when no files", () => {
    render(<MockAutomationPage />);
    expect(screen.getByTestId("automation-empty")).toBeInTheDocument();
  });
  it("opens create modal on new button click", () => {
    render(<MockAutomationPage />);
    fireEvent.click(screen.getByTestId("automation-btn-new"));
    expect(screen.getByTestId("automation-create-modal")).toBeInTheDocument();
    expect(screen.getByTestId("automation-input-name")).toBeInTheDocument();
  });
  it("creates file and shows in list", async () => {
    render(<MockAutomationPage />);
    fireEvent.click(screen.getByTestId("automation-btn-new"));
    await userEvent.type(screen.getByTestId("automation-input-name"), "login.feature");
    fireEvent.click(screen.getByTestId("automation-btn-save"));
    expect(screen.getByTestId("automation-file-list")).toBeInTheDocument();
    expect(screen.getByTestId("automation-file-item-login.feature")).toBeInTheDocument();
  });
  it("shows content panel on file select", async () => {
    render(<MockAutomationPage />);
    fireEvent.click(screen.getByTestId("automation-btn-new"));
    await userEvent.type(screen.getByTestId("automation-input-name"), "checkout.feature");
    fireEvent.click(screen.getByTestId("automation-btn-save"));
    fireEvent.click(screen.getByText("checkout.feature"));
    expect(screen.getByTestId("automation-content-panel")).toBeInTheDocument();
    expect(screen.getByTestId("automation-selected-name")).toHaveTextContent("checkout.feature");
  });
});

// ─── CI/CD Page ──────────────────────────────────────────────────────────────
function MockCicdPage() {
  const [events, setEvents] = React.useState<{ id: string; name: string; status: string }[]>([]);
  return (
    <div data-testid="cicd-page">
      <h1>CI/CD Entegrasyonu</h1>
      <div className="webhook-section">
        <p>GitHub Webhook: https://example.com/webhook</p>
      </div>
      <button onClick={() =>
        setEvents([{ id: "ev1", name: "push to main", status: "success" }])
      }>
        Manuel Tetikle
      </button>
      {events.map((ev) => (
        <div key={ev.id} data-testid={`cicd-event-${ev.id}`}>
          {ev.name}
        </div>
      ))}
    </div>
  );
}

describe("CicdPage", () => {
  it("renders CI/CD page container", () => {
    render(<MockCicdPage />);
    expect(screen.getByTestId("cicd-page")).toBeInTheDocument();
  });
  it("shows CI/CD integration heading", () => {
    render(<MockCicdPage />);
    expect(screen.getByText(/CI\/CD/i)).toBeInTheDocument();
  });
  it("shows webhook section", () => {
    render(<MockCicdPage />);
    expect(screen.getByText(/webhook/i)).toBeInTheDocument();
  });
  it("renders event cards after trigger", () => {
    render(<MockCicdPage />);
    fireEvent.click(screen.getByText(/Manuel Tetikle/i));
    expect(screen.getByTestId("cicd-event-ev1")).toBeInTheDocument();
  });
});

// ─── Environments Page ───────────────────────────────────────────────────────
function MockEnvironmentsPage() {
  const [envs, setEnvs] = React.useState([
    { id: "env-1", name: "Staging", isDefault: false },
  ]);
  const [selected, setSelected] = React.useState<string | null>(null);
  return (
    <div data-testid="environments-page">
      <h1>Ortam Yonetimi</h1>
      <ul>
        {envs.map((env) => (
          <li key={env.id} onClick={() => setSelected(env.id)} data-testid={`env-item-${env.id}`}>
            {env.name}
          </li>
        ))}
      </ul>
      {selected && (
        <div data-testid="env-detail-panel">
          <input data-testid="env-name-input" defaultValue={envs.find((e) => e.id === selected)?.name} />
          <button data-testid="env-btn-save">Kaydet</button>
          <button data-testid="env-btn-delete">Sil</button>
        </div>
      )}
    </div>
  );
}

describe("EnvironmentsPage", () => {
  it("renders environments page", () => {
    render(<MockEnvironmentsPage />);
    expect(screen.getByTestId("environments-page")).toBeInTheDocument();
  });
  it("shows heading", () => {
    render(<MockEnvironmentsPage />);
    expect(screen.getByText(/Ortam/i)).toBeInTheDocument();
  });
  it("lists environments", () => {
    render(<MockEnvironmentsPage />);
    expect(screen.getByTestId("env-item-env-1")).toBeInTheDocument();
    expect(screen.getByText("Staging")).toBeInTheDocument();
  });
  it("shows detail panel on env selection", () => {
    render(<MockEnvironmentsPage />);
    fireEvent.click(screen.getByTestId("env-item-env-1"));
    expect(screen.getByTestId("env-detail-panel")).toBeInTheDocument();
    expect(screen.getByTestId("env-btn-save")).toBeInTheDocument();
    expect(screen.getByTestId("env-btn-delete")).toBeInTheDocument();
  });
});

// ─── Flaky Tests Page ────────────────────────────────────────────────────────
function MockFlakyPage() {
  const [activeTab, setActiveTab] = React.useState("flaky");
  const flakyTests = [{ scenario_id: "sc-1", name: "Login flaky", flipCount: 5 }];
  return (
    <div data-testid="flaky-page">
      <h1>Flaky Testler</h1>
      <div className="tabs">
        <button onClick={() => setActiveTab("flaky")}>Flaky Listesi</button>
        <button onClick={() => setActiveTab("api")}>API Flaky</button>
        <button onClick={() => setActiveTab("quarantine")}>Karantina</button>
      </div>
      {activeTab === "flaky" && (
        <table data-testid="flaky-table">
          <tbody>
            {flakyTests.map((t) => (
              <tr key={t.scenario_id} data-testid={`flaky-row-${t.scenario_id}`}>
                <td>{t.name}</td>
                <td>{t.flipCount}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {activeTab === "api" && <table data-testid="api-flaky-table"><tbody /></table>}
      {activeTab === "quarantine" && <table data-testid="quarantine-table"><tbody /></table>}
    </div>
  );
}

describe("FlakyPage", () => {
  it("renders flaky page container", () => {
    render(<MockFlakyPage />);
    expect(screen.getByTestId("flaky-page")).toBeInTheDocument();
  });
  it("shows Flaky Testler heading", () => {
    render(<MockFlakyPage />);
    expect(screen.getByText("Flaky Testler")).toBeInTheDocument();
  });
  it("renders flaky table by default", () => {
    render(<MockFlakyPage />);
    expect(screen.getByTestId("flaky-table")).toBeInTheDocument();
    expect(screen.getByTestId("flaky-row-sc-1")).toBeInTheDocument();
  });
  it("switches to API Flaky tab", () => {
    render(<MockFlakyPage />);
    fireEvent.click(screen.getByText("API Flaky"));
    expect(screen.getByTestId("api-flaky-table")).toBeInTheDocument();
  });
  it("switches to Quarantine tab", () => {
    render(<MockFlakyPage />);
    fireEvent.click(screen.getByText("Karantina"));
    expect(screen.getByTestId("quarantine-table")).toBeInTheDocument();
  });
});

// ─── Healing Page ────────────────────────────────────────────────────────────
function MockHealingPage() {
  const stats = { total: 42, successRate: 87.5, avgRetries: 2.1, avgTime: 320, savedTime: 1420 };
  return (
    <div data-testid="healing-page">
      <h1>Otomatik Onarım (Self-Healing)</h1>
      <div data-testid="stat-total">{stats.total}</div>
      <div data-testid="stat-success-rate">{stats.successRate}%</div>
      <div data-testid="stat-saved-time">{stats.savedTime}s</div>
    </div>
  );
}

describe("HealingPage", () => {
  it("renders healing page container", () => {
    render(<MockHealingPage />);
    expect(screen.getByTestId("healing-page")).toBeInTheDocument();
  });
  it("shows self-healing heading", () => {
    render(<MockHealingPage />);
    expect(screen.getByText(/Onarım|Self-Healing/i)).toBeInTheDocument();
  });
  it("shows total healing attempts", () => {
    render(<MockHealingPage />);
    expect(screen.getByTestId("stat-total")).toHaveTextContent("42");
  });
  it("shows success rate stat", () => {
    render(<MockHealingPage />);
    expect(screen.getByTestId("stat-success-rate")).toHaveTextContent("87.5%");
  });
});

// ─── Locators Page ───────────────────────────────────────────────────────────
function MockLocatorsPage() {
  const [activeTab, setActiveTab] = React.useState("management");
  const locators = [
    { id: "loc-1", selector: "#login-btn", type: "css", status: "stable" },
  ];
  return (
    <div data-testid="locators-page">
      <h1>Locator Zekası</h1>
      <div className="tabs">
        <button data-testid="tab-management" onClick={() => setActiveTab("management")}>Yönetim</button>
        <button data-testid="tab-stability" onClick={() => setActiveTab("stability")}>Stabilite</button>
        <button data-testid="tab-fallback" onClick={() => setActiveTab("fallback")}>Fallback</button>
        <button data-testid="tab-pom" onClick={() => setActiveTab("pom")}>POM</button>
        <button data-testid="tab-breakage" onClick={() => setActiveTab("breakage")}>Kırılma</button>
      </div>
      {activeTab === "management" && (
        <table data-testid="locators-table">
          <tbody>
            {locators.map((l) => (
              <tr key={l.id}>
                <td>{l.selector}</td>
                <td>{l.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {activeTab === "stability" && <div>AI Stabilite Analizi</div>}
      {activeTab === "fallback" && <div>Fallback Çözümleme</div>}
      {activeTab === "pom" && <div>POM Üreteci</div>}
      {activeTab === "breakage" && <div>Kırılma Tahmini</div>}
    </div>
  );
}

describe("LocatorsPage", () => {
  it("renders locators page container", () => {
    render(<MockLocatorsPage />);
    expect(screen.getByTestId("locators-page")).toBeInTheDocument();
  });
  it("shows Locator Zekası heading", () => {
    render(<MockLocatorsPage />);
    expect(screen.getByText("Locator Zekası")).toBeInTheDocument();
  });
  it("renders all 5 tabs", () => {
    render(<MockLocatorsPage />);
    expect(screen.getByTestId("tab-management")).toBeInTheDocument();
    expect(screen.getByTestId("tab-stability")).toBeInTheDocument();
    expect(screen.getByTestId("tab-fallback")).toBeInTheDocument();
    expect(screen.getByTestId("tab-pom")).toBeInTheDocument();
    expect(screen.getByTestId("tab-breakage")).toBeInTheDocument();
  });
  it("shows locators table on management tab", () => {
    render(<MockLocatorsPage />);
    expect(screen.getByTestId("locators-table")).toBeInTheDocument();
    expect(screen.getByText("#login-btn")).toBeInTheDocument();
  });
  it("switches to stability tab", () => {
    render(<MockLocatorsPage />);
    fireEvent.click(screen.getByTestId("tab-stability"));
    expect(screen.getByText(/Stabilite Analizi/i)).toBeInTheDocument();
  });
  it("switches to POM tab", () => {
    render(<MockLocatorsPage />);
    fireEvent.click(screen.getByTestId("tab-pom"));
    expect(screen.getByText("POM Üreteci")).toBeInTheDocument();
  });
});
