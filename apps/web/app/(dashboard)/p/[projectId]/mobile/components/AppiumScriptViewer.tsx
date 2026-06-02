"use client";

type AppiumAction = {
  action: "launch" | "find" | "tap" | "sendKeys" | "verifyVisible" | "wait" | "swipe";
  by?: "accessibilityId" | "xpath" | "predicate";
  value?: string;
  text?: string;
  timeout?: number;
  ms?: number;
  direction?: "up" | "down" | "left" | "right";
};

interface AppiumScriptViewerProps {
  steps: AppiumAction[] | null;
}

export function AppiumScriptViewer({ steps }: AppiumScriptViewerProps) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 max-h-[340px] overflow-y-auto">
      <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-2">
        Üretilen Appium Adımları
      </p>
      {!steps ? (
        <p className="text-xs text-slate-500 italic">
          Henüz üretilmedi — "Adımları Üret"e basın.
        </p>
      ) : (
        <ol className="space-y-1">
          {steps.map((s, i) => (
            <li key={i} className="text-[11px] font-mono flex gap-2">
              <span className="text-slate-600">{String(i + 1).padStart(2, "0")}</span>
              <span className="text-blue-300">{s.action}</span>
              {s.by && <span className="text-slate-500">by={s.by}</span>}
              {s.value && (
                <span className="text-emerald-300 truncate">&quot;{s.value}&quot;</span>
              )}
              {s.text && (
                <span className="text-amber-300 truncate">&quot;{s.text}&quot;</span>
              )}
              {s.ms && <span className="text-slate-500">{s.ms}ms</span>}
              {s.timeout && (
                <span className="text-slate-600 text-[10px]">timeout={s.timeout}ms</span>
              )}
              {s.direction && (
                <span className="text-purple-300">{s.direction}</span>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
