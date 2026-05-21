/** @jest-environment node */
import {
  PERSONA_PRESETS,
  getPersonaPreset,
  PERSONA_STORAGE_KEY,
  type PersonaId,
} from "../persona-focus";

describe("PERSONA_PRESETS", () => {
  it("has at least 5 presets", () => {
    expect(PERSONA_PRESETS.length).toBeGreaterThanOrEqual(5);
  });

  it("first preset is 'balanced'", () => {
    expect(PERSONA_PRESETS[0].id).toBe("balanced");
  });

  it("every preset has required fields", () => {
    PERSONA_PRESETS.forEach((preset) => {
      expect(preset.id).toBeTruthy();
      expect(preset.label).toBeTruthy();
      expect(preset.shortLabel).toBeTruthy();
      expect(preset.description).toBeTruthy();
      expect(Array.isArray(preset.focusSegments)).toBe(true);
      expect(Array.isArray(preset.focusFlows)).toBe(true);
      expect(Array.isArray(preset.quickLinks)).toBe(true);
    });
  });

  it("contains 'analyst' preset", () => {
    expect(PERSONA_PRESETS.some((p) => p.id === "analyst")).toBe(true);
  });

  it("contains 'automation_engineer' preset", () => {
    expect(PERSONA_PRESETS.some((p) => p.id === "automation_engineer")).toBe(true);
  });

  it("contains 'testops_lead' preset", () => {
    expect(PERSONA_PRESETS.some((p) => p.id === "testops_lead")).toBe(true);
  });

  it("analyst preset has non-empty focusSegments", () => {
    const analyst = PERSONA_PRESETS.find((p) => p.id === "analyst");
    expect(analyst?.focusSegments.length).toBeGreaterThan(0);
  });

  it("every preset has at least 1 quickLink", () => {
    PERSONA_PRESETS.forEach((preset) => {
      expect(preset.quickLinks.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("every quickLink has label and path", () => {
    PERSONA_PRESETS.forEach((preset) => {
      preset.quickLinks.forEach((link) => {
        expect(link.label).toBeTruthy();
        expect(typeof link.path).toBe("string");
      });
    });
  });
});

describe("getPersonaPreset", () => {
  it("returns the balanced preset (first) for any input", () => {
    const result = getPersonaPreset("analyst");
    expect(result.id).toBe("balanced");
  });

  it("returns balanced for null", () => {
    expect(getPersonaPreset(null).id).toBe("balanced");
  });

  it("returns balanced for undefined", () => {
    expect(getPersonaPreset(undefined).id).toBe("balanced");
  });
});

describe("PERSONA_STORAGE_KEY", () => {
  it("is a non-empty string", () => {
    expect(typeof PERSONA_STORAGE_KEY).toBe("string");
    expect(PERSONA_STORAGE_KEY.length).toBeGreaterThan(0);
  });
});
