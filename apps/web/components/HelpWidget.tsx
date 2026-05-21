"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useKnowledgeBase, type KbArticle } from "@/lib/useKnowledgeBase";

/**
 * Floating help widget — sağ alt köşe.
 *
 * Özellikler:
 *  - KB hızlı arama
 *  - Sayfa-spesifik öneri (path ↔ topic mapping)
 *  - Kısayollar listesi
 *  - "Sorum var" → support form (placeholder)
 *  - Cmd+K command palette hatırlatması
 */

// Sayfa path → KB topic mapping
const PATH_TO_TOPICS: Array<{ pattern: RegExp; topics: string[] }> = [
  { pattern: /\/scenarios\/new/, topics: ["İlk senaryomu nasıl yazarım?"] },
  { pattern: /\/sifir-bilgi/, topics: ["İlk senaryomu nasıl yazarım?", "Türkçe BDD"] },
  { pattern: /\/executions\/\w+/, topics: ["Test koştu, fail oldu"] },
  { pattern: /\/flaky/, topics: ["Flaky test nasıl tespit edilir?"] },
  { pattern: /\/cicd/, topics: ["CI/CD'ye nasıl entegre"] },
  { pattern: /\/privacy/, topics: ["KVKK uyum"] },
  { pattern: /\/healing/, topics: ["Test koştu, fail oldu"] },
];

function suggestArticlesForPath(pathname: string, articles: KbArticle[]): KbArticle[] {
  const topics = new Set<string>();
  for (const { pattern, topics: keywords } of PATH_TO_TOPICS) {
    if (pattern.test(pathname)) keywords.forEach((k) => topics.add(k));
  }
  if (topics.size === 0) return [];
  return articles.filter((a) =>
    Array.from(topics).some((kw) => a.title.toLowerCase().includes(kw.toLowerCase())),
  );
}

export function HelpWidget() {
  const pathname = usePathname() ?? "";
  const { articles, search } = useKnowledgeBase();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [view, setView] = useState<"home" | "search">("home");

  // Don't show on auth pages
  if (pathname.startsWith("/login") || pathname.startsWith("/reset-password") || pathname === "/offline") {
    return null;
  }

  const results = query.trim() ? search(query) : [];
  const suggestions = suggestArticlesForPath(pathname, articles);

  return (
    <>
      {/* Floating button */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-4 right-4 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600 text-white shadow-2xl hover:bg-indigo-500 transition-transform hover:scale-110"
        aria-label="Yardım"
        data-testid="help-widget-toggle"
      >
        {open ? (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
            <path d="M6 6l12 12M6 18L18 6" />
          </svg>
        ) : (
          <span className="text-lg font-bold">?</span>
        )}
      </button>

      {/* Panel */}
      {open && (
        <div
          className="fixed bottom-20 right-4 z-40 w-96 max-w-[calc(100vw-2rem)] rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl"
          data-testid="help-widget-panel"
        >
          <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
            <h3 className="text-sm font-semibold text-white">Yardım Merkezi</h3>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="text-slate-500 hover:text-white"
              aria-label="Kapat"
            >
              ×
            </button>
          </div>

          <div className="border-b border-slate-800 p-3">
            <input
              type="search"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setView(e.target.value.trim() ? "search" : "home");
              }}
              placeholder="🔍 Sorunu yaz (örn: 'flaky test', 'CI')"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              data-testid="help-widget-search"
            />
          </div>

          <div className="max-h-96 overflow-auto p-2">
            {view === "search" ? (
              <>
                {results.length === 0 ? (
                  <p
                    className="px-3 py-6 text-center text-xs text-slate-500"
                    data-testid="help-widget-no-results"
                  >
                    "{query}" için sonuç yok. <Link href="/kb" className="text-indigo-400 underline">Tüm KB'yi gör</Link>
                  </p>
                ) : (
                  <ul className="space-y-1" data-testid="help-widget-results">
                    {results.map((a) => (
                      <li key={a.id}>
                        <Link
                          href={`/kb/${a.id}`}
                          className="block rounded px-3 py-2 text-xs text-slate-300 hover:bg-slate-800"
                          onClick={() => setOpen(false)}
                        >
                          <p className="font-medium text-white">{a.title}</p>
                          <p className="mt-0.5 line-clamp-1 text-[10px] text-slate-500">
                            {a.body.replace(/[#*`]/g, "").slice(0, 80)}
                          </p>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            ) : (
              <>
                {suggestions.length > 0 && (
                  <div className="mb-3">
                    <p className="px-3 pt-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Bu sayfa için
                    </p>
                    <ul className="space-y-1" data-testid="help-widget-suggestions">
                      {suggestions.slice(0, 3).map((a) => (
                        <li key={a.id}>
                          <Link
                            href={`/kb/${a.id}`}
                            className="block rounded px-3 py-2 text-xs text-slate-300 hover:bg-slate-800"
                            onClick={() => setOpen(false)}
                          >
                            📄 {a.title}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div>
                  <p className="px-3 pt-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Hızlı bağlantılar
                  </p>
                  <ul className="space-y-1">
                    <li>
                      <Link
                        href="/kb"
                        className="block rounded px-3 py-2 text-xs text-slate-300 hover:bg-slate-800"
                        onClick={() => setOpen(false)}
                      >
                        📚 Tüm Knowledge Base
                      </Link>
                    </li>
                    <li>
                      <Link
                        href="/status"
                        className="block rounded px-3 py-2 text-xs text-slate-300 hover:bg-slate-800"
                        onClick={() => setOpen(false)}
                      >
                        🟢 Sistem durumu
                      </Link>
                    </li>
                    <li>
                      <a
                        href="https://github.com/YasinBulgani/BGTS-Test-Donusum/issues/new"
                        target="_blank"
                        rel="noreferrer"
                        className="block rounded px-3 py-2 text-xs text-slate-300 hover:bg-slate-800"
                      >
                        🐛 Hata bildir / Özellik öner
                      </a>
                    </li>
                  </ul>
                </div>

                <div className="mt-3 border-t border-slate-800 pt-2">
                  <p className="px-3 pt-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Kısayollar
                  </p>
                  <ul className="px-3 py-1 text-[11px] text-slate-400 space-y-1">
                    <li className="flex justify-between">
                      <span>Komut paleti</span>
                      <kbd className="rounded bg-slate-800 px-1.5 font-mono">Cmd+K</kbd>
                    </li>
                    <li className="flex justify-between">
                      <span>AI asistan</span>
                      <kbd className="rounded bg-slate-800 px-1.5 font-mono">Cmd+J</kbd>
                    </li>
                    <li className="flex justify-between">
                      <span>Yardım modal</span>
                      <kbd className="rounded bg-slate-800 px-1.5 font-mono">?</kbd>
                    </li>
                  </ul>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
