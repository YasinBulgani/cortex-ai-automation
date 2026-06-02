"use client";

/**
 * FailureAnalysisTable — Manuel test senaryoları tablosu.
 *
 * Sorumluluklar:
 *  - AI tarafından üretilen manuel test senaryolarını listeler
 *  - Her test için aksiyon/beklenen sonuç adımlarını tablo olarak gösterir
 *  - "Projeye Kaydet" aksiyonunu parent'a callback ile iletir
 *  - Boş durum mesajı
 */

import { Button } from "@/components/ui/button";

type ManualTestStep = {
  action: string;
  expected: string;
};

type ManualTest = {
  title: string;
  steps: ManualTestStep[];
};

interface FailureAnalysisTableProps {
  tests: ManualTest[];
  onSave: (
    title: string,
    steps: ManualTestStep[],
    isBdd: boolean
  ) => void;
}

export function FailureAnalysisTable({ tests, onSave }: FailureAnalysisTableProps) {
  if (tests.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 p-8 text-center">
        <p className="text-slate-400">
          Henuz manuel test uretilmedi. Analiz sekmesinden baslayin.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {tests.map((t, i) => (
        <div key={i} className="rounded-lg border border-slate-800 p-4">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">{t.title}</h3>
            <Button
              type="button"
              variant="secondary"
              className="h-7 px-2 text-xs"
              onClick={() => onSave(t.title, t.steps, false)}
            >
              Projeye Kaydet
            </Button>
          </div>
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs text-slate-400">
                <th className="w-8 pb-2 text-center">#</th>
                <th className="pb-2">Aksiyon</th>
                <th className="pb-2">Beklenen Sonuc</th>
              </tr>
            </thead>
            <tbody>
              {t.steps.map((s, j) => (
                <tr key={j} className="border-b border-slate-800/50 last:border-0">
                  <td className="py-2 text-center text-xs text-slate-400">{j + 1}</td>
                  <td className="py-2">{s.action}</td>
                  <td className="py-2 text-green-700 dark:text-green-400">{s.expected}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
