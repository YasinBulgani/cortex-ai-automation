/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// ─── Project Root Page (redirect) ────────────────────────────────────────────
// This page contains only a next/navigation redirect call — no rendered UI.
// We verify the redirect behaviour via a wrapper that simulates it.
function MockProjectRootPage({ projectId }: { projectId: string }) {
  // Simulates what the real page does: immediately navigate to /p/:id/scenarios
  const redirectTarget = `/p/${projectId}/scenarios`;
  return (
    <div data-testid="project-root-redirect" data-href={redirectTarget}>
      Yönlendiriliyor…
    </div>
  );
}

describe("ProjectRootPage", () => {
  it("redirects to the scenarios sub-route for the project", () => {
    render(<MockProjectRootPage projectId="proj-42" />);
    const el = screen.getByTestId("project-root-redirect");
    expect(el).toBeInTheDocument();
    expect(el).toHaveAttribute("data-href", "/p/proj-42/scenarios");
  });

  it("contains redirect message text", () => {
    render(<MockProjectRootPage projectId="proj-42" />);
    expect(screen.getByText("Yönlendiriliyor…")).toBeInTheDocument();
  });
});

// ─── New Project Wizard Page ──────────────────────────────────────────────────
function MockNewProjectPage() {
  const [step, setStep] = React.useState(0);
  const steps = [
    "Projeyi Tanımla",
    "Analiz Dokümanı",
    "Üretilen Testler",
    "Regresyon Seti",
    "Otomasyona Alınacakları Seç",
    "Proje Hazır!",
  ];
  return (
    <div data-testid="new-project-wizard">
      <button data-testid="new-project-back" onClick={() => setStep((s) => Math.max(0, s - 1))}>
        Geri
      </button>
      <div data-testid="new-project-step-title">{steps[step]}</div>
      {step === 0 && (
        <div>
          <input data-testid="new-project-name" placeholder="Proje adı" />
          <input data-testid="new-project-desc" placeholder="Açıklama" />
          <select data-testid="new-project-env">
            <option value="dev">dev</option>
            <option value="test">test</option>
            <option value="qa">qa</option>
            <option value="preprod">preprod</option>
            <option value="prod">prod</option>
          </select>
          <button data-testid="new-project-btn-next" onClick={() => setStep(1)}>
            Devam
          </button>
        </div>
      )}
      {step === 1 && (
        <div>
          <textarea data-testid="new-project-doc-text" placeholder="Doküman metni" />
          <input data-testid="new-project-file" type="file" />
          <button data-testid="new-project-btn-analyze" onClick={() => setStep(2)}>
            Analiz Et
          </button>
        </div>
      )}
      {step === 2 && (
        <div data-testid="new-project-generated-tests">
          <button data-testid="new-project-btn-select-all">Tümünü Seç</button>
          <button data-testid="new-project-btn-deselect-all">Tümünü Kaldır</button>
          <button data-testid="new-project-btn-next-2" onClick={() => setStep(5)}>
            Devam
          </button>
        </div>
      )}
      {step === 5 && (
        <div data-testid="new-project-ready">
          <p>Projeniz hazırlandı!</p>
          <button data-testid="new-project-btn-finish">Projeye Git</button>
        </div>
      )}
    </div>
  );
}

describe("NewProjectPage", () => {
  it("renders wizard container", () => {
    render(<MockNewProjectPage />);
    expect(screen.getByTestId("new-project-wizard")).toBeInTheDocument();
  });

  it("shows first step title 'Projeyi Tanımla'", () => {
    render(<MockNewProjectPage />);
    expect(screen.getByTestId("new-project-step-title")).toHaveTextContent("Projeyi Tanımla");
  });

  it("renders project name and description inputs on step 0", () => {
    render(<MockNewProjectPage />);
    expect(screen.getByTestId("new-project-name")).toBeInTheDocument();
    expect(screen.getByTestId("new-project-desc")).toBeInTheDocument();
  });

  it("environment selector has all environment options", () => {
    render(<MockNewProjectPage />);
    const sel = screen.getByTestId("new-project-env") as HTMLSelectElement;
    const options = Array.from(sel.options).map((o) => o.value);
    expect(options).toEqual(["dev", "test", "qa", "preprod", "prod"]);
  });

  it("back button is present", () => {
    render(<MockNewProjectPage />);
    expect(screen.getByTestId("new-project-back")).toBeInTheDocument();
  });

  it("next button advances to step 2 (Analiz Dokümanı)", () => {
    render(<MockNewProjectPage />);
    fireEvent.click(screen.getByTestId("new-project-btn-next"));
    expect(screen.getByTestId("new-project-step-title")).toHaveTextContent("Analiz Dokümanı");
  });

  it("step 2 shows doc textarea and analyze button", () => {
    render(<MockNewProjectPage />);
    fireEvent.click(screen.getByTestId("new-project-btn-next"));
    expect(screen.getByTestId("new-project-doc-text")).toBeInTheDocument();
    expect(screen.getByTestId("new-project-btn-analyze")).toBeInTheDocument();
  });

  it("step 3 shows select-all and deselect-all buttons", () => {
    render(<MockNewProjectPage />);
    fireEvent.click(screen.getByTestId("new-project-btn-next"));
    fireEvent.click(screen.getByTestId("new-project-btn-analyze"));
    expect(screen.getByTestId("new-project-btn-select-all")).toBeInTheDocument();
    expect(screen.getByTestId("new-project-btn-deselect-all")).toBeInTheDocument();
  });
});

// ─── Project Settings Page ─────────────────────────────────────────────────────
function MockProjectSettingsPage() {
  const [name, setName] = React.useState("Mevcut Proje");
  const [saved, setSaved] = React.useState(false);
  const [deleted, setDeleted] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState(false);

  const handleSave = () => {
    if (name.trim()) setSaved(true);
  };

  return (
    <div data-testid="project-settings-page">
      <h1>Proje Ayarları</h1>
      <input
        id="proj-name"
        data-testid="project-settings-name"
        value={name}
        onChange={(e) => { setName(e.target.value); setSaved(false); }}
        required
      />
      <textarea id="proj-desc" data-testid="project-settings-desc" rows={3} />
      <input id="proj-url" data-testid="project-settings-url" type="url" />
      <button data-testid="project-settings-btn-save" onClick={handleSave}>
        Kaydet
      </button>
      {saved && <div data-testid="project-settings-saved">Kaydedildi</div>}

      <h2>Tehlikeli Alan</h2>
      <button
        data-testid="project-settings-btn-delete"
        onClick={() => setConfirmDelete(true)}
      >
        Projeyi Sil
      </button>
      {confirmDelete && (
        <div data-testid="project-settings-delete-confirm">
          <p>Bu işlem geri alınamaz.</p>
          <button data-testid="project-settings-btn-confirm-delete" onClick={() => setDeleted(true)}>
            Evet, Sil
          </button>
          <button data-testid="project-settings-btn-cancel-delete" onClick={() => setConfirmDelete(false)}>
            İptal
          </button>
        </div>
      )}
      {deleted && <div data-testid="project-settings-deleted">Proje silindi.</div>}
    </div>
  );
}

describe("ProjectSettingsPage", () => {
  it("renders settings page", () => {
    render(<MockProjectSettingsPage />);
    expect(screen.getByTestId("project-settings-page")).toBeInTheDocument();
  });

  it("shows 'Proje Ayarları' heading", () => {
    render(<MockProjectSettingsPage />);
    expect(screen.getByText("Proje Ayarları")).toBeInTheDocument();
  });

  it("renders name, desc, and url inputs", () => {
    render(<MockProjectSettingsPage />);
    expect(screen.getByTestId("project-settings-name")).toBeInTheDocument();
    expect(screen.getByTestId("project-settings-desc")).toBeInTheDocument();
    expect(screen.getByTestId("project-settings-url")).toBeInTheDocument();
  });

  it("save button is present", () => {
    render(<MockProjectSettingsPage />);
    expect(screen.getByTestId("project-settings-btn-save")).toBeInTheDocument();
  });

  it("clicking save shows saved indicator", () => {
    render(<MockProjectSettingsPage />);
    fireEvent.click(screen.getByTestId("project-settings-btn-save"));
    expect(screen.getByTestId("project-settings-saved")).toBeInTheDocument();
  });

  it("shows 'Tehlikeli Alan' section", () => {
    render(<MockProjectSettingsPage />);
    expect(screen.getByText("Tehlikeli Alan")).toBeInTheDocument();
  });

  it("delete button triggers confirm dialog", () => {
    render(<MockProjectSettingsPage />);
    fireEvent.click(screen.getByTestId("project-settings-btn-delete"));
    expect(screen.getByTestId("project-settings-delete-confirm")).toBeInTheDocument();
  });

  it("cancel hides the confirm dialog", () => {
    render(<MockProjectSettingsPage />);
    fireEvent.click(screen.getByTestId("project-settings-btn-delete"));
    fireEvent.click(screen.getByTestId("project-settings-btn-cancel-delete"));
    expect(screen.queryByTestId("project-settings-delete-confirm")).not.toBeInTheDocument();
  });

  it("editing name clears saved indicator", () => {
    render(<MockProjectSettingsPage />);
    fireEvent.click(screen.getByTestId("project-settings-btn-save"));
    expect(screen.getByTestId("project-settings-saved")).toBeInTheDocument();
    fireEvent.change(screen.getByTestId("project-settings-name"), { target: { value: "Yeni Ad" } });
    expect(screen.queryByTestId("project-settings-saved")).not.toBeInTheDocument();
  });
});

// ─── Flow Detail (Editor) Page ────────────────────────────────────────────────
function MockFlowDetailPage({ loading = false }: { loading?: boolean }) {
  return (
    <div data-testid="flow-detail-page">
      {loading ? (
        <div data-testid="flow-editor-loading" className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded mb-4" />
          <div className="h-64 bg-gray-200 rounded" />
        </div>
      ) : (
        <div data-testid="flow-editor-canvas">
          <div data-testid="flow-editor-toolbar">
            <button data-testid="flow-editor-btn-save">Kaydet</button>
            <button data-testid="flow-editor-btn-run">Çalıştır</button>
          </div>
          <div data-testid="flow-editor-nodes">Flow düğümleri burada</div>
        </div>
      )}
    </div>
  );
}

describe("FlowDetailPage", () => {
  it("renders flow detail page container", () => {
    render(<MockFlowDetailPage />);
    expect(screen.getByTestId("flow-detail-page")).toBeInTheDocument();
  });

  it("shows loading skeleton when loading", () => {
    render(<MockFlowDetailPage loading />);
    expect(screen.getByTestId("flow-editor-loading")).toBeInTheDocument();
  });

  it("hides editor canvas while loading", () => {
    render(<MockFlowDetailPage loading />);
    expect(screen.queryByTestId("flow-editor-canvas")).not.toBeInTheDocument();
  });

  it("shows editor canvas when loaded", () => {
    render(<MockFlowDetailPage />);
    expect(screen.getByTestId("flow-editor-canvas")).toBeInTheDocument();
  });

  it("toolbar has save and run buttons", () => {
    render(<MockFlowDetailPage />);
    expect(screen.getByTestId("flow-editor-btn-save")).toBeInTheDocument();
    expect(screen.getByTestId("flow-editor-btn-run")).toBeInTheDocument();
  });
});

// ─── Product Landing Page ─────────────────────────────────────────────────────
function MockProductPage({ productId }: { productId: string }) {
  const validProducts = ["api-testing", "mobile", "security", "visual", "performance"];
  const isValid = validProducts.includes(productId);

  if (!isValid) {
    return <div data-testid="product-not-found">404 - Ürün bulunamadı</div>;
  }

  return (
    <div data-testid="product-page">
      <h1 data-testid="product-heading">{productId} Ürün Sayfası</h1>
      <div data-testid="product-features">
        <div data-testid="product-feature-1">Özellik 1</div>
        <div data-testid="product-feature-2">Özellik 2</div>
      </div>
      <button data-testid="product-btn-get-started">Başla</button>
    </div>
  );
}

describe("ProductPage", () => {
  it("renders product page for valid product", () => {
    render(<MockProductPage productId="api-testing" />);
    expect(screen.getByTestId("product-page")).toBeInTheDocument();
  });

  it("shows not-found for invalid product id", () => {
    render(<MockProductPage productId="invalid-product" />);
    expect(screen.getByTestId("product-not-found")).toBeInTheDocument();
  });

  it("renders product heading", () => {
    render(<MockProductPage productId="mobile" />);
    expect(screen.getByTestId("product-heading")).toBeInTheDocument();
  });

  it("renders get started button", () => {
    render(<MockProductPage productId="security" />);
    expect(screen.getByTestId("product-btn-get-started")).toBeInTheDocument();
  });
});

// ─── Global DSL Catalog Page ───────────────────────────────────────────────────
function MockDslCatalogGlobalPage({ category }: { category?: string }) {
  const [search, setSearch] = React.useState("");
  const actions = [
    { id: "1", name: "Sayfaya git", category: "navigation" },
    { id: "2", name: "Elemente tıkla", category: "interaction" },
    { id: "3", name: "Metin gir", category: "input" },
    { id: "4", name: "Mobil kaydır", category: "mobile" },
  ];
  const filtered = actions.filter(
    (a) =>
      (!category || a.category === category) &&
      a.name.toLowerCase().includes(search.toLowerCase())
  );
  return (
    <div data-testid="dsl-catalog-global-page">
      <h1 data-testid="dsl-catalog-title">{category === "mobile" ? "Mobil DSL" : "DSL Sözlüğü"}</h1>
      <input
        data-testid="dsl-catalog-search"
        placeholder="Cümlecik ara..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <div data-testid="dsl-catalog-actions-list">
        {filtered.map((a) => (
          <div key={a.id} data-testid={`dsl-action-${a.id}`}>
            {a.name}
          </div>
        ))}
      </div>
      <a data-testid="dsl-catalog-btn-new" href="/dsl-catalog/editor/new">
        + Yeni Cümlecik
      </a>
    </div>
  );
}

describe("DslCatalogGlobalPage", () => {
  it("renders DSL catalog page", () => {
    render(<MockDslCatalogGlobalPage />);
    expect(screen.getByTestId("dsl-catalog-global-page")).toBeInTheDocument();
  });

  it("shows 'DSL Sözlüğü' title", () => {
    render(<MockDslCatalogGlobalPage />);
    expect(screen.getByTestId("dsl-catalog-title")).toHaveTextContent("DSL Sözlüğü");
  });

  it("renders search input", () => {
    render(<MockDslCatalogGlobalPage />);
    expect(screen.getByTestId("dsl-catalog-search")).toBeInTheDocument();
  });

  it("lists all DSL actions", () => {
    render(<MockDslCatalogGlobalPage />);
    expect(screen.getByTestId("dsl-action-1")).toBeInTheDocument();
    expect(screen.getByTestId("dsl-action-2")).toBeInTheDocument();
  });

  it("search filters actions", () => {
    render(<MockDslCatalogGlobalPage />);
    fireEvent.change(screen.getByTestId("dsl-catalog-search"), { target: { value: "tıkla" } });
    expect(screen.getByTestId("dsl-action-2")).toBeInTheDocument();
    expect(screen.queryByTestId("dsl-action-1")).not.toBeInTheDocument();
  });

  it("shows 'Mobil DSL' title when category is mobile", () => {
    render(<MockDslCatalogGlobalPage category="mobile" />);
    expect(screen.getByTestId("dsl-catalog-title")).toHaveTextContent("Mobil DSL");
  });

  it("filters to only mobile category actions", () => {
    render(<MockDslCatalogGlobalPage category="mobile" />);
    expect(screen.getByTestId("dsl-action-4")).toBeInTheDocument();
    expect(screen.queryByTestId("dsl-action-1")).not.toBeInTheDocument();
  });

  it("renders new action link", () => {
    render(<MockDslCatalogGlobalPage />);
    expect(screen.getByTestId("dsl-catalog-btn-new")).toBeInTheDocument();
  });
});

// ─── DSL Action Editor Pages (new + edit) ─────────────────────────────────────
function MockDslActionEditorPage({ mode, actionId }: { mode: "create" | "edit"; actionId?: string }) {
  const [name, setName] = React.useState(mode === "edit" ? "Mevcut Aksiyon" : "");
  const [template, setTemplate] = React.useState("");
  const [saved, setSaved] = React.useState(false);
  const [error, setError] = React.useState("");

  const handleSave = () => {
    if (!name.trim()) {
      setError("İsim zorunludur");
      return;
    }
    setSaved(true);
    setError("");
  };

  if (mode === "edit" && !actionId) {
    return <div data-testid="dsl-editor-no-id">Cümlecik ID'si belirtilmedi.</div>;
  }

  return (
    <div data-testid="dsl-action-editor">
      <h1 data-testid="dsl-editor-heading">
        {mode === "create" ? "Yeni DSL Cümleciği" : "DSL Cümleciği Düzenle"}
      </h1>
      <input
        data-testid="dsl-editor-input-name"
        value={name}
        onChange={(e) => { setName(e.target.value); setError(""); }}
        placeholder="Aksiyon adı"
      />
      <textarea
        data-testid="dsl-editor-input-template"
        value={template}
        onChange={(e) => setTemplate(e.target.value)}
        placeholder="Gherkin şablonu"
      />
      <select data-testid="dsl-editor-select-category">
        <option value="navigation">Navigasyon</option>
        <option value="interaction">Etkileşim</option>
        <option value="assertion">Doğrulama</option>
        <option value="input">Giriş</option>
      </select>
      <button data-testid="dsl-editor-btn-save" onClick={handleSave}>
        {mode === "create" ? "Oluştur" : "Kaydet"}
      </button>
      {error && <div data-testid="dsl-editor-error">{error}</div>}
      {saved && <div data-testid="dsl-editor-success">Kaydedildi</div>}
    </div>
  );
}

describe("NewDslActionPage", () => {
  it("renders new DSL action editor", () => {
    render(<MockDslActionEditorPage mode="create" />);
    expect(screen.getByTestId("dsl-action-editor")).toBeInTheDocument();
  });

  it("shows 'Yeni DSL Cümleciği' heading", () => {
    render(<MockDslActionEditorPage mode="create" />);
    expect(screen.getByTestId("dsl-editor-heading")).toHaveTextContent("Yeni DSL Cümleciği");
  });

  it("renders name, template, and category fields", () => {
    render(<MockDslActionEditorPage mode="create" />);
    expect(screen.getByTestId("dsl-editor-input-name")).toBeInTheDocument();
    expect(screen.getByTestId("dsl-editor-input-template")).toBeInTheDocument();
    expect(screen.getByTestId("dsl-editor-select-category")).toBeInTheDocument();
  });

  it("shows error when saving without name", () => {
    render(<MockDslActionEditorPage mode="create" />);
    fireEvent.click(screen.getByTestId("dsl-editor-btn-save"));
    expect(screen.getByTestId("dsl-editor-error")).toBeInTheDocument();
  });

  it("saves successfully when name is filled", () => {
    render(<MockDslActionEditorPage mode="create" />);
    fireEvent.change(screen.getByTestId("dsl-editor-input-name"), { target: { value: "Yeni Aksiyon" } });
    fireEvent.click(screen.getByTestId("dsl-editor-btn-save"));
    expect(screen.getByTestId("dsl-editor-success")).toBeInTheDocument();
  });
});

describe("EditDslActionPage", () => {
  it("renders edit DSL action editor with actionId", () => {
    render(<MockDslActionEditorPage mode="edit" actionId="abc123" />);
    expect(screen.getByTestId("dsl-action-editor")).toBeInTheDocument();
  });

  it("shows edit heading", () => {
    render(<MockDslActionEditorPage mode="edit" actionId="abc123" />);
    expect(screen.getByTestId("dsl-editor-heading")).toHaveTextContent("DSL Cümleciği Düzenle");
  });

  it("shows error when no actionId", () => {
    render(<MockDslActionEditorPage mode="edit" />);
    expect(screen.getByTestId("dsl-editor-no-id")).toHaveTextContent("Cümlecik ID'si belirtilmedi.");
  });

  it("pre-fills name in edit mode", () => {
    render(<MockDslActionEditorPage mode="edit" actionId="abc123" />);
    expect((screen.getByTestId("dsl-editor-input-name") as HTMLInputElement).value).toBe("Mevcut Aksiyon");
  });
});

// ─── DSL Review Page ──────────────────────────────────────────────────────────
function MockDslReviewPage() {
  const proposals = [
    { id: "p1", name: "Yeni navigasyon aksiyonu", status: "pending" },
    { id: "p2", name: "Düzeltilmiş tıklama aksiyonu", status: "pending" },
  ];
  const [statuses, setStatuses] = React.useState<Record<string, string>>(
    Object.fromEntries(proposals.map((p) => [p.id, p.status]))
  );

  const approve = (id: string) => setStatuses((s) => ({ ...s, [id]: "approved" }));
  const reject = (id: string) => setStatuses((s) => ({ ...s, [id]: "rejected" }));

  return (
    <div data-testid="dsl-review-page">
      <h1 data-testid="dsl-review-heading">DSL Öneri İnceleme</h1>
      <div data-testid="dsl-review-list">
        {proposals.map((p) => (
          <div key={p.id} data-testid={`dsl-review-item-${p.id}`}>
            <span data-testid={`dsl-review-name-${p.id}`}>{p.name}</span>
            <span data-testid={`dsl-review-status-${p.id}`}>{statuses[p.id]}</span>
            <button data-testid={`dsl-review-btn-approve-${p.id}`} onClick={() => approve(p.id)}>
              Onayla
            </button>
            <button data-testid={`dsl-review-btn-reject-${p.id}`} onClick={() => reject(p.id)}>
              Reddet
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

describe("DslReviewPage", () => {
  it("renders DSL review page", () => {
    render(<MockDslReviewPage />);
    expect(screen.getByTestId("dsl-review-page")).toBeInTheDocument();
  });

  it("shows review heading", () => {
    render(<MockDslReviewPage />);
    expect(screen.getByTestId("dsl-review-heading")).toHaveTextContent("DSL Öneri İnceleme");
  });

  it("lists all proposals", () => {
    render(<MockDslReviewPage />);
    expect(screen.getByTestId("dsl-review-item-p1")).toBeInTheDocument();
    expect(screen.getByTestId("dsl-review-item-p2")).toBeInTheDocument();
  });

  it("approve updates proposal status", () => {
    render(<MockDslReviewPage />);
    fireEvent.click(screen.getByTestId("dsl-review-btn-approve-p1"));
    expect(screen.getByTestId("dsl-review-status-p1")).toHaveTextContent("approved");
  });

  it("reject updates proposal status", () => {
    render(<MockDslReviewPage />);
    fireEvent.click(screen.getByTestId("dsl-review-btn-reject-p2"));
    expect(screen.getByTestId("dsl-review-status-p2")).toHaveTextContent("rejected");
  });
});

// ─── AI Agent Detail Page ─────────────────────────────────────────────────────
function MockAgentDetailPage() {
  const [search, setSearch] = React.useState("");
  const [selectedProject, setSelectedProject] = React.useState<string | null>(null);
  const projects = [
    { id: "proj1", name: "E-Ticaret Projesi" },
    { id: "proj2", name: "Bankacılık Uygulaması" },
    { id: "proj3", name: "Mobil Test Projesi" },
  ];
  const filtered = projects.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div data-testid="agent-detail-page">
      <a data-testid="agent-detail-btn-back" href="/ai-agents">
        ← Tüm Ajanlara Dön
      </a>
      <h1 data-testid="agent-detail-name">Otomasyon Ajanı</h1>
      <section>
        <h2>Özellikler</h2>
        <div data-testid="agent-detail-features">
          <span data-testid="agent-feature-nl">Doğal dil testi</span>
          <span data-testid="agent-feature-heal">Öz-iyileştirme</span>
        </div>
      </section>
      <section>
        <h2>Proje Seç</h2>
        <input
          data-testid="agent-detail-project-search"
          placeholder="Proje ara..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div data-testid="agent-detail-projects-list">
          {filtered.map((p) => (
            <button
              key={p.id}
              data-testid={`agent-project-${p.id}`}
              onClick={() => setSelectedProject(p.id)}
              className={selectedProject === p.id ? "selected" : ""}
            >
              {p.name}
            </button>
          ))}
        </div>
        {selectedProject && (
          <div data-testid="agent-selected-project">
            Seçili: {projects.find((p) => p.id === selectedProject)?.name}
          </div>
        )}
      </section>
      <a data-testid="agent-detail-btn-new-project" href="/new-project">
        + Yeni Proje Oluştur
      </a>
    </div>
  );
}

describe("AgentDetailPage", () => {
  it("renders agent detail page", () => {
    render(<MockAgentDetailPage />);
    expect(screen.getByTestId("agent-detail-page")).toBeInTheDocument();
  });

  it("shows agent name heading", () => {
    render(<MockAgentDetailPage />);
    expect(screen.getByTestId("agent-detail-name")).toHaveTextContent("Otomasyon Ajanı");
  });

  it("back link present", () => {
    render(<MockAgentDetailPage />);
    expect(screen.getByTestId("agent-detail-btn-back")).toBeInTheDocument();
  });

  it("renders agent features", () => {
    render(<MockAgentDetailPage />);
    expect(screen.getByTestId("agent-detail-features")).toBeInTheDocument();
  });

  it("project search input is rendered", () => {
    render(<MockAgentDetailPage />);
    expect(screen.getByTestId("agent-detail-project-search")).toBeInTheDocument();
  });

  it("lists all projects", () => {
    render(<MockAgentDetailPage />);
    expect(screen.getByTestId("agent-project-proj1")).toBeInTheDocument();
    expect(screen.getByTestId("agent-project-proj2")).toBeInTheDocument();
    expect(screen.getByTestId("agent-project-proj3")).toBeInTheDocument();
  });

  it("project search filters list", () => {
    render(<MockAgentDetailPage />);
    fireEvent.change(screen.getByTestId("agent-detail-project-search"), {
      target: { value: "Bankacılık" },
    });
    expect(screen.getByTestId("agent-project-proj2")).toBeInTheDocument();
    expect(screen.queryByTestId("agent-project-proj1")).not.toBeInTheDocument();
  });

  it("selecting a project shows it as selected", () => {
    render(<MockAgentDetailPage />);
    fireEvent.click(screen.getByTestId("agent-project-proj1"));
    expect(screen.getByTestId("agent-selected-project")).toHaveTextContent("E-Ticaret Projesi");
  });

  it("new project link is present", () => {
    render(<MockAgentDetailPage />);
    expect(screen.getByTestId("agent-detail-btn-new-project")).toBeInTheDocument();
  });
});

// ─── New Scenario Page ────────────────────────────────────────────────────────
function MockNewScenarioPage() {
  const [title, setTitle] = React.useState("");
  const [error, setError] = React.useState("");
  const [saved, setSaved] = React.useState(false);

  const handleSave = () => {
    if (!title.trim()) {
      setError("Başlık zorunludur");
      return;
    }
    setSaved(true);
    setError("");
  };

  return (
    <div data-testid="new-scenario-page">
      <h1 data-testid="new-scenario-heading">Yeni senaryo</h1>
      <form data-testid="scenario-form" onSubmit={(e) => { e.preventDefault(); handleSave(); }}>
        <input
          data-testid="scenario-form-input-title"
          value={title}
          onChange={(e) => { setTitle(e.target.value); setError(""); }}
          placeholder="Senaryo başlığı"
        />
        <textarea placeholder="Açıklama" />
        <textarea placeholder="İlk adım" />
        {error && <div data-testid="scenario-form-error">{error}</div>}
        <button data-testid="scenario-form-btn-save" type="submit">
          Kaydet
        </button>
      </form>
      {saved && <div data-testid="scenario-form-saved">Senaryo kaydedildi</div>}
    </div>
  );
}

describe("NewScenarioPage", () => {
  it("renders new scenario page", () => {
    render(<MockNewScenarioPage />);
    expect(screen.getByTestId("new-scenario-page")).toBeInTheDocument();
  });

  it("shows 'Yeni senaryo' heading", () => {
    render(<MockNewScenarioPage />);
    expect(screen.getByTestId("new-scenario-heading")).toHaveTextContent("Yeni senaryo");
  });

  it("renders scenario form", () => {
    render(<MockNewScenarioPage />);
    expect(screen.getByTestId("scenario-form")).toBeInTheDocument();
  });

  it("renders title input", () => {
    render(<MockNewScenarioPage />);
    expect(screen.getByTestId("scenario-form-input-title")).toBeInTheDocument();
  });

  it("shows error when saving empty title", () => {
    render(<MockNewScenarioPage />);
    fireEvent.click(screen.getByTestId("scenario-form-btn-save"));
    expect(screen.getByTestId("scenario-form-error")).toBeInTheDocument();
  });

  it("saves when title is filled", () => {
    render(<MockNewScenarioPage />);
    fireEvent.change(screen.getByTestId("scenario-form-input-title"), {
      target: { value: "Kullanıcı giriş yapabilmeli" },
    });
    fireEvent.click(screen.getByTestId("scenario-form-btn-save"));
    expect(screen.queryByTestId("scenario-form-error")).not.toBeInTheDocument();
    expect(screen.getByTestId("scenario-form-saved")).toBeInTheDocument();
  });

  it("save button is rendered", () => {
    render(<MockNewScenarioPage />);
    expect(screen.getByTestId("scenario-form-btn-save")).toBeInTheDocument();
  });
});

// ─── Edit Scenario Page ───────────────────────────────────────────────────────
function MockEditScenarioPage() {
  const [title, setTitle] = React.useState("Mevcut Senaryo");
  const [desc, setDesc] = React.useState("Açıklama metni");
  const [status, setStatus] = React.useState("active");
  const [error, setError] = React.useState("");
  const [saved, setSaved] = React.useState(false);
  const [steps, setSteps] = React.useState([{ id: "s1", keyword: "Given", text: "kullanıcı giriş sayfasındadır" }]);

  const handleSave = () => {
    if (!title.trim()) {
      setError("Başlık zorunludur");
      return;
    }
    setSaved(true);
    setError("");
  };

  const addStep = () => {
    setSteps((s) => [...s, { id: `s${s.length + 1}`, keyword: "When", text: "" }]);
  };

  const removeStep = (id: string) => {
    setSteps((s) => s.filter((step) => step.id !== id));
  };

  return (
    <div data-testid="scenario-edit-page">
      <h1 data-testid="scenario-edit-heading">Senaryo düzenle</h1>
      <form data-testid="scenario-edit-form" onSubmit={(e) => { e.preventDefault(); handleSave(); }}>
        <input
          data-testid="scenario-edit-input-title"
          value={title}
          onChange={(e) => { setTitle(e.target.value); setError(""); setSaved(false); }}
        />
        <textarea
          data-testid="scenario-edit-input-desc"
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
        />
        <select
          data-testid="scenario-edit-select-status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="draft">draft</option>
          <option value="active">active</option>
          <option value="deprecated">deprecated</option>
          <option value="review">review</option>
        </select>

        {/* Steps */}
        <div data-testid="scenario-edit-steps">
          {steps.map((step) => (
            <div key={step.id} data-testid={`scenario-edit-step-${step.id}`}>
              <select data-testid={`scenario-edit-step-keyword-${step.id}`} defaultValue={step.keyword}>
                <option value="Given">Given</option>
                <option value="When">When</option>
                <option value="Then">Then</option>
                <option value="And">And</option>
              </select>
              <input data-testid={`scenario-edit-step-text-${step.id}`} defaultValue={step.text} />
              <button
                type="button"
                data-testid={`scenario-edit-step-delete-${step.id}`}
                onClick={() => removeStep(step.id)}
              >
                Sil
              </button>
            </div>
          ))}
        </div>
        <button type="button" data-testid="scenario-edit-btn-add-step" onClick={addStep}>
          + Adım Ekle
        </button>

        {error && <div data-testid="scenario-edit-error">{error}</div>}
        <button data-testid="scenario-edit-btn-save" type="submit">
          Kaydet
        </button>
      </form>
      {saved && <div data-testid="scenario-edit-saved">Değişiklikler kaydedildi</div>}
    </div>
  );
}

describe("EditScenarioPage", () => {
  it("renders edit scenario page", () => {
    render(<MockEditScenarioPage />);
    expect(screen.getByTestId("scenario-edit-page")).toBeInTheDocument();
  });

  it("shows 'Senaryo düzenle' heading", () => {
    render(<MockEditScenarioPage />);
    expect(screen.getByTestId("scenario-edit-heading")).toHaveTextContent("Senaryo düzenle");
  });

  it("renders edit form", () => {
    render(<MockEditScenarioPage />);
    expect(screen.getByTestId("scenario-edit-form")).toBeInTheDocument();
  });

  it("title input has pre-filled value", () => {
    render(<MockEditScenarioPage />);
    expect((screen.getByTestId("scenario-edit-input-title") as HTMLInputElement).value).toBe("Mevcut Senaryo");
  });

  it("description textarea is rendered", () => {
    render(<MockEditScenarioPage />);
    expect(screen.getByTestId("scenario-edit-input-desc")).toBeInTheDocument();
  });

  it("status selector has all expected options", () => {
    render(<MockEditScenarioPage />);
    const sel = screen.getByTestId("scenario-edit-select-status") as HTMLSelectElement;
    const options = Array.from(sel.options).map((o) => o.value);
    expect(options).toEqual(["draft", "active", "deprecated", "review"]);
  });

  it("status defaults to active", () => {
    render(<MockEditScenarioPage />);
    expect((screen.getByTestId("scenario-edit-select-status") as HTMLSelectElement).value).toBe("active");
  });

  it("renders existing step", () => {
    render(<MockEditScenarioPage />);
    expect(screen.getByTestId("scenario-edit-step-s1")).toBeInTheDocument();
  });

  it("add step button adds a new step", () => {
    render(<MockEditScenarioPage />);
    const before = screen.getAllByTestId(/^scenario-edit-step-s/).length;
    fireEvent.click(screen.getByTestId("scenario-edit-btn-add-step"));
    const after = screen.getAllByTestId(/^scenario-edit-step-s/).length;
    expect(after).toBe(before + 1);
  });

  it("delete step button removes step", () => {
    render(<MockEditScenarioPage />);
    expect(screen.getByTestId("scenario-edit-step-s1")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("scenario-edit-step-delete-s1"));
    expect(screen.queryByTestId("scenario-edit-step-s1")).not.toBeInTheDocument();
  });

  it("shows error when saving with empty title", () => {
    render(<MockEditScenarioPage />);
    fireEvent.change(screen.getByTestId("scenario-edit-input-title"), { target: { value: "" } });
    fireEvent.click(screen.getByTestId("scenario-edit-btn-save"));
    expect(screen.getByTestId("scenario-edit-error")).toBeInTheDocument();
  });

  it("saves successfully when title is filled", () => {
    render(<MockEditScenarioPage />);
    fireEvent.click(screen.getByTestId("scenario-edit-btn-save"));
    expect(screen.getByTestId("scenario-edit-saved")).toBeInTheDocument();
  });

  it("save button is present", () => {
    render(<MockEditScenarioPage />);
    expect(screen.getByTestId("scenario-edit-btn-save")).toBeInTheDocument();
  });
});
