"use client";

import { useState } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  type DesignFieldSpec,
  type DesignRun,
  useCreatePairwiseRun,
  useDesignRuns,
  usePromoteCases,
} from "@/lib/hooks/use-mgmt-design";

const INP =
  "w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-disabled focus:border-brand/40 focus:outline-none transition-colors";

function emptyField(): DesignFieldSpec {
  return { name: "", data_type: "enum", min_value: null, max_value: null, allowed_set: null, nullable: false };
}

export default function PairwisePage() {
  const projectId = useRouteParam("projectId") ?? "";
  const [fields, setFields]   = useState<DesignFieldSpec[]>([emptyField(), emptyField()]);
  const [context, setContext] = useState("");
  const [promoted, setPromoted] = useState<Set<number>>(new Set());
  const [selectedHistory, setSelectedHistory] = useState<DesignRun | null>(null);
  const [viewMode, setViewMode] = useState<"list" | "matrix">("list");

  const runMut     = useCreatePairwiseRun();
  const run        = runMut.data;
  const promoteMut = usePromoteCases(run?.id);

  const { data: historyRuns = [] } = useDesignRuns({ technique: "PAIRWISE", projectId });
  const recentRuns = historyRuns.slice(0, 5);
  const displayCases = selectedHistory ? selectedHistory.generated_cases : (run?.generated_cases ?? []);

  const update = (i: number, patch: Partial<DesignFieldSpec>) =>
    setFields(f => f.map((x, idx) => idx === i ? { ...x, ...patch } : x));

  const submit = () => {
    const valid = fields.filter(f => f.name.trim() && Array.isArray(f.allowed_set) && (f.allowed_set as string[]).length >= 2);
    if (valid.length < 2) return;
    runMut.mutate({ project_id: projectId, fields: valid, requirement_text: context.trim() || undefined });
  };

  const promote = (indexes: number[]) => {
    promoteMut.mutate({ case_indexes: indexes }, {
      onSuccess: () => setPromoted(p => new Set([...p, ...indexes])),
    });
  };

  const isReady = fields.filter(f => f.name.trim() && Array.isArray(f.allowed_set) && (f.allowed_set as string[]).length >= 2).length >= 2;

  const totalCombinations = fields.reduce((acc, f) => {
    const vals = Array.isArray(f.allowed_set) ? (f.allowed_set as string[]).length : 0;
    return vals > 0 ? acc * vals : acc;
  }, 1);

  const cases = run?.generated_cases ?? [];

  return (
    <div className="min-h-full bg-surface-base px-6 py-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[15px] font-semibold text-fg">Pairwise (All-Pairs) Testing</h1>
          <p className="mt-0.5 text-[12px] text-fg-subtle">
            N parametre için tüm ikili kombinasyonları kapsayan minimum test seti oluştur
          </p>
        </div>
        {run && !selectedHistory && (
          <span className="text-[11px] text-fg-disabled">
            {cases.length} case · {totalCombinations} tam kombinasyon
          </span>
        )}
      </div>

      {/* How it works */}
      <div className="rounded-xl border border-brand/20 bg-brand/5 px-4 py-3 text-[11px] text-fg-muted space-y-1">
        <p className="font-semibold text-fg-muted">Nasıl Çalışır?</p>
        <p>Her parametre için olası değerleri tanımlayın. Pairwise algoritması, tüm ikili kombinasyonları kapsayan en az sayıda test case oluşturur.</p>
        <p className="text-fg-disabled">En az 2 parametre ve her parametre için en az 2 değer gereklidir.</p>
      </div>

      {/* Recent Runs */}
      {recentRuns.length > 0 && (
        <div className="rounded-xl border border-border bg-surface-raised p-4 space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Son Çalışmalar</p>
          <div className="flex flex-wrap gap-2">
            {recentRuns.map((r) => (
              <button
                key={r.id}
                type="button"
                onClick={() => setSelectedHistory(prev => prev?.id === r.id ? null : r)}
                className={cn(
                  "flex items-center gap-2 rounded-lg border px-3 py-1.5 text-[11px] transition-colors",
                  selectedHistory?.id === r.id
                    ? "border-brand/40 bg-brand/10 text-brand"
                    : "border-border bg-surface-overlay/30 text-fg-muted hover:text-fg hover:border-border"
                )}
              >
                <span className="text-fg-subtle font-mono">
                  {new Date(r.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                </span>
                <span className="text-fg-muted">{r.generated_cases.length} case</span>
              </button>
            ))}
          </div>
          {selectedHistory && (
            <p className="text-[11px] text-brand/70">
              {new Date(selectedHistory.created_at).toLocaleString("tr-TR")} tarihli çalışma görüntüleniyor —{" "}
              <button type="button" onClick={() => setSelectedHistory(null)} className="underline hover:text-brand">kapat</button>
            </p>
          )}
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        {/* Form */}
        <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Parametreler</p>

          {fields.map((f, i) => {
            const values = Array.isArray(f.allowed_set) ? (f.allowed_set as string[]) : [];
            return (
              <div key={i} className="space-y-2 rounded-lg border border-border bg-surface-overlay/30 p-3">
                <div className="flex gap-2">
                  <span className="flex h-6 w-5 shrink-0 items-center justify-center text-[11px] text-fg-disabled font-mono">{i + 1}</span>
                  <input
                    value={f.name}
                    onChange={e => update(i, { name: e.target.value })}
                    placeholder="Parametre adı (ör. Tarayıcı, OS, Dil)"
                    className={cn(INP, "flex-1")}
                  />
                  {fields.length > 2 && (
                    <button
                      type="button"
                      onClick={() => setFields(p => p.filter((_, j) => j !== i))}
                      className="shrink-0 text-fg-disabled hover:text-red-400 transition-colors text-[12px]"
                    >✕</button>
                  )}
                </div>
                <div className="pl-7 space-y-1.5">
                  <p className="text-[10px] text-fg-disabled">Değerler (virgülle ayırın):</p>
                  <input
                    value={values.join(", ")}
                    onChange={e => update(i, { allowed_set: e.target.value.split(",").map(s => s.trim()).filter(Boolean) })}
                    placeholder="ör. Chrome, Firefox, Safari"
                    className={cn(INP, "text-[12px]")}
                  />
                  {values.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {values.map((v, vi) => (
                        <span key={vi} className="rounded border border-brand/30 bg-brand/10 px-1.5 py-0.5 text-[10px] text-brand/80">
                          {v}
                        </span>
                      ))}
                      <span className="text-[10px] text-fg-disabled self-center">{values.length} değer</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          <Button
            variant="outline"
            type="button"
            onClick={() => setFields(p => [...p, emptyField()])}
            className="w-full gap-1.5 border-dashed border-border py-2 text-[12px] text-fg-disabled hover:text-fg-muted"
          >
            + Parametre Ekle
          </Button>

          {/* Complexity preview */}
          {isReady && (
            <div className="rounded-lg border border-border bg-surface-overlay/50 px-3 py-2 text-[11px] text-fg-subtle">
              <span className="font-medium text-fg">Tam kombinasyon:</span> {totalCombinations.toLocaleString("tr-TR")} →{" "}
              <span className="text-emerald-400">Pairwise ile önemli ölçüde azaltılır</span>
            </div>
          )}

          <textarea
            value={context}
            onChange={e => setContext(e.target.value)}
            rows={2}
            placeholder="Requirement context veya ek açıklama (opsiyonel)…"
            className={cn(INP, "resize-none")}
          />

          <Button
            variant="primary"
            type="button"
            onClick={submit}
            disabled={!isReady || runMut.isPending}
            className="w-full rounded-xl py-2.5 text-[13px] font-medium"
          >
            {runMut.isPending ? "Üretiliyor…" : "Pairwise Çalıştır"}
          </Button>

          {runMut.isError && (
            <p className="text-[11px] text-red-400">Hata oluştu — backend bağlantısını kontrol edin.</p>
          )}
        </div>

        {/* Results */}
        <div className="space-y-4">
          {/* Coverage stats */}
          {run && !selectedHistory && (
            <div className="rounded-xl border border-border bg-surface-raised p-4 space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Kapsam Özeti</p>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: "Test Sayısı",   value: cases.length,               color: "text-brand" },
                  { label: "Parametre",     value: (Array.isArray(run.input_spec.fields) ? (run.input_spec.fields as unknown[]).length : null) ?? fields.length, color: "text-fg" },
                  { label: "Azaltma",       value: `%${totalCombinations > 0 ? Math.max(0, Math.round((1 - cases.length / totalCombinations) * 100)) : 0}`, color: "text-emerald-400" },
                ].map(s => (
                  <div key={s.label} className="rounded-lg border border-border bg-surface-overlay px-3 py-2 text-center">
                    <p className={cn("text-[15px] font-bold", s.color)}>{s.value}</p>
                    <p className="text-[10px] text-fg-subtle mt-0.5">{s.label}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cases */}
          <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">
                {selectedHistory ? "Geçmiş Çalışma Senaryoları" : "Üretilen Senaryolar"}
              </p>
              {displayCases.length > 0 && (
                <div className="flex rounded-lg border border-border overflow-hidden text-[10px]">
                  {(["list", "matrix"] as const).map(mode => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setViewMode(mode)}
                      className={cn(
                        "px-2.5 py-1 font-medium transition-colors",
                        viewMode === mode
                          ? "bg-brand text-brand-fg"
                          : "text-fg-subtle hover:text-fg hover:bg-surface-overlay"
                      )}
                    >
                      {mode === "list" ? "Liste" : "Tablo"}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {!run && !selectedHistory ? (
              <div className="py-12 text-center">
                <div className="text-3xl mb-2">⚡</div>
                <p className="text-[13px] text-fg-disabled">Parametrelerinizi tanımlayın ve çalıştırın</p>
              </div>
            ) : displayCases.length === 0 ? (
              <div className="py-8 text-center text-[13px] text-fg-disabled">Senaryo üretilemedi</div>
            ) : (
              <>
                {viewMode === "list" ? (
                  <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                    {displayCases.map((c, i) => {
                      const inputs = (c.inputs ?? {}) as Record<string, unknown>;
                      const paramEntries = Object.entries(inputs);
                      return (
                        <div key={i} className="flex items-start gap-3 rounded-lg border border-border bg-surface-overlay/30 px-3 py-2.5">
                          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand/60" />
                          <div className="flex-1 min-w-0">
                            <p className="text-[12px] text-fg font-medium">{c.name}</p>
                            {paramEntries.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1.5">
                                {paramEntries.map(([k, v]) => (
                                  <span key={k} className="inline-flex items-center gap-1 rounded border border-border bg-surface-overlay px-1.5 py-0.5 text-[10px]">
                                    <span className="text-fg-disabled">{k}:</span>
                                    <span className="text-fg font-medium">{String(v)}</span>
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                          {!selectedHistory && (
                            promoted.has(i) ? (
                              <span className="text-[11px] text-emerald-500/70 shrink-0 mt-0.5">✓ Kaydedildi</span>
                            ) : (
                              <Button
                                variant="outline"
                                size="sm"
                                type="button"
                                onClick={() => promote([i])}
                                disabled={promoteMut.isPending}
                                className="shrink-0 border-border px-2 py-0.5 text-[11px] text-fg-subtle hover:text-brand mt-0.5"
                              >
                                Kaydet
                              </Button>
                            )
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  /* Matrix table view */
                  <div className="overflow-auto max-h-96 rounded-lg border border-border">
                    <table className="w-full text-[11px] border-collapse">
                      <thead>
                        <tr>
                          <th className="px-2 py-2 text-left font-semibold text-fg-disabled bg-surface-overlay border-b border-border w-8">#</th>
                          {Object.keys((displayCases[0]?.inputs ?? {}) as Record<string, unknown>).map(k => (
                            <th key={k} className="px-3 py-2 text-left font-semibold text-brand bg-brand/10 border-b border-border whitespace-nowrap">
                              {k}
                            </th>
                          ))}
                          {!selectedHistory && (
                            <th className="px-2 py-2 text-center font-semibold text-fg-disabled bg-surface-overlay border-b border-border">Aksiyon</th>
                          )}
                        </tr>
                      </thead>
                      <tbody>
                        {displayCases.map((c, i) => {
                          const inputs = (c.inputs ?? {}) as Record<string, unknown>;
                          return (
                            <tr key={i} className={cn("border-b border-border/40", i % 2 === 0 ? "bg-surface-overlay/20" : "bg-surface-raised")}>
                              <td className="px-2 py-2 text-fg-disabled font-mono">{i + 1}</td>
                              {Object.values(inputs).map((v, vi) => (
                                <td key={vi} className="px-3 py-2 text-fg font-medium">{String(v)}</td>
                              ))}
                              {!selectedHistory && (
                                <td className="px-2 py-2 text-center">
                                  {promoted.has(i) ? (
                                    <span className="text-emerald-500/70">✓</span>
                                  ) : (
                                    <button
                                      type="button"
                                      onClick={() => promote([i])}
                                      disabled={promoteMut.isPending}
                                      className="rounded border border-border px-2 py-0.5 text-[10px] text-fg-subtle hover:text-brand transition-colors disabled:opacity-40"
                                    >
                                      Kaydet
                                    </button>
                                  )}
                                </td>
                              )}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
                {!selectedHistory && (
                  <Button
                    variant="outline"
                    type="button"
                    onClick={() => promote(cases.map((_, i) => i).filter(i => !promoted.has(i)))}
                    disabled={promoteMut.isPending || promoted.size === cases.length}
                    className="w-full rounded-xl border-border py-2 text-[12px] text-fg-muted hover:text-fg"
                  >
                    {promoteMut.isPending ? "Kaydediliyor…" : promoted.size === cases.length ? "Tümü Kaydedildi ✓" : `Tümünü Kaydet (${cases.length - promoted.size})`}
                  </Button>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
