/** @jest-environment jsdom */
/**
 * use-management.ts hook unit testleri.
 *
 * Test kapsamı:
 *   - useManagementProjects   — query: proje listesi çekilir
 *   - useCreateManagementCase — mutation: yeni test case oluşturulur
 *   - useManagementSettings   — query: settings okunur
 *   - usePatchManagementSetting — mutation: settings yazılır
 *
 * apiFetch tüm testlerde mock'lanır; gerçek HTTP bağlantısı YOK.
 */

import React from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const apiFetchMock = jest.fn();
jest.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

import {
  useManagementProjects,
  useCreateManagementCase,
  useManagementSettings,
  usePatchManagementSetting,
} from "@/lib/hooks/use-management";
import type { ManagementProject, TestCase } from "@/lib/hooks/use-management";

// ─── Shared helpers ─────────────────────────────────────────────────────────

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: qc }, children);
  };
}

const PROJECT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

const MOCK_PROJECT: ManagementProject = {
  id: PROJECT_ID,
  tenant_id: "tenant-1",
  tspm_project_id: "tspm-1",
  key: "PROJ",
  name: "Test Project",
  description: "A test project",
  status: "active",
  created_by: "user-1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const MOCK_CASE: TestCase = {
  id: "case-111",
  project_id: PROJECT_ID,
  suite_id: null,
  folder_id: null,
  parent_id: null,
  case_key: "PROJ-TC-001",
  title: "Login test",
  objective: "Verify login works",
  preconditions: null,
  test_data: {},
  priority: "P1",
  severity: "high",
  type: "manual",
  automation_status: "not_automated",
  status: "active",
  source_type: "manual",
  source_ref: null,
  tags: [],
  custom_fields: {},
  current_version: 1,
  last_run_status: null,
  last_run_at: null,
  owner_id: null,
  archived: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  steps: [],
};

const MOCK_SETTINGS = {
  project_id: PROJECT_ID,
  user_settings: {
    view_mode: "list",
    columns_visible: ["title", "status", "priority"],
    dark_mode: true,
  },
};

beforeEach(() => {
  apiFetchMock.mockReset();
});

// ─── 1. useManagementProjects ────────────────────────────────────────────────
describe("useManagementProjects", () => {
  test("başarılı fetch: data döner ve isLoading false olur", async () => {
    apiFetchMock.mockResolvedValue([MOCK_PROJECT]);

    const { result } = renderHook(() => useManagementProjects(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data).toEqual([MOCK_PROJECT]);
    expect(result.current.isError).toBe(false);
  });

  test("doğru endpoint'e GET isteği gönderir", async () => {
    apiFetchMock.mockResolvedValue([]);

    renderHook(() => useManagementProjects(), { wrapper: makeWrapper() });

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalled());

    const [url] = apiFetchMock.mock.calls[0];
    expect(url).toMatch(/\/api\/v1\/test-management\/projects/);
  });

  test("fetch hata verince isError true olur", async () => {
    apiFetchMock.mockRejectedValue(new Error("404 Not Found"));

    const { result } = renderHook(() => useManagementProjects(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });

  test("boş liste dönünce data boş array olur", async () => {
    apiFetchMock.mockResolvedValue([]);

    const { result } = renderHook(() => useManagementProjects(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toEqual([]);
  });
});

// ─── 2. useCreateManagementCase ─────────────────────────────────────────────
describe("useCreateManagementCase", () => {
  const NEW_CASE_PAYLOAD = {
    title: "New login test",
    priority: "P1" as const,
    type: "manual" as const,
  };

  test("mutate çağrısı doğru URL'e POST atar", async () => {
    apiFetchMock.mockResolvedValue(MOCK_CASE);

    const { result } = renderHook(
      () => useCreateManagementCase(PROJECT_ID),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync(NEW_CASE_PAYLOAD as Parameters<typeof result.current.mutateAsync>[0]);
    });

    const [url, init] = apiFetchMock.mock.calls[apiFetchMock.mock.calls.length - 1];
    expect(url).toMatch(new RegExp(`/projects/${PROJECT_ID}/cases`));
    expect(init.method).toBe("POST");
  });

  test("POST body'de payload doğru gönderilir", async () => {
    apiFetchMock.mockResolvedValue(MOCK_CASE);

    const { result } = renderHook(
      () => useCreateManagementCase(PROJECT_ID),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync(NEW_CASE_PAYLOAD as Parameters<typeof result.current.mutateAsync>[0]);
    });

    const [, init] = apiFetchMock.mock.calls[apiFetchMock.mock.calls.length - 1];
    expect(init.json.title).toBe("New login test");
    expect(init.json.priority).toBe("P1");
  });

  test("mutation başarılı → isSuccess true, data döner", async () => {
    apiFetchMock.mockResolvedValue(MOCK_CASE);

    const { result } = renderHook(
      () => useCreateManagementCase(PROJECT_ID),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync(NEW_CASE_PAYLOAD as Parameters<typeof result.current.mutateAsync>[0]);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_CASE);
  });

  test("mutation hata → isError true", async () => {
    apiFetchMock.mockRejectedValue(new Error("422 Unprocessable Entity"));

    const { result } = renderHook(
      () => useCreateManagementCase(PROJECT_ID),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      try {
        await result.current.mutateAsync(NEW_CASE_PAYLOAD as Parameters<typeof result.current.mutateAsync>[0]);
      } catch {
        // expected
      }
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ─── 3. useManagementSettings ───────────────────────────────────────────────
describe("useManagementSettings", () => {
  test("settings başarıyla okunur", async () => {
    apiFetchMock.mockResolvedValue(MOCK_SETTINGS);

    const { result } = renderHook(
      () => useManagementSettings(PROJECT_ID),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data).toEqual(MOCK_SETTINGS);
    expect(result.current.isError).toBe(false);
  });

  test("projectId yokken query çalışmaz (enabled: false)", () => {
    renderHook(() => useManagementSettings(undefined), {
      wrapper: makeWrapper(),
    });

    // projectId undefined → apiFetch çağrılmamalı
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  test("doğru endpoint'e istek gönderir", async () => {
    apiFetchMock.mockResolvedValue(MOCK_SETTINGS);

    renderHook(() => useManagementSettings(PROJECT_ID), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalled());

    const [url] = apiFetchMock.mock.calls[0];
    expect(url).toMatch(new RegExp(`/projects/${PROJECT_ID}/settings`));
  });

  test("fetch hata → isError true", async () => {
    apiFetchMock.mockRejectedValue(new Error("403 Forbidden"));

    const { result } = renderHook(
      () => useManagementSettings(PROJECT_ID),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  test("user_settings içindeki değerler döner", async () => {
    apiFetchMock.mockResolvedValue(MOCK_SETTINGS);

    const { result } = renderHook(
      () => useManagementSettings(PROJECT_ID),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data?.user_settings?.view_mode).toBe("list");
    expect(result.current.data?.user_settings?.dark_mode).toBe(true);
  });
});

// ─── 4. usePatchManagementSetting ───────────────────────────────────────────
describe("usePatchManagementSetting", () => {
  test("PATCH isteği doğru URL'e ve body ile gönderilir", async () => {
    // Settings query'si için ilk çağrı (useUpdateManagementUserSettings içinde)
    apiFetchMock.mockResolvedValue({ view_mode: "grid" });

    const { result } = renderHook(
      () => usePatchManagementSetting<string>(PROJECT_ID, "view_mode"),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync("grid");
    });

    const [url, init] = apiFetchMock.mock.calls[apiFetchMock.mock.calls.length - 1];
    expect(url).toMatch(new RegExp(`/projects/${PROJECT_ID}/settings/user`));
    expect(init.method).toBe("PATCH");
    expect(init.json).toEqual({ view_mode: "grid" });
  });

  test("farklı key ile farklı setting patch'lenir", async () => {
    apiFetchMock.mockResolvedValue({ dark_mode: false });

    const { result } = renderHook(
      () => usePatchManagementSetting<boolean>(PROJECT_ID, "dark_mode"),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync(false);
    });

    const [, init] = apiFetchMock.mock.calls[apiFetchMock.mock.calls.length - 1];
    expect(init.json).toEqual({ dark_mode: false });
  });

  test("mutation başarılı → isSuccess true", async () => {
    apiFetchMock.mockResolvedValue({ columns_visible: ["title"] });

    const { result } = renderHook(
      () => usePatchManagementSetting<string[]>(PROJECT_ID, "columns_visible"),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync(["title"]);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  test("mutation hata → isError true", async () => {
    apiFetchMock.mockRejectedValue(new Error("500 Server Error"));

    const { result } = renderHook(
      () => usePatchManagementSetting<string>(PROJECT_ID, "view_mode"),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      try {
        await result.current.mutateAsync("grid");
      } catch {
        // expected
      }
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  test("null değeri de patch'lenebilir", async () => {
    apiFetchMock.mockResolvedValue({ selected_suite: null });

    const { result } = renderHook(
      () => usePatchManagementSetting<null>(PROJECT_ID, "selected_suite"),
      { wrapper: makeWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync(null);
    });

    const [, init] = apiFetchMock.mock.calls[apiFetchMock.mock.calls.length - 1];
    expect(init.json).toEqual({ selected_suite: null });
  });
});
