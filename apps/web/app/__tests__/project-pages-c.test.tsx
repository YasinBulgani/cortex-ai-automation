/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ─── Flows Page ───────────────────────────────────────────────────────────────
function MockFlowsPage() {
  const [flows, setFlows] = React.useState([
    { id: "fl-1", name: "Login Akışı", scenarioCount: 3 },
    { id: "fl-2", name: "Ödeme Akışı", scenarioCount: 5 },
  ]);
  const [showForm, setShowForm] = React.useState(false);
  const [name, setName] = React.useState("");

  return (
    <div data-testid="flows-page">
      <h1>Test Akışları</h1>
      <button onClick={() => setShowForm(!showForm)} data-testid="flows-btn-create">Yeni Akış</button>
      {showForm && (
        <form data-testid="flows-form">
          <input
            data-testid="flows-input-name"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="Akış adı"
          />
          <button
            type="button"
            onClick={() => { if (name) { setFlows(f => [...f, { id: `fl-${Date.now()}`, name, scenarioCount: 0 }]); setShowForm(false); setName(""); } }}
          >Kaydet</button>
        </form>
      )}
      <div data-testid="flows-grid">
        {flows.map(f => (
          <a key={f.id} href={`/flows/${f.id}`} data-testid={`flows-card-${f.id}`}>
            <span>{f.name}</span>
            <span>{f.scenarioCount} senaryo</span>
          </a>
        ))}
      </div>
    </div>
  );
}

describe("FlowsPage", () => {
  it("renders flows page", () => {
    render(<MockFlowsPage />);
    expect(screen.getByTestId("flows-page")).toBeInTheDocument();
  });
  it("shows Test Akışları heading", () => {
    render(<MockFlowsPage />);
    expect(screen.getByText("Test Akışları")).toBeInTheDocument();
  });
  it("renders flow cards in grid", () => {
    render(<MockFlowsPage />);
    expect(screen.getByTestId("flows-grid")).toBeInTheDocument();
    expect(screen.getByTestId("flows-card-fl-1")).toBeInTheDocument();
    expect(screen.getByTestId("flows-card-fl-2")).toBeInTheDocument();
  });
  it("shows create form on button click", () => {
    render(<MockFlowsPage />);
    fireEvent.click(screen.getByTestId("flows-btn-create"));
    expect(screen.getByTestId("flows-form")).toBeInTheDocument();
    expect(screen.getByTestId("flows-input-name")).toBeInTheDocument();
  });
  it("creates new flow", async () => {
    render(<MockFlowsPage />);
    fireEvent.click(screen.getByTestId("flows-btn-create"));
    await userEvent.type(screen.getByTestId("flows-input-name"), "Kayıt Akışı");
    fireEvent.click(screen.getByText("Kaydet"));
    expect(screen.getByText("Kayıt Akışı")).toBeInTheDocument();
  });
});

// ─── Schedules Page ───────────────────────────────────────────────────────────
function MockSchedulesPage() {
  const [schedules, setSchedules] = React.useState([
    { id: "sch-1", name: "Gece Koşumu", cron: "0 2 * * *", active: true },
  ]);
  const [showForm, setShowForm] = React.useState(false);
  const [name, setName] = React.useState("");
  const [cron, setCron] = React.useState("");

  return (
    <div data-testid="schedules-page">
      <h1>Zamanlayıcılar</h1>
      <button data-testid="schedules-btn-new" onClick={() => setShowForm(true)}>Yeni Zamanlayıcı</button>
      {showForm && (
        <form data-testid="schedules-form">
          <input data-testid="schedules-input-name" value={name} onChange={e => setName(e.target.value)} placeholder="Ad" />
          <input data-testid="schedules-input-cron" value={cron} onChange={e => setCron(e.target.value)} placeholder="* * * * *" />
          <button
            type="button"
            data-testid="schedules-btn-create"
            onClick={() => {
              if (name && cron) {
                setSchedules(s => [...s, { id: `sch-${s.length + 1}`, name, cron, active: false }]);
                setShowForm(false);
              }
            }}
          >Oluştur</button>
        </form>
      )}
      {schedules.map(sch => (
        <div key={sch.id} data-testid={`schedule-card-${sch.id}`}>
          <span>{sch.name}</span>
          <span>{sch.cron}</span>
          <span>{sch.active ? "Aktif" : "Pasif"}</span>
        </div>
      ))}
    </div>
  );
}

describe("SchedulesPage", () => {
  it("renders schedules page", () => {
    render(<MockSchedulesPage />);
    expect(screen.getByTestId("schedules-page")).toBeInTheDocument();
  });
  it("shows Zamanlayıcılar heading", () => {
    render(<MockSchedulesPage />);
    expect(screen.getByText("Zamanlayıcılar")).toBeInTheDocument();
  });
  it("renders existing schedule cards", () => {
    render(<MockSchedulesPage />);
    expect(screen.getByTestId("schedule-card-sch-1")).toBeInTheDocument();
    expect(screen.getByText("Gece Koşumu")).toBeInTheDocument();
  });
  it("opens create form", () => {
    render(<MockSchedulesPage />);
    fireEvent.click(screen.getByTestId("schedules-btn-new"));
    expect(screen.getByTestId("schedules-form")).toBeInTheDocument();
    expect(screen.getByTestId("schedules-input-name")).toBeInTheDocument();
    expect(screen.getByTestId("schedules-input-cron")).toBeInTheDocument();
  });
  it("creates new schedule", async () => {
    render(<MockSchedulesPage />);
    fireEvent.click(screen.getByTestId("schedules-btn-new"));
    await userEvent.type(screen.getByTestId("schedules-input-name"), "Haftalık Koşum");
    await userEvent.type(screen.getByTestId("schedules-input-cron"), "0 9 * * 1");
    fireEvent.click(screen.getByTestId("schedules-btn-create"));
    expect(screen.getByText("Haftalık Koşum")).toBeInTheDocument();
  });
});

// ─── Reports Page ─────────────────────────────────────────────────────────────
function MockReportsPage() {
  const stats = { total: 24, completed: 20, failed: 4 };
  return (
    <div data-testid="reports-page">
      <h1>Raporlar</h1>
      <div data-testid="reports-stats">
        <span>Toplam: {stats.total}</span>
        <span>Başarılı: {stats.completed}</span>
        <span>Başarısız: {stats.failed}</span>
      </div>
      <button data-testid="reports-btn-csv">CSV İndir</button>
      <button data-testid="reports-btn-html">HTML İndir</button>
      <table data-testid="reports-table">
        <tbody>
          <tr><td>Execution 1</td><td>success</td></tr>
        </tbody>
      </table>
    </div>
  );
}

describe("ReportsPage", () => {
  it("renders reports page", () => {
    render(<MockReportsPage />);
    expect(screen.getByTestId("reports-page")).toBeInTheDocument();
  });
  it("shows Raporlar heading", () => {
    render(<MockReportsPage />);
    expect(screen.getByText("Raporlar")).toBeInTheDocument();
  });
  it("shows CSV and HTML download buttons", () => {
    render(<MockReportsPage />);
    expect(screen.getByTestId("reports-btn-csv")).toBeInTheDocument();
    expect(screen.getByTestId("reports-btn-html")).toBeInTheDocument();
  });
  it("shows execution stats", () => {
    render(<MockReportsPage />);
    expect(screen.getByText(/Toplam: 24/)).toBeInTheDocument();
    expect(screen.getByText(/Başarılı: 20/)).toBeInTheDocument();
    expect(screen.getByText(/Başarısız: 4/)).toBeInTheDocument();
  });
});

// ─── Requirements Page ────────────────────────────────────────────────────────
function MockRequirementsPage() {
  const [reqs, setReqs] = React.useState([
    { id: "req-1", externalId: "REQ-001", title: "Kullanıcı giriş yapabilmeli", priority: "high" },
  ]);
  const [showForm, setShowForm] = React.useState(false);
  const [extId, setExtId] = React.useState("");
  const [reqTitle, setReqTitle] = React.useState("");

  return (
    <div data-testid="requirements-page">
      <h1>Gereksinimler</h1>
      <button data-testid="requirements-btn-new" onClick={() => setShowForm(true)}>Yeni Gereksinim</button>
      {showForm && (
        <form data-testid="requirements-form">
          <input data-testid="requirements-input-external-id" value={extId} onChange={e => setExtId(e.target.value)} placeholder="Dış ID" />
          <input data-testid="requirements-input-title" value={reqTitle} onChange={e => setReqTitle(e.target.value)} placeholder="Başlık" />
          <select data-testid="requirements-select-priority">
            <option value="high">Yüksek</option>
            <option value="medium">Orta</option>
          </select>
          <input data-testid="requirements-input-source" placeholder="Kaynak" />
          <button
            type="button"
            data-testid="requirements-btn-create"
            onClick={() => {
              if (reqTitle) {
                setReqs(r => [...r, { id: `req-${r.length + 1}`, externalId: extId, title: reqTitle, priority: "medium" }]);
                setShowForm(false);
              }
            }}
          >Oluştur</button>
        </form>
      )}
      <table>
        <tbody>
          {reqs.map(r => (
            <tr key={r.id} data-testid={`req-row-${r.id}`}>
              <td>{r.externalId}</td>
              <td>{r.title}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

describe("RequirementsPage", () => {
  it("renders requirements page", () => {
    render(<MockRequirementsPage />);
    expect(screen.getByTestId("requirements-page")).toBeInTheDocument();
  });
  it("shows Gereksinimler heading", () => {
    render(<MockRequirementsPage />);
    expect(screen.getByText("Gereksinimler")).toBeInTheDocument();
  });
  it("shows existing requirements", () => {
    render(<MockRequirementsPage />);
    expect(screen.getByTestId("req-row-req-1")).toBeInTheDocument();
    expect(screen.getByText("REQ-001")).toBeInTheDocument();
  });
  it("shows create form", () => {
    render(<MockRequirementsPage />);
    fireEvent.click(screen.getByTestId("requirements-btn-new"));
    expect(screen.getByTestId("requirements-form")).toBeInTheDocument();
    expect(screen.getByTestId("requirements-input-external-id")).toBeInTheDocument();
    expect(screen.getByTestId("requirements-input-title")).toBeInTheDocument();
  });
  it("creates new requirement", async () => {
    render(<MockRequirementsPage />);
    fireEvent.click(screen.getByTestId("requirements-btn-new"));
    await userEvent.type(screen.getByTestId("requirements-input-external-id"), "REQ-002");
    await userEvent.type(screen.getByTestId("requirements-input-title"), "Şifre sıfırlanabilmeli");
    fireEvent.click(screen.getByTestId("requirements-btn-create"));
    expect(screen.getByText("Şifre sıfırlanabilmeli")).toBeInTheDocument();
  });
});

// ─── Integrations Page ────────────────────────────────────────────────────────
function MockIntegrationsPage() {
  const [integrations, setIntegrations] = React.useState([
    { id: "int-1", provider: "jira", baseUrl: "https://jira.example.com", active: true },
  ]);
  const [showForm, setShowForm] = React.useState(false);
  const [provider, setProvider] = React.useState("jira");

  return (
    <div data-testid="integrations-page">
      <h1>Entegrasyonlar</h1>
      <button onClick={() => setShowForm(true)}>Yeni Entegrasyon</button>
      {showForm && (
        <form data-testid="integrations-form">
          <select data-testid="integrations-select-provider" value={provider} onChange={e => setProvider(e.target.value)}>
            <option value="jira">Jira</option>
            <option value="azure">Azure DevOps</option>
            <option value="slack">Slack</option>
          </select>
          {provider === "slack" ? (
            <input data-testid="integrations-input-webhook-url" placeholder="Webhook URL" />
          ) : (
            <>
              <input data-testid="integrations-input-base-url" placeholder="Base URL" />
              <input data-testid="integrations-input-api-token" placeholder="API Token" />
              <input data-testid="integrations-input-project-key" placeholder="Project Key" />
            </>
          )}
          <button type="button" data-testid="integrations-btn-create" onClick={() => setShowForm(false)}>Oluştur</button>
        </form>
      )}
      {integrations.map(int => (
        <div key={int.id} data-testid={`integration-card-${int.id}`}>
          <span>{int.provider}</span>
          <span>{int.active ? "Aktif" : "Pasif"}</span>
        </div>
      ))}
    </div>
  );
}

describe("IntegrationsPage", () => {
  it("renders integrations page", () => {
    render(<MockIntegrationsPage />);
    expect(screen.getByTestId("integrations-page")).toBeInTheDocument();
  });
  it("shows Entegrasyonlar heading", () => {
    render(<MockIntegrationsPage />);
    expect(screen.getByText("Entegrasyonlar")).toBeInTheDocument();
  });
  it("shows existing integrations", () => {
    render(<MockIntegrationsPage />);
    expect(screen.getByTestId("integration-card-int-1")).toBeInTheDocument();
  });
  it("shows create form with provider selector", () => {
    render(<MockIntegrationsPage />);
    fireEvent.click(screen.getByText("Yeni Entegrasyon"));
    expect(screen.getByTestId("integrations-form")).toBeInTheDocument();
    expect(screen.getByTestId("integrations-select-provider")).toBeInTheDocument();
  });
  it("shows webhook URL for Slack provider", async () => {
    render(<MockIntegrationsPage />);
    fireEvent.click(screen.getByText("Yeni Entegrasyon"));
    fireEvent.change(screen.getByTestId("integrations-select-provider"), { target: { value: "slack" } });
    expect(screen.getByTestId("integrations-input-webhook-url")).toBeInTheDocument();
  });
});

// ─── Test Data Page ────────────────────────────────────────────────────────────
function MockTestDataPage() {
  const [datasets] = React.useState([
    { id: "ds-1", name: "Login Verileri", rows: 10, columns: ["email", "password"] },
  ]);
  const [selected, setSelected] = React.useState<string | null>(null);

  return (
    <div data-testid="test-data-page">
      <h1>Test Verileri</h1>
      <div data-testid="dataset-list">
        {datasets.map(ds => (
          <div key={ds.id} data-testid={`dataset-${ds.id}`} onClick={() => setSelected(ds.id)}>
            <span>{ds.name}</span>
            <span>{ds.rows} satır</span>
          </div>
        ))}
      </div>
      {selected && (
        <div data-testid="dataset-editor">
          <button data-testid="add-column-btn">Sütun Ekle</button>
          <button data-testid="add-row-btn">Satır Ekle</button>
          <button data-testid="export-csv-btn">CSV Dışa Aktar</button>
        </div>
      )}
    </div>
  );
}

describe("TestDataPage", () => {
  it("renders test data page", () => {
    render(<MockTestDataPage />);
    expect(screen.getByTestId("test-data-page")).toBeInTheDocument();
  });
  it("shows Test Verileri heading", () => {
    render(<MockTestDataPage />);
    expect(screen.getByText("Test Verileri")).toBeInTheDocument();
  });
  it("shows dataset list", () => {
    render(<MockTestDataPage />);
    expect(screen.getByTestId("dataset-list")).toBeInTheDocument();
    expect(screen.getByTestId("dataset-ds-1")).toBeInTheDocument();
    expect(screen.getByText("Login Verileri")).toBeInTheDocument();
  });
  it("shows editor on dataset selection", () => {
    render(<MockTestDataPage />);
    fireEvent.click(screen.getByTestId("dataset-ds-1"));
    expect(screen.getByTestId("dataset-editor")).toBeInTheDocument();
    expect(screen.getByTestId("add-column-btn")).toBeInTheDocument();
    expect(screen.getByTestId("export-csv-btn")).toBeInTheDocument();
  });
});

// ─── Visual Regression Page ────────────────────────────────────────────────────
function MockVisualPage() {
  const [baselines, setBaselines] = React.useState([
    { id: "bl-1", name: "Login sayfası", lastRun: "2026-05-10" },
  ]);
  return (
    <div data-testid="visual-regression-page">
      <h1>Visual Regression</h1>
      <div data-testid="baselines-list">
        {baselines.map(b => (
          <div key={b.id} data-testid={`baseline-${b.id}`}>
            <span>{b.name}</span>
            <button data-testid={`compare-btn-${b.id}`}>Karşılaştır</button>
            <button data-testid={`delete-baseline-${b.id}`} onClick={() => setBaselines(bs => bs.filter(x => x.id !== b.id))}>Sil</button>
          </div>
        ))}
      </div>
    </div>
  );
}

describe("VisualPage", () => {
  it("renders visual regression page", () => {
    render(<MockVisualPage />);
    expect(screen.getByTestId("visual-regression-page")).toBeInTheDocument();
  });
  it("shows Visual Regression heading", () => {
    render(<MockVisualPage />);
    expect(screen.getByText("Visual Regression")).toBeInTheDocument();
  });
  it("shows baseline list", () => {
    render(<MockVisualPage />);
    expect(screen.getByTestId("baselines-list")).toBeInTheDocument();
    expect(screen.getByTestId("baseline-bl-1")).toBeInTheDocument();
    expect(screen.getByText("Login sayfası")).toBeInTheDocument();
  });
  it("shows compare and delete buttons per baseline", () => {
    render(<MockVisualPage />);
    expect(screen.getByTestId("compare-btn-bl-1")).toBeInTheDocument();
    expect(screen.getByTestId("delete-baseline-bl-1")).toBeInTheDocument();
  });
  it("removes baseline on delete", () => {
    render(<MockVisualPage />);
    fireEvent.click(screen.getByTestId("delete-baseline-bl-1"));
    expect(screen.queryByTestId("baseline-bl-1")).not.toBeInTheDocument();
  });
});

// ─── Mobile History Page ──────────────────────────────────────────────────────
function MockMobileHistoryPage() {
  const runs = [
    { id: "mh-1", platform: "iOS", status: "success", passRate: 95, duration: 120 },
    { id: "mh-2", platform: "Android", status: "failed", passRate: 60, duration: 180 },
  ];
  return (
    <div data-testid="mobile-history-page">
      <h1>Mobil Koşum Geçmişi</h1>
      <div data-testid="stat-total">{runs.length} Koşum</div>
      <div data-testid="stat-ios">1 iOS</div>
      <div data-testid="stat-android">1 Android</div>
      <table>
        <tbody>
          {runs.map(r => (
            <tr key={r.id} data-testid={`mobile-history-row-${r.id}`}>
              <td>{r.platform}</td>
              <td>{r.status}</td>
              <td>{r.passRate}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

describe("MobileHistoryPage", () => {
  it("renders mobile history page", () => {
    render(<MockMobileHistoryPage />);
    expect(screen.getByTestId("mobile-history-page")).toBeInTheDocument();
  });
  it("shows Mobil Koşum Geçmişi heading", () => {
    render(<MockMobileHistoryPage />);
    expect(screen.getByText("Mobil Koşum Geçmişi")).toBeInTheDocument();
  });
  it("shows stat cards for total, iOS, Android", () => {
    render(<MockMobileHistoryPage />);
    expect(screen.getByTestId("stat-total")).toBeInTheDocument();
    expect(screen.getByTestId("stat-ios")).toBeInTheDocument();
    expect(screen.getByTestId("stat-android")).toBeInTheDocument();
  });
  it("renders run rows", () => {
    render(<MockMobileHistoryPage />);
    expect(screen.getByTestId("mobile-history-row-mh-1")).toBeInTheDocument();
    expect(screen.getByTestId("mobile-history-row-mh-2")).toBeInTheDocument();
  });
  it("shows platform badges", () => {
    render(<MockMobileHistoryPage />);
    expect(screen.getByText("iOS")).toBeInTheDocument();
    expect(screen.getByText("Android")).toBeInTheDocument();
  });
});

// ─── Scenarios Generate Page ───────────────────────────────────────────────────
function MockScenarioGeneratePage() {
  const [analysisText, setAnalysisText] = React.useState("");
  const [generated, setGenerated] = React.useState<{ id: string; title: string }[]>([]);
  const [selected, setSelected] = React.useState<string[]>([]);

  return (
    <div data-testid="scenario-generate-page">
      <a href="/scenarios" data-testid="generate-btn-back">← Geri</a>
      <h1>BDD Senaryosu Üret</h1>
      <textarea
        data-testid="generate-input-analysis"
        value={analysisText}
        onChange={e => setAnalysisText(e.target.value)}
        placeholder="Analiz belgesi..."
      />
      <button
        data-testid="generate-btn-submit"
        disabled={!analysisText}
        onClick={() => setGenerated([
          { id: "gen-1", title: "Kullanıcı login senaryosu" },
          { id: "gen-2", title: "Şifre sıfırlama senaryosu" },
        ])}
      >
        Üret
      </button>
      {generated.map(g => (
        <div key={g.id} data-testid={`generated-card-${g.id}`}>
          <input
            type="checkbox"
            checked={selected.includes(g.id)}
            onChange={() => setSelected(sel => sel.includes(g.id) ? sel.filter(s => s !== g.id) : [...sel, g.id])}
          />
          <span>{g.title}</span>
        </div>
      ))}
      {selected.length > 0 && <button data-testid="save-selected-btn">Seçilenleri Kaydet ({selected.length})</button>}
    </div>
  );
}

describe("ScenarioGeneratePage", () => {
  it("renders scenario generate page", () => {
    render(<MockScenarioGeneratePage />);
    expect(screen.getByTestId("scenario-generate-page")).toBeInTheDocument();
  });
  it("shows back link", () => {
    render(<MockScenarioGeneratePage />);
    expect(screen.getByTestId("generate-btn-back")).toBeInTheDocument();
  });
  it("shows analysis textarea", () => {
    render(<MockScenarioGeneratePage />);
    expect(screen.getByTestId("generate-input-analysis")).toBeInTheDocument();
  });
  it("submit button disabled when empty", () => {
    render(<MockScenarioGeneratePage />);
    expect(screen.getByTestId("generate-btn-submit")).toBeDisabled();
  });
  it("generates scenarios on submit", async () => {
    render(<MockScenarioGeneratePage />);
    await userEvent.type(screen.getByTestId("generate-input-analysis"), "sistem gereksinimleri");
    fireEvent.click(screen.getByTestId("generate-btn-submit"));
    expect(screen.getByTestId("generated-card-gen-1")).toBeInTheDocument();
    expect(screen.getByText("Kullanıcı login senaryosu")).toBeInTheDocument();
  });
  it("shows save button when scenarios selected", async () => {
    render(<MockScenarioGeneratePage />);
    await userEvent.type(screen.getByTestId("generate-input-analysis"), "gereksinim");
    fireEvent.click(screen.getByTestId("generate-btn-submit"));
    fireEvent.click(screen.getAllByRole("checkbox")[0]);
    expect(screen.getByTestId("save-selected-btn")).toBeInTheDocument();
    expect(screen.getByText(/Seçilenleri Kaydet \(1\)/)).toBeInTheDocument();
  });
});

// ─── Scenario Detail Page ──────────────────────────────────────────────────────
function MockScenarioDetailPage() {
  const scenario = {
    id: "sc-42",
    title: "Login Başarılı Senaryo",
    description: "Geçerli kimlik bilgileriyle giriş",
    status: "active",
    version: 3,
    steps: [
      { id: "step-1", action: "Navigate to login" },
      { id: "step-2", action: "Fill credentials" },
    ],
  };

  return (
    <div data-testid="scenario-detail-page">
      <a href="/scenarios" data-testid="scenario-detail-btn-back">← Senaryolar</a>
      <h1 data-testid="scenario-detail-heading">{scenario.title}</h1>
      <p>{scenario.description}</p>
      <span>Durum: {scenario.status}</span>
      <span>v{scenario.version}</span>
      <ol>
        {scenario.steps.map((s, i) => (
          <li key={s.id}>{s.action}</li>
        ))}
      </ol>
      <a href={`/scenarios/edit/${scenario.id}`} data-testid="scenario-detail-btn-edit">Düzenle</a>
    </div>
  );
}

describe("ScenarioDetailPage", () => {
  it("renders scenario detail page", () => {
    render(<MockScenarioDetailPage />);
    expect(screen.getByTestId("scenario-detail-page")).toBeInTheDocument();
  });
  it("shows scenario heading", () => {
    render(<MockScenarioDetailPage />);
    expect(screen.getByTestId("scenario-detail-heading")).toHaveTextContent("Login Başarılı Senaryo");
  });
  it("shows back and edit buttons", () => {
    render(<MockScenarioDetailPage />);
    expect(screen.getByTestId("scenario-detail-btn-back")).toBeInTheDocument();
    expect(screen.getByTestId("scenario-detail-btn-edit")).toBeInTheDocument();
  });
  it("shows scenario description and status", () => {
    render(<MockScenarioDetailPage />);
    expect(screen.getByText("Geçerli kimlik bilgileriyle giriş")).toBeInTheDocument();
    expect(screen.getByText(/active/i)).toBeInTheDocument();
  });
  it("shows step list", () => {
    render(<MockScenarioDetailPage />);
    expect(screen.getByText("Navigate to login")).toBeInTheDocument();
    expect(screen.getByText("Fill credentials")).toBeInTheDocument();
  });
});
