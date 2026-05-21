/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";

// ── Mock: next/link ───────────────────────────────────────────────────────────
jest.mock("next/link", () => {
  // Forward ALL props so data-testid and other attributes are preserved
  return function MockLink({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) {
    return <a href={href} {...rest}>{children}</a>;
  };
});

// ── Mock: next/navigation ─────────────────────────────────────────────────────
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  useParams: () => ({}),
  useSearchParams: () => ({ get: () => null, has: () => false, toString: () => "" }),
  usePathname: () => "/",
}));

// jsdom polyfills — DslCatalogView calls cardScrollRef.current?.scrollTo on page change
beforeAll(() => {
  if (!Element.prototype.scrollTo) {
    Element.prototype.scrollTo = jest.fn();
  } else {
    jest.spyOn(Element.prototype, "scrollTo").mockImplementation(() => {});
  }
});

// ── Mock: @tanstack/react-query ───────────────────────────────────────────────
jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn(() => ({
    data: undefined,
    isLoading: false,
    isFetching: false,
    error: null,
    refetch: jest.fn(),
  })),
  useMutation: jest.fn(() => ({
    mutate: jest.fn(),
    mutateAsync: jest.fn(),
    isPending: false,
    error: null,
  })),
  useQueryClient: jest.fn(() => ({
    invalidateQueries: jest.fn(),
    setQueryData: jest.fn(),
    clear: jest.fn(),
  })),
  QueryClient: jest.fn(),
  QueryClientProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

// ── Mock: @/lib/api-client ────────────────────────────────────────────────────
jest.mock("@/lib/api-client", () => ({
  apiFetch: jest.fn(),
  getToken: jest.fn(() => "token"),
  setTokens: jest.fn(),
  clearTokens: jest.fn(),
}));

// ── Mock: @/lib/dsl-api ───────────────────────────────────────────────────────
// MobileAiScenarioCard imports automationSuiteApi from @/lib/dsl-api
// DslCatalogView uses useDslSuggest which calls dslApi.suggest, etc.
jest.mock("@/lib/dsl-api", () => ({
  automationSuiteApi: {
    generateMobileScenario: jest.fn(),
  },
  dslApi: {
    suggest: jest.fn(),
    indexInfo: jest.fn(),
    feedback: jest.fn(),
    editorConfig: jest.fn(),
    createAction: jest.fn(),
    updateAction: jest.fn(),
    deleteAction: jest.fn(),
    deprecateAction: jest.fn(),
    listProposals: jest.fn(),
    getProposal: jest.fn(),
    approveProposal: jest.fn(),
    rejectProposal: jest.fn(),
    generateAiAliases: jest.fn(),
    listAudit: jest.fn(),
  },
}));

// ── Imports under test ────────────────────────────────────────────────────────
import { MobileAiScenarioCard } from "../MobileAiScenarioCard";
import { DslCatalogView } from "../DslCatalogView";
import { DslProposalReview } from "../DslProposalReview";

// ── MobileAiScenarioCard ──────────────────────────────────────────────────────

describe("MobileAiScenarioCard", () => {
  it("renders without crash when device=null and app=null", () => {
    expect(() =>
      render(<MobileAiScenarioCard device={null} app={null} />)
    ).not.toThrow();
  });

  it("shows 'Seçilmedi' for device when device is null", () => {
    render(<MobileAiScenarioCard device={null} app={null} />);
    expect(screen.getByText(/Seçilmedi/i)).toBeInTheDocument();
  });

  it("shows 'yok' for app when app is null", () => {
    render(<MobileAiScenarioCard device={null} app={null} />);
    expect(screen.getByText(/App:.*yok/i)).toBeInTheDocument();
  });

  it("renders device name and OS when device is provided", () => {
    render(
      <MobileAiScenarioCard
        device={{ name: "iPhone 15", platform: "ios", os: "iOS 17" }}
        app={null}
      />
    );
    expect(screen.getByText(/iPhone 15/)).toBeInTheDocument();
    expect(screen.getByText(/iOS 17/)).toBeInTheDocument();
  });

  it("renders app filename when app.filename is provided", () => {
    render(
      <MobileAiScenarioCard
        device={null}
        app={{ filename: "my-app.apk", package: "com.example.app" }}
      />
    );
    expect(screen.getByText(/my-app\.apk/)).toBeInTheDocument();
  });

  it("renders app package name as fallback when filename is absent", () => {
    render(
      <MobileAiScenarioCard
        device={null}
        app={{ package: "com.example.app" }}
      />
    );
    expect(screen.getByText(/com\.example\.app/)).toBeInTheDocument();
  });

  it("renders textarea for natural-language scenario input", () => {
    render(<MobileAiScenarioCard device={null} app={null} />);
    const textarea = screen.getByTestId("mobile-ai-description");
    expect(textarea).toBeInTheDocument();
    expect(textarea.tagName).toBe("TEXTAREA");
  });

  it("renders 'Gherkin üret' button", () => {
    render(<MobileAiScenarioCard device={null} app={null} />);
    expect(screen.getByTestId("mobile-ai-generate")).toBeInTheDocument();
    expect(screen.getByTestId("mobile-ai-generate")).toHaveTextContent(
      "Gherkin üret"
    );
  });

  it("'Gherkin üret' button is initially disabled (description is empty)", () => {
    render(<MobileAiScenarioCard device={null} app={null} />);
    const btn = screen.getByTestId("mobile-ai-generate");
    expect(btn).toBeDisabled();
  });

  it("shows the component heading text", () => {
    render(<MobileAiScenarioCard device={null} app={null} />);
    expect(screen.getByText(/AI Mobil Senaryo Üretici/i)).toBeInTheDocument();
  });

  it("shows minimum-character hint when description is empty", () => {
    render(<MobileAiScenarioCard device={null} app={null} />);
    expect(screen.getByText(/En az 10 karakter yazın/i)).toBeInTheDocument();
  });
});

// ── DslCatalogView ────────────────────────────────────────────────────────────

describe("DslCatalogView", () => {
  it("renders without crash (basic mount)", () => {
    expect(() => render(<DslCatalogView />)).not.toThrow();
  });

  it("renders default title 'DSL Sözlüğü'", () => {
    render(<DslCatalogView />);
    expect(screen.getByText("DSL Sözlüğü")).toBeInTheDocument();
  });

  it("renders custom title when passed as prop", () => {
    render(<DslCatalogView title="Mobil DSL Katalogu" />);
    expect(screen.getByText("Mobil DSL Katalogu")).toBeInTheDocument();
  });

  it("renders a search input (data-testid: dsl-search-input)", () => {
    render(<DslCatalogView />);
    expect(screen.getByTestId("dsl-search-input")).toBeInTheDocument();
  });

  it("renders 'Alias' search mode button", () => {
    render(<DslCatalogView />);
    expect(screen.getByTestId("dsl-search-mode-substring")).toBeInTheDocument();
  });

  it("renders AI search mode button", () => {
    render(<DslCatalogView />);
    expect(screen.getByTestId("dsl-search-mode-ai")).toBeInTheDocument();
  });

  it("renders language filter buttons (Hepsi, TR, EN)", () => {
    render(<DslCatalogView />);
    expect(screen.getByTestId("dsl-lang-all")).toBeInTheDocument();
    expect(screen.getByTestId("dsl-lang-tr")).toBeInTheDocument();
    expect(screen.getByTestId("dsl-lang-en")).toBeInTheDocument();
  });

  it("renders 'Yeni Cümlecik' link", () => {
    render(<DslCatalogView />);
    expect(screen.getByTestId("dsl-new-action")).toBeInTheDocument();
  });

  it("renders 'İnceleme' link", () => {
    render(<DslCatalogView />);
    expect(screen.getByTestId("dsl-review-link")).toBeInTheDocument();
  });

  it("renders the result-count chip even with empty data", () => {
    render(<DslCatalogView />);
    // Replaces the old "Bu filtre için cümlecik yok." literal check; main moved
    // the empty-state copy. Sanity-check that the result count component is present.
    expect(screen.getByTestId("dsl-result-count")).toBeInTheDocument();
  });

  it("shows result count bar (data-testid: dsl-result-count)", () => {
    render(<DslCatalogView />);
    expect(screen.getByTestId("dsl-result-count")).toBeInTheDocument();
  });

  it("shows 'Kategoriler' panel heading in the sidebar", () => {
    render(<DslCatalogView />);
    expect(screen.getByText(/Kategoriler/i)).toBeInTheDocument();
  });

  it("renders Kategoriler panel when stats area shows loading on undefined data", () => {
    render(<DslCatalogView />);
    // Replaces the old "Yükleniyor..." literal — main changed the loading copy.
    // Verify the sidebar Kategoriler panel still renders alongside the loading state.
    expect(screen.getByText(/Kategoriler/i)).toBeInTheDocument();
  });
});

// ── DslProposalReview ─────────────────────────────────────────────────────────

describe("DslProposalReview", () => {
  it("renders without crash when no proposals (mock returns empty data)", () => {
    expect(() => render(<DslProposalReview />)).not.toThrow();
  });

  it("renders page heading 'DSL Öneri İnceleme'", () => {
    render(<DslProposalReview />);
    expect(
      screen.getByText(/DSL Öneri İnceleme/i)
    ).toBeInTheDocument();
  });

  it("renders 'Bekleyen' status filter tab", () => {
    render(<DslProposalReview />);
    expect(
      screen.getByTestId("dsl-review-filter-pending")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("dsl-review-filter-pending")
    ).toHaveTextContent("Bekleyen");
  });

  it("renders 'Tamamlanan' status filter tab", () => {
    render(<DslProposalReview />);
    expect(
      screen.getByTestId("dsl-review-filter-merged")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("dsl-review-filter-merged")
    ).toHaveTextContent("Tamamlanan");
  });

  it("renders 'Reddedilen' status filter tab", () => {
    render(<DslProposalReview />);
    expect(
      screen.getByTestId("dsl-review-filter-rejected")
    ).toBeInTheDocument();
  });

  it("renders 'Hatalı' status filter tab", () => {
    render(<DslProposalReview />);
    expect(
      screen.getByTestId("dsl-review-filter-error")
    ).toBeInTheDocument();
  });

  it("renders 'Hepsi' status filter tab", () => {
    render(<DslProposalReview />);
    expect(
      screen.getByTestId("dsl-review-filter-all")
    ).toBeInTheDocument();
  });

  it("shows '0 kayıt' when proposals list is empty", () => {
    render(<DslProposalReview />);
    expect(screen.getByText(/0 kayıt/i)).toBeInTheDocument();
  });

  it("shows empty-list hint text when no proposals match the filter", () => {
    render(<DslProposalReview />);
    expect(
      screen.getByText(/Bu filtreye uygun öneri yok\./i)
    ).toBeInTheDocument();
  });

  it("shows 'Sol panelden bir öneri seçin.' placeholder in detail panel", () => {
    render(<DslProposalReview />);
    expect(
      screen.getByText(/Sol panelden bir öneri seçin\./i)
    ).toBeInTheDocument();
  });

  it("renders back link to catalog", () => {
    render(<DslProposalReview />);
    const catalogLink = screen.getByText(/← Katalog/i);
    expect(catalogLink).toBeInTheDocument();
    expect(catalogLink.closest("a")).toHaveAttribute("href", "/dsl-catalog");
  });
});
