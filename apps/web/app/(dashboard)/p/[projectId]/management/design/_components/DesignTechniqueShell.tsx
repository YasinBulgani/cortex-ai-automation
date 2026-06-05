"use client";

import { useState, useEffect } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";
import {
  useManagementSettingValue,
  usePatchManagementSetting,
} from "@/lib/hooks/use-management";
import {
  type DesignDataType,
  type DesignFieldSpec,
  type GeneratedCaseDraft,
  type DesignPartition,
  type DesignRun,
  useDesignRuns,
} from "@/lib/hooks/use-mgmt-design";

// ── Constants ─────────────────────────────────────────────────────────────────

export const DATA_TYPES: DesignDataType[] = ["int", "float", "string", "date", "bool", "enum"];

export const INP =
  "w-full rounded-lg border border-border bg-white/[0.03] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 focus:border-teal-500/30 focus:outline-none transition-colors";

export function emptyField(): DesignFieldSpec {
  return { name: "", data_type: "int", min_value: null, max_value: null, allowed_set: null, nullable: false };
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface FieldTemplate {
  name: string;
  fields: DesignFieldSpec[];
  savedAt: string;
}

export type SupportedTechnique = "BVA" | "EQ" | "DT" | "PAIRWISE";

interface DesignTechniqueShellProps {
  technique: SupportedTechnique;
  title: string;
  description: string;
  /** Called when the user presses the Run button. Receives the current fields and context text. */
  onRun: (fields: DesignFieldSpec[], context: string) => void;
  isRunning: boolean;
  result?: DesignRun | null;
  promoted: Set<number>;
  onPromote: (indexes: number[]) => void;
  isPending: boolean;
  /** Optional extra slot rendered above the run button (e.g. technique-specific inputs) */
  extraFormSlot?: React.ReactNode;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function DesignTechniqueShell({
  technique,
  title,
  description,
  onRun,
  isRunning,
  result,
  promoted,
  onPromote,
  isPending,
  extraFormSlot,
}: DesignTechniqueShellProps) {
  const projectId = useRouteParam("projectId") ?? "";
  const templateKey = `${technique.toLowerCase()}_field_templates`;
  const { data: allTemplates } = useManagementSettingValue<Record<string, FieldTemplate[]>>(
    projectId || undefined,
    "design_templates",
    {},
  );
  const saveTemplatesSetting = usePatchManagementSetting<Record<string, FieldTemplate[]>>(
    projectId,
    "design_templates",
  );

  const [fields, setFields] = useState<DesignFieldSpec[]>([emptyField()]);
  const [context, setContext] = useState("");
  const [templates, setTemplates] = useState<FieldTemplate[]>([]);
  const [templateName, setTemplateName] = useState("");
  const [showTemplateSave, setShowTemplateSave] = useState(false);

  const historyQ = useDesignRuns({ technique, projectId: projectId || undefined });
  const recentRuns = (historyQ.data ?? []).slice(0, 5);

  useEffect(() => {
    setTemplates(allTemplates[templateKey] ?? []);
  }, [allTemplates, templateKey]);

  const update = (i: number, patch: Partial<DesignFieldSpec>) =>
    setFields(f => f.map((x, idx) => (idx === i ? { ...x, ...patch } : x)));

  const saveTemplate = async () => {
    const name = templateName.trim() || `Sablon ${new Date().toLocaleDateString("tr-TR")}`;
    const newTemplate: FieldTemplate = {
      name,
      fields: JSON.parse(JSON.stringify(fields)) as DesignFieldSpec[],
      savedAt: new Date().toISOString(),
    };
    const updated = [newTemplate, ...templates].slice(0, 10);
    setTemplates(updated);
    await saveTemplatesSetting.mutateAsync({ ...allTemplates, [templateKey]: updated });
    setTemplateName("");
    setShowTemplateSave(false);
  };

  const loadTemplate = (t: FieldTemplate) => {
    setFields(JSON.parse(JSON.stringify(t.fields)) as DesignFieldSpec[]);
  };

  const deleteTemplate = async (idx: number) => {
    const updated = templates.filter((_, i) => i !== idx);
    setTemplates(updated);
    await saveTemplatesSetting.mutateAsync({ ...allTemplates, [templateKey]: updated });
  };

  const cases: GeneratedCaseDraft[] = result?.generated_cases ?? [];
  const partitions: DesignPartition[] = result?.partitions ?? [];

  const runLabel = isRunning ? "Uretiliyor..." : `${technique} Calistir`;

  return (
    <div className="min-h-full bg-bg px-6 py-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[15px] font-semibold text-slate-100">{title}</h1>
          <p className="mt-0.5 text-[12px] text-slate-500">{description}</p>
        </div>
        {result && (
          <span className="text-[11px] text-slate-600">
            {cases.length} case uretildi · {promoted.size} kaydedildi
            {partitions.length > 0 && ` · ${partitions.length} partition`}
          </span>
        )}
      </div>

      {/* Saved templates */}
      {templates.length > 0 && (
        <div className="rounded-xl border border-border bg-surface-raised p-4 space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">Kayitli Sablonlar</p>
          <div className="flex flex-wrap gap-2">
            {templates.map((t, i) => (
              <div
                key={i}
                className="flex items-center gap-1.5 rounded-lg border border-border bg-white/[0.03] px-2.5 py-1.5"
              >
                <button
                  type="button"
                  onClick={() => loadTemplate(t)}
                  className="text-[12px] text-slate-300 hover:text-teal-400 transition-colors"
                >
                  {t.name}
                </button>
                <span className="text-[10px] text-slate-600">({t.fields.length} alan)</span>
                <button
                  type="button"
                  onClick={() => deleteTemplate(i)}
                  className="text-slate-700 hover:text-red-400 transition-colors text-[11px] ml-1"
                >
                  x
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        {/* Form panel */}
        <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">Alan Tanimlari</p>

          {fields.map((f, i) => (
            <div key={i} className="space-y-2 rounded-lg border border-border bg-white/[0.02] p-3">
              <div className="flex gap-2">
                <span className="flex h-6 w-5 shrink-0 items-center justify-center text-[11px] text-slate-600 font-mono">
                  {i + 1}
                </span>
                <input
                  value={f.name}
                  onChange={e => update(i, { name: e.target.value })}
                  placeholder="Alan adi"
                  className={cn(INP, "flex-1")}
                />
                <select
                  value={f.data_type}
                  onChange={e => update(i, { data_type: e.target.value as DesignDataType })}
                  className="w-20 shrink-0 rounded-lg border border-border bg-white/[0.03] px-2 py-2 text-[12px] text-slate-300 focus:outline-none"
                >
                  {DATA_TYPES.map(t => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setFields(p => p.filter((_, j) => j !== i))}
                  className="shrink-0 text-slate-700 hover:text-red-400 transition-colors text-[12px]"
                >
                  x
                </button>
              </div>

              {(f.data_type === "int" || f.data_type === "float" || f.data_type === "string") && (
                <div className="flex gap-2 pl-7">
                  <input
                    value={f.min_value ?? ""}
                    onChange={e => update(i, { min_value: e.target.value || null })}
                    placeholder="min"
                    className={cn(INP, "text-[12px]")}
                  />
                  <input
                    value={f.max_value ?? ""}
                    onChange={e => update(i, { max_value: e.target.value || null })}
                    placeholder="max"
                    className={cn(INP, "text-[12px]")}
                  />
                </div>
              )}

              {f.data_type === "enum" && (
                <input
                  value={Array.isArray(f.allowed_set) ? (f.allowed_set as string[]).join(", ") : ""}
                  onChange={e =>
                    update(i, {
                      allowed_set: e.target.value
                        .split(",")
                        .map(s => s.trim())
                        .filter(Boolean),
                    })
                  }
                  placeholder="degerler: a, b, c"
                  className={cn(INP, "pl-7 text-[12px]")}
                />
              )}

              <label className="flex items-center gap-2 pl-7 text-[11px] text-slate-500">
                <input
                  type="checkbox"
                  checked={!!f.nullable}
                  onChange={e => update(i, { nullable: e.target.checked })}
                  className="h-3 w-3 accent-blue-500"
                />
                Null deger kabul eder
              </label>
            </div>
          ))}

          <button
            type="button"
            onClick={() => setFields(p => [...p, emptyField()])}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-border py-2 text-[12px] text-slate-600 hover:text-slate-400 transition-colors"
          >
            + Alan Ekle
          </button>

          <textarea
            value={context}
            onChange={e => setContext(e.target.value)}
            rows={2}
            placeholder="Requirement context (opsiyonel)..."
            className={cn(INP, "resize-none")}
          />

          {extraFormSlot}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => onRun(fields, context)}
              disabled={fields.some(f => !f.name.trim()) || isRunning}
              className="flex-1 rounded-xl bg-brand py-2.5 text-[13px] font-medium text-white hover:brightness-105 disabled:opacity-40 transition-colors"
            >
              {runLabel}
            </button>
            <button
              type="button"
              onClick={() => setShowTemplateSave(v => !v)}
              className="rounded-xl border border-border px-3 py-2.5 text-[12px] text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-colors"
            >
              Sablon Kaydet
            </button>
          </div>

          {showTemplateSave && (
            <div className="flex gap-2">
              <input
                value={templateName}
                onChange={e => setTemplateName(e.target.value)}
                placeholder="Sablon adi (opsiyonel)"
                className={cn(INP, "text-[12px]")}
              />
              <button
                type="button"
                onClick={saveTemplate}
                className="shrink-0 rounded-lg bg-blue-600/80 px-3 py-2 text-[12px] text-white hover:bg-blue-600 transition-colors"
              >
                Kaydet
              </button>
            </div>
          )}
        </div>

        {/* Results panel */}
        <div className="space-y-4">
          {/* Partitions (EQ only) */}
          {partitions.length > 0 && (
            <div className="rounded-xl border border-border bg-surface-raised p-4 space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                Partitions ({partitions.length})
              </p>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {partitions.map(p => (
                  <div key={p.id} className="flex items-center gap-2 py-1">
                    <span
                      className={cn(
                        "h-1.5 w-1.5 shrink-0 rounded-full",
                        p.is_valid ? "bg-emerald-500/70" : "bg-red-500/60",
                      )}
                    />
                    <span className="text-[12px] text-slate-400">{p.partition_label}</span>
                    {p.sample_value && (
                      <span className="font-mono text-[11px] text-slate-600">({p.sample_value})</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cases */}
          <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-3">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">Uretilen Senaryolar</p>

            {!result ? (
              <div className="py-12 text-center text-[13px] text-slate-600">Henuz calistirilmadi</div>
            ) : cases.length === 0 ? (
              <div className="py-8 text-center text-[13px] text-slate-600">Senaryo uretilemedi</div>
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
                          <p className="mt-0.5 text-[11px] text-slate-600 line-clamp-1">{c.rationale}</p>
                        )}
                        {c.partition_label && (
                          <p className="mt-0.5 text-[11px] text-slate-600">{c.partition_label}</p>
                        )}
                      </div>
                      {promoted.has(i) ? (
                        <span className="shrink-0 text-[11px] text-emerald-500/70">v</span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => onPromote([i])}
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
                  onClick={() => onPromote(cases.map((_, i) => i).filter(i => !promoted.has(i)))}
                  disabled={isPending || promoted.size === cases.length}
                  className="w-full rounded-xl border border-border py-2 text-[12px] text-slate-400 hover:text-slate-200 disabled:opacity-40 transition-colors"
                >
                  {isPending ? "Kaydediliyor..." : "Tumunu Repository'ye Kaydet"}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* History */}
      <div className="rounded-xl border border-border bg-surface-raised p-5 space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">Onceki Analizler</p>
        {historyQ.isLoading ? (
          <div className="py-6 text-center text-[12px] text-slate-600">Yukleniyor...</div>
        ) : recentRuns.length === 0 ? (
          <div className="py-6 text-center text-[12px] text-slate-600">Henuz gecmis analiz yok</div>
        ) : (
          <div className="space-y-2">
            {recentRuns.map(r => {
              const fieldCount = Array.isArray((r.input_spec as { fields?: unknown[] }).fields)
                ? (r.input_spec as { fields: unknown[] }).fields.length
                : 0;
              return (
                <div
                  key={r.id}
                  className="flex items-center gap-3 rounded-lg border border-border bg-white/[0.02] px-3 py-2.5"
                >
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500/40" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] text-slate-400">
                      {new Date(r.created_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" })}
                    </p>
                    <p className="text-[11px] text-slate-600">
                      {fieldCount} alan · {r.generated_cases.length} case uretildi
                      {r.partitions.length > 0 && ` · ${r.partitions.length} partition`}
                    </p>
                  </div>
                  <a
                    href={`/p/${projectId}/management/repository`}
                    className="shrink-0 rounded border border-border px-2 py-0.5 text-[11px] text-slate-500 hover:text-teal-400 transition-colors"
                  >
                    Case leri Gor
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
