"use client";

/**
 * ConsentManager — Anonimizasyon (k-Anonymity + l-Diversity) ayarları ve
 * çalıştırma paneli.
 *
 * Sorumluluklar:
 *  - k-Anonymity ve l-Diversity slider'ları
 *  - Veri girişi (JSON textarea)
 *  - Anonimizasyon tetikleme butonu
 *  - Sonuç metrikleri + anonimize edilmiş veri tablosu
 */

import { SectionCard } from "@/components/nexus/SectionCard";
import type { AnonymizationResult } from "@/lib/hooks/use-synthetic-advanced";

interface ConsentManagerProps {
  sampleDataText: string;
  onSampleDataChange: (value: string) => void;
  kAnon: number;
  onKAnonChange: (value: number) => void;
  lDiv: number;
  onLDivChange: (value: number) => void;
  onAnonymize: () => void;
  isPending: boolean;
  result: AnonymizationResult | null;
}

export function ConsentManager({
  sampleDataText,
  onSampleDataChange,
  kAnon,
  onKAnonChange,
  lDiv,
  onLDivChange,
  onAnonymize,
  isPending,
  result,
}: ConsentManagerProps) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5">
        <p className="text-sm font-medium text-emerald-300 mb-3">k-Anonimlik & l-Cesitlilik</p>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1">k-Anonymity (min. {kAnon})</label>
            <input
              type="range"
              min={2}
              max={20}
              value={kAnon}
              onChange={(e) => onKAnonChange(Number(e.target.value))}
              aria-label="k-Anonymity degeri"
              title="k-Anonymity degeri"
              className="w-full accent-emerald-500"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>2</span><span>10</span><span>20</span>
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">l-Diversity (min. {lDiv})</label>
            <input
              type="range"
              min={1}
              max={10}
              value={lDiv}
              onChange={(e) => onLDivChange(Number(e.target.value))}
              aria-label="l-Diversity degeri"
              title="l-Diversity degeri"
              className="w-full accent-emerald-500"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>1</span><span>5</span><span>10</span>
            </div>
          </div>
        </div>
        <textarea
          value={sampleDataText}
          onChange={(e) => onSampleDataChange(e.target.value)}
          rows={5}
          aria-label="Anonimizasyon veri girişi"
          title="Anonimizasyon veri girişi"
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono resize-none mb-3"
        />
        <button
          onClick={onAnonymize}
          disabled={isPending}
          className="px-4 py-2 text-sm font-semibold text-emerald-300 border border-emerald-500/30 rounded-xl hover:bg-emerald-500/10 transition-all disabled:opacity-50"
        >
          {isPending ? "Anonimize Ediliyor..." : "Anonimize Et"}
        </button>
      </div>

      {result && (
        <div className="space-y-3">
          <div className="grid grid-cols-4 gap-3">
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
              <p className="text-xs text-slate-400 mb-1">Kayit</p>
              <p className="text-2xl font-bold text-white">
                {result.original_count} → {result.output_count}
              </p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
              <p className="text-xs text-slate-400 mb-1">Baskilanan</p>
              <p className="text-2xl font-bold text-amber-400">{result.suppressed_count}</p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
              <p className="text-xs text-slate-400 mb-1">k / l Deger</p>
              <p className="text-2xl font-bold text-emerald-400">
                {result.k_achieved} / {result.l_achieved}
              </p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
              <p className="text-xs text-slate-400 mb-1">Bilgi Kaybi</p>
              <p
                className={`text-2xl font-bold ${
                  result.information_loss > 0.5 ? "text-red-400" : "text-emerald-400"
                }`}
              >
                {(result.information_loss * 100).toFixed(1)}%
              </p>
            </div>
          </div>

          {result.anonymized_data.length > 0 && (
            <SectionCard title="Anonimize Edilmis Veri" noPad>
              <div className="overflow-auto max-h-56">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-slate-800">
                    <tr>
                      {Object.keys(result.anonymized_data[0]).map((col) => (
                        <th
                          key={col}
                          className="px-3 py-2 text-left font-medium text-slate-400 whitespace-nowrap"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {result.anonymized_data.slice(0, 30).map((row, i) => (
                      <tr key={i} className="hover:bg-slate-800/50">
                        {Object.values(row).map((val, j) => (
                          <td key={j} className="px-3 py-1.5 text-slate-300 whitespace-nowrap">
                            {String(val ?? "")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </SectionCard>
          )}
        </div>
      )}
    </div>
  );
}
