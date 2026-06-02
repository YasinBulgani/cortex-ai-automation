"use client";

/**
 * DslSearchBar
 *
 * Search and filter toolbar for the DSL Catalog page.
 * Contains:
 *   - Free-text search input
 *   - Language (alias lang) filter select
 *   - Active category badge with clear button
 *   - Total action count display
 *
 * Usage:
 *   <DslSearchBar
 *     searchTerm={searchTerm}
 *     onSearchChange={setSearchTerm}
 *     selectedLang={selectedLang}
 *     onLangChange={setSelectedLang}
 *     total={total}
 *     selectedCategory={selectedCategory}
 *     onClearCategory={() => setSelectedCategory("")}
 *   />
 */

import { Input } from "@/components/ui/input";
import type { DslLang } from "@/lib/dsl-api";

export interface DslSearchBarProps {
  searchTerm: string;
  onSearchChange: (value: string) => void;
  selectedLang: DslLang | "";
  onLangChange: (value: DslLang | "") => void;
  total: number;
  selectedCategory: string;
  onClearCategory: () => void;
}

export function DslSearchBar({
  searchTerm,
  onSearchChange,
  selectedLang,
  onLangChange,
  total,
  selectedCategory,
  onClearCategory,
}: DslSearchBarProps) {
  return (
    <div className="flex items-center gap-3 border-b border-slate-800 bg-slate-950/70 px-4 py-3">
      <Input
        placeholder="Cümlecik ara: tikla, click, should be visible…"
        value={searchTerm}
        onChange={(e) => onSearchChange(e.target.value)}
        className="max-w-md"
      />

      <select
        aria-label="Alias dili filtresi"
        value={selectedLang}
        onChange={(e) => onLangChange(e.target.value as DslLang | "")}
        className="h-10 rounded border border-slate-800 bg-slate-900 px-2 text-sm text-white"
      >
        <option value="">Tüm diller</option>
        <option value="tr">Türkçe</option>
        <option value="en">English</option>
      </select>

      {selectedCategory && (
        <button
          type="button"
          onClick={onClearCategory}
          className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700"
        >
          Kategori: {selectedCategory} ✕
        </button>
      )}

      <span className="ml-auto text-xs text-slate-400">
        {total.toLocaleString("tr-TR")} cümlecik
      </span>
    </div>
  );
}
