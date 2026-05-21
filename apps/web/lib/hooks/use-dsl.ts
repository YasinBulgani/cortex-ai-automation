"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import {
  dslApi,
  type DslAction,
  type DslActionListResponse,
  type DslAiAliasResponse,
  type DslApplyResponse,
  type DslDeprecateRequest,
  type DslEditOptions,
  type DslEditorConfig,
  type DslFeedbackRequest,
  type DslFeedbackResponse,
  type DslGitMode,
  type DslImplementation,
  type DslIndexInfo,
  type DslLang,
  type DslParameter,
  type DslProposal,
  type DslProposalStatus,
  type DslSearchHit,
  type DslSearchResponse,
  type DslStats,
  type DslSuggestMode,
} from "@/lib/dsl-api";

// Tipleri dsl-api'den yeniden export et — eski import'ları bozmadan tek kaynak
// (single source of truth) sağla.
export type {
  DslAction,
  DslActionListResponse,
  DslApplyResponse,
  DslEditOptions,
  DslEditorConfig,
  DslGitMode,
  DslImplementation,
  DslIndexInfo,
  DslParameter,
  DslProposal,
  DslProposalStatus,
  DslSearchHit,
  DslSearchResponse,
  DslStats,
};

// ── Use-dsl'e özel küçük tip ─────────────────────────────────────────
export interface DslCategory {
  id: string;
  count: number;
  top_level: string;
}

export interface DslListFilters {
  category?: string;
  lang?: string;
  tag?: string;
  step_type?: "given" | "when" | "then";
  page?: number;
  page_size?: number;
}

// ── Query Keys ────────────────────────────────────────────────────────
export const dslKeys = {
  all: ["dsl"] as const,
  stats: () => [...dslKeys.all, "stats"] as const,
  categories: () => [...dslKeys.all, "categories"] as const,
  actions: () => [...dslKeys.all, "actions"] as const,
  actionList: (filters: DslListFilters) => [...dslKeys.actions(), "list", filters] as const,
  actionDetail: (id: string) => [...dslKeys.actions(), "detail", id] as const,
  search: (q: string, lang?: string) => [...dslKeys.all, "search", q, lang ?? "all"] as const,
  suggest: (q: string, mode: DslSuggestMode) =>
    [...dslKeys.all, "suggest", mode, q] as const,
  indexInfo: () => [...dslKeys.all, "index-info"] as const,
  editorConfig: () => [...dslKeys.all, "editor-config"] as const,
  proposals: (
    filters: { status?: DslProposalStatus; action_id?: string; limit?: number } = {},
  ) => [...dslKeys.all, "proposals", filters] as const,
  proposalDetail: (id: string) =>
    [...dslKeys.all, "proposals", "detail", id] as const,
  audit: (action_id?: string) =>
    [...dslKeys.all, "audit", action_id ?? "all"] as const,
};

// ── Hooks ─────────────────────────────────────────────────────────────

/** Katalog genel istatistikleri (toplam, kategori dağılımı, dil vb.). */
export function useDslStats() {
  return useQuery({
    queryKey: dslKeys.stats(),
    queryFn: () => apiFetch<DslStats>("/api/v1/dsl/stats"),
    staleTime: 5 * 60 * 1000,
  });
}

/** Kategoriler ve cümlecik sayıları (UI sol panel için). */
export function useDslCategories() {
  return useQuery({
    queryKey: dslKeys.categories(),
    queryFn: () => apiFetch<DslCategory[]>("/api/v1/dsl/categories"),
    staleTime: 5 * 60 * 1000,
  });
}

/** Kataloğu filtreli ve sayfalanmış şekilde getirir. */
export function useDslActions(filters: DslListFilters = {}) {
  const { category, lang, tag, step_type, page = 1, page_size = 50 } = filters;

  return useQuery({
    queryKey: dslKeys.actionList({ category, lang, tag, step_type, page, page_size }),
    queryFn: () => {
      const qs = new URLSearchParams();
      if (category) qs.set("category", category);
      if (lang) qs.set("lang", lang);
      if (tag) qs.set("tag", tag);
      if (step_type) qs.set("step_type", step_type);
      qs.set("page", String(page));
      qs.set("page_size", String(page_size));
      return apiFetch<DslActionListResponse>(`/api/v1/dsl/actions?${qs}`);
    },
    staleTime: 60 * 1000,
  });
}

/** Tek bir cümleciğin tam detayı. */
export function useDslAction(actionId: string | undefined) {
  return useQuery({
    queryKey: dslKeys.actionDetail(actionId ?? ""),
    queryFn: () => apiFetch<DslAction>(`/api/v1/dsl/actions/${actionId}`),
    enabled: !!actionId,
    staleTime: 5 * 60 * 1000,
  });
}

/** Katalogda alias ve description üzerinde arama yapar. */
export function useDslSearch(query: string, lang?: string, limit = 50) {
  const trimmed = query.trim();
  return useQuery({
    queryKey: dslKeys.search(trimmed, lang),
    queryFn: () => {
      const qs = new URLSearchParams({ q: trimmed, limit: String(limit) });
      if (lang) qs.set("lang", lang);
      return apiFetch<DslSearchResponse>(`/api/v1/dsl/search?${qs}`);
    },
    enabled: trimmed.length > 0,
    staleTime: 30 * 1000,
  });
}

// ── AI: NL Suggest (auto|lexical|hybrid|semantic) ───────────────────────

/**
 * Doğal dil → DSL cümlecik önerisi.
 * `mode`:
 *  - `auto` (varsayılan): index varsa hybrid, yoksa lexical
 *  - `lexical`: sadece kelime bazlı (AI gereksiz)
 *  - `hybrid`: lexical + embedding birleşik
 *  - `semantic`: sadece embedding
 */
export function useDslSuggest(
  description: string,
  {
    mode = "auto",
    limit = 10,
    enabled = true,
    minLength = 3,
  }: {
    mode?: DslSuggestMode;
    limit?: number;
    enabled?: boolean;
    minLength?: number;
  } = {},
) {
  const q = description.trim();
  return useQuery({
    queryKey: dslKeys.suggest(q, mode),
    queryFn: () => dslApi.suggest({ description: q, limit, mode }),
    enabled: enabled && q.length >= minLength,
    staleTime: 30 * 1000,
  });
}

/** Embedding indeksinin durumu (ready, rows, dim, model, built_at). */
export function useDslIndexInfo(enabled = true) {
  return useQuery({
    queryKey: dslKeys.indexInfo(),
    queryFn: () => dslApi.indexInfo(),
    enabled,
    staleTime: 60 * 1000,
    refetchInterval: 2 * 60 * 1000,
  });
}

/**
 * Arama sonuçu için kullanıcı geri bildirimi (👍 / 👎).
 * Başarılı olduğunda aktif suggest query'sini yeniden çeker.
 */
export function useDslFeedback() {
  const qc = useQueryClient();
  return useMutation<DslFeedbackResponse, Error, DslFeedbackRequest>({
    mutationFn: (body) => dslApi.feedback(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: dslKeys.all });
    },
  });
}

// ── Editor ────────────────────────────────────────────────────────────

/** Git mode, provider, base branch gibi editör yapılandırması. */
export function useDslEditorConfig() {
  return useQuery({
    queryKey: dslKeys.editorConfig(),
    queryFn: () => dslApi.editorConfig(),
    staleTime: 5 * 60 * 1000,
  });
}

function useDslCrudInvalidate() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: dslKeys.all });
  };
}

export function useDslCreateAction() {
  const invalidate = useDslCrudInvalidate();
  return useMutation<
    DslApplyResponse,
    Error,
    { action: Partial<DslAction> & { id: string; category: string }; options?: DslEditOptions }
  >({
    mutationFn: (body) => dslApi.createAction(body),
    onSuccess: invalidate,
  });
}

export function useDslUpdateAction() {
  const invalidate = useDslCrudInvalidate();
  return useMutation<
    DslApplyResponse,
    Error,
    { actionId: string; action: Partial<DslAction>; options?: DslEditOptions }
  >({
    mutationFn: ({ actionId, action, options }) =>
      dslApi.updateAction(actionId, { action, options }),
    onSuccess: invalidate,
  });
}

export function useDslDeleteAction() {
  const invalidate = useDslCrudInvalidate();
  return useMutation<DslApplyResponse, Error, { actionId: string; options?: DslEditOptions }>({
    mutationFn: ({ actionId, options }) => dslApi.deleteAction(actionId, options),
    onSuccess: invalidate,
  });
}

export function useDslDeprecateAction() {
  const invalidate = useDslCrudInvalidate();
  return useMutation<
    DslApplyResponse,
    Error,
    { actionId: string; body: DslDeprecateRequest }
  >({
    mutationFn: ({ actionId, body }) => dslApi.deprecateAction(actionId, body),
    onSuccess: invalidate,
  });
}

// ── Proposals ─────────────────────────────────────────────────────────

export function useDslProposals(
  filters: { status?: DslProposalStatus; action_id?: string; limit?: number } = {},
) {
  return useQuery({
    queryKey: dslKeys.proposals(filters),
    queryFn: () => dslApi.listProposals(filters),
    staleTime: 30 * 1000,
    refetchOnWindowFocus: false,
  });
}

export function useDslProposal(proposalId: string | undefined) {
  return useQuery({
    queryKey: dslKeys.proposalDetail(proposalId ?? ""),
    queryFn: () => dslApi.getProposal(proposalId ?? ""),
    enabled: !!proposalId,
    staleTime: 10 * 1000,
  });
}

export function useDslApproveProposal() {
  const invalidate = useDslCrudInvalidate();
  return useMutation<
    DslApplyResponse,
    Error,
    { proposalId: string; body?: { note?: string; git_mode?: DslGitMode } }
  >({
    mutationFn: ({ proposalId, body }) => dslApi.approveProposal(proposalId, body ?? {}),
    onSuccess: invalidate,
  });
}

export function useDslRejectProposal() {
  const invalidate = useDslCrudInvalidate();
  return useMutation<DslProposal, Error, { proposalId: string; body?: { note?: string } }>({
    mutationFn: ({ proposalId, body }) => dslApi.rejectProposal(proposalId, body ?? {}),
    onSuccess: invalidate,
  });
}

// ── AI Alias Generator ────────────────────────────────────────────────

export function useDslGenerateAiAliases() {
  const invalidate = useDslCrudInvalidate();
  return useMutation<
    DslAiAliasResponse,
    Error,
    { actionId: string; lang: DslLang; count?: number }
  >({
    mutationFn: ({ actionId, lang, count }) =>
      dslApi.generateAiAliases(actionId, { lang, count }),
    onSuccess: invalidate,
  });
}

// ── Audit ─────────────────────────────────────────────────────────────

export function useDslAudit(action_id?: string, limit = 100) {
  return useQuery({
    queryKey: dslKeys.audit(action_id),
    queryFn: () => dslApi.listAudit({ action_id, limit }),
    staleTime: 60 * 1000,
  });
}
