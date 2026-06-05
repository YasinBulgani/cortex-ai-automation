"use client";

import { useState } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";
import {
  type GeneratedCaseDraft,
  useCreateDtRun,
  useDesignRuns,
  usePromoteCases,
} from "@/lib/hooks/use-mgmt-design";

const INP =
  "w-full rounded-lg border border-border bg-white/[0.03] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 focus:border-teal-500/30 focus:outline-none transition-colors";

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
              className="ml-0.5 text-slate-600 hover:text-red-400 transition-colors"
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
        <button
          type="button"
          onClick={commit}
          disabled={!draft.trim()}
          className="shrink-0 rounded-lg border border-border px-3 py-2 text-[12px] text-slate-400 hover:text-slate-200 disabled:opacity-40 transition-colors"
        >
          Ekle
        </button>
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
    <div className="min-h-full bg-bg px-6 py-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[15px] font-semibold text-slate-100">Decision Table</h1>
          <p className="mt-0.5 text-[12px] text-slate-500">
            Koşul / aksiyon kombinasyonlarından otomatik test senaryosu üret
          </p>
        </div>
        {run && (
          <span className="text-[11px] text-slate-600">
            {cases.length} case üretildi · {promoted.size} kaydedildi
          </span>
        )}
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        {/* ── Form ────────────────────────────────────────────────────────── */}
        <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-5">

          {/* Conditions */}
          <div className="space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
              Koşullar
            </p>
            <p className="text-[11px] text-slate-600">
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
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
              Aksiyonlar
            </p>
            <p className="text-[11px] text-slate-600">
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

          <button
            type="button"
            onClick={handleRun}
            disabled={!canRun}
            className="w-full rounded-xl bg-brand py-2.5 text-[13px] font-medium text-white hover:brightness-105 disabled:opacity-40 transition-colors"
          >
            {runMut.isPending ? "Üretiliyor…" : "DT Çalıştır"}
          </button>

          {conditions.length === 0 && actions.length === 0 && (
            <p className="text-center text-[11px] text-slate-700">
              En az 1 koşul ve 1 aksiyon eklemek gerekiyor
            </p>
          )}
        </div>

        {/* ── Results ─────────────────────────────────────────────────────── */}
        <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
            Üretilen Senaryolar
          </p>

          {/* Decision table size preview */}
          {conditions.length > 0 && actions.length > 0 && !run && (
            <div className="rounded-lg border border-border bg-white/[0.02] p-3">
              <p className="text-[11px] text-slate-600 font-medium mb-1">Tablo Özeti</p>
              <p className="text-[11px] text-slate-500">
                {conditions.length} koşul × {actions.length} aksiyon ={" "}
                <span className="text-teal-400">maks {maxRules} kural</span>
              </p>
            </div>
          )}

          {!run ? (
            <div className="py-12 text-center text-[13px] text-slate-600">
              Henüz çalıştırılmadı
            </div>
          ) : cases.length === 0 ? (
            <div className="py-8 text-center text-[13px] text-slate-600">
              Senaryo üretilemedi
            </div>
          ) : (
            <>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {cases.map((c, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 rounded-lg border border-border bg-white/[0.02] px-3 py-2.5"
                  >
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500/60" />
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] text-slate-300">{c.name}</p>
                      {c.rationale && (
                        <p className="mt-0.5 text-[11px] text-slate-600 line-clamp-2">
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
                        className="shrink-0 rounded border border-border px-2 py-0.5 text-[11px] text-slate-500 hover:text-teal-400 transition-colors"
                      >
                        Kaydet
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={() => handlePromote(cases.map((_, i) => i).filter(i => !promoted.has(i)))}
                disabled={promoteMut.isPending || promoted.size === cases.length}
                className="w-full rounded-xl border border-border py-2 text-[12px] text-slate-400 hover:text-slate-200 disabled:opacity-40 transition-colors"
              >
                {promoteMut.isPending ? "Kaydediliyor…" : "Tümünü Repository'ye Kaydet"}
              </button>
            </>
          )}
        </div>
      </div>

      {/* ── History ───────────────────────────────────────────────────────── */}
      <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
          Önceki Analizler
        </p>
        {historyQ.isLoading ? (
          <div className="py-6 text-center text-[12px] text-slate-600">Yükleniyor…</div>
        ) : recentRuns.length === 0 ? (
          <div className="py-6 text-center text-[12px] text-slate-600">
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
                  className="flex items-center gap-3 rounded-lg border border-border bg-white/[0.02] px-3 py-2.5"
                >
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500/40" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] text-slate-400">
                      {new Date(r.created_at).toLocaleString("tr-TR", {
                        dateStyle: "short",
                        timeStyle: "short",
                      })}
                    </p>
                    <p className="text-[11px] text-slate-600">
                      {condCount} koşul · {r.generated_cases.length} case üretildi
                    </p>
                  </div>
                  <a
                    href={`/p/${projectId}/management/repository`}
                    className="shrink-0 rounded border border-border px-2 py-0.5 text-[11px] text-slate-500 hover:text-teal-400 transition-colors"
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
