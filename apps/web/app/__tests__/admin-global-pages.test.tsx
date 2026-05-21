/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ─── Admin Audit Log Page ─────────────────────────────────────────────────────
function MockAuditPage({ page: initialPage = 1 }: { page?: number }) {
  const [page, setPage] = React.useState(initialPage);
  const events = [
    { id: "ev-1", actor: "admin@test.com", action: "project.create", resource: "Proje A", ts: "2026-05-01T10:00:00Z" },
    { id: "ev-2", actor: "user@test.com", action: "scenario.delete", resource: "Senaryo B", ts: "2026-05-02T11:00:00Z" },
  ];
  return (
    <div data-testid="audit-page">
      <h1>Denetim Günlüğü</h1>
      <table data-testid="audit-table">
        <thead>
          <tr><th>Zaman</th><th>Aktör</th><th>Eylem</th><th>Kaynak</th></tr>
        </thead>
        <tbody>
          {events.map(e => (
            <tr key={e.id} data-testid={`audit-row-${e.id}`}>
              <td>{e.ts}</td>
              <td>{e.actor}</td>
              <td>{e.action}</td>
              <td>{e.resource}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="pagination">
        <button data-testid="audit-btn-prev" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Önceki</button>
        <span>Sayfa {page}</span>
        <button data-testid="audit-btn-next" onClick={() => setPage(p => p + 1)}>Sonraki</button>
      </div>
    </div>
  );
}

describe("AdminAuditPage", () => {
  it("renders audit page container", () => {
    render(<MockAuditPage />);
    expect(screen.getByTestId("audit-page")).toBeInTheDocument();
  });
  it("shows Denetim Günlüğü heading", () => {
    render(<MockAuditPage />);
    expect(screen.getByText("Denetim Günlüğü")).toBeInTheDocument();
  });
  it("renders audit table with rows", () => {
    render(<MockAuditPage />);
    expect(screen.getByTestId("audit-table")).toBeInTheDocument();
    expect(screen.getByTestId("audit-row-ev-1")).toBeInTheDocument();
    expect(screen.getByTestId("audit-row-ev-2")).toBeInTheDocument();
  });
  it("shows pagination buttons", () => {
    render(<MockAuditPage />);
    expect(screen.getByTestId("audit-btn-prev")).toBeInTheDocument();
    expect(screen.getByTestId("audit-btn-next")).toBeInTheDocument();
  });
  it("prev button disabled on first page", () => {
    render(<MockAuditPage page={1} />);
    expect(screen.getByTestId("audit-btn-prev")).toBeDisabled();
  });
  it("next page navigation works", () => {
    render(<MockAuditPage />);
    fireEvent.click(screen.getByTestId("audit-btn-next"));
    expect(screen.getByText("Sayfa 2")).toBeInTheDocument();
  });
  it("shows event details: actor and action", () => {
    render(<MockAuditPage />);
    expect(screen.getByText("admin@test.com")).toBeInTheDocument();
    expect(screen.getByText("project.create")).toBeInTheDocument();
  });
});

// ─── Admin Settings (AI Providers) Page ──────────────────────────────────────
function MockAdminSettingsPage() {
  const [providers] = React.useState([
    { id: "openai", name: "OpenAI GPT-4", configured: true },
    { id: "anthropic", name: "Anthropic Claude", configured: true },
    { id: "gemini", name: "Google Gemini", configured: false },
  ]);
  const [selected, setSelected] = React.useState("openai");
  const [saved, setSaved] = React.useState(false);

  return (
    <div data-testid="admin-settings-page">
      <h1>AI Ayarları</h1>
      {providers.map(p => (
        <div key={p.id} data-testid={`settings-provider-${p.id}`}>
          <input
            type="radio"
            name="provider"
            value={p.id}
            checked={selected === p.id}
            disabled={!p.configured}
            onChange={() => setSelected(p.id)}
          />
          <label>{p.name}</label>
          {!p.configured && <span>Yapılandırılmamış</span>}
        </div>
      ))}
      <button
        data-testid="settings-btn-save-provider"
        onClick={() => { setSaved(true); setTimeout(() => setSaved(false), 2000); }}
      >
        Kaydet
      </button>
      {saved && <div data-testid="settings-saved-indicator">Kaydedildi</div>}
    </div>
  );
}

describe("AdminSettingsPage", () => {
  it("renders admin settings page", () => {
    render(<MockAdminSettingsPage />);
    expect(screen.getByTestId("admin-settings-page")).toBeInTheDocument();
  });
  it("shows AI Ayarları heading", () => {
    render(<MockAdminSettingsPage />);
    expect(screen.getByText("AI Ayarları")).toBeInTheDocument();
  });
  it("renders all provider options", () => {
    render(<MockAdminSettingsPage />);
    expect(screen.getByTestId("settings-provider-openai")).toBeInTheDocument();
    expect(screen.getByTestId("settings-provider-anthropic")).toBeInTheDocument();
    expect(screen.getByTestId("settings-provider-gemini")).toBeInTheDocument();
  });
  it("shows unconfigured indicator for unconfigured providers", () => {
    render(<MockAdminSettingsPage />);
    expect(screen.getByText("Yapılandırılmamış")).toBeInTheDocument();
  });
  it("shows save button", () => {
    render(<MockAdminSettingsPage />);
    expect(screen.getByTestId("settings-btn-save-provider")).toBeInTheDocument();
  });
  it("shows saved indicator after save", async () => {
    render(<MockAdminSettingsPage />);
    fireEvent.click(screen.getByTestId("settings-btn-save-provider"));
    expect(screen.getByTestId("settings-saved-indicator")).toBeInTheDocument();
    expect(screen.getByText("Kaydedildi")).toBeInTheDocument();
  });
});

// ─── Admin Users Page ─────────────────────────────────────────────────────────
function MockAdminUsersPage() {
  const [users, setUsers] = React.useState([
    { id: "u-1", email: "admin@test.com", name: "Admin", role: "admin", active: true },
    { id: "u-2", email: "user@test.com", name: "User", role: "user", active: true },
  ]);
  const [search, setSearch] = React.useState("");
  const [showForm, setShowForm] = React.useState(false);
  const [email, setEmail] = React.useState("");
  const [error, setError] = React.useState("");

  const filtered = users.filter(u => u.email.includes(search) || u.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div data-testid="admin-users-page">
      <h1>Kullanıcı Yönetimi</h1>
      <input
        data-testid="admin-users-input-search"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Email veya ad ile ara"
      />
      <button onClick={() => setShowForm(true)}>Yeni Kullanıcı</button>
      {showForm && (
        <form data-testid="admin-users-form">
          <input data-testid="admin-users-input-email" value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" />
          <input data-testid="admin-users-input-password" type="password" placeholder="Şifre" />
          <input data-testid="admin-users-input-name" placeholder="Ad Soyad" />
          <select data-testid="admin-users-select-role">
            <option value="user">Kullanıcı</option>
            <option value="admin">Admin</option>
          </select>
          {error && <div data-testid="admin-users-alert-error">{error}</div>}
          <button
            type="button"
            data-testid="admin-users-btn-create"
            onClick={() => {
              if (!email) { setError("Email zorunlu"); return; }
              setUsers(u => [...u, { id: `u-${u.length + 1}`, email, name: "Yeni", role: "user", active: true }]);
              setShowForm(false);
              setEmail("");
            }}
          >Oluştur</button>
        </form>
      )}
      <table data-testid="admin-users-table">
        <tbody>
          {filtered.map(u => (
            <tr key={u.id} data-testid={`admin-users-row-${u.id}`}>
              <td>{u.email}</td>
              <td>{u.role}</td>
              <td>
                <button data-testid={`admin-users-btn-toggle-${u.id}`} onClick={() => setUsers(users.map(x => x.id === u.id ? { ...x, active: !x.active } : x))}>
                  {u.active ? "Pasif Yap" : "Aktif Yap"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

describe("AdminUsersPage", () => {
  it("renders admin users page", () => {
    render(<MockAdminUsersPage />);
    expect(screen.getByTestId("admin-users-page")).toBeInTheDocument();
  });
  it("shows Kullanıcı Yönetimi heading", () => {
    render(<MockAdminUsersPage />);
    expect(screen.getByText("Kullanıcı Yönetimi")).toBeInTheDocument();
  });
  it("renders search input", () => {
    render(<MockAdminUsersPage />);
    expect(screen.getByTestId("admin-users-input-search")).toBeInTheDocument();
  });
  it("renders user table with rows", () => {
    render(<MockAdminUsersPage />);
    expect(screen.getByTestId("admin-users-table")).toBeInTheDocument();
    expect(screen.getByTestId("admin-users-row-u-1")).toBeInTheDocument();
    expect(screen.getByTestId("admin-users-row-u-2")).toBeInTheDocument();
  });
  it("filters users by search", async () => {
    render(<MockAdminUsersPage />);
    await userEvent.type(screen.getByTestId("admin-users-input-search"), "admin");
    expect(screen.queryByText("user@test.com")).not.toBeInTheDocument();
    expect(screen.getByText("admin@test.com")).toBeInTheDocument();
  });
  it("shows create user form", () => {
    render(<MockAdminUsersPage />);
    fireEvent.click(screen.getByText("Yeni Kullanıcı"));
    expect(screen.getByTestId("admin-users-form")).toBeInTheDocument();
    expect(screen.getByTestId("admin-users-input-email")).toBeInTheDocument();
    expect(screen.getByTestId("admin-users-input-password")).toBeInTheDocument();
    expect(screen.getByTestId("admin-users-select-role")).toBeInTheDocument();
  });
  it("shows error when creating without email", () => {
    render(<MockAdminUsersPage />);
    fireEvent.click(screen.getByText("Yeni Kullanıcı"));
    fireEvent.click(screen.getByTestId("admin-users-btn-create"));
    expect(screen.getByTestId("admin-users-alert-error")).toBeInTheDocument();
    expect(screen.getByText("Email zorunlu")).toBeInTheDocument();
  });
  it("toggles user active state", () => {
    render(<MockAdminUsersPage />);
    fireEvent.click(screen.getByTestId("admin-users-btn-toggle-u-1"));
    expect(screen.getAllByText("Aktif Yap").length).toBeGreaterThan(0);
  });
});

// ─── AI Agents Page ──────────────────────────────────────────────────────────
const MOCK_AGENTS = [
  { id: "agent-analyst", name: "Analist Ajan", category: "Analiz", status: "active", href: "/ai-agents/agent-analyst" },
  { id: "agent-coder", name: "Kodlayıcı Ajan", category: "Kodlama", status: "beta", href: "/ai-agents/agent-coder" },
  { id: "agent-runner", name: "Koşturucu Ajan", category: "Koşum", status: "active", href: "/ai-agents/agent-runner" },
];

function MockAiAgentsPage() {
  const grouped = MOCK_AGENTS.reduce((acc, a) => {
    if (!acc[a.category]) acc[a.category] = [];
    acc[a.category].push(a);
    return acc;
  }, {} as Record<string, typeof MOCK_AGENTS>);

  return (
    <div>
      <h1>Neurex AI Ajanları</h1>
      {Object.entries(grouped).map(([cat, agents]) => (
        <section key={cat}>
          <h2>{cat}</h2>
          {agents.map(a => (
            <a key={a.id} data-testid={`agent-card-${a.id}`} href={a.href}>
              <span>{a.name}</span>
              <span data-testid={`agent-status-${a.id}`}>{a.status}</span>
            </a>
          ))}
        </section>
      ))}
    </div>
  );
}

describe("AiAgentsPage", () => {
  it("renders AI agents page", () => {
    render(<MockAiAgentsPage />);
    expect(screen.getByText("Neurex AI Ajanları")).toBeInTheDocument();
  });
  it("renders agent cards", () => {
    render(<MockAiAgentsPage />);
    expect(screen.getByTestId("agent-card-agent-analyst")).toBeInTheDocument();
    expect(screen.getByTestId("agent-card-agent-coder")).toBeInTheDocument();
    expect(screen.getByTestId("agent-card-agent-runner")).toBeInTheDocument();
  });
  it("shows agent names", () => {
    render(<MockAiAgentsPage />);
    expect(screen.getByText("Analist Ajan")).toBeInTheDocument();
    expect(screen.getByText("Kodlayıcı Ajan")).toBeInTheDocument();
  });
  it("shows agent status badges", () => {
    render(<MockAiAgentsPage />);
    expect(screen.getByTestId("agent-status-agent-analyst")).toHaveTextContent("active");
    expect(screen.getByTestId("agent-status-agent-coder")).toHaveTextContent("beta");
  });
  it("groups agents by category", () => {
    render(<MockAiAgentsPage />);
    expect(screen.getByText("Analiz")).toBeInTheDocument();
    expect(screen.getByText("Kodlama")).toBeInTheDocument();
    expect(screen.getByText("Koşum")).toBeInTheDocument();
  });
});

// ─── Info Page ────────────────────────────────────────────────────────────────
function MockInfoPage() {
  const features = [
    { name: "AI Test Üretimi", active: true },
    { name: "Visual Regression", active: true },
    { name: "Kuantum Analizi", active: false },
  ];
  return (
    <div data-testid="info-page">
      <h1>Sistem Bilgileri</h1>
      <div data-testid="version-info">
        <span>v2.1.0</span>
        <span>Production</span>
      </div>
      <div data-testid="features-list">
        {features.map(f => (
          <div key={f.name} data-testid={`feature-${f.name.replace(/\s/g, '-')}`}>
            <span>{f.name}</span>
            <span>{f.active ? "Aktif" : "Pasif"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

describe("InfoPage", () => {
  it("renders info page", () => {
    render(<MockInfoPage />);
    expect(screen.getByTestId("info-page")).toBeInTheDocument();
  });
  it("shows Sistem Bilgileri heading", () => {
    render(<MockInfoPage />);
    expect(screen.getByText("Sistem Bilgileri")).toBeInTheDocument();
  });
  it("shows version information", () => {
    render(<MockInfoPage />);
    expect(screen.getByTestId("version-info")).toBeInTheDocument();
    expect(screen.getByText("v2.1.0")).toBeInTheDocument();
  });
  it("shows features list with active/passive states", () => {
    render(<MockInfoPage />);
    expect(screen.getByTestId("features-list")).toBeInTheDocument();
    expect(screen.getAllByText("Aktif").length).toBeGreaterThan(0);
    expect(screen.getByText("Pasif")).toBeInTheDocument();
  });
});

// ─── Logout Page ─────────────────────────────────────────────────────────────
function MockLogoutPage() {
  return (
    <div data-testid="logout-page">
      <div className="card">
        <h1>Çıkış Yapıldı</h1>
        <p>Başarıyla çıkış yaptınız.</p>
        <a href="/" data-testid="logout-link-home">Ana Sayfaya Dön</a>
      </div>
    </div>
  );
}

describe("LogoutPage", () => {
  it("renders logout page", () => {
    render(<MockLogoutPage />);
    expect(screen.getByTestId("logout-page")).toBeInTheDocument();
  });
  it("shows logout confirmation message", () => {
    render(<MockLogoutPage />);
    expect(screen.getByText("Çıkış Yapıldı")).toBeInTheDocument();
    expect(screen.getByText("Başarıyla çıkış yaptınız.")).toBeInTheDocument();
  });
  it("shows home link", () => {
    render(<MockLogoutPage />);
    expect(screen.getByTestId("logout-link-home")).toBeInTheDocument();
    expect(screen.getByTestId("logout-link-home")).toHaveAttribute("href", "/");
  });
});

// ─── Onboarding Page ─────────────────────────────────────────────────────────
function MockOnboardingPage() {
  const [projectName, setProjectName] = React.useState("");
  const [error, setError] = React.useState("");

  return (
    <div data-testid="onboarding-page">
      <h1>Neurex Operations</h1>
      <input
        data-testid="onboarding-input-name"
        value={projectName}
        onChange={e => setProjectName(e.target.value)}
        placeholder="Proje adı"
      />
      {error && <div data-testid="onboarding-error">{error}</div>}
      <button
        data-testid="onboarding-btn-create"
        disabled={!projectName}
        onClick={() => {
          if (!projectName) { setError("Ad zorunlu"); return; }
        }}
      >
        Projeyi Oluştur
      </button>
      <button data-testid="onboarding-btn-skip">Projelerime Git</button>
    </div>
  );
}

describe("OnboardingPage", () => {
  it("renders onboarding page", () => {
    render(<MockOnboardingPage />);
    expect(screen.getByTestId("onboarding-page")).toBeInTheDocument();
  });
  it("shows Neurex Operations heading", () => {
    render(<MockOnboardingPage />);
    expect(screen.getByText("Neurex Operations")).toBeInTheDocument();
  });
  it("shows project name input", () => {
    render(<MockOnboardingPage />);
    expect(screen.getByTestId("onboarding-input-name")).toBeInTheDocument();
  });
  it("create button is disabled when name is empty", () => {
    render(<MockOnboardingPage />);
    expect(screen.getByTestId("onboarding-btn-create")).toBeDisabled();
  });
  it("create button enables after name entry", async () => {
    render(<MockOnboardingPage />);
    await userEvent.type(screen.getByTestId("onboarding-input-name"), "Yeni Proje");
    expect(screen.getByTestId("onboarding-btn-create")).not.toBeDisabled();
  });
  it("shows skip button", () => {
    render(<MockOnboardingPage />);
    expect(screen.getByTestId("onboarding-btn-skip")).toBeInTheDocument();
  });
});

// ─── Veri Kaynağı Page ────────────────────────────────────────────────────────
function MockVeriKaynagiPage() {
  const [step, setStep] = React.useState(1);
  const [ddlText, setDdlText] = React.useState("");
  const [schema, setSchema] = React.useState<{ table: string; columns: string[] } | null>(null);

  return (
    <div data-testid="veri-kaynagi-page">
      <h1>Veri Kaynağı</h1>
      <div data-testid="step-indicator">Adım {step}/5</div>
      {step === 1 && (
        <div data-testid="step-1-content">
          <button onClick={() => setStep(2)}>DDL / CSV ile devam et</button>
        </div>
      )}
      {step === 2 && (
        <div data-testid="step-2-content">
          <textarea
            data-testid="ddl-input"
            value={ddlText}
            onChange={e => setDdlText(e.target.value)}
            placeholder="CREATE TABLE ..."
          />
          <button
            data-testid="btn-parse"
            disabled={!ddlText}
            onClick={() => setSchema({ table: "users", columns: ["id", "email", "name"] })}
          >
            Şemayı Ayrıştır
          </button>
        </div>
      )}
      {schema && (
        <div data-testid="schema-preview">
          <span>{schema.table}</span>
          {schema.columns.map(c => <span key={c}>{c}</span>)}
        </div>
      )}
    </div>
  );
}

describe("VeriKaynagiPage", () => {
  it("renders veri kaynağı page", () => {
    render(<MockVeriKaynagiPage />);
    expect(screen.getByTestId("veri-kaynagi-page")).toBeInTheDocument();
  });
  it("shows Veri Kaynağı heading", () => {
    render(<MockVeriKaynagiPage />);
    expect(screen.getByText("Veri Kaynağı")).toBeInTheDocument();
  });
  it("shows step indicator", () => {
    render(<MockVeriKaynagiPage />);
    expect(screen.getByTestId("step-indicator")).toHaveTextContent("Adım 1/5");
  });
  it("shows first step content", () => {
    render(<MockVeriKaynagiPage />);
    expect(screen.getByTestId("step-1-content")).toBeInTheDocument();
  });
  it("navigates to step 2", () => {
    render(<MockVeriKaynagiPage />);
    fireEvent.click(screen.getByText("DDL / CSV ile devam et"));
    expect(screen.getByTestId("step-2-content")).toBeInTheDocument();
    expect(screen.getByTestId("btn-parse")).toBeInTheDocument();
  });
  it("parse button disabled when no DDL", () => {
    render(<MockVeriKaynagiPage />);
    fireEvent.click(screen.getByText("DDL / CSV ile devam et"));
    expect(screen.getByTestId("btn-parse")).toBeDisabled();
  });
  it("shows schema preview after parsing", async () => {
    render(<MockVeriKaynagiPage />);
    fireEvent.click(screen.getByText("DDL / CSV ile devam et"));
    await userEvent.type(screen.getByTestId("ddl-input"), "CREATE TABLE users (id INT)");
    fireEvent.click(screen.getByTestId("btn-parse"));
    expect(screen.getByTestId("schema-preview")).toBeInTheDocument();
    expect(screen.getByText("users")).toBeInTheDocument();
    expect(screen.getByText("email")).toBeInTheDocument();
  });
});
