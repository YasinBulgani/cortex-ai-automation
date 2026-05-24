/**
 * Ürün ailesi için paylaşılan tipler.
 *
 * Her ürün paketi (packages/product-{id}) bu tipleri kullanarak
 * kendi manifest + landing içeriğini export eder.
 */

export type ProductFamilyId =
  | "one"
  | "studio"
  | "service"
  | "web"
  | "mobile"
  | "data"
  | "management"
  | "intelligence"
  | "nexus-code";

export type ProductAvailability = "core" | "active" | "beta" | "embedded";

export type AppRouteKey = string;

export type NavGroupKey =
  | ""
  | "Tasarım"
  | "Üretim"
  | "Koşu & Gözlem"
  | "Kalite"
  | "Veri"
  | "Yapılandırma"
  | "AI";

export type ProductAvailabilityMeta = {
  label: string;
  className: string;
};

export type ProductManifest = {
  id: ProductFamilyId;
  name: string;
  shortName: string;
  tagline: string;
  description: string;
  availability: ProductAvailability;
  defaultEntryKey: AppRouteKey;
  /** Bu ürünün sidebar'da göstereceği route key'leri. routes.ts'deki katalogla birleşir. */
  routeKeys: AppRouteKey[];
};

export type ProductLandingContent = {
  eyebrow: string;
  headline: string;
  summary: string;
  primaryOutcome: string;
  startRouteKey: AppRouteKey;
  projectKeywords: string[];
};

export type ProductPackage = {
  manifest: ProductManifest;
  landing: ProductLandingContent;
};

/**
 * Merkezi route katalogu için tip. productIds compose sırasında türetilir;
 * burada route tanımı ürün-agnostiktir.
 */
export type RouteCatalogEntry = {
  key: AppRouteKey;
  path: string | null;
  segment: string;
  label: string;
  group: NavGroupKey;
};

/** Backward-compatible tip: lib/product.ts kullanıcıları için. */
export type ProjectNavDefinition = RouteCatalogEntry & {
  productIds: ProductFamilyId[];
};

export type ProjectNavLink = ProjectNavDefinition & {
  href: string;
};

export type ProductFamilyMember = ProductManifest & {
  /** Compose sonrası türetilen segment listesi. */
  routeSegments: string[];
};
