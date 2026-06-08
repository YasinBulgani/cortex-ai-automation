"use client";

import { useState } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  type GeneratedCaseDraft,
  useCreateDtRun,
  useDesignRuns,
  usePromoteCases,
} from "@/lib/hooks/use-mgmt-design";

const INP =
  "w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-disabled focus:border-teal-500/30 focus:outline-none transition-colors";

function TagList({
  items,
  onRemove,
  placeholder,
  onAdd,
  accent,
}: {
  items: string[];
  onRemove: (i: number) => void;
  placeholder: string;
  onAdd: (v: string) => void;
  accent: "teal" | "violet";
}) {
  const [draft, setDraft] = useState("");

  const commit = () => {
    const v = draft.trim();
    if (!v) return;
    onAdd(v);
    setDraft("");
  };

  const accentBorder =
    accent === "teal"
      ? "border-teal-500/40 text-teal-300"
      : "border-violet-500/40 text-violet-300";
  const accentDot = accent === "teal" ? "bg-teal-500/60" : "bg-violet-500/60";

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5 min-h-[28px]">
        {items.map((item, i) => (
          <span
            key={i}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[12px]",
              accentBorder,
            )}
          >
            <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", accentDot)} />
            {item}
            <button
              type="button"
              onClick={() => onRemove(i)}
              className="ml-0.5 text-fg-disabled hover:text-red-400 transition-colors"
            >
              ✕
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter") {
              e.preventDefault();
              commit();
            }
          }}
          placeholder={placeholder}
          className={cn(INP, "text-[12px]")}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={commit}
          disabled={!draft.trim()}
          className="shrink-0 px-3 py-2 text-[12px] text-fg-muted hover:text-fg"
        >
          Ekle
        </Button>
      </div>
    </div>
  );
}

export default function DtPage() {
  const projectId = useRouteParam("projectId") ?? "";

  const [conditions, setConditions] = useState<string[]>([]);
  const [actions, setActions]       = useState<string[]>([]);
  const [context, setContext]       = useState("");
  const [promoted, setPromoted]     = useState<Set<number>>(new Set());
  const [viewMode, setViewMode]     = useState<"list" | "matrix">("list");

  const runMut     = useCreateDtRun();
  const run        = runMut.data;
  const promoteMut = usePromoteCases(run?.id);
  const historyQ   = useDesignRuns({ technique: "DT", projectId: projectId || undefined });
  const recentRuns = (historyQ.data ?? []).slice(0, 5);

  const cases: GeneratedCaseDraft[] = run?.generated_cases ?? [];

  const handleRun = () => {
    runMut.mutate({
      project_id: projectId,
      conditions,
      actions,
      requirement_text: context.trim() || undefined,
    });
  };

  const handlePromote = (indexes: number[]) => {
    promoteMut.mutate(
      { case_indexes: indexes },
      { onSuccess: () => setPromoted(p => new Set([...p, ...indexes])) },
    );
  };

  const canRun = conditions.length > 0 && actions.length > 0 && !runMut.isPending;
  const maxRules = conditions.length > 0 ? Math.pow(2, conditions.length) : 0;

  return (
    <div className="min-h-full bg-surface-base px-6 py-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[15px] font-semibold text-fg">Decision Table</h1>
          <p className="mt-0.5 text-[12px] text-fg-subtle">
            Koşul / aksiyon kombinasyonlarından otomatik test senaryosu üret
          </p>
        </div>
        {run && (
          <span className="text-[11px] text-fg-disabled">
            {cases.length} case üretildi · {promoted.size} kaydedildi
          </span>
        )}
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        {/* ── Form ────────────────────────────────────────────────────────── */}
        <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-5">

          {/* Conditions */}
          <div className="space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">
              Koşullar
            </p>
            <p className="text-[11px] text-fg-disabled">
              Her bir giriş koşulunu ekle (örn: &quot;Kullanıcı giriş yapmış&quot;, &quot;Bakiye &gt; 0&quot;)
            </p>
            <TagList
              items={conditions}
              onRemove={i => setConditions(c => c.filter((_, j) => j !== i))}
              onAdd={v => setConditions(c => [...c, v])}
              placeholder="Koşul ekle, Enter ile onayla…"
              accent="teal"
            />
          </div>

          {/* Actions */}
          <div className="space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">
              Aksiyonlar
            </p>
            <p className="text-[11px] text-fg-disabled">
              Beklenen her aksiyon/sonucu ekle (örn: &quot;Ödeme gerçekleşir&quot;, &quot;Hata mesajı göster&quot;)
            </p>
            <TagList
              items={actions}
              onRemove={i => setActions(a => a.filter((_, j) => j !== i))}
              onAdd={v => setActions(a => [...a, v])}
              placeholder="Aksiyon ekle, Enter ile onayla…"
              accent="violet"
            />
          </div>

          <textarea
            value={context}
            onChange={e => setContext(e.target.value)}
            rows={2}
            placeholder="Requirement context (opsiyonel)…"
            className={cn(INP, "resize-none")}
          />

          <Button
            type="button"
            variant="primary"
            onClick={handleRun}
            disabled={!canRun}
            className="w-full rounded-xl py-2.5 text-[13px] font-medium"
          >
            {runMut.isPending ? "Üretiliyor…" : "DT Çalıştır"}
          </Button>

          {conditions.length === 0 && actions.length === 0 && (
            <p className="text-center text-[11px] text-fg-disabled">
              En az 1 koşul ve 1 aksiyon eklemek gerekiyor
            </p>
          )}
        </div>

        {/* ── Results ─────────────────────────────────────────────────────── */}
        <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">
              Üretilen Senaryolar
            </p>
            {run && cases.length > 0 && (
              <div className="flex rounded-lg border border-border overflow-hidden text-[10px]">
                <button onClick={() => setViewMode("list")} className={cn("px-2.5 py-1 transition-colors", viewMode === "list" ? "bg-teal-500/15 text-teal-400 font-semibold" : "text-fg-muted hover:text-fg")}>Liste</button>
                <button onClick={() => setViewMode("matrix")} className={cn("px-2.5 py-1 border-l border-border transition-colors", viewMode === "matrix" ? "bg-teal-500/15 text-teal-400 font-semibold" : "text-fg-muted hover:text-fg")}>Tablo</button>
              </div>
            )}
          </div>

          {/* Decision table size preview */}
          {conditions.length > 0 && actions.length > 0 && !run && (
            <div className="rounded-lg border border-border bg-surface-overlay/30 p-3">
              <p className="text-[11px] text-fg-disabled font-medium mb-1">Tablo Özeti</p>
              <p className="text-[11px] text-fg-subtle">
                {conditions.length} koşul × {actions.length} aksiyon ={" "}
                <span className="text-teal-400">maks {maxRules} kural</span>
              </p>
            </div>
          )}

          {!run ? (
            <div className="py-12 text-center text-[13px] text-fg-disabled">
              Henüz çalıştırılmadı
            </div>
          ) : cases.length === 0 ? (
            <div className="py-8 text-center text-[13px] text-fg-disabled">
              Senaryo üretilemedi
            </div>
          ) : viewMode === "matrix" ? (
            /* ── Matrix (Decision Table) View ─────────────────────────────── */
            <div className="overflow-auto max-h-96">
              <table className="w-full border-collapse text-[11px]">
                <thead>
                  <tr>
                    <th className="border border-border bg-surface-overlay/50 px-2 py-1.5 text-left text-fg-subtle whitespace-nowrap">#</th>
                    {conditions.map(cond => (
                      <th key={cond} className="border border-border bg-teal-500/10 px-2 py-1.5 text-left text-teal-400 whitespace-nowrap max-w-[100px]">
                        <span className="line-clamp-1">{cond}</span>
                      </th>
                    ))}
                    {actions.map(act => (
                      <th key={act} className="border border-border bg-violet-500/10 px-2 py-1.5 text-left text-violet-400 whitespace-nowrap max-w-[100px]">
                        <span className="line-clamp-1">{act}</span>
                      </th>
                    ))}
                    <th className="border border-border bg-surface-overlay/50 px-2 py-1.5 text-left text-fg-subtle whitespace-nowrap">Beklenen</th>
                    <th className="border border-border bg-surface-overlay/50 px-2 py-1.5 text-fg-subtle whitespace-nowrap">Aksiyon</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map((c, i) => {
                    const inp = c.inputs as Record<string, unknown>;
                    const isPromoted = promoted.has(i);
                    return (
                      <tr key={i} className={cn("transition-colors", isPromoted ? "bg-emerald-950/20" : "hover:bg-surface-overlay/30")}>
                        <td className="border border-border px-2 py-1 text-fg-disabled font-mono">{i + 1}</td>
                        {conditions.map(cond => {
                          const val = inp[cond];
                          const isTrue = val === true || val === "true" || val === "Y" || val === "yes";
                          const isFalse = val === false || val === "false" || val === "N" || val === "no";
                          return (
                            <td key={cond} className="border border-border px-2 py-1 text-center">
                              {isTrue ? <span className="text-teal-400 font-bold">Y</span>
                               : isFalse ? <span className="text-fg-disabled">N</span>
                               : val != null ? <span className="text-fg-muted font-mono text-[10px]">{String(val)}</span>
                               : <span className="text-fg-disabled">—</span>}
                            </td>
                          );
                        })}
                        {actions.map(act => {
                          const val = inp[act];
                          const isTrue = val === true || val === "Y" || val === "X" || val === "yes" || val === 1;
                          return (
                            <td key={act} className="border border-border px-2 py-1 text-center">
                              {isTrue ? <span className="text-violet-400 font-bold">✓</span>
                               : val != null ? <span className="text-fg-muted font-mono text-[10px]">{String(val)}</span>
                               : <span className="text-fg-disabled">—</span>}
                            </td>
                          );
                        })}
                        <td className="border border-border px-2 py-1 text-fg-muted max-w-[120px]">
                          <span className="line-clamp-1">{c.expected}</span>
                        </td>
                        <td className="border border-border px-2 py-1 text-center">
                          {isPromoted ? (
                            <span className="text-emerald-500/70 text-[10px]">✓ Kaydedildi</span>
                          ) : (
                            <button type="button" onClick={() => handlePromote([i])}
                              className="rounded border border-border px-1.5 py-0.5 text-[10px] text-fg-subtle hover:text-teal-400 transition-colors">
                              Kaydet
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            /* ── List View ─────────────────────────────────────────────────── */
            <>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {cases.map((c, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 rounded-lg border border-border bg-surface-overlay/30 px-3 py-2.5"
                  >
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500/60" />
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] text-fg">{c.name}</p>
                      {c.rationale && (
                        <p className="mt-0.5 text-[11px] text-fg-disabled line-clamp-2">
                          {c.rationale}
                        </p>
                      )}
                    </div>
                    {promoted.has(i) ? (
                      <span className="shrink-0 text-[11px] text-emerald-500/70">✓</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handlePromote([i])}
                        className="shrink-0 rounded border border-border px-2 py-0.5 text-[11px] text-fg-subtle hover:text-teal-400 transition-colors"
                      >
                        Kaydet
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
          {run && cases.length > 0 && (
            <Button
              type="button"
              variant="outline"
              onClick={() => handlePromote(cases.map((_, i) => i).filter(i => !promoted.has(i)))}
              disabled={promoteMut.isPending || promoted.size === cases.length}
              className="w-full rounded-xl py-2 text-[12px] text-fg-muted hover:text-fg"
            >
              {promoteMut.isPending ? "Kaydediliyor…" : promoted.size === cases.length ? "Tümü Kaydedildi ✓" : "Tümünü Repository'ye Kaydet"}
            </Button>
          )}
        </div>
      </div>

      {/* ── History ───────────────────────────────────────────────────────── */}
      <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">
          Önceki Analizler
        </p>
        {historyQ.isLoading ? (
          <div className="py-6 text-center text-[12px] text-fg-disabled">Yükleniyor…</div>
        ) : recentRuns.length === 0 ? (
          <div className="py-6 text-center text-[12px] text-fg-disabled">
            Henüz geçmiş analiz yok
          </div>
        ) : (
          <div className="space-y-2">
            {recentRuns.map(r => {
              const condCount = Array.isArray(
                (r.input_spec as { conditions?: unknown[] }).conditions,
              )
                ? (r.input_spec as { conditions: unknown[] }).conditions.length
                : 0;
              return (
                <div
                  key={r.id}
                  className="flex items-center gap-3 rounded-lg border border-border bg-surface-overlay/30 px-3 py-2.5"
                >
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500/40" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] text-fg-muted">
                      {new Date(r.created_at).toLocaleString("tr-TR", {
                        dateStyle: "short",
                        timeStyle: "short",
                      })}
                    </p>
                    <p className="text-[11px] text-fg-disabled">
                      {condCount} koşul · {r.generated_cases.length} case üretildi
                    </p>
                  </div>
                  <a
                    href={`/p/${projectId}/management/repository`}
                    className="shrink-0 rounded border border-border px-2 py-0.5 text-[11px] text-fg-subtle hover:text-teal-400 transition-colors"
                  >
                    Case&apos;leri Gör
                  </a>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
