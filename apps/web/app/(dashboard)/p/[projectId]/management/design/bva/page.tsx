"use client";

import { useState } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";
import {
  type DesignDataType,
  type DesignFieldSpec,
  type DesignRun,
  useCreateBvaRun,
  useDesignRuns,
  usePromoteCases,
} from "@/lib/hooks/use-mgmt-design";

const DATA_TYPES: DesignDataType[] = ["int", "float", "string", "date", "bool", "enum"];

function emptyField(): DesignFieldSpec {
  return { name: "", data_type: "int", min_value: null, max_value: null, allowed_set: null, nullable: false };
}

const INP = "w-full rounded-lg border border-border bg-white/[0.03] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 focus:border-teal-500/30 focus:outline-none transition-colors";

export default function BvaPage() {
  const projectId = useRouteParam("projectId") ?? "";
  const [fields, setFields]   = useState<DesignFieldSpec[]>([emptyField()]);
  const [context, setContext] = useState("");
  const [promoted, setPromoted] = useState<Set<number>>(new Set());
  const [selectedHistory, setSelectedHistory] = useState<DesignRun | null>(null);

  const runMut     = useCreateBvaRun();
  const run        = runMut.data;
  const promoteMut = usePromoteCases(run?.id);

  const { data: historyRuns = [] } = useDesignRuns({ technique: "BVA", projectId });

  const update = (i: number, patch: Partial<DesignFieldSpec>) =>
    setFields(f => f.map((x, idx) => idx === i ? { ...x, ...patch } : x));

  const submit = () => runMut.mutate({
    project_id: projectId,
    fields,
    requirement_text: context.trim() || undefined,
  });

  const promote = (indexes: number[]) => {
    promoteMut.mutate({ case_indexes: indexes }, {
      onSuccess: () => setPromoted(p => new Set([...p, ...indexes])),
    });
  };

  const cases = run?.generated_cases ?? [];

  const recentRuns = historyRuns.slice(0, 5);
  const displayCases = selectedHistory ? selectedHistory.generated_cases : cases;

  return (
    <div className="min-h-full bg-bg px-6 py-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[15px] font-semibold text-slate-100">Boundary Value Analysis</h1>
          <p className="mt-0.5 text-[12px] text-slate-500">Alan sınırlarından otomatik test senaryosu üret</p>
        </div>
        {run && !selectedHistory && <span className="text-[11px] text-slate-600">{cases.length} case üretildi · {promoted.size} kaydedildi</span>}
      </div>

      {/* Recent Runs */}
      {recentRuns.length > 0 && (
        <div className="rounded-xl border border-border bg-surface-raised p-4 space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">Son Çalışmalar</p>
          <div className="flex flex-wrap gap-2">
            {recentRuns.map((r) => (
              <button
                key={r.id}
                type="button"
                onClick={() => setSelectedHistory(prev => prev?.id === r.id ? null : r)}
                className={cn(
                  "flex items-center gap-2 rounded-lg border px-3 py-1.5 text-[11px] transition-colors",
                  selectedHistory?.id === r.id
                    ? "border-teal-500/40 bg-teal-500/10 text-teal-300"
                    : "border-border bg-white/[0.02] text-slate-400 hover:text-slate-200 hover:border-slate-600"
                )}
              >
                <span className="text-slate-500 font-mono">
                  {new Date(r.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                </span>
                <span className="text-slate-400">{r.generated_cases.length} case</span>
                <span className="text-slate-600">·</span>
                <span className="text-slate-500">{((r.input_spec.fields as unknown[])?.length ?? "?")} alan</span>
              </button>
            ))}
          </div>
          {selectedHistory && (
            <p className="text-[11px] text-teal-400/70">
              {new Date(selectedHistory.created_at).toLocaleString("tr-TR")} tarihli çalışma görüntüleniyor —{" "}
              <button type="button" onClick={() => setSelectedHistory(null)} className="underline hover:text-teal-300">kapat</button>
            </p>
          )}
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        {/* Form */}
        <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">Alan Tanımları</p>

          {fields.map((f, i) => (
            <div key={i} className="space-y-2 rounded-lg border border-border bg-white/[0.02] p-3">
              <div className="flex gap-2">
                <span className="flex h-6 w-5 shrink-0 items-center justify-center text-[11px] text-slate-600 font-mono">{i+1}</span>
                <input value={f.name} onChange={e => update(i, { name: e.target.value })}
                  placeholder="Alan adı" className={cn(INP, "flex-1")}/>
                <select value={f.data_type} onChange={e => update(i, { data_type: e.target.value as DesignDataType })}
                  className="w-20 shrink-0 rounded-lg border border-border bg-white/[0.03] px-2 py-2 text-[12px] text-slate-300 focus:outline-none">
                  {DATA_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <button type="button" onClick={() => setFields(p => p.filter((_, j) => j !== i))}
                  className="shrink-0 text-slate-700 hover:text-red-400 transition-colors text-[12px]">✕</button>
              </div>
              {(f.data_type === "int" || f.data_type === "float" || f.data_type === "string") && (
                <div className="flex gap-2 pl-7">
                  <input value={f.min_value ?? ""} onChange={e => update(i, { min_value: e.target.value || null })}
                    placeholder="min" className={cn(INP, "text-[12px]")}/>
                  <input value={f.max_value ?? ""} onChange={e => update(i, { max_value: e.target.value || null })}
                    placeholder="max" className={cn(INP, "text-[12px]")}/>
                </div>
              )}
              {f.data_type === "enum" && (
                <input
                  value={Array.isArray(f.allowed_set) ? (f.allowed_set as string[]).join(", ") : ""}
                  onChange={e => update(i, { allowed_set: e.target.value.split(",").map(s => s.trim()).filter(Boolean) })}
                  placeholder="değerler: a, b, c" className={cn(INP, "pl-7 text-[12px]")}/>
              )}
            </div>
          ))}

          <button type="button" onClick={() => setFields(p => [...p, emptyField()])}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-border py-2 text-[12px] text-slate-600 hover:text-slate-400 transition-colors">
            + Alan Ekle
          </button>

          <textarea value={context} onChange={e => setContext(e.target.value)} rows={2}
            placeholder="Requirement context (opsiyonel)…" className={cn(INP, "resize-none")}/>

          <button type="button" onClick={submit}
            disabled={fields.some(f => !f.name.trim()) || runMut.isPending}
            className="w-full rounded-xl bg-teal-600 py-2.5 text-[13px] font-medium text-white hover:bg-teal-700 disabled:opacity-40 transition-colors">
            {runMut.isPending ? "Üretiliyor…" : "BVA Çalıştır"}
          </button>
        </div>

        {/* Results */}
        <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
            {selectedHistory ? "Geçmiş Çalışma Senaryoları" : "Üretilen Senaryolar"}
          </p>

          {!run && !selectedHistory ? (
            <div className="py-12 text-center text-[13px] text-slate-600">Henüz çalıştırılmadı</div>
          ) : displayCases.length === 0 ? (
            <div className="py-8 text-center text-[13px] text-slate-600">Senaryo üretilemedi</div>
          ) : (
            <>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {displayCases.map((c, i) => (
                  <div key={i} className="flex items-start gap-3 rounded-lg border border-border bg-white/[0.02] px-3 py-2.5">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500/60"/>
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] text-slate-300">{c.name}</p>
                      {c.rationale && <p className="mt-0.5 text-[11px] text-slate-600 line-clamp-1">{c.rationale}</p>}
                    </div>
                    {!selectedHistory && (
                      promoted.has(i) ? (
                        <span className="shrink-0 text-[11px] text-emerald-500/70">✓</span>
                      ) : (
                        <button type="button" onClick={() => promote([i])}
                          className="shrink-0 rounded border border-border px-2 py-0.5 text-[11px] text-slate-500 hover:text-teal-400 transition-colors">
                          Kaydet
                        </button>
                      )
                    )}
                  </div>
                ))}
              </div>
              {!selectedHistory && (
                <button type="button"
                  onClick={() => promote(cases.map((_, i) => i).filter(i => !promoted.has(i)))}
                  disabled={promoteMut.isPending || promoted.size === cases.length}
                  className="w-full rounded-xl border border-border py-2 text-[12px] text-slate-400 hover:text-slate-200 disabled:opacity-40 transition-colors">
                  {promoteMut.isPending ? "Kaydediliyor…" : "Tümünü Repository'ye Kaydet"}
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
