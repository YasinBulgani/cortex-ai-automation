"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/nexus/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Project = { id: string; name: string };

const FAKER_TYPES = [
  { value: "name",       label: "Ad Soyad" },
  { value: "first_name", label: "Ad" },
  { value: "last_name",  label: "Soyad" },
  { value: "email",      label: "E-posta" },
  { value: "phone",      label: "Telefon" },
  { value: "address",    label: "Adres" },
  { value: "city",       label: "Şehir" },
  { value: "company",    label: "Şirket" },
  { value: "text",       label: "Metin" },
  { value: "uuid",       label: "UUID" },
  { value: "number",     label: "Sayı" },
  { value: "date",       label: "Tarih" },
  { value: "boolean",    label: "Boolean" },
];

type SchemaRow = { id: number; colName: string; fakerType: string };

export default function VeriSimulatoru() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState("");

  const [schemaRows, setSchemaRows] = useState<SchemaRow[]>([
    { id: 1, colName: "ad_soyad", fakerType: "name" },
    { id: 2, colName: "email",    fakerType: "email" },
    { id: 3, colName: "telefon",  fakerType: "phone" },
  ]);
  const nextId = useRef(4);
  const [rowCount,   setRowCount]   = useState(10);
  const [simLoading, setSimLoading] = useState(false);
  const [simResult,  setSimResult]  = useState<{ columns: string[]; rows: string[][] } | null>(null);
  const [simErr,     setSimErr]     = useState<string | null>(null);

  const load = useCallback(() => {
    apiFetch<Project[]>("/api/v1/tspm/projects")
      .then((ps) => {
        setProjects(ps);
        setSelectedProject((prev) => prev || ps[0]?.id || "");
      })
      .catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  function addRow() {
    setSchemaRows((p) => [...p, { id: nextId.current++, colName: "", fakerType: "name" }]);
  }
  function removeRow(id: number) {
    setSchemaRows((p) => p.filter((r) => r.id !== id));
  }
  function updateRow(id: number, field: "colName" | "fakerType", val: string) {
    setSchemaRows((p) => p.map((r) => (r.id === id ? { ...r, [field]: val } : r)));
  }

  async function handleSimulate() {
    if (!selectedProject) { setSimErr("Önce bir proje seçin"); return; }
    const schema: Record<string, string> = {};
    for (const r of schemaRows) if (r.colName.trim()) schema[r.colName.trim()] = r.fakerType;
    if (!Object.keys(schema).length) { setSimErr("En az 1 kolon ekleyin"); return; }
    setSimLoading(true); setSimErr(null); setSimResult(null);
    try {
      const res = await apiFetch<{ columns: string[]; rows: string[][] }>(
        `/api/v1/tspm/projects/${selectedProject}/test-data/generate`,
        { method: "POST", json: { schema, count: rowCount, locale: "tr_TR" } },
      );
      setSimResult(res);
    } catch (err) {
      setSimErr(err instanceof Error ? err.message : "Simülasyon başarısız");
    } finally {
      setSimLoading(false);
    }
  }

  function downloadCSV() {
    if (!simResult) return;
    const csv = [simResult.columns, ...simResult.rows]
      .map((r) => r.map((v) => `"${v.replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const a = Object.assign(document.createElement("a"), {
      href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })),
      download: "simulated_data.csv",
    });
    a.click();
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6" data-testid="veri-simulatoru-page">
      <PageHeader
        icon={<span className="text-lg">🧬</span>}
        title="Veri Simülatörü"
        description="Sentetik test verisi üretin"
      />

      {/* Proje seçici */}
      <div className="rounded-lg border border-slate-800 p-4 flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium text-slate-400 shrink-0">Aktif Proje:</span>
        {projects.length === 0 ? (
          <span className="text-sm text-slate-400">Yükleniyor…</span>
        ) : (
          <div className="flex flex-wrap gap-2">
            {projects.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setSelectedProject(p.id)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                  selectedProject === p.id
                    ? "border-blue-500 bg-blue-500/10 text-blue-400"
                    : "border-slate-800 hover:border-blue-500/50"
                }`}
              >
                {p.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Schema builder */}
      <section className="rounded-lg border border-slate-800 overflow-hidden">
        <div className="border-b border-slate-800 bg-slate-800/30 px-4 py-3">
          <h2 className="text-sm font-semibold">Sentetik Veri Üretici</h2>
          <p className="text-xs text-slate-400 mt-0.5">Kolon şemasını tanımlayın, rastgele gerçekçi veri üretin</p>
        </div>

        <div className="p-4 space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Kolon Şeması</span>
              <button type="button" onClick={addRow} className="text-xs text-blue-400 hover:underline">
                + Kolon Ekle
              </button>
            </div>
            {schemaRows.map((row) => (
              <div key={row.id} className="flex items-center gap-2">
                <Input
                  placeholder="kolon_adı"
                  value={row.colName}
                  onChange={(e) => updateRow(row.id, "colName", e.target.value)}
                  className="flex-1 text-xs h-8"
                  data-testid={`col-name-${row.id}`}
                />
                <select
                  value={row.fakerType}
                  onChange={(e) => updateRow(row.id, "fakerType", e.target.value)}
                  className="h-8 rounded border border-slate-800 bg-slate-900 px-2 text-xs"
                  data-testid={`col-type-${row.id}`}
                >
                  {FAKER_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => removeRow(row.id)}
                  disabled={schemaRows.length <= 1}
                  className="text-xs text-red-400 hover:text-red-600 disabled:opacity-30"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400">Satır:</span>
            <input
              type="number"
              value={rowCount}
              min={1}
              max={500}
              onChange={(e) => setRowCount(Number(e.target.value))}
              className="h-8 w-20 rounded border border-slate-800 bg-slate-900 px-2 text-xs"
              data-testid="row-count"
            />
          </div>

          {simErr && <p className="text-xs text-red-600">{simErr}</p>}

          <Button
            type="button"
            onClick={handleSimulate}
            disabled={simLoading}
            className="w-full"
            data-testid="btn-generate"
          >
            {simLoading ? "Üretiliyor…" : "Veri Üret"}
          </Button>

          {simResult && (
            <div className="space-y-2" data-testid="sim-result">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">{simResult.rows.length} satır üretildi</span>
                <button type="button" onClick={downloadCSV} className="text-xs text-blue-400 hover:underline">
                  ↓ CSV İndir
                </button>
              </div>
              <div className="overflow-x-auto rounded border border-slate-800">
                <table className="w-full min-w-[300px] text-xs" data-testid="result-table">
                  <thead className="border-b border-slate-800 bg-slate-800/30">
                    <tr>
                      {simResult.columns.map((c) => (
                        <th key={c} className="px-3 py-2 text-left font-medium">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {simResult.rows.slice(0, 8).map((row, i) => (
                      <tr key={i} className="border-b border-slate-800 last:border-0">
                        {row.map((cell, j) => (
                          <td key={j} className="px-3 py-1.5 text-slate-400 truncate max-w-[140px]">{cell}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                {simResult.rows.length > 8 && (
                  <p className="p-2 text-center text-[11px] text-slate-400">
                    +{simResult.rows.length - 8} satır daha (CSV'de tümü mevcut)
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
