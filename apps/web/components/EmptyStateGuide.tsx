"use client";

import Link from "next/link";
import type { ReactNode } from "react";

type Step = {
  title: string;
  description?: string;
  href?: string;
  onClick?: () => void;
};

type Props = {
  icon?: ReactNode;
  title: string;
  description?: string;
  primaryAction?: { label: string; href?: string; onClick?: () => void; testId?: string };
  secondaryAction?: { label: string; href?: string; onClick?: () => void };
  steps?: Step[];
  kbHref?: string;
  testId?: string;
};

/**
 * Genel-amaçlı boş durum rehberi.
 *
 * Tüm "henüz X yok" sayfalarında kullanılabilir:
 *   <EmptyStateGuide
 *     icon="📝"
 *     title="Henüz senaryo yok"
 *     description="..."
 *     primaryAction={{ label: "Yeni Senaryo", href: ".../scenarios/new" }}
 *     steps={[...]}
 *     kbHref="/kb/a-12345"
 *   />
 */
export function EmptyStateGuide({
  icon,
  title,
  description,
  primaryAction,
  secondaryAction,
  steps,
  kbHref,
  testId = "empty-state-guide",
}: Props) {
  return (
    <div
      className="mx-auto max-w-2xl rounded-2xl border border-dashed border-slate-700 bg-slate-900/30 p-10 text-center"
      data-testid={testId}
    >
      {icon && (
        <div className="mx-auto text-5xl" aria-hidden="true">
          {icon}
        </div>
      )}
      <h2 className="mt-4 text-xl font-bold text-white">{title}</h2>
      {description && (
        <p className="mt-2 text-sm text-slate-400">{description}</p>
      )}

      {(primaryAction || secondaryAction) && (
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          {primaryAction &&
            (primaryAction.href ? (
              <Link
                href={primaryAction.href}
                onClick={primaryAction.onClick}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
                data-testid={primaryAction.testId ?? "empty-state-primary"}
              >
                {primaryAction.label}
              </Link>
            ) : (
              <button
                type="button"
                onClick={primaryAction.onClick}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
                data-testid={primaryAction.testId ?? "empty-state-primary"}
              >
                {primaryAction.label}
              </button>
            ))}
          {secondaryAction &&
            (secondaryAction.href ? (
              <Link
                href={secondaryAction.href}
                onClick={secondaryAction.onClick}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800"
                data-testid="empty-state-secondary"
              >
                {secondaryAction.label}
              </Link>
            ) : (
              <button
                type="button"
                onClick={secondaryAction.onClick}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800"
                data-testid="empty-state-secondary"
              >
                {secondaryAction.label}
              </button>
            ))}
        </div>
      )}

      {steps && steps.length > 0 && (
        <div className="mt-8 text-left" data-testid="empty-state-steps">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Bu sayfada genelde:
          </p>
          <ol className="mt-3 space-y-2">
            {steps.map((step, idx) => (
              <li
                key={idx}
                className="flex items-start gap-3 text-sm"
                data-testid={`empty-state-step-${idx}`}
              >
                <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-bold text-indigo-300">
                  {idx + 1}
                </span>
                <div className="min-w-0 flex-1">
                  {step.href ? (
                    <Link
                      href={step.href}
                      className="font-medium text-slate-200 hover:text-white"
                    >
                      {step.title}
                    </Link>
                  ) : (
                    <span className="font-medium text-slate-200">{step.title}</span>
                  )}
                  {step.description && (
                    <p className="mt-0.5 text-xs text-slate-500">{step.description}</p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      {kbHref && (
        <Link
          href={kbHref}
          className="mt-6 inline-block text-xs text-indigo-400 hover:text-indigo-300"
          data-testid="empty-state-kb-link"
        >
          📖 Detaylı rehberi oku →
        </Link>
      )}
    </div>
  );
}
