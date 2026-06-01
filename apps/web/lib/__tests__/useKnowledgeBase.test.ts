/**
 * useKnowledgeBase hook — 13 unit tests
 *
 * Tests cover:
 *   - initial state
 *   - localStorage load on mount
 *   - backend fetch on mount
 *   - backend preference over localStorage
 *   - network-error fallback to localStorage
 *   - non-ok response fallback to localStorage
 *   - localStorage sync after backend success
 *   - create(), update(), remove(), list(), search(), vote()
 *
 * No real fetch or localStorage is used — both are mocked.
 */

import { renderHook, act, waitFor } from "@testing-library/react";
import { useKnowledgeBase, KbArticle } from "../useKnowledgeBase";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

global.fetch = jest.fn();

const mockFetch = global.fetch as jest.Mock;

// Minimal localStorage mock backed by a plain object
const localStorageData: Record<string, string> = {};
const localStorageMock = {
  getItem: jest.fn((key: string) => localStorageData[key] ?? null),
  setItem: jest.fn((key: string, value: string) => {
    localStorageData[key] = value;
  }),
  removeItem: jest.fn((key: string) => {
    delete localStorageData[key];
  }),
  clear: jest.fn(() => {
    Object.keys(localStorageData).forEach((k) => delete localStorageData[k]);
  }),
};
Object.defineProperty(global, "localStorage", {
  value: localStorageMock,
  writable: true,
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STORAGE_KEY = "neurex_kb_articles_v1";

function makeArticle(overrides: Partial<KbArticle> = {}): KbArticle {
  return {
    id: "a-test-1",
    title: "Test Article",
    body: "Body text",
    tags: ["tag1"],
    category: "general",
    author_id: "u1",
    author_name: "Tester",
    created_at: "2026-01-01T00:00:00.000Z",
    updated_at: "2026-01-01T00:00:00.000Z",
    view_count: 0,
    helpful_count: 0,
    unhelpful_count: 0,
    ...overrides,
  };
}

function seedLocalStorage(articles: KbArticle[]) {
  localStorageData[STORAGE_KEY] = JSON.stringify(articles);
}

function mockBackendSuccess(articles: KbArticle[]) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => articles,
  } as Response);
}

function mockBackendNetworkError() {
  mockFetch.mockRejectedValueOnce(new Error("network error"));
}

function mockBackendNonOk() {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    json: async () => ({ detail: "Unauthorized" }),
  } as Response);
}

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorageMock.clear();
  mockFetch.mockClear();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useKnowledgeBase", () => {
  // ── 1. Initial state ──────────────────────────────────────────────────────
  it("initializes with an empty articles array when storage and backend are both empty", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    } as Response);

    const { result } = renderHook(() => useKnowledgeBase());

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    expect(result.current.articles).toEqual([]);
  });

  // ── 2. localStorage load on mount ─────────────────────────────────────────
  it("loads articles from localStorage immediately on mount before backend responds", async () => {
    const stored = [makeArticle({ id: "local-1", title: "Stored Article" })];
    seedLocalStorage(stored);

    // Backend responds after a delay — simulate by never resolving in this test
    let resolveBackend!: (v: unknown) => void;
    mockFetch.mockReturnValueOnce(
      new Promise((res) => {
        resolveBackend = res;
      }),
    );

    const { result } = renderHook(() => useKnowledgeBase());

    // Immediately after mount (before backend), localStorage articles should be visible
    expect(result.current.articles).toHaveLength(1);
    expect(result.current.articles[0].title).toBe("Stored Article");

    // Cleanup — resolve the pending fetch
    resolveBackend({ ok: true, json: async () => [] });
  });

  // ── 3. Backend fetch on mount ─────────────────────────────────────────────
  it("calls fetch('/api/v1/kb/articles') on mount", async () => {
    mockBackendSuccess([]);

    renderHook(() => useKnowledgeBase());

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/kb/articles",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  // ── 4. Backend data preferred over localStorage ───────────────────────────
  it("replaces localStorage articles with backend data when backend succeeds", async () => {
    seedLocalStorage([makeArticle({ id: "local-1", title: "Local" })]);
    const backendArticles = [makeArticle({ id: "backend-1", title: "Backend" })];
    mockBackendSuccess(backendArticles);

    const { result } = renderHook(() => useKnowledgeBase());

    await waitFor(() => {
      expect(result.current.articles.some((a) => a.id === "backend-1")).toBe(true);
    });

    expect(result.current.articles.some((a) => a.id === "local-1")).toBe(false);
  });

  // ── 5. Network-error fallback to localStorage ─────────────────────────────
  it("falls back to localStorage articles when backend throws a network error", async () => {
    const stored = [makeArticle({ id: "local-1", title: "Offline Article" })];
    seedLocalStorage(stored);
    mockBackendNetworkError();

    const { result } = renderHook(() => useKnowledgeBase());

    await waitFor(() => {
      // fetch was called and rejected — articles still from localStorage
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    expect(result.current.articles).toHaveLength(1);
    expect(result.current.articles[0].title).toBe("Offline Article");
  });

  // ── 6. Non-ok response fallback ───────────────────────────────────────────
  it("falls back to localStorage articles when backend returns a non-ok response", async () => {
    const stored = [makeArticle({ id: "local-2", title: "Auth Fallback" })];
    seedLocalStorage(stored);
    mockBackendNonOk();

    const { result } = renderHook(() => useKnowledgeBase());

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    expect(result.current.articles.some((a) => a.id === "local-2")).toBe(true);
  });

  // ── 7. Backend data saved to localStorage ────────────────────────────────
  it("saves backend data to localStorage when backend succeeds", async () => {
    const backendArticles = [makeArticle({ id: "b1", title: "From Backend" })];
    mockBackendSuccess(backendArticles);

    renderHook(() => useKnowledgeBase());

    await waitFor(() => {
      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    const savedRaw = localStorageData[STORAGE_KEY];
    expect(savedRaw).toBeDefined();
    const saved: KbArticle[] = JSON.parse(savedRaw);
    expect(saved.some((a) => a.id === "b1")).toBe(true);
  });

  // ── 8. create() adds article ──────────────────────────────────────────────
  it("create() adds a new article to the articles list", async () => {
    mockBackendSuccess([]);

    const { result } = renderHook(() => useKnowledgeBase());
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    act(() => {
      result.current.create({ title: "New Article", body: "New body", category: "faq" });
    });

    expect(result.current.articles).toHaveLength(1);
    expect(result.current.articles[0].title).toBe("New Article");
    expect(result.current.articles[0].category).toBe("faq");
  });

  // ── 9. update() modifies existing article ─────────────────────────────────
  it("update() modifies an existing article's fields", async () => {
    const article = makeArticle({ id: "u1", title: "Original" });
    seedLocalStorage([article]);
    mockBackendSuccess([article]);

    const { result } = renderHook(() => useKnowledgeBase());
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    act(() => {
      result.current.update("u1", { title: "Updated Title" });
    });

    const updated = result.current.articles.find((a) => a.id === "u1");
    expect(updated?.title).toBe("Updated Title");
  });

  // ── 10. remove() deletes article ─────────────────────────────────────────
  it("remove() deletes the article with the given id", async () => {
    const a1 = makeArticle({ id: "r1", title: "To Remove" });
    const a2 = makeArticle({ id: "r2", title: "Keep" });
    seedLocalStorage([a1, a2]);
    mockBackendSuccess([a1, a2]);

    const { result } = renderHook(() => useKnowledgeBase());
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    act(() => {
      result.current.remove("r1");
    });

    expect(result.current.articles.some((a) => a.id === "r1")).toBe(false);
    expect(result.current.articles.some((a) => a.id === "r2")).toBe(true);
  });

  // ── 11. list() filters by category ───────────────────────────────────────
  it("list() returns only articles matching the requested category", async () => {
    const faq = makeArticle({ id: "f1", category: "faq" });
    const guide = makeArticle({ id: "g1", category: "guide" });
    mockBackendSuccess([faq, guide]);

    const { result } = renderHook(() => useKnowledgeBase());
    await waitFor(() => {
      expect(result.current.articles).toHaveLength(2);
    });

    const faqOnly = result.current.list({ category: "faq" });
    expect(faqOnly).toHaveLength(1);
    expect(faqOnly[0].id).toBe("f1");
  });

  // ── 12. search() finds articles by query ─────────────────────────────────
  it("search() returns articles whose title contains the query string", async () => {
    const a1 = makeArticle({ id: "s1", title: "Login testing guide" });
    const a2 = makeArticle({ id: "s2", title: "Payment flow scenarios" });
    mockBackendSuccess([a1, a2]);

    const { result } = renderHook(() => useKnowledgeBase());
    await waitFor(() => {
      expect(result.current.articles).toHaveLength(2);
    });

    const results = result.current.search("login");
    expect(results).toHaveLength(1);
    expect(results[0].id).toBe("s1");
  });

  // ── 13. vote() increments helpful_count ──────────────────────────────────
  it("vote(id, true) increments helpful_count by 1", async () => {
    const article = makeArticle({ id: "v1", helpful_count: 3, unhelpful_count: 1 });
    seedLocalStorage([article]);
    mockBackendSuccess([article]);

    const { result } = renderHook(() => useKnowledgeBase());
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    act(() => {
      result.current.vote("v1", true);
    });

    const voted = result.current.articles.find((a) => a.id === "v1");
    expect(voted?.helpful_count).toBe(4);
    expect(voted?.unhelpful_count).toBe(1); // unchanged
  });
});
