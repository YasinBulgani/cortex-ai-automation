/** @jest-environment jsdom */
/**
 * M-1 (BVA) + M-2 (Equivalence) + M-9 (Parameterized Cases) frontend tests.
 *
 * Mocks the `apiFetch` shim so we exercise hook → mutation wiring without
 * a server. ManagementShell sub-modules that hit the network (NotificationBell,
 * LanguageSwitcher) are stubbed.
 */
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

const apiFetchMock = jest.fn();
jest.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

// Heavy shell dependencies hit the network when mounted — stub them out.
jest.mock("@/components/management/NotificationBell", () => ({
  NotificationBell: () => null,
}));
jest.mock("@/components/LanguageSwitcher", () => ({
  LanguageSwitcher: () => null,
}));

import { ParameterizedCasesPanel } from "@/app/(dashboard)/p/[projectId]/management/_components/ParameterizedCasesPanel";

const CASE_ID = "33333333-3333-3333-3333-333333333333";
const PARAM_SET_ID = "44444444-4444-4444-4444-444444444444";

function withClient(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

beforeEach(() => {
  apiFetchMock.mockReset();
});

describe("ParameterizedCasesPanel", () => {
  function setupNoSets() {
    // GET /cases/.../params → []
    apiFetchMock.mockImplementation((url: string, init?: { method?: string }) => {
      if (url.endsWith("/params") && (!init || !init.method)) {
        return Promise.resolve([]);
      }
      return Promise.resolve(null);
    });
  }

  test("renders empty state and schema editor", async () => {
    setupNoSets();
    render(withClient(<ParameterizedCasesPanel caseId={CASE_ID} />));
    await waitFor(() =>
      expect(screen.getByText(/Henüz parametre seti yok/i)).toBeTruthy(),
    );
    expect(screen.getByPlaceholderText(/field name/i)).toBeTruthy();
    expect(screen.getByText(/Schema kaydet/i)).toBeTruthy();
  });

  test("creates a new param set when 'Schema kaydet' is clicked", async () => {
    let postedBody: unknown = null;
    apiFetchMock.mockImplementation((url: string, init?: { method?: string; json?: unknown }) => {
      if (url.endsWith("/params") && (!init || !init.method)) {
        return Promise.resolve([]);
      }
      if (url.endsWith("/params") && init?.method === "POST") {
        postedBody = init.json;
        return Promise.resolve({
          id: PARAM_SET_ID,
          tenant_id: "t",
          case_id: CASE_ID,
          schema_json: { fields: [{ name: "age", type: "int", required: true }] },
          created_at: new Date().toISOString(),
        });
      }
      return Promise.resolve([]);
    });

    render(withClient(<ParameterizedCasesPanel caseId={CASE_ID} />));
    await waitFor(() => expect(screen.getByPlaceholderText(/field name/i)).toBeTruthy());

    // Fill the first field row's name input.
    const nameInput = screen.getByPlaceholderText(/field name/i) as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "age" } });

    const saveBtn = screen.getByText(/Schema kaydet/i);
    await act(async () => {
      fireEvent.click(saveBtn);
    });

    await waitFor(() => expect(postedBody).not.toBeNull());
    const body = postedBody as { case_id: string; schema_json: { fields: Array<{ name: string }> } };
    expect(body.case_id).toBe(CASE_ID);
    expect(body.schema_json.fields[0].name).toBe("age");
  });

  test("renders DataTableEditor with AI / CSV / blank-row controls when a set exists", async () => {
    apiFetchMock.mockImplementation((url: string, init?: { method?: string }) => {
      if (url.endsWith("/params") && (!init || !init.method)) {
        return Promise.resolve([
          {
            id: PARAM_SET_ID,
            tenant_id: "t",
            case_id: CASE_ID,
            schema_json: { fields: [{ name: "name", type: "string", required: true }] },
            created_at: new Date().toISOString(),
          },
        ]);
      }
      if (url.endsWith(`/params/${PARAM_SET_ID}/data`)) {
        return Promise.resolve([]);
      }
      return Promise.resolve(null);
    });

    render(withClient(<ParameterizedCasesPanel caseId={CASE_ID} />));
    await waitFor(() => expect(screen.getByText(/AI ile satır üret/i)).toBeTruthy());
    expect(screen.getByText(/CSV yükle/i)).toBeTruthy();
    expect(screen.getByText(/\+ Boş satır/i)).toBeTruthy();
    // Expand button text is exactly "Expand" — ExpandRow has multiple matches.
    expect(screen.getByRole("button", { name: /^Expand$/i })).toBeTruthy();
  });

  test("AI satır üret button calls generate-rows endpoint with payload", async () => {
    let postedUrl = "";
    let postedJson: any = null;
    apiFetchMock.mockImplementation((url: string, init?: { method?: string; json?: unknown }) => {
      if (url.endsWith("/params") && (!init || !init.method)) {
        return Promise.resolve([
          {
            id: PARAM_SET_ID,
            tenant_id: "t",
            case_id: CASE_ID,
            schema_json: { fields: [{ name: "n", type: "int", required: true }] },
            created_at: new Date().toISOString(),
          },
        ]);
      }
      if (url.endsWith(`/params/${PARAM_SET_ID}/data`)) {
        return Promise.resolve([]);
      }
      if (url.endsWith(`/cases/${CASE_ID}/data`) && init?.method === "POST") {
        postedUrl = url;
        postedJson = init.json;
        return Promise.resolve([]);
      }
      return Promise.resolve(null);
    });

    render(withClient(<ParameterizedCasesPanel caseId={CASE_ID} />));
    await waitFor(() => expect(screen.getByText(/AI ile satır üret/i)).toBeTruthy());

    await act(async () => {
      fireEvent.click(screen.getByText(/AI ile satır üret/i));
    });

    await waitFor(() => expect(postedUrl).toContain(`/cases/${CASE_ID}/data`));
    expect(postedJson).toMatchObject({
      param_set_id: PARAM_SET_ID,
      source: "llm",
    });
    expect(typeof postedJson.count).toBe("number");
  });

  test("Expand button calls expand endpoint", async () => {
    let expandCalled = false;
    apiFetchMock.mockImplementation((url: string, init?: { method?: string }) => {
      if (url.endsWith("/params") && (!init || !init.method)) return Promise.resolve([]);
      if (url.endsWith(`/cases/${CASE_ID}/expand`) && init?.method === "POST") {
        expandCalled = true;
        return Promise.resolve({ execution_ids: ["a", "b"], run_case_ids: [] });
      }
      return Promise.resolve(null);
    });

    render(withClient(<ParameterizedCasesPanel caseId={CASE_ID} />));
    const expandBtn = await waitFor(() =>
      screen.getByRole("button", { name: /^Expand$/i }),
    );

    await act(async () => {
      fireEvent.click(expandBtn);
    });
    await waitFor(() => expect(expandCalled).toBe(true));
  });
});

// ── Hook-level coverage for BVA / EQ / Promote ──────────────────────────────


describe("use-mgmt-design hooks", () => {
  // Render hooks in a tiny harness component so we don't need renderHook.
  function HookProbe<T>({ run }: { run: () => T }) {
    const value = run();
    (HookProbe as any).lastValue = value;
    return null;
  }

  async function runHook<T>(useHook: () => T): Promise<T> {
    const qc = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
        mutations: { retry: false },
      },
    });
    render(
      <QueryClientProvider client={qc}>
        <HookProbe run={useHook} />
      </QueryClientProvider>,
    );
    return (HookProbe as any).lastValue as T;
  }

  test("useCreateBvaRun POSTs to /design/bva", async () => {
    apiFetchMock.mockResolvedValue({
      id: "r-1",
      tenant_id: "t",
      technique: "BVA",
      input_spec: {},
      generated_cases: [],
      source: "fallback",
      partitions: [],
      created_at: new Date().toISOString(),
    });
    const { useCreateBvaRun } = await import("@/lib/hooks/use-mgmt-design");
    const m = await runHook(() => useCreateBvaRun());
    await act(async () => {
      await m.mutateAsync({
        project_id: "p-1",
        fields: [{ name: "age", data_type: "int", min_value: "0", max_value: "9" }],
        requirement_text: "test",
      });
    });
    const [url, init] = apiFetchMock.mock.calls[apiFetchMock.mock.calls.length - 1];
    expect(url).toMatch(/\/design\/bva$/);
    expect(init.method).toBe("POST");
    expect(init.json.fields[0].name).toBe("age");
  });

  test("useCreateEqRun POSTs to /design/eq", async () => {
    apiFetchMock.mockResolvedValue({
      id: "r-2",
      tenant_id: "t",
      technique: "EQ",
      input_spec: {},
      generated_cases: [],
      source: "fallback",
      partitions: [],
      created_at: new Date().toISOString(),
    });
    const { useCreateEqRun } = await import("@/lib/hooks/use-mgmt-design");
    const m = await runHook(() => useCreateEqRun());
    await act(async () => {
      await m.mutateAsync({
        project_id: "p-1",
        fields: [{ name: "x", data_type: "int", min_value: "0", max_value: "9" }],
      });
    });
    const [url] = apiFetchMock.mock.calls[apiFetchMock.mock.calls.length - 1];
    expect(url).toMatch(/\/design\/eq$/);
  });

  test("usePromoteCases targets the run-id-scoped URL", async () => {
    apiFetchMock.mockResolvedValue({ case_ids: ["c1", "c2"] });
    const { usePromoteCases } = await import("@/lib/hooks/use-mgmt-design");
    const m = await runHook(() => usePromoteCases("r-99"));
    await act(async () => {
      await m.mutateAsync({ case_indexes: [0, 1], suite_id: null });
    });
    const [url, init] = apiFetchMock.mock.calls[apiFetchMock.mock.calls.length - 1];
    expect(url).toMatch(/\/design\/runs\/r-99\/promote$/);
    expect(init.method).toBe("POST");
    expect(init.json.case_indexes).toEqual([0, 1]);
  });

  test("useDesignRuns serialises filter params", async () => {
    apiFetchMock.mockResolvedValue([]);
    const { useDesignRuns } = await import("@/lib/hooks/use-mgmt-design");
    await runHook(() => useDesignRuns({ technique: "BVA", projectId: "p-x" }));
    await waitFor(() => {
      const lastCall = apiFetchMock.mock.calls[apiFetchMock.mock.calls.length - 1];
      expect(lastCall).toBeDefined();
      expect(String(lastCall[0])).toMatch(/technique=BVA/);
      expect(String(lastCall[0])).toMatch(/project_id=p-x/);
    });
  });
});
