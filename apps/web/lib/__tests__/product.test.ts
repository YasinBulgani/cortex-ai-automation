/** @jest-environment node */
import {
  isValidProductFamilyId,
  getProductFamilyMember,
  getRoutesForProduct,
  getPrimaryRoutesForProduct,
  getSegmentLabel,
  getProductEntryHref,
  getProductLandingHref,
  getProductBySegment,
  getRouteDefinition,
  getDefaultEntrySegmentForProduct,
  PRODUCT_FAMILY,
  PRODUCT_FAMILY_BY_ID,
  DEFAULT_PRODUCT_FAMILY_ID,
  ROUTE_SEGMENT_LABELS,
  NAV_GROUP_ORDER,
} from "../product";

describe("isValidProductFamilyId", () => {
  it("returns true for all defined product IDs", () => {
    const ids = ["one", "studio", "service", "web", "mobile", "data", "management", "intelligence", "nexus-code"];
    ids.forEach((id) => expect(isValidProductFamilyId(id)).toBe(true));
  });

  it("returns false for unknown id", () => {
    expect(isValidProductFamilyId("unknown")).toBe(false);
  });

  it("returns false for null", () => {
    expect(isValidProductFamilyId(null)).toBe(false);
  });

  it("returns false for undefined", () => {
    expect(isValidProductFamilyId(undefined)).toBe(false);
  });

  it("returns false for empty string", () => {
    expect(isValidProductFamilyId("")).toBe(false);
  });
});

describe("getProductFamilyMember", () => {
  it("returns correct member for 'one'", () => {
    const member = getProductFamilyMember("one");
    expect(member.id).toBe("one");
    expect(member.name).toBe("Neurex One");
  });

  it("returns correct member for 'web'", () => {
    const member = getProductFamilyMember("web");
    expect(member.id).toBe("web");
    expect(member.defaultEntryKey).toBe("scenarios");
  });

  it("returns correct member for 'mobile'", () => {
    const member = getProductFamilyMember("mobile");
    expect(member.availability).toBe("beta");
  });

  it("all products have routeSegments", () => {
    PRODUCT_FAMILY.forEach((p) => {
      expect(Array.isArray(p.routeSegments)).toBe(true);
    });
  });

  it("PRODUCT_FAMILY has 9 members", () => {
    expect(PRODUCT_FAMILY).toHaveLength(9);
  });

  it("DEFAULT_PRODUCT_FAMILY_ID is 'one'", () => {
    expect(DEFAULT_PRODUCT_FAMILY_ID).toBe("one");
  });
});

describe("getRoutesForProduct", () => {
  it("returns routes for 'one' product (largest set)", () => {
    const routes = getRoutesForProduct("one");
    expect(routes.length).toBeGreaterThan(10);
  });

  it("'web' product includes scenarios", () => {
    const routes = getRoutesForProduct("web");
    expect(routes.some((r) => r.key === "scenarios")).toBe(true);
  });

  it("'service' product includes api-testing", () => {
    const routes = getRoutesForProduct("service");
    expect(routes.some((r) => r.key === "api-testing")).toBe(true);
  });

  it("'data' product includes synthetic", () => {
    const routes = getRoutesForProduct("data");
    expect(routes.some((r) => r.key === "synthetic")).toBe(true);
  });

  it("'intelligence' product includes ai-chat", () => {
    const routes = getRoutesForProduct("intelligence");
    expect(routes.some((r) => r.key === "ai-chat")).toBe(true);
  });
});

describe("getPrimaryRoutesForProduct", () => {
  it("returns only routes with non-null, non-empty paths", () => {
    const routes = getPrimaryRoutesForProduct("web");
    expect(routes.every((r) => r.path !== null && r.path !== "")).toBe(true);
  });

  it("excludes project-overview (empty path) for all products", () => {
    const routes = getPrimaryRoutesForProduct("one");
    expect(routes.some((r) => r.key === "project-overview")).toBe(false);
  });
});

describe("getSegmentLabel", () => {
  it("returns correct label for 'scenarios'", () => {
    expect(getSegmentLabel("scenarios")).toBe("Senaryolar");
  });

  it("returns 'Proje Özeti' for empty string", () => {
    expect(getSegmentLabel("")).toBe("Proje Özeti");
  });

  it("returns 'Proje Özeti' for null", () => {
    expect(getSegmentLabel(null)).toBe("Proje Özeti");
  });

  it("returns 'Proje Özeti' for undefined", () => {
    expect(getSegmentLabel(undefined)).toBe("Proje Özeti");
  });

  it("returns segment itself for unknown segment", () => {
    expect(getSegmentLabel("unknown-segment")).toBe("unknown-segment");
  });

  it("ROUTE_SEGMENT_LABELS has profile entry", () => {
    expect(ROUTE_SEGMENT_LABELS["profile"]).toBe("Profil");
  });

  it("ROUTE_SEGMENT_LABELS has new-project entry", () => {
    expect(ROUTE_SEGMENT_LABELS["new-project"]).toBe("Yeni Proje");
  });
});

describe("getProductEntryHref", () => {
  it("returns /projects when projectId is null", () => {
    expect(getProductEntryHref(null, "one")).toBe("/projects");
  });

  it("returns /projects when projectId is undefined", () => {
    expect(getProductEntryHref(undefined, "one")).toBe("/projects");
  });

  it("returns correct href for web product", () => {
    const href = getProductEntryHref("proj-123", "web");
    expect(href).toMatch(/^\/p\/proj-123\//);
  });

  it("returns correct href for one product (default entry: settings)", () => {
    const href = getProductEntryHref("proj-abc", "one");
    expect(href).toBe("/p/proj-abc/settings");
  });

  it("returns correct href for service product (default entry: api-testing)", () => {
    const href = getProductEntryHref("proj-abc", "service");
    expect(href).toBe("/p/proj-abc/api-testing");
  });

  it("returns correct href for data product (default entry: synthetic)", () => {
    const href = getProductEntryHref("proj-abc", "data");
    expect(href).toBe("/p/proj-abc/synthetic");
  });
});

describe("getProductLandingHref", () => {
  it("returns /products/one for one", () => {
    expect(getProductLandingHref("one")).toBe("/products/one");
  });

  it("returns /products/nexus-code for nexus-code", () => {
    expect(getProductLandingHref("nexus-code")).toBe("/products/nexus-code");
  });
});

describe("getProductBySegment", () => {
  it("returns default product for null segment", () => {
    const product = getProductBySegment(null);
    expect(product.id).toBe(DEFAULT_PRODUCT_FAMILY_ID);
  });

  it("returns default product for undefined", () => {
    const product = getProductBySegment(undefined);
    expect(product.id).toBe(DEFAULT_PRODUCT_FAMILY_ID);
  });

  it("returns default product for unknown segment", () => {
    const product = getProductBySegment("totally-unknown");
    expect(product.id).toBe(DEFAULT_PRODUCT_FAMILY_ID);
  });
});

describe("getRouteDefinition", () => {
  it("returns definition for 'scenarios'", () => {
    const route = getRouteDefinition("scenarios");
    expect(route?.key).toBe("scenarios");
    expect(route?.path).toBe("scenarios");
  });

  it("returns undefined for unknown key", () => {
    expect(getRouteDefinition("nonexistent-key")).toBeUndefined();
  });
});

describe("getDefaultEntrySegmentForProduct", () => {
  it("returns 'settings' for one", () => {
    expect(getDefaultEntrySegmentForProduct("one")).toBe("settings");
  });

  it("returns 'scenarios' for web", () => {
    expect(getDefaultEntrySegmentForProduct("web")).toBe("scenarios");
  });

  it("returns 'synthetic' for data", () => {
    expect(getDefaultEntrySegmentForProduct("data")).toBe("synthetic");
  });
});

describe("NAV_GROUP_ORDER", () => {
  it("has expected groups in order", () => {
    expect(NAV_GROUP_ORDER[0]).toBe("Tasarım");
    expect(NAV_GROUP_ORDER).toContain("AI");
    expect(NAV_GROUP_ORDER).toContain("Kalite");
  });
});

describe("PRODUCT_FAMILY_BY_ID", () => {
  it("contains all 9 products keyed by id", () => {
    expect(Object.keys(PRODUCT_FAMILY_BY_ID)).toHaveLength(9);
    expect(PRODUCT_FAMILY_BY_ID["mobile"].name).toBe("Neurex Mobile");
    expect(PRODUCT_FAMILY_BY_ID["management"].name).toBe("Neurex Management");
  });
});
