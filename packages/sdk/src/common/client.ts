/**
 * @cortex/sdk — HTTP client foundation.
 *
 * Wraps fetch() with:
 *  - Base URL configuration
 *  - Authorization header injection (Bearer token)
 *  - JSON request / response handling
 *  - Typed error class (CortexApiError)
 *  - Automatic retry on 429 / 5xx (optional, configurable)
 */

// ── Error ─────────────────────────────────────────────────────────────────────

export class CortexApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly statusText: string,
    public readonly body: unknown,
    public readonly url: string,
  ) {
    super(`CortexApiError ${status} ${statusText} — ${url}`);
    this.name = "CortexApiError";
  }
}

// ── Config ────────────────────────────────────────────────────────────────────

export interface CortexClientConfig {
  /** Base URL, e.g. "https://api.cortex.example.com" */
  baseUrl: string;
  /** Bearer token or API key.  Injected as `Authorization: Bearer <token>`. */
  apiKey?: string;
  /**
   * Extra headers sent with every request.
   * Per-request headers override these.
   */
  defaultHeaders?: Record<string, string>;
  /**
   * Max number of automatic retries on 429 / 500-599.
   * Default: 2.  Set to 0 to disable.
   */
  maxRetries?: number;
  /**
   * Initial retry delay in milliseconds (doubles on each attempt).
   * Default: 500.
   */
  retryDelayMs?: number;
  /** Custom fetch implementation (useful for testing / Node.js polyfill). */
  fetch?: typeof globalThis.fetch;
}

// ── Request options ───────────────────────────────────────────────────────────

export interface RequestOptions {
  headers?: Record<string, string>;
  signal?: AbortSignal;
  /** If provided, body is serialized as JSON and Content-Type is set. */
  json?: unknown;
  /** Raw body string (overrides json). */
  body?: BodyInit;
}

// ── Client ────────────────────────────────────────────────────────────────────

export class CortexClient {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly defaultHeaders: Record<string, string>;
  private readonly maxRetries: number;
  private readonly retryDelayMs: number;
  private readonly _fetch: typeof globalThis.fetch;

  constructor(config: CortexClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, "");
    this.apiKey = config.apiKey;
    this.defaultHeaders = config.defaultHeaders ?? {};
    this.maxRetries = config.maxRetries ?? 2;
    this.retryDelayMs = config.retryDelayMs ?? 500;
    this._fetch = config.fetch ?? globalThis.fetch.bind(globalThis);
  }

  // ── Low-level ───────────────────────────────────────────────────────────────

  async request<T = unknown>(
    method: string,
    path: string,
    options: RequestOptions = {},
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;

    const headers: Record<string, string> = {
      Accept: "application/json",
      ...this.defaultHeaders,
    };

    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    let body: BodyInit | undefined = options.body;

    if (options.json !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.json);
    }

    if (options.headers) {
      Object.assign(headers, options.headers);
    }

    let attempt = 0;
    let lastError: CortexApiError | null = null;

    while (attempt <= this.maxRetries) {
      const res = await this._fetch(url, {
        method,
        headers,
        body,
        signal: options.signal,
      });

      if (res.ok) {
        if (res.status === 204) return undefined as T;
        return (await res.json()) as T;
      }

      const isRetryable =
        res.status === 429 || (res.status >= 500 && res.status < 600);

      let bodyText: unknown;
      try {
        bodyText = await res.json();
      } catch {
        bodyText = await res.text().catch(() => null);
      }

      lastError = new CortexApiError(res.status, res.statusText, bodyText, url);

      if (!isRetryable || attempt >= this.maxRetries) {
        throw lastError;
      }

      // Exponential backoff
      await new Promise((r) =>
        setTimeout(r, this.retryDelayMs * Math.pow(2, attempt)),
      );
      attempt++;
    }

    throw lastError!;
  }

  // ── Convenience ─────────────────────────────────────────────────────────────

  get<T = unknown>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>("GET", path, options);
  }

  post<T = unknown>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>("POST", path, options);
  }

  patch<T = unknown>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>("PATCH", path, options);
  }

  put<T = unknown>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>("PUT", path, options);
  }

  delete<T = unknown>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>("DELETE", path, options);
  }
}
