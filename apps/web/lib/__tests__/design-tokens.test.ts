/** @jest-environment node */
import {
  surfaces,
  text,
  statusBadge,
  productMeta,
  density,
  focusRing,
  focusRingDanger,
  interactive,
  animate,
} from "../design-tokens";
import type { ProductFamilyId } from "../product";

// ─── surfaces ─────────────────────────────────────────────────────────────────

describe("surfaces", () => {
  const EXPECTED_KEYS = ["base", "raised", "overlay", "accent"] as const;

  it("has all required surface keys", () => {
    expect(Object.keys(surfaces)).toEqual(
      expect.arrayContaining([...EXPECTED_KEYS])
    );
  });

  it("has exactly 4 keys (no extras)", () => {
    expect(Object.keys(surfaces)).toHaveLength(4);
  });

  it("all values are non-empty strings", () => {
    Object.values(surfaces).forEach((v) => {
      expect(typeof v).toBe("string");
      expect(v.length).toBeGreaterThan(0);
    });
  });

  it.each(EXPECTED_KEYS)("key '%s' is a non-empty string", (key) => {
    expect(typeof surfaces[key]).toBe("string");
    expect(surfaces[key].length).toBeGreaterThan(0);
  });
});

// ─── text ─────────────────────────────────────────────────────────────────────

describe("text", () => {
  const EXPECTED_KEYS = ["default", "muted", "subtle", "disabled"] as const;

  it("has all required text keys", () => {
    expect(Object.keys(text)).toEqual(
      expect.arrayContaining([...EXPECTED_KEYS])
    );
  });

  it("has exactly 4 keys (no extras)", () => {
    expect(Object.keys(text)).toHaveLength(4);
  });

  it("all values are non-empty strings", () => {
    Object.values(text).forEach((v) => {
      expect(typeof v).toBe("string");
      expect(v.length).toBeGreaterThan(0);
    });
  });

  it.each(EXPECTED_KEYS)("key '%s' is a non-empty string", (key) => {
    expect(typeof text[key]).toBe("string");
    expect(text[key].length).toBeGreaterThan(0);
  });
});

// ─── statusBadge ──────────────────────────────────────────────────────────────

describe("statusBadge", () => {
  const EXPECTED_KEYS = ["success", "warning", "danger", "info", "neutral"] as const;

  it("has all required statusBadge keys", () => {
    expect(Object.keys(statusBadge)).toEqual(
      expect.arrayContaining([...EXPECTED_KEYS])
    );
  });

  it("has exactly 5 keys (no extras)", () => {
    expect(Object.keys(statusBadge)).toHaveLength(5);
  });

  it("all values are non-empty strings", () => {
    Object.values(statusBadge).forEach((v) => {
      expect(typeof v).toBe("string");
      expect(v.length).toBeGreaterThan(0);
    });
  });

  it.each(EXPECTED_KEYS)("key '%s' is a non-empty string", (key) => {
    expect(typeof statusBadge[key]).toBe("string");
    expect(statusBadge[key].length).toBeGreaterThan(0);
  });
});

// ─── productMeta ──────────────────────────────────────────────────────────────

describe("productMeta", () => {
  const EXPECTED_PRODUCT_IDS: ProductFamilyId[] = [
    "one",
    "studio",
    "service",
    "web",
    "mobile",
    "data",
    "management",
    "intelligence",
    "nexus-code",
  ];

  const REQUIRED_SUB_KEYS = ["emoji", "brandClass", "bgClass", "borderClass", "cssVar"] as const;

  it("has all 9 required product IDs", () => {
    expect(Object.keys(productMeta)).toEqual(
      expect.arrayContaining(EXPECTED_PRODUCT_IDS)
    );
  });

  it("has exactly 9 entries (no extras)", () => {
    expect(Object.keys(productMeta)).toHaveLength(9);
  });

  it.each(EXPECTED_PRODUCT_IDS)("product '%s' exists", (id) => {
    expect(productMeta[id]).toBeDefined();
  });

  it.each(EXPECTED_PRODUCT_IDS)("product '%s' has all required sub-keys", (id) => {
    const entry = productMeta[id];
    REQUIRED_SUB_KEYS.forEach((key) => {
      expect(entry).toHaveProperty(key);
    });
  });

  it.each(EXPECTED_PRODUCT_IDS)("product '%s' sub-keys are all non-empty strings", (id) => {
    const entry = productMeta[id];
    REQUIRED_SUB_KEYS.forEach((key) => {
      expect(typeof entry[key]).toBe("string");
      expect(entry[key].length).toBeGreaterThan(0);
    });
  });

  it.each(EXPECTED_PRODUCT_IDS)("product '%s' cssVar starts with '--'", (id) => {
    expect(productMeta[id].cssVar.startsWith("--")).toBe(true);
  });

  it("all brandClass values are distinct", () => {
    const classes = EXPECTED_PRODUCT_IDS.map((id) => productMeta[id].brandClass);
    const unique = new Set(classes);
    expect(unique.size).toBe(EXPECTED_PRODUCT_IDS.length);
  });

  it("all cssVar values are distinct", () => {
    const vars = EXPECTED_PRODUCT_IDS.map((id) => productMeta[id].cssVar);
    const unique = new Set(vars);
    expect(unique.size).toBe(EXPECTED_PRODUCT_IDS.length);
  });
});

// ─── density ──────────────────────────────────────────────────────────────────

describe("density", () => {
  const EXPECTED_LEVELS = ["compact", "comfortable", "spacious"] as const;
  const REQUIRED_SUB_KEYS = ["padding", "text", "gap"] as const;

  it("has all required density levels", () => {
    expect(Object.keys(density)).toEqual(
      expect.arrayContaining([...EXPECTED_LEVELS])
    );
  });

  it("has exactly 3 levels (no extras)", () => {
    expect(Object.keys(density)).toHaveLength(3);
  });

  it.each(EXPECTED_LEVELS)("level '%s' exists", (level) => {
    expect(density[level]).toBeDefined();
  });

  it.each(EXPECTED_LEVELS)("level '%s' has all required sub-keys", (level) => {
    const entry = density[level];
    REQUIRED_SUB_KEYS.forEach((key) => {
      expect(entry).toHaveProperty(key);
    });
  });

  it.each(EXPECTED_LEVELS)("level '%s' sub-keys are all non-empty strings", (level) => {
    const entry = density[level];
    REQUIRED_SUB_KEYS.forEach((key) => {
      expect(typeof entry[key]).toBe("string");
      expect(entry[key].length).toBeGreaterThan(0);
    });
  });
});

// ─── focusRing ────────────────────────────────────────────────────────────────

describe("focusRing", () => {
  it("is a non-empty string", () => {
    expect(typeof focusRing).toBe("string");
    expect(focusRing.length).toBeGreaterThan(0);
  });

  it("contains focus-visible classes", () => {
    expect(focusRing).toContain("focus-visible");
  });
});

// ─── focusRingDanger ──────────────────────────────────────────────────────────

describe("focusRingDanger", () => {
  it("is a non-empty string", () => {
    expect(typeof focusRingDanger).toBe("string");
    expect(focusRingDanger.length).toBeGreaterThan(0);
  });

  it("contains focus-visible classes", () => {
    expect(focusRingDanger).toContain("focus-visible");
  });

  it("is distinct from focusRing", () => {
    expect(focusRingDanger).not.toBe(focusRing);
  });

  it("contains 'danger' somewhere in the class string", () => {
    expect(focusRingDanger).toContain("danger");
  });
});

// ─── interactive ──────────────────────────────────────────────────────────────

describe("interactive", () => {
  const EXPECTED_KEYS = ["subtle", "brand", "danger"] as const;

  it("has all required interactive keys", () => {
    expect(Object.keys(interactive)).toEqual(
      expect.arrayContaining([...EXPECTED_KEYS])
    );
  });

  it("has exactly 3 keys (no extras)", () => {
    expect(Object.keys(interactive)).toHaveLength(3);
  });

  it("all values are non-empty strings", () => {
    Object.values(interactive).forEach((v) => {
      expect(typeof v).toBe("string");
      expect(v.length).toBeGreaterThan(0);
    });
  });

  it.each(EXPECTED_KEYS)("key '%s' is a non-empty string", (key) => {
    expect(typeof interactive[key]).toBe("string");
    expect(interactive[key].length).toBeGreaterThan(0);
  });

  it("each variant produces a distinct class string", () => {
    const classes = EXPECTED_KEYS.map((k) => interactive[k]);
    const unique = new Set(classes);
    expect(unique.size).toBe(EXPECTED_KEYS.length);
  });
});

// ─── animate ──────────────────────────────────────────────────────────────────

describe("animate", () => {
  const EXPECTED_KEYS = [
    "fadeIn",
    "slideUp",
    "slideDown",
    "scaleIn",
    "pulse",
    "shimmer",
  ] as const;

  it("has all required animate keys", () => {
    expect(Object.keys(animate)).toEqual(
      expect.arrayContaining([...EXPECTED_KEYS])
    );
  });

  it("has exactly 6 keys (no extras)", () => {
    expect(Object.keys(animate)).toHaveLength(6);
  });

  it("all values are non-empty strings", () => {
    Object.values(animate).forEach((v) => {
      expect(typeof v).toBe("string");
      expect(v.length).toBeGreaterThan(0);
    });
  });

  it.each(EXPECTED_KEYS)("key '%s' is a non-empty string", (key) => {
    expect(typeof animate[key]).toBe("string");
    expect(animate[key].length).toBeGreaterThan(0);
  });

  it("each animation produces a distinct class string", () => {
    const classes = EXPECTED_KEYS.map((k) => animate[k]);
    const unique = new Set(classes);
    expect(unique.size).toBe(EXPECTED_KEYS.length);
  });

  it("all values start with 'animate-'", () => {
    Object.values(animate).forEach((v) => {
      expect(v.startsWith("animate-")).toBe(true);
    });
  });
});
