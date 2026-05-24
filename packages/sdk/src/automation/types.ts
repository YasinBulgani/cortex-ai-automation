/**
 * Automation domain types.
 */

import type { UUID, ISODateTime } from "../common/types";

// ── Playwright MCP ────────────────────────────────────────────────────────────

export type PlaywrightBrowser = "chromium" | "firefox" | "webkit";

export interface PlaywrightSessionConfig {
  browser?: PlaywrightBrowser;
  headless?: boolean;
  viewport?: { width: number; height: number };
  locale?: string;
  timezone?: string;
}

export interface PlaywrightSession {
  session_id: string;
  browser: PlaywrightBrowser;
  status: "created" | "active" | "closed";
  created_at: ISODateTime;
}

export interface NavigateInput {
  url: string;
}

export interface LocatorInput {
  selector: string;
}

export interface FillInput {
  selector: string;
  value: string;
}

export interface ClickInput {
  selector: string;
}

export interface ScreenshotResult {
  base64: string;
  mime_type: "image/png";
}

// ── AI-driven test generation ─────────────────────────────────────────────────

export interface NlTestValidateInput {
  nl_description: string;
  project_id?: UUID;
}

export interface NlTestValidateResult {
  valid: boolean;
  confidence: number;
  suggested_steps: Array<{
    action: string;
    target?: string;
    value?: string;
  }>;
  warnings: string[];
}

// ── Automation suite health ───────────────────────────────────────────────────

export interface AutomationSuiteHealth {
  status: "healthy" | "degraded" | "down";
  components: Record<
    string,
    {
      status: "healthy" | "degraded" | "down";
      latency_ms?: number;
      detail?: string;
    }
  >;
}
