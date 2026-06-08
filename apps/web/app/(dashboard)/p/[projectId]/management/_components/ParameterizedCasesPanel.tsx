"use client";

import { useMemo, useState } from "react";

import {
  type CaseParamSet,
  useAddManualRows,
  useCaseParamSets,
  useCreateParamSet,
  useDataRows,
  useExpandCase,
  useGenerateDataRows,
} from "@/lib/hooks/use-mgmt-design";



interface FieldRow {
  name: string;
  type: string;
  required: boolean;
}

function readFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}

export function ParameterizedCasesPanel({ caseId }: { caseId: string }) {
  const paramSetsQuery = useCaseParamSets(caseId);
  const sets = paramSetsQuery.data ?? [];
  const [selectedSetId, setSelectedSetId] = useState<string | null>(null);
  const activeSet: CaseParamSet | undefined = useMemo(
    () => sets.find((s) => s.id === selectedSetId) ?? sets[0],
    [sets, selectedSetId],
  );

  return (
    <section className="rounded-xl border border-border bg-surface-raised p-5">
      <div className="space-y-4">
        <SchemaEditor caseId={caseId} />
        {paramSetsQuery.isLoading && (
          <p className="text-sm text-fg-subtle">Param setleri yükleniyor...</p>
        )}
        {!paramSetsQuery.isLoading && sets.length === 0 && (
          <p className="text-sm text-fg-subtle">Henüz parametre seti yok. Yukarıdan oluşturun.</p>
        )}
        {sets.length > 0 && (
          <div className="space-y-2">
            <label className="block text-xs uppercase tracking-wide text-fg-muted">
              Aktif param set
            </label>
            <select
              value={activeSet?.id ?? ""}
              onChange={(e) => setSelectedSetId(e.target.value)}
              className="w-full rounded border border-border bg-surface-raised px-2 py-1 text-sm text-white"
            >
              {sets.map((s) => (
                <option key={s.id} value={s.id}>
                  {new Date(s.created_at).toLocaleString("tr-TR")} ·{" "}
                  {(s.schema_json.fields ?? []).length} alan
                </option>
              ))}
            </select>
          </div>
        )}
        {activeSet && <DataTableEditor caseId={caseId} paramSet={activeSet} />}
        <ExpandRow caseId={caseId} />
      </div>
    </section>
  );
}

function SchemaEditor({ caseId }: { caseId: string }) {
  const createParamSet = useCreateParamSet(caseId);
  const [fields, setFields] = useState<FieldRow[]>([{ name: "", type: "string", required: true }]);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const valid = fields.every((f) => f.name.trim().length > 0) && fields.length > 0;

  const update = (idx: number, patch: Partial<FieldRow>) => {
    setFields((prev) => prev.map((f, i) => (i === idx ? { ...f, ...patch } : f)));
  };

  return (
    <div className="rounded-lg border border-border bg-bg p-3">
      <p className="mb-2 text-xs uppercase tracking-wide text-fg-muted">Yeni schema</p>
      <div className="space-y-2">
        {fields.map((f, idx) => (
          <div key={idx} className="grid gap-2 md:grid-cols-[1fr_auto_auto_auto]">
            <input
              value={f.name}
              onChange={(e) => update(idx, { name: e.target.value })}
              placeholder="field name"
              className="rounded border border-border bg-surface-raised px-2 py-1 text-sm text-white"
            />
            <select
              value={f.type}
              onChange={(e) => update(idx, { type: e.target.value })}
              className="rounded border border-border bg-surface-raised px-2 py-1 text-sm text-white"
            >
              <option value="string">string</option>
              <option value="int">int</option>
              <option value="float">float</option>
              <option value="bool">bool</option>
              <option value="date">date</option>
              <option value="enum">enum</option>
            </select>
            <label className="flex items-center gap-1 text-xs text-fg">
              <input
                type="checkbox"
                checked={f.required}
                onChange={(e) => update(idx, { required: e.target.checked })}
              />
              required
            </label>
            <button
              type="button"
              onClick={() => setFields((prev) => prev.filter((_, i) => i !== idx))}
              className="text-xs text-red-300 hover:text-red-200"
            >
              sil
            </button>
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setFields((p) => [...p, { name: "", type: "string", required: false }])}
          className="rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface-overlay"
        >
          + Alan
        </button>
        <button
          type="button"
          disabled={!valid || createParamSet.isPending}
          onClick={async () => {
            setSaveErr(null);
            try {
              await createParamSet.mutateAsync({ fields });
              setFields([{ name: "", type: "string", required: true }]);
            } catch {
              setSaveErr("Schema kaydedilemedi. Lütfen tekrar deneyin.");
            }
          }}
          className="rounded bg-cyan-500 px-3 py-1 text-xs font-semibold text-surface-base hover:bg-cyan-400 disabled:opacity-40"
        >
          {createParamSet.isPending ? "Kaydediliyor..." : "Schema kaydet"}
        </button>
        {saveErr && (
          <p className="w-full text-xs text-red-400">{saveErr}</p>
        )}
      </div>
    </div>
  );
}

function DataTableEditor({ caseId, paramSet }: { caseId: string; paramSet: CaseParamSet }) {
  const rowsQuery = useDataRows(caseId, paramSet.id);
  const generate = useGenerateDataRows(caseId);
  const addManual = useAddManualRows(caseId, paramSet.id);
  const [count, setCount] = useState<number>(5);

  const fieldNames = (paramSet.schema_json.fields ?? []).map((f) => f.name);

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const content = await readFile(file);
    await generate.mutateAsync({
      param_set_id: paramSet.id,
      source: "csv",
      csv_content: content,
    });
    e.target.value = "";
  };

  const handleAddBlankRow = async () => {
    const values: Record<string, unknown> = {};
    for (const name of fieldNames) values[name] = "";
    await addManual.mutateAsync([
      { values, expected: {}, source_type: "manual", category: null },
    ]);
  };

  return (
    <div className="rounded-lg border border-border bg-bg p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs uppercase tracking-wide text-fg-muted">Data rows</p>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-2 text-xs text-fg">
            count
            <input
              type="number"
              min={1}
              max={50}
              value={count}
              onChange={(e) => setCount(Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
              className="w-16 rounded border border-border bg-surface-raised px-2 py-1 text-xs text-white"
            />
          </label>
          <button
            type="button"
            disabled={generate.isPending}
            onClick={() =>
              generate.mutateAsync({
                param_set_id: paramSet.id,
                source: "llm",
                count,
              })
            }
            className="rounded bg-cyan-500 px-3 py-1 text-xs font-semibold text-surface-base hover:bg-cyan-400 disabled:opacity-40"
          >
            {generate.isPending ? "AI üretiyor..." : "AI ile satır üret"}
          </button>
          <label className="cursor-pointer rounded border border-border px-3 py-1 text-xs text-fg hover:bg-surface-overlay">
            CSV yükle
            <input type="file" accept=".csv,text/csv" onChange={handleCsvUpload} className="hidden" />
          </label>
          <button
            type="button"
            onClick={handleAddBlankRow}
            disabled={addManual.isPending}
            className="rounded border border-border px-3 py-1 text-xs text-fg hover:bg-surface-overlay"
          >
            + Boş satır
          </button>
        </div>
      </div>
      <div className="overflow-x-auto rounded border border-border">
        <table className="min-w-full divide-y divide-slate-800 text-xs">
          <thead className="bg-surface-raised uppercase tracking-wide text-fg-muted">
            <tr>
              <th className="px-3 py-2 text-left">#</th>
              <th className="px-3 py-2 text-left">Category</th>
              <th className="px-3 py-2 text-left">Source</th>
              {fieldNames.map((n) => (
                <th key={n} className="px-3 py-2 text-left">
                  {n}
                </th>
              ))}
              <th className="px-3 py-2 text-left">Expected</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-fg">
            {(rowsQuery.data ?? []).map((row, idx) => (
              <tr key={row.id} className="hover:bg-surface-raised">
                <td className="px-3 py-2 font-mono text-fg-subtle">{idx + 1}</td>
                <td className="px-3 py-2">{row.category ?? "—"}</td>
                <td className="px-3 py-2 text-fg-muted">{row.source_type}</td>
                {fieldNames.map((n) => (
                  <td key={n} className="px-3 py-2 font-mono text-[11px]">
                    {String(row.values[n] ?? "")}
                  </td>
                ))}
                <td className="px-3 py-2 font-mono text-[11px] text-fg-muted">
                  {JSON.stringify(row.expected)}
                </td>
              </tr>
            ))}
            {(rowsQuery.data ?? []).length === 0 && (
              <tr>
                <td colSpan={fieldNames.length + 4} className="px-3 py-4 text-center text-fg-subtle">
                  Henüz satır yok.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ExpandRow({ caseId }: { caseId: string }) {
  const expand = useExpandCase(caseId);
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-bg p-3">
      <div>
        <p className="text-sm font-medium text-fg">Expand cases</p>
        <p className="text-xs text-fg-subtle">
          Tüm param setlerindeki satırlar için execution stub üretir.
        </p>
      </div>
      <button
        type="button"
        disabled={expand.isPending}
        onClick={() => expand.mutateAsync()}
        className="rounded bg-brand px-3 py-2 text-sm font-semibold text-white hover:brightness-105 disabled:opacity-40"
      >
        {expand.isPending
          ? "Çalışıyor..."
          : expand.data
            ? `Expanded · ${expand.data.execution_ids.length}`
            : "Expand"}
      </button>
    </div>
  );
}
