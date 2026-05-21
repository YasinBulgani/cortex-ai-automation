import { describe, it, expect, beforeEach } from "vitest";
import {
  generateBddScenario,
  analyzeTestFailure,
  healLocator,
  registerBuiltinPrompts,
} from "./library";
import { renderPrompt, defaultRegistry } from "./registry";

describe("generateBddScenario prompt", () => {
  it("has correct id and version", () => {
    expect(generateBddScenario.id).toBe("scenario.generate-bdd");
    expect(generateBddScenario.version).toBe("1.0.0");
  });

  it("declares required variables", () => {
    expect(generateBddScenario.variables).toContain("project_name");
    expect(generateBddScenario.variables).toContain("requirement");
    expect(generateBddScenario.variables).toContain("domain_context");
  });

  it("renders correctly with all variables", () => {
    const rendered = renderPrompt(generateBddScenario, {
      project_name: "Test App",
      requirement: "Login with 2FA",
      domain_context: "Security",
    });
    expect(rendered).toContain("Test App");
    expect(rendered).toContain("Login with 2FA");
    expect(rendered).toContain("Security");
  });

  it("throws when variable missing", () => {
    expect(() =>
      renderPrompt(generateBddScenario, {
        project_name: "X",
        requirement: "Y",
      } as Parameters<typeof renderPrompt<typeof generateBddScenario>>[1]),
    ).toThrow();
  });

  it("has premium recommended tier", () => {
    expect(generateBddScenario.recommended_tier).toBe("premium");
  });
});

describe("analyzeTestFailure prompt", () => {
  it("has correct id", () => {
    expect(analyzeTestFailure.id).toBe("analysis.test-failure");
  });

  it("declares all required variables", () => {
    const vars = analyzeTestFailure.variables;
    expect(vars).toContain("test_name");
    expect(vars).toContain("error_message");
    expect(vars).toContain("stack_trace");
    expect(vars).toContain("recent_changes");
  });

  it("renders with all variables substituted", () => {
    const rendered = renderPrompt(analyzeTestFailure, {
      test_name: "login_test",
      error_message: "Timeout 30000ms",
      stack_trace: "at Page.waitForSelector",
      recent_changes: "Added 2FA step",
    });
    expect(rendered).toContain("login_test");
    expect(rendered).toContain("Timeout 30000ms");
    expect(rendered).toContain("Added 2FA step");
  });

  it("template contains JSON format hint", () => {
    expect(analyzeTestFailure.template).toContain("root_cause");
    expect(analyzeTestFailure.template).toContain("fix_suggestion");
  });
});

describe("healLocator prompt", () => {
  it("has correct id", () => {
    expect(healLocator.id).toBe("automation.heal-locator");
  });

  it("renders with all variables", () => {
    const rendered = renderPrompt(healLocator, {
      broken_locator: "#submit-btn",
      page_url: "https://app.example.com/login",
      dom_snippet: "<button class='btn-primary'>Submit</button>",
    });
    expect(rendered).toContain("#submit-btn");
    expect(rendered).toContain("https://app.example.com/login");
    expect(rendered).toContain("Submit");
  });

  it("has balanced recommended tier", () => {
    expect(healLocator.recommended_tier).toBe("balanced");
  });
});

describe("registerBuiltinPrompts", () => {
  beforeEach(() => {
    registerBuiltinPrompts();
  });

  it("registers generateBddScenario", () => {
    expect(defaultRegistry.get(generateBddScenario.id)).toBeDefined();
  });

  it("registers analyzeTestFailure", () => {
    expect(defaultRegistry.get(analyzeTestFailure.id)).toBeDefined();
  });

  it("registers healLocator", () => {
    expect(defaultRegistry.get(healLocator.id)).toBeDefined();
  });

  it("all built-in prompts appear in list", () => {
    const ids = defaultRegistry.list().map(p => p.id);
    expect(ids).toContain(generateBddScenario.id);
    expect(ids).toContain(analyzeTestFailure.id);
    expect(ids).toContain(healLocator.id);
  });
});
