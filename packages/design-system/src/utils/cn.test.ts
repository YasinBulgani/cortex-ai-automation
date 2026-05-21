import { describe, it, expect } from "vitest";
import { cn } from "./cn";

describe("cn utility", () => {
  it("merges string class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("skips falsy values", () => {
    expect(cn("foo", false, null, undefined, "")).toBe("foo");
  });

  it("handles conditional classes", () => {
    const active = true;
    const disabled = false;
    expect(cn("base", active && "active", disabled && "disabled")).toBe("base active");
  });

  it("flattens nested arrays", () => {
    expect(cn("a", ["b", ["c", "d"]])).toBe("a b c d");
  });

  it("returns empty string when all falsy", () => {
    expect(cn(false, null, undefined)).toBe("");
  });

  it("handles numbers", () => {
    expect(cn("col", 4)).toBe("col 4");
  });
});
