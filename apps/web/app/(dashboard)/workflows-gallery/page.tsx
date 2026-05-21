"use client";

import Link from "next/link";
import { useState } from "react";

import { WORKFLOW_TEMPLATES, type WorkflowTemplate } from "@/lib/workflowTemplates";

const DIFFICULTY_LABELS: Record<WorkflowTemplate["difficulty"], { label: string; color: string }> = {
  beginner: { label: "Başlangıç", color: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" },
  intermediate: { label: "Orta", color: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
  advanced: { label: "İleri", color: "bg-rose-500/20 text-rose-300 border-rose-500/30" },
};

export default function WorkflowsGalleryPage() {
  const [filter, setFilter] = useState<"all" | WorkflowTemplate["difficulty"]>("all");
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  const allTags = Array.from(new Set(WORKFLOW_TEMPLATES.flatMap((t) => t.tags))).sort();

  const visible = WORKFLOW_TEMPLATES.filter((t) => {
    if (filter !== "all" && t.difficulty !== filter) return false;
    if (selectedTag && !t.tags.includes(selectedTag)) return false;
    return true;
  });

  return (
    <div
      className="min-h-screen bg-slate-950 text-slate-100"
      data-testid="workflows-gallery-page"
    >
      <div className="mx-auto max-w-6xl px-6 py-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">⚡ Workflow Galerisi</h1>
          <p className="mt-2 text-sm text-slate-400">
            Önceden tanımlı QA akışları. Tıkla → adım adım rehberi takip et.
          </p>
        </header>

        <div className="mb-6 space-y-3">
          <div className="flex flex-wrap gap-2" data-testid="workflow-difficulty-filter">
            <button
              type="button"
              onClick={() => setFilter("all")}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                filter === "all"
                  ? "bg-indigo-600 text-white"
                  : "border border-slate-700 text-slate-400 hover:bg-slate-800"
              }`}
              data-testid="workflow-filter-all"
            >
              Tümü ({WORKFLOW_TEMPLATES.length})
            </button>
            {(Object.keys(DIFFICULTY_LABELS) as Array<WorkflowTemplate["difficulty"]>).map(
              (d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setFilter(d)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                    filter === d
                      ? "bg-indigo-600 text-white"
                      : "border border-slate-700 text-slate-400 hover:bg-slate-800"
                  }`}
                  data-testid={`workflow-filter-${d}`}
                >
                  {DIFFICULTY_LABELS[d].label}
                </button>
              ),
            )}
          </div>

          <div className="flex flex-wrap gap-1.5" data-testid="workflow-tag-filter">
            {allTags.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
                className={`rounded px-2 py-0.5 text-[10px] ${
                  selectedTag === tag
                    ? "bg-indigo-500 text-white"
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                }`}
                data-testid={`workflow-tag-${tag}`}
              >
                #{tag}
              </button>
            ))}
          </div>
        </div>

        {visible.length === 0 ? (
          <p
            className="rounded-xl border border-dashed border-slate-700 py-12 text-center text-sm text-slate-500"
            data-testid="workflows-empty"
          >
            Seçili filtreyle template yok.
          </p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2" data-testid="workflows-list">
            {visible.map((t) => (
              <div
                key={t.id}
                className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 hover:border-indigo-500/30"
                data-testid={`workflow-card-${t.id}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="text-3xl">{t.icon}</div>
                    <div>
                      <h3 className="text-lg font-semibold text-white">{t.title}</h3>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                        <span
                          className={`rounded border px-1.5 py-0.5 ${DIFFICULTY_LABELS[t.difficulty].color}`}
                        >
                          {DIFFICULTY_LABELS[t.difficulty].label}
                        </span>
                        <span className="text-slate-500">⏱ {t.estimatedTime}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <p className="mt-3 text-sm text-slate-400">{t.description}</p>

                <div className="mt-4">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Adımlar ({t.steps.length})
                  </p>
                  <ol className="mt-2 space-y-1">
                    {t.steps.slice(0, 3).map((s, idx) => (
                      <li key={idx} className="text-xs text-slate-300">
                        <span className="mr-2 text-slate-500">{idx + 1}.</span>
                        {s.title}
                      </li>
                    ))}
                    {t.steps.length > 3 && (
                      <li className="text-xs text-slate-500">
                        ... ve {t.steps.length - 3} adım daha
                      </li>
                    )}
                  </ol>
                </div>

                <div className="mt-4 rounded-lg bg-slate-950/50 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Sonuç
                  </p>
                  <p className="mt-1 text-xs italic text-slate-300">{t.outcome}</p>
                </div>

                <div className="mt-4 flex flex-wrap gap-1.5">
                  {t.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>

                <Link
                  href={`/workflows-gallery/${t.id}`}
                  className="mt-4 inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
                  data-testid={`workflow-start-${t.id}`}
                >
                  Bu akışı kur →
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
