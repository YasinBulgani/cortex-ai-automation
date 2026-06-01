/**
 * @cortex/sdk — Automation API client.
 *
 * Covers Playwright MCP proxy endpoints and NL test generation.
 */

import type { CortexClient } from "../common/client";
import type {
  PlaywrightSession,
  PlaywrightSessionConfig,
  NavigateInput,
  FillInput,
  ClickInput,
  LocatorInput,
  ScreenshotResult,
  NlTestValidateInput,
  NlTestValidateResult,
  AutomationSuiteHealth,
} from "./types";

const PLAYWRIGHT_BASE = "/api/v1/playwright-mcp";
const NL_BASE = "/api/v1/nl-test";
const SUITE_BASE = "/api/v1/automation-suite";

// ── Playwright sub-client ─────────────────────────────────────────────────────

export class PlaywrightClient {
  constructor(private readonly http: CortexClient) {}

  /** Start a new browser session. */
  createSession(config: PlaywrightSessionConfig = {}): Promise<PlaywrightSession> {
    return this.http.post(`${PLAYWRIGHT_BASE}/sessions`, { json: config });
  }

  /** Navigate to a URL in an existing session. */
  navigate(sessionId: string, input: NavigateInput): Promise<{ ok: boolean }> {
    return this.http.post(`${PLAYWRIGHT_BASE}/sessions/${sessionId}/navigate`, {
      json: input,
    });
  }

  /** Click an element. */
  click(sessionId: string, input: ClickInput): Promise<{ ok: boolean }> {
    return this.http.post(`${PLAYWRIGHT_BASE}/sessions/${sessionId}/click`, {
      json: input,
    });
  }

  /** Fill an input element. */
  fill(sessionId: string, input: FillInput): Promise<{ ok: boolean }> {
    return this.http.post(`${PLAYWRIGHT_BASE}/sessions/${sessionId}/fill`, {
      json: input,
    });
  }

  /** Take a screenshot of the current page. */
  screenshot(sessionId: string): Promise<ScreenshotResult> {
    return this.http.get(`${PLAYWRIGHT_BASE}/sessions/${sessionId}/screenshot`);
  }

  /** Evaluate a locator and return matching element info. */
  locator(sessionId: string, input: LocatorInput): Promise<Record<string, unknown>> {
    return this.http.post(`${PLAYWRIGHT_BASE}/sessions/${sessionId}/locator`, {
      json: input,
    });
  }

  /** Close a browser session. */
  closeSession(sessionId: string): Promise<{ ok: boolean }> {
    return this.http.delete(`${PLAYWRIGHT_BASE}/sessions/${sessionId}`);
  }
}

// ── NL test client ────────────────────────────────────────────────────────────

export class NlTestClient {
  constructor(private readonly http: CortexClient) {}

  /** Validate and parse a natural-language test description. */
  validate(input: NlTestValidateInput): Promise<NlTestValidateResult> {
    return this.http.post(`${NL_BASE}/validate`, { json: input });
  }
}

// ── Main automation client ────────────────────────────────────────────────────

export class AutomationClient {
  readonly playwright: PlaywrightClient;
  readonly nlTest: NlTestClient;

  constructor(private readonly http: CortexClient) {
    this.playwright = new PlaywrightClient(http);
    this.nlTest = new NlTestClient(http);
  }

  /** Check health of all automation sub-systems. */
  health(): Promise<AutomationSuiteHealth> {
    return this.http.get(`${SUITE_BASE}/health`);
  }
}
