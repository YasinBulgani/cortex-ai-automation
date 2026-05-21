/** @jest-environment node */
import {
  normalizeProvenance,
  isRealProvenance,
  provenanceLabel,
  provenanceBadgeClass,
  artifactTargetLabel,
  artifactTargetBadgeClass,
  validationStatusLabel,
  validationStatusBadgeClass,
  type ProvenanceKind,
  type ArtifactTarget,
  type ValidationStatus,
} from "../provenance";

// ─── normalizeProvenance ──────────────────────────────────────────────────────

describe("normalizeProvenance", () => {
  describe("null / undefined input", () => {
    it("returns 'real' for undefined", () => {
      expect(normalizeProvenance(undefined)).toBe("real");
    });

    it("returns 'real' for null", () => {
      expect(normalizeProvenance(null)).toBe("real");
    });

    it("returns 'real' for empty object", () => {
      expect(normalizeProvenance({})).toBe("real");
    });

    it("returns 'real' when provenance field is null", () => {
      expect(normalizeProvenance({ provenance: null })).toBe("real");
    });

    it("returns 'real' when all flags are false", () => {
      expect(
        normalizeProvenance({ stub: false, fallback: false, simulated: false, mock_mode: false })
      ).toBe("real");
    });

    it("returns 'real' when all flags are 0", () => {
      expect(
        normalizeProvenance({ stub: 0, fallback: 0, simulated: 0, mock_mode: 0 })
      ).toBe("real");
    });
  });

  describe("explicit provenance string field", () => {
    it("returns 'real' for provenance='real'", () => {
      expect(normalizeProvenance({ provenance: "real" })).toBe("real");
    });

    it("returns 'simulated' for provenance='simulated'", () => {
      expect(normalizeProvenance({ provenance: "simulated" })).toBe("simulated");
    });

    it("returns 'fallback' for provenance='fallback'", () => {
      expect(normalizeProvenance({ provenance: "fallback" })).toBe("fallback");
    });

    it("returns 'stub' for provenance='stub'", () => {
      expect(normalizeProvenance({ provenance: "stub" })).toBe("stub");
    });

    it("explicit provenance takes priority over boolean flags", () => {
      expect(
        normalizeProvenance({ provenance: "real", stub: true, fallback: true, simulated: true })
      ).toBe("real");
    });

    it("explicit 'fallback' provenance takes priority over stub flag", () => {
      expect(normalizeProvenance({ provenance: "fallback", stub: true })).toBe("fallback");
    });
  });

  describe("boolean flags — stub", () => {
    it("returns 'stub' when stub is true (boolean)", () => {
      expect(normalizeProvenance({ stub: true })).toBe("stub");
    });

    it("returns 'stub' when stub is 1 (number)", () => {
      expect(normalizeProvenance({ stub: 1 })).toBe("stub");
    });

    it("returns 'stub' when stub is string 'true'", () => {
      expect(normalizeProvenance({ stub: "true" as unknown as boolean })).toBe("stub");
    });

    it("returns 'stub' when stub is string '1'", () => {
      expect(normalizeProvenance({ stub: "1" as unknown as boolean })).toBe("stub");
    });

    it("stub flag takes priority over fallback flag", () => {
      expect(normalizeProvenance({ stub: true, fallback: true })).toBe("stub");
    });

    it("stub flag takes priority over simulated flag", () => {
      expect(normalizeProvenance({ stub: true, simulated: true })).toBe("stub");
    });
  });

  describe("boolean flags — fallback", () => {
    it("returns 'fallback' when fallback is true (boolean)", () => {
      expect(normalizeProvenance({ fallback: true })).toBe("fallback");
    });

    it("returns 'fallback' when fallback is 1 (number)", () => {
      expect(normalizeProvenance({ fallback: 1 })).toBe("fallback");
    });

    it("returns 'fallback' when fallback is string 'true'", () => {
      expect(normalizeProvenance({ fallback: "true" as unknown as boolean })).toBe("fallback");
    });

    it("returns 'fallback' when fallback is string '1'", () => {
      expect(normalizeProvenance({ fallback: "1" as unknown as boolean })).toBe("fallback");
    });

    it("fallback flag takes priority over simulated flag", () => {
      expect(normalizeProvenance({ fallback: true, simulated: true })).toBe("fallback");
    });
  });

  describe("boolean flags — simulated", () => {
    it("returns 'simulated' when simulated is true (boolean)", () => {
      expect(normalizeProvenance({ simulated: true })).toBe("simulated");
    });

    it("returns 'simulated' when simulated is 1 (number)", () => {
      expect(normalizeProvenance({ simulated: 1 })).toBe("simulated");
    });

    it("returns 'simulated' when simulated is string 'true'", () => {
      expect(normalizeProvenance({ simulated: "true" as unknown as boolean })).toBe("simulated");
    });

    it("returns 'simulated' when simulated is string '1'", () => {
      expect(normalizeProvenance({ simulated: "1" as unknown as boolean })).toBe("simulated");
    });
  });

  describe("boolean flags — mock_mode", () => {
    it("returns 'simulated' when mock_mode is true (boolean)", () => {
      expect(normalizeProvenance({ mock_mode: true })).toBe("simulated");
    });

    it("returns 'simulated' when mock_mode is 1 (number)", () => {
      expect(normalizeProvenance({ mock_mode: 1 })).toBe("simulated");
    });

    it("returns 'simulated' when mock_mode is string 'true'", () => {
      expect(normalizeProvenance({ mock_mode: "true" as unknown as boolean })).toBe("simulated");
    });

    it("returns 'simulated' when mock_mode is string '1'", () => {
      expect(normalizeProvenance({ mock_mode: "1" as unknown as boolean })).toBe("simulated");
    });

    it("returns 'simulated' when both simulated and mock_mode are true", () => {
      expect(normalizeProvenance({ simulated: true, mock_mode: true })).toBe("simulated");
    });
  });

  describe("unknown provenance string falls through to flags", () => {
    it("unknown provenance + stub flag → 'stub'", () => {
      expect(normalizeProvenance({ provenance: "unknown-value", stub: true })).toBe("stub");
    });

    it("unknown provenance + fallback flag → 'fallback'", () => {
      expect(normalizeProvenance({ provenance: "unknown-value", fallback: true })).toBe("fallback");
    });

    it("unknown provenance + simulated flag → 'simulated'", () => {
      expect(normalizeProvenance({ provenance: "unknown-value", simulated: true })).toBe("simulated");
    });

    it("unknown provenance + mock_mode flag → 'simulated'", () => {
      expect(normalizeProvenance({ provenance: "unknown-value", mock_mode: true })).toBe("simulated");
    });

    it("unknown provenance with no flags → 'real'", () => {
      expect(normalizeProvenance({ provenance: "unknown-value" })).toBe("real");
    });

    it("empty-string provenance with no flags → 'real'", () => {
      expect(normalizeProvenance({ provenance: "" })).toBe("real");
    });
  });

  describe("isTruthy boundary cases", () => {
    it("string 'false' is NOT truthy — returns 'real'", () => {
      expect(normalizeProvenance({ stub: "false" as unknown as boolean })).toBe("real");
    });

    it("string '0' is NOT truthy — returns 'real'", () => {
      expect(normalizeProvenance({ simulated: "0" as unknown as boolean })).toBe("real");
    });

    it("null flag values are NOT truthy — returns 'real'", () => {
      expect(normalizeProvenance({ stub: null, fallback: null, simulated: null })).toBe("real");
    });
  });
});

// ─── isRealProvenance ─────────────────────────────────────────────────────────

describe("isRealProvenance", () => {
  it("returns true for 'real'", () => {
    expect(isRealProvenance("real")).toBe(true);
  });

  it("returns false for 'simulated'", () => {
    expect(isRealProvenance("simulated")).toBe(false);
  });

  it("returns false for 'fallback'", () => {
    expect(isRealProvenance("fallback")).toBe(false);
  });

  it("returns false for 'stub'", () => {
    expect(isRealProvenance("stub")).toBe(false);
  });
});

// ─── provenanceLabel ──────────────────────────────────────────────────────────

describe("provenanceLabel", () => {
  it("returns 'Gerçek' for 'real'", () => {
    expect(provenanceLabel("real")).toBe("Gerçek");
  });

  it("returns 'Simüle' for 'simulated'", () => {
    expect(provenanceLabel("simulated")).toBe("Simüle");
  });

  it("returns 'Fallback' for 'fallback'", () => {
    expect(provenanceLabel("fallback")).toBe("Fallback");
  });

  it("returns 'Stub' for 'stub'", () => {
    expect(provenanceLabel("stub")).toBe("Stub");
  });

  it("every ProvenanceKind returns a non-empty label", () => {
    const kinds: ProvenanceKind[] = ["real", "simulated", "fallback", "stub"];
    kinds.forEach((k) => expect(provenanceLabel(k).length).toBeGreaterThan(0));
  });
});

// ─── provenanceBadgeClass ─────────────────────────────────────────────────────

describe("provenanceBadgeClass", () => {
  const kinds: ProvenanceKind[] = ["real", "simulated", "fallback", "stub"];

  it.each(kinds)("returns a non-empty string for '%s'", (kind) => {
    expect(typeof provenanceBadgeClass(kind)).toBe("string");
    expect(provenanceBadgeClass(kind).length).toBeGreaterThan(0);
  });

  it("'real' badge class contains 'emerald'", () => {
    expect(provenanceBadgeClass("real")).toContain("emerald");
  });

  it("'simulated' badge class contains 'amber'", () => {
    expect(provenanceBadgeClass("simulated")).toContain("amber");
  });

  it("'fallback' badge class contains 'orange'", () => {
    expect(provenanceBadgeClass("fallback")).toContain("orange");
  });

  it("'stub' badge class contains 'slate'", () => {
    expect(provenanceBadgeClass("stub")).toContain("slate");
  });

  it("each kind produces a distinct badge class", () => {
    const classes = kinds.map(provenanceBadgeClass);
    const unique = new Set(classes);
    expect(unique.size).toBe(kinds.length);
  });
});

// ─── artifactTargetLabel ──────────────────────────────────────────────────────

describe("artifactTargetLabel", () => {
  it("returns 'Playwright' for 'playwright'", () => {
    expect(artifactTargetLabel("playwright")).toBe("Playwright");
  });

  it("returns 'MaviYaka' for 'maviyaka'", () => {
    expect(artifactTargetLabel("maviyaka")).toBe("MaviYaka");
  });

  it("returns 'Ortak' for 'shared'", () => {
    expect(artifactTargetLabel("shared")).toBe("Ortak");
  });

  it("every ArtifactTarget returns a non-empty label", () => {
    const targets: ArtifactTarget[] = ["shared", "playwright", "maviyaka"];
    targets.forEach((t) => expect(artifactTargetLabel(t).length).toBeGreaterThan(0));
  });
});

// ─── artifactTargetBadgeClass ─────────────────────────────────────────────────

describe("artifactTargetBadgeClass", () => {
  const targets: ArtifactTarget[] = ["shared", "playwright", "maviyaka"];

  it.each(targets)("returns a non-empty string for '%s'", (target) => {
    expect(typeof artifactTargetBadgeClass(target)).toBe("string");
    expect(artifactTargetBadgeClass(target).length).toBeGreaterThan(0);
  });

  it("'playwright' badge class contains 'violet'", () => {
    expect(artifactTargetBadgeClass("playwright")).toContain("violet");
  });

  it("'maviyaka' badge class contains 'sky'", () => {
    expect(artifactTargetBadgeClass("maviyaka")).toContain("sky");
  });

  it("'shared' badge class contains 'slate'", () => {
    expect(artifactTargetBadgeClass("shared")).toContain("slate");
  });

  it("each target produces a distinct badge class", () => {
    const classes = targets.map(artifactTargetBadgeClass);
    const unique = new Set(classes);
    expect(unique.size).toBe(targets.length);
  });
});

// ─── validationStatusLabel ────────────────────────────────────────────────────

describe("validationStatusLabel", () => {
  it("returns 'Doğrulandı' for 'validated'", () => {
    expect(validationStatusLabel("validated")).toBe("Doğrulandı");
  });

  it("returns 'Doğrulama Hatası' for 'failed'", () => {
    expect(validationStatusLabel("failed")).toBe("Doğrulama Hatası");
  });

  it("returns 'Bekliyor' for 'pending'", () => {
    expect(validationStatusLabel("pending")).toBe("Bekliyor");
  });

  it("returns 'Uygulanmaz' for 'not_applicable'", () => {
    expect(validationStatusLabel("not_applicable")).toBe("Uygulanmaz");
  });

  it("every ValidationStatus returns a non-empty label", () => {
    const statuses: ValidationStatus[] = ["pending", "validated", "failed", "not_applicable"];
    statuses.forEach((s) => expect(validationStatusLabel(s).length).toBeGreaterThan(0));
  });
});

// ─── validationStatusBadgeClass ───────────────────────────────────────────────

describe("validationStatusBadgeClass", () => {
  const statuses: ValidationStatus[] = ["pending", "validated", "failed", "not_applicable"];

  it.each(statuses)("returns a non-empty string for '%s'", (status) => {
    expect(typeof validationStatusBadgeClass(status)).toBe("string");
    expect(validationStatusBadgeClass(status).length).toBeGreaterThan(0);
  });

  it("'validated' badge class contains 'emerald'", () => {
    expect(validationStatusBadgeClass("validated")).toContain("emerald");
  });

  it("'failed' badge class contains 'red'", () => {
    expect(validationStatusBadgeClass("failed")).toContain("red");
  });

  it("'pending' badge class contains 'amber'", () => {
    expect(validationStatusBadgeClass("pending")).toContain("amber");
  });

  it("'not_applicable' badge class contains 'slate'", () => {
    expect(validationStatusBadgeClass("not_applicable")).toContain("slate");
  });

  it("each status produces a distinct badge class", () => {
    const classes = statuses.map(validationStatusBadgeClass);
    const unique = new Set(classes);
    expect(unique.size).toBe(statuses.length);
  });
});
