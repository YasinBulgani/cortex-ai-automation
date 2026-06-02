"use client";

// ─── Types ────────────────────────────────────────────────────────────────────

export type ActionRecord = {
  step: number;
  type: string;
  selector?: string;
  value?: string;
  description: string;
  success: boolean;
  url: string;
  timestamp: string;
  wave?: number;
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function cn(...cls: (string | false | null | undefined)[]) {
  return cls.filter(Boolean).join(" ");
}

function actionIcon(type: string) {
  const icons: Record<string, string> = {
    click: "👆", fill: "⌨️", navigate: "🔗", scroll: "📜",
    hover: "🖱️", press_key: "⌨️", done: "✅",
    type_text: "⌨️", clear_and_fill: "🔄", scroll_to_top: "⬆️",
    select_option: "📋", assert_visible: "👁️",
    wait_for_text: "⏳", wait_for_selector: "⏳",
  };
  return icons[type] ?? "⚡";
}

// ─── Props ────────────────────────────────────────────────────────────────────

export interface AgentActionLogProps {
  actions: ActionRecord[];
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * AgentActionLog
 *
 * Displays the scrollable history of agent browser actions inside the
 * left panel of the LLM Agent page. All state is owned by the parent;
 * this component is purely presentational.
 */
export function AgentActionLog({ actions }: AgentActionLogProps) {
  return (
    <div className="border-t border-slate-800 bg-slate-900/60" style={{ maxHeight: "220px" }}>
      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-1.5">
        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
          Eylem Geçmişi
        </span>
        <span className="text-[10px] text-slate-600">{actions.length} eylem</span>
      </div>

      <div className="overflow-y-auto" style={{ maxHeight: "180px" }}>
        {actions.length === 0 && (
          <div className="px-3 py-4 text-center text-[11px] text-slate-600">
            Henüz eylem yok
          </div>
        )}

        {[...actions].reverse().map((a) => (
          <div
            key={`${a.step}-${a.timestamp}`}
            className={cn(
              "flex items-start gap-2 border-b border-slate-800/60 px-3 py-2 text-[11px]",
              a.success === false ? "bg-red-500/5 border-red-500/20" : ""
            )}
          >
            <span className="mt-0.5 shrink-0 text-sm">{actionIcon(a.type)}</span>

            <div className="min-w-0 flex-1">
              <p
                className={cn(
                  "font-medium truncate",
                  a.success === false ? "text-red-300" : "text-slate-300"
                )}
              >
                {a.description}
              </p>
              <p className="text-slate-600 truncate font-mono">
                {a.selector ?? a.value ?? ""}
              </p>
            </div>

            <div className="flex items-center gap-1 shrink-0">
              {a.success === false && (
                <span className="text-[9px] text-red-400">✗</span>
              )}
              <span className="rounded px-1 py-0.5 text-[9px] font-bold uppercase bg-slate-800 text-slate-400">
                #{a.step}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
