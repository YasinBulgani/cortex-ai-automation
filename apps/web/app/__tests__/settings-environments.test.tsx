/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

// ─── Suppress console errors ───────────────────────────────────────────────
beforeAll(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  jest.spyOn(console, "warn").mockImplementation(() => {});
  jest.spyOn(console, "log").mockImplementation(() => {});
});
afterAll(() => {
  (console.error as jest.Mock).mockRestore();
  (console.warn as jest.Mock).mockRestore();
  (console.log as jest.Mock).mockRestore();
});

// ─── Standard mocks ────────────────────────────────────────────────────────
jest.mock("next/link", () =>
  function MockLink({ href, children, ...rest }: any) {
    return <a href={href} {...rest}>{children}</a>;
  }
);

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  useParams: () => ({}),
  usePathname: () => "/p/proj-1",
}));

jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn(() => "proj-1"),
}));

jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn(),
}));

jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title, right }: any) => (
    <div data-testid="page-header">
      {title}
      {right}
    </div>
  ),
}));

jest.mock("@/components/nexus/SectionCard", () => ({
  SectionCard: ({ title, children, right }: any) => (
    <div data-testid="section-card">
      {title && <div>{title}</div>}
      {right && <div>{right}</div>}
      {children}
    </div>
  ),
}));

jest.mock("@/components/nexus/EmptyState", () => ({
  EmptyState: ({ title }: any) => <div data-testid="empty-state">{title}</div>,
}));

jest.mock("@/lib/hooks/use-api-testing", () => ({
  useEnvironments: jest.fn(),
  useCreateEnvironment: jest.fn(),
  useUpdateEnvironment: jest.fn(),
  useDeleteEnvironment: jest.fn(),
}));

// ─── Imports ───────────────────────────────────────────────────────────────
import { apiFetch } from "@/lib/api";
import {
  useEnvironments,
  useCreateEnvironment,
  useUpdateEnvironment,
  useDeleteEnvironment,
} from "@/lib/hooks/use-api-testing";

import SettingsPage from "@/app/(dashboard)/p/[projectId]/settings/page";
import EnvironmentsPage from "@/app/(dashboard)/p/[projectId]/environments/page";

const mockedApiFetch = apiFetch as jest.MockedFunction<typeof apiFetch>;
const mockedUseEnvironments = useEnvironments as jest.Mock;
const mockedUseCreateEnvironment = useCreateEnvironment as jest.Mock;
const mockedUseUpdateEnvironment = useUpdateEnvironment as jest.Mock;
const mockedUseDeleteEnvironment = useDeleteEnvironment as jest.Mock;

// ──────────────────────────────────────────────────────────────────────────
// SettingsPage Tests
// ──────────────────────────────────────────────────────────────────────────

describe("SettingsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("1. renders loading state initially", () => {
    // apiFetch never resolves during this test
    mockedApiFetch.mockReturnValue(new Promise(() => {}));
    render(<SettingsPage />);
    expect(screen.getByText(/Proje bilgileri yükleniyor/i)).toBeInTheDocument();
  });

  it("2. shows settings form after project loads (name, description fields)", async () => {
    mockedApiFetch.mockResolvedValueOnce({
      id: "proj-1",
      name: "Test Project",
      description: "A test description",
      base_url: "https://test.example.com",
    });
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByLabelText(/Proje Adı/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/Açıklama/i)).toBeInTheDocument();
  });

  it("3. pre-fills form with project data from API", async () => {
    mockedApiFetch.mockResolvedValueOnce({
      id: "proj-1",
      name: "ARK Banking",
      description: "Banking project",
      base_url: "https://api.ark.com",
    });
    render(<SettingsPage />);
    await waitFor(() => {
      expect((screen.getByLabelText(/Proje Adı/i) as HTMLInputElement).value).toBe("ARK Banking");
    });
    expect((screen.getByLabelText(/Açıklama/i) as HTMLTextAreaElement).value).toBe("Banking project");
  });

  it("4. name input is editable", async () => {
    mockedApiFetch.mockResolvedValueOnce({
      id: "proj-1",
      name: "Old Name",
      description: "",
      base_url: "",
    });
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByLabelText(/Proje Adı/i)).toBeInTheDocument();
    });
    const nameInput = screen.getByLabelText(/Proje Adı/i) as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "New Name" } });
    expect(nameInput.value).toBe("New Name");
  });

  it("5. base_url field renders", async () => {
    mockedApiFetch.mockResolvedValueOnce({
      id: "proj-1",
      name: "My Project",
      description: "",
      base_url: "https://base.example.com",
    });
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByLabelText(/Base URL/i)).toBeInTheDocument();
    });
    expect((screen.getByLabelText(/Base URL/i) as HTMLInputElement).value).toBe(
      "https://base.example.com"
    );
  });

  it("6. save button present", async () => {
    mockedApiFetch.mockResolvedValueOnce({
      id: "proj-1",
      name: "My Project",
      description: "",
      base_url: "",
    });
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Kaydet/i })).toBeInTheDocument();
    });
  });

  it("7. delete project button present and shows danger styling", async () => {
    mockedApiFetch.mockResolvedValueOnce({
      id: "proj-1",
      name: "My Project",
      description: "",
      base_url: "",
    });
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Projeyi Sil/i })).toBeInTheDocument();
    });
    const deleteBtn = screen.getByRole("button", { name: /Projeyi Sil/i });
    expect(deleteBtn.className).toMatch(/red/);
  });

  it("8. successful save shows success message", async () => {
    mockedApiFetch
      .mockResolvedValueOnce({
        id: "proj-1",
        name: "My Project",
        description: "",
        base_url: "",
      })
      .mockResolvedValueOnce(undefined); // save PUT call

    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Kaydet/i })).toBeInTheDocument();
    });

    const form = screen.getByRole("button", { name: /Kaydet/i }).closest("form")!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(screen.getByText(/Proje ayarları kaydedildi/i)).toBeInTheDocument();
    });
  });
});

// ──────────────────────────────────────────────────────────────────────────
// EnvironmentsPage Tests
// ──────────────────────────────────────────────────────────────────────────

describe("EnvironmentsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default mock state — override per test
    mockedUseCreateEnvironment.mockReturnValue({ mutate: jest.fn(), isPending: false });
    mockedUseUpdateEnvironment.mockReturnValue({ mutate: jest.fn(), isPending: false });
    mockedUseDeleteEnvironment.mockReturnValue({ mutate: jest.fn(), isPending: false });
  });

  it("1. renders page container (data-testid=environments-page)", () => {
    mockedUseEnvironments.mockReturnValue({ data: [], isLoading: false });
    render(<EnvironmentsPage />);
    expect(screen.getByTestId("environments-page")).toBeInTheDocument();
  });

  it("2. shows page title via PageHeader", () => {
    mockedUseEnvironments.mockReturnValue({ data: [], isLoading: false });
    render(<EnvironmentsPage />);
    const header = screen.getByTestId("page-header");
    expect(header).toBeInTheDocument();
    expect(header.textContent).toContain("Ortam");
  });

  it("3. shows loading state", () => {
    mockedUseEnvironments.mockReturnValue({ data: undefined, isLoading: true });
    render(<EnvironmentsPage />);
    // Loading spinner is rendered as an animated div — page container should still be there
    expect(screen.getByTestId("environments-page")).toBeInTheDocument();
    // The environments list is not rendered while loading
    expect(screen.queryByTestId("section-card")).not.toBeInTheDocument();
    expect(screen.queryByTestId("empty-state")).not.toBeInTheDocument();
  });

  it("4. shows empty state when no environments", () => {
    mockedUseEnvironments.mockReturnValue({ data: [], isLoading: false });
    render(<EnvironmentsPage />);
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state").textContent).toContain("ortam");
  });

  it("5. renders environment card when data loaded", () => {
    mockedUseEnvironments.mockReturnValue({
      data: [{ id: "env-1", name: "Staging", variables: {}, sensitive_keys: [], is_default: false }],
      isLoading: false,
    });
    render(<EnvironmentsPage />);
    const cards = screen.getAllByTestId("section-card");
    expect(cards.length).toBeGreaterThan(0);
    expect(screen.getByText("Staging")).toBeInTheDocument();
  });

  it("6. 'Yeni Ortam' create button is present", () => {
    mockedUseEnvironments.mockReturnValue({ data: [], isLoading: false });
    render(<EnvironmentsPage />);
    expect(screen.getByRole("button", { name: /Yeni Ortam/i })).toBeInTheDocument();
  });

  it("7. environment variables section renders when an environment is selected", () => {
    const env = { id: "env-1", name: "Staging", variables: { base_url: "https://staging.test" }, sensitive_keys: [], is_default: false };
    mockedUseEnvironments.mockReturnValue({
      data: [env],
      isLoading: false,
    });
    render(<EnvironmentsPage />);

    // Click the environment to select it
    fireEvent.click(screen.getByText("Staging"));

    // After selection, the Variables section card should appear
    const sectionCards = screen.getAllByTestId("section-card");
    const hasVariables = sectionCards.some((el) => el.textContent?.includes("Değişkenler"));
    expect(hasVariables).toBe(true);
  });

  it("8. variable key input is present in the form after selecting env and adding a row", () => {
    const env = { id: "env-1", name: "Staging", variables: {}, sensitive_keys: [], is_default: false };
    mockedUseEnvironments.mockReturnValue({
      data: [env],
      isLoading: false,
    });
    render(<EnvironmentsPage />);

    // Select the environment
    fireEvent.click(screen.getByText("Staging"));

    // Click "Değişken Ekle" to add a row
    const addVarBtn = screen.getByRole("button", { name: /Değişken Ekle/i });
    fireEvent.click(addVarBtn);

    // A key input with placeholder "key" should now be present
    const keyInputs = screen.getAllByPlaceholderText("key");
    expect(keyInputs.length).toBeGreaterThan(0);
  });
});
