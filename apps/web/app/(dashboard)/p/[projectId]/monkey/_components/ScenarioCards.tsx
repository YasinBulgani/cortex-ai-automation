"use client";

// ── ScenarioCards ─────────────────────────────────────────────────────────────
/**
 * LLM çıktısını (Markdown) parse ederek senaryo kartlarına dönüştürür.
 * Henüz streaming sırasında çağrıldığında tamamlanmamış senaryoları da gösterir.
 */
export function ScenarioCards({
  markdown,
  streaming,
}: {
  markdown: string;
  streaming: boolean;
}) {
  // "### Senaryo N:" ile başlayan blokları böl
  const rawBlocks = markdown.split(/(?=###\s+Senaryo\s+\d+)/i).filter((b) => b.trim());

  if (rawBlocks.length === 0) {
    // Henüz ilk senaryo başlığına ulaşılmadı — ham metni göster
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-950 p-3 text-[11px] text-slate-300 whitespace-pre-wrap leading-5 min-h-[60px]">
        {markdown}
        {streaming && (
          <span className="inline-block w-1.5 h-3.5 bg-sky-400 animate-pulse ml-0.5 align-middle" />
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {rawBlocks.map((block, idx) => {
        const lines = block.trim().split("\n");
        const titleLine = lines[0] ?? "";
        const title = titleLine.replace(/^###\s+/, "").trim();
        const body = lines.slice(1).join("\n").trim();

        // Durum satırını bul
        const statusLine = lines.find((l) => l.startsWith("**Durum**"));
        const isSuccess = statusLine?.includes("✅");
        const isFail = statusLine?.includes("❌");
        const isWarn = statusLine?.includes("⚠️");

        // Önem derecesi
        const importanceLine = lines.find((l) => l.startsWith("**Önem"));
        const isCritical = importanceLine?.toLowerCase().includes("kritik");
        const isHigh = importanceLine?.toLowerCase().includes("yüksek");

        const borderColor = isFail
          ? "border-red-500/30"
          : isWarn
            ? "border-amber-500/30"
            : isSuccess
              ? "border-emerald-500/20"
              : "border-slate-700";

        const badgeBg = isFail
          ? "bg-red-500/10 text-red-300"
          : isWarn
            ? "bg-amber-500/10 text-amber-300"
            : isSuccess
              ? "bg-emerald-500/10 text-emerald-300"
              : "bg-slate-700/40 text-slate-400";

        const statusIcon = isFail ? "❌" : isWarn ? "⚠️" : isSuccess ? "✅" : "⏳";

        const importanceBadge = isCritical ? (
          <span className="rounded px-1.5 py-0.5 text-[9px] font-bold uppercase bg-red-500/20 text-red-300">
            Kritik
          </span>
        ) : isHigh ? (
          <span className="rounded px-1.5 py-0.5 text-[9px] font-bold uppercase bg-orange-500/20 text-orange-300">
            Yüksek
          </span>
        ) : null;

        // Body'yi okunabilir şekilde render et — **bold** → <strong>
        const renderBody = (text: string) => {
          const rows = text.split("\n");
          return rows.map((row, i) => {
            if (row.match(/^\*\*[^*]+\*\*:/)) {
              const [label, ...rest] = row.split("**:");
              const labelText = label.replace("**", "").replace(/^\s*/, "");
              return (
                <div key={i} className="mt-2 first:mt-0">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    {labelText}
                  </span>
                  {rest.length > 0 && (
                    <span className="text-[11px] text-slate-300">
                      {" "}
                      {rest.join("**:").trim()}
                    </span>
                  )}
                </div>
              );
            }
            if (row.match(/^\d+\./)) {
              return (
                <div key={i} className="ml-3 text-[11px] text-slate-300">
                  {row}
                </div>
              );
            }
            if (row.startsWith("- ")) {
              return (
                <div key={i} className="ml-3 text-[11px] text-slate-400">
                  • {row.slice(2)}
                </div>
              );
            }
            if (!row.trim()) return <div key={i} className="h-1" />;
            return (
              <div key={i} className="text-[11px] text-slate-300">
                {row}
              </div>
            );
          });
        };

        return (
          <details
            key={idx}
            open={idx === 0}
            className={`rounded-xl border ${borderColor} bg-slate-900/60 overflow-hidden`}
          >
            <summary
              className={`flex cursor-pointer select-none items-center gap-2.5 px-4 py-3 ${badgeBg} rounded-xl`}
            >
              <span className="text-base">{statusIcon}</span>
              <span className="flex-1 text-sm font-semibold text-slate-100 leading-snug">
                {title}
              </span>
              {importanceBadge}
              {idx === rawBlocks.length - 1 && streaming && (
                <span className="inline-block h-2 w-2 rounded-full bg-sky-400 animate-pulse" />
              )}
            </summary>
            <div className="border-t border-slate-800 px-4 py-3 space-y-0.5">
              {renderBody(body)}
            </div>
          </details>
        );
      })}
      {streaming && (
        <div className="flex items-center gap-2 text-[11px] text-sky-400">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-sky-400 animate-pulse" />
          Analiz devam ediyor…
        </div>
      )}
    </div>
  );
}
