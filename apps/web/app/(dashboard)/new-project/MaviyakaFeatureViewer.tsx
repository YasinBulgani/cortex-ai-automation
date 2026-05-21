"use client";

import { GHERKIN_KW } from "./constants";
import type { LocatorEntry } from "./types";

export function MaviyakaFeatureViewer({
  content,
  allLocators,
  onRedKeyClick,
}: {
  content: string;
  allLocators: LocatorEntry[];
  onRedKeyClick: (key: string) => void;
}) {
  const keySet = new Set(allLocators.map((l) => l.key));
  return (
    <pre className="rounded-lg bg-slate-950 p-4 text-xs font-mono whitespace-pre-wrap overflow-auto max-h-96 leading-5">
      {content.split("\n").map((line, li) => {
        const parts = line.split('"');
        return (
          <div key={li}>
            {parts.map((part, pi) => {
              if (pi % 2 === 0) {
                const trimmed = part.trimStart();
                for (const kw of GHERKIN_KW) {
                  if (trimmed.startsWith(kw)) {
                    const indent = part.slice(0, part.length - trimmed.length);
                    const after = trimmed.slice(kw.length);
                    return (
                      <span key={pi}>
                        <span className="text-slate-600">{indent}</span>
                        <span className="text-blue-400 font-semibold">{kw}</span>
                        <span className="text-slate-300">{after}</span>
                      </span>
                    );
                  }
                }
                return <span key={pi} className="text-slate-300">{part}</span>;
              }
              // quoted value
              if (keySet.has(part)) {
                return <span key={pi} className="text-emerald-400">&quot;{part}&quot;</span>;
              }
              return (
                <button
                  key={pi}
                  type="button"
                  onClick={() => onRedKeyClick(part)}
                  className="text-red-400 hover:text-red-300 underline underline-offset-2 cursor-pointer"
                  title={`"${part}" lokator bulunamadı — tıkla AI önerisi`}
                >
                  &quot;{part}&quot;
                </button>
              );
            })}
          </div>
        );
      })}
    </pre>
  );
}
