"use client";

import type {
  LocatorEntry,
  LocatorFile,
  MaviyakaFeature,
  ScenarioMappingReport,
  StepMapping,
  XPathQuality,
} from "../types";
import { actionNeedsLocator } from "../types";
import { MaviyakaFeatureViewer } from "../MaviyakaFeatureViewer";

interface FeatureOutputPanelProps {
  maviyakaFeatures: MaviyakaFeature[];
  activeFeatureIdx: number;
  locatorFiles: LocatorFile[];
  stepMappings: ScenarioMappingReport[];
  activeMappingIdx: number;
  testDataMap: Record<string, string>;
  running: boolean;
  ideRunning: boolean;
  onSetActiveFeatureIdx: (i: number) => void;
  onSetActiveMappingIdx: (i: number) => void;
  onSuggestLocatorForKey: (key: string) => void;
  onSuggestLocatorForStep: (step: StepMapping) => void;
  onNotify: (msg: string) => void;
  onOpenIde: () => void;
  onSkipToFinish: () => void;
}

function XPathQualityBadge({ q }: { q: XPathQuality | null | undefined }) {
  if (!q) return null;
  const cls =
    q.grade === "good"
      ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
      : q.grade === "warn"
      ? "bg-amber-500/15 text-amber-300 border-amber-500/40"
      : q.grade === "bad"
      ? "bg-red-500/15 text-red-300 border-red-500/40"
      : "bg-slate-700/40 text-slate-400 border-slate-600";
  const label =
    q.grade === "good" ? "sağlam"
    : q.grade === "warn" ? "orta"
    : q.grade === "bad" ? "kırılgan"
    : "geçersiz";
  const tip = [
    q.strengths.length > 0 ? `✓ ${q.strengths.join(", ")}` : "",
    q.issues.length > 0 ? `⚠ ${q.issues.join(", ")}` : "",
  ].filter(Boolean).join("  |  ");
  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 text-[10px] ${cls}`}
      title={tip || "XPath kalite skoru"}
    >
      <span className="font-semibold">{q.score}</span>
      <span className="opacity-80">{label}</span>
      {q.issues.length > 0 && (
        <span className="opacity-70">· {q.issues[0]}{q.issues.length > 1 ? ` +${q.issues.length - 1}` : ""}</span>
      )}
    </div>
  );
}

export function FeatureOutputPanel({
  maviyakaFeatures,
  activeFeatureIdx,
  locatorFiles,
  stepMappings,
  activeMappingIdx,
  testDataMap,
  running,
  ideRunning,
  onSetActiveFeatureIdx,
  onSetActiveMappingIdx,
  onSuggestLocatorForKey,
  onSuggestLocatorForStep,
  onNotify,
  onOpenIde,
  onSkipToFinish,
}: FeatureOutputPanelProps) {
  if (maviyakaFeatures.length === 0) return null;

  const allLocators: LocatorEntry[] = locatorFiles.flatMap((f) => f.locators);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <h3 className="text-sm font-semibold text-slate-300">Üretilen Feature Dosyaları</h3>
        <span className="text-[11px] text-slate-500">
          <span className="text-blue-400 font-semibold">keyword</span>
          &nbsp;·&nbsp;
          <span className="text-emerald-400">mevcut lokator</span>
          &nbsp;·&nbsp;
          <span className="text-red-400 underline">eksik lokator (tıkla → AI)</span>
        </span>
      </div>

      {/* Sekme seçici */}
      <div className="flex flex-wrap gap-1.5">
        {maviyakaFeatures.map((f, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onSetActiveFeatureIdx(i)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition
              ${activeFeatureIdx === i ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}
          >
            {f.title}
          </button>
        ))}
      </div>

      {maviyakaFeatures[activeFeatureIdx] && (
        <MaviyakaFeatureViewer
          content={maviyakaFeatures[activeFeatureIdx].content}
          allLocators={allLocators}
          onRedKeyClick={onSuggestLocatorForKey}
        />
      )}

      {/* LLM Destekli Adım → Locator → XPath Raporu */}
      {stepMappings.length > 0 && (
        <div className="rounded-xl border border-purple-500/30 bg-slate-900 p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-purple-200">
                🔗 Adım → Locator → XPath Eşleme Raporu
              </h3>
              <p className="mt-0.5 text-xs text-slate-500">
                LLM her manuel adımı katalogdaki bir key ile eşledi ve karşılığındaki XPath değerini feature&apos;a gömdü.
                Kırmızı satırlar: locator gerekli ama bulunamadı → satırdaki <span className="font-semibold text-amber-300">AI öner</span> ile hızlıca yeni locator öner.
                <span className="ml-1 text-slate-400">open</span> gibi URL tabanlı aksiyonlar için locator gerekmez.
              </p>
              <p className="mt-1 text-[11px] text-slate-500">
                Her XPath&apos;in yanında <span className="text-emerald-300">sağlam</span> /
                <span className="mx-1 text-amber-300">orta</span> /
                <span className="text-red-300">kırılgan</span> rozeti var
                (absolute path, numeric index, dinamik class gibi kırılganlıkları otomatik işaretler).
                Üzerine gelince nedenleri görürsün.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-[11px]">
              <span className="rounded bg-purple-500/15 px-2 py-0.5 text-purple-300">LLM</span>
              <span className="rounded bg-blue-500/15 px-2 py-0.5 text-blue-300">Kural</span>
              <span className="rounded bg-slate-700 px-2 py-0.5 text-slate-300">Otomatik</span>
            </div>
          </div>

          {/* Senaryo sekmeleri */}
          <div className="flex flex-wrap gap-1.5">
            {stepMappings.map((m, i) => {
              const missing = m.steps.filter(
                (s) => s.idx >= 0 && actionNeedsLocator(s.action) && !s.locator_key,
              ).length;
              return (
                <button
                  key={m.scenario_id || i}
                  type="button"
                  onClick={() => onSetActiveMappingIdx(i)}
                  className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium transition
                    ${activeMappingIdx === i
                      ? "bg-purple-600 text-white"
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}
                >
                  <span className="max-w-[240px] truncate">{m.scenario_title}</span>
                  {missing > 0 && (
                    <span className="rounded bg-red-500/20 px-1.5 py-0.5 text-[10px] text-red-300">
                      {missing} eksik
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {stepMappings[activeMappingIdx] && (
            <div className="overflow-hidden rounded-lg border border-slate-800">
              <table className="w-full text-xs">
                <thead className="bg-slate-950 text-[10px] uppercase tracking-widest text-slate-500">
                  <tr>
                    <th className="px-3 py-2 text-left w-[28%]">Adım</th>
                    <th className="px-3 py-2 text-left w-[10%]">Aksiyon</th>
                    <th className="px-3 py-2 text-left w-[18%]">Locator Key</th>
                    <th className="px-3 py-2 text-left w-[30%]">XPath</th>
                    <th className="px-3 py-2 text-left w-[14%]">Kaynak</th>
                  </tr>
                </thead>
                <tbody>
                  {stepMappings[activeMappingIdx].steps.map((s, si) => {
                    const needsLoc = actionNeedsLocator(s.action);
                    const missing = s.idx >= 0 && needsLoc && !s.locator_key;
                    const rowCls = missing
                      ? "bg-red-950/30 border-t border-red-900/30"
                      : "border-t border-slate-800 hover:bg-slate-800/30";
                    const sourceBadge =
                      s.source === "llm"
                        ? "bg-purple-500/15 text-purple-300"
                        : s.source === "rule"
                        ? "bg-blue-500/15 text-blue-300"
                        : "bg-slate-700 text-slate-300";
                    const actionColor =
                      s.action === "click"
                        ? "text-amber-300"
                        : s.action === "input"
                        ? "text-sky-300"
                        : s.action === "see" || s.action === "verify"
                        ? "text-emerald-300"
                        : "text-slate-300";
                    return (
                      <tr key={si} className={rowCls}>
                        <td className="px-3 py-2 text-slate-300">
                          <div className="flex items-start gap-2">
                            <span className="shrink-0 text-slate-600 font-mono">
                              {s.idx >= 0 ? `#${s.idx + 1}` : "auto"}
                            </span>
                            <span className="break-words">{s.original}</span>
                          </div>
                          {s.data_value && (
                            <div className="mt-1 text-[10px] text-yellow-400 font-mono">
                              data: &quot;{s.data_value}&quot;
                            </div>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <span className={`font-mono ${actionColor}`}>{s.action}</span>
                        </td>
                        <td className="px-3 py-2">
                          {s.locator_key ? (
                            <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 font-mono text-emerald-300">
                              {s.locator_key}
                            </span>
                          ) : !needsLoc ? (
                            <span
                              className="rounded bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-400"
                              title="Bu aksiyon element gerektirmez (ör. open → URL tabanlı)"
                            >
                              locator gerekmez
                            </span>
                          ) : (
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className="text-red-400 italic">eksik</span>
                              <button
                                type="button"
                                onClick={() => onSuggestLocatorForStep(s)}
                                className="rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-amber-300 transition hover:bg-amber-500/20"
                                title="Bu adım için AI'dan yeni locator önerisi al"
                              >
                                AI öner
                              </button>
                            </div>
                          )}
                          {typeof s.score === "number" && s.source === "rule" && (
                            <span className="ml-1.5 text-[10px] text-slate-500">%{Math.round((s.score || 0) * 100)}</span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          {s.xpath ? (
                            <div className="space-y-1">
                              <div className="flex items-start gap-1.5">
                                <code className="break-all text-[11px] text-slate-400 flex-1">{s.xpath}</code>
                                <button
                                  type="button"
                                  onClick={() => {
                                    navigator.clipboard?.writeText(s.xpath || "");
                                    onNotify("XPath kopyalandı");
                                  }}
                                  className="shrink-0 rounded border border-slate-700 bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400 hover:bg-slate-700 hover:text-white"
                                  title="XPath'i kopyala"
                                >
                                  kopya
                                </button>
                              </div>
                              <XPathQualityBadge q={s.xpath_quality} />
                            </div>
                          ) : !needsLoc ? (
                            <span className="text-[11px] italic text-slate-500">URL tabanlı aksiyon</span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${sourceBadge}`}>
                            {s.source}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* AI Test Verisi */}
      {Object.keys(testDataMap).length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
            AI Üretilen Test Verisi
          </p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {Object.entries(testDataMap).map(([k, v]) => (
              <div key={k} className="rounded-lg bg-slate-950 px-3 py-2 text-xs">
                <span className="text-yellow-400 font-mono">@{k}</span>
                <span className="text-slate-600 mx-1">=</span>
                <span className="text-slate-300">{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Başlat / Atla */}
      <div className="flex flex-wrap gap-3 pt-2">
        <button
          type="button"
          onClick={onOpenIde}
          disabled={running || ideRunning}
          className="flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-40"
        >
          💻 Testleri Başlat — IDE&apos;de aç
        </button>
        <button
          type="button"
          onClick={onSkipToFinish}
          className="rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
        >
          Atla & Bitir →
        </button>
      </div>
    </div>
  );
}
