/**
 * Design Tokens — TypeScript erişimi
 *
 * CSS değişkenleri tokens.css'te tanımlı. Burada JS/TS tarafından kullanmak
 * için tip-güvenli helper'lar var. Dinamik stil gerektirmedikçe doğrudan
 * Tailwind class'larını kullan (`bg-surface-raised`, `text-fg-muted` vs.).
 */

import type { ProductFamilyId } from "./product";

// ─── Surface katmanları ─────────────────────────────────────────────────
export const surfaces = {
  base:    "bg-surface-base",
  raised:  "bg-surface-raised",
  overlay: "bg-surface-overlay",
  accent:  "bg-surface-accent",
} as const;

// ─── Foreground ─────────────────────────────────────────────────────────
export const text = {
  default:  "text-fg",
  muted:    "text-fg-muted",
  subtle:   "text-fg-subtle",
  disabled: "text-fg-disabled",
} as const;

// ─── Status pill class'ları (badge'ler için tek satır) ──────────────────
export const statusBadge = {
  success: "bg-success-subtle text-success border border-success/30",
  warning: "bg-warning-subtle text-warning border border-warning/30",
  danger:  "bg-danger-subtle text-danger border border-danger/30",
  info:    "bg-info-subtle text-info border border-info/30",
  neutral: "bg-surface-overlay text-fg-muted border border-border",
} as const;

// ─── Per-product brand metadata ─────────────────────────────────────────
export const productMeta: Record<ProductFamilyId, {
  emoji: string;
  brandClass: string;       // Tailwind text class
  bgClass: string;          // Tailwind bg class
  borderClass: string;
  cssVar: string;           // CSS değişken adı (--product-X)
}> = {
  one:          { emoji: "⚡", brandClass: "text-product-one",          bgClass: "bg-product-one",          borderClass: "border-product-one",          cssVar: "--product-one" },
  studio:       { emoji: "✏️", brandClass: "text-product-studio",       bgClass: "bg-product-studio",       borderClass: "border-product-studio",       cssVar: "--product-studio" },
  service:      { emoji: "🔌", brandClass: "text-product-service",      bgClass: "bg-product-service",      borderClass: "border-product-service",      cssVar: "--product-service" },
  web:          { emoji: "🌐", brandClass: "text-product-web",          bgClass: "bg-product-web",          borderClass: "border-product-web",          cssVar: "--product-web" },
  mobile:       { emoji: "📱", brandClass: "text-product-mobile",       bgClass: "bg-product-mobile",       borderClass: "border-product-mobile",       cssVar: "--product-mobile" },
  data:         { emoji: "💾", brandClass: "text-product-data",         bgClass: "bg-product-data",         borderClass: "border-product-data",         cssVar: "--product-data" },
  management:   { emoji: "📋", brandClass: "text-product-management",   bgClass: "bg-product-management",   borderClass: "border-product-management",   cssVar: "--product-management" },
  intelligence: { emoji: "🧠", brandClass: "text-product-intelligence", bgClass: "bg-product-intelligence", borderClass: "border-product-intelligence", cssVar: "--product-intelligence" },
  "nexus-code": { emoji: "💻", brandClass: "text-product-code",         bgClass: "bg-product-code",         borderClass: "border-product-code",         cssVar: "--product-code" },
};

// ─── Spacing/sizing semantic helpers ────────────────────────────────────
export const density = {
  compact:     { padding: "px-2 py-1",   text: "text-xs",  gap: "gap-1.5" },
  comfortable: { padding: "px-3 py-2",   text: "text-sm",  gap: "gap-2"   },
  spacious:    { padding: "px-4 py-3",   text: "text-base",gap: "gap-3"   },
} as const;

// ─── Focus ring ─────────────────────────────────────────────────────────
export const focusRing      = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface-base";
export const focusRingDanger= "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger focus-visible:ring-offset-2 focus-visible:ring-offset-surface-base";

// ─── Hover/active states ────────────────────────────────────────────────
export const interactive = {
  subtle:   "hover:bg-surface-overlay active:bg-surface-accent transition-colors duration-fast",
  brand:    "hover:bg-brand-soft hover:text-brand-primary transition-colors duration-fast",
  danger:   "hover:bg-danger-subtle hover:text-danger transition-colors duration-fast",
} as const;

// ─── Animation classes ──────────────────────────────────────────────────
export const animate = {
  fadeIn:    "animate-fade-in",
  slideUp:   "animate-slide-up",
  slideDown: "animate-slide-down",
  scaleIn:   "animate-scale-in",
  pulse:     "animate-pulse-soft",
  shimmer:   "animate-shimmer",
} as const;
