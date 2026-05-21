/** @jest-environment jsdom */
import React from "react";
import { renderHook, act } from "@testing-library/react";
import { ProjectProvider, useProject, type Project } from "../useProject";

const SAMPLE_PROJECT: Project = {
  id: "proj-1",
  name: "Test Projesi",
  target_url: "https://example.com",
};

const LS_KEY = "bgts_active_project";

function wrapper({ children }: { children: React.ReactNode }) {
  return <ProjectProvider>{children}</ProjectProvider>;
}

describe("useProject / ProjectProvider", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns null project initially when no localStorage entry", () => {
    const { result } = renderHook(() => useProject(), { wrapper });
    // project starts null (state default before useEffect reads localStorage)
    // After hydration it may still be null if nothing stored
    expect(result.current.project).toBeNull();
    expect(result.current.projectId).toBeNull();
  });

  it("setProject stores project and updates state", () => {
    const { result } = renderHook(() => useProject(), { wrapper });

    act(() => {
      result.current.setProject(SAMPLE_PROJECT);
    });

    expect(result.current.project).toEqual(SAMPLE_PROJECT);
    expect(result.current.projectId).toBe("proj-1");
  });

  it("setProject writes to localStorage", () => {
    const { result } = renderHook(() => useProject(), { wrapper });

    act(() => {
      result.current.setProject(SAMPLE_PROJECT);
    });

    const stored = JSON.parse(localStorage.getItem(LS_KEY) || "null");
    expect(stored).toEqual(SAMPLE_PROJECT);
  });

  it("setProject(null) clears localStorage and state", () => {
    const { result } = renderHook(() => useProject(), { wrapper });

    act(() => { result.current.setProject(SAMPLE_PROJECT); });
    act(() => { result.current.setProject(null); });

    expect(result.current.project).toBeNull();
    expect(result.current.projectId).toBeNull();
    expect(localStorage.getItem(LS_KEY)).toBeNull();
  });

  it("loads project from localStorage on mount (hydration)", async () => {
    localStorage.setItem(LS_KEY, JSON.stringify(SAMPLE_PROJECT));

    const { result } = renderHook(() => useProject(), { wrapper });

    // After the useEffect fires (act flushes effects)
    expect(result.current.project).toEqual(SAMPLE_PROJECT);
  });

  it("projectId matches project.id", () => {
    const { result } = renderHook(() => useProject(), { wrapper });

    act(() => { result.current.setProject({ id: "xyz", name: "XYZ" }); });

    expect(result.current.projectId).toBe("xyz");
  });

  it("handles corrupted localStorage gracefully (does not throw)", () => {
    localStorage.setItem(LS_KEY, "not-valid-json{{{{");
    expect(() => renderHook(() => useProject(), { wrapper })).not.toThrow();
  });

  it("default context values work outside provider (fallback)", () => {
    // No wrapper — uses createContext default values
    const { result } = renderHook(() => useProject());
    expect(result.current.project).toBeNull();
    expect(result.current.projectId).toBeNull();
    expect(typeof result.current.setProject).toBe("function");
  });
});
