"use client";

import { Button } from "@/components/ui/button";

// ── Types ────────────────────────────────────────────────────────────────────

type AiPhase = "idle" | "scenarios" | "karate" | "done" | "error";

function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

// ── Props ────────────────────────────────────────────────────────────────────

export interface AiPipelinePanelProps {
  // AI scenario pipeline
  aiPhase: AiPhase;
  aiError: string | null;
  scenariosText: string | null;
  karateText: string | null;
  onExtractScenarios: () => void;
  onGenerateKarate: () => void;
  onExportScenarios: () => void;
  onExportKarate: () => void;
  // Analysis streaming
  analysisStreaming: boolean;
  analysisText: string;
  analysisDone: boolean;
  analysisError: string | null;
  onStartAnalysis: () => void;
  onAbortAnalysis: () => void;
  onExportAnalysis: () => void;
  // Context for empty state
  actionsPerformed: number;
  pagesVisitedCount: number;
  errorCount: number;
}

// ── Component ────────────────────────────────────────────────────────────────

export function AiPipelinePanel({
  aiPhase,
  aiError,
  scenariosText,
  karateText,
  onExtractScenarios,
  onGenerateKarate,
  onExportScenarios,
  onExportKarate,
  analysisStreaming,
  analysisText,
  analysisDone,
  analysisError,
  onStartAnalysis,
  onAbortAnalysis,
  onExportAnalysis,
  actionsPerformed,
  pagesVisitedCount,
  errorCount,
}: AiPipelinePanelProps) {
  const aiLoading = aiPhase === "scenarios" || aiPhase === "karate";

  return (
    <>
      {/* AI Test Senaryosu & Otomasyon */}
      <div className="mt-2 flex flex-col gap-4 rounded-xl border border-violet-400/20 bg-violet-500/5 p-4">
        <div className="flex items-center gap-2">
          <span className="text-base">🤖</span>
          <span className="text-sm font-semibold text-violet-200">
            AI Test Senaryosu &amp; Otomasyon
          </span>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              type="button"
              onClick={onExtractScenarios}
              disabled={aiLoading}
              className={cn(
                "gap-2 border px-4 py-2 text-sm font-semibold",
                aiLoading
                  ? "border-slate-700 bg-slate-900/40 text-slate-500"
                  : "border-violet-400/30 bg-violet-500/15 text-violet-100 hover:bg-violet-500/25",
              )}
            >
              {aiPhase === "scenarios" ? (
                <span>⏳ Senaryolar üretiliyor...</span>
              ) : (
                <>
                  <span>✦</span>
                  <span>AI Senaryo Çıkar</span>
                </>
              )}
            </Button>

            {scenariosText && (
              <Button
                variant="outline"
                size="sm"
                type="button"
                onClick={onExportScenarios}
                className="gap-1.5 border border-slate-600 bg-slate-800/50 text-xs font-semibold text-slate-300 hover:bg-slate-700/50"
              >
                ↓ Senaryolar (.md)
              </Button>
            )}
          </div>

          {scenariosText && (
            <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-700 bg-slate-900/60 p-3">
              <pre className="whitespace-pre-wrap text-[11px] leading-5 text-slate-300">
                {scenariosText}
              </pre>
            </div>
          )}
        </div>

        {scenariosText && (
          <div className="flex flex-col gap-2 border-t border-slate-700/50 pt-4">
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                type="button"
                onClick={onGenerateKarate}
                disabled={aiLoading}
                className={cn(
                  "gap-2 border px-4 py-2 text-sm font-semibold",
                  aiLoading
                    ? "border-slate-700 bg-slate-900/40 text-slate-500"
                    : "border-sky-400/30 bg-sky-500/15 text-sky-100 hover:bg-sky-500/25",
                )}
              >
                {aiPhase === "karate" ? (
                  <span>⏳ Karate DSL üretiliyor...</span>
                ) : (
                  <>
                    <span>◈</span>
                    <span>Karate DSL Üret</span>
                  </>
                )}
              </Button>

              {karateText && (
                <Button
                  variant="outline"
                  size="sm"
                  type="button"
                  onClick={onExportKarate}
                  className="gap-1.5 border border-emerald-400/25 bg-emerald-500/10 text-xs font-semibold text-emerald-200 hover:bg-emerald-500/20"
                >
                  ↓ İndir (.feature)
                </Button>
              )}
            </div>

            {karateText && (
              <div className="max-h-96 overflow-y-auto rounded-lg border border-sky-400/20 bg-slate-950 p-3">
                <pre className="whitespace-pre-wrap text-[11px] leading-5 text-sky-200">
                  {karateText}
                </pre>
              </div>
            )}
          </div>
        )}

        {aiPhase === "error" && aiError && (
          <div className="rounded-lg border border-red-400/20 bg-red-500/5 px-3 py-2 text-xs text-red-300">
            AI Gateway hatası: {aiError}
          </div>
        )}
      </div>

      {/* Akıllı Senaryo Analizi (LLM Streaming) */}
      <div className="flex flex-col gap-4 rounded-xl border border-sky-400/20 bg-sky-500/5 p-4">
        {/* Header + controls */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-base">🔬</span>
            <div>
              <p className="text-sm font-semibold text-sky-200">Akıllı Senaryo Analizi</p>
              <p className="text-[11px] text-slate-400">
                LLM, eylem günlüğünüzü okuyarak denenen her senaryoyu detaylıca belgeler
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {analysisDone && (
              <Button
                variant="outline"
                size="sm"
                type="button"
                onClick={onExportAnalysis}
                className="gap-1.5 border border-sky-400/25 bg-sky-500/10 text-xs font-semibold text-sky-200 hover:bg-sky-500/20"
              >
                ↓ Analizi İndir (.md)
              </Button>
            )}
            {analysisStreaming && (
              <Button
                variant="ghost-danger"
                size="sm"
                type="button"
                onClick={onAbortAnalysis}
                className="border border-red-400/30 bg-red-500/15 text-xs font-semibold text-red-200 hover:bg-red-500/25"
              >
                ⏹ Durdur
              </Button>
            )}
            {!analysisStreaming && (
              <Button
                variant="outline"
                type="button"
                onClick={onStartAnalysis}
                className={cn(
                  "gap-2 border px-4 py-2 text-sm font-semibold",
                  analysisDone
                    ? "border-slate-600 bg-slate-800/50 text-slate-300 hover:bg-slate-700/50"
                    : "border-sky-400/40 bg-sky-500/20 text-sky-50 hover:bg-sky-500/30",
                )}
              >
                <span>🔬</span>
                <span>{analysisDone ? "Yeniden Analiz Et" : "Senaryoları Analiz Et"}</span>
              </Button>
            )}
          </div>
        </div>

        {/* Streaming progress */}
        {analysisStreaming && (
          <div className="flex items-center gap-2 text-xs text-sky-300">
            <span className="inline-block h-2 w-2 rounded-full bg-sky-400 animate-pulse" />
            LLM senaryoları yazıyor… ({analysisText.length} karakter)
          </div>
        )}

        {/* Error */}
        {analysisError && (
          <div className="rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">
            ❌ {analysisError}
          </div>
        )}

        {/* Streaming output */}
        {analysisText && (
          <div className="relative">
            <ScenarioCards markdown={analysisText} streaming={analysisStreaming} />

            <details className="mt-3">
              <summary className="cursor-pointer text-[11px] text-slate-500 hover:text-slate-300 select-none">
                Ham Markdown göster
              </summary>
              <div className="mt-2 max-h-96 overflow-y-auto rounded-lg border border-slate-700 bg-slate-950 p-3">
                <pre className="whitespace-pre-wrap text-[11px] leading-5 text-slate-300">
                  {analysisText}
                  {analysisStreaming && (
                    <span className="inline-block w-1.5 h-3.5 bg-sky-400 animate-pulse ml-0.5 align-middle" />
                  )}
                </pre>
              </div>
            </details>
          </div>
        )}

        {/* Empty state */}
        {!analysisText && !analysisStreaming && !analysisError && (
          <div className="rounded-lg border border-slate-700 bg-slate-900/40 px-4 py-8 text-center">
            <p className="text-2xl mb-2">🔬</p>
            <p className="text-sm text-slate-400">
              LLM, monkey test oturumunda denenen tüm senaryoları sayfa akışlarına göre gruplar ve belgeler.
            </p>
            <p className="text-xs text-slate-500 mt-1">
              {actionsPerformed} eylem · {pagesVisitedCount} sayfa · {errorCount} hata analiz edilecek
            </p>
          </div>
        )}
      </div>
    </>
  );
}

// ── ScenarioCards helper ──────────────────────────────────────────────────────
/**
 * LLM çıktısını (Markdown) parse ederek senaryo kartlarına dönüştürür.
 */
function ScenarioCards({
  markdown,
  streaming,
}: {
  markdown: string;
  streaming: boolean;
}) {
  const rawBlocks = markdown
    .split(/(?=###\s+Senaryo\s+\d+)/i)
    .filter((b) => b.trim());

  if (rawBlocks.length === 0) {
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

        const statusLine = lines.find((l) => l.startsWith("**Durum**"));
        const isSuccess = statusLine?.includes("✅");
        const isFail = statusLine?.includes("❌");
        const isWarn = statusLine?.includes("⚠️");

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

        const renderBody = (text: string) =>
          text.split("\n").map((row, i) => {
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
            if (row.match(/^\d+\./))
              return (
                <div key={i} className="ml-3 text-[11px] text-slate-300">
                  {row}
                </div>
              );
            if (row.startsWith("- "))
              return (
                <div key={i} className="ml-3 text-[11px] text-slate-400">
                  • {row.slice(2)}
                </div>
              );
            if (!row.trim()) return <div key={i} className="h-1" />;
            return (
              <div key={i} className="text-[11px] text-slate-300">
                {row}
              </div>
            );
          });

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
