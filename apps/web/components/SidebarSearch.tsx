"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

type NavItem = {
  label: string;
  path: string;
  group?: string;
};

type Props = {
  items: NavItem[];
  projectBasePath?: string; // e.g. "/p/proj-1"
};

/**
 * Sidebar üstüne yerleştirilebilir search box.
 * Mevcut nav definitions üzerinden fuzzy filter yapar.
 */
export function SidebarSearch({ items, projectBasePath = "" }: Props) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const scored = items
      .map((item) => {
        const label = item.label.toLowerCase();
        const group = (item.group ?? "").toLowerCase();
        const path = item.path.toLowerCase();
        let score = 0;
        if (label.startsWith(q)) score = 10;
        else if (label.includes(q)) score = 5;
        else if (group.includes(q)) score = 2;
        else if (path.includes(q)) score = 1;
        return { item, score };
      })
      .filter((x) => x.score > 0);
    scored.sort((a, b) => b.score - a.score);
    return scored.map((x) => x.item).slice(0, 8);
  }, [query, items]);

  return (
    <div className="px-3 py-2" data-testid="sidebar-search">
      <div className="relative">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="🔍 Hızlı bul…"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
          data-testid="sidebar-search-input"
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery("")}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            aria-label="Temizle"
            data-testid="sidebar-search-clear"
          >
            ×
          </button>
        )}
      </div>

      {query.trim() && (
        <div className="mt-2" data-testid="sidebar-search-results">
          {filtered.length === 0 ? (
            <p className="px-2 py-3 text-center text-[10px] text-slate-500">
              Sonuç yok. Cmd+K ile genel arama dene.
            </p>
          ) : (
            <ul className="space-y-0.5">
              {filtered.map((item) => {
                const href = item.path.startsWith("/")
                  ? item.path
                  : projectBasePath
                    ? `${projectBasePath}/${item.path}`
                    : item.path;
                return (
                  <li key={`${item.group}-${item.path}`}>
                    <Link
                      href={href}
                      onClick={() => setQuery("")}
                      className="block rounded px-2 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
                      data-testid={`sidebar-search-result-${item.path}`}
                    >
                      <span className="font-medium">{item.label}</span>
                      {item.group && (
                        <span className="ml-2 text-[9px] text-slate-500">{item.group}</span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
