/** @jest-environment node */

jest.mock("../(dashboard)/new-project/types", () => ({
  actionNeedsLocator: (action: string) =>
    ["click", "input", "clear", "wait", "verify", "see"].includes(action),
  NO_LOCATOR_ACTIONS: new Set(["open"]),
}));

import {
  slugifyProjectName,
  maviyakaStepLine,
  buildFeatureFromMapping,
  buildXPathReportMd,
} from "../(dashboard)/new-project/helpers";

import type { StepMapping, ScenarioMappingReport } from "../(dashboard)/new-project/types";

// ─── slugifyProjectName ──────────────────────────────────────────────────────

describe("slugifyProjectName", () => {
  it("converts Turkish characters to ASCII equivalents", () => {
    expect(slugifyProjectName("Çalışma")).toBe("calisma");
  });

  it("replaces spaces with underscores", () => {
    expect(slugifyProjectName("test projesi")).toBe("test_projesi");
  });

  it("strips leading and trailing underscores", () => {
    expect(slugifyProjectName("_test_")).toBe("test");
  });

  it("returns 'proje' for empty string", () => {
    expect(slugifyProjectName("")).toBe("proje");
  });

  it("returns 'proje' for whitespace-only string", () => {
    expect(slugifyProjectName("   ")).toBe("proje");
  });

  it("truncates result to 40 characters maximum", () => {
    const long = "abcdefghijklmnopqrstuvwxyz1234567890extra";
    const result = slugifyProjectName(long);
    expect(result.length).toBeLessThanOrEqual(40);
  });

  it("removes special characters except letters, digits, and underscores", () => {
    expect(slugifyProjectName("hello@world!foo#bar")).toBe("hello_world_foo_bar");
  });
});

// ─── maviyakaStepLine ────────────────────────────────────────────────────────

function makeStep(overrides: Partial<StepMapping>): StepMapping {
  return {
    idx: 0,
    original: "step text",
    action: "see",
    locator_key: null,
    xpath: null,
    data_value: null,
    source: "rule",
    ...overrides,
  } as StepMapping;
}

describe("maviyakaStepLine", () => {
  const URL = "https://example.com";

  it("open action returns Given line with the URL", () => {
    const line = maviyakaStepLine(makeStep({ action: "open" }), URL);
    expect(line).toContain("Given I open the application url");
    expect(line).toContain(URL);
  });

  it("click action returns When I click on line", () => {
    const line = maviyakaStepLine(
      makeStep({ action: "click", locator_key: "LoginButton" }),
      URL,
    );
    expect(line).toContain("When I click on");
    expect(line).toContain("LoginButton");
  });

  it("input action with data_value includes value and locator", () => {
    const line = maviyakaStepLine(
      makeStep({ action: "input", locator_key: "UsernameField", data_value: "admin" }),
      URL,
    );
    expect(line).toContain("When I enter");
    expect(line).toContain("admin");
    expect(line).toContain("UsernameField");
  });

  it("verify action returns Then I verify element line", () => {
    const line = maviyakaStepLine(
      makeStep({ action: "verify", locator_key: "StatusLabel", data_value: "Success" }),
      URL,
    );
    expect(line).toContain("Then I verify element");
    expect(line).toContain("StatusLabel");
    expect(line).toContain("Success");
  });

  it("see action returns Then I see the element line", () => {
    const line = maviyakaStepLine(
      makeStep({ action: "see", locator_key: "WelcomeBanner" }),
      URL,
    );
    expect(line).toContain("Then I see the element");
    expect(line).toContain("WelcomeBanner");
  });

  it("unknown action falls back to see/default line", () => {
    // Casting to bypass TypeScript — simulates runtime unknown action
    const line = maviyakaStepLine(
      makeStep({ action: "unknown" as StepMapping["action"], locator_key: "SomeEl" }),
      URL,
    );
    expect(line).toContain("Then I see the element");
  });
});

// ─── buildFeatureFromMapping ─────────────────────────────────────────────────

describe("buildFeatureFromMapping", () => {
  const sampleMapping: ScenarioMappingReport = {
    scenario_id: "sc-1",
    scenario_title: "User Login",
    llm_used: false,
    steps: [
      {
        idx: -1,
        original: "navigate to app",
        action: "open",
        locator_key: null,
        xpath: null,
        data_value: null,
        source: "auto",
      },
      {
        idx: 0,
        original: "click the login button",
        action: "click",
        locator_key: "LoginBtn",
        xpath: null,
        data_value: null,
        source: "llm",
      },
    ],
  };

  it("returns a string starting with 'Feature:'", () => {
    const result = buildFeatureFromMapping("My Feature", sampleMapping, "https://app.test");
    expect(result.startsWith("Feature:")).toBe(true);
  });

  it("contains the provided title in the feature header", () => {
    const result = buildFeatureFromMapping("Login Flow", sampleMapping, "https://app.test");
    expect(result).toContain("Feature: Login Flow");
  });

  it("contains 'Scenario:' keyword", () => {
    const result = buildFeatureFromMapping("My Feature", sampleMapping, "https://app.test");
    expect(result).toContain("Scenario:");
  });

  it("contains generated step lines from the mapping", () => {
    const result = buildFeatureFromMapping("My Feature", sampleMapping, "https://app.test");
    // open → Given I open
    expect(result).toContain("Given I open the application url");
    // click → When I click on
    expect(result).toContain("When I click on");
    expect(result).toContain("LoginBtn");
  });
});

// ─── buildXPathReportMd (smoke) ──────────────────────────────────────────────

describe("buildXPathReportMd", () => {
  const mappings: ScenarioMappingReport[] = [
    {
      scenario_id: "sc-1",
      scenario_title: "Smoke Test",
      llm_used: true,
      steps: [
        {
          idx: 0,
          original: "click submit",
          action: "click",
          locator_key: "SubmitBtn",
          xpath: "//button[@id='submit']",
          data_value: null,
          source: "llm",
        },
      ],
    },
  ];

  it("returns a string containing the URL and environment info", () => {
    const result = buildXPathReportMd(mappings, "https://app.test", "staging");
    expect(result).toContain("https://app.test");
    expect(result).toContain("STAGING");
  });

  it("contains the scenario title", () => {
    const result = buildXPathReportMd(mappings, "https://app.test", "staging");
    expect(result).toContain("Smoke Test");
  });

  it("includes scenario count", () => {
    const result = buildXPathReportMd(mappings, "https://app.test", "staging");
    expect(result).toContain("1");
  });
});
