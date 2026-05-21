/** @jest-environment node */
import { SERVICE_NAMES, parseServicesBody, ensureMutationEnabled } from "../dev-services";

// ---------------------------------------------------------------------------
// Mock node:child_process to avoid actual process spawning
// ---------------------------------------------------------------------------
jest.mock("node:child_process", () => ({
  execFile: jest.fn(),
}));

// ---------------------------------------------------------------------------
// SERVICE_NAMES
// ---------------------------------------------------------------------------
describe("SERVICE_NAMES", () => {
  it("is an array containing all expected service identifiers", () => {
    expect(SERVICE_NAMES).toContain("postgres");
    expect(SERVICE_NAMES).toContain("redis");
    expect(SERVICE_NAMES).toContain("backend");
    expect(SERVICE_NAMES).toContain("worker");
    expect(SERVICE_NAMES).toContain("engine");
    expect(SERVICE_NAMES).toContain("ai-gateway");
  });

  it("has length 6", () => {
    expect(SERVICE_NAMES).toHaveLength(6);
  });
});

// ---------------------------------------------------------------------------
// parseServicesBody
// ---------------------------------------------------------------------------
describe("parseServicesBody", () => {
  it("returns all SERVICE_NAMES when body is undefined", () => {
    expect(parseServicesBody(undefined)).toEqual([...SERVICE_NAMES]);
  });

  it("returns all SERVICE_NAMES when body is null", () => {
    expect(parseServicesBody(null)).toEqual([...SERVICE_NAMES]);
  });

  it("returns all SERVICE_NAMES when body is an empty object {}", () => {
    expect(parseServicesBody({})).toEqual([...SERVICE_NAMES]);
  });

  it("returns filtered array for valid service names", () => {
    const result = parseServicesBody({ services: ["postgres", "redis"] });
    expect(result).toEqual(["postgres", "redis"]);
  });

  it("throws when the services array contains invalid names", () => {
    expect(() =>
      parseServicesBody({ services: ["postgres", "invalid"] })
    ).toThrow();
  });

  it("returns all SERVICE_NAMES when services array is empty", () => {
    expect(parseServicesBody({ services: [] })).toEqual([...SERVICE_NAMES]);
  });
});

// ---------------------------------------------------------------------------
// ensureMutationEnabled
// ---------------------------------------------------------------------------
describe("ensureMutationEnabled", () => {
  const originalNodeEnv = process.env.NODE_ENV;
  const originalEnableControl = process.env.ENABLE_DEV_SERVICE_CONTROL;

  afterEach(() => {
    // Restore environment after each test
    process.env.NODE_ENV = originalNodeEnv;
    if (originalEnableControl === undefined) {
      delete process.env.ENABLE_DEV_SERVICE_CONTROL;
    } else {
      process.env.ENABLE_DEV_SERVICE_CONTROL = originalEnableControl;
    }
  });

  it("does not throw when NODE_ENV is not 'production' (default Jest env)", () => {
    // Jest sets NODE_ENV to "test" by default
    expect(() => ensureMutationEnabled()).not.toThrow();
  });

  it("throws when NODE_ENV is 'production' and ENABLE_DEV_SERVICE_CONTROL is not set", () => {
    process.env.NODE_ENV = "production";
    delete process.env.ENABLE_DEV_SERVICE_CONTROL;

    expect(() => ensureMutationEnabled()).toThrow();
  });

  it("does not throw when NODE_ENV is 'production' and ENABLE_DEV_SERVICE_CONTROL is 'true'", () => {
    process.env.NODE_ENV = "production";
    process.env.ENABLE_DEV_SERVICE_CONTROL = "true";

    expect(() => ensureMutationEnabled()).not.toThrow();
  });
});
