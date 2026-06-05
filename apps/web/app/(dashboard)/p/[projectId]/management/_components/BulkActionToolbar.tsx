"use client";

import { useState } from "react";

export interface BulkAction {
  id: string;
  label: string;
  icon: string;
  variant?: "default" | "danger";
}

interface BulkActionToolbarProps {
  selectedCount: number;
  actions: BulkAction[];
  onAction: (actionId: string, selectedIds: string[]) => void | Promise<void>;
  selectedIds: string[];
  onClearSelection: () => void;
}

export function BulkActionToolbar({
  selectedCount,
  actions,
  onAction,
  selectedIds,
  onClearSelection,
}: BulkActionToolbarProps) {
  const [loading, setLoading] = useState<string | null>(null);

  if (selectedCount === 0) return null;

  const handleAction = async (actionId: string) => {
    setLoading(actionId);
    try {
      await onAction(actionId, selectedIds);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 animate-in slide-in-from-bottom-4 duration-200">
      <div className="flex items-center gap-3 rounded-xl border border-border-strong bg-surface-overlay px-4 py-3 shadow-2xl shadow-black/50">
        {/* Seçim sayısı */}
        <div className="flex items-center gap-2 pr-3 border-r border-border">
          <div className="w-6 h-6 rounded-full bg-brand flex items-center justify-center text-xs font-bold text-white">
            {selectedCount}
          </div>
          <span className="text-sm text-slate-300 font-medium whitespace-nowrap">
            case seçildi
          </span>
        </div>

        {/* Aksiyonlar */}
        <div className="flex items-center gap-2">
          {actions.map((action) => (
            <button
              key={action.id}
              onClick={() => handleAction(action.id)}
              disabled={loading !== null}
              className={`
                flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition-colors disabled:opacity-50
                ${action.variant === "danger"
                  ? "bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/30"
                  : "bg-slate-700 hover:bg-slate-600 text-slate-200 border border-border-strong"}
              `}
            >
              {loading === action.id ? (
                <span className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
              ) : (
                <span>{action.icon}</span>
              )}
              {action.label}
            </button>
          ))}
        </div>

        {/* Temizle */}
        <button
          onClick={onClearSelection}
          className="ml-1 text-slate-500 hover:text-white text-sm transition-colors"
          title="Seçimi temizle"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

// ── Satır checkbox'ı ─────────────────────────────────────────────────────────

interface SelectCheckboxProps {
  id: string;
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
}

export function SelectCheckbox({ id, selectedIds, onToggle }: SelectCheckboxProps) {
  const checked = selectedIds.has(id);
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onToggle(id); }}
      className={`
        w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-all
        ${checked
          ? "bg-brand border-teal-600 text-white"
          : "border-border-strong hover:border-teal-500 bg-transparent"}
      `}
    >
      {checked && (
        <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 12 12" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M2 6l3 3 5-5" />
        </svg>
      )}
    </button>
  );
}

// ── Select All checkbox ──────────────────────────────────────────────────────

interface SelectAllCheckboxProps {
  totalIds: string[];
  selectedIds: Set<string>;
  onSelectAll: () => void;
  onClearAll: () => void;
}

export function SelectAllCheckbox({ totalIds, selectedIds, onSelectAll, onClearAll }: SelectAllCheckboxProps) {
  const allSelected = totalIds.length > 0 && totalIds.every((id) => selectedIds.has(id));
  const someSelected = totalIds.some((id) => selectedIds.has(id));

  return (
    <button
      onClick={allSelected || someSelected ? onClearAll : onSelectAll}
      className={`
        w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-all
        ${allSelected
          ? "bg-brand border-teal-600 text-white"
          : someSelected
          ? "bg-brand/50 border-teal-600 text-white"
          : "border-border-strong hover:border-teal-500 bg-transparent"}
      `}
      title={allSelected ? "Tümünü kaldır" : "Tümünü seç"}
    >
      {allSelected && (
        <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 12 12" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M2 6l3 3 5-5" />
        </svg>
      )}
      {someSelected && !allSelected && <span className="w-2 h-0.5 bg-white rounded" />}
    </button>
  );
}
