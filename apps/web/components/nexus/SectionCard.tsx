"use client";
import React from "react";

interface SectionCardProps {
  title?: string;
  /** İsteğe bağlı açıklama — başlığın altında küçük, ince metin olarak çıkar. */
  subtitle?: string;
  icon?: React.ReactNode;
  right?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  noPad?: boolean;
}

export function SectionCard({
  title,
  subtitle,
  icon,
  right,
  children,
  className = "",
  noPad = false,
}: SectionCardProps) {
  return (
    <div className={`rounded-xl border border-slate-700 bg-slate-900/40 ${className}`}>
      {(title || right) && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
          <div className="flex items-center gap-2 min-w-0">
            {icon && <span className="text-slate-400 shrink-0">{icon}</span>}
            <div className="min-w-0">
              {title && <h3 className="text-sm font-semibold text-white truncate">{title}</h3>}
              {subtitle && (
                <p className="text-xs text-slate-400 truncate" data-testid="section-card-subtitle">
                  {subtitle}
                </p>
              )}
            </div>
          </div>
          {right && <div className="flex items-center gap-2 shrink-0">{right}</div>}
        </div>
      )}
      <div className={noPad ? "" : "p-4"}>{children}</div>
    </div>
  );
}
