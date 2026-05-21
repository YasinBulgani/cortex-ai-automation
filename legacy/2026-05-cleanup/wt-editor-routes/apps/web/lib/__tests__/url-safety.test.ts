describe("getSafeNextPath", () => {
  function getSafeNextPath(candidate: string | null | undefined): string {
    if (!candidate) return "/projects";
    const trimmed = candidate.trim();
    if (!trimmed) return "/projects";
    if (trimmed === "/login" || trimmed.startsWith("/login/")) return "/projects";
    if (!trimmed.startsWith("/") || trimmed.startsWith("//")) return "/projects";
    if (trimmed.includes("\\") || trimmed.includes("\r") || trimmed.includes("\n")) {
      return "/projects";
    }
    try {
      const parsed = new URL(trimmed, "http://bgts.local");
      if (parsed.origin !== "http://bgts.local") return "/projects";
      return `${parsed.pathname}${parsed.search}${parsed.hash}`;
    } catch {
      return "/projects";
    }
  }

  it("returns /projects for null", () => {
    expect(getSafeNextPath(null)).toBe("/projects");
  });

  it("returns /projects for undefined", () => {
    expect(getSafeNextPath(undefined)).toBe("/projects");
  });

  it("returns /projects for empty string", () => {
    expect(getSafeNextPath("")).toBe("/projects");
  });

  it("returns /projects for /login path", () => {
    expect(getSafeNextPath("/login")).toBe("/projects");
  });

  it("returns /projects for /login/ subpath", () => {
    expect(getSafeNextPath("/login/callback")).toBe("/projects");
  });

  it("passes valid internal paths through", () => {
    expect(getSafeNextPath("/p/proj-1/scenarios")).toBe("/p/proj-1/scenarios");
  });

  it("rejects protocol-relative URLs", () => {
    expect(getSafeNextPath("//evil.com")).toBe("/projects");
  });

  it("rejects relative paths without leading slash", () => {
    expect(getSafeNextPath("relative/path")).toBe("/projects");
  });

  it("rejects backslash injection", () => {
    expect(getSafeNextPath("/path\\evil")).toBe("/projects");
  });

  it("rejects newline injection", () => {
    expect(getSafeNextPath("/path\nHeader: injected")).toBe("/projects");
  });

  it("rejects carriage return injection", () => {
    expect(getSafeNextPath("/path\rHeader: injected")).toBe("/projects");
  });

  it("preserves query params", () => {
    expect(getSafeNextPath("/p/proj-1?tab=2")).toBe("/p/proj-1?tab=2");
  });

  it("preserves hash fragments", () => {
    expect(getSafeNextPath("/p/proj-1#section")).toBe("/p/proj-1#section");
  });
});
