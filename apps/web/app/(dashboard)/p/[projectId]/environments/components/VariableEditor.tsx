"use client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface VarRow {
  key: string;
  value: string;
  sensitive?: boolean;
  revealed?: boolean;
}

const SUGGESTED_KEYS = [
  "base_url",
  "auth_token",
  "api_key",
  "timeout",
  "tckn",
  "username",
  "password",
];

// ── Props ─────────────────────────────────────────────────────────────────────

export interface VariableEditorProps {
  rows: VarRow[];
  onAdd: () => void;
  onUpdate: (idx: number, patch: Partial<VarRow>) => void;
  onRemove: (idx: number) => void;
  onAddSuggestion: (key: string) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function VariableEditor({
  rows,
  onAdd,
  onUpdate,
  onRemove,
  onAddSuggestion,
}: VariableEditorProps) {
  const btnSecondary =
    "inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition-colors";

  return (
    <div>
      {rows.length === 0 ? (
        <p className="text-sm text-slate-500 text-center py-4">
          Henüz değişken eklenmedi. Aşağıdan değişken ekleyin veya bir şablon
          uygulayın.
        </p>
      ) : (
        <div className="space-y-2">
          {/* Header */}
          <div className="grid grid-cols-12 gap-2 px-1 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
            <div className="col-span-4">Anahtar</div>
            <div className="col-span-6">Değer</div>
            <div className="col-span-2 text-center">Eylem</div>
          </div>
          {rows.map((row, idx) => (
            <div
              key={idx}
              className="grid grid-cols-12 gap-2 items-center rounded-lg bg-slate-800/40 p-2"
            >
              {/* Key */}
              <div className="col-span-4">
                <input
                  type="text"
                  className="w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 font-mono text-xs text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none"
                  value={row.key}
                  onChange={(e) => onUpdate(idx, { key: e.target.value })}
                  placeholder="key"
                />
              </div>
              {/* Value — masked if sensitive and not revealed */}
              <div className="col-span-6 relative">
                <input
                  type={row.sensitive && !row.revealed ? "password" : "text"}
                  className="w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 font-mono text-xs text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none pr-8"
                  value={row.value}
                  onChange={(e) => onUpdate(idx, { value: e.target.value })}
                  placeholder={row.sensitive ? "••••••••" : "değer"}
                />
                {row.sensitive && (
                  <button
                    type="button"
                    onClick={() => onUpdate(idx, { revealed: !row.revealed })}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    title={row.revealed ? "Gizle" : "Göster"}
                  >
                    {row.revealed ? "🙈" : "👁"}
                  </button>
                )}
              </div>
              {/* Actions: sensitive toggle + delete */}
              <div className="col-span-2 flex items-center justify-center gap-1">
                <button
                  type="button"
                  onClick={() =>
                    onUpdate(idx, { sensitive: !row.sensitive })
                  }
                  className={`rounded p-1 text-xs transition-colors ${
                    row.sensitive
                      ? "text-amber-400 bg-amber-500/10"
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                  title={row.sensitive ? "Hassas (gizli)" : "Normal"}
                >
                  {row.sensitive ? "🔒" : "🔓"}
                </button>
                <button
                  type="button"
                  onClick={() => onRemove(idx)}
                  className="rounded p-1 text-slate-500 hover:text-red-400 transition-colors"
                  title="Sil"
                >
                  🗑
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add row + suggestions */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button type="button" className={btnSecondary} onClick={onAdd}>
          + Değişken Ekle
        </button>
        <span className="text-xs text-slate-600 mx-1">|</span>
        {SUGGESTED_KEYS.filter((k) => !rows.some((r) => r.key === k)).map(
          (k) => (
            <button
              key={k}
              type="button"
              className="rounded-full border border-slate-700 bg-slate-800/60 px-2.5 py-0.5 text-[11px] font-mono text-slate-400 hover:border-blue-500/40 hover:text-blue-400 transition-colors"
              onClick={() => onAddSuggestion(k)}
            >
              + {k}
            </button>
          ),
        )}
      </div>
    </div>
  );
}
