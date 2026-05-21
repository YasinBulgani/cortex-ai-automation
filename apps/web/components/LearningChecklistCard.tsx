"use client";

import Link from "next/link";
import { useState } from "react";

import { useLearningChecklist } from "@/lib/useLearningChecklist";

/**
 * Welcome dashboard'a yerleştirilecek learning checklist kartı.
 *
 * Özellikler:
 *  - Progress ring (%)
 *  - Required vs optional ayrımı
 *  - Mark complete (manuel + auto-detect future)
 *  - Dismiss (kapat ama tekrar göster opsiyonu)
 */
export function LearningChecklistCard() {
  const {
    items,
    completed,
    dismissed,
    markComplete,
    markIncomplete,
    dismiss,
    totalCompleted,
    totalItems,
    progressPct,
    requiredCompletedAll,
  } = useLearningChecklist();

  const [showAll, setShowAll] = useState(false);

  if (dismissed) {
    return null;
  }

  const visible = showAll ? items : items.slice(0, 5);
  const isComplete = totalCompleted === totalItems;

  return (
    <div
      className="rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-5"
      data-testid="learning-checklist-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-white">
            {isComplete ? "🎉 Tamamlandı!" : "🚀 Başlangıç rehberi"}
          </h3>
          <p className="mt-1 text-xs text-slate-400">
            {isComplete
              ? "Tüm temel adımları bitirdin. Şimdi gerçek işine başlayabilirsin."
              : "Test otomasyonu deneyiminden tam yararlanmak için bu adımları takip et."}
          </p>
        </div>
        <button
          type="button"
          onClick={dismiss}
          className="rounded-md p-1 text-slate-500 hover:text-slate-300"
          aria-label="Checklist'i kapat"
          data-testid="learning-checklist-dismiss"
        >
          ×
        </button>
      </div>

      <div className="mt-4">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span data-testid="learning-checklist-progress-label">
            {totalCompleted} / {totalItems} tamamlandı
          </span>
          <span data-testid="learning-checklist-progress-pct">{progressPct}%</span>
        </div>
        <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      <ul className="mt-4 space-y-2" data-testid="learning-checklist-items">
        {visible.map((item) => {
          const done = completed.has(item.id);
          return (
            <li
              key={item.id}
              className={`flex items-start gap-3 rounded-lg border p-3 transition-colors ${
                done
                  ? "border-emerald-500/20 bg-emerald-500/5"
                  : "border-slate-800 bg-slate-900/40 hover:bg-slate-900/60"
              }`}
              data-testid={`learning-item-${item.id}`}
            >
              <button
                type="button"
                onClick={() => (done ? markIncomplete(item.id) : markComplete(item.id))}
                className={`mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded border-2 text-xs ${
                  done
                    ? "border-emerald-500 bg-emerald-500 text-white"
                    : "border-slate-600 text-transparent hover:border-slate-400"
                }`}
                aria-label={done ? `${item.title} işaretini kaldır` : `${item.title} tamamlandı işaretle`}
                data-testid={`learning-toggle-${item.id}`}
              >
                {done && "✓"}
              </button>
              <div className="min-w-0 flex-1">
                <Link
                  href={item.href}
                  className="block"
                  onClick={() => {
                    if (!done) {
                      // Auto-mark complete on click — soft hint they took the action
                      // (revisable via the toggle)
                    }
                  }}
                >
                  <p
                    className={`text-sm font-medium ${
                      done ? "text-slate-500 line-through" : "text-white"
                    }`}
                  >
                    {item.icon} {item.title}
                    {item.required && !done && (
                      <span className="ml-2 rounded bg-amber-500/20 px-1.5 py-0.5 text-[9px] font-semibold text-amber-300">
                        ZORUNLU
                      </span>
                    )}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-400">{item.description}</p>
                </Link>
              </div>
            </li>
          );
        })}
      </ul>

      {items.length > 5 && (
        <button
          type="button"
          onClick={() => setShowAll((v) => !v)}
          className="mt-3 w-full rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-400 hover:bg-slate-800"
          data-testid="learning-checklist-toggle-all"
        >
          {showAll ? "Sadece ilk 5'i göster" : `Tümünü göster (${items.length})`}
        </button>
      )}

      {requiredCompletedAll && !isComplete && (
        <p
          className="mt-3 text-center text-xs text-emerald-400"
          data-testid="learning-required-complete"
        >
          ✓ Zorunlu adımlar tamamlandı. İsteğe bağlı adımlarla devam edebilirsin.
        </p>
      )}
    </div>
  );
}
