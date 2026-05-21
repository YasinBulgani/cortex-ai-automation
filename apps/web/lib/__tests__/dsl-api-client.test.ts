/** @jest-environment node */

// ── Mock: @/lib/api-client ────────────────────────────────────────────────────
jest.mock("@/lib/api-client", () => ({
  apiFetch: jest.fn(),
}));

import { apiFetch } from "@/lib/api-client";
import { dslApi } from "../dsl-api";

const mockApiFetch = apiFetch as jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
});

// ── dslApi.suggest ─────────────────────────────────────────────────────────────

describe("dslApi.suggest", () => {
  it("calls apiFetch with POST /api/v1/dsl/suggest", async () => {
    mockApiFetch.mockResolvedValueOnce({ query: "tıkla", total: 0, items: [] });
    await dslApi.suggest({ description: "tıkla butona" });
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/dsl/suggest", {
      method: "POST",
      json: { description: "tıkla butona" },
    });
  });

  it("returns what apiFetch returns", async () => {
    const expected = { query: "tıkla", total: 1, items: [{ action: {}, matched_language: "tr", matched_alias: "tıkla" }] };
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.suggest({ description: "tıkla" });
    expect(result).toBe(expected);
  });

  it("passes limit and mode in the request body", async () => {
    mockApiFetch.mockResolvedValueOnce({ query: "q", total: 0, items: [] });
    await dslApi.suggest({ description: "some action", limit: 5, mode: "hybrid" });
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/dsl/suggest", {
      method: "POST",
      json: { description: "some action", limit: 5, mode: "hybrid" },
    });
  });
});

// ── dslApi.indexInfo ───────────────────────────────────────────────────────────

describe("dslApi.indexInfo", () => {
  it("calls apiFetch with GET /api/v1/dsl/index/info", async () => {
    mockApiFetch.mockResolvedValueOnce({ ready: true, rows: 100, dim: 384, model: "all-MiniLM-L6-v2", corpus_hash: "abc" });
    await dslApi.indexInfo();
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/dsl/index/info");
  });

  it("returns what apiFetch returns", async () => {
    const expected = { ready: false, rows: 0, dim: 0, model: "none", corpus_hash: "" };
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.indexInfo();
    expect(result).toBe(expected);
  });

  it("does not pass any body or method options", async () => {
    mockApiFetch.mockResolvedValueOnce({ ready: true, rows: 50, dim: 384, model: "m", corpus_hash: "h" });
    await dslApi.indexInfo();
    // Should be called with only the URL, no options argument
    expect(mockApiFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockApiFetch.mock.calls[0];
    expect(url).toBe("/api/v1/dsl/index/info");
    expect(options).toBeUndefined();
  });
});

// ── dslApi.feedback ────────────────────────────────────────────────────────────

describe("dslApi.feedback", () => {
  const feedbackBody = {
    query: "tıkla",
    action_id: "click.element",
    vote: "up" as const,
  };

  it("calls apiFetch with POST /api/v1/dsl/feedback", async () => {
    mockApiFetch.mockResolvedValueOnce({ id: "fb-1", recorded_at: "2025-01-01T00:00:00Z", bonus_applied: 1 });
    await dslApi.feedback(feedbackBody);
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/dsl/feedback", {
      method: "POST",
      json: feedbackBody,
    });
  });

  it("returns what apiFetch returns", async () => {
    const expected = { id: "fb-42", recorded_at: "2025-06-01T00:00:00Z", bonus_applied: 0 };
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.feedback(feedbackBody);
    expect(result).toBe(expected);
  });

  it("passes all feedback fields including optional rank and search_mode", async () => {
    mockApiFetch.mockResolvedValueOnce({ id: "fb-2", recorded_at: "", bonus_applied: 0 });
    const fullBody = { ...feedbackBody, rank: 3, raw_score: 0.95, search_mode: "semantic" as const };
    await dslApi.feedback(fullBody);
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/dsl/feedback", {
      method: "POST",
      json: fullBody,
    });
  });
});

// ── dslApi.editorConfig ────────────────────────────────────────────────────────

describe("dslApi.editorConfig", () => {
  it("calls apiFetch with GET /api/v1/dsl/editor/config", async () => {
    mockApiFetch.mockResolvedValueOnce({ git_enabled: true, git_mode: "pr", base_branch: "main", provider: "github", remote: "origin", strict_clean: false });
    await dslApi.editorConfig();
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/dsl/editor/config");
  });

  it("returns what apiFetch returns", async () => {
    const expected = { git_enabled: false, git_mode: "direct_commit" as const, base_branch: "develop", provider: "gitlab", remote: "upstream", strict_clean: true };
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.editorConfig();
    expect(result).toBe(expected);
  });

  it("does not pass any body or method options", async () => {
    mockApiFetch.mockResolvedValueOnce({});
    await dslApi.editorConfig();
    const [url, options] = mockApiFetch.mock.calls[0];
    expect(url).toBe("/api/v1/dsl/editor/config");
    expect(options).toBeUndefined();
  });
});

// ── dslApi.createAction ────────────────────────────────────────────────────────

describe("dslApi.createAction", () => {
  const createBody = {
    action: { id: "new.action", category: "ui", description: "New action" } as any,
  };

  it("calls apiFetch with POST /api/v1/dsl/actions", async () => {
    mockApiFetch.mockResolvedValueOnce({ proposal_id: "p1", status: "pending", mode: "review", action_id: "new.action", file_paths: [] });
    await dslApi.createAction(createBody);
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/dsl/actions", {
      method: "POST",
      json: createBody,
    });
  });

  it("returns what apiFetch returns", async () => {
    const expected = { proposal_id: "p2", status: "merged" as const, mode: "direct_commit" as const, action_id: "new.action", file_paths: ["dsl/new.yaml"] };
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.createAction(createBody);
    expect(result).toBe(expected);
  });

  it("passes options when provided", async () => {
    mockApiFetch.mockResolvedValueOnce({ proposal_id: "p3", status: "pending", mode: "pr", action_id: "a", file_paths: [] });
    const bodyWithOptions = { ...createBody, options: { require_review: true, git_mode: "pr" as const } };
    await dslApi.createAction(bodyWithOptions);
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/dsl/actions", {
      method: "POST",
      json: bodyWithOptions,
    });
  });
});

// ── dslApi.updateAction ────────────────────────────────────────────────────────

describe("dslApi.updateAction", () => {
  const updateBody = { action: { description: "Updated description" } };

  it("calls apiFetch with PATCH /api/v1/dsl/actions/{id}", async () => {
    mockApiFetch.mockResolvedValueOnce({ proposal_id: "p1", status: "pending", mode: "review", action_id: "click.element", file_paths: [] });
    await dslApi.updateAction("click.element", updateBody);
    expect(mockApiFetch).toHaveBeenCalledWith(
      `/api/v1/dsl/actions/${encodeURIComponent("click.element")}`,
      { method: "PATCH", json: updateBody },
    );
  });

  it("returns what apiFetch returns", async () => {
    const expected = { proposal_id: "p4", status: "merged" as const, mode: "direct_commit" as const, action_id: "click.element", file_paths: [] };
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.updateAction("click.element", updateBody);
    expect(result).toBe(expected);
  });

  it("URL-encodes the actionId", async () => {
    mockApiFetch.mockResolvedValueOnce({ proposal_id: "p5", status: "pending", mode: "review", action_id: "some/action", file_paths: [] });
    await dslApi.updateAction("some/action", updateBody);
    const [url] = mockApiFetch.mock.calls[0];
    expect(url).toBe(`/api/v1/dsl/actions/${encodeURIComponent("some/action")}`);
  });
});

// ── dslApi.deleteAction ────────────────────────────────────────────────────────

describe("dslApi.deleteAction", () => {
  it("calls apiFetch with DELETE /api/v1/dsl/actions/{id}", async () => {
    mockApiFetch.mockResolvedValueOnce({ proposal_id: "p1", status: "pending", mode: "review", action_id: "click.element", file_paths: [] });
    await dslApi.deleteAction("click.element");
    expect(mockApiFetch).toHaveBeenCalledWith(
      `/api/v1/dsl/actions/${encodeURIComponent("click.element")}`,
      { method: "DELETE", json: { options: {} } },
    );
  });

  it("returns what apiFetch returns", async () => {
    const expected = { proposal_id: "p6", status: "merged" as const, mode: "direct_commit" as const, action_id: "click.element", file_paths: [] };
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.deleteAction("click.element");
    expect(result).toBe(expected);
  });

  it("passes delete options when provided", async () => {
    mockApiFetch.mockResolvedValueOnce({ proposal_id: "p7", status: "pending", mode: "pr", action_id: "act", file_paths: [] });
    const opts = { require_review: true, git_mode: "pr" as const };
    await dslApi.deleteAction("act", opts);
    expect(mockApiFetch).toHaveBeenCalledWith(
      `/api/v1/dsl/actions/${encodeURIComponent("act")}`,
      { method: "DELETE", json: { options: opts } },
    );
  });
});

// ── dslApi.deprecateAction ─────────────────────────────────────────────────────

describe("dslApi.deprecateAction", () => {
  const deprecateBody = { replacement: "new.click.action", reason: "Renamed", since: "2025-01-01" };

  it("calls apiFetch with POST /api/v1/dsl/actions/{id}/deprecate", async () => {
    mockApiFetch.mockResolvedValueOnce({ proposal_id: "p1", status: "pending", mode: "review", action_id: "old.action", file_paths: [] });
    await dslApi.deprecateAction("old.action", deprecateBody);
    expect(mockApiFetch).toHaveBeenCalledWith(
      `/api/v1/dsl/actions/${encodeURIComponent("old.action")}/deprecate`,
      { method: "POST", json: deprecateBody },
    );
  });

  it("returns what apiFetch returns", async () => {
    const expected = { proposal_id: "p8", status: "merged" as const, mode: "direct_commit" as const, action_id: "old.action", file_paths: [] };
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.deprecateAction("old.action", deprecateBody);
    expect(result).toBe(expected);
  });

  it("URL-encodes the actionId", async () => {
    mockApiFetch.mockResolvedValueOnce({ proposal_id: "px", status: "pending", mode: "review", action_id: "a/b", file_paths: [] });
    await dslApi.deprecateAction("a/b", deprecateBody);
    const [url] = mockApiFetch.mock.calls[0];
    expect(url).toContain(encodeURIComponent("a/b"));
  });
});

// ── dslApi.listProposals ───────────────────────────────────────────────────────

describe("dslApi.listProposals", () => {
  it("calls apiFetch with GET /api/v1/dsl/proposals (no filters)", async () => {
    mockApiFetch.mockResolvedValueOnce({ items: [], total: 0 });
    await dslApi.listProposals();
    const [url] = mockApiFetch.mock.calls[0];
    expect(url).toBe("/api/v1/dsl/proposals");
  });

  it("appends status filter as query param", async () => {
    mockApiFetch.mockResolvedValueOnce({ items: [], total: 0 });
    await dslApi.listProposals({ status: "pending" });
    const [url] = mockApiFetch.mock.calls[0];
    expect(url).toContain("status=pending");
  });

  it("returns what apiFetch returns", async () => {
    const expected = { items: [{ id: "prop-1" }], total: 1 };
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.listProposals({ status: "approved" });
    expect(result).toBe(expected);
  });

  it("appends action_id and limit filters when provided", async () => {
    mockApiFetch.mockResolvedValueOnce({ items: [], total: 0 });
    await dslApi.listProposals({ action_id: "click.btn", limit: 25 });
    const [url] = mockApiFetch.mock.calls[0];
    expect(url).toContain("action_id=click.btn");
    expect(url).toContain("limit=25");
  });
});

// ── dslApi.getProposal ─────────────────────────────────────────────────────────

describe("dslApi.getProposal", () => {
  it("calls apiFetch with GET /api/v1/dsl/proposals/{id}", async () => {
    mockApiFetch.mockResolvedValueOnce({ id: "prop-1" });
    await dslApi.getProposal("prop-1");
    expect(mockApiFetch).toHaveBeenCalledWith(
      `/api/v1/dsl/proposals/${encodeURIComponent("prop-1")}`,
    );
  });

  it("returns what apiFetch returns", async () => {
    const expected = { id: "prop-99", action_id: "click.el" };
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.getProposal("prop-99");
    expect(result).toBe(expected);
  });

  it("URL-encodes the proposalId", async () => {
    mockApiFetch.mockResolvedValueOnce({});
    await dslApi.getProposal("prop/with/slashes");
    const [url] = mockApiFetch.mock.calls[0];
    expect(url).toBe(`/api/v1/dsl/proposals/${encodeURIComponent("prop/with/slashes")}`);
  });
});

// ── dslApi.approveProposal ─────────────────────────────────────────────────────

describe("dslApi.approveProposal", () => {
  it("calls apiFetch with POST /api/v1/dsl/proposals/{id}/approve", async () => {
    mockApiFetch.mockResolvedValueOnce({ proposal_id: "p1", status: "merged", mode: "direct_commit", action_id: "a", file_paths: [] });
    await dslApi.approveProposal("prop-1");
    expect(mockApiFetch).toHaveBeenCalledWith(
      `/api/v1/dsl/proposals/${encodeURIComponent("prop-1")}/approve`,
      { method: "POST", json: {} },
    );
  });

  it("returns what apiFetch returns", async () => {
    const expected = { proposal_id: "p1", status: "merged" as const, mode: "pr" as const, action_id: "act", file_paths: [] };
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.approveProposal("prop-1");
    expect(result).toBe(expected);
  });

  it("passes note and git_mode in body when provided", async () => {
    mockApiFetch.mockResolvedValueOnce({ proposal_id: "p2", status: "merged", mode: "pr", action_id: "act", file_paths: [] });
    await dslApi.approveProposal("prop-2", { note: "LGTM", git_mode: "pr" });
    expect(mockApiFetch).toHaveBeenCalledWith(
      `/api/v1/dsl/proposals/${encodeURIComponent("prop-2")}/approve`,
      { method: "POST", json: { note: "LGTM", git_mode: "pr" } },
    );
  });
});

// ── dslApi.rejectProposal ──────────────────────────────────────────────────────

describe("dslApi.rejectProposal", () => {
  it("calls apiFetch with POST /api/v1/dsl/proposals/{id}/reject", async () => {
    mockApiFetch.mockResolvedValueOnce({ id: "prop-1", status: "rejected" });
    await dslApi.rejectProposal("prop-1");
    expect(mockApiFetch).toHaveBeenCalledWith(
      `/api/v1/dsl/proposals/${encodeURIComponent("prop-1")}/reject`,
      { method: "POST", json: {} },
    );
  });

  it("returns what apiFetch returns", async () => {
    const expected = { id: "prop-2", status: "rejected" };
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.rejectProposal("prop-2");
    expect(result).toBe(expected);
  });

  it("passes note in body when provided", async () => {
    mockApiFetch.mockResolvedValueOnce({ id: "prop-3", status: "rejected" });
    await dslApi.rejectProposal("prop-3", { note: "Does not meet standards" });
    expect(mockApiFetch).toHaveBeenCalledWith(
      `/api/v1/dsl/proposals/${encodeURIComponent("prop-3")}/reject`,
      { method: "POST", json: { note: "Does not meet standards" } },
    );
  });
});

// ── dslApi.generateAiAliases ───────────────────────────────────────────────────

describe("dslApi.generateAiAliases", () => {
  it("calls apiFetch with POST /api/v1/dsl/actions/{id}/ai-aliases", async () => {
    mockApiFetch.mockResolvedValueOnce({ accepted: [], rejected: [], proposals: [] });
    await dslApi.generateAiAliases("click.element", { lang: "tr" });
    expect(mockApiFetch).toHaveBeenCalledWith(
      `/api/v1/dsl/actions/${encodeURIComponent("click.element")}/ai-aliases`,
      { method: "POST", json: { lang: "tr" } },
    );
  });

  it("returns what apiFetch returns", async () => {
    const expected = { accepted: ["tıkla", "bas"], rejected: ["vur"], proposals: ["dokun"] };
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.generateAiAliases("click.element", { lang: "tr" });
    expect(result).toBe(expected);
  });

  it("passes count in body when provided", async () => {
    mockApiFetch.mockResolvedValueOnce({ accepted: [], rejected: [], proposals: [] });
    await dslApi.generateAiAliases("click.element", { lang: "en", count: 5 });
    expect(mockApiFetch).toHaveBeenCalledWith(
      `/api/v1/dsl/actions/${encodeURIComponent("click.element")}/ai-aliases`,
      { method: "POST", json: { lang: "en", count: 5 } },
    );
  });
});

// ── dslApi.listAudit ───────────────────────────────────────────────────────────

describe("dslApi.listAudit", () => {
  it("calls apiFetch with GET /api/v1/dsl/audit (no params)", async () => {
    mockApiFetch.mockResolvedValueOnce([]);
    await dslApi.listAudit();
    const [url] = mockApiFetch.mock.calls[0];
    expect(url).toBe("/api/v1/dsl/audit");
  });

  it("appends action_id as query param when provided", async () => {
    mockApiFetch.mockResolvedValueOnce([]);
    await dslApi.listAudit({ action_id: "click.btn" });
    const [url] = mockApiFetch.mock.calls[0];
    expect(url).toContain("action_id=click.btn");
  });

  it("appends limit as query param when provided", async () => {
    mockApiFetch.mockResolvedValueOnce([]);
    await dslApi.listAudit({ limit: 50 });
    const [url] = mockApiFetch.mock.calls[0];
    expect(url).toContain("limit=50");
  });

  it("returns what apiFetch returns", async () => {
    const expected = [{ id: "audit-1", action_id: "click.el", operation: "update", created_at: "2025-01-01T00:00:00Z" }];
    mockApiFetch.mockResolvedValueOnce(expected);
    const result = await dslApi.listAudit({ action_id: "click.el" });
    expect(result).toBe(expected);
  });
});
