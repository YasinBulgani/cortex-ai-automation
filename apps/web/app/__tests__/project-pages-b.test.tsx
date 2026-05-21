/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ─── Manual Tests Page ───────────────────────────────────────────────────────
function MockManualPage() {
  const [tests, setTests] = React.useState<{ id: string; title: string; priority: string; review_status: string }[]>([]);
  const [showForm, setShowForm] = React.useState(false);
  const [title, setTitle] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  return (
    <div data-testid="manual-tests-page">
      <h1>Manuel Testler</h1>
      <a href="/manual-to-automation" data-testid="manual-tests-btn-to-automation">Otomasyona Dönüştür</a>
      <button data-testid="manual-tests-btn-new" onClick={() => setShowForm(true)}>Yeni Test</button>
      {loading && <div data-testid="manual-tests-loading">Yükleniyor...</div>}
      {showForm && (
        <form data-testid="manual-tests-create-form">
          <input data-testid="manual-tests-input-title" value={title} onChange={e => setTitle(e.target.value)} placeholder="Başlık" />
          <select data-testid="manual-tests-select-priority">
            <option value="high">Yüksek</option>
            <option value="medium">Orta</option>
            <option value="low">Düşük</option>
          </select>
          <button
            type="button"
            data-testid="manual-tests-btn-create"
            onClick={() => {
              if (title) {
                setTests(t => [...t, { id: `t-${Date.now()}`, title, priority: "high", review_status: "pending" }]);
                setShowForm(false);
                setTitle("");
              }
            }}
          >Kaydet</button>
        </form>
      )}
      {tests.length === 0 && !showForm && (
        <div>
          <button data-testid="manual-tests-btn-empty-new" onClick={() => setShowForm(true)}>İlk testi oluştur</button>
        </div>
      )}
      {tests.length > 0 && (
        <div data-testid="manual-tests-list">
          {tests.map(t => (
            <div key={t.id} data-testid={`manual-test-card-${t.id}`}>
              <span>{t.title}</span>
              <button data-testid={`manual-test-delete-${t.id}`} onClick={() => setTests(ts => ts.filter(x => x.id !== t.id))}>Sil</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

describe("ManualPage", () => {
  it("renders manual tests page", () => {
    render(<MockManualPage />);
    expect(screen.getByTestId("manual-tests-page")).toBeInTheDocument();
  });
  it("shows heading and action buttons", () => {
    render(<MockManualPage />);
    expect(screen.getByText("Manuel Testler")).toBeInTheDocument();
    expect(screen.getByTestId("manual-tests-btn-new")).toBeInTheDocument();
    expect(screen.getByTestId("manual-tests-btn-to-automation")).toBeInTheDocument();
  });
  it("shows create form on new button click", () => {
    render(<MockManualPage />);
    fireEvent.click(screen.getByTestId("manual-tests-btn-new"));
    expect(screen.getByTestId("manual-tests-create-form")).toBeInTheDocument();
    expect(screen.getByTestId("manual-tests-input-title")).toBeInTheDocument();
    expect(screen.getByTestId("manual-tests-select-priority")).toBeInTheDocument();
  });
  it("creates test and shows in list", async () => {
    render(<MockManualPage />);
    fireEvent.click(screen.getByTestId("manual-tests-btn-new"));
    await userEvent.type(screen.getByTestId("manual-tests-input-title"), "Login testi");
    fireEvent.click(screen.getByTestId("manual-tests-btn-create"));
    expect(screen.getByTestId("manual-tests-list")).toBeInTheDocument();
    expect(screen.getByText("Login testi")).toBeInTheDocument();
  });
  it("deletes test from list", async () => {
    render(<MockManualPage />);
    fireEvent.click(screen.getByTestId("manual-tests-btn-new"));
    await userEvent.type(screen.getByTestId("manual-tests-input-title"), "Silinecek Test");
    fireEvent.click(screen.getByTestId("manual-tests-btn-create"));
    const deleteBtn = screen.getAllByText("Sil")[0];
    fireEvent.click(deleteBtn);
    expect(screen.queryByText("Silinecek Test")).not.toBeInTheDocument();
  });
});

// ─── Playwright Console Page ──────────────────────────────────────────────────
function MockPlaywrightConsolePage() {
  const [output, setOutput] = React.useState(">>> console ready");
  return (
    <div data-testid="playwright-console-page">
      <h1>Playwright Konsol</h1>
      <pre className="output">{output}</pre>
      <button data-testid="copy-output-btn" onClick={() => {}}>Kopyala</button>
    </div>
  );
}

describe("PlaywrightConsolePage", () => {
  it("renders playwright console page", () => {
    render(<MockPlaywrightConsolePage />);
    expect(screen.getByTestId("playwright-console-page")).toBeInTheDocument();
  });
  it("shows heading", () => {
    render(<MockPlaywrightConsolePage />);
    expect(screen.getByText("Playwright Konsol")).toBeInTheDocument();
  });
  it("renders copy output button", () => {
    render(<MockPlaywrightConsolePage />);
    expect(screen.getByTestId("copy-output-btn")).toBeInTheDocument();
  });
  it("shows console output", () => {
    render(<MockPlaywrightConsolePage />);
    expect(screen.getByText(/console ready/i)).toBeInTheDocument();
  });
});

// ─── Prioritize Page ─────────────────────────────────────────────────────────
function MockPrioritizePage() {
  const tests = [
    { id: "pt-1", name: "Login testi", score: 95, riskLevel: "high", duration: 120 },
    { id: "pt-2", name: "Sepet testi", score: 72, riskLevel: "medium", duration: 90 },
  ];
  return (
    <div data-testid="prioritize-page">
      <h1>Test Önceliklendirme</h1>
      <table data-testid="priority-table">
        <thead>
          <tr><th>Test</th><th>Skor</th><th>Risk</th><th>Süre</th></tr>
        </thead>
        <tbody>
          {tests.map(t => (
            <tr key={t.id}>
              <td>{t.name}</td>
              <td>{t.score}</td>
              <td>{t.riskLevel}</td>
              <td>{t.duration}s</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

describe("PrioritizePage", () => {
  it("renders prioritize page", () => {
    render(<MockPrioritizePage />);
    expect(screen.getByTestId("prioritize-page")).toBeInTheDocument();
  });
  it("shows Test Önceliklendirme heading", () => {
    render(<MockPrioritizePage />);
    expect(screen.getByText("Test Önceliklendirme")).toBeInTheDocument();
  });
  it("renders priority table with tests", () => {
    render(<MockPrioritizePage />);
    expect(screen.getByTestId("priority-table")).toBeInTheDocument();
    expect(screen.getByText("Login testi")).toBeInTheDocument();
    expect(screen.getByText("Sepet testi")).toBeInTheDocument();
  });
  it("shows risk level and score columns", () => {
    render(<MockPrioritizePage />);
    expect(screen.getByText("95")).toBeInTheDocument();
    expect(screen.getByText("high")).toBeInTheDocument();
  });
});

// ─── Recorder Page ────────────────────────────────────────────────────────────
function MockRecorderPage() {
  const [url, setUrl] = React.useState("");
  const [sessions, setSessions] = React.useState<{ id: string; name: string }[]>([]);
  return (
    <div data-testid="recorder-page">
      <h1>Test Kaydedici</h1>
      <input
        data-testid="recorder-url-input"
        value={url}
        onChange={e => setUrl(e.target.value)}
        placeholder="https://..."
      />
      <button
        data-testid="recorder-btn-start"
        disabled={!url}
        onClick={() => setSessions(s => [...s, { id: `sess-${s.length + 1}`, name: `Oturum ${s.length + 1}` }])}
      >
        Kaydı Başlat
      </button>
      {sessions.map(s => (
        <div key={s.id} data-testid={`recorder-session-${s.id}`}>
          {s.name}
          <button data-testid={`recorder-btn-stop-${s.id}`}>Durdur</button>
        </div>
      ))}
    </div>
  );
}

describe("RecorderPage", () => {
  it("renders recorder page", () => {
    render(<MockRecorderPage />);
    expect(screen.getByTestId("recorder-page")).toBeInTheDocument();
  });
  it("shows URL input and start button", () => {
    render(<MockRecorderPage />);
    expect(screen.getByTestId("recorder-url-input")).toBeInTheDocument();
    expect(screen.getByTestId("recorder-btn-start")).toBeInTheDocument();
  });
  it("start button is disabled when URL empty", () => {
    render(<MockRecorderPage />);
    expect(screen.getByTestId("recorder-btn-start")).toBeDisabled();
  });
  it("start button enables after URL entry", async () => {
    render(<MockRecorderPage />);
    await userEvent.type(screen.getByTestId("recorder-url-input"), "https://example.com");
    expect(screen.getByTestId("recorder-btn-start")).not.toBeDisabled();
  });
  it("creates session card on start", async () => {
    render(<MockRecorderPage />);
    await userEvent.type(screen.getByTestId("recorder-url-input"), "https://example.com");
    fireEvent.click(screen.getByTestId("recorder-btn-start"));
    expect(screen.getByTestId("recorder-session-sess-1")).toBeInTheDocument();
    expect(screen.getByTestId("recorder-btn-stop-sess-1")).toBeInTheDocument();
  });
});

// ─── Runs Page ───────────────────────────────────────────────────────────────
function MockRunsPage() {
  const runs = [
    { id: "run-1", status: "success", duration: 45, createdAt: "2026-05-01T10:00:00Z" },
    { id: "run-2", status: "failed", duration: 23, createdAt: "2026-05-02T11:00:00Z" },
  ];
  return (
    <div data-testid="runs-page">
      <h1>Test Koşuları (Engine)</h1>
      <table>
        <tbody>
          {runs.map(r => (
            <tr key={r.id} data-testid={`run-row-${r.id}`}>
              <td data-testid={`run-status-${r.id}`}>{r.status}</td>
              <td>{r.duration}s</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

describe("RunsPage", () => {
  it("renders runs page", () => {
    render(<MockRunsPage />);
    expect(screen.getByTestId("runs-page")).toBeInTheDocument();
  });
  it("shows page heading", () => {
    render(<MockRunsPage />);
    expect(screen.getByText(/Test Koşuları/i)).toBeInTheDocument();
  });
  it("lists run rows", () => {
    render(<MockRunsPage />);
    expect(screen.getByTestId("run-row-run-1")).toBeInTheDocument();
    expect(screen.getByTestId("run-row-run-2")).toBeInTheDocument();
  });
  it("shows run statuses", () => {
    render(<MockRunsPage />);
    expect(screen.getByTestId("run-status-run-1")).toHaveTextContent("success");
    expect(screen.getByTestId("run-status-run-2")).toHaveTextContent("failed");
  });
});

// ─── Security Page ───────────────────────────────────────────────────────────
function MockSecurityPage() {
  const [activeTab, setActiveTab] = React.useState("dashboard");
  const findings = [
    { id: "f1", title: "SQL Injection", severity: "critical", owasp: "API1" },
    { id: "f2", title: "Auth bypass", severity: "high", owasp: "API2" },
  ];
  return (
    <div data-testid="security-page">
      <h1>Güvenlik Tarama</h1>
      <button onClick={() => setActiveTab("dashboard")}>Dashboard</button>
      <button onClick={() => setActiveTab("results")}>Tarama Sonuçları</button>
      {activeTab === "dashboard" && (
        <div data-testid="security-dashboard">
          <div>Toplam Bulgu: {findings.length}</div>
        </div>
      )}
      {activeTab === "results" && (
        <div data-testid="security-results">
          {findings.map(f => (
            <div key={f.id} data-testid={`finding-${f.id}`}>
              <span>{f.title}</span>
              <span>{f.severity}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

describe("SecurityPage", () => {
  it("renders security page", () => {
    render(<MockSecurityPage />);
    expect(screen.getByTestId("security-page")).toBeInTheDocument();
  });
  it("shows Güvenlik Tarama heading", () => {
    render(<MockSecurityPage />);
    expect(screen.getByText("Güvenlik Tarama")).toBeInTheDocument();
  });
  it("shows dashboard by default", () => {
    render(<MockSecurityPage />);
    expect(screen.getByTestId("security-dashboard")).toBeInTheDocument();
  });
  it("switches to scan results tab", () => {
    render(<MockSecurityPage />);
    fireEvent.click(screen.getByText("Tarama Sonuçları"));
    expect(screen.getByTestId("security-results")).toBeInTheDocument();
    expect(screen.getByTestId("finding-f1")).toBeInTheDocument();
  });
});

// ─── Synthetic Page ──────────────────────────────────────────────────────────
function MockSyntheticPage() {
  const [datasets] = React.useState([
    { id: "ds-1", name: "Kullanıcı Verileri", description: "Sahte kullanıcılar" },
  ]);
  const [selected, setSelected] = React.useState<string | null>(null);
  const [count, setCount] = React.useState(100);
  return (
    <div data-testid="synthetic-page">
      <h1>Sentetik Veri</h1>
      {datasets.map(ds => (
        <div key={ds.id} data-testid={`dataset-card-${ds.id}`} onClick={() => setSelected(ds.id)}>
          {ds.name}
        </div>
      ))}
      {selected && (
        <div data-testid="dataset-config">
          <input
            type="range"
            min={1}
            max={1000}
            value={count}
            onChange={e => setCount(Number(e.target.value))}
            data-testid="count-slider"
          />
          <button data-testid="generate-btn">Üret</button>
        </div>
      )}
    </div>
  );
}

describe("SyntheticPage", () => {
  it("renders synthetic page", () => {
    render(<MockSyntheticPage />);
    expect(screen.getByTestId("synthetic-page")).toBeInTheDocument();
  });
  it("shows Sentetik Veri heading", () => {
    render(<MockSyntheticPage />);
    expect(screen.getByText("Sentetik Veri")).toBeInTheDocument();
  });
  it("shows dataset cards", () => {
    render(<MockSyntheticPage />);
    expect(screen.getByTestId("dataset-card-ds-1")).toBeInTheDocument();
    expect(screen.getByText("Kullanıcı Verileri")).toBeInTheDocument();
  });
  it("shows config panel on dataset selection", () => {
    render(<MockSyntheticPage />);
    fireEvent.click(screen.getByTestId("dataset-card-ds-1"));
    expect(screen.getByTestId("dataset-config")).toBeInTheDocument();
    expect(screen.getByTestId("generate-btn")).toBeInTheDocument();
  });
});

// ─── Privacy Page ────────────────────────────────────────────────────────────
function MockPrivacyPage() {
  const [activeTab, setActiveTab] = React.useState("audit");
  return (
    <div data-testid="privacy-page">
      <h1>Gizlilik ve Uyumluluk</h1>
      <button onClick={() => setActiveTab("audit")}>Denetim</button>
      <button onClick={() => setActiveTab("anonymize")}>Anonimleştirme</button>
      <button onClick={() => setActiveTab("compliance")}>Uyumluluk</button>
      {activeTab === "audit" && <div data-testid="audit-tab">PII Tarama</div>}
      {activeTab === "anonymize" && <div data-testid="anonymize-tab">k-Anonimite</div>}
      {activeTab === "compliance" && <div data-testid="compliance-tab">KVKK / GDPR</div>}
    </div>
  );
}

describe("PrivacyPage", () => {
  it("renders privacy page", () => {
    render(<MockPrivacyPage />);
    expect(screen.getByTestId("privacy-page")).toBeInTheDocument();
  });
  it("shows Gizlilik heading", () => {
    render(<MockPrivacyPage />);
    expect(screen.getByText("Gizlilik ve Uyumluluk")).toBeInTheDocument();
  });
  it("shows audit tab by default", () => {
    render(<MockPrivacyPage />);
    expect(screen.getByTestId("audit-tab")).toBeInTheDocument();
  });
  it("switches to anonymize tab", () => {
    render(<MockPrivacyPage />);
    fireEvent.click(screen.getByText("Anonimleştirme"));
    expect(screen.getByTestId("anonymize-tab")).toBeInTheDocument();
  });
  it("switches to compliance tab", () => {
    render(<MockPrivacyPage />);
    fireEvent.click(screen.getByText("Uyumluluk"));
    expect(screen.getByTestId("compliance-tab")).toHaveTextContent("KVKK / GDPR");
  });
});

// ─── API Testing Page ─────────────────────────────────────────────────────────
function MockApiTestingPage() {
  const [activeTab, setActiveTab] = React.useState("endpoints");
  const [importUrl, setImportUrl] = React.useState("");
  const endpoints = [
    { id: "ep-1", method: "GET", path: "/api/users", status: 200 },
    { id: "ep-2", method: "POST", path: "/api/login", status: 201 },
  ];
  return (
    <div data-testid="api-testing-page">
      <h1>API Testing Intelligence</h1>
      <div className="tabs">
        <button onClick={() => setActiveTab("endpoints")}>Endpointler</button>
        <button onClick={() => setActiveTab("test-cases")}>Test Durumları</button>
        <button onClick={() => setActiveTab("builder")}>İstek Oluşturucu</button>
      </div>
      {activeTab === "endpoints" && (
        <div>
          <input
            data-testid="spec-import-url"
            value={importUrl}
            onChange={e => setImportUrl(e.target.value)}
            placeholder="Swagger URL"
          />
          <button data-testid="spec-import-btn">İçe Aktar</button>
          <button data-testid="ai-generate-btn">AI Üret</button>
          <table data-testid="endpoint-table">
            <tbody>
              {endpoints.map(ep => (
                <tr key={ep.id}>
                  <td>{ep.method}</td>
                  <td>{ep.path}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {activeTab === "builder" && (
        <div>
          <select data-testid="request-method"><option>GET</option><option>POST</option></select>
          <input data-testid="request-url" placeholder="URL" />
          <button data-testid="request-send">Gönder</button>
        </div>
      )}
    </div>
  );
}

describe("ApiTestingPage", () => {
  it("renders api testing page", () => {
    render(<MockApiTestingPage />);
    expect(screen.getByTestId("api-testing-page")).toBeInTheDocument();
  });
  it("shows API Testing heading", () => {
    render(<MockApiTestingPage />);
    expect(screen.getByText("API Testing Intelligence")).toBeInTheDocument();
  });
  it("shows spec import URL and import button", () => {
    render(<MockApiTestingPage />);
    expect(screen.getByTestId("spec-import-url")).toBeInTheDocument();
    expect(screen.getByTestId("spec-import-btn")).toBeInTheDocument();
  });
  it("shows AI generate button", () => {
    render(<MockApiTestingPage />);
    expect(screen.getByTestId("ai-generate-btn")).toBeInTheDocument();
  });
  it("renders endpoint table", () => {
    render(<MockApiTestingPage />);
    expect(screen.getByTestId("endpoint-table")).toBeInTheDocument();
    expect(screen.getByText("GET")).toBeInTheDocument();
    expect(screen.getByText("/api/users")).toBeInTheDocument();
  });
  it("shows request builder on tab switch", () => {
    render(<MockApiTestingPage />);
    fireEvent.click(screen.getByText("İstek Oluşturucu"));
    expect(screen.getByTestId("request-method")).toBeInTheDocument();
    expect(screen.getByTestId("request-url")).toBeInTheDocument();
    expect(screen.getByTestId("request-send")).toBeInTheDocument();
  });
});

// ─── Chain Builder Page ───────────────────────────────────────────────────────
function MockChainBuilderPage() {
  const [chainName, setChainName] = React.useState("");
  return (
    <div data-testid="chain-builder-page">
      <h1>Zincir Oluşturucu</h1>
      <input
        data-testid="chain-name-input"
        value={chainName}
        onChange={e => setChainName(e.target.value)}
        placeholder="Zincir adı"
      />
      <button data-testid="add-request-node-btn">İstek Node Ekle</button>
      <button data-testid="save-chain-btn" disabled={!chainName}>Zinciri Kaydet</button>
      <button data-testid="run-chain-btn" disabled={!chainName}>Zinciri Çalıştır</button>
      <div data-testid="flow-canvas" className="reactflow-wrapper" />
    </div>
  );
}

describe("ChainBuilderPage", () => {
  it("renders chain builder page", () => {
    render(<MockChainBuilderPage />);
    expect(screen.getByTestId("chain-builder-page")).toBeInTheDocument();
  });
  it("shows heading", () => {
    render(<MockChainBuilderPage />);
    expect(screen.getByText("Zincir Oluşturucu")).toBeInTheDocument();
  });
  it("shows chain name input", () => {
    render(<MockChainBuilderPage />);
    expect(screen.getByTestId("chain-name-input")).toBeInTheDocument();
  });
  it("save and run buttons disabled when no chain name", () => {
    render(<MockChainBuilderPage />);
    expect(screen.getByTestId("save-chain-btn")).toBeDisabled();
    expect(screen.getByTestId("run-chain-btn")).toBeDisabled();
  });
  it("buttons enable after name input", async () => {
    render(<MockChainBuilderPage />);
    await userEvent.type(screen.getByTestId("chain-name-input"), "Auth Zinciri");
    expect(screen.getByTestId("save-chain-btn")).not.toBeDisabled();
    expect(screen.getByTestId("run-chain-btn")).not.toBeDisabled();
  });
});

// ─── Analysis Page ────────────────────────────────────────────────────────────
function MockAnalysisPage() {
  const [activeTab, setActiveTab] = React.useState("analyze");
  const [text, setText] = React.useState("");
  return (
    <div data-testid="analysis-page">
      <h1>Analiz Merkezi</h1>
      <div className="tabs">
        <button onClick={() => setActiveTab("analyze")}>Analiz</button>
        <button onClick={() => setActiveTab("manual")}>Manuel Testler</button>
        <button onClick={() => setActiveTab("bdd")}>BDD Senaryolar</button>
      </div>
      {activeTab === "analyze" && (
        <div>
          <div data-testid="file-drop-zone">Dosya sürükle</div>
          <textarea
            data-testid="analysis-textarea"
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="Analiz metni..."
          />
          <button data-testid="analyze-btn" disabled={!text}>Analiz Et</button>
        </div>
      )}
      {activeTab === "manual" && <div data-testid="manual-results">Manuel Test Sonuçları</div>}
      {activeTab === "bdd" && <div data-testid="bdd-results">BDD Senaryoları</div>}
    </div>
  );
}

describe("AnalysisPage", () => {
  it("renders analysis page", () => {
    render(<MockAnalysisPage />);
    expect(screen.getByTestId("analysis-page")).toBeInTheDocument();
  });
  it("shows Analiz Merkezi heading", () => {
    render(<MockAnalysisPage />);
    expect(screen.getByText("Analiz Merkezi")).toBeInTheDocument();
  });
  it("shows file drop zone and textarea on analyze tab", () => {
    render(<MockAnalysisPage />);
    expect(screen.getByTestId("file-drop-zone")).toBeInTheDocument();
    expect(screen.getByTestId("analysis-textarea")).toBeInTheDocument();
  });
  it("analyze button disabled when no text", () => {
    render(<MockAnalysisPage />);
    expect(screen.getByTestId("analyze-btn")).toBeDisabled();
  });
  it("analyze button enabled with text", async () => {
    render(<MockAnalysisPage />);
    await userEvent.type(screen.getByTestId("analysis-textarea"), "sistem analizi");
    expect(screen.getByTestId("analyze-btn")).not.toBeDisabled();
  });
  it("switches to BDD tab", () => {
    render(<MockAnalysisPage />);
    fireEvent.click(screen.getByText("BDD Senaryolar"));
    expect(screen.getByTestId("bdd-results")).toBeInTheDocument();
  });
});

// ─── Mobile Page ─────────────────────────────────────────────────────────────
function MockMobilePage() {
  const [activeTab, setActiveTab] = React.useState("virtual");
  return (
    <div data-testid="mobile-page">
      <h1>Neurex Farm (Mobil Test Orkestrasyonu)</h1>
      <button onClick={() => setActiveTab("virtual")}>Sanal Cihaz</button>
      <button onClick={() => setActiveTab("live")}>Canlı Cihaz</button>
      <button data-testid="run-btn">Çalıştır</button>
      {activeTab === "virtual" && <div data-testid="virtual-panel">Playwright Virtual</div>}
      {activeTab === "live" && <div data-testid="live-panel">Appium / ADB</div>}
    </div>
  );
}

describe("MobilePage", () => {
  it("renders mobile page", () => {
    render(<MockMobilePage />);
    expect(screen.getByTestId("mobile-page")).toBeInTheDocument();
  });
  it("shows mobile heading", () => {
    render(<MockMobilePage />);
    expect(screen.getByText(/Neurex Farm/i)).toBeInTheDocument();
  });
  it("shows run button", () => {
    render(<MockMobilePage />);
    expect(screen.getByTestId("run-btn")).toBeInTheDocument();
  });
  it("shows virtual device panel by default", () => {
    render(<MockMobilePage />);
    expect(screen.getByTestId("virtual-panel")).toBeInTheDocument();
  });
  it("switches to live device tab", () => {
    render(<MockMobilePage />);
    fireEvent.click(screen.getByText("Canlı Cihaz"));
    expect(screen.getByTestId("live-panel")).toBeInTheDocument();
  });
});
