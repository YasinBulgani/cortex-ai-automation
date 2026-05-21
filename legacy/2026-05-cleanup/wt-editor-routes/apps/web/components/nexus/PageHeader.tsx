"use client";
import React from "react";

interface PageHeaderProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  right?: React.ReactNode;
  badge?: React.ReactNode;
}

export function PageHeader({ icon, title, description, right, badge }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4 mb-6">
      <div className="flex items-start gap-3">
        {icon && (
          <div className="p-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 mt-0.5">
            {icon}
          </div>
        )}
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white">{title}</h1>
            {badge}
          </div>
          {description && (
            <p className="text-sm text-slate-400 mt-0.5">{description}</p>
          )}
        </div>
      </div>
      {right && <div className="flex items-center gap-2 shrink-0">{right}</div>}
    </div>
  );
}
