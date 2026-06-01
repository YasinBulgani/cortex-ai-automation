"use client";

import { useCallback, useEffect, useState } from "react";

export type KbArticle = {
  id: string;
  title: string;
  body: string;
  tags: string[];
  category: string;
  author_id: string;
  author_name: string;
  created_at: string;
  updated_at: string;
  view_count: number;
  helpful_count: number;
  unhelpful_count: number;
};

export type ListFilter = {
  category?: string;
  tag?: string;
  sort?: "newest" | "popular" | "helpful";
};

const STORAGE_KEY = "neurex_kb_articles_v1";
const KB_API_BASE = "/api/v1/kb";

// Backend-first with localStorage fallback.
// Now that /api/v1/kb router is registered (2026-05-24), initial load
// fetches from the backend and syncs to localStorage for offline use.
// Mutations still write to localStorage; backend sync is planned.

function loadFromStorage(): KbArticle[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveToStorage(items: KbArticle[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    /* quota / unavailable */
  }
}

async function fetchFromBackend(): Promise<KbArticle[] | null> {
  try {
    const res = await fetch(`${KB_API_BASE}/articles`, {
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) return null; // backend unavailable or auth required → use localStorage
    const data: KbArticle[] = await res.json();
    return Array.isArray(data) ? data : null;
  } catch {
    return null; // network error → graceful fallback
  }
}

function makeId(): string {
  return `a-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function nowIso(): string {
  return new Date().toISOString();
}

export function useKnowledgeBase() {
  const [articles, setArticles] = useState<KbArticle[]>([]);

  useEffect(() => {
    // Load from localStorage immediately for instant display
    const local = loadFromStorage();
    if (local.length > 0) setArticles(local);

    // Then try backend — if it responds, prefer its data (authoritative source)
    fetchFromBackend().then((backendData) => {
      if (backendData && backendData.length > 0) {
        setArticles(backendData);
        saveToStorage(backendData); // sync to localStorage for offline use
      } else if (local.length === 0) {
        setArticles([]); // both empty
      }
    });
  }, []);

  const persist = useCallback((next: KbArticle[]) => {
    setArticles(next);
    saveToStorage(next);
  }, []);

  const create = useCallback(
    (input: {
      title: string;
      body: string;
      tags?: string[];
      category?: string;
      author_id?: string;
      author_name?: string;
    }): KbArticle => {
      const article: KbArticle = {
        id: makeId(),
        title: input.title.trim(),
        body: input.body.trim(),
        tags: input.tags ?? [],
        category: input.category ?? "general",
        author_id: input.author_id ?? "you",
        author_name: input.author_name ?? "Sen",
        created_at: nowIso(),
        updated_at: nowIso(),
        view_count: 0,
        helpful_count: 0,
        unhelpful_count: 0,
      };
      const all = loadFromStorage();
      persist([article, ...all]);
      return article;
    },
    [persist],
  );

  const update = useCallback(
    (id: string, patch: Partial<Pick<KbArticle, "title" | "body" | "tags" | "category">>) => {
      const all = loadFromStorage();
      const next = all.map((a) =>
        a.id === id ? { ...a, ...patch, updated_at: nowIso() } : a,
      );
      persist(next);
      return next.find((a) => a.id === id) ?? null;
    },
    [persist],
  );

  const remove = useCallback(
    (id: string) => {
      const all = loadFromStorage();
      persist(all.filter((a) => a.id !== id));
    },
    [persist],
  );

  const incrementView = useCallback((id: string) => {
    const all = loadFromStorage();
    const next = all.map((a) =>
      a.id === id ? { ...a, view_count: a.view_count + 1 } : a,
    );
    persist(next);
  }, [persist]);

  const vote = useCallback((id: string, helpful: boolean) => {
    const all = loadFromStorage();
    const next = all.map((a) =>
      a.id === id
        ? {
            ...a,
            helpful_count: helpful ? a.helpful_count + 1 : a.helpful_count,
            unhelpful_count: helpful ? a.unhelpful_count : a.unhelpful_count + 1,
          }
        : a,
    );
    persist(next);
  }, [persist]);

  const list = useCallback(
    (filter: ListFilter = {}) => {
      let items = articles.slice();
      if (filter.category) items = items.filter((a) => a.category === filter.category);
      if (filter.tag) items = items.filter((a) => a.tags.includes(filter.tag!));
      switch (filter.sort) {
        case "popular":
          items.sort((a, b) => b.view_count - a.view_count);
          break;
        case "helpful":
          items.sort(
            (a, b) =>
              b.helpful_count - b.unhelpful_count - (a.helpful_count - a.unhelpful_count),
          );
          break;
        default:
          items.sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
      }
      return items;
    },
    [articles],
  );

  const search = useCallback(
    (query: string, limit = 20): KbArticle[] => {
      const q = query.trim().toLowerCase();
      if (!q) return [];
      const scored: { score: number; article: KbArticle }[] = [];
      for (const a of articles) {
        let score = 0;
        if (a.title.toLowerCase().includes(q)) score += 5;
        if (a.body.toLowerCase().includes(q)) score += 1;
        for (const t of a.tags) {
          if (t.toLowerCase() === q) score += 3;
          else if (t.toLowerCase().includes(q)) score += 1.5;
        }
        if (score > 0) scored.push({ score, article: a });
      }
      scored.sort((a, b) => b.score - a.score || b.article.view_count - a.article.view_count);
      return scored.slice(0, limit).map((s) => s.article);
    },
    [articles],
  );

  return { articles, create, update, remove, incrementView, vote, list, search };
}
