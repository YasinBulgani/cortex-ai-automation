import { describe, it, expect } from "vitest";
import { ToolRegistry, searchProjectTool, type ToolContext } from "./index";

const ctx: ToolContext = {
  tenant_id: "tenant-1",
  user_id: "user-1",
  request_id: "req-1",
};

describe("ToolRegistry", () => {
  it("starts empty", () => {
    const registry = new ToolRegistry();
    expect(registry.list()).toHaveLength(0);
  });

  it("registers and retrieves a tool by name", () => {
    const registry = new ToolRegistry();
    registry.register("search_projects", searchProjectTool);
    expect(registry.get("search_projects")).toBe(searchProjectTool);
  });

  it("returns undefined for unknown tool", () => {
    const registry = new ToolRegistry();
    expect(registry.get("nonexistent")).toBeUndefined();
  });

  it("list returns schemas of registered tools", () => {
    const registry = new ToolRegistry();
    registry.register("search_projects", searchProjectTool);
    const tools = registry.list();
    expect(tools).toHaveLength(1);
    expect(tools[0].function.name).toBe("search_projects");
  });

  it("invoke calls handler and returns result", async () => {
    const registry = new ToolRegistry();
    registry.register("search_projects", searchProjectTool);
    const result = await registry.invoke("search_projects", { query: "alpha" }, ctx) as { results: Array<{ id: string; name: string }> };
    expect(result.results[0].name).toContain("alpha");
  });

  it("invoke throws for unknown tool", async () => {
    const registry = new ToolRegistry();
    await expect(registry.invoke("ghost", {}, ctx)).rejects.toThrow("Tool not found: ghost");
  });

  it("supports multiple registered tools", () => {
    const registry = new ToolRegistry();

    const tool2 = {
      schema: { type: "function" as const, function: { name: "other_tool", description: "other", parameters: { type: "object" as const, properties: {}, required: [] } } },
      async execute(_input: unknown, _ctx: ToolContext) { return {}; },
    };

    registry.register("search_projects", searchProjectTool);
    registry.register("other_tool", tool2);
    expect(registry.list()).toHaveLength(2);
  });

  it("later registration overwrites same name", async () => {
    const registry = new ToolRegistry();

    const v1 = {
      schema: { type: "function" as const, function: { name: "my_tool", description: "v1", parameters: { type: "object" as const, properties: {}, required: [] } } },
      async execute(_input: unknown, _ctx: ToolContext) { return { version: 1 }; },
    };
    const v2 = {
      schema: { type: "function" as const, function: { name: "my_tool", description: "v2", parameters: { type: "object" as const, properties: {}, required: [] } } },
      async execute(_input: unknown, _ctx: ToolContext) { return { version: 2 }; },
    };

    registry.register("my_tool", v1);
    registry.register("my_tool", v2);
    expect(registry.list()).toHaveLength(1);
    const result = await registry.invoke("my_tool", {}, ctx) as { version: number };
    expect(result.version).toBe(2);
  });
});

describe("searchProjectTool", () => {
  it("has correct schema function name", () => {
    expect(searchProjectTool.schema.function.name).toBe("search_projects");
  });

  it("schema requires query parameter", () => {
    expect(searchProjectTool.schema.function.parameters.required).toContain("query");
  });

  it("execute returns results array with id and name", async () => {
    const result = await searchProjectTool.execute({ query: "neurex" }, ctx);
    expect(result.results).toBeInstanceOf(Array);
    expect(result.results[0]).toHaveProperty("id");
    expect(result.results[0]).toHaveProperty("name");
  });

  it("execute reflects query in result name", async () => {
    const result = await searchProjectTool.execute({ query: "my-project" }, ctx);
    expect(result.results[0].name).toContain("my-project");
  });

  it("execute works without optional limit", async () => {
    const result = await searchProjectTool.execute({ query: "test" }, ctx);
    expect(result.results).toHaveLength(1);
  });
});
