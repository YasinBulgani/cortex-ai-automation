/** @jest-environment jsdom */
/**
 * M-50 Threaded Comments frontend tests.
 *
 * Covers:
 *  - `buildCommentTree` pure helper (no React)
 *  - `<CommentThread>` empty state, list render, reply-form toggle,
 *    emoji reaction mutation, soft-deleted tombstone, mention highlight.
 *
 * Network is fully mocked via `jest.mock("@/lib/api-client", ...)`.
 */
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

const apiFetchMock = jest.fn();
jest.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

import {
  CommentThread,
} from "@/app/(dashboard)/p/[projectId]/management/_components/CommentThread";
import {
  buildCommentTree,
  type MgmtComment,
} from "@/lib/hooks/use-mgmt-comments";

const TENANT = "00000000-0000-0000-0000-000000000001";
const PROJECT_ID = "11111111-1111-1111-1111-111111111111";
const CASE_ID = "22222222-2222-2222-2222-222222222222";
const ALICE = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const BOB = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";

function makeComment(over: Partial<MgmtComment> = {}): MgmtComment {
  return {
    id: over.id ?? "c-1",
    tenant_id: TENANT,
    project_id: PROJECT_ID,
    entity_type: "case",
    entity_id: CASE_ID,
    author_id: ALICE,
    parent_id: null,
    body_md: "hello",
    mentions: [],
    reactions: {},
    edited_at: null,
    deleted_at: null,
    created_at: "2026-05-27T10:00:00Z",
    ...over,
  };
}

function withQc(children: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  apiFetchMock.mockReset();
});

describe("buildCommentTree", () => {
  it("returns empty array for empty input", () => {
    expect(buildCommentTree([])).toEqual([]);
  });

  it("groups parent -> children", () => {
    const a = makeComment({ id: "a" });
    const b = makeComment({ id: "b", parent_id: "a" });
    const c = makeComment({ id: "c", parent_id: "a" });
    const tree = buildCommentTree([a, b, c]);
    expect(tree).toHaveLength(1);
    expect(tree[0].id).toBe("a");
    expect(tree[0].children.map((n) => n.id).sort()).toEqual(["b", "c"]);
  });

  it("orphan children (missing parent) treated as roots", () => {
    const orphan = makeComment({ id: "x", parent_id: "missing" });
    const tree = buildCommentTree([orphan]);
    expect(tree).toHaveLength(1);
    expect(tree[0].id).toBe("x");
  });

  it("preserves chronological order at each level", () => {
    const a = makeComment({ id: "a", created_at: "2026-05-01T00:00:00Z" });
    const r1 = makeComment({ id: "r1", parent_id: "a", created_at: "2026-05-02" });
    const r2 = makeComment({ id: "r2", parent_id: "a", created_at: "2026-05-03" });
    const tree = buildCommentTree([a, r1, r2]);
    expect(tree[0].children.map((n) => n.id)).toEqual(["r1", "r2"]);
  });
});

describe("<CommentThread>", () => {
  it("renders empty state when API returns []", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    await act(async () => {
      render(
        withQc(
          <CommentThread entityType="case" entityId={CASE_ID} projectId={PROJECT_ID} />,
        ),
      );
    });
    await waitFor(() => expect(screen.getByText(/No comments yet/i)).toBeInTheDocument());
  });

  it("renders list of comments with author/body", async () => {
    apiFetchMock.mockResolvedValueOnce([
      makeComment({ id: "c1", body_md: "first comment", author_id: ALICE }),
      makeComment({ id: "c2", body_md: "second comment", author_id: BOB }),
    ]);
    await act(async () => {
      render(
        withQc(
          <CommentThread
            entityType="case"
            entityId={CASE_ID}
            projectId={PROJECT_ID}
            currentUserId={ALICE}
            userDirectory={{ [ALICE]: "Alice", [BOB]: "Bob" }}
          />,
        ),
      );
    });
    await waitFor(() => expect(screen.getByText("first comment")).toBeInTheDocument());
    expect(screen.getByText("second comment")).toBeInTheDocument();
    expect(screen.getAllByText("Alice").length).toBeGreaterThan(0);
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText(/2 comment\(s\)/)).toBeInTheDocument();
  });

  it("clicking Reply opens a reply textarea", async () => {
    apiFetchMock.mockResolvedValueOnce([makeComment({ id: "c1", body_md: "root" })]);
    await act(async () => {
      render(
        withQc(<CommentThread entityType="case" entityId={CASE_ID} currentUserId={BOB} />),
      );
    });
    await waitFor(() => expect(screen.getByText("root")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /^Reply$/ }));
    expect(screen.getByPlaceholderText(/Write a reply/i)).toBeInTheDocument();
  });

  it("clicking an emoji button fires the react mutation", async () => {
    apiFetchMock.mockResolvedValueOnce([
      makeComment({ id: "c1", body_md: "react me" }),
    ]);
    // 2nd call (the mutation)
    apiFetchMock.mockResolvedValueOnce(makeComment({ id: "c1", reactions: { "+1": [BOB] } }));

    await act(async () => {
      render(
        withQc(<CommentThread entityType="case" entityId={CASE_ID} currentUserId={BOB} />),
      );
    });
    await waitFor(() => expect(screen.getByText("react me")).toBeInTheDocument());

    const plusOne = screen.getByRole("button", { name: /React with \+1/i });
    await act(async () => {
      fireEvent.click(plusOne);
    });

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/api/v1/test-management/comments/c1/react",
        expect.objectContaining({
          method: "POST",
          json: expect.objectContaining({ emoji: "+1", add: true }),
        }),
      );
    });
  });

  it("soft-deleted comment shows tombstone label", async () => {
    apiFetchMock.mockResolvedValueOnce([
      makeComment({
        id: "c1",
        body_md: "",
        deleted_at: "2026-05-27T12:00:00Z",
      }),
    ]);
    await act(async () => {
      render(
        withQc(<CommentThread entityType="case" entityId={CASE_ID} currentUserId={BOB} />),
      );
    });
    await waitFor(() => expect(screen.getByText(/comment removed/i)).toBeInTheDocument());
    // No reply button on a deleted node
    expect(screen.queryByRole("button", { name: /^Reply$/ })).toBeNull();
  });

  it("highlights @uuid mention with directory label", async () => {
    apiFetchMock.mockResolvedValueOnce([
      makeComment({ id: "c1", body_md: `cc @${BOB} please`, author_id: ALICE }),
    ]);
    await act(async () => {
      render(
        withQc(
          <CommentThread
            entityType="case"
            entityId={CASE_ID}
            currentUserId={ALICE}
            userDirectory={{ [BOB]: "Bob" }}
          />,
        ),
      );
    });
    // The literal mention should become a "@Bob" highlighted span
    await waitFor(() => expect(screen.getByText(/@Bob/)).toBeInTheDocument());
  });
});

describe("AI summary panel", () => {
  it("clicking AI özet button calls /comments/summarize and renders the response", async () => {
    const summaryResponse = {
      entity_type: "case",
      entity_id: CASE_ID,
      tldr: "Short summary of discussion",
      decisions: ["Use Playwright for E2E"],
      openQuestions: ["Who owns the rollout?"],
      comment_count: 2,
      source: "llm",
      generated_at: "2026-05-28T10:00:00Z",
    };

    apiFetchMock.mockImplementation((url: string, init?: any) => {
      if (typeof url !== "string") return Promise.resolve(null);
      if (url.includes("/comments/summarize") && init?.method === "POST") {
        return Promise.resolve(summaryResponse);
      }
      if (url.includes("/test-management/comments")) {
        return Promise.resolve([
          makeComment({ id: "c-1", body_md: "first" }),
          makeComment({ id: "c-2", body_md: "second" }),
        ]);
      }
      return Promise.resolve(null);
    });

    await act(async () => {
      render(
        withQc(
          <CommentThread
            entityType="case"
            entityId={CASE_ID}
            currentUserId={ALICE}
          />,
        ),
      );
    });

    const trigger = await screen.findByRole("button", { name: /AI özet/i });
    await act(async () => {
      fireEvent.click(trigger);
    });

    await waitFor(() => {
      const summarizeCalls = apiFetchMock.mock.calls.filter(
        (c) => typeof c[0] === "string" && c[0].includes("/comments/summarize"),
      );
      expect(summarizeCalls.length).toBeGreaterThan(0);
    });

    await waitFor(() => {
      expect(screen.getByText(/Short summary of discussion/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Use Playwright for E2E/)).toBeInTheDocument();
    expect(screen.getByText(/Who owns the rollout\?/)).toBeInTheDocument();
  });
});
