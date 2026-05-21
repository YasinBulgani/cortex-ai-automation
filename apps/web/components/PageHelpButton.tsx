"use client";

import Link from "next/link";
import { useState } from "react";

type Props = {
  /** KB article path (örn. /kb/a-12345) */
  kbHref?: string;
  /** Inline metin (tooltip benzeri) */
  hint?: string;
  /** Detaylı uzun açıklama */
  details?: string;
  /** Ek link'ler */
  links?: Array<{ label: string; href: string }>;
};

/**
 * Her sayfa header'ında "?" butonu — popover ile bağlamsal yardım.
 *
 * Usage:
 *   <PageHeader title="Senaryolar" right={<PageHelpButton kbHref="/kb/a-12345" hint="..." />} />
 */
export function PageHelpButton({ kbHref, hint, details, links }: Props) {
  const [open, setOpen] = useState(false);

  if (!hint && !details && !kbHref && !links?.length) {
    return null;
  }

  return (
    <div className="relative" data-testid="page-help-button">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex h-7 w-7 items-center justify-center rounded-full border border-slate-700 text-xs text-slate-400 hover:bg-slate-800 hover:text-white"
        aria-label="Sayfa yardımı"
        data-testid="page-help-toggle"
      >
        ?
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <div
            className="absolute right-0 top-9 z-50 w-80 rounded-xl border border-slate-700 bg-slate-900 p-4 shadow-2xl"
            data-testid="page-help-popover"
          >
            {hint && <p className="text-sm font-medium text-white">{hint}</p>}
            {details && (
              <p className="mt-2 text-xs leading-relaxed text-slate-400">{details}</p>
            )}

            {(kbHref || (links && links.length > 0)) && (
              <div className="mt-3 border-t border-slate-800 pt-3 space-y-1">
                {kbHref && (
                  <Link
                    href={kbHref}
                    onClick={() => setOpen(false)}
                    className="block rounded px-2 py-1.5 text-xs text-indigo-400 hover:bg-slate-800"
                    data-testid="page-help-kb-link"
                  >
                    📖 Tam rehberi oku →
                  </Link>
                )}
                {links?.map((l) => (
                  <Link
                    key={l.href}
                    href={l.href}
                    onClick={() => setOpen(false)}
                    className="block rounded px-2 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
                  >
                    {l.label} →
                  </Link>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
