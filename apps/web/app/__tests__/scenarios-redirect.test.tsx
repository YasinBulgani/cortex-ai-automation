/** @jest-environment jsdom */
/**
 * Regression tests for /scenarios and /scenarios/new redirect pages.
 *
 * Why these tests exist
 * ---------------------
 * The first cut of these pages read localStorage["bgts_active_project"] as
 * if it were a bare project id. But the canonical writer (useProject.tsx)
 * stores `JSON.stringify({id, name, ...})`. The redirect therefore built
 * URLs like `/p/{"id":"abc","name":"X"}/scenarios` — visibly broken.
 *
 * These tests pin the contract:
 *   - When the JSON object has a string .id, redirect to /p/<id>/scenarios.
 *   - When localStorage is empty → fall back to /portfolio (list) or
 *     /task-drafts (compose), per page semantics.
 *   - When the JSON is malformed → same fallback as empty.
 *   - The /new page must preserve query-string from the inbound URL.
 *   - The id must be URI-encoded (defense against odd ids with slashes).
 */
import React from "react";
import { render, waitFor } from "@testing-library/react";

const replace = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams(mockSearch),
}));

let mockSearch = "";

// Imported AFTER mocks so they pick up the mocked next/navigation.
import ScenariosRedirectPage from "@/app/(dashboard)/scenarios/page";
import NewScenarioRedirectPage from "@/app/(dashboard)/scenarios/new/page";

const LS_KEY = "bgts_active_project";

beforeEach(() => {
  replace.mockClear();
  window.localStorage.clear();
  mockSearch = "";
});

describe("/scenarios redirect", () => {
  it("redirects to /p/<id>/scenarios when a Project JSON exists", async () => {
    window.localStorage.setItem(LS_KEY, JSON.stringify({ id: "proj-42", name: "X" }));
    render(<ScenariosRedirectPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/p/proj-42/scenarios"));
  });

  it("falls back to /portfolio when localStorage is empty", async () => {
    render(<ScenariosRedirectPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/portfolio"));
  });

  it("falls back to /portfolio when JSON is malformed", async () => {
    window.localStorage.setItem(LS_KEY, "{not-json");
    render(<ScenariosRedirectPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/portfolio"));
  });

  it("falls back to /portfolio when .id is missing or not a string", async () => {
    window.localStorage.setItem(LS_KEY, JSON.stringify({ name: "no id here" }));
    render(<ScenariosRedirectPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/portfolio"));
  });

  it("URI-encodes ids with special characters", async () => {
    window.localStorage.setItem(LS_KEY, JSON.stringify({ id: "weird/id with space", name: "Y" }));
    render(<ScenariosRedirectPage />);
    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/p/weird%2Fid%20with%20space/scenarios")
    );
  });
});

describe("/scenarios/new redirect", () => {
  it("redirects to /p/<id>/scenarios/new and preserves query string", async () => {
    window.localStorage.setItem(LS_KEY, JSON.stringify({ id: "proj-7", name: "Z" }));
    mockSearch = "source=palette&utm=docs";
    render(<NewScenarioRedirectPage />);
    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/p/proj-7/scenarios/new?source=palette&utm=docs")
    );
  });

  it("falls back to /task-drafts (with qs) when no active project", async () => {
    mockSearch = "source=cmd";
    render(<NewScenarioRedirectPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/task-drafts?source=cmd"));
  });

  it("falls back to /task-drafts without trailing ? when query is empty", async () => {
    render(<NewScenarioRedirectPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/task-drafts"));
  });
});
