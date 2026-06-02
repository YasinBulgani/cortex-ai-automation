"use client";

import type { ApiEnvironment } from "@/lib/hooks/use-api-testing";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface EnvironmentCardProps {
  env: ApiEnvironment;
  isSelected: boolean;
  onSelect: (env: ApiEnvironment) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function EnvironmentCard({
  env,
  isSelected,
  onSelect,
}: EnvironmentCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(env)}
      className={`w-full px-4 py-3 text-left transition-colors hover:bg-slate-800/60 ${
        isSelected
          ? "bg-slate-800/80 border-l-2 border-blue-500"
          : ""
      }`}
    >
      <div className="flex items-center justify-between mb-0.5">
        <span className="text-sm font-medium text-white truncate">
          {env.name}
        </span>
        <div className="flex items-center gap-1.5 shrink-0">
          {env.is_default && (
            <span className="rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
              Varsayılan
            </span>
          )}
          {env.sensitive_keys.length > 0 && (
            <span
              className="text-[10px] text-amber-400"
              title="Hassas değişkenler var"
            >
              🔒
            </span>
          )}
        </div>
      </div>
      <div className="flex gap-2 text-[11px] text-slate-500">
        <span>{Object.keys(env.variables).length} değişken</span>
        {env.sensitive_keys.length > 0 && (
          <span>{env.sensitive_keys.length} hassas</span>
        )}
      </div>
    </button>
  );
}
