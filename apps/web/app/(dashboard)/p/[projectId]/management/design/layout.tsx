"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";

const TECHNIQUES: { slug: string; label: string; hint: string }[] = [
  { slug: "bva",      label: "BVA",              hint: "Sınır Değer Analizi" },
  { slug: "eq",       label: "Eşdeğerlik",       hint: "Eşdeğerlik Bölümleme" },
  { slug: "dt",       label: "Karar Tablosu",    hint: "Decision Table" },
  { slug: "pairwise", label: "Pairwise",         hint: "İkili Kombinasyon" },
  { slug: "gherkin",  label: "BDD / Gherkin",    hint: "Senaryo Editörü" },
];

export default function DesignLayout({ children }: { children: React.ReactNode }) {
  const projectId = useRouteParam("projectId") ?? "";
  const pathname = usePathname() ?? "";

  return (
    <div className="flex min-h-full flex-col bg-surface-base">
      {/* Tab bar */}
      <div className="border-b border-border bg-surface-raised px-4 pt-3 sm:px-6">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Test Tasarım Teknikleri</p>
        <nav className="flex flex-wrap gap-1" aria-label="Test tasarım teknikleri">
          {TECHNIQUES.map(t => {
            const href = `/p/${projectId}/management/design/${t.slug}`;
            const isActive = pathname.includes(`/management/design/${t.slug}`);
            return (
              <Link
                key={t.slug}
                href={href}
                title={t.hint}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "rounded-t-lg border-b-2 px-3.5 py-2 text-[13px] font-medium transition-colors",
                  isActive
                    ? "border-teal-500 text-fg"
                    : "border-transparent text-fg-subtle hover:text-fg",
                )}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Active technique */}
      <div className="flex-1">{children}</div>
    </div>
  );
}
