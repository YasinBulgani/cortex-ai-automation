"use client";

import { useState } from "react";
import type { AutomationFile } from "../types";
import { PRODUCT_AVAILABILITY_META } from "../constants";
import type { ProductFamilyId } from "@/lib/product";
import { getProductFamilyMember } from "@/lib/product";

interface ProductGuide {
  title: string;
  description: string;
  recommendedPath: string;
}

interface CompletionStepProps {
  featureFiles: AutomationFile[];
  testFiles: AutomationFile[];
  runOutput: string | null;
  projectId: string | null;
  selectedProductId: ProductFamilyId;
  productGuide: ProductGuide;
  onNavigate: (href: string) => void;
  onGoBackToAutomation: () => void;
}

export function CompletionStep({
  featureFiles,
  testFiles,
  runOutput,
  projectId,
  selectedProductId,
  productGuide,
  onNavigate,
  onGoBackToAutomation,
}: CompletionStepProps) {
  const selectedProduct = getProductFamilyMember(selectedProductId);
  const [activeFile, setActiveFile] = useState<AutomationFile | null>(null);

  function projectEntryHref() {
    if (!projectId) return "/projects";
    const firstSegment = selectedProduct.routeSegments[0];
    return firstSegment ? `/p/${projectId}/${firstSegment}` : `/p/${projectId}`;
  }

  return (
    <div className="space-y-5">
      <div>
        <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-600/20">
          <svg className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-xl font-bold">Proje Hazır!</h2>
        <p className="mt-1 text-sm text-slate-400">
          {featureFiles.length + testFiles.length > 0
            ? `${featureFiles.length} feature + ${testFiles.length} test dosyası üretildi. Dosyaları incele ve projeye git.`
            : "Otomasyon kodu üretildi. Dosyaları incele ve projeye git."}
        </p>
      </div>

      <div className="rounded-xl border border-violet-500/20 bg-violet-500/10 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-200/80">Hazir acilis noktasi</p>
            <p className="mt-2 text-lg font-semibold text-white">{selectedProduct.name}</p>
            <p className="mt-1 text-sm text-slate-300">{productGuide.title}</p>
            <p className="mt-2 text-sm leading-6 text-slate-400">{productGuide.description}</p>
          </div>
          <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${PRODUCT_AVAILABILITY_META[selectedProduct.availability].className}`}>
            {PRODUCT_AVAILABILITY_META[selectedProduct.availability].label}
          </span>
        </div>
      </div>

      {/* Dosya yoksa yeniden üret */}
      {featureFiles.length === 0 && testFiles.length === 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 text-center space-y-3">
          <p className="text-sm text-slate-400">
            Dosyalar yüklenemedi. Tekrar denemek için aşağıdaki butonu kullanın.
          </p>
          <button
            onClick={onGoBackToAutomation}
            className="rounded-xl border border-slate-700 px-5 py-2 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-white"
          >
            ← Otomasyon adımına dön
          </button>
        </div>
      )}

      {/* Dosya gezgini */}
      {(featureFiles.length > 0 || testFiles.length > 0) && (
        <div className="flex gap-4 rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden" style={{ minHeight: 400 }}>
          {/* Sol panel — dosya listesi */}
          <div className="w-56 shrink-0 border-r border-slate-800 p-3 space-y-1">
            {featureFiles.length > 0 && (
              <>
                <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-slate-600">Feature Dosyaları</p>
                {featureFiles.map((f, i) => (
                  <button
                    key={i}
                    onClick={() => setActiveFile(f)}
                    className={`w-full rounded-lg px-3 py-2 text-left text-xs transition
                      ${activeFile?.name === f.name ? "bg-blue-600/20 text-blue-400" : "text-slate-400 hover:bg-slate-800"}`}
                  >
                    📄 {f.name}
                  </button>
                ))}
              </>
            )}
            {testFiles.length > 0 && (
              <>
                <p className="mt-3 px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-slate-600">Test Dosyaları</p>
                {testFiles.map((f, i) => (
                  <button
                    key={i}
                    onClick={() => setActiveFile(f)}
                    className={`w-full rounded-lg px-3 py-2 text-left text-xs transition
                      ${activeFile?.name === f.name ? "bg-blue-600/20 text-blue-400" : "text-slate-400 hover:bg-slate-800"}`}
                  >
                    🧪 {f.name}
                  </button>
                ))}
              </>
            )}
          </div>

          {/* Sağ panel — kod görüntüleyici */}
          <div className="flex-1 overflow-auto p-4">
            {activeFile ? (
              <>
                <p className="mb-3 text-xs font-medium text-slate-500">{activeFile.name}</p>
                <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                  {activeFile.content}
                </pre>
              </>
            ) : (
              <p className="text-sm text-slate-600 mt-4">Sol panelden bir dosya seç</p>
            )}
          </div>
        </div>
      )}

      {/* Çalıştırma çıktısı */}
      {runOutput && (
        <div className="rounded-xl border border-emerald-800 bg-emerald-950/30 p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-emerald-400">Test Sonucu</p>
          <pre className="text-xs text-emerald-300 whitespace-pre-wrap">{runOutput}</pre>
        </div>
      )}

      {/* CTA butonları */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => onNavigate(projectEntryHref())}
          className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
        >
          {selectedProduct.shortName} çalışma alanini ac →
        </button>
        <button
          onClick={() => onNavigate(`/p/${projectId}`)}
          className="rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-white"
        >
          Proje Özetine git
        </button>
        <button
          onClick={() => onNavigate(`/p/${projectId}/${productGuide.recommendedPath}`)}
          className="rounded-xl border border-violet-500/20 bg-violet-500/10 px-6 py-2.5 text-sm font-medium text-violet-100 transition hover:border-violet-400/30 hover:bg-violet-500/15"
        >
          Önerilen adım: {selectedProduct.shortName}
        </button>
        <button
          onClick={() => onNavigate("/")}
          className="rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
        >
          Ana Sayfa
        </button>
      </div>
    </div>
  );
}
