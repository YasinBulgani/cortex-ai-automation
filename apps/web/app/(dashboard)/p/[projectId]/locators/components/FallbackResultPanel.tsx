"use client";

import { useState } from "react";
import type { FallbackResponse, FallbackResult } from "@/lib/hooks/use-locator-intelligence";
import { SectionCard } from "@/components/nexus";

// ── Sub-components ───────────────────────────────────────────────────

function ConfidenceBar({ value, max = 1 }: { value: number; max?: number }) {
  const pct = Math.min(100, (value / max) * 100);
  const color = pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="h-1.5 rounded-full bg-slate-700 overflow-hidden">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        void navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="rounded p-1 text-slate-400 hover:text-white hover:bg-slate-700 transition-all"
      title="Kopyala"
    >
      {copied ? (
        <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
          />
        </svg>
      )}
    </button>
  );
}

// ── Props ────────────────────────────────────────────────────────────

export interface FallbackResultPanelProps {
  result: FallbackResponse;
}

// ── Component ────────────────────────────────────────────────────────

export function FallbackResultPanel({ result }: FallbackResultPanelProps) {
  return (
    <>
      {/* Success/Fail banner */}
      <div
        className={`rounded-xl border px-4 py-4 ${
          result.success
            ? "border-emerald-500/30 bg-emerald-500/10"
            : "border-red-500/30 bg-red-500/10"
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {result.success ? (
              <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ) : (
              <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
            <div>
              <p className={`text-sm font-semibold ${result.success ? "text-emerald-300" : "text-red-300"}`}>
                {result.success ? "Çözüm bulundu!" : "Çözüm bulunamadi"}
              </p>
              {result.best_selector && (
                <p className="font-mono text-xs text-white mt-1">{result.best_selector}</p>
              )}
            </div>
          </div>
          {result.best_selector && <CopyButton text={result.best_selector} />}
        </div>
        <div className="mt-3 flex gap-4 text-xs text-slate-400">
          <span>
            Strateji: <strong className="text-white">{result.strategies_tried}</strong> denendi
          </span>
          <span>
            Toplam: <strong className="text-white">{result.total_latency_ms}ms</strong>
          </span>
          {result.best_strategy && (
            <span>
              Kazanan: <strong className="text-white">{result.best_strategy}</strong>
            </span>
          )}
        </div>
      </div>

      {/* Strategy chain visualization */}
      <SectionCard
        title="Strateji Zinciri"
        icon={
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        }
      >
        <div className="flex gap-3 overflow-x-auto pb-2">
          {result.all_results.map((r: FallbackResult, i: number) => {
            const isWinner = result.success && r.strategy === result.best_strategy && r.found;
            return (
              <div
                key={i}
                className={`flex-shrink-0 w-56 rounded-xl border p-4 ${
                  isWinner
                    ? "border-emerald-500/40 bg-emerald-500/10 ring-1 ring-emerald-500/30"
                    : r.found
                    ? "border-blue-500/30 bg-blue-500/5"
                    : "border-slate-700 bg-slate-900/40"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span
                    className={`text-xs font-bold uppercase tracking-wider ${
                      isWinner ? "text-emerald-400" : "text-slate-300"
                    }`}
                  >
                    {r.strategy}
                  </span>
                  {r.found ? (
                    <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  )}
                </div>

                <p className="font-mono text-[10px] text-slate-400 truncate mb-2" title={r.selector}>
                  {r.selector}
                </p>

                <p className="text-[10px] text-slate-500 mb-1">Guven</p>
                <ConfidenceBar value={r.confidence} />

                <div className="mt-2 flex items-center justify-between text-[10px] text-slate-500">
                  <span>Gecikme</span>
                  <span className="font-mono text-slate-400">{r.latency_ms}ms</span>
                </div>

                <p className="mt-2 text-[10px] text-slate-500 line-clamp-2">{r.reason}</p>

                {isWinner && (
                  <div className="mt-2 rounded-full bg-emerald-500/20 px-2 py-0.5 text-center text-[10px] font-bold text-emerald-400 uppercase tracking-wider">
                    Kazanan
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </SectionCard>

      {/* Best result detail */}
      {result.success && result.best_selector && (
        <SectionCard
          title="En Iyi Sonuç"
          icon={
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
              />
            </svg>
          }
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs text-slate-500 mb-1">Selector</p>
              <div className="flex items-center gap-2">
                <code className="font-mono text-sm text-emerald-300 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20 flex-1 truncate">
                  {result.best_selector}
                </code>
                <CopyButton text={result.best_selector} />
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-500 mb-1">Strateji</p>
              <p className="text-sm font-medium text-white">{result.best_strategy}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 mb-1">Guven Skoru</p>
              <ConfidenceBar value={result.best_confidence} />
            </div>
            <div>
              <p className="text-xs text-slate-500 mb-1">Stabilite Skoru</p>
              <ConfidenceBar value={result.best_stability} max={5} />
            </div>
          </div>
        </SectionCard>
      )}
    </>
  );
}
