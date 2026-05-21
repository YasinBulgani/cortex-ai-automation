/**
 * DSL + Otomasyon Süiti API istemcisi.
 *
 * Backend endpoint'leri:
 *   GET  /api/v1/dsl/actions                 — sayfalandırılmış liste
 *   GET  /api/v1/dsl/actions/{id}            — tekil
 *   GET  /api/v1/dsl/search?q=...            — alias/description araması
 *   GET  /api/v1/dsl/search/semantic         — AI (embedding) arama
 *   GET  /api/v1/dsl/stats                   — katalog istatistikleri
 *   GET  /api/v1/dsl/categories              — 2 seviyeli ağaç
 *   POST /api/v1/dsl/suggest                 — NL → öneri (auto|lexical|hybrid|semantic)
 *   POST /api/v1/dsl/feedback                — arama sonuçu için 👍/👎
 *   GET  /api/v1/dsl/index/info              — embed index durumu
 *   POST /api/v1/dsl/index/rebuild           — embed index yeniden inşa
 *   POST /api/v1/dsl/reload                  — cache reload (+ index rebuild)
 *
 *   POST /api/v1/automation-suite/generate
 *   POST /api/v1/automation-suite/run
 *   GET  /api/v1/automation-suite/runs/{id}
 *   POST /api/v1/automation-suite/catalog/suggest
 *   GET  /api/v1/automation-suite/health
 */

import { apiFetch } from "@/lib/api-client";

// ── DSL Types ────────────────────────────────────────────────────────────────

export type DslLang = "tr" | "en";

export type DslParameter = {
  name: string;
  type: string;
  description?: string | null;
  required?: boolean;
  default?: unknown;
  examples?: unknown[] | null;
};

export type DslImplementation = {
  source_file: string;
  module?: string | null;
  function?: string | null;
  class?: string | null;
  method?: string | null;
  pattern?: string | null;
};

export type DslDeprecation = {
  replacement: string;
  since?: string | null;
  reason?: string | null;
};

export type DslAction = {
  id: string;
  category: string;
  description: string;
  aliases: Record<string, string[]>;
  // Backend Pydantic tarafı her zaman boş liste döner; tip katmanı bunu zorunlu
  // kabul eder ki UI'da optional check'i her yerde yapmak zorunda kalmayalım.
  parameters: DslParameter[];
  implementations: Record<string, DslImplementation>;
  tags: string[];
  since?: string | null;
  deprecated?: DslDeprecation | boolean | null;
  examples: string[];
  notes?: string | null;
  source_yaml?: string | null;
};

export type DslActionListResponse = {
  items: DslAction[];
  total: number;
  page: number;
  page_size: number;
};

export type DslSearchHit = {
  action: DslAction;
  matched_language: string;
  matched_alias: string;
  // AI / hybrid için ekstra alanlar — lexical aramada null kalır
  score?: number | null;
  source?: "lexical" | "semantic" | "hybrid" | "llm_rerank" | null;
  reason?: string | null;
};

export type DslSearchMode =
  | "lexical"
  | "semantic"
  | "hybrid"
  | "lexical_fallback"
  | "hybrid_empty"
  | "empty";

export type DslSuggestMode = "auto" | "lexical" | "hybrid" | "semantic";

export type DslIndexInfo = {
  ready: boolean;
  rows: number;
  dim: number;
  model: string;
  built_at?: number | null;
  corpus_hash: string;
};

export type DslSearchResponse = {
  query: string;
  total: number;
  items: DslSearchHit[];
  mode?: DslSearchMode | null;
  index_info?: DslIndexInfo | null;
};

export type DslFeedbackVote = "up" | "down" | "ignored";

export type DslFeedbackRequest = {
  query: string;
  action_id: string;
  vote: DslFeedbackVote;
  search_mode?: "lexical" | "semantic" | "hybrid" | "llm_rerank";
  rank?: number;
  raw_score?: number;
};

export type DslFeedbackResponse = {
  id: string;
  recorded_at: string;
  bonus_applied: number;
};

export type DslIndexRebuildResponse = {
  status: string;
  rows: number;
  latency_ms?: number | null;
  error?: string | null;
};

// ── Editör / Proposal Types ───────────────────────────────────────────────

export type DslEditOperation = "create" | "update" | "delete" | "deprecate";
export type DslProposalStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "merged"
  | "error";

export type DslGitMode = "direct_commit" | "pr";

export type DslEditOptions = {
  require_review?: boolean;
  git_mode?: DslGitMode;
  commit_message?: string;
};

export type DslApplyResponse = {
  proposal_id: string;
  status: "pending" | "merged" | "error";
  mode: "direct_commit" | "pr" | "disabled" | "review";
  action_id: string;
  commit_sha?: string | null;
  branch?: string | null;
  pr_url?: string | null;
  file_paths: string[];
};

export type DslProposalDiff = {
  op: DslEditOperation;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  changed_fields: string[];
};

export type DslProposal = {
  id: string;
  action_id: string;
  proposer_kind: "human" | "ai";
  operation: DslEditOperation;
  status: DslProposalStatus;
  diff: DslProposalDiff;
  ai_reasoning?: string | null;
  base_commit_sha?: string | null;
  branch?: string | null;
  commit_sha?: string | null;
  pr_url?: string | null;
  error_message?: string | null;
  reviewer_note?: string | null;
  created_at: string;
  reviewed_at?: string | null;
};

export type DslProposalListResponse = {
  items: DslProposal[];
  total: number;
};

export type DslAuditEntry = {
  id: string;
  action_id: string;
  operation: DslEditOperation;
  commit_sha?: string | null;
  pr_url?: string | null;
  created_at: string;
  proposal_id?: string | null;
};

export type DslEditorConfig = {
  git_enabled: boolean;
  git_mode: DslGitMode;
  base_branch: string;
  provider: string;
  remote: string;
  strict_clean: boolean;
};

export type DslDeprecateRequest = {
  replacement: string;
  reason?: string;
  since?: string;
  options?: DslEditOptions;
};

export type DslAiAliasResponse = {
  accepted: string[];
  rejected: string[];
  proposals: string[];
  lang?: DslLang | null;
  action_id?: string | null;
  reason?: string | null;
};

export type DslStats = {
  total: number;
  unique_ids: number;
  by_top_category: Record<string, number>;
  by_full_category: Record<string, number>;
  by_implementation: Record<string, number>;
  by_source_file: Record<string, number>;
  by_step_type: Record<string, number>;
  top_tags: Array<{ tag: string; count: number }>;
  aliases: Record<string, number>;
  loaded_at?: string | null;
};

export type DslCategoryNode = {
  id: string;
  label: string;
  count: number;
  children: DslCategoryNode[];
};

export type DslReloadResponse = {
  status: string;
  total_before: number;
  total_after: number;
  loaded_at: string;
};

// ── DSL API ──────────────────────────────────────────────────────────────────

function buildQuery(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export const dslApi = {
  listActions(params: {
    category?: string;
    lang?: DslLang;
    tag?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<DslActionListResponse> {
    return apiFetch<DslActionListResponse>(
      `/api/v1/dsl/actions${buildQuery(params)}`,
    );
  },

  getAction(id: string): Promise<DslAction> {
    return apiFetch<DslAction>(
      `/api/v1/dsl/actions/${encodeURIComponent(id)}`,
    );
  },

  search(params: {
    q: string;
    lang?: DslLang;
    limit?: number;
  }): Promise<DslSearchResponse> {
    return apiFetch<DslSearchResponse>(
      `/api/v1/dsl/search${buildQuery(params)}`,
    );
  },

  stats(): Promise<DslStats> {
    return apiFetch<DslStats>(`/api/v1/dsl/stats`);
  },

  categories(): Promise<DslCategoryNode[]> {
    return apiFetch<DslCategoryNode[]>(`/api/v1/dsl/categories`);
  },

  suggest(body: {
    description: string;
    limit?: number;
    mode?: DslSuggestMode;
  }): Promise<DslSearchResponse> {
    return apiFetch<DslSearchResponse>(`/api/v1/dsl/suggest`, {
      method: "POST",
      json: body,
    });
  },

  searchSemantic(body: {
    q: string;
    lang?: DslLang;
    limit?: number;
    min_score?: number;
  }): Promise<DslSearchResponse> {
    return apiFetch<DslSearchResponse>(`/api/v1/dsl/search/semantic`, {
      method: "POST",
      json: body,
    });
  },

  feedback(body: DslFeedbackRequest): Promise<DslFeedbackResponse> {
    return apiFetch<DslFeedbackResponse>(`/api/v1/dsl/feedback`, {
      method: "POST",
      json: body,
    });
  },

  indexInfo(): Promise<DslIndexInfo> {
    return apiFetch<DslIndexInfo>(`/api/v1/dsl/index/info`);
  },

  rebuildIndex(force: boolean = false): Promise<DslIndexRebuildResponse> {
    const qs = force ? "?force=true" : "";
    return apiFetch<DslIndexRebuildResponse>(`/api/v1/dsl/index/rebuild${qs}`, {
      method: "POST",
    });
  },

  reload(): Promise<DslReloadResponse> {
    return apiFetch<DslReloadResponse>(`/api/v1/dsl/reload`, {
      method: "POST",
    });
  },

  // ── Editor / CRUD ─────────────────────────────────────────────────────

  editorConfig(): Promise<DslEditorConfig> {
    return apiFetch<DslEditorConfig>(`/api/v1/dsl/editor/config`);
  },

  createAction(body: {
    action: Partial<DslAction> & { id: string; category: string };
    options?: DslEditOptions;
  }): Promise<DslApplyResponse> {
    return apiFetch<DslApplyResponse>(`/api/v1/dsl/actions`, {
      method: "POST",
      json: body,
    });
  },

  updateAction(
    actionId: string,
    body: { action: Partial<DslAction>; options?: DslEditOptions },
  ): Promise<DslApplyResponse> {
    return apiFetch<DslApplyResponse>(
      `/api/v1/dsl/actions/${encodeURIComponent(actionId)}`,
      { method: "PATCH", json: body },
    );
  },

  deleteAction(
    actionId: string,
    options: DslEditOptions = {},
  ): Promise<DslApplyResponse> {
    return apiFetch<DslApplyResponse>(
      `/api/v1/dsl/actions/${encodeURIComponent(actionId)}`,
      { method: "DELETE", json: { options } },
    );
  },

  deprecateAction(
    actionId: string,
    body: DslDeprecateRequest,
  ): Promise<DslApplyResponse> {
    return apiFetch<DslApplyResponse>(
      `/api/v1/dsl/actions/${encodeURIComponent(actionId)}/deprecate`,
      { method: "POST", json: body },
    );
  },

  listProposals(params: {
    status?: DslProposalStatus;
    action_id?: string;
    limit?: number;
  } = {}): Promise<DslProposalListResponse> {
    return apiFetch<DslProposalListResponse>(
      `/api/v1/dsl/proposals${buildQuery(params as Record<string, unknown>)}`,
    );
  },

  getProposal(proposalId: string): Promise<DslProposal> {
    return apiFetch<DslProposal>(
      `/api/v1/dsl/proposals/${encodeURIComponent(proposalId)}`,
    );
  },

  approveProposal(
    proposalId: string,
    body: { note?: string; git_mode?: DslGitMode } = {},
  ): Promise<DslApplyResponse> {
    return apiFetch<DslApplyResponse>(
      `/api/v1/dsl/proposals/${encodeURIComponent(proposalId)}/approve`,
      { method: "POST", json: body },
    );
  },

  rejectProposal(
    proposalId: string,
    body: { note?: string } = {},
  ): Promise<DslProposal> {
    return apiFetch<DslProposal>(
      `/api/v1/dsl/proposals/${encodeURIComponent(proposalId)}/reject`,
      { method: "POST", json: body },
    );
  },

  listAudit(params: { action_id?: string; limit?: number } = {}): Promise<DslAuditEntry[]> {
    return apiFetch<DslAuditEntry[]>(
      `/api/v1/dsl/audit${buildQuery(params as Record<string, unknown>)}`,
    );
  },

  generateAiAliases(
    actionId: string,
    body: { lang: DslLang; count?: number },
  ): Promise<DslAiAliasResponse> {
    return apiFetch<DslAiAliasResponse>(
      `/api/v1/dsl/actions/${encodeURIComponent(actionId)}/ai-aliases`,
      { method: "POST", json: body },
    );
  },
};

// ── Automation Suite Types ───────────────────────────────────────────────────

export type Framework = "playwright" | "selenium" | "cypress";
export type RunStatus =
  | "queued"
  | "running"
  | "passed"
  | "failed"
  | "error"
  | "cancelled";

export type SuiteGenerateRequest = {
  manual_test_id: number;
  target_url?: string;
  framework?: Framework;
  auto_run?: boolean;
};

export type SuiteGenerateResponse = {
  ok: boolean;
  test_title: string;
  steps_count: number;
  gherkin: string;
  framework: Framework;
  generated_code?: string | null;
  feature_path?: string | null;
  locators?: Record<string, unknown> | null;
  model?: string | null;
  dsl_matched_actions: string[];
  dsl_unknown_steps: string[];
  run_id?: string | null;
};

export type SuiteRunRequest = {
  feature_path?: string;
  suite_id?: string;
  framework?: Framework;
  headless?: boolean;
  tags?: string[];
};

export type SuiteRunResponse = {
  run_id: string;
  status: RunStatus;
  message: string;
};

export type SuiteRunStatus = {
  run_id: string;
  status: RunStatus;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  feature_path?: string | null;
  framework?: Framework | null;
  passed?: number | null;
  failed?: number | null;
  error?: string | null;
  report_url?: string | null;
  logs_tail: string[];
};

export type SuiteCatalogSuggestItem = {
  action_id: string;
  category?: string | null;
  matched_language: string;
  matched_alias: string;
  description?: string | null;
};

export type SuiteCatalogSuggestResponse = {
  query: string;
  total: number;
  items: SuiteCatalogSuggestItem[];
};

export type SuiteHealthResponse = {
  status: "ok" | "degraded";
  backend: "ok";
  engine: Record<string, unknown>;
  dsl: Record<string, unknown>;
};

export type MobileScenarioRequest = {
  description: string;
  device?: {
    platform?: "ios" | "android";
    name?: string;
    os?: string;
    slug?: string;
  };
  app?: {
    package?: string;
    name?: string;
    upload_id?: string;
    filename?: string;
  } | null;
  max_steps?: number;
};

export type MobileScenarioResponse = {
  gherkin: string;
  matched_action_ids: string[];
  unknown_steps: string[];
  used_model?: string | null;
  device_label?: string | null;
  mobile_alias_count: number;
};

// ── Automation Suite API ─────────────────────────────────────────────────────

export const automationSuiteApi = {
  generate(body: SuiteGenerateRequest): Promise<SuiteGenerateResponse> {
    return apiFetch<SuiteGenerateResponse>(
      `/api/v1/automation-suite/generate`,
      { method: "POST", json: body },
    );
  },

  run(body: SuiteRunRequest): Promise<SuiteRunResponse> {
    return apiFetch<SuiteRunResponse>(`/api/v1/automation-suite/run`, {
      method: "POST",
      json: body,
    });
  },

  getRun(runId: string): Promise<SuiteRunStatus> {
    return apiFetch<SuiteRunStatus>(
      `/api/v1/automation-suite/runs/${encodeURIComponent(runId)}`,
    );
  },

  suggest(body: {
    description: string;
    limit?: number;
  }): Promise<SuiteCatalogSuggestResponse> {
    return apiFetch<SuiteCatalogSuggestResponse>(
      `/api/v1/automation-suite/catalog/suggest`,
      { method: "POST", json: body },
    );
  },

  health(): Promise<SuiteHealthResponse> {
    return apiFetch<SuiteHealthResponse>(`/api/v1/automation-suite/health`);
  },

  generateMobileScenario(
    body: MobileScenarioRequest,
  ): Promise<MobileScenarioResponse> {
    return apiFetch<MobileScenarioResponse>(
      `/api/v1/automation-suite/mobile/generate`,
      { method: "POST", json: body },
    );
  },
};
