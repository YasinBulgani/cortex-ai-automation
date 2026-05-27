// ── Types ────────────────────────────────────────────────────────────────────

export type ActionType =
  | "click"
  | "input"
  | "scroll"
  | "navigate"
  | "resize"
  | "keypress";

export type SessionConfig = {
  targetUrl: string;
  actionCount: number;
  seed: string;
  actionTypes: ActionType[];
};

export type AiPhase = "idle" | "scenarios" | "karate" | "done" | "error";

export type EngineAction = {
  step: number;
  type: string;
  url: string;
  timestamp: string;
  target?: string;
  value?: string;
  result?: string;
  triggered_error?: boolean;
  load_time_ms?: number;
  direction?: string;
  key?: string;
  viewport?: string;
};

export type EngineConsoleError = {
  type: string;
  text: string;
  url: string;
  timestamp: string;
  category: string;
};

export type EngineNetworkError = {
  url: string;
  status: number;
  page_url: string;
  timestamp: string;
  category: string;
};

export type EngineBug = {
  category: string;
  severity: "critical" | "warning" | string;
  count: number;
  sample: string;
  affected_pages: string[];
};

export type EngineScenario = {
  title: string;
  type: string;
  description: string;
  steps: { action: string; expected: string }[];
  priority: string;
};

export type EngineRecommendation = { priority: string; text: string };

export type EngineAnalysis = {
  scenarios: EngineScenario[];
  bugs: EngineBug[];
  recommendations: EngineRecommendation[];
  risk_level: string;
  summary: {
    total_bugs: number;
    critical_bugs: number;
    warning_bugs: number;
    scenarios_generated: number;
    pages_with_errors: number;
    error_categories: string[];
    network_categories: string[];
  };
};

export type EngineResult = {
  run_id?: string;
  status: string;
  test_url: string;
  actions_performed: number;
  actions_log: EngineAction[];
  action_stats: Record<string, { total: number; success: number; error: number }>;
  console_errors: EngineConsoleError[];
  network_errors: EngineNetworkError[];
  error_count: number;
  stability_score: number;
  pages_visited_count: number;
  total_time_seconds: number;
  started_at: string;
  video_url?: string | null;
  screenshots?: { final?: string; [key: string]: string | undefined };
  analysis: EngineAnalysis;
};

export type AuthConfig = {
  login_url: string;
  username_selector: string;
  password_selector: string;
  submit_selector: string;
  username: string;
  password: string;
};

export type LiveFrame = { step: number | "final"; screenshot: string; url: string };

export type HistoryEntry = {
  id: string;
  timestamp: string;
  url: string;
  actions: number;
  errors: number;
  stability: number;
  scenarios: number;
  videoUrl?: string | null;
  data: EngineResult;
};

// ── Constants ────────────────────────────────────────────────────────────────

export const DEFAULT_ACTIONS: ActionType[] = [
  "click",
  "input",
  "scroll",
  "navigate",
  "keypress",
];

export const ACTION_LABELS: Record<ActionType, string> = {
  click: "Rastgele Tıklama",
  input: "Rastgele Yazma",
  scroll: "Kaydırma",
  navigate: "Geri/İleri Gezinme",
  resize: "Pencere Boyutu Değiştirme",
  keypress: "Rastgele Tuş Basma",
};

export const FRONTEND_TO_ENGINE_ACTIONS: Record<ActionType, string[]> = {
  click: ["click"],
  input: ["fill"],
  scroll: ["scroll"],
  navigate: ["navigate", "back_forward"],
  resize: ["resize_viewport"],
  keypress: ["keyboard", "tab_navigation"],
};

export const HISTORY_KEY = "bgts_monkey_history_v1";
export const HISTORY_MAX = 20;
