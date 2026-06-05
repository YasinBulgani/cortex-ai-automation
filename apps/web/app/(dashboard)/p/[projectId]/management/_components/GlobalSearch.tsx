"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  useSearchSimilarCases,
  useManagementDefects,
  useManagementRuns,
  useSharedSteps,
  type SimilarCaseResult,
  type DefectLink,
  type TestRun,
  type SharedStep,
} from "@/lib/hooks/use-management";

// ─── Types ────────────────────────────────────────────────────────────────────

type ResultCategory = "cases" | "runs" | "defects" | "shared-steps";

interface SearchResult {
  id: string;
  category: ResultCategory;
  title: string;
  meta: string;
  href: string;
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function IcCase() {
  return (
    <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
    </svg>
  );
}

function IcRun() {
  return (
    <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <circle cx="12" cy="12" r="9"/>
      <path strokeLinecap="round" strokeLinejoin="round" d="M10 8l6 4-6 4V8z"/>
    </svg>
  );
}

function IcBug() {
  return (
    <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M8 2a2 2 0 014 0M16 2a2 2 0 00-4 0M5 8h14M5 8a7 7 0 0014 0M5 8l-2-2m16 2 2-2M7 14H4m16 0h-3m-6 6v-6m0 6H8m4 0h4"/>
    </svg>
  );
}

function IcSteps() {
  return (
    <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
    </svg>
  );
}

function IcSearch() {
  return (
    <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <circle cx="11" cy="11" r="8"/>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35"/>
    </svg>
  );
}

function IcSpinner() {
  return (
    <svg className="h-4 w-4 shrink-0 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-6.219-8.56"/>
    </svg>
  );
}

// ─── Category config ──────────────────────────────────────────────────────────

const CATEGORY_CONFIG: Record<ResultCategory, { label: string; Icon: () => React.ReactElement; color: string }> = {
  cases: { label: "Test Case'leri", Icon: IcCase, color: "text-brand" },
  runs: { label: "Test Koşuları", Icon: IcRun, color: "text-purple-400" },
  defects: { label: "Defektler", Icon: IcBug, color: "text-danger" },
  "shared-steps": { label: "Paylaşılan Adımlar", Icon: IcSteps, color: "text-amber-400" },
};

const CATEGORY_ORDER: ResultCategory[] = ["cases", "runs", "defects", "shared-steps"];

// ─── Status badge ─────────────────────────────────────────────────────────────

function statusBadgeClass(status: string): string {
  switch (status) {
    case "passed":      return "bg-emerald-500/15 text-emerald-400";
    case "failed":      return "bg-danger-subtle text-danger";
    case "running":     return "bg-amber-500/15 text-amber-400";
    case "blocked":     return "bg-orange-500/15 text-orange-400";
    case "open":        return "bg-danger-subtle text-danger";
    case "closed":      return "bg-surface-overlay text-fg-subtle";
    default:            return "bg-surface-overlay text-fg-subtle";
  }
}

// ─── GlobalSearch component ───────────────────────────────────────────────────

interface GlobalSearchProps {
  projectId: string;
  mpid: string | null;
  onClose: () => void;
}

export function GlobalSearch({ projectId, mpid, onClose }: GlobalSearchProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  // ── Hooks ──────────────────────────────────────────────────────────────────
  const searchCases = useSearchSimilarCases(mpid ?? "");
  const { data: defects = [] } = useManagementDefects(mpid ?? undefined);
  const { data: runs = [] } = useManagementRuns(mpid ?? undefined);
  const { data: sharedSteps = [] } = useSharedSteps(mpid ?? undefined);

  // ── Debounce ───────────────────────────────────────────────────────────────
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(t);
  }, [query]);

  // ── Trigger AI case search on debounced query ──────────────────────────────
  useEffect(() => {
    if (debouncedQuery.trim().length >= 2 && mpid) {
      searchCases.mutate({ query: debouncedQuery.trim(), k: 8 });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery, mpid]);

  // ── Build results ──────────────────────────────────────────────────────────
  const results = useMemo<SearchResult[]>(() => {
    const q = debouncedQuery.toLowerCase();
    if (!q) return [];

    const out: SearchResult[] = [];

    // Cases — from AI search
    (searchCases.data ?? []).forEach((c: SimilarCaseResult) => {
      out.push({
        id: c.case_id,
        category: "cases",
        title: c.title,
        meta: c.case_key,
        href: `/p/${projectId}/management/cases/${c.case_id}`,
      });
    });

    // Runs — local filter
    runs
      .filter((r: TestRun) => r.name.toLowerCase().includes(q))
      .slice(0, 5)
      .forEach((r: TestRun) => {
        out.push({
          id: r.id,
          category: "runs",
          title: r.name,
          meta: r.status,
          href: `/p/${projectId}/management/runs`,
        });
      });

    // Defects — local filter
    defects
      .filter((d: DefectLink) => d.title.toLowerCase().includes(q) || d.external_key.toLowerCase().includes(q))
      .slice(0, 5)
      .forEach((d: DefectLink) => {
        out.push({
          id: d.id,
          category: "defects",
          title: d.title,
          meta: `${d.external_key} · ${d.severity}`,
          href: `/p/${projectId}/management/defects`,
        });
      });

    // Shared steps — local filter
    sharedSteps
      .filter((s: SharedStep) => s.name.toLowerCase().includes(q))
      .slice(0, 5)
      .forEach((s: SharedStep) => {
        out.push({
          id: s.id,
          category: "shared-steps",
          title: s.name,
          meta: `${s.usage_count} kullanım`,
          href: `/p/${projectId}/management/shared-steps`,
        });
      });

    return out;
  }, [debouncedQuery, searchCases.data, runs, defects, sharedSteps, projectId]);

  const isLoading = searchCases.isPending && debouncedQuery.length >= 2;

  // ── Grouped results ────────────────────────────────────────────────────────
  const grouped = useMemo(() => {
    const map = new Map<ResultCategory, SearchResult[]>();
    for (const cat of CATEGORY_ORDER) {
      const items = results.filter(r => r.category === cat);
      if (items.length) map.set(cat, items);
    }
    return map;
  }, [results]);

  // Flat list for keyboard nav
  const flat = useMemo(() => results, [results]);

  // ── Focus input on mount ───────────────────────────────────────────────────
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // ── Keyboard navigation ────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex(i => Math.min(i + 1, flat.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex(i => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        const item = flat[activeIndex];
        if (item) {
          router.push(item.href);
          onClose();
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [flat, activeIndex, router, onClose]);

  // Reset active index when results change
  useEffect(() => {
    setActiveIndex(0);
  }, [results]);

  // Scroll active item into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-index="${activeIndex}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  const handleItemClick = useCallback((href: string) => {
    router.push(href);
    onClose();
  }, [router, onClose]);

  // ── Flat index tracker ─────────────────────────────────────────────────────
  let flatIdx = 0;

  return (
    <div
      className="fixed inset-0 z-[300] flex items-start justify-center px-4 pt-[12vh] bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-[640px] rounded-2xl border border-border bg-surface-raised shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 border-b border-border px-4 py-3">
          <span className={cn("shrink-0", isLoading ? "text-brand" : "text-fg-subtle")}>
            {isLoading ? <IcSpinner /> : <IcSearch />}
          </span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Test case, koşu, defekt veya adım ara…"
            className="flex-1 bg-transparent text-[14px] text-fg placeholder:text-fg-subtle outline-none"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="shrink-0 text-fg-subtle hover:text-fg transition-colors"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          )}
          <kbd className="shrink-0 rounded border border-border bg-surface-overlay px-1.5 py-0.5 font-mono text-[10px] text-fg-disabled">
            Esc
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-[420px] overflow-y-auto">
          {!debouncedQuery ? (
            <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-fg-subtle">
              <IcSearch />
              <p className="text-[13px]">Aramak için yazmaya başlayın</p>
              <p className="text-[11px] text-fg-disabled">
                ↑↓ gezin &nbsp;·&nbsp; Enter seçin &nbsp;·&nbsp; Esc kapat
              </p>
            </div>
          ) : isLoading && results.length === 0 ? (
            <div className="flex items-center justify-center gap-2 py-10 text-fg-subtle">
              <IcSpinner />
              <span className="text-[13px]">Aranıyor…</span>
            </div>
          ) : results.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
              <svg className="h-8 w-8 text-fg-disabled" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"/>
              </svg>
              <p className="text-[13px] text-fg-subtle">
                <span className="font-medium text-fg">&ldquo;{debouncedQuery}&rdquo;</span> için sonuç bulunamadı
              </p>
            </div>
          ) : (
            <div className="py-2">
              {CATEGORY_ORDER.map(cat => {
                const items = grouped.get(cat);
                if (!items) return null;
                const { label, Icon, color } = CATEGORY_CONFIG[cat];
                return (
                  <div key={cat}>
                    {/* Category header */}
                    <div className="flex items-center gap-2 px-4 py-2">
                      <span className={color}><Icon /></span>
                      <span className="text-[9px] font-bold uppercase tracking-widest text-fg-subtle">{label}</span>
                      <span className="ml-auto rounded-full bg-surface-overlay px-1.5 py-0.5 text-[9px] text-fg-disabled">
                        {items.length}
                      </span>
                    </div>

                    {/* Items */}
                    {items.map(item => {
                      const thisIdx = flatIdx++;
                      const isActive = thisIdx === activeIndex;
                      return (
                        <button
                          key={item.id}
                          type="button"
                          data-index={thisIdx}
                          onClick={() => handleItemClick(item.href)}
                          onMouseEnter={() => setActiveIndex(thisIdx)}
                          className={cn(
                            "flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors",
                            isActive ? "bg-brand/10 text-fg" : "text-fg-muted hover:bg-surface-overlay"
                          )}
                        >
                          <span className={cn("shrink-0", isActive ? CATEGORY_CONFIG[item.category].color : "text-fg-subtle")}>
                            {(() => { const IC = CATEGORY_CONFIG[item.category].Icon; return <IC />; })()}
                          </span>
                          <span className="flex-1 min-w-0">
                            <span className="block truncate text-[13px] font-medium">{item.title}</span>
                            {item.meta && (
                              <span className={cn(
                                "inline-block mt-0.5 rounded px-1.5 py-0.5 text-[10px]",
                                statusBadgeClass(item.meta) === "bg-surface-overlay text-fg-subtle"
                                  ? "text-fg-subtle"
                                  : statusBadgeClass(item.meta)
                              )}>
                                {item.meta}
                              </span>
                            )}
                          </span>
                          {isActive && (
                            <kbd className="shrink-0 rounded border border-border bg-surface-overlay px-1.5 py-0.5 font-mono text-[9px] text-fg-disabled">
                              ↵
                            </kbd>
                          )}
                        </button>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-border bg-surface-overlay px-4 py-2">
          <div className="flex items-center gap-4 text-[10px] text-fg-disabled">
            <span><kbd className="rounded border border-border/50 px-1 py-0.5 font-mono text-[9px]">↑↓</kbd> Gezin</span>
            <span><kbd className="rounded border border-border/50 px-1 py-0.5 font-mono text-[9px]">↵</kbd> Git</span>
            <span><kbd className="rounded border border-border/50 px-1 py-0.5 font-mono text-[9px]">Esc</kbd> Kapat</span>
            {results.length > 0 && (
              <span className="ml-auto">{results.length} sonuç</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
