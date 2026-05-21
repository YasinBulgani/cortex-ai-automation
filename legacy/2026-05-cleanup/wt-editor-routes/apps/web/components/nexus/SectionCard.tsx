"use client";
import React from "react";

interface SectionCardProps {
  title?: string;
  icon?: React.ReactNode;
  right?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  noPad?: boolean;
}

export function SectionCard({ title, icon, right, children, className = "", noPad = false }: SectionCardProps) {
  return (
    <div className={`rounded-xl border border-slate-700 bg-slate-900/40 ${className}`}>
      {(title || right) && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            {icon && <span className="text-slate-400">{icon}</span>}
            {title && <h3 className="text-sm font-semibold text-white">{title}</h3>}
          </div>
          {right && <div className="flex items-center gap-2">{right}</div>}
        </div>
      )}
      <div className={noPad ? "" : "p-4"}>{children}</div>
    </div>
  );
}
