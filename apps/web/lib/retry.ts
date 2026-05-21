/**
 * Smart retry with exponential backoff + jitter.
 *
 * Use cases:
 *  - Test execution step retry on transient flakiness
 *  - API call retry on 5xx / network errors
 *  - SSE reconnection
 *
 * Default policy:
 *  - 3 retries
 *  - Base delay 250ms, factor 2, max 5000ms
 *  - Full jitter (0..delay random)
 *  - Retries on: any thrown error UNLESS shouldRetry returns false
 */

export type RetryPolicy = {
  /** Maximum number of retry attempts (excluding the initial try). Default 3. */
  maxRetries?: number;
  /** Base delay in ms before the first retry. Default 250. */
  baseDelayMs?: number;
  /** Backoff multiplier per attempt. Default 2. */
  factor?: number;
  /** Maximum capped delay in ms. Default 5000. */
  maxDelayMs?: number;
  /** Jitter strategy: "full" (default), "equal", or "none". */
  jitter?: "full" | "equal" | "none";
  /** Predicate: return false to abort retries for this error. Default: always retry. */
  shouldRetry?: (error: unknown, attempt: number) => boolean;
  /** Called before each retry — useful for logging/metrics. */
  onRetry?: (error: unknown, attempt: number, delayMs: number) => void;
  /** AbortSignal that cancels remaining retries. */
  signal?: AbortSignal;
};

export type RetryError = Error & {
  attempts: number;
  cause: unknown;
};

const DEFAULTS: Required<
  Omit<RetryPolicy, "shouldRetry" | "onRetry" | "signal">
> = {
  maxRetries: 3,
  baseDelayMs: 250,
  factor: 2,
  maxDelayMs: 5000,
  jitter: "full",
};

function computeDelay(
  attempt: number,
  baseDelayMs: number,
  factor: number,
  maxDelayMs: number,
  jitter: RetryPolicy["jitter"],
): number {
  // attempt is 1-based: first retry = attempt 1
  const raw = baseDelayMs * Math.pow(factor, attempt - 1);
  const capped = Math.min(raw, maxDelayMs);
  if (jitter === "none") return capped;
  if (jitter === "equal") return capped / 2 + Math.random() * (capped / 2);
  return Math.random() * capped; // full
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("aborted", "AbortError"));
      return;
    }
    const t = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(t);
      reject(new DOMException("aborted", "AbortError"));
    });
  });
}

/**
 * Retry an async operation with exponential backoff + jitter.
 *
 * @example
 *   const result = await retry(() => apiFetch("/api/v1/run"), {
 *     maxRetries: 5,
 *     shouldRetry: (e) => isTransient(e),
 *   });
 */
export async function retry<T>(
  fn: () => Promise<T>,
  policy: RetryPolicy = {},
): Promise<T> {
  const cfg = { ...DEFAULTS, ...policy };
  let lastError: unknown;

  for (let attempt = 0; attempt <= cfg.maxRetries; attempt++) {
    if (cfg.signal?.aborted) {
      throw new DOMException("aborted", "AbortError");
    }
    try {
      return await fn();
    } catch (err) {
      lastError = err;
      const isLast = attempt === cfg.maxRetries;
      if (isLast) break;
      if (policy.shouldRetry && !policy.shouldRetry(err, attempt + 1)) break;

      const delay = computeDelay(
        attempt + 1,
        cfg.baseDelayMs,
        cfg.factor,
        cfg.maxDelayMs,
        cfg.jitter,
      );
      policy.onRetry?.(err, attempt + 1, delay);
      try {
        await sleep(delay, cfg.signal);
      } catch (sleepErr) {
        // Signal aborted during sleep
        throw sleepErr;
      }
    }
  }

  const wrapped: RetryError = Object.assign(
    new Error(
      `retry failed after ${cfg.maxRetries + 1} attempts: ${
        lastError instanceof Error ? lastError.message : String(lastError)
      }`,
    ) as RetryError,
    { attempts: cfg.maxRetries + 1, cause: lastError },
  );
  throw wrapped;
}

/**
 * Common predicate: retry only on transient errors (network/timeout/5xx).
 */
export function isTransientError(err: unknown): boolean {
  if (!err) return false;
  if (err instanceof TypeError) return true; // network errors usually surface as TypeError
  const e = err as { status?: number; name?: string; message?: string };
  if (e.name === "AbortError") return false;
  if (typeof e.status === "number") {
    return e.status >= 500 || e.status === 408 || e.status === 429;
  }
  if (typeof e.message === "string") {
    return (
      /network|fetch failed|ECONNRESET|ETIMEDOUT|timeout/i.test(e.message) ||
      false
    );
  }
  return false;
}
