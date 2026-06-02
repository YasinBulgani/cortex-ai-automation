"use client";

import { useMemo, useState } from "react";

import {
  type DesignDataType,
  type DesignFieldSpec,
  type DesignRun,
  useCreateEqRun,
  usePromoteCases,
} from "@/lib/hooks/use-mgmt-design";

import {
  ManagementPanel,
  ManagementShell,
  ManagementStat,
} from "../../_components/ManagementShell";

const DATA_TYPES: DesignDataType[] = ["int", "float", "string", "date", "bool", "enum"];

function emptyField(): DesignFieldSpec {
  return {
    name: "",
    data_type: "int",
    min_value: "",
    max_value: "",
    allowed_set: null,
    nullable: false,
  };
}

export default function ManagementEqPage({ params }: { params: { projectId: string } }) {
  const createRun = useCreateEqRun();
  const [fields, setFields] = useState<DesignFieldSpec[]>([emptyField()]);
  const [requirementText, setRequirementText] = useState<string>("");
  const [run, setRun] = useState<DesignRun | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const promote = usePromoteCases(run?.id);
  const [promotedIds, setPromotedIds] = useState<string[]>([]);

  const canSubmit = useMemo(
    () => fields.every((f) => f.name.trim().length > 0),
    [fields],
  );

  const update = (idx: number, patch: Partial<DesignFieldSpec>) => {
    setFields((prev) => prev.map((f, i) => (i === idx ? { ...f, ...patch } : f)));
  };

  const submit = async () => {
    setPromotedIds([]);
    setSelected(new Set());
    const payload = {
      project_id: params.projectId,
      fields: fields.map((f) => ({
        ...f,
        min_value: f.min_value || null,
        max_value: f.max_value || null,
      })),
      requirement_text: requirementText,
    };
    const result = await createRun.mutateAsync(payload);
    setRun(result);
  };

  const togglePromote = (idx: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const doPromote = async () => {
    if (!run || selected.size === 0) return;
    const res = await promote.mutateAsync({
      case_indexes: Array.from(selected).sort((a, b) => a - b),
    });
    setPromotedIds(res.case_ids);
    setSelected(new Set());
  };

  return (
    <ManagementShell
      projectId={params.projectId}
      title="Equivalence Partitioning"
      description="Geçerli ve geçersiz sınıflara böl, her sınıf için temsili case üret."
      active="management/design/eq"
    >
      <div className="grid gap-4 md:grid-cols-3">
        <ManagementStat label="Fields" value={String(fields.length)} note="input alanları" />
        <ManagementStat
          label="Partitions"
          value={String(run?.partitions.length ?? 0)}
          note={run ? `source: ${run.source}` : "henüz çalıştırılmadı"}
        />
        <ManagementStat
          label="Promoted"
          value={String(promotedIds.length)}
          note="bu oturumda"
        />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <ManagementPanel title="Field Specs">
          <div className="space-y-3">
            <textarea
              value={requirementText}
              onChange={(e) => setRequirementText(e.target.value)}
              rows={3}
              placeholder="Gereksinim metni (opsiyonel)..."
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
            />
            {fields.map((field, idx) => (
              <div
                key={idx}
                className="space-y-2 rounded-lg border border-slate-800 bg-slate-950/60 p-3"
              >
                <div className="grid gap-2 md:grid-cols-[1fr_auto_auto]">
                  <input
                    value={field.name}
                    onChange={(e) => update(idx, { name: e.target.value })}
                    placeholder="field name"
                    className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-white focus:border-cyan-500 focus:outline-none"
                  />
                  <select
                    value={field.data_type}
                    onChange={(e) =>
                      update(idx, { data_type: e.target.value as DesignDataType })
                    }
                    className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-white"
                  >
                    {DATA_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                  <label className="flex items-center gap-1 text-xs text-slate-300">
                    <input
                      type="checkbox"
                      checked={!!field.nullable}
                      onChange={(e) => update(idx, { nullable: e.target.checked })}
                    />
                    nullable
                  </label>
                </div>
                <div className="grid gap-2 md:grid-cols-2">
                  <input
                    value={field.min_value ?? ""}
                    onChange={(e) => update(idx, { min_value: e.target.value })}
                    placeholder="min"
                    className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-white"
                  />
                  <input
                    value={field.max_value ?? ""}
                    onChange={(e) => update(idx, { max_value: e.target.value })}
                    placeholder="max"
                    className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-white"
                  />
                </div>
                {(field.data_type === "enum" || field.data_type === "bool") && (
                  <input
                    value={Array.isArray(field.allowed_set) ? field.allowed_set.join(",") : ""}
                    onChange={(e) =>
                      update(idx, {
                        allowed_set: e.target.value
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean),
                      })
                    }
                    placeholder="allowed values (virgüllü)"
                    className="w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-white"
                  />
                )}
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() =>
                      setFields((prev) => prev.filter((_, i) => i !== idx))
                    }
                    className="text-xs text-rose-300 hover:text-rose-200"
                  >
                    Alanı sil
                  </button>
                </div>
              </div>
            ))}
            <button
              type="button"
              onClick={() => setFields((prev) => [...prev, emptyField()])}
              className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800"
            >
              + Alan ekle
            </button>
            <button
              type="button"
              disabled={!canSubmit || createRun.isPending}
              onClick={submit}
              className="rounded-lg bg-cyan-500 px-3 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-40"
            >
              {createRun.isPending ? "Üretiliyor..." : "Partition üret"}
            </button>
          </div>
        </ManagementPanel>

        <div className="space-y-4">
          {run && (
            <ManagementPanel title={`Partitions (${run.partitions.length})`}>
              <div className="flex flex-wrap gap-2">
                {run.partitions.map((p) => (
                  <div
                    key={p.id}
                    className={`rounded-lg border px-3 py-2 text-sm ${
                      p.is_valid
                        ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
                        : "border-rose-500/40 bg-rose-500/10 text-rose-200"
                    }`}
                  >
                    <span className="font-medium">{p.partition_label}</span>
                    {p.sample_value !== null && p.sample_value !== undefined && (
                      <span className="ml-2 font-mono text-xs opacity-80">
                        e.g. {p.sample_value}
                      </span>
                    )}
                  </div>
                ))}
                {run.partitions.length === 0 && (
                  <p className="text-sm text-slate-500">Partition üretilemedi.</p>
                )}
              </div>
            </ManagementPanel>
          )}

          <ManagementPanel title={run ? `Generated cases (${run.generated_cases.length})` : "Generated cases"}>
            {!run && <p className="text-sm text-slate-500">Henüz üretim çalıştırılmadı.</p>}
            {run && run.generated_cases.length > 0 && (
              <div className="space-y-3">
                <div className="overflow-x-auto rounded-lg border border-slate-800">
                  <table className="min-w-full divide-y divide-slate-800 text-sm">
                    <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
                      <tr>
                        <th className="px-3 py-2 text-left">✓</th>
                        <th className="px-3 py-2 text-left">Name</th>
                        <th className="px-3 py-2 text-left">Partition</th>
                        <th className="px-3 py-2 text-left">Inputs</th>
                        <th className="px-3 py-2 text-left">Expected</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-slate-200">
                      {run.generated_cases.map((c, idx) => (
                        <tr key={idx} className="hover:bg-slate-900/50">
                          <td className="px-3 py-2">
                            <input
                              type="checkbox"
                              checked={selected.has(idx)}
                              onChange={() => togglePromote(idx)}
                            />
                          </td>
                          <td className="px-3 py-2">{c.name}</td>
                          <td className="px-3 py-2 text-xs text-slate-400">
                            {c.partition_label ?? "—"}
                          </td>
                          <td className="px-3 py-2 font-mono text-xs text-slate-400">
                            {JSON.stringify(c.inputs)}
                          </td>
                          <td className="px-3 py-2 text-xs text-slate-400">{c.expected}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <button
                  type="button"
                  onClick={doPromote}
                  disabled={selected.size === 0 || promote.isPending}
                  className="rounded-lg bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:opacity-40"
                >
                  {promote.isPending ? "Promote..." : `Promote (${selected.size})`}
                </button>
                {promotedIds.length > 0 && (
                  <p className="text-xs text-emerald-300">
                    {promotedIds.length} case başarıyla TestCase repository'sine eklendi.
                  </p>
                )}
              </div>
            )}
          </ManagementPanel>
        </div>
      </div>
    </ManagementShell>
  );
}
