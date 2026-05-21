"use client";

/**
 * Neurex Farm — AI Mobil Senaryo Üretici
 * ---------------------------------------
 * Aktif cihaz + uygulama bağlamıyla kullanıcının doğal dilde yazdığı
 * isteği mobil DSL katalogu üzerinden Gherkin'e çevirir.
 *
 * UX akışı:
 *   1. Textarea'ya doğal dil gir (TR/EN)
 *   2. "Gherkin üret" → backend /automation-suite/mobile/generate
 *   3. Sonuç panelinde Gherkin + eşleşen/bilinmeyen adımlar
 *   4. "Kopyala" veya (ileride) "Koşuma gönder" — mevcut SSE akışına
 *      feature path ile bağlanacak
 *
 * Backend istek sırasında cihaz profilini (platform, OS, viewport) ve
 * yüklenmiş app id'sini payload'a dahil eder — AI model bu bağlamı
 * prompt'a alır.
 */

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import {
  automationSuiteApi,
  type MobileScenarioResponse,
} from "@/lib/dsl-api";

interface DeviceInfo {
  name: string;
  platform: "ios" | "android";
  os: string;
  slug?: string;
}

interface AppInfo {
  package?: string;
  name?: string;
  upload_id?: string;
  filename?: string;
}

export function MobileAiScenarioCard({
  device,
  app,
}: {
  device: DeviceInfo | null;
  app: AppInfo | null;
}) {
  const [description, setDescription] = useState("");
  const [result, setResult] = useState<MobileScenarioResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const mutation = useMutation<MobileScenarioResponse, Error, void>({
    mutationFn: () =>
      automationSuiteApi.generateMobileScenario({
        description: description.trim(),
        device: device ? {
          name: device.name,
          platform: device.platform,
          os: device.os,
          slug: device.slug,
        } : undefined,
        app: app ?? null,
        max_steps: 8,
      }),
    onSuccess: (data) => {
      setResult(data);
      setCopied(false);
    },
    onError: () => {
      setResult(null);
    },
  });

  async function onCopyGherkin() {
    if (!result?.gherkin) return;
    try {
      await navigator.clipboard.writeText(result.gherkin);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* yoksay */
    }
  }

  const canGenerate =
    description.trim().length >= 10 && !mutation.isPending;

  return (
    <div className="rounded-xl border border-violet-500/30 bg-gradient-to-br from-violet-500/10 via-slate-900 to-slate-950 p-4">
      <div className="mb-3 flex items-center gap-2">
        <span>🤖</span>
        <h2 className="text-sm font-semibold text-white">
          AI Mobil Senaryo Üretici
        </h2>
        <span className="ml-auto rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 text-[10px] uppercase tracking-wider text-violet-200">
          ollama + mobil DSL
        </span>
      </div>

      <div className="mb-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
        <span className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-0.5">
          Cihaz: {device ? `${device.name} · ${device.os}` : "Seçilmedi"}
        </span>
        <span className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-0.5">
          App: {app ? app.filename ?? app.package ?? "yüklendi" : "yok"}
        </span>
      </div>

      <label className="block">
        <span className="mb-1 block text-[11px] text-slate-400">
          Senaryoyu doğal dille anlat (TR veya EN)
        </span>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Örn: Uygulama açılır, arama simgesine dokunulur, 'laptop' yazılır, ilk ürün seçilir ve sepete eklenir."
          rows={4}
          className="w-full rounded-lg border border-slate-700 bg-slate-900 p-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-violet-500/50"
          data-testid="mobile-ai-description"
        />
      </label>

      <div className="mt-3 flex items-center justify-between gap-2">
        <span className="text-[11px] text-slate-500">
          {description.trim().length < 10
            ? "En az 10 karakter yazın"
            : `${description.trim().length} karakter`}
        </span>
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={!canGenerate}
          className="rounded-lg bg-violet-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-40"
          data-testid="mobile-ai-generate"
        >
          {mutation.isPending ? "AI düşünüyor…" : "Gherkin üret"}
        </button>
      </div>

      {mutation.error && (
        <div className="mt-3 rounded-lg border border-rose-500/30 bg-rose-500/5 p-3 text-xs text-rose-200">
          Hata: {mutation.error.message}
        </div>
      )}

      {result && (
        <div className="mt-3 space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-[11px] text-slate-400">
              ✓ {result.matched_action_ids.length} adım eşleşti
              {result.unknown_steps.length > 0 && (
                <>
                  {" · "}
                  <span className="text-amber-300">
                    ⚠ {result.unknown_steps.length} bilinmeyen
                  </span>
                </>
              )}
              {" · "}
              <span className="text-slate-600">
                {result.mobile_alias_count} mobil cümlecik tarandı
              </span>
            </div>
            <button
              type="button"
              onClick={onCopyGherkin}
              className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800"
            >
              {copied ? "✓ Kopyalandı" : "Gherkin kopyala"}
            </button>
          </div>

          <pre
            className="max-h-64 overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-3 font-mono text-[12px] text-slate-100"
            data-testid="mobile-ai-gherkin"
          >
            {result.gherkin}
          </pre>

          {result.unknown_steps.length > 0 && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-2 text-[11px] text-amber-200">
              <div className="mb-1 font-semibold">Bilinmeyen adımlar:</div>
              <ul className="list-inside list-disc space-y-0.5">
                {result.unknown_steps.slice(0, 5).map((s, i) => (
                  <li key={i} className="font-mono">
                    {s}
                  </li>
                ))}
              </ul>
              <div className="mt-1 text-[10px] text-amber-300/70">
                Kataloğa eklemek için DSL Sözlüğü &gt; + Yeni Cümlecik.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
