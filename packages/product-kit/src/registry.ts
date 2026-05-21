/**
 * Ürün paketlerini compose eden registry.
 *
 * Her ürün paketi sadece kendi manifest + landing içeriğini export eder;
 * burada hepsi tek `composeProductRegistry()` çağrısıyla birleştirilir ve
 * eski API yüzeyiyle (PRODUCT_FAMILY, PROJECT_NAV_DEFINITIONS vb.) uyumlu
 * türevler üretilir.
 */

import { ROUTE_BY_KEY } from "./routes";
import type {
  AppRouteKey,
  ProductAvailability,
  ProductAvailabilityMeta,
  ProductFamilyId,
  ProductFamilyMember,
  ProductLandingContent,
  ProductPackage,
  ProjectNavDefinition,
} from "./types";

export const PRODUCT_FAMILY_STORAGE_KEY = "bgts_product_family_focus";

export const PRODUCT_AVAILABILITY_META: Record<ProductAvailability, ProductAvailabilityMeta> = {
  core: { label: "Core", className: "border-sky-400/20 bg-sky-500/10 text-sky-200" },
  active: { label: "Active", className: "border-emerald-400/20 bg-emerald-500/10 text-emerald-200" },
  beta: { label: "Beta", className: "border-amber-400/20 bg-amber-500/10 text-amber-200" },
  embedded: { label: "Embedded", className: "border-violet-400/20 bg-violet-500/10 text-violet-200" },
};

export type ProductRegistry = {
  members: ProductFamilyMember[];
  byId: Record<string, ProductFamilyMember>;
  landingById: Record<ProductFamilyId, ProductLandingContent>;
  navDefinitions: ProjectNavDefinition[];
};

function uniqueSegments(segments: string[]): string[] {
  return [...new Set(segments.filter(Boolean))];
}

export function composeProductRegistry(packages: ProductPackage[]): ProductRegistry {
  // route key -> hangi ürünlerin sahip olduğu
  const ownershipByKey = new Map<AppRouteKey, ProductFamilyId[]>();
  for (const pkg of packages) {
    for (const key of pkg.manifest.routeKeys) {
      const list = ownershipByKey.get(key) ?? [];
      list.push(pkg.manifest.id);
      ownershipByKey.set(key, list);
    }
  }

  // navDefinitions: katalogdaki her route + sahibi olan productId'ler
  const navDefinitions: ProjectNavDefinition[] = Object.values(ROUTE_BY_KEY).map((entry) => ({
    ...entry,
    productIds: ownershipByKey.get(entry.key) ?? [],
  }));

  const members: ProductFamilyMember[] = packages.map(({ manifest }) => {
    const segments = manifest.routeKeys
      .map((k) => ROUTE_BY_KEY[k])
      .filter((r): r is NonNullable<typeof r> => Boolean(r && r.path !== null && r.path !== ""))
      .map((r) => r.segment);
    return { ...manifest, routeSegments: uniqueSegments(segments) };
  });

  const byId = Object.fromEntries(members.map((m) => [m.id, m])) as Record<string, ProductFamilyMember>;

  const landingById = Object.fromEntries(
    packages.map((p) => [p.manifest.id, p.landing]),
  ) as Record<ProductFamilyId, ProductLandingContent>;

  return { members, byId, landingById, navDefinitions };
}

export const DEFAULT_PRODUCT_FAMILY_ID: ProductFamilyId = "one";

export function isValidProductFamilyId(
  value: string | null | undefined,
  registry: ProductRegistry,
): value is ProductFamilyId {
  return registry.members.some((p) => p.id === value);
}
