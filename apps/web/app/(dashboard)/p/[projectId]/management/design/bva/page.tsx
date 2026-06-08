"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  type DesignDataType,
  type DesignFieldSpec,
  type DesignRun,
  type DesignTemplate,
  useCreateBvaRun,
  useDeleteDesignTemplate,
  useDesignRuns,
  useDesignTemplates,
  usePromoteCases,
  useSaveDesignTemplate,
} from "@/lib/hooks/use-mgmt-design";

const DATA_TYPES: DesignDataType[] = ["int", "float", "string", "date", "bool", "enum"];

function emptyField(): DesignFieldSpec {
  return { name: "", data_type: "int", min_value: null, max_value: null, allowed_set: null, nullable: false };
}

const INP = "w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-disabled focus:border-teal-500/30 focus:outline-none transition-colors";

export default function BvaPage() {
  const projectId = useRouteParam("projectId") ?? "";
  const qc = useQueryClient();
  const [fields, setFields]   = useState<DesignFieldSpec[]>([emptyField()]);
  const [context, setContext] = useState("");
  const [promoted, setPromoted] = useState<Set<number>>(new Set());
  const [selectedHistory, setSelectedHistory] = useState<DesignRun | null>(null);
  const [templateName, setTemplateName] = useState("");
  const [showTemplateSave, setShowTemplateSave] = useState(false);

  const runMut     = useCreateBvaRun();
  const run        = runMut.data;
  const promoteMut = usePromoteCases(run?.id);

  const { data: historyRuns = [] } = useDesignRuns({ technique: "BVA", projectId });
  const { data: savedTemplates = [] } = useDesignTemplates(projectId || undefined);
  const saveTemplateMut   = useSaveDesignTemplate(projectId);
  const deleteTemplateMut = useDeleteDesignTemplate(projectId);

  const bvaTemplates = savedTemplates.filter((t: DesignTemplate) => t.technique === "BVA");

  const handleSaveTemplate = () => {
    if (!templateName.trim()) return;
    saveTemplateMut.mutate(
      { name: templateName.trim(), technique: "BVA", fields },
      {
        onSuccess: () => {
          setTemplateName("");
          setShowTemplateSave(false);
        },
      }
    );
  };

  const handleLoadTemplate = (tpl: DesignTemplate) => {
    setFields(tpl.fields.map(f => ({ ...f })));
  };

  const update = (i: number, patch: Partial<DesignFieldSpec>) =>
    setFields(f => f.map((x, idx) => idx === i ? { ...x, ...patch } : x));

  const validateBvaFields = (fs: DesignFieldSpec[]): string | null => {
    for (const f of fs) {
      if (!f.name.trim()) return "Alan adı boş olamaz"
      if (f.data_type !== "string" && f.data_type !== "bool" && f.data_type !== "enum") {
        const min = f.min_value
        const max = f.max_value
        const hasMin = min !== null && min !== undefined && min !== ""
        const hasMax = max !== null && max !== undefined && max !== ""
        if (f.data_type === "date") {
          // Dates are ISO strings (yyyy-mm-dd); compare via Date.parse, not parseFloat.
          const minT = hasMin ? Date.parse(String(min)) : NaN
          const maxT = hasMax ? Date.parse(String(max)) : NaN
          if (hasMin && isNaN(minT)) return `"${f.name}" minimum tarihi geçerli bir tarih olmalı`
          if (hasMax && isNaN(maxT)) return `"${f.name}" maksimum tarihi geçerli bir tarih olmalı`
          if (hasMin && hasMax && minT > maxT) return `"${f.name}" minimum tarihi maksimumdan sonra olamaz`
        } else {
          let minN = NaN, maxN = NaN
          if (hasMin) {
            minN = parseFloat(String(min))
            if (isNaN(minN)) return `"${f.name}" minimum değeri geçerli bir sayı olmalı`
            if (!isFinite(minN)) return `"${f.name}" minimum değeri sonsuz olamaz`
          }
          if (hasMax) {
            maxN = parseFloat(String(max))
            if (isNaN(maxN)) return `"${f.name}" maksimum değeri geçerli bir sayı olmalı`
            if (!isFinite(maxN)) return `"${f.name}" maksimum değeri sonsuz olamaz`
          }
          if (hasMin && hasMax && minN > maxN) return `"${f.name}" minimum değeri maksimumdan büyük olamaz`
        }
      }
    }
    return null
  }

  const [validationError, setValidationError] = useState<string | null>(null)

  const submit = () => {
    const err = validateBvaFields(fields)
    if (err) { setValidationError(err); return }
    setValidationError(null)
    runMut.mutate({
      project_id: projectId,
      fields,
      requirement_text: context.trim() || undefined,
    })
  };

  const promote = (indexes: number[]) => {
    promoteMut.mutate({ case_indexes: indexes }, {
      onSuccess: () => {
        setPromoted(p => new Set([...p, ...indexes]));
        void qc.invalidateQueries({ queryKey: ["management", projectId] });
      },
    });
  };

  const cases = run?.generated_cases ?? [];

  const recentRuns = historyRuns.slice(0, 5);
  const displayCases = selectedHistory ? selectedHistory.generated_cases : cases;

  return (
    <div className="min-h-full bg-surface-base px-6 py-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[15px] font-semibold text-fg">Boundary Value Analysis</h1>
          <p className="mt-0.5 text-[12px] text-fg-subtle">Alan sınırlarından otomatik test senaryosu üret</p>
        </div>
        {run && !selectedHistory && <span className="text-[11px] text-fg-disabled">{cases.length} case üretildi · {promoted.size} kaydedildi</span>}
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
                    ? "border-teal-500/40 bg-teal-500/10 text-teal-300"
                    : "border-border bg-surface-overlay/30 text-fg-muted hover:text-fg hover:border-border"
                )}
              >
                <span className="text-fg-subtle font-mono">
                  {new Date(r.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                </span>
                <span className="text-fg-muted">{r.generated_cases.length} case</span>
                <span className="text-fg-disabled">·</span>
                <span className="text-fg-subtle">{((r.input_spec.fields as unknown[])?.length ?? "?")} alan</span>
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

      {/* Saved Templates */}
      {bvaTemplates.length > 0 && (
        <div className="rounded-xl border border-border bg-surface-raised p-4 space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Kayıtlı Şablonlar</p>
          <div className="flex flex-wrap gap-2">
            {bvaTemplates.map((tpl: DesignTemplate) => (
              <div key={tpl.id} className="flex items-center gap-1.5 rounded-lg border border-border bg-surface-overlay/30 px-3 py-1.5">
                <button
                  type="button"
                  onClick={() => handleLoadTemplate(tpl)}
                  className="text-[12px] text-fg hover:text-teal-300 transition-colors"
                >
                  {tpl.name}
                </button>
                <span className="text-fg-disabled text-[10px]">({tpl.fields.length} alan)</span>
                <button
                  type="button"
                  onClick={() => deleteTemplateMut.mutate(tpl.id)}
                  className="ml-1 text-fg-disabled hover:text-red-400 transition-colors text-[11px]"
                  title="Şablonu sil"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-fg-disabled">Bir şablona tıklayarak alanları yükle</p>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        {/* Form */}
        <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Alan Tanımları</p>

          {fields.map((f, i) => (
            <div key={i} className="space-y-2 rounded-lg border border-border bg-surface-overlay/30 p-3">
              <div className="flex gap-2">
                <span className="flex h-6 w-5 shrink-0 items-center justify-center text-[11px] text-fg-disabled font-mono">{i+1}</span>
                <input value={f.name} onChange={e => update(i, { name: e.target.value })}
                  placeholder="Alan adı" className={cn(INP, "flex-1")}/>
                <select value={f.data_type} onChange={e => update(i, { data_type: e.target.value as DesignDataType })}
                  className="w-20 shrink-0 rounded-lg border border-border bg-surface-overlay px-2 py-2 text-[12px] text-fg focus:outline-none">
                  {DATA_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <button type="button" onClick={() => setFields(p => p.filter((_, j) => j !== i))}
                  className="shrink-0 text-fg-disabled hover:text-red-400 transition-colors text-[12px]">✕</button>
              </div>
              {(f.data_type === "int" || f.data_type === "float" || f.data_type === "string") && (
                <div className="flex gap-2 pl-7">
                  <input value={f.min_value ?? ""} onChange={e => update(i, { min_value: e.target.value || null })}
                    placeholder="min" className={cn(INP, "text-[12px]")}/>
                  <input value={f.max_value ?? ""} onChange={e => update(i, { max_value: e.target.value || null })}
                    placeholder="max" className={cn(INP, "text-[12px]")}/>
                </div>
              )}
              {f.data_type === "date" && (
                <div className="flex gap-2 pl-7">
                  <input type="date" value={f.min_value ?? ""} onChange={e => update(i, { min_value: e.target.value || null })}
                    className={cn(INP, "text-[12px]")} title="Minimum tarih"/>
                  <input type="date" value={f.max_value ?? ""} onChange={e => update(i, { max_value: e.target.value || null })}
                    className={cn(INP, "text-[12px]")} title="Maksimum tarih"/>
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
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-border py-2 text-[12px] text-fg-disabled hover:text-fg-muted transition-colors">
            + Alan Ekle
          </button>

          <textarea value={context} onChange={e => setContext(e.target.value)} rows={2}
            placeholder="Requirement context (opsiyonel)…" className={cn(INP, "resize-none")}/>

          {/* Template save */}
          {showTemplateSave ? (
            <div className="flex gap-2">
              <input
                value={templateName}
                onChange={e => setTemplateName(e.target.value)}
                placeholder="Şablon adı…"
                className={cn(INP, "flex-1 text-[12px]")}
                onKeyDown={e => { if (e.key === "Enter") handleSaveTemplate(); if (e.key === "Escape") setShowTemplateSave(false); }}
                autoFocus
              />
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={handleSaveTemplate}
                disabled={!templateName.trim() || saveTemplateMut.isPending}
                className="shrink-0"
              >
                {saveTemplateMut.isPending ? "…" : "Kaydet"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => { setShowTemplateSave(false); setTemplateName(""); }}
                className="shrink-0"
              >
                İptal
              </Button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowTemplateSave(true)}
              disabled={fields.every(f => !f.name.trim())}
              className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-border py-1.5 text-[11px] text-fg-disabled hover:text-fg-muted disabled:opacity-30 transition-colors"
            >
              + Bu alanları şablon olarak kaydet (ekipte paylaş)
            </button>
          )}

          <Button type="button" variant="primary" onClick={submit}
            disabled={fields.some(f => !f.name.trim()) || runMut.isPending}
            className="w-full rounded-xl">
            {runMut.isPending ? "Üretiliyor…" : "BVA Çalıştır"}
          </Button>
          {validationError && (
            <p className="mt-2 text-xs text-amber-400">{validationError}</p>
          )}
          {runMut.isError && (
            <p className="mt-2 text-xs text-red-400">
              Hata: {runMut.error instanceof Error ? runMut.error.message : "Çalıştırılamadı"}
            </p>
          )}
        </div>

        {/* Results */}
        <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">
            {selectedHistory ? "Geçmiş Çalışma Senaryoları" : "Üretilen Senaryolar"}
          </p>

          {!run && !selectedHistory ? (
            <div className="py-12 text-center text-[13px] text-fg-disabled">Henüz çalıştırılmadı</div>
          ) : displayCases.length === 0 ? (
            <div className="py-8 text-center text-[13px] text-fg-disabled">Senaryo üretilemedi</div>
          ) : (
            <>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {displayCases.map((c, i) => (
                  <div key={i} className="flex items-start gap-3 rounded-lg border border-border bg-surface-overlay/30 px-3 py-2.5">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500/60"/>
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] text-fg">{c.name}</p>
                      {c.rationale && <p className="mt-0.5 text-[11px] text-fg-disabled line-clamp-1">{c.rationale}</p>}
                    </div>
                    {!selectedHistory && (
                      promoted.has(i) ? (
                        <span className="shrink-0 text-[11px] text-emerald-500/70">✓</span>
                      ) : (
                        <button type="button" onClick={() => promote([i])}
                          className="shrink-0 rounded border border-border px-2 py-0.5 text-[11px] text-fg-subtle hover:text-teal-400 transition-colors">
                          Kaydet
                        </button>
                      )
                    )}
                  </div>
                ))}
              </div>
              {!selectedHistory && (
                <Button type="button" variant="outline"
                  onClick={() => promote(cases.map((_, i) => i).filter(i => !promoted.has(i)))}
                  disabled={promoteMut.isPending || promoted.size === cases.length}
                  className="w-full rounded-xl">
                  {promoteMut.isPending ? "Kaydediliyor…" : "Tümünü Repository'ye Kaydet"}
                </Button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
