"use client";

import type {
  LocatorFile,
  LocatorMatch,
  LocatorMatchLlmStatus,
  LocatorMatchStatus,
} from "../types";
import { matchKey } from "../types";
import { Button } from "@/components/ui/button";

interface MatchStats {
  steps_considered: number;
  skipped_url_only: number;
}

interface LocatorMatchPanelProps {
  matching: boolean;
  locatorMatches: LocatorMatch[];
  matchStatuses: Record<string, LocatorMatchStatus>;
  matchScenarioCount: number;
  matchLlmStatus: LocatorMatchLlmStatus | null;
  unmatchedLocatorKeys: string[];
  matchStats: MatchStats | null;
  overridePopoverKey: string | null;
  locatorFiles: LocatorFile[];
  onApproveAll: () => void;
  onRejectAll: () => void;
  onReMatch: () => void;
  onSetMatchStatus: (key: string, status: LocatorMatchStatus) => void;
  onSetOverridePopoverKey: (key: string | null) => void;
  onOverrideMatchLocator: (matchKey: string, newLocatorKey: string) => void;
  onJumpToLocator: (key: string) => void;
}

function XPathBadge({ q }: { q: LocatorMatch["xpath_quality"] }) {
  if (!q) return null;
  const palette: Record<string, { cls: string; icon: string; label: string }> = {
    good:    { cls: "bg-emerald-500/15 text-emerald-300", icon: "🟢", label: "Stabil XPath" },
    warn:    { cls: "bg-amber-500/15 text-amber-300",     icon: "🟡", label: "Kırılgan olabilir" },
    bad:     { cls: "bg-red-500/15 text-red-300",         icon: "🔴", label: "Kırılgan XPath" },
    invalid: { cls: "bg-red-700/30 text-red-200",         icon: "⛔", label: "Geçersiz XPath" },
  };
  const p = palette[q.grade] || palette.warn;
  const tooltip = [
    `${p.label} · skor %${q.score}`,
    q.issues.length > 0 ? `Sorunlar: ${q.issues.join(", ")}` : null,
    q.strengths.length > 0 ? `Güç: ${q.strengths.join(", ")}` : null,
  ].filter(Boolean).join("\n");
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${p.cls}`}
      title={tooltip}
    >
      {p.icon} %{q.score}
    </span>
  );
}

export function LocatorMatchPanel({
  matching,
  locatorMatches,
  matchStatuses,
  matchScenarioCount,
  matchLlmStatus,
  unmatchedLocatorKeys,
  matchStats,
  overridePopoverKey,
  locatorFiles,
  onApproveAll,
  onRejectAll,
  onReMatch,
  onSetMatchStatus,
  onSetOverridePopoverKey,
  onOverrideMatchLocator,
  onJumpToLocator,
}: LocatorMatchPanelProps) {
  if (!matching && locatorMatches.length === 0) return null;

  // Group by scenario + step
  const groups = new Map<
    string,
    {
      scenarioId: string;
      scenarioTitle: string;
      stepIdx: number;
      stepText: string;
      items: LocatorMatch[];
    }
  >();
  for (const m of locatorMatches) {
    const gk = `${m.scenario_id}::${m.step_index}`;
    if (!groups.has(gk)) {
      groups.set(gk, {
        scenarioId: m.scenario_id,
        scenarioTitle: m.scenario_title,
        stepIdx: m.step_index,
        stepText: m.step_text,
        items: [],
      });
    }
    groups.get(gk)!.items.push(m);
  }

  const setGroupStatus = (items: LocatorMatch[], status: LocatorMatchStatus) => {
    items.forEach((m) => onSetMatchStatus(matchKey(m), status));
  };

  const groupList = Array.from(groups.values());

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-300">
            🎯 Manuel Adım ⇄ Lokator Eşleşmeleri
          </h3>
          <p className="mt-0.5 text-xs text-slate-500">
            {matching
              ? "Eşleştiriliyor…"
              : `${locatorMatches.length} öneri · ${matchScenarioCount} senaryo incelendi — her satırda "Bu uygun mudur?" yanıtını ver.`}
          </p>
        </div>
        {locatorMatches.length > 0 && !matching && (
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onApproveAll}
              className="border-emerald-500/40 bg-emerald-500/10 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/20"
            >
              ✓ Hepsini Onayla
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onRejectAll}
              className="border-slate-700 bg-slate-800 text-xs font-semibold text-slate-400 hover:border-slate-600"
            >
              ✗ Hepsini Reddet
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onReMatch}
              className="border-slate-700 bg-slate-800 text-xs font-semibold text-slate-400 hover:border-blue-500 hover:text-blue-300"
            >
              ↻ Tekrar Eşleştir
            </Button>
          </div>
        )}
      </div>

      {matching && (
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <svg className="h-4 w-4 animate-spin text-blue-400" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          AI senaryo adımlarını lokator önerileriyle karşılaştırıyor…
        </div>
      )}

      {!matching && locatorMatches.length > 0 && matchLlmStatus && !matchLlmStatus.available && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          <div className="flex items-center gap-2 font-semibold">
            <span>⚠️</span>
            <span>AI eşleştirme devre dışı — heuristic (anahtar kelime) fallback kullanılıyor</span>
          </div>
          <p className="mt-1 text-[11px] text-amber-300/80">
            Güven skorları düşük (~%40–%60) ve tek tip görünebilir. LLM&apos;i etkinleştirmek için backend&apos;de
            <code className="mx-1 rounded bg-amber-500/20 px-1 font-mono">OPENAI_API_KEY</code>
            veya eşdeğer AI sağlayıcı ayarını kontrol edin.
          </p>
          {matchLlmStatus.error && (
            <p className="mt-1 font-mono text-[10px] text-amber-300/60">
              Hata: {matchLlmStatus.error}
            </p>
          )}
        </div>
      )}

      {!matching && matchStats && matchStats.skipped_url_only > 0 && (
        <div className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-[11px] text-slate-400">
          <span className="font-semibold text-slate-300">ℹ️ Bilgi:</span>{" "}
          {matchStats.skipped_url_only} navigasyon adımı (URL&apos;ye git, sayfa aç…) locator
          eşleştirmesinden çıkarıldı. UI element referansı içermeyen adımlar için lokator
          önerilmiyor.
        </div>
      )}

      {!matching && unmatchedLocatorKeys.length > 0 && (
        <details className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-xs text-slate-400">
          <summary className="cursor-pointer font-semibold text-slate-300">
            🔍 {unmatchedLocatorKeys.length} lokator hiçbir adıma bağlanamadı — genişlet
          </summary>
          <p className="mt-1.5 text-[11px] text-slate-500">
            Bu lokatörler crawl&apos;da bulundu ama manuel senaryo adımlarınızdaki hiçbir
            element ifadesiyle eşleşmedi. Muhtemelen bu elementleri kullanan adımı
            unuttunuz veya locator key&apos;leri adım metninden çok farklı isimlendirildi.
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {unmatchedLocatorKeys.map((k) => (
              <span
                key={k}
                className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[11px] text-slate-300"
              >
                {k}
              </span>
            ))}
          </div>
        </details>
      )}

      {!matching && locatorMatches.length > 0 && (
        <div className="space-y-3">
          {groupList.map((grp) => {
            const approvedCount = grp.items.filter((m) => matchStatuses[matchKey(m)] === "approved").length;
            const rejectedCount = grp.items.filter((m) => matchStatuses[matchKey(m)] === "rejected").length;
            const pendingCount = grp.items.length - approvedCount - rejectedCount;
            return (
              <div
                key={`${grp.scenarioId}::${grp.stepIdx}`}
                className="rounded-lg border border-slate-800 bg-slate-950/40"
              >
                {/* Grup başlığı */}
                <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-800 px-3 py-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="text-slate-500">Senaryo:</span>
                      <span className="text-slate-200 font-medium">{grp.scenarioTitle}</span>
                      <span className="text-slate-600">·</span>
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[11px] text-slate-300">
                        Adım #{grp.stepIdx + 1}
                      </span>
                      <span className="text-slate-600">·</span>
                      <span className="text-[11px] text-slate-500">
                        {grp.items.length} lokator önerisi
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      <span className="text-slate-600">Adım metni:</span> {grp.stepText}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="text-[11px] text-emerald-400">✓{approvedCount}</span>
                    <span className="text-[11px] text-slate-500">✗{rejectedCount}</span>
                    <span className="text-[11px] text-slate-600">·{pendingCount}</span>
                    {pendingCount > 0 && (
                      <>
                        <button
                          type="button"
                          onClick={() => setGroupStatus(grp.items, "approved")}
                          className="ml-1 rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[11px] text-emerald-300 hover:bg-emerald-500/20"
                          title="Bu adımdaki tüm önerileri onayla"
                        >
                          ✓ Adım
                        </button>
                        <button
                          type="button"
                          onClick={() => setGroupStatus(grp.items, "rejected")}
                          className="rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-[11px] text-slate-400 hover:border-slate-600"
                          title="Bu adımdaki tüm önerileri reddet"
                        >
                          ✗ Adım
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Aday lokator satırları */}
                <div className="divide-y divide-slate-800/60">
                  {grp.items.map((m) => {
                    const mk = matchKey(m);
                    const status = matchStatuses[mk] || "pending";
                    const rowCls =
                      status === "approved"
                        ? "bg-emerald-500/5"
                        : status === "rejected"
                        ? "opacity-50"
                        : "";
                    const confPct = Math.round((m.confidence || 0) * 100);
                    const confColor =
                      confPct >= 80 ? "text-emerald-400" : confPct >= 60 ? "text-amber-400" : "text-red-400";
                    const sourceBadge: Record<string, { cls: string; icon: string; title: string }> = {
                      llm:       { cls: "bg-sky-500/15 text-sky-300",         icon: "🤖", title: "AI semantik eşleştirme" },
                      heuristic: { cls: "bg-amber-500/15 text-amber-300",     icon: "📐", title: "Heuristic — anahtar kelime örtüşmesi (AI devre dışı)" },
                      manual:    { cls: "bg-emerald-500/15 text-emerald-300", icon: "👤", title: "Kullanıcı tarafından manuel seçildi" },
                    };
                    const sb = sourceBadge[m.source || "heuristic"] || sourceBadge.heuristic;
                    const otherKeysForStep = grp.items.map((im) => im.suggested_key);
                    const availableKeys = locatorFiles
                      .flatMap((f) => f.locators.map((l) => l.key))
                      .filter((k) => !otherKeysForStep.includes(k));
                    return (
                      <div key={mk} className={`relative px-3 py-2 transition ${rowCls}`}>
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-1.5 text-xs">
                              <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-300">
                                {m.element_phrase || "—"}
                              </span>
                              <span className="text-slate-600">→</span>
                              <button
                                type="button"
                                onClick={() => onJumpToLocator(m.suggested_key)}
                                className="rounded bg-blue-500/15 px-2 py-0.5 font-mono text-blue-300 hover:bg-blue-500/25 hover:underline"
                                title="Locator editöründe aç"
                              >
                                {m.suggested_key}
                              </button>
                              <span
                                className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${sb.cls}`}
                                title={sb.title}
                              >
                                {sb.icon}
                              </span>
                              <XPathBadge q={m.xpath_quality} />
                              <span className={`ml-auto font-mono text-[11px] ${confColor}`}>
                                %{confPct}
                              </span>
                            </div>
                            <div className="mt-1 font-mono text-[11px] text-slate-500 break-all">
                              {m.suggested_locator.type}={m.suggested_locator.value}
                            </div>
                            {m.reason && (
                              <p className="mt-0.5 text-[11px] text-slate-600 italic">{m.reason}</p>
                            )}
                          </div>
                          <div className="flex flex-col gap-1 shrink-0">
                            <button
                              type="button"
                              onClick={() => onSetMatchStatus(mk, "approved")}
                              aria-label={`${m.suggested_key} önerisini onayla`}
                              className={`rounded px-2.5 py-0.5 text-xs font-semibold transition ${
                                status === "approved"
                                  ? "bg-emerald-500 text-white"
                                  : "border border-emerald-500/40 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
                              }`}
                            >
                              ✓
                            </button>
                            <button
                              type="button"
                              onClick={() => onSetOverridePopoverKey(overridePopoverKey === mk ? null : mk)}
                              aria-label={`${m.suggested_key} için başka locator seç`}
                              className={`rounded px-2.5 py-0.5 text-xs font-semibold transition ${
                                overridePopoverKey === mk
                                  ? "bg-blue-500 text-white"
                                  : "border border-slate-700 bg-slate-800 text-slate-400 hover:border-blue-500 hover:text-blue-300"
                              }`}
                              title="Başka locator seç"
                            >
                              ↻
                            </button>
                            <button
                              type="button"
                              onClick={() => onSetMatchStatus(mk, "rejected")}
                              aria-label={`${m.suggested_key} önerisini reddet`}
                              className={`rounded px-2.5 py-0.5 text-xs font-semibold transition ${
                                status === "rejected"
                                  ? "bg-slate-600 text-white"
                                  : "border border-slate-700 bg-slate-800 text-slate-400 hover:border-slate-600"
                              }`}
                            >
                              ✗
                            </button>
                          </div>
                        </div>
                        {overridePopoverKey === mk && (
                          <div className="mt-2 rounded-lg border border-blue-500/30 bg-slate-950 p-2">
                            <div className="mb-1.5 flex items-center justify-between text-[11px]">
                              <span className="font-semibold text-blue-300">
                                Bu adıma başka bir locator ata
                              </span>
                              <button
                                type="button"
                                onClick={() => onSetOverridePopoverKey(null)}
                                className="text-slate-500 hover:text-slate-300"
                              >
                                ✕
                              </button>
                            </div>
                            {availableKeys.length === 0 ? (
                              <p className="text-[11px] text-slate-500">
                                Bu adımdaki diğer öneriler dışında locator kalmadı.
                              </p>
                            ) : (
                              <div className="max-h-32 overflow-y-auto space-y-0.5">
                                {availableKeys.map((k) => (
                                  <button
                                    key={k}
                                    type="button"
                                    onClick={() => onOverrideMatchLocator(mk, k)}
                                    className="w-full rounded px-2 py-1 text-left font-mono text-[11px] text-slate-300 hover:bg-blue-500/15 hover:text-blue-300"
                                  >
                                    {k}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}

          <div className="flex flex-wrap items-center gap-4 border-t border-slate-800 pt-3 text-xs">
            <span className="text-slate-500">
              {groupList.length} adım · {locatorMatches.length} öneri
            </span>
            <span className="text-emerald-400">
              ✓ {Object.values(matchStatuses).filter((s) => s === "approved").length} onaylı
            </span>
            <span className="text-slate-500">
              ✗ {Object.values(matchStatuses).filter((s) => s === "rejected").length} reddedildi
            </span>
            <span className="text-slate-600">
              {Object.values(matchStatuses).filter((s) => s === "pending").length} bekleniyor
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
