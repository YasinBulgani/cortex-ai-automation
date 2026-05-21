/**
 * Playwright MCP (Model Context Protocol) konfigürasyonu.
 *
 * AI agent'lar (Planner, Generator, Healer) için
 * tarayıcı erişim ve snapshot ayarları.
 */
export interface MCPConfig {
  browser: "chromium" | "firefox" | "webkit";
  headless: boolean;
  viewport: { width: number; height: number };
  snapshotMode: "accessibility" | "screenshot" | "both";
  healerEnabled: boolean;
  healerMaxRetries: number;
  llmEndpoint: string;
}

export const mcpConfig: MCPConfig = {
  browser: "chromium",
  headless: true,
  viewport: { width: 1280, height: 720 },
  snapshotMode: "accessibility",
  healerEnabled: process.env.ENABLE_SELF_HEALING !== "false",
  healerMaxRetries: 1,
  llmEndpoint: process.env.ENGINE_BASE || "http://127.0.0.1:5001",
};
