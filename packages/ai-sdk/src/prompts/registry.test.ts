import { describe, it, expect } from "vitest";
import { PromptRegistry, renderPrompt, type PromptTemplate } from "./registry";

const samplePrompt: PromptTemplate<{ name: string; topic: string }> = {
  id: "test.greeting",
  version: "1.0.0",
  description: "Test prompt",
  template: "Hello {{ name }}, let's talk about {{ topic }}.",
  variables: ["name", "topic"],
};

describe("renderPrompt", () => {
  it("substitutes variables", () => {
    const result = renderPrompt(samplePrompt, { name: "Ada", topic: "math" });
    expect(result).toBe("Hello Ada, let's talk about math.");
  });

  it("throws when variable missing", () => {
    expect(() =>
      renderPrompt(samplePrompt, { name: "Ada" } as { name: string; topic: string }),
    ).toThrow(/Missing variable/);
  });

  it("throws when unfilled placeholder remains", () => {
    const buggy: PromptTemplate<{ name: string }> = {
      ...samplePrompt,
      template: "Hello {{ name }}, {{ undefined_var }}",
      variables: ["name"],
    };
    expect(() => renderPrompt(buggy, { name: "Ada" })).toThrow(/Unfilled placeholder/);
  });

  it("handles repeated variables", () => {
    const repeated: PromptTemplate<{ word: string }> = {
      ...samplePrompt,
      template: "{{ word }} {{ word }} {{ word }}",
      variables: ["word"],
    };
    expect(renderPrompt(repeated, { word: "echo" })).toBe("echo echo echo");
  });

  it("handles whitespace in placeholders", () => {
    const ws: PromptTemplate<{ name: string }> = {
      ...samplePrompt,
      template: "Hi {{name}} and {{  name  }}",
      variables: ["name"],
    };
    expect(renderPrompt(ws, { name: "X" })).toBe("Hi X and X");
  });
});

describe("PromptRegistry", () => {
  it("registers and retrieves by id", () => {
    const reg = new PromptRegistry();
    reg.register(samplePrompt);
    expect(reg.get(samplePrompt.id)).toBeDefined();
  });

  it("retrieves by id@version", () => {
    const reg = new PromptRegistry();
    reg.register(samplePrompt);
    expect(reg.get(samplePrompt.id, "1.0.0")).toBeDefined();
  });

  it("returns undefined for unknown id", () => {
    const reg = new PromptRegistry();
    expect(reg.get("nonexistent")).toBeUndefined();
  });

  it("lists unique prompts", () => {
    const reg = new PromptRegistry();
    reg.register(samplePrompt);
    reg.register({ ...samplePrompt, version: "1.0.1" });
    const list = reg.list();
    expect(list.length).toBe(1);
  });
});
