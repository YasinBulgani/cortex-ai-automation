import { isTransientError, retry } from "@/lib/retry";

// Force jitter=none for deterministic tests
const noJitter = { jitter: "none" as const, baseDelayMs: 1, maxDelayMs: 2 };

describe("retry()", () => {
  it("returns immediately when fn resolves on first try", async () => {
    const fn = jest.fn(() => Promise.resolve(42));
    const result = await retry(fn, noJitter);
    expect(result).toBe(42);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("retries on failure up to maxRetries+1 attempts", async () => {
    const fn = jest.fn(() => Promise.reject(new Error("transient")));
    await expect(retry(fn, { ...noJitter, maxRetries: 3 })).rejects.toThrow(
      /retry failed after 4 attempts/,
    );
    expect(fn).toHaveBeenCalledTimes(4);
  });

  it("succeeds after intermittent failure", async () => {
    let calls = 0;
    const fn = jest.fn(() => {
      calls++;
      return calls < 3 ? Promise.reject(new Error("flaky")) : Promise.resolve("ok");
    });
    const result = await retry(fn, { ...noJitter, maxRetries: 5 });
    expect(result).toBe("ok");
    expect(calls).toBe(3);
  });

  it("calls onRetry hook before each retry", async () => {
    const onRetry = jest.fn();
    const fn = jest
      .fn()
      .mockRejectedValueOnce(new Error("e1"))
      .mockResolvedValueOnce("done");
    await retry(fn, { ...noJitter, onRetry });
    expect(onRetry).toHaveBeenCalledTimes(1);
    const [err, attempt, delay] = onRetry.mock.calls[0];
    expect((err as Error).message).toBe("e1");
    expect(attempt).toBe(1);
    expect(typeof delay).toBe("number");
  });

  it("aborts further retries when shouldRetry returns false", async () => {
    const shouldRetry = jest.fn(() => false);
    const fn = jest.fn(() => Promise.reject(new Error("permanent")));
    await expect(retry(fn, { ...noJitter, shouldRetry, maxRetries: 5 })).rejects.toThrow(
      /retry failed after 6 attempts/,
    );
    // fn called only once since shouldRetry stopped further attempts
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("respects AbortSignal — does not start new attempt after abort", async () => {
    const controller = new AbortController();
    controller.abort();
    const fn = jest.fn(() => Promise.resolve("never"));
    await expect(
      retry(fn, { ...noJitter, signal: controller.signal }),
    ).rejects.toThrow();
    expect(fn).not.toHaveBeenCalled();
  });

  it("wrapped error preserves cause + attempts", async () => {
    const original = new Error("root cause");
    const fn = jest.fn(() => Promise.reject(original));
    try {
      await retry(fn, { ...noJitter, maxRetries: 2 });
      fail("should have thrown");
    } catch (e: any) {
      expect(e.attempts).toBe(3);
      expect(e.cause).toBe(original);
    }
  });

  it("applies exponential backoff (delay grows)", async () => {
    const delays: number[] = [];
    const fn = jest.fn(() => Promise.reject(new Error("boom")));
    await retry(fn, {
      maxRetries: 3,
      baseDelayMs: 10,
      factor: 2,
      maxDelayMs: 10_000,
      jitter: "none",
      onRetry: (_e, _a, delay) => {
        delays.push(delay);
      },
    }).catch(() => {});
    // attempts 1,2,3 → 10, 20, 40
    expect(delays).toEqual([10, 20, 40]);
  });

  it("caps delay at maxDelayMs", async () => {
    const delays: number[] = [];
    const fn = jest.fn(() => Promise.reject(new Error("boom")));
    // Tiny base values for fast test; cap ratio is what matters
    await retry(fn, {
      maxRetries: 4,
      baseDelayMs: 1,
      factor: 10,
      maxDelayMs: 5,
      jitter: "none",
      onRetry: (_e, _a, delay) => {
        delays.push(delay);
      },
    }).catch(() => {});
    // 1, 5 (capped), 5, 5
    expect(delays[0]).toBe(1);
    expect(delays[1]).toBe(5);
    expect(delays[2]).toBe(5);
    expect(delays[3]).toBe(5);
  });
});

describe("isTransientError()", () => {
  it("returns true for TypeError (network)", () => {
    expect(isTransientError(new TypeError("Failed to fetch"))).toBe(true);
  });

  it("returns true for 5xx status", () => {
    expect(isTransientError({ status: 503 })).toBe(true);
    expect(isTransientError({ status: 500 })).toBe(true);
  });

  it("returns true for 408 timeout and 429 rate limit", () => {
    expect(isTransientError({ status: 408 })).toBe(true);
    expect(isTransientError({ status: 429 })).toBe(true);
  });

  it("returns false for 4xx (except 408, 429)", () => {
    expect(isTransientError({ status: 400 })).toBe(false);
    expect(isTransientError({ status: 401 })).toBe(false);
    expect(isTransientError({ status: 404 })).toBe(false);
  });

  it("returns false for AbortError", () => {
    const err = new Error("aborted");
    (err as any).name = "AbortError";
    expect(isTransientError(err)).toBe(false);
  });

  it("returns true for ECONNRESET / ETIMEDOUT messages", () => {
    expect(isTransientError(new Error("connect ECONNRESET 1.2.3.4:80"))).toBe(true);
    expect(isTransientError(new Error("ETIMEDOUT"))).toBe(true);
  });

  it("returns false for null/undefined", () => {
    expect(isTransientError(null)).toBe(false);
    expect(isTransientError(undefined)).toBe(false);
  });
});
