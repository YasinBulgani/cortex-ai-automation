"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  useDslActions,
  useDslCategories,
  useDslFeedback,
  useDslGenerateAiAliases,
  useDslIndexInfo,
  useDslSearch,
  useDslStats,
  useDslSuggest,
  type DslAction,
  type DslSearchHit,
} from "@/lib/hooks/use-dsl";

type LangFilter = "all" | "tr" | "en";
type SearchMode = "substring" | "ai";

const CATEGORY_LABELS: Record<string, string> = {
  ui: "UI",
  api: "API",
  assert: "Doğrulama",
  bgts: "Bankacılık Domain",
  setup: "Setup",
  uncategorized: "Diğer",
};

const INPUT_CLS =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50";

const BADGE_CLS =
  "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium";

const LANG_BADGE: Record<string, string> = {
  tr: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
  en: "border-blue-500/30 bg-blue-500/10 text-blue-400",
  meta: "border-slate-600 bg-slate-800 text-slate-300",
};

const IMPL_BADGE: Record<string, string> = {
  python: "border-yellow-500/30 bg-yellow-500/10 text-yellow-400",
  java: "border-orange-500/30 bg-orange-500/10 text-orange-400",
  typescript: "border-sky-500/30 bg-sky-500/10 text-sky-400",
};

function ActionCard({
  action,
  highlight,
  onOpen,
  hit,
  onVote,
  votedAs,
}: {
  action: DslAction;
  highlight?: string;
  onOpen: (a: DslAction) => void;
  hit?: DslSearchHit;
  onVote?: (vote: "up" | "down") => void;
  votedAs?: "up" | "down" | null;
}) {
  const firstTr = action.aliases?.tr?.[0];
  const firstEn = action.aliases?.en?.[0];
  const primary = firstTr ?? firstEn ?? action.description;
  const score = typeof hit?.score === "number" ? hit.score : null;
  const source = hit?.source ?? null;
  const reason = hit?.reason ?? null;

  return (
    <div
      className="group flex w-full flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-left transition-colors hover:border-blue-500/40 hover:bg-slate-900"
      data-testid={`dsl-action-card-${action.id}`}
    >
      <button
        type="button"
        onClick={() => onOpen(action)}
        className="flex flex-col gap-2 text-left"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className={`${BADGE_CLS} border-slate-700 bg-slate-800 text-slate-300`}>
                {action.category}
              </span>
              {Object.keys(action.implementations ?? {}).map((lang) => (
                <span
                  key={lang}
                  className={`${BADGE_CLS} ${IMPL_BADGE[lang] ?? "border-slate-600 bg-slate-800 text-slate-300"}`}
                >
                  {lang}
                </span>
              ))}
              {source && source !== "lexical" && (
                <span
                  className={`${BADGE_CLS} ${
                    source === "semantic"
                      ? "border-violet-500/30 bg-violet-500/10 text-violet-300"
                      : source === "hybrid"
                      ? "border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-300"
                      : "border-amber-500/30 bg-amber-500/10 text-amber-300"
                  }`}
                  title={`Kaynak: ${source}`}
                >
                  AI · {source}
                </span>
              )}
            </div>
            <div className="mt-1 font-mono text-xs text-slate-400 truncate">{action.id}</div>
          </div>
          {score !== null && (
            <div className="flex min-w-[72px] shrink-0 flex-col items-end gap-1">
              <span
                className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                  score >= 0.75
                    ? "bg-emerald-500/15 text-emerald-300"
                    : score >= 0.5
                    ? "bg-blue-500/15 text-blue-300"
                    : "bg-slate-700/60 text-slate-400"
                }`}
              >
                {(score * 100).toFixed(0)}%
              </span>
              <div className="h-1 w-16 overflow-hidden rounded-full bg-slate-800">
                <div
                  className={`h-full ${
                    score >= 0.75
                      ? "bg-emerald-400"
                      : score >= 0.5
                      ? "bg-blue-400"
                      : "bg-slate-500"
                  }`}
                  style={{ width: `${Math.max(6, Math.round(score * 100))}%` }}
                />
              </div>
            </div>
          )}
        </div>

        <div className="font-mono text-sm text-white">
          {highlight ? renderHighlight(primary, highlight) : primary}
        </div>

        {action.description && action.description !== primary && (
          <div className="text-xs text-slate-400 line-clamp-2">{action.description}</div>
        )}

        {reason && (
          <div className="rounded-md border border-blue-500/20 bg-blue-500/5 p-2 text-[11px] text-blue-200/90">
            💡 {reason}
          </div>
        )}
      </button>

      {onVote && (
        <div className="flex items-center justify-between border-t border-slate-800 pt-2 text-[11px] text-slate-500">
          <span>Bu sonuç yardımcı oldu mu?</span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onVote("up");
              }}
              className={`rounded-md border px-2 py-0.5 transition-colors ${
                votedAs === "up"
                  ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-300"
                  : "border-slate-700 bg-slate-900 text-slate-400 hover:border-emerald-500/40 hover:text-emerald-300"
              }`}
              data-testid={`dsl-vote-up-${action.id}`}
              aria-label="Bu sonuç yararlı"
            >
              👍
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onVote("down");
              }}
              className={`rounded-md border px-2 py-0.5 transition-colors ${
                votedAs === "down"
                  ? "border-rose-500/50 bg-rose-500/15 text-rose-300"
                  : "border-slate-700 bg-slate-900 text-slate-400 hover:border-rose-500/40 hover:text-rose-300"
              }`}
              data-testid={`dsl-vote-down-${action.id}`}
              aria-label="Bu sonuç yararsız"
            >
              👎
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function AiStatusBanner({
  indexReady,
  rows,
  model,
  activeMode,
}: {
  indexReady: boolean;
  rows: number;
  model: string;
  activeMode: string | null | undefined;
}) {
  const isFallback = activeMode === "lexical_fallback";
  if (indexReady && !isFallback) {
    return (
      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-violet-500/20 bg-violet-500/5 px-3 py-2 text-[11px] text-violet-200/90">
        <span>🤖 AI arama aktif</span>
        <span className="text-violet-300/60">·</span>
        <span>Model: <span className="font-mono">{model || "bge-m3"}</span></span>
        <span className="text-violet-300/60">·</span>
        <span>{rows} satır indekslenmiş</span>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-200/90">
      <span>⚠ AI indeksi henüz hazır değil — şu an alias araması kullanılıyor.</span>
      <span className="text-amber-200/60">
        Index'i oluşturmak için: <span className="font-mono">/api/v1/dsl/index/rebuild</span>
      </span>
    </div>
  );
}

function renderHighlight(text: string, q: string) {
  if (!q) return text;
  const idx = text.toLowerCase().indexOf(q.toLowerCase());
  if (idx < 0) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-yellow-500/30 text-yellow-200">{text.slice(idx, idx + q.length)}</mark>
      {text.slice(idx + q.length)}
    </>
  );
}

function AiAliasSuggestSection({ actionId }: { actionId: string }) {
  const gen = useDslGenerateAiAliases();
  const [lang, setLang] = useState<"tr" | "en">("tr");
  const [count, setCount] = useState<number>(3);
  const [lastResult, setLastResult] = useState<
    { accepted: string[]; rejected: string[]; reason?: string | null; lang: string } | null
  >(null);

  async function onGenerate() {
    try {
      const res = await gen.mutateAsync({ actionId, lang, count });
      setLastResult({
        accepted: res.accepted,
        rejected: res.rejected,
        reason: res.reason,
        lang,
      });
    } catch (err) {
      setLastResult({
        accepted: [],
        rejected: [],
        reason: err instanceof Error ? err.message : String(err),
        lang,
      });
    }
  }

  return (
    <section className="mt-5 rounded-lg border border-violet-500/20 bg-violet-500/5 p-3">
      <h3 className="mb-2 flex items-center gap-2 font-semibold text-violet-200">
        <span>🤖</span>
        <span>AI Alias Önerileri</span>
      </h3>
      <p className="mb-3 text-[11px] text-violet-300/70">
        Ollama, mevcut alias'lara benzer olmayan yeni adaylar üretir. Kabul
        edilenler admin onayı bekleyen &quot;pending&quot; öneri olarak
        İnceleme sayfasına düşer.
      </p>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-1 text-xs text-slate-300">
          <span>Dil:</span>
          <select
            className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white"
            value={lang}
            onChange={(e) => setLang(e.target.value as "tr" | "en")}
            aria-label="Alias dili"
            title="Alias dili"
          >
            <option value="tr">Türkçe</option>
            <option value="en">İngilizce</option>
          </select>
        </label>
        <label className="flex items-center gap-1 text-xs text-slate-300">
          <span>Adet:</span>
          <input
            type="number"
            min={1}
            max={10}
            value={count}
            onChange={(e) => setCount(Math.max(1, Math.min(10, Number(e.target.value) || 3)))}
            aria-label="Kaç alias üretilsin"
            title="Kaç alias üretilsin (1-10)"
            className="w-14 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white"
          />
        </label>
        <button
          type="button"
          onClick={onGenerate}
          disabled={gen.isPending}
          className="rounded-md border border-violet-500/40 bg-violet-500/10 px-3 py-1 text-xs text-violet-200 hover:bg-violet-500/20 disabled:opacity-40"
          data-testid="dsl-ai-alias-generate"
        >
          {gen.isPending ? "Düşünüyor…" : "AI'dan üret"}
        </button>
      </div>

      {lastResult && (
        <div className="mt-2 space-y-2 text-xs">
          {lastResult.accepted.length > 0 && (
            <div>
              <div className="mb-1 font-semibold text-emerald-300">
                ✓ Kabul edilen ({lastResult.lang}) — {lastResult.accepted.length}
              </div>
              <ul className="space-y-1">
                {lastResult.accepted.map((a) => (
                  <li
                    key={a}
                    className="rounded-md border border-emerald-500/20 bg-emerald-500/5 px-2 py-1.5 font-mono text-emerald-100"
                  >
                    {a}
                  </li>
                ))}
              </ul>
              <p className="mt-1 text-[11px] text-emerald-300/70">
                İnceleme sayfasında &quot;Pending&quot; altında görünecek.
              </p>
            </div>
          )}
          {lastResult.rejected.length > 0 && (
            <div>
              <div className="mb-1 font-semibold text-slate-400">
                ⊘ Mevcuda benzer bulunduğu için elenenler — {lastResult.rejected.length}
              </div>
              <ul className="space-y-1">
                {lastResult.rejected.map((a) => (
                  <li key={a} className="text-slate-500 line-through">
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {lastResult.reason && (
            <div className="text-[11px] text-amber-200">
              ⚠ {lastResult.reason}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function ActionDetail({
  action,
  onClose,
}: {
  action: DslAction;
  onClose: () => void;
}) {
  const [copied, setCopied] = useState<string | null>(null);

  async function copy(text: string, key: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      /* yoksay */
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end bg-black/60 p-0 sm:p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="flex h-full w-full max-w-2xl flex-col overflow-hidden rounded-none border border-slate-800 bg-slate-950 shadow-2xl sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-800 p-5">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`${BADGE_CLS} border-slate-700 bg-slate-800 text-slate-300`}>
                {action.category}
              </span>
              {action.tags?.slice(0, 5).map((t) => (
                <span
                  key={t}
                  className={`${BADGE_CLS} border-slate-700 bg-slate-800 text-slate-400`}
                >
                  #{t}
                </span>
              ))}
            </div>
            <h2 className="mt-2 font-mono text-base font-semibold text-white break-all">
              {action.id}
            </h2>
            {action.description && (
              <p className="mt-1 text-sm text-slate-400">{action.description}</p>
            )}
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <button
              type="button"
              className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-300 hover:bg-slate-800"
              onClick={onClose}
              aria-label="Kapat"
            >
              ×
            </button>
            <Link
              href={`/dsl-catalog/editor/${encodeURIComponent(action.id)}`}
              className="rounded-lg border border-blue-500/40 bg-blue-500/10 px-2.5 py-1 text-xs text-blue-200 hover:bg-blue-500/20"
              data-testid={`dsl-edit-${action.id}`}
            >
              ✎ Düzenle
            </Link>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5 text-sm">
          <section>
            <h3 className="mb-2 font-semibold text-slate-200">Alias'lar</h3>
            {Object.entries(action.aliases ?? {}).map(([lang, arr]) => (
              <div key={lang} className="mb-3">
                <div className="mb-1 text-xs uppercase tracking-wider text-slate-500">{lang}</div>
                <ul className="space-y-1">
                  {arr.map((alias) => (
                    <li key={alias} className="flex items-start gap-2">
                      <code className="flex-1 rounded-md border border-slate-800 bg-slate-900 px-2 py-1.5 font-mono text-xs text-white">
                        {alias}
                      </code>
                      <button
                        type="button"
                        className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
                        onClick={() => copy(alias, `${lang}:${alias}`)}
                      >
                        {copied === `${lang}:${alias}` ? "✓" : "Kopyala"}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </section>

          <AiAliasSuggestSection actionId={action.id} />

          {action.parameters?.length > 0 && (
            <section className="mt-4">
              <h3 className="mb-2 font-semibold text-slate-200">Parametreler</h3>
              <div className="overflow-hidden rounded-lg border border-slate-800">
                <table className="w-full text-xs">
                  <thead className="bg-slate-900 text-slate-400">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">Ad</th>
                      <th className="px-3 py-2 text-left font-medium">Tip</th>
                      <th className="px-3 py-2 text-left font-medium">Zorunlu</th>
                      <th className="px-3 py-2 text-left font-medium">Açıklama</th>
                    </tr>
                  </thead>
                  <tbody>
                    {action.parameters.map((p) => (
                      <tr key={p.name} className="border-t border-slate-800">
                        <td className="px-3 py-2 font-mono text-white">{p.name}</td>
                        <td className="px-3 py-2 text-slate-300">{p.type}</td>
                        <td className="px-3 py-2 text-slate-300">{p.required === false ? "—" : "✓"}</td>
                        <td className="px-3 py-2 text-slate-400">{p.description ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <section className="mt-4">
            <h3 className="mb-2 font-semibold text-slate-200">Implementation'lar</h3>
            <div className="space-y-2">
              {Object.entries(action.implementations ?? {}).map(([lang, impl]) => (
                <div key={lang} className="rounded-lg border border-slate-800 bg-slate-900 p-3">
                  <div className="flex items-center justify-between">
                    <span className={`${BADGE_CLS} ${IMPL_BADGE[lang] ?? ""}`}>{lang}</span>
                    <code className="text-xs text-slate-400">
                      {impl.function ?? impl.method ?? impl.class ?? "—"}
                    </code>
                  </div>
                  <div className="mt-1 font-mono text-xs text-slate-300 break-all">
                    {impl.source_file}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {action.notes && (
            <section className="mt-4 rounded-lg border border-amber-900/40 bg-amber-500/10 p-3 text-xs text-amber-200">
              {action.notes}
            </section>
          )}

          {action.examples?.length > 0 && (
            <section className="mt-4">
              <h3 className="mb-2 font-semibold text-slate-200">Örnekler</h3>
              {action.examples.map((ex, i) => (
                <pre
                  key={i}
                  className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900 p-3 font-mono text-xs text-slate-200"
                >
                  {ex}
                </pre>
              ))}
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

export function DslCatalogView({
  title = "DSL Sözlüğü",
  forceCategory,
}: {
  title?: string;
  /**
   * Verildiğinde kategori filtresi bu değere kilitlenir ve sol panelde
   * yalnızca bu üst kategorinin alt ağacı gösterilir. "/dsl-catalog/mobile"
   * gibi özel sekmelerde kullanılır.
   */
  forceCategory?: string;
} = {}) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string | null>(forceCategory ?? null);
  const [langFilter, setLangFilter] = useState<LangFilter>("all");
  const [selected, setSelected] = useState<DslAction | null>(null);
  const [page, setPage] = useState(1);
  const [searchMode, setSearchMode] = useState<SearchMode>("substring");
  const [votes, setVotes] = useState<Record<string, "up" | "down">>({});

  const stats = useDslStats();
  const categories = useDslCategories();
  const feedback = useDslFeedback();
  const indexInfo = useDslIndexInfo(searchMode === "ai");

  const isSearching = search.trim().length >= 2;
  const aiEnabled = searchMode === "ai";

  // Substring modu — hızlı alias araması
  const searchResults = useDslSearch(
    isSearching && !aiEnabled ? search : "",
    langFilter === "all" ? undefined : langFilter,
    100,
  );
  // AI modu — doğal dil öneri (auto: index varsa hybrid, yoksa lexical fallback)
  const aiSuggest = useDslSuggest(search, {
    enabled: isSearching && aiEnabled,
    mode: "auto",
    limit: 25,
    minLength: 2,
  });

  const listQuery = useDslActions({
    category: category ?? undefined,
    lang: langFilter === "all" ? undefined : langFilter,
    page,
    page_size: 50,
  });

  const activeHits = useMemo(() => {
    if (!isSearching) return [];
    return aiEnabled ? aiSuggest.data?.items ?? [] : searchResults.data?.items ?? [];
  }, [isSearching, aiEnabled, aiSuggest.data, searchResults.data]);

  const activeActions: DslAction[] = useMemo(() => {
    if (isSearching) return activeHits.map((h) => h.action);
    return listQuery.data?.items ?? [];
  }, [isSearching, activeHits, listQuery.data]);

  const hitByActionId = useMemo(() => {
    const m = new Map<string, DslSearchHit>();
    for (const hit of activeHits) m.set(hit.action.id, hit);
    return m;
  }, [activeHits]);

  const activeTotal = isSearching
    ? aiEnabled
      ? aiSuggest.data?.total ?? 0
      : searchResults.data?.total ?? 0
    : listQuery.data?.total ?? 0;

  const activeMode = aiEnabled ? aiSuggest.data?.mode ?? null : null;
  const isAiLoading = aiEnabled && aiSuggest.isFetching;

  function handleVote(actionId: string, vote: "up" | "down") {
    // Optimistic işaretleme — backend hata verirse geri alınır
    setVotes((prev) => ({ ...prev, [actionId]: vote }));
    const hit = hitByActionId.get(actionId);
    feedback.mutate(
      {
        query: search.trim(),
        action_id: actionId,
        vote,
        search_mode: (hit?.source ?? "lexical") as
          | "lexical"
          | "semantic"
          | "hybrid"
          | "llm_rerank",
        rank: activeActions.findIndex((a) => a.id === actionId),
        raw_score: typeof hit?.score === "number" ? hit.score : undefined,
      },
      {
        onError: () => {
          setVotes((prev) => {
            const { [actionId]: _, ...rest } = prev;
            return rest;
          });
        },
      },
    );
  }

  const topCats = categories.data
    ? Array.from(
        categories.data
          .filter((c) => !forceCategory || c.top_level === forceCategory)
          .reduce((m, c) => {
            m.set(c.top_level, (m.get(c.top_level) ?? 0) + c.count);
            return m;
          }, new Map<string, number>()),
      )
        .map(([id, count]) => ({ id, count }))
        .sort((a, b) => b.count - a.count)
    : [];

  const subCats = categories.data?.filter((c) => {
    if (!category) return false;
    return c.top_level === category || c.id.startsWith(category + ".");
  });

  return (
    <div className="flex h-full flex-col gap-4 p-4 sm:p-6">
      {/* Header */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">{title}</h1>
          <p className="mt-1 text-sm text-slate-400">
            {stats.data ? (
              <>
                <span className="font-semibold text-white">{stats.data.total}</span> cümlecik,{" "}
                <span className="text-emerald-400">{stats.data.aliases.tr}</span> Türkçe +{" "}
                <span className="text-blue-400">{stats.data.aliases.en}</span> İngilizce alias
              </>
            ) : (
              "Yükleniyor..."
            )}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          {stats.data?.loaded_at && (
            <span>Yüklendi: {new Date(stats.data.loaded_at).toLocaleString()}</span>
          )}
          <Link
            href="/dsl-catalog/editor/new"
            className="rounded-lg border border-blue-500/40 bg-blue-500/10 px-3 py-1.5 text-sm text-blue-200 hover:bg-blue-500/20"
            data-testid="dsl-new-action"
          >
            + Yeni Cümlecik
          </Link>
          <Link
            href="/dsl-catalog/review"
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
            data-testid="dsl-review-link"
          >
            İnceleme
          </Link>
        </div>
      </header>

      {/* Filters */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/50 p-3 sm:flex-row sm:items-center">
        <div className="flex-1">
          <div className="relative">
            <input
              type="search"
              className={INPUT_CLS + " pr-10"}
              placeholder={
                aiEnabled
                  ? "Doğal dil: 'login butonuna tıkla ve anasayfa açılsın'"
                  : "Ara: 'tikla', 'yazar', 'I click on', 'onay'..."
              }
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              data-testid="dsl-search-input"
            />
            {isAiLoading && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-violet-300">
                ⌛ AI düşünüyor…
              </span>
            )}
          </div>
        </div>

        {/* Arama modu toggle */}
        <div className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 p-0.5">
          <button
            type="button"
            onClick={() => {
              setSearchMode("substring");
              setPage(1);
            }}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              searchMode === "substring"
                ? "bg-slate-700 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
            data-testid="dsl-search-mode-substring"
            title="Alias metinlerinde substring araması (hızlı)"
          >
            Alias
          </button>
          <button
            type="button"
            onClick={() => {
              setSearchMode("ai");
              setPage(1);
            }}
            className={`flex items-center gap-1 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              searchMode === "ai"
                ? "bg-violet-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
            data-testid="dsl-search-mode-ai"
            title="Doğal dil — Ollama tabanlı anlamsal arama"
          >
            <span>🤖</span>
            <span>AI</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          {(["all", "tr", "en"] as LangFilter[]).map((l) => (
            <button
              type="button"
              key={l}
              onClick={() => {
                setLangFilter(l);
                setPage(1);
              }}
              className={`rounded-lg border px-3 py-1.5 text-sm ${
                langFilter === l
                  ? "border-blue-500/50 bg-blue-500/10 text-blue-200"
                  : "border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800"
              }`}
              data-testid={`dsl-lang-${l}`}
            >
              {l === "all" ? "Hepsi" : l.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* AI modunda index durumu + mod göstergesi */}
      {aiEnabled && (
        <AiStatusBanner
          indexReady={indexInfo.data?.ready ?? false}
          rows={indexInfo.data?.rows ?? 0}
          model={indexInfo.data?.model ?? "-"}
          activeMode={activeMode}
        />
      )}

      <div className="flex flex-1 min-h-0 flex-col gap-4 lg:flex-row">
        {/* Sol: Kategori ağacı */}
        <aside className="flex-shrink-0 rounded-xl border border-slate-800 bg-slate-900/50 p-3 lg:w-60">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Kategoriler
          </div>
          <ul className="space-y-0.5 text-sm">
            <li>
              <button
                type="button"
                onClick={() => {
                  setCategory(null);
                  setPage(1);
                }}
                className={`flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left ${
                  category === null
                    ? "bg-blue-500/10 text-blue-200"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                <span>Hepsi</span>
                <span className="text-xs text-slate-500">{stats.data?.total ?? "—"}</span>
              </button>
            </li>
            {topCats.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => {
                    setCategory(c.id);
                    setPage(1);
                  }}
                  className={`flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left ${
                    category === c.id
                      ? "bg-blue-500/10 text-blue-200"
                      : "text-slate-300 hover:bg-slate-800"
                  }`}
                  data-testid={`dsl-cat-${c.id}`}
                >
                  <span>{CATEGORY_LABELS[c.id] ?? c.id}</span>
                  <span className="text-xs text-slate-500">{c.count}</span>
                </button>
                {category === c.id && subCats && subCats.length > 0 && (
                  <ul className="mt-1 ml-2 space-y-0.5 border-l border-slate-800 pl-2 text-xs">
                    {subCats.map((s) => (
                      <li key={s.id}>
                        <button
                          type="button"
                          onClick={() => {
                            setCategory(s.id);
                            setPage(1);
                          }}
                          className={`flex w-full items-center justify-between rounded px-2 py-1 text-left ${
                            category === s.id
                              ? "text-blue-200"
                              : "text-slate-400 hover:text-slate-200"
                          }`}
                        >
                          <span className="truncate">{s.id}</span>
                          <span className="ml-2 text-slate-600">{s.count}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </aside>

        {/* Sağ: Cümlecik listesi */}
        <main className="flex flex-1 min-h-0 flex-col">
          <div
            className="mb-2 flex items-center justify-between text-xs text-slate-500"
            data-testid="dsl-result-count"
          >
            <span>
              {isSearching
                ? `${activeTotal} sonuç — "${search}"`
                : `${activeTotal} cümlecik${category ? ` — ${category}` : ""}`}
            </span>
            {isSearching && aiEnabled && activeMode && (
              <span className="font-mono text-[10px] uppercase tracking-wider text-slate-600">
                mode: {activeMode}
              </span>
            )}
          </div>

          <div className="flex-1 overflow-y-auto pr-1">
            {activeActions.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center text-sm text-slate-400">
                {isSearching
                  ? "Bu aramaya uygun cümlecik bulunamadı."
                  : "Bu filtre için cümlecik yok."}
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-1 xl:grid-cols-2">
                {activeActions.map((a) => {
                  const hit = hitByActionId.get(a.id);
                  const canVote = isSearching && aiEnabled && !!hit;
                  return (
                    <ActionCard
                      key={a.id}
                      action={a}
                      highlight={isSearching ? search : undefined}
                      onOpen={setSelected}
                      hit={hit}
                      onVote={canVote ? (v) => handleVote(a.id, v) : undefined}
                      votedAs={votes[a.id] ?? null}
                    />
                  );
                })}
              </div>
            )}
          </div>

          {!isSearching && activeTotal > 50 && (
            <div className="mt-3 flex items-center justify-between text-sm text-slate-400">
              <button
                type="button"
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1 hover:bg-slate-800 disabled:opacity-40"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                ← Önceki
              </button>
              <span>
                Sayfa {page} / {Math.ceil(activeTotal / 50)}
              </span>
              <button
                type="button"
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1 hover:bg-slate-800 disabled:opacity-40"
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= Math.ceil(activeTotal / 50)}
              >
                Sonraki →
              </button>
            </div>
          )}
        </main>
      </div>

      {selected && <ActionDetail action={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
