"use client";

import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { useSharedSteps, type SharedStepItem } from "@/lib/hooks/use-management";

interface Props {
  projectId: string;
  onInsert: (steps: SharedStepItem[]) => void;
  onClose: () => void;
}

export function SharedStepPicker({ projectId, onInsert, onClose }: Props) {
  const { data: templates = [], isLoading } = useSharedSteps(projectId || undefined);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return templates;
    return templates.filter(t =>
      t.name.toLowerCase().includes(q) ||
      t.description?.toLowerCase().includes(q) ||
      t.tags.some(tag => tag.toLowerCase().includes(q))
    );
  }, [templates, search]);

  const selectedTemplate = templates.find(t => t.id === selected);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-6 bg-black/70 backdrop-blur-sm">
      <div className="relative flex max-h-[80vh] w-full max-w-2xl flex-col rounded-2xl border border-border bg-surface-raised shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <h2 className="text-[14px] font-semibold text-fg">Paylaşılan Adım Şablonu Ekle</h2>
            <p className="mt-0.5 text-[11px] text-fg-subtle">Seçilen şablonun adımları mevcut adımların sonuna eklenir</p>
          </div>
          <button type="button" onClick={onClose}
            className="rounded-lg p-1.5 text-fg-subtle hover:bg-surface-overlay transition-colors">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div className="flex flex-1 min-h-0 overflow-hidden">
          {/* Left — template list */}
          <div className="flex w-64 shrink-0 flex-col border-r border-border">
            <div className="p-3">
              <div className="flex items-center gap-2 rounded-xl border border-border bg-surface-overlay px-3 py-1.5 focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/15 transition-all">
                <svg className="h-3.5 w-3.5 shrink-0 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <circle cx="11" cy="11" r="8"/><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35"/>
                </svg>
                <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Şablon ara…"
                  className="flex-1 bg-transparent text-[12px] text-fg placeholder:text-fg-subtle outline-none" />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5">
              {isLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="h-12 rounded-lg bg-surface-overlay animate-pulse" />
                ))
              ) : filtered.length === 0 ? (
                <div className="py-8 text-center">
                  <p className="text-[12px] text-fg-subtle">
                    {search ? "Sonuç bulunamadı" : "Henüz şablon yok"}
                  </p>
                  {!search && (
                    <p className="mt-1 text-[10px] text-fg-disabled">
                      Önce Paylaşılan Adımlar sayfasından şablon oluşturun
                    </p>
                  )}
                </div>
              ) : (
                filtered.map(t => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setSelected(t.id)}
                    className={cn(
                      "flex w-full flex-col items-start rounded-lg px-3 py-2 text-left transition-colors",
                      selected === t.id
                        ? "bg-brand-soft border border-brand/20"
                        : "hover:bg-surface-overlay border border-transparent"
                    )}
                  >
                    <p className={cn("text-[12px] font-medium", selected === t.id ? "text-brand" : "text-fg")}>{t.name}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] text-fg-subtle">{t.steps.length} adım</span>
                      {t.usage_count > 0 && (
                        <span className="text-[10px] text-fg-disabled">{t.usage_count}× kullanım</span>
                      )}
                    </div>
                    {t.tags.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {t.tags.slice(0, 3).map(tag => (
                          <span key={tag} className="rounded border border-border px-1.5 py-0.5 text-[9px] text-fg-disabled">{tag}</span>
                        ))}
                      </div>
                    )}
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Right — preview */}
          <div className="flex flex-1 flex-col overflow-hidden">
            {selectedTemplate ? (
              <>
                <div className="border-b border-border px-5 py-3">
                  <p className="text-[13px] font-semibold text-fg">{selectedTemplate.name}</p>
                  {selectedTemplate.description && (
                    <p className="mt-0.5 text-[11px] text-fg-subtle">{selectedTemplate.description}</p>
                  )}
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-2">
                  {selectedTemplate.steps.map((s, i) => (
                    <div key={i} className="flex gap-3 rounded-lg border border-border bg-surface-overlay p-3">
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-raised text-[10px] font-semibold text-fg-muted">
                        {i + 1}
                      </span>
                      <div className="min-w-0">
                        <p className="text-[12px] text-fg">{s.action}</p>
                        {s.expected_result && (
                          <p className="mt-1 text-[11px] text-fg-subtle border-l-2 border-border/60 pl-2">{s.expected_result}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="border-t border-border p-4">
                  <button
                    type="button"
                    onClick={() => { onInsert(selectedTemplate.steps); onClose(); }}
                    className="w-full rounded-xl bg-brand py-2.5 text-[13px] font-semibold text-brand-fg shadow-sm hover:brightness-105 transition-all"
                  >
                    {selectedTemplate.steps.length} Adımı Ekle →
                  </button>
                </div>
              </>
            ) : (
              <div className="flex flex-1 items-center justify-center">
                <div className="text-center">
                  <svg className="mx-auto h-10 w-10 text-fg-disabled" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                  </svg>
                  <p className="mt-2 text-[12px] text-fg-subtle">Önizlemek için bir şablon seçin</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
