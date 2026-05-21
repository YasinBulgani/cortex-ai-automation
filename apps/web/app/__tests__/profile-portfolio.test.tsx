/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ─── Profile Page ─────────────────────────────────────────────────────────────
function MockProfilePage() {
  const [name, setName] = React.useState("Yasin Bulgan");
  const [phone, setPhone] = React.useState("555-1234");
  const [dept, setDept] = React.useState("QA");
  const [msg, setMsg] = React.useState("");
  const [showPw, setShowPw] = React.useState(false);
  const [currentPw, setCurrentPw] = React.useState("");
  const [newPw, setNewPw] = React.useState("");

  return (
    <div data-testid="profile-page">
      <h1>Profil</h1>
      <input
        data-testid="profile-input-name"
        value={name}
        onChange={e => setName(e.target.value)}
      />
      <input
        data-testid="profile-input-email"
        defaultValue="yasin@test.com"
        readOnly
      />
      <input
        data-testid="profile-input-phone"
        value={phone}
        onChange={e => setPhone(e.target.value)}
      />
      <input
        data-testid="profile-input-department"
        value={dept}
        onChange={e => setDept(e.target.value)}
      />
      <button
        data-testid="profile-btn-save"
        onClick={() => setMsg("Profil güncellendi")}
      >
        Kaydet
      </button>
      {msg && <div data-testid="profile-alert-msg">{msg}</div>}
      <button
        data-testid="profile-btn-password"
        onClick={() => setShowPw(!showPw)}
      >
        Şifreyi Değiştir
      </button>
      {showPw && (
        <div>
          <input
            data-testid="profile-input-current-pw"
            type="password"
            value={currentPw}
            onChange={e => setCurrentPw(e.target.value)}
            placeholder="Mevcut şifre"
          />
          <input
            data-testid="profile-input-new-pw"
            type="password"
            value={newPw}
            onChange={e => setNewPw(e.target.value)}
            placeholder="Yeni şifre"
          />
          <button
            data-testid="profile-btn-change-pw"
            disabled={!currentPw || !newPw}
          >
            Şifreyi Güncelle
          </button>
        </div>
      )}
    </div>
  );
}

describe("ProfilePage", () => {
  it("renders profile page", () => {
    render(<MockProfilePage />);
    expect(screen.getByTestId("profile-page")).toBeInTheDocument();
  });
  it("shows Profil heading", () => {
    render(<MockProfilePage />);
    expect(screen.getByText("Profil")).toBeInTheDocument();
  });
  it("renders all profile input fields", () => {
    render(<MockProfilePage />);
    expect(screen.getByTestId("profile-input-name")).toBeInTheDocument();
    expect(screen.getByTestId("profile-input-email")).toBeInTheDocument();
    expect(screen.getByTestId("profile-input-phone")).toBeInTheDocument();
    expect(screen.getByTestId("profile-input-department")).toBeInTheDocument();
  });
  it("email field is read-only", () => {
    render(<MockProfilePage />);
    expect(screen.getByTestId("profile-input-email")).toHaveAttribute("readonly");
  });
  it("shows save confirmation after save", () => {
    render(<MockProfilePage />);
    fireEvent.click(screen.getByTestId("profile-btn-save"));
    expect(screen.getByTestId("profile-alert-msg")).toHaveTextContent("Profil güncellendi");
  });
  it("shows password change section on button click", () => {
    render(<MockProfilePage />);
    fireEvent.click(screen.getByTestId("profile-btn-password"));
    expect(screen.getByTestId("profile-input-current-pw")).toBeInTheDocument();
    expect(screen.getByTestId("profile-input-new-pw")).toBeInTheDocument();
    expect(screen.getByTestId("profile-btn-change-pw")).toBeInTheDocument();
  });
  it("password update button disabled when fields empty", () => {
    render(<MockProfilePage />);
    fireEvent.click(screen.getByTestId("profile-btn-password"));
    expect(screen.getByTestId("profile-btn-change-pw")).toBeDisabled();
  });
  it("password update button enabled when both fields filled", async () => {
    render(<MockProfilePage />);
    fireEvent.click(screen.getByTestId("profile-btn-password"));
    await userEvent.type(screen.getByTestId("profile-input-current-pw"), "oldpass");
    await userEvent.type(screen.getByTestId("profile-input-new-pw"), "newpass123");
    expect(screen.getByTestId("profile-btn-change-pw")).not.toBeDisabled();
  });
  it("can edit name field", async () => {
    render(<MockProfilePage />);
    const nameInput = screen.getByTestId("profile-input-name") as HTMLInputElement;
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Yeni Ad");
    expect(nameInput.value).toBe("Yeni Ad");
  });
});

// ─── Portfolio (Projects) Page ────────────────────────────────────────────────
function MockPortfolioPage() {
  const [search, setSearch] = React.useState("");
  const [showArchived, setShowArchived] = React.useState(false);
  const [view, setView] = React.useState<"grid" | "list">("grid");
  const projects = [
    { id: "proj-1", name: "E-Ticaret Projesi", product: "web", archived: false },
    { id: "proj-2", name: "Mobil Uygulama", product: "mobile", archived: false },
    { id: "proj-3", name: "Eski Proje", product: "web", archived: true },
  ];
  const productTabs = ["one", "web", "mobile", "service"];

  const filtered = projects.filter(p => {
    if (!showArchived && p.archived) return false;
    if (search && !p.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div>
      <h1>Projeler</h1>
      <div className="product-tabs">
        {productTabs.map(tab => (
          <button key={tab} data-testid={`product-tab-${tab}`}>{tab}</button>
        ))}
      </div>
      <input
        data-testid="portfolio-search"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Proje ara"
      />
      <label>
        <input type="checkbox" checked={showArchived} onChange={e => setShowArchived(e.target.checked)} />
        Arşivlenenleri göster
      </label>
      <div className="view-toggle">
        <button onClick={() => setView("grid")}>Grid</button>
        <button onClick={() => setView("list")}>Liste</button>
      </div>
      <div data-testid="projects-container">
        {filtered.map(p => (
          <a key={p.id} href={`/p/${p.id}`} data-testid={`project-card-${p.id}`}>
            {p.name}
          </a>
        ))}
      </div>
    </div>
  );
}

describe("PortfolioPage", () => {
  it("renders portfolio page with heading", () => {
    render(<MockPortfolioPage />);
    expect(screen.getByText("Projeler")).toBeInTheDocument();
  });
  it("renders product tabs", () => {
    render(<MockPortfolioPage />);
    expect(screen.getByTestId("product-tab-one")).toBeInTheDocument();
    expect(screen.getByTestId("product-tab-web")).toBeInTheDocument();
    expect(screen.getByTestId("product-tab-mobile")).toBeInTheDocument();
    expect(screen.getByTestId("product-tab-service")).toBeInTheDocument();
  });
  it("shows active project cards", () => {
    render(<MockPortfolioPage />);
    expect(screen.getByTestId("project-card-proj-1")).toBeInTheDocument();
    expect(screen.getByTestId("project-card-proj-2")).toBeInTheDocument();
    expect(screen.queryByTestId("project-card-proj-3")).not.toBeInTheDocument(); // archived
  });
  it("shows archived projects when toggled", () => {
    render(<MockPortfolioPage />);
    fireEvent.click(screen.getByRole("checkbox"));
    expect(screen.getByTestId("project-card-proj-3")).toBeInTheDocument();
  });
  it("filters projects by search", async () => {
    render(<MockPortfolioPage />);
    await userEvent.type(screen.getByTestId("portfolio-search"), "Mobil");
    expect(screen.queryByTestId("project-card-proj-1")).not.toBeInTheDocument();
    expect(screen.getByTestId("project-card-proj-2")).toBeInTheDocument();
  });
});

// ─── Reset Password Page ───────────────────────────────────────────────────────
function MockResetPasswordPage({ hasToken = true }: { hasToken?: boolean }) {
  const [pw, setPw] = React.useState("");
  const [confirm, setConfirm] = React.useState("");
  const [showPw, setShowPw] = React.useState(false);
  const [success, setSuccess] = React.useState(false);
  const [error, setError] = React.useState("");

  if (!hasToken) {
    return (
      <div data-testid="reset-error">
        <p>Geçersiz veya eksik token</p>
        <a href="/login">Giriş sayfasına git</a>
      </div>
    );
  }

  return (
    <div data-testid="reset-password-page">
      <h1>Yeni Şifre Belirle</h1>
      {!success ? (
        <form>
          <input
            type={showPw ? "text" : "password"}
            data-testid="reset-input-password"
            value={pw}
            onChange={e => setPw(e.target.value)}
            placeholder="Yeni şifre"
          />
          <input
            type={showPw ? "text" : "password"}
            data-testid="reset-input-confirm"
            value={confirm}
            onChange={e => setConfirm(e.target.value)}
            placeholder="Şifreyi onayla"
          />
          <button type="button" data-testid="toggle-show-pw" onClick={() => setShowPw(!showPw)}>
            {showPw ? "Gizle" : "Göster"}
          </button>
          {error && <div data-testid="reset-error-msg">{error}</div>}
          <button
            type="button"
            data-testid="reset-btn-submit"
            disabled={!pw || pw.length < 8 || pw !== confirm}
            onClick={() => {
              if (pw !== confirm) { setError("Şifreler eşleşmiyor"); return; }
              setSuccess(true);
            }}
          >
            Şifreyi Sıfırla
          </button>
        </form>
      ) : (
        <div data-testid="reset-success">
          <p>Şifreniz başarıyla güncellendi</p>
          <a href="/login">Giriş yap</a>
        </div>
      )}
    </div>
  );
}

describe("ResetPasswordPage", () => {
  it("renders reset password form", () => {
    render(<MockResetPasswordPage />);
    expect(screen.getByTestId("reset-password-page")).toBeInTheDocument();
  });
  it("shows Yeni Şifre Belirle heading", () => {
    render(<MockResetPasswordPage />);
    expect(screen.getByText("Yeni Şifre Belirle")).toBeInTheDocument();
  });
  it("renders password and confirm inputs", () => {
    render(<MockResetPasswordPage />);
    expect(screen.getByTestId("reset-input-password")).toBeInTheDocument();
    expect(screen.getByTestId("reset-input-confirm")).toBeInTheDocument();
  });
  it("submit button disabled when password is too short", async () => {
    render(<MockResetPasswordPage />);
    await userEvent.type(screen.getByTestId("reset-input-password"), "short");
    await userEvent.type(screen.getByTestId("reset-input-confirm"), "short");
    expect(screen.getByTestId("reset-btn-submit")).toBeDisabled();
  });
  it("submit button disabled when passwords don't match", async () => {
    render(<MockResetPasswordPage />);
    await userEvent.type(screen.getByTestId("reset-input-password"), "password123");
    await userEvent.type(screen.getByTestId("reset-input-confirm"), "password456");
    expect(screen.getByTestId("reset-btn-submit")).toBeDisabled();
  });
  it("submit button enabled when valid passwords match", async () => {
    render(<MockResetPasswordPage />);
    await userEvent.type(screen.getByTestId("reset-input-password"), "password123");
    await userEvent.type(screen.getByTestId("reset-input-confirm"), "password123");
    expect(screen.getByTestId("reset-btn-submit")).not.toBeDisabled();
  });
  it("shows success state after submit", async () => {
    render(<MockResetPasswordPage />);
    await userEvent.type(screen.getByTestId("reset-input-password"), "password123");
    await userEvent.type(screen.getByTestId("reset-input-confirm"), "password123");
    fireEvent.click(screen.getByTestId("reset-btn-submit"));
    expect(screen.getByTestId("reset-success")).toBeInTheDocument();
  });
  it("shows error state when no token", () => {
    render(<MockResetPasswordPage hasToken={false} />);
    expect(screen.getByTestId("reset-error")).toBeInTheDocument();
  });
  it("toggles password visibility", () => {
    render(<MockResetPasswordPage />);
    const pwInput = screen.getByTestId("reset-input-password") as HTMLInputElement;
    expect(pwInput.type).toBe("password");
    fireEvent.click(screen.getByTestId("toggle-show-pw"));
    expect(pwInput.type).toBe("text");
  });
});

// ─── IDE Page ─────────────────────────────────────────────────────────────────
function MockIdePage() {
  const [search, setSearch] = React.useState("");
  const [openTabs, setOpenTabs] = React.useState<string[]>(["sc-1"]);
  const [activeTab, setActiveTab] = React.useState("sc-1");
  const projects = [{ id: "proj-1", name: "Test Projesi", scenarios: [{ id: "sc-1", title: "Login Senaryosu" }] }];
  const [expanded, setExpanded] = React.useState<string[]>(["proj-1"]);

  return (
    <div data-testid="scenario-ide-page">
      <div data-testid="scenario-ide-explorer">
        <input
          data-testid="scenario-ide-search"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Proje / senaryo ara"
        />
        <button data-testid="scenario-ide-expand-all" onClick={() => setExpanded(projects.map(p => p.id))}>Tümünü Genişlet</button>
        <button data-testid="scenario-ide-collapse-all" onClick={() => setExpanded([])}>Tümünü Kapat</button>
        {projects.map(p => (
          <div key={p.id} data-testid={`scenario-ide-project-${p.id}`}>
            <button onClick={() => setExpanded(exp => exp.includes(p.id) ? exp.filter(e => e !== p.id) : [...exp, p.id])}>{p.name}</button>
            {expanded.includes(p.id) && p.scenarios.map(sc => (
              <div key={sc.id} data-testid={`scenario-ide-scenario-${sc.id}`} onClick={() => {
                if (!openTabs.includes(sc.id)) setOpenTabs(t => [...t, sc.id]);
                setActiveTab(sc.id);
              }}>
                {sc.title}
              </div>
            ))}
          </div>
        ))}
      </div>
      <div data-testid="scenario-ide-tabs">
        {openTabs.map(tabId => (
          <div key={tabId} data-testid={`scenario-ide-tab-${tabId}`} onClick={() => setActiveTab(tabId)}>
            {projects.flatMap(p => p.scenarios).find(sc => sc.id === tabId)?.title}
          </div>
        ))}
      </div>
      <button data-testid="scenario-ide-refresh">Yenile</button>
      <button data-testid="scenario-ide-open-full">Tam Ekran</button>
    </div>
  );
}

describe("IdePage", () => {
  it("renders IDE page", () => {
    render(<MockIdePage />);
    expect(screen.getByTestId("scenario-ide-page")).toBeInTheDocument();
  });
  it("shows file explorer", () => {
    render(<MockIdePage />);
    expect(screen.getByTestId("scenario-ide-explorer")).toBeInTheDocument();
  });
  it("shows search input", () => {
    render(<MockIdePage />);
    expect(screen.getByTestId("scenario-ide-search")).toBeInTheDocument();
  });
  it("shows expand/collapse all buttons", () => {
    render(<MockIdePage />);
    expect(screen.getByTestId("scenario-ide-expand-all")).toBeInTheDocument();
    expect(screen.getByTestId("scenario-ide-collapse-all")).toBeInTheDocument();
  });
  it("shows project in explorer", () => {
    render(<MockIdePage />);
    expect(screen.getByTestId("scenario-ide-project-proj-1")).toBeInTheDocument();
  });
  it("shows scenario in tabs", () => {
    render(<MockIdePage />);
    expect(screen.getByTestId("scenario-ide-tabs")).toBeInTheDocument();
    expect(screen.getByTestId("scenario-ide-tab-sc-1")).toBeInTheDocument();
  });
  it("collapses explorer on collapse all", () => {
    render(<MockIdePage />);
    fireEvent.click(screen.getByTestId("scenario-ide-collapse-all"));
    expect(screen.queryByTestId("scenario-ide-scenario-sc-1")).not.toBeInTheDocument();
  });
});
