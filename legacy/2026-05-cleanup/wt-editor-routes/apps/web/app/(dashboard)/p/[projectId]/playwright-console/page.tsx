"use client";

import { useState } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { cn } from "@/lib/utils";
import { usePlaywrightHealth } from "@/lib/hooks/use-playwright-mcp";

const SAMPLE_OUTPUT = [
  "Running 3 tests using 1 worker",
  "",
  "  ✓ login.spec.ts:5 — should display login form (1.2s)",
  "  ✓ login.spec.ts:12 — should login with valid credentials (2.4s)",
  "  ✗ login.spec.ts:20 — should show error for invalid password (0.8s)",
  "",
  "  2 passed, 1 failed",
  "  Finished in 4.4s",
];

export default function PlaywrightConsolePage() {
  const projectId = useRouteParam("projectId");
  const { data: health, isLoading } = usePlaywrightHealth();
  const [lines, setLines] = useState<string[]>(SAMPLE_OUTPUT);
  const [copied, setCopied] = useState(false);

  const available = health?.status === "ok";

  const handleCopy = async () => {
    await navigator.clipboard.writeText(lines.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="playwright-console-page">
      <PageHeader
        title="Playwright Konsol"
        description="Test koşum çıktısını görüntüleyin"
        badge={
          isLoading ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-emerald-400" />
          ) : available ? (
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
              AKTIF
            </span>
          ) : (
            <span className="rounded-full border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[10px] font-semibold text-red-400">
              BAĞLI DEĞİL
            </span>
          )
        }
      />

      {!isLoading && !available && (
        <SectionCard title="Playwright Bulunamadı">
          <p className="text-sm text-slate-300">
            Playwright MCP servisi şu anda kullanılamıyor. Backend&apos;de Playwright kurulu olduğundan emin olun.
          </p>
          <code className="mt-2 block rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs text-emerald-400 font-mono">
            pip install playwright && playwright install chromium
          </code>
        </SectionCard>
      )}

      {(available || isLoading) && (
        <SectionCard
          title="Konsol Çıktısı"
          right={
            <button
              type="button"
              onClick={handleCopy}
              data-testid="copy-output-btn"
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700 transition-colors"
            >
              {copied ? "✓ Kopyalandı" : "Kopyala"}
            </button>
          }
        >
          <div className="rounded-lg border border-slate-700 bg-slate-950 overflow-hidden">
            <div className="flex items-center gap-2 bg-slate-800 px-3 py-1.5">
              <span className="h-2 w-2 rounded-full bg-red-500" />
              <span className="h-2 w-2 rounded-full bg-yellow-500" />
              <span className="h-2 w-2 rounded-full bg-green-500" />
              <span className="ml-2 text-[11px] text-slate-400 font-mono">playwright output</span>
            </div>
            <div className="h-64 overflow-y-auto p-4 font-mono text-[12px] leading-relaxed">
              {lines.length === 0 ? (
                <span className="text-slate-600">Çıktı bekleniyor...</span>
              ) : (
                lines.map((line, i) => (
                  <div
                    key={i}
                    className={cn(
                      "whitespace-pre-wrap",
                      line.includes("✓") ? "text-emerald-400" :
                      line.includes("✗") ? "text-red-400" :
                      line.includes("passed") ? "text-emerald-400" :
                      line.includes("failed") ? "text-red-400" :
                      "text-slate-300",
                    )}
                  >
                    {line || "\u00A0"}
                  </div>
                ))
              )}
            </div>
          </div>
        </SectionCard>
      )}
    </div>
  );
}
