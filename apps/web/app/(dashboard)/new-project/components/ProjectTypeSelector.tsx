"use client";

import {
  PRODUCT_FAMILY,
  type ProductFamilyId,
} from "@/lib/product";
import { PRODUCT_AVAILABILITY_META } from "../constants";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ProjectTypeSelectorProps {
  selectedProductId: ProductFamilyId;
  selectedProductName: string;
  selectedProductTagline: string;
  selectedProductAvailability: keyof typeof PRODUCT_AVAILABILITY_META;
  onProductChange: (productId: ProductFamilyId) => void;
}

// ── Mobile product banner (< md) ─────────────────────────────────────────────

export function MobileProductBanner({
  selectedProductId,
  selectedProductName,
  selectedProductTagline,
  selectedProductAvailability,
  onProductChange,
}: ProjectTypeSelectorProps) {
  const availMeta = PRODUCT_AVAILABILITY_META[selectedProductAvailability];
  return (
    <div className="mb-6 rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/10 via-slate-900 to-slate-950 p-4 md:hidden">
      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-violet-200/80">
        Neurex Product Focus
      </p>
      <div className="mt-2 flex items-center gap-2">
        <h2 className="text-lg font-semibold text-white">{selectedProductName}</h2>
        <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${availMeta.className}`}>
          {availMeta.label}
        </span>
      </div>
      <p className="mt-1 text-sm text-violet-200/90">{selectedProductTagline}</p>
      <div className="mt-3 grid grid-cols-2 gap-1.5">
        {PRODUCT_FAMILY.map((product) => (
          <button
            key={product.id}
            type="button"
            onClick={() => onProductChange(product.id)}
            className={`rounded-lg border px-2 py-1.5 text-left transition ${
              product.id === selectedProductId
                ? "border-violet-300/40 bg-violet-400/15 text-violet-50"
                : "border-slate-800 bg-slate-900/60 text-slate-300"
            }`}
          >
            <span className="block text-[10px] font-semibold uppercase tracking-[0.16em]">
              {product.shortName}
            </span>
            <span className="mt-0.5 block text-[11px] leading-snug">{product.tagline}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Sidebar product switcher grid (xl+) ──────────────────────────────────────

export function SidebarProductSwitcher({
  selectedProductId,
  onProductChange,
}: Pick<ProjectTypeSelectorProps, "selectedProductId" | "onProductChange">) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
        Ürünü değiştir
      </p>
      <div className="mt-3 grid grid-cols-2 gap-1.5">
        {PRODUCT_FAMILY.map((product) => (
          <button
            key={product.id}
            type="button"
            onClick={() => onProductChange(product.id)}
            className={`rounded-lg border px-2 py-1.5 text-left transition ${
              product.id === selectedProductId
                ? "border-violet-300/40 bg-violet-400/15 text-violet-50"
                : "border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200"
            }`}
          >
            <span className="block text-[9px] font-semibold uppercase tracking-[0.14em]">
              {product.shortName}
            </span>
            <span className="mt-0.5 block text-[10px] leading-tight">{product.tagline}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
