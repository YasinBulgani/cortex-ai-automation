"use client";

/**
 * Test data parameterization UI — A5.
 *
 * CSV/Excel data table binding. Scenario detail sayfasında inline edit;
 * her row bir test iteration'ı oluşturur.
 */

import { useCallback, useEffect, useState } from "react";

export type DataRow = Record<string, string>;

type Props = {
  initialColumns?: string[];
  initialRows?: DataRow[];
  onChange?: (columns: string[], rows: DataRow[]) => void;
  storageKey?: string; // optional localStorage persistence
};

export function DataParameterTable({
  initialColumns = ["param1", "param2"],
  initialRows = [],
  onChange,
  storageKey,
}: Props) {
  const [columns, setColumns] = useState<string[]>(initialColumns);
  const [rows, setRows] = useState<DataRow[]>(initialRows);

  // Load from storage
  useEffect(() => {
    if (!storageKey) return;
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed.columns)) setColumns(parsed.columns);
        if (Array.isArray(parsed.rows)) setRows(parsed.rows);
      }
    } catch {
      /* ignore */
    }
  }, [storageKey]);

  // Save + notify on change
  const persist = useCallback(
    (cols: string[], rs: DataRow[]) => {
      setColumns(cols);
      setRows(rs);
      onChange?.(cols, rs);
      if (storageKey) {
        try {
          localStorage.setItem(storageKey, JSON.stringify({ columns: cols, rows: rs }));
        } catch {
          /* ignore */
        }
      }
    },
    [onChange, storageKey],
  );

  const addRow = () => {
    const blank: DataRow = {};
    columns.forEach((c) => {
      blank[c] = "";
    });
    persist(columns, [...rows, blank]);
  };

  const removeRow = (idx: number) => {
    persist(
      columns,
      rows.filter((_, i) => i !== idx),
    );
  };

  const updateCell = (rowIdx: number, col: string, value: string) => {
    const next = rows.map((r, i) =>
      i === rowIdx ? { ...r, [col]: value } : r,
    );
    persist(columns, next);
  };

  const addColumn = () => {
    const name = prompt("Sütun adı:");
    if (!name || columns.includes(name)) return;
    const newCols = [...columns, name];
    const newRows = rows.map((r) => ({ ...r, [name]: "" }));
    persist(newCols, newRows);
  };

  const removeColumn = (col: string) => {
    if (columns.length <= 1) return;
    const newCols = columns.filter((c) => c !== col);
    const newRows = rows.map((r) => {
      const { [col]: _, ...rest } = r;
      return rest;
    });
    persist(newCols, newRows);
  };

  const importCsv = (csv: string) => {
    const lines = csv.trim().split(/\r?\n/);
    if (lines.length < 1) return;
    const headers = lines[0].split(",").map((h) => h.trim());
    const newRows: DataRow[] = lines.slice(1).map((line) => {
      const values = line.split(",").map((v) => v.trim());
      const row: DataRow = {};
      headers.forEach((h, i) => {
        row[h] = values[i] ?? "";
      });
      return row;
    });
    persist(headers, newRows);
  };

  return (
    <div className="space-y-3" data-testid="data-parameter-table">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Test Veri Parametreleri</h3>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={addColumn}
            className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
            data-testid="data-param-add-column"
          >
            + Sütun
          </button>
          <button
            type="button"
            onClick={addRow}
            className="rounded-md bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-500"
            data-testid="data-param-add-row"
          >
            + Satır
          </button>
        </div>
      </div>

      <div className="overflow-auto rounded-lg border border-slate-800">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-slate-900">
              <th className="px-2 py-1 text-left font-medium text-slate-500">#</th>
              {columns.map((col) => (
                <th key={col} className="px-2 py-1 text-left font-medium text-slate-300">
                  <div className="flex items-center gap-1">
                    <span>{col}</span>
                    <button
                      type="button"
                      onClick={() => removeColumn(col)}
                      className="text-slate-600 hover:text-red-400"
                      title={`Sütun '${col}' sil`}
                      aria-label={`Sütun ${col} sil`}
                      data-testid={`data-param-remove-column-${col}`}
                    >
                      ×
                    </button>
                  </div>
                </th>
              ))}
              <th className="w-8" />
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length + 2}
                  className="px-4 py-6 text-center text-slate-500"
                  data-testid="data-param-empty"
                >
                  Satır yok — "+ Satır" ile ekle
                </td>
              </tr>
            ) : (
              rows.map((row, i) => (
                <tr key={i} className="border-t border-slate-800" data-testid={`data-param-row-${i}`}>
                  <td className="px-2 py-1 text-slate-600">{i + 1}</td>
                  {columns.map((col) => (
                    <td key={col} className="px-1 py-0.5">
                      <input
                        type="text"
                        value={row[col] ?? ""}
                        onChange={(e) => updateCell(i, col, e.target.value)}
                        className="w-full rounded border border-transparent bg-transparent px-1 py-0.5 text-slate-200 focus:border-slate-700 focus:outline-none"
                        data-testid={`data-param-cell-${i}-${col}`}
                      />
                    </td>
                  ))}
                  <td className="px-1 py-1 text-right">
                    <button
                      type="button"
                      onClick={() => removeRow(i)}
                      className="text-slate-600 hover:text-red-400"
                      aria-label={`Satır ${i + 1} sil`}
                      data-testid={`data-param-remove-row-${i}`}
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <details className="text-xs text-slate-500">
        <summary className="cursor-pointer hover:text-slate-300">CSV içe aktar</summary>
        <textarea
          rows={4}
          placeholder="param1,param2,param3&#10;deger1,deger2,deger3"
          className="mt-2 w-full rounded border border-slate-700 bg-slate-900 p-2 font-mono text-xs"
          onBlur={(e) => {
            if (e.target.value.trim()) importCsv(e.target.value);
          }}
          data-testid="data-param-csv-input"
        />
      </details>
    </div>
  );
}
