"use client";

/**
 * DslActionCard
 *
 * Renders a single DSL action as a clickable list item (ActionList row) and,
 * when selected, the full detail panel (ActionDetail).
 *
 * Usage:
 *   // List row
 *   <DslActionCard
 *     action={action}
 *     selected={selectedId === action.id}
 *     onSelect={setSelected}
 *   />
 *
 *   // Full detail view
 *   <DslActionCardDetail action={selectedAction} />
 */

import { Badge } from "@/components/ui/badge";
import type { DslAction } from "@/lib/dsl-api";

// ── List row ───────────────────────────────────────────────────────────────

export interface DslActionCardProps {
  action: DslAction;
  selected: boolean;
  onSelect: (action: DslAction) => void;
}

export function DslActionCard({ action, selected, onSelect }: DslActionCardProps) {
  const langs = Object.keys(action.aliases || {}).sort().join(" / ") || "—";
  const primary =
    action.aliases?.tr?.[0] || action.aliases?.en?.[0] || action.description;
  const impls = Object.keys(action.implementations || {});

  return (
    <li
      onClick={() => onSelect(action)}
      className={[
        "cursor-pointer px-4 py-3 transition-colors",
        selected ? "bg-blue-600/20" : "hover:bg-white/5",
      ].join(" ")}
    >
      <div className="flex items-center justify-between gap-3">
        <code className="font-mono text-sm text-white">{action.id}</code>
        <div className="flex items-center gap-2">
          <Badge>{langs}</Badge>
          {impls.map((i) => (
            <Badge key={i} className="border-blue-700 text-blue-300">
              {i}
            </Badge>
          ))}
        </div>
      </div>
      <p className="mt-1 text-sm text-slate-300">{primary}</p>
      <p className="mt-0.5 text-xs text-slate-500">
        {action.category} · {action.tags?.slice(0, 4).join(", ") || "tag yok"}
      </p>
    </li>
  );
}

// ── Detail panel ───────────────────────────────────────────────────────────

export interface DslActionCardDetailProps {
  action: DslAction | null;
}

export function DslActionCardDetail({ action }: DslActionCardDetailProps) {
  if (!action) {
    return (
      <div className="flex h-full items-center justify-center text-center text-sm text-slate-500">
        Bir cümlecik seçin — detay burada görüntülenir.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 text-sm text-slate-200">
      <div>
        <code className="font-mono text-base text-white">{action.id}</code>
        <p className="mt-1 text-xs text-slate-400">{action.category}</p>
      </div>

      <p className="text-sm">{action.description}</p>

      {/* Aliases */}
      <section>
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Alias'lar
        </h3>
        <div className="flex flex-col gap-2">
          {Object.entries(action.aliases || {}).map(([lang, list]) => (
            <div key={lang}>
              <p className="text-xs font-semibold text-blue-300">
                {lang.toUpperCase()}
              </p>
              <ul className="ml-3 list-disc space-y-1">
                {list.map((alias, i) => (
                  <li key={i} className="text-sm text-slate-200">
                    <code className="break-words text-slate-100">{alias}</code>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* Parameters */}
      {action.parameters && action.parameters.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Parametreler
          </h3>
          <ul className="ml-3 list-disc space-y-1 text-xs">
            {action.parameters.map((p) => (
              <li key={p.name}>
                <span className="font-mono text-white">{p.name}</span>{" "}
                <span className="text-slate-400">({p.type})</span>
                {p.description ? ` — ${p.description}` : ""}
                {p.required ? "" : " · opsiyonel"}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Implementations */}
      {action.implementations &&
        Object.keys(action.implementations).length > 0 && (
          <section>
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              İmplementasyon
            </h3>
            <div className="flex flex-col gap-2 text-xs">
              {Object.entries(action.implementations).map(([lang, impl]) => (
                <div
                  key={lang}
                  className="rounded border border-slate-800 bg-slate-900/70 p-2"
                >
                  <p className="mb-1 font-semibold text-blue-300">{lang}</p>
                  <p className="break-all text-slate-300">{impl.source_file}</p>
                  {(impl.module || impl.class) && (
                    <p className="mt-0.5 text-slate-500">
                      {impl.module || impl.class}
                      {impl.function || impl.method
                        ? `.${impl.function || impl.method}`
                        : ""}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

      {/* Tags */}
      {action.tags && action.tags.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Etiketler
          </h3>
          <div className="flex flex-wrap gap-1">
            {action.tags.map((t) => (
              <Badge key={t}>{t}</Badge>
            ))}
          </div>
        </section>
      )}

      {/* Examples */}
      {action.examples && action.examples.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Örnekler
          </h3>
          {action.examples.map((ex, i) => (
            <pre
              key={i}
              className="overflow-x-auto rounded border border-slate-800 bg-slate-950 p-2 text-xs text-slate-200"
            >
              {ex}
            </pre>
          ))}
        </section>
      )}
    </div>
  );
}
