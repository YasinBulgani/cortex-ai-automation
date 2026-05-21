/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";

// ── Mock: next/navigation ─────────────────────────────────────────────────────
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn() }),
  useParams: () => ({}),
}));

// ── Mock: @/lib/hooks/use-dsl ─────────────────────────────────────────────────
jest.mock("@/lib/hooks/use-dsl", () => ({
  useDslAction: jest.fn(() => ({ data: null, isLoading: false, error: null })),
  useDslEditorConfig: jest.fn(() => ({ data: null, isLoading: false })),
  useDslCreateAction: jest.fn(() => ({ mutateAsync: jest.fn(), isPending: false })),
  useDslUpdateAction: jest.fn(() => ({ mutateAsync: jest.fn(), isPending: false })),
  useDslDeleteAction: jest.fn(() => ({ mutateAsync: jest.fn(), isPending: false })),
  useDslDeprecateAction: jest.fn(() => ({ mutateAsync: jest.fn(), isPending: false })),
  useDslGenerateAiAliases: jest.fn(() => ({ mutateAsync: jest.fn(), isPending: false })),
}));

// ── Mock: @/lib/hooks/use-auth ────────────────────────────────────────────────
jest.mock("@/lib/hooks/use-auth", () => ({
  useCurrentUser: jest.fn(() => ({
    data: { roles: ["admin"], permissions: [] },
    isLoading: false,
  })),
}));

// ── Mock: @/lib/api-client (pulled in transitively by use-dsl) ────────────────
jest.mock("@/lib/api-client", () => ({
  apiFetch: jest.fn(),
  getToken: jest.fn(() => "token"),
  setTokens: jest.fn(),
  clearTokens: jest.fn(),
  ApiError: class ApiError extends Error {
    body: unknown;
    constructor(message: string, body?: unknown) {
      super(message);
      this.body = body;
    }
  },
}));

// ── Import under test ─────────────────────────────────────────────────────────
import { DslActionEditor } from "../DslActionEditor";

// ── Tests ─────────────────────────────────────────────────────────────────────
describe("DslActionEditor", () => {
  it("renders without crash in create mode (no actionId)", () => {
    expect(() =>
      render(<DslActionEditor mode="create" />)
    ).not.toThrow();
  });

  it("renders without crash in edit mode (with actionId prop)", () => {
    expect(() =>
      render(<DslActionEditor mode="edit" actionId="click_on_button" />)
    ).not.toThrow();
  });

  it("shows form inputs for alias (TR section is present)", () => {
    render(<DslActionEditor mode="create" />);
    // The Alias'lar section heading
    expect(screen.getByText("Alias'lar")).toBeInTheDocument();
  });

  it("shows language labels for TR and EN alias sections", () => {
    render(<DslActionEditor mode="create" />);
    // Two language labels rendered via <label className={LABEL}>
    expect(screen.getByText("Türkçe")).toBeInTheDocument();
    expect(screen.getByText("İngilizce")).toBeInTheDocument();
  });

  it("shows the alias add buttons for TR and EN", () => {
    render(<DslActionEditor mode="create" />);
    expect(screen.getByText("+ TR alias")).toBeInTheDocument();
    expect(screen.getByText("+ EN alias")).toBeInTheDocument();
  });

  it("shows submit/save button (data-testid: dsl-editor-save)", () => {
    render(<DslActionEditor mode="create" />);
    expect(screen.getByTestId("dsl-editor-save")).toBeInTheDocument();
  });

  it("save button shows 'Oluştur' in create mode", () => {
    render(<DslActionEditor mode="create" />);
    expect(screen.getByTestId("dsl-editor-save")).toHaveTextContent("Oluştur");
  });

  it("save button shows 'Güncelle' in edit mode", () => {
    render(<DslActionEditor mode="edit" actionId="click_on_button" />);
    expect(screen.getByTestId("dsl-editor-save")).toHaveTextContent("Güncelle");
  });

  it("shows cancel/back button with '← Geri' text", () => {
    render(<DslActionEditor mode="create" />);
    expect(screen.getByText("← Geri")).toBeInTheDocument();
  });

  it("shows page heading 'Yeni DSL Cümleciği' in create mode", () => {
    render(<DslActionEditor mode="create" />);
    expect(screen.getByText("Yeni DSL Cümleciği")).toBeInTheDocument();
  });

  it("shows ID input field in create mode", () => {
    render(<DslActionEditor mode="create" />);
    const idInput = screen.getByPlaceholderText("click_on_button");
    expect(idInput).toBeInTheDocument();
  });

  it("shows category input field", () => {
    render(<DslActionEditor mode="create" />);
    const catInput = screen.getByPlaceholderText("ui.click");
    expect(catInput).toBeInTheDocument();
  });

  it("shows description textarea", () => {
    render(<DslActionEditor mode="create" />);
    const descInput = screen.getByPlaceholderText(
      "Cümleciğin ne yaptığının kısa açıklaması"
    );
    expect(descInput).toBeInTheDocument();
  });

  it("shows git mode selector", () => {
    render(<DslActionEditor mode="create" />);
    const gitSelect = screen.getByLabelText("Git kaydetme modu");
    expect(gitSelect).toBeInTheDocument();
  });

  it("shows 'Kaydet' section heading in the sidebar", () => {
    render(<DslActionEditor mode="create" />);
    expect(screen.getByText("Kaydet")).toBeInTheDocument();
  });

  it("shows Parametreler section heading", () => {
    render(<DslActionEditor mode="create" />);
    expect(screen.getByText("Parametreler")).toBeInTheDocument();
  });

  it("shows + Parametre button to add parameters", () => {
    render(<DslActionEditor mode="create" />);
    expect(screen.getByText("+ Parametre")).toBeInTheDocument();
  });
});
