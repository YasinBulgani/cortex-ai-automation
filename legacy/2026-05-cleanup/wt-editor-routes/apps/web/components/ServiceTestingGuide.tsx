"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import {
  DEFAULT_PRODUCT_FAMILY_ID,
  PRODUCT_FAMILY,
  PRODUCT_FAMILY_STORAGE_KEY,
  getProductFamilyMember,
  type ProductFamilyId,
} from "@/lib/product";

type ServiceTestingStage = "spec" | "chain" | "run";

const STAGES: Array<{
  id: ServiceTestingStage;
  label: string;
  title: string;
  href: (projectId: string) => string;
  priorityProducts: ProductFamilyId[];
}> = [
  {
    id: "spec",
    label: "01",
    title: "Spec ve Risk",
    href: (projectId) => `/p/${projectId}/api-testing`,
    priorityProducts: ["service", "one", "intelligence"],
  },
  {
    id: "chain",
    label: "02",
    title: "Chain Kur",
    href: (projectId) => `/p/${projectId}/chain-builder`,
    priorityProducts: ["service"],
  },
  {
    id: "run",
    label: "03",
    title: "Kos ve Gozlemle",
    href: (projectId) => `/p/${projectId}/api-tests`,
    priorityProducts: ["service", "one", "intelligence"],
  },
];

const DESCRIPTIONS: Record<ServiceTestingStage, string> = {
  spec: "OpenAPI veya Swagger baglamini ice alin, riskli endpointleri secin ve AI ile test adaylari uretin.",
  chain: "Request'leri zincire baglayip veri akisini, extraction kurallarini ve assertion mantigini tasarlayin.",
  run: "Servis testlerini calistirin, sonuc raporlarini inceleyin ve bir sonraki kalite dongusunu belirleyin.",
};

const PRODUCT_NOTES: Record<ServiceTestingStage, Partial<Record<ProductFamilyId, string>>> = {
  spec: {
    one: "Platform cekirdegi icin servis baglami ve entegrasyon riski burada gorunur hale gelir.",
    service: "Service lensinde bu asama ana giris noktasi; spec, risk ve AI test adayi kalitesi burada belirlenir.",
    intelligence: "AI kalite katmani icin grounding ve risk sinyali bu ekranda guclenir.",
  },
  chain: {
    service: "Service urununde asil farklastirici katman burada; extractor, assertion ve stateful akislari burada kurarsiniz.",
    one: "Platform seviyesinde zincirlenmis servis akislarinin ortak modeli burada sabitlenir.",
  },
  run: {
    one: "Platform ritmi ve servis kosu gorunurlugu burada netlesir.",
    service: "Service odaginda gercek kalite sinyali assertion sonuclari ve run davranisindan gelir.",
    intelligence: "AI analizi ve kendini iyilestiren dongu icin taze servis kosu verisi burada uretilir.",
  },
};

function getSafeProductId(value: string | null | undefined): ProductFamilyId {
  return PRODUCT_FAMILY.some((product) => product.id === value)
    ? (value as ProductFamilyId)
    : DEFAULT_PRODUCT_FAMILY_ID;
}

export function ServiceTestingGuide({
  projectId,
  stage,
  className,
}: {
  projectId: string;
  stage: ServiceTestingStage;
  className?: string;
}) {
  const [activeProductId, setActiveProductId] = useState<ProductFamilyId>(DEFAULT_PRODUCT_FAMILY_ID);
  const selectedProduct = getProductFamilyMember(activeProductId);
  const stageConfig = STAGES.find((item) => item.id === stage) ?? STAGES[0];
  const productFocused = stageConfig.priorityProducts.includes(activeProductId);
  const productNote =
    PRODUCT_NOTES[stage][activeProductId] ??
    "Bu akis secili urunu destekleyen genel servis kalite hattinin bir parcasi olarak calisir.";

  useEffect(() => {
    try {
      const raw = localStorage.getItem(PRODUCT_FAMILY_STORAGE_KEY);
      setActiveProductId(getSafeProductId(raw));
    } catch {
      // ignore
    }

    const syncProduct = (event?: Event) => {
      const nextId = event instanceof CustomEvent ? String(event.detail ?? "") : null;
      try {
        const raw = nextId || localStorage.getItem(PRODUCT_FAMILY_STORAGE_KEY);
        setActiveProductId(getSafeProductId(raw));
      } catch {
        // ignore
      }
    };

    window.addEventListener("storage", syncProduct);
    window.addEventListener("bgts-product-family-changed", syncProduct as EventListener);
    return () => {
      window.removeEventListener("storage", syncProduct);
      window.removeEventListener("bgts-product-family-changed", syncProduct as EventListener);
    };
  }, []);

  return (
    <section
      className={cn(
        "rounded-2xl border border-cyan-500/20 bg-gradient-to-br from-cyan-500/10 via-slate-900 to-slate-950 p-4 shadow-[0_0_0_1px_rgba(14,116,144,0.15)]",
        className,
      )}
      data-testid={`service-testing-guide-${stage}`}
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-200/80">Servis Test Akisi</p>
            <span className="rounded-full border border-violet-400/20 bg-violet-500/10 px-2.5 py-1 text-[11px] font-medium text-violet-100">
              {selectedProduct.name}
            </span>
            {productFocused && (
              <span className="rounded-full border border-amber-300/20 bg-amber-400/10 px-2.5 py-1 text-[11px] font-medium text-amber-100">
                Bu urunde oncelikli
              </span>
            )}
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-300">{DESCRIPTIONS[stage]}</p>
          <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/45 px-3 py-2.5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Secili urun icin anlami</p>
            <p className="mt-1 text-sm leading-6 text-slate-300">{productNote}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/p/${projectId}/api-testing`}
            className="rounded-full border border-slate-700 bg-slate-950/50 px-3 py-1.5 text-xs text-slate-300 transition hover:border-slate-500 hover:text-white"
          >
            API Testing AI
          </Link>
          <Link
            href={`/p/${projectId}/api-tests`}
            className="rounded-full border border-slate-700 bg-slate-950/50 px-3 py-1.5 text-xs text-slate-300 transition hover:border-slate-500 hover:text-white"
          >
            API Testleri
          </Link>
          <Link
            href={`/p/${projectId}/chain-builder`}
            className="rounded-full border border-slate-700 bg-slate-950/50 px-3 py-1.5 text-xs text-slate-300 transition hover:border-slate-500 hover:text-white"
          >
            Chain Builder
          </Link>
          <Link
            href={`/p/${projectId}/test-history`}
            className="rounded-full border border-slate-700 bg-slate-950/50 px-3 py-1.5 text-xs text-slate-300 transition hover:border-slate-500 hover:text-white"
          >
            Test Gecmisi
          </Link>
          <Link
            href={`/p/${projectId}/ai-chat`}
            className="rounded-full border border-slate-700 bg-slate-950/50 px-3 py-1.5 text-xs text-slate-300 transition hover:border-slate-500 hover:text-white"
          >
            AI Asistan
          </Link>
        </div>
      </div>

      <div className="mt-4 grid gap-2 md:grid-cols-3">
        {STAGES.map((item, index) => {
          const active = item.id === stage;
          const itemFocused = item.priorityProducts.includes(activeProductId);
          return (
            <Link
              key={item.id}
              href={item.href(projectId)}
              className={cn(
                "rounded-xl border px-3 py-3 transition",
                active
                  ? "border-cyan-300/40 bg-cyan-500/10 text-white"
                  : "border-slate-800 bg-slate-950/40 text-slate-300 hover:border-slate-600 hover:text-white",
              )}
            >
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "inline-flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-semibold",
                    active ? "bg-cyan-300/20 text-cyan-100" : "bg-slate-800 text-slate-400",
                  )}
                >
                  {item.label}
                </span>
                <span className="text-sm font-medium">{item.title}</span>
              </div>
              <p className="mt-2 text-xs text-slate-400">
                {index === 0
                  ? "Spec import, endpoint secimi ve AI test uretimi"
                  : index === 1
                    ? "Durumsal chain, extractor ve assertion baglama"
                    : "Kosu, sonuc analizi ve rapor takibi"}
              </p>
              {itemFocused && (
                <p className="mt-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-amber-200/80">
                  Secili urunde one cikiyor
                </p>
              )}
            </Link>
          );
        })}
      </div>
    </section>
  );
}
