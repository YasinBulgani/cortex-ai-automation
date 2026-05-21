/**
 * Ürün ailesi ve görünür shell kimliği sabitleri.
 *
 * Bu dosya artık ince bir compose+re-export katmanıdır. Her ürünün manifest
 * ve landing içeriği kendi @neurex/product-{id} paketinde yaşar; ortak tip
 * ve route katalogu @neurex/product-kit'te tutulur.
 *
 * Public API (PRODUCT_FAMILY, PROJECT_NAV_DEFINITIONS, helper fonksiyonlar)
 * geriye dönük olarak aynen korunur — mevcut tüketici kod değişmeden çalışır.
 */

import {
  composeProductRegistry,
  DEFAULT_PRODUCT_FAMILY_ID as KIT_DEFAULT_PRODUCT_FAMILY_ID,
  NAV_GROUP_LABELS as KIT_NAV_GROUP_LABELS,
  NAV_GROUP_ORDER as KIT_NAV_GROUP_ORDER,
  PRODUCT_AVAILABILITY_META as KIT_PRODUCT_AVAILABILITY_META,
  PRODUCT_FAMILY_STORAGE_KEY as KIT_PRODUCT_FAMILY_STORAGE_KEY,
  ROUTE_BY_KEY,
  isValidProductFamilyId as kitIsValidProductFamilyId,
} from "@neurex/product-kit";
import type {
  AppRouteKey,
  NavGroupKey,
  ProductAvailability,
  ProductAvailabilityMeta,
  ProductFamilyId,
  ProductFamilyMember,
  ProductLandingContent,
  ProjectNavDefinition,
  ProjectNavLink,
} from "@neurex/product-kit";

import productCode from "@neurex/product-code";
import productData from "@neurex/product-data";
import productIntelligence from "@neurex/product-intelligence";
import productMobile from "@neurex/product-mobile";
import productOne from "@neurex/product-one";
import productService from "@neurex/product-service";
import productStudio from "@neurex/product-studio";
import productWeb from "@neurex/product-web";

// ─── Tip yeniden ihracı (eski tüketiciler için) ──────────────────────────
export type {
  AppRouteKey,
  NavGroupKey,
  ProductAvailability,
  ProductAvailabilityMeta,
  ProductFamilyId,
  ProductFamilyMember,
  ProductLandingContent,
  ProjectNavDefinition,
  ProjectNavLink,
};

// ─── Sabit yeniden ihracı ────────────────────────────────────────────────
export const PRODUCT_FAMILY_STORAGE_KEY = KIT_PRODUCT_FAMILY_STORAGE_KEY;
export const PRODUCT_AVAILABILITY_META = KIT_PRODUCT_AVAILABILITY_META;
export const NAV_GROUP_LABELS = KIT_NAV_GROUP_LABELS;
export const NAV_GROUP_ORDER: string[] = [...KIT_NAV_GROUP_ORDER];
export const DEFAULT_PRODUCT_FAMILY_ID = KIT_DEFAULT_PRODUCT_FAMILY_ID;

// ─── Marka sabitleri (uygulama-özel; pakete taşınmadı) ───────────────────
const ENV_BRAND_NAME =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_APP_NAME) || "";

const DEFAULT_BRAND_NAME = "Neurex";
const DEFAULT_PLATFORM_NAME = "Neurex One";
const DEFAULT_SHELL_NAME = "Neurex QA Operations";

export const PLATFORM_BRAND = {
  name: ENV_BRAND_NAME || DEFAULT_BRAND_NAME,
  platformName: ENV_BRAND_NAME ? `${ENV_BRAND_NAME} One` : DEFAULT_PLATFORM_NAME,
  vision: "Test senaryolarını tasarla, otomasyona dönüştür ve çalıştır.",
  shellName: ENV_BRAND_NAME ? `${ENV_BRAND_NAME} Operations` : DEFAULT_SHELL_NAME,
  shellShort: ENV_BRAND_NAME || DEFAULT_BRAND_NAME,
} as const;

export const PRODUCT_NAME = PLATFORM_BRAND.shellName;
export const PRODUCT_TAGLINE =
  "Test operasyonlarını tek omurgada tasarla, çalıştır ve gözlemle.";
export const PRODUCT_SHORT = PLATFORM_BRAND.shellShort;
export const PRODUCT_VERSION = "2.0.0-demo";

// ─── Compose: tüm ürün paketlerini tek registry'de topla ─────────────────
const REGISTRY = composeProductRegistry([
  productOne,
  productStudio,
  productService,
  productWeb,
  productMobile,
  productData,
  productIntelligence,
  productCode,
]);

export const PROJECT_NAV_DEFINITIONS: ProjectNavDefinition[] = REGISTRY.navDefinitions;
export const PRODUCT_FAMILY: ProductFamilyMember[] = REGISTRY.members;
export const PRODUCT_FAMILY_BY_ID: Record<string, ProductFamilyMember> = REGISTRY.byId;
export const PRODUCT_LANDING_CONTENT: Record<ProductFamilyId, ProductLandingContent> =
  REGISTRY.landingById;

// ─── Yardımcı fonksiyonlar (eski API yüzeyi, davranış aynı) ──────────────
export function getProductFamilyMember(id: ProductFamilyId): ProductFamilyMember {
  return PRODUCT_FAMILY_BY_ID[id] ?? PRODUCT_FAMILY_BY_ID[DEFAULT_PRODUCT_FAMILY_ID];
}

export function getRoutesForProduct(productId: ProductFamilyId): ProjectNavDefinition[] {
  return PROJECT_NAV_DEFINITIONS.filter((route) => route.productIds.includes(productId));
}

export function getPrimaryRoutesForProduct(productId: ProductFamilyId): ProjectNavDefinition[] {
  return getRoutesForProduct(productId).filter(
    (route) => route.path !== null && route.path !== "",
  );
}

export function getRouteDefinition(key: AppRouteKey): ProjectNavDefinition | undefined {
  return PROJECT_NAV_DEFINITIONS.find((route) => route.key === key);
}

export function getDefaultEntryRouteForProduct(
  productId: ProductFamilyId,
): ProjectNavDefinition | undefined {
  const member = getProductFamilyMember(productId);
  return getRouteDefinition(member.defaultEntryKey);
}

export function getDefaultEntrySegmentForProduct(productId: ProductFamilyId): string {
  return getDefaultEntryRouteForProduct(productId)?.segment ?? "";
}

export function getProductBySegment(segment?: string | null): ProductFamilyMember {
  if (!segment) return PRODUCT_FAMILY_BY_ID[DEFAULT_PRODUCT_FAMILY_ID];
  const route = PROJECT_NAV_DEFINITIONS.find((candidate) => candidate.segment === segment);
  const productId = route?.productIds[0];
  return productId && PRODUCT_FAMILY_BY_ID[productId]
    ? PRODUCT_FAMILY_BY_ID[productId]
    : PRODUCT_FAMILY_BY_ID[DEFAULT_PRODUCT_FAMILY_ID];
}

export function isSegmentInProduct(
  _productId: ProductFamilyId,
  segment?: string | null,
): boolean {
  if (!segment) return true;
  return PROJECT_NAV_DEFINITIONS.some((route) => route.segment === segment);
}

const EXTRA_ROUTE_SEGMENT_LABELS: Record<string, string> = {
  "new-project": "Yeni Proje",
  profile: "Profil",
  projects: "Projeler",
};

export const ROUTE_SEGMENT_LABELS: Record<string, string> = PROJECT_NAV_DEFINITIONS.reduce(
  (labels, route) => {
    if (!(route.segment in labels)) {
      labels[route.segment] = route.label;
    }
    return labels;
  },
  { ...EXTRA_ROUTE_SEGMENT_LABELS, "": "Proje Özeti" } as Record<string, string>,
);

export function getSegmentLabel(segment?: string | null): string {
  if (!segment) return ROUTE_SEGMENT_LABELS[""];
  return ROUTE_SEGMENT_LABELS[segment] ?? segment;
}

export function isValidProductFamilyId(
  value: string | null | undefined,
): value is ProductFamilyId {
  return kitIsValidProductFamilyId(value, REGISTRY);
}

export function getProductEntryHref(
  projectId: string | null | undefined,
  productId: ProductFamilyId,
): string {
  if (!projectId) return "/projects";
  const entry = getDefaultEntryRouteForProduct(productId);
  if (!entry || !entry.path) return `/p/${projectId}`;
  return `/p/${projectId}/${entry.path}`;
}

export function getProductLandingHref(productId: ProductFamilyId): string {
  return `/products/${productId}`;
}

export function getProjectPrimaryNav(projectId: string): ProjectNavLink[] {
  return PROJECT_NAV_DEFINITIONS.map((item) => ({
    ...item,
    href:
      item.path === null
        ? "/info/whats-new"
        : item.path
          ? `/p/${projectId}/${item.path}`
          : `/p/${projectId}`,
  }));
}

// ROUTE_BY_KEY'yi de re-export et — Faz 2'de productId scope kontrolü için
// kullanılacak.
export { ROUTE_BY_KEY };
