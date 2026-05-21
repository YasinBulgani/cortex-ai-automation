"use client";

import { useEffect, useState } from "react";

import {
  type Shortcut,
  displayCombo,
  useKeyboardShortcuts,
} from "@/lib/useKeyboardShortcuts";

/**
 * Global help modal — opens with ? key.
 */
export function KeyboardShortcutsHelp({
  shortcuts,
}: {
  shortcuts: Shortcut[];
}) {
  const [open, setOpen] = useState(false);

  // ? key (shift+/) opens help
  useKeyboardShortcuts([
    {
      combo: "shift+/",
      description: "Klavye kısayolları yardımı",
      handler: () => setOpen((v) => !v),
    },
    {
      combo: "escape",
      description: "Açık modal'ı kapat",
      handler: () => setOpen(false),
    },
  ]);

  if (!open) return null;

  // Group by section (split by "—")
  const grouped: Record<string, Shortcut[]> = {};
  for (const s of shortcuts) {
    const [section, label] = s.description.split("—").map((p) => p.trim());
    const sec = label ? section : "Genel";
    grouped[sec] = grouped[sec] ?? [];
    grouped[sec].push({ ...s, description: label || section });
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4"
      onClick={() => setOpen(false)}
      data-testid="keyboard-help-overlay"
    >
      <div
        className="max-h-[80vh] w-full max-w-2xl overflow-auto rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        data-testid="keyboard-help-panel"
      >
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h2 className="text-lg font-bold">Klavye Kısayolları</h2>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="text-slate-500 hover:text-white"
            data-testid="keyboard-help-close"
          >
            ×
          </button>
        </div>
        <div className="mt-4 space-y-6">
          {Object.entries(grouped).map(([section, items]) => (
            <div key={section}>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                {section}
              </h3>
              <div className="space-y-1.5">
                {items.map((s, i) => (
                  <div
                    key={`${section}-${i}`}
                    className="flex items-center justify-between text-sm"
                    data-testid={`keyboard-help-item-${i}`}
                  >
                    <span className="text-slate-300">{s.description}</span>
                    <kbd className="rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-xs font-mono">
                      {displayCombo(s.combo)}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
