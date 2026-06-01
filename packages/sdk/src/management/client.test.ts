/**
 * ManagementClient unit tests.
 */

import { describe, it, expect, vi } from "vitest";
import { CortexClient } from "../common/client";
import { ManagementClient } from "./client";

function makeHttp(response: unknown) {
  const mockFetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    statusText: "OK",
    json: () => Promise.resolve(response),
  } as unknown as Response);

  return new CortexClient({
    baseUrl: "https://api.example.com",
    fetch: mockFetch,
  });
}

describe("ManagementClient", () => {
  it("lists projects at correct path", async () => {
    const projects = [{ id: "p1", name: "Alpha" }];
    const http = makeHttp(projects);
    const spy = vi.spyOn(http, "get");
    const mgmt = new ManagementClient(http);

    const result = await mgmt.projects.list();
    expect(result).toEqual(projects);
    expect(spy).toHaveBeenCalledWith("/api/v1/test-management/projects");
  });

  it("lists cases for a project", async () => {
    const cases = [{ id: "c1", title: "Login Test" }];
    const http = makeHttp(cases);
    const spy = vi.spyOn(http, "get");
    const mgmt = new ManagementClient(http);

    await mgmt.cases("proj-123").list();
    expect(spy).toHaveBeenCalledWith(
      "/api/v1/test-management/projects/proj-123/cases",
    );
  });

  it("passes q and include_archived to cases list", async () => {
    const http = makeHttp([]);
    const spy = vi.spyOn(http, "get");
    const mgmt = new ManagementClient(http);

    await mgmt.cases("proj-123").list({ q: "login", includeArchived: true });
    expect(spy).toHaveBeenCalledWith(expect.stringContaining("q=login"));
    expect(spy).toHaveBeenCalledWith(
      expect.stringContaining("include_archived=true"),
    );
  });

  it("fetches traceability matrix", async () => {
    const matrix = [{ requirement_key: "REQ-001", cases: [] }];
    const http = makeHttp(matrix);
    const spy = vi.spyOn(http, "get");
    const mgmt = new ManagementClient(http);

    const result = await mgmt.requirements("proj-123").traceability();
    expect(result).toEqual(matrix);
    expect(spy).toHaveBeenCalledWith(
      "/api/v1/test-management/projects/proj-123/requirements/traceability",
    );
  });

  it("commits an import job", async () => {
    const job = { id: "job-1", status: "committed" };
    const http = makeHttp(job);
    const spy = vi.spyOn(http, "post");
    const mgmt = new ManagementClient(http);

    await mgmt.imports("proj-123").commit("job-1");
    expect(spy).toHaveBeenCalledWith(
      "/api/v1/test-management/projects/proj-123/imports/job-1/commit",
      undefined,
    );
  });

  it("archives a case", async () => {
    const archived = { id: "c1", archived: true };
    const http = makeHttp(archived);
    const spy = vi.spyOn(http, "post");
    const mgmt = new ManagementClient(http);

    await mgmt.cases("proj-123").archive("c1");
    expect(spy).toHaveBeenCalledWith(
      "/api/v1/test-management/projects/proj-123/cases/c1/archive",
      undefined,
    );
  });
});
