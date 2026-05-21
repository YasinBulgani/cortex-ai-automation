/**
 * Ürün ailesi ve görünür shell kimliği sabitleri.
 */

export type ProductFamilyId =
  | "one"
  | "studio"
  | "service"
  | "web"
  | "mobile"
  | "data"
  | "intelligence";

export type ProductAvailability = "core" | "active" | "beta" | "embedded";
export type AppRouteKey = string;
export type NavGroupKey = "" | "Tasarla" | "Otomasyon" | "AI";

export type ProductFamilyMember = {
  id: ProductFamilyId;
  name: string;
  shortName: string;
  tagline: string;
  description: string;
  availability: ProductAvailability;
  defaultEntryKey: AppRouteKey;
  routeSegments: string[];
};

export type ProductAvailabilityMeta = {
  label: string;
  className: string;
};

export type ProjectNavDefinition = {
  key: AppRouteKey;
  path: string | null;
  segment: string;
  label: string;
  group: NavGroupKey;
  productIds: ProductFamilyId[];
};

export type ProjectNavLink = ProjectNavDefinition & {
  href: string;
};

export const PRODUCT_FAMILY_STORAGE_KEY = "bgts_product_family_focus";

export const PRODUCT_AVAILABILITY_META: Record<ProductAvailability, ProductAvailabilityMeta> = {
  core: { label: "Core", className: "border-sky-400/20 bg-sky-500/10 text-sky-200" },
  active: { label: "Active", className: "border-emerald-400/20 bg-emerald-500/10 text-emerald-200" },
  beta: { label: "Beta", className: "border-amber-400/20 bg-amber-500/10 text-amber-200" },
  embedded: { label: "Embedded", className: "border-violet-400/20 bg-violet-500/10 text-violet-200" },
};

export const PLATFORM_BRAND = {
  name: "Visium",
  platformName: "Visium One",
  vision:
    "Test senaryolarını tasarla, otomasyona dönüştür ve çalıştır.",
  shellName: "Visium Operations",
  shellShort: "Visium",
} as const;

export const PRODUCT_NAME = PLATFORM_BRAND.shellName;

export const PRODUCT_TAGLINE =
  "Test operasyonlarını tek omurgada tasarla, çalıştır ve gözlemle.";

export const PRODUCT_SHORT = PLATFORM_BRAND.shellShort;

export const PRODUCT_VERSION = "2.0.0-demo";

export const NAV_GROUP_LABELS: Record<string, string> = {
  Tasarla: "Tasarla",
  Otomasyon: "Otomasyon",
  AI: "AI",
};

const ALL_PRODUCTS: ProductFamilyId[] = ["one", "studio", "service", "web", "mobile", "data", "intelligence"];

export const PROJECT_NAV_DEFINITIONS: ProjectNavDefinition[] = [
  { key: "project-overview", path: "", segment: "", label: "Proje Özeti", group: "", productIds: ALL_PRODUCTS },
  { key: "scenarios", path: "scenarios", segment: "scenarios", label: "Senaryolar", group: "Tasarla", productIds: ALL_PRODUCTS },
  { key: "test-cases", path: "test-cases", segment: "test-cases", label: "AI Test Case", group: "Tasarla", productIds: ALL_PRODUCTS },
  { key: "automation-gen", path: "automation-gen", segment: "automation-gen", label: "Otomasyon Üret", group: "Otomasyon", productIds: ALL_PRODUCTS },
  { key: "executions", path: "executions", segment: "executions", label: "Koşular", group: "Otomasyon", productIds: ALL_PRODUCTS },
  { key: "runs", path: "runs", segment: "runs", label: "Koşu Geçmişi", group: "Otomasyon", productIds: ALL_PRODUCTS },
  { key: "reports", path: "reports", segment: "reports", label: "Raporlar", group: "Otomasyon", productIds: ALL_PRODUCTS },
  { key: "ai-chat", path: "ai-chat", segment: "ai-chat", label: "AI Asistan", group: "AI", productIds: ALL_PRODUCTS },
  { key: "nl-test-gen", path: "nl-test-gen", segment: "nl-test-gen", label: "NL Test Üretici", group: "AI", productIds: ALL_PRODUCTS },
  { key: "qa-orchestrator", path: "qa-orchestrator", segment: "qa-orchestrator", label: "QA Orkestratör", group: "AI", productIds: ALL_PRODUCTS },
  { key: "ai-metrics", path: "ai-metrics", segment: "ai-metrics", label: "LLM Metrikleri", group: "AI", productIds: ALL_PRODUCTS },
  { key: "settings", path: "settings", segment: "settings", label: "Ayarlar", group: "", productIds: ALL_PRODUCTS },
];

type ProductFamilySeed = Omit<ProductFamilyMember, "routeSegments">;

const PRODUCT_FAMILY_SEEDS: ProductFamilySeed[] = [
  {
    id: "one",
    name: "Visium One",
    shortName: "One",
    tagline: "Platform çekirdeği",
    description: "Test otomasyon platformu.",
    availability: "core",
    defaultEntryKey: "scenarios",
  },
];

function uniqueSegments(segments: string[]): string[] {
  return [...new Set(segments.filter(Boolean))];
}

export function getRoutesForProduct(productId: ProductFamilyId): ProjectNavDefinition[] {
  return PROJECT_NAV_DEFINITIONS.filter((route) => route.productIds.includes(productId));
}

export function getPrimaryRoutesForProduct(productId: ProductFamilyId): ProjectNavDefinition[] {
  return getRoutesForProduct(productId).filter((route) => route.path !== null && route.path !== "");
}

function getRouteSegmentsForProduct(productId: ProductFamilyId): string[] {
  return uniqueSegments(getPrimaryRoutesForProduct(productId).map((route) => route.segment));
}

export const PRODUCT_FAMILY: ProductFamilyMember[] = PRODUCT_FAMILY_SEEDS.map((product) => ({
  ...product,
  routeSegments: getRouteSegmentsForProduct(product.id),
}));

export const PRODUCT_FAMILY_BY_ID = Object.fromEntries(
  PRODUCT_FAMILY.map((product) => [product.id, product]),
) as Record<string, ProductFamilyMember>;

export const DEFAULT_PRODUCT_FAMILY_ID: ProductFamilyId = "one";

export function getProductFamilyMember(id: ProductFamilyId): ProductFamilyMember {
  return PRODUCT_FAMILY_BY_ID[id] ?? PRODUCT_FAMILY_BY_ID[DEFAULT_PRODUCT_FAMILY_ID];
}

export function getRouteDefinition(key: AppRouteKey): ProjectNavDefinition | undefined {
  return PROJECT_NAV_DEFINITIONS.find((route) => route.key === key);
}

export function getDefaultEntryRouteForProduct(productId: ProductFamilyId): ProjectNavDefinition | undefined {
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

export function isSegmentInProduct(_productId: ProductFamilyId, segment?: string | null): boolean {
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

export function isValidProductFamilyId(value: string | null | undefined): value is ProductFamilyId {
  return PRODUCT_FAMILY.some((product) => product.id === value);
}

export function getProductEntryHref(
  projectId: string | null | undefined,
  _productId: ProductFamilyId,
): string {
  if (!projectId) return "/projects";
  return `/p/${projectId}`;
}

export function getProjectPrimaryNav(projectId: string): ProjectNavLink[] {
  return PROJECT_NAV_DEFINITIONS.map((item) => ({
    ...item,
    href: item.path === null ? "/info/whats-new" : item.path ? `/p/${projectId}/${item.path}` : `/p/${projectId}`,
  }));
}
