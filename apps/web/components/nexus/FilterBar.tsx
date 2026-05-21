"use client";
import React from "react";

interface FilterOption {
  label: string;
  value: string;
}

interface FilterBarProps {
  search?: string;
  onSearch?: (v: string) => void;
  searchPlaceholder?: string;
  filters?: {
    key: string;
    label: string;
    value: string;
    options: FilterOption[];
    onChange: (v: string) => void;
  }[];
  right?: React.ReactNode;
}

export function FilterBar({ search, onSearch, searchPlaceholder = "Ara...", filters = [], right }: FilterBarProps) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {onSearch !== undefined && (
        <div className="relative flex-1 min-w-48">
          <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search ?? ""}
            onChange={e => onSearch(e.target.value)}
            placeholder={searchPlaceholder}
            data-testid="search-input"
            className="w-full pl-8 pr-3 py-1.5 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-slate-500 transition-colors"
          />
        </div>
      )}

      {filters.map(f => (
        <select
          key={f.key}
          value={f.value}
          onChange={e => f.onChange(e.target.value)}
          className="px-3 py-1.5 text-sm bg-slate-800 border border-slate-700 rounded-lg text-slate-300 focus:outline-none focus:border-slate-500 transition-colors cursor-pointer"
        >
          <option value="">{f.label}</option>
          {f.options.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      ))}

      {right && <div className="ml-auto flex items-center gap-2">{right}</div>}
    </div>
  );
}
