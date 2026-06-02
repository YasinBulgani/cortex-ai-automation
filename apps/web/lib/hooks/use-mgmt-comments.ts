"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

export type CommentEntityType = "case" | "defect" | "plan" | "run" | "requirement";

export interface MgmtComment {
  id: string;
  tenant_id: string;
  project_id?: string | null;
  entity_type: CommentEntityType;
  entity_id: string;
  author_id?: string | null;
  parent_id?: string | null;
  body_md: string;
  mentions: string[];
  reactions: Record<string, string[]>;
  edited_at?: string | null;
  deleted_at?: string | null;
  created_at: string;
}

export interface CreateCommentInput {
  entity_type: CommentEntityType;
  entity_id: string;
  body_md: string;
  parent_id?: string | null;
  mentions?: string[];
  project_id?: string | null;
}

export interface UpdateCommentInput {
  body_md: string;
  mentions?: string[];
}

export interface ReactCommentInput {
  emoji: string;
  add?: boolean;
}

export const commentKeys = {
  all: ["mgmt-comments"] as const,
  list: (entityType: CommentEntityType | undefined, entityId: string | undefined) =>
    [...commentKeys.all, entityType, entityId] as const,
};

const COMMENTS_BASE = "/api/v1/test-management/comments";

export function useComments(
  entityType: CommentEntityType | undefined,
  entityId: string | undefined,
  options: { includeDeleted?: boolean } = {},
) {
  const includeDeleted = options.includeDeleted ?? false;
  return useQuery({
    queryKey: [...commentKeys.list(entityType, entityId), includeDeleted] as const,
    queryFn: () => {
      const params = new URLSearchParams({
        entity_type: entityType ?? "",
        entity_id: entityId ?? "",
      });
      if (includeDeleted) params.set("include_deleted", "true");
      return apiFetch<MgmtComment[]>(`${COMMENTS_BASE}?${params.toString()}`);
    },
    enabled: !!entityType && !!entityId,
    staleTime: 10_000,
  });
}

export function useCreateComment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateCommentInput) =>
      apiFetch<MgmtComment>(COMMENTS_BASE, { method: "POST", json: payload }),
    onSuccess: (created) => {
      void qc.invalidateQueries({
        queryKey: commentKeys.list(created.entity_type, created.entity_id),
      });
    },
  });
}

export function useUpdateComment(entityType: CommentEntityType, entityId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ commentId, ...payload }: UpdateCommentInput & { commentId: string }) =>
      apiFetch<MgmtComment>(`${COMMENTS_BASE}/${commentId}`, {
        method: "PATCH",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: commentKeys.list(entityType, entityId) });
    },
  });
}

export function useDeleteComment(entityType: CommentEntityType, entityId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (commentId: string) =>
      apiFetch<MgmtComment>(`${COMMENTS_BASE}/${commentId}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: commentKeys.list(entityType, entityId) });
    },
  });
}

export function useReactToComment(entityType: CommentEntityType, entityId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ commentId, ...payload }: ReactCommentInput & { commentId: string }) =>
      apiFetch<MgmtComment>(`${COMMENTS_BASE}/${commentId}/react`, {
        method: "POST",
        json: { add: true, ...payload },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: commentKeys.list(entityType, entityId) });
    },
  });
}

/**
 * Group a flat list of comments into a parent → children tree, preserving
 * chronological order on each level.
 */
export interface CommentNode extends MgmtComment {
  children: CommentNode[];
}

export function buildCommentTree(comments: MgmtComment[]): CommentNode[] {
  const byId = new Map<string, CommentNode>();
  const roots: CommentNode[] = [];
  for (const c of comments) {
    byId.set(c.id, { ...c, children: [] });
  }
  for (const node of byId.values()) {
    if (node.parent_id && byId.has(node.parent_id)) {
      byId.get(node.parent_id)!.children.push(node);
    } else {
      roots.push(node);
    }
  }
  return roots;
}

// ── M-50 AI Thread Summary ───────────────────────────────────────────────────

export interface ThreadSummaryOut {
  entity_type: CommentEntityType;
  entity_id: string;
  generated_at: string;
  tldr: string;
  decisions: string[];
  openQuestions: string[];
  comment_count: number;
  source: "llm" | "fallback";
}

/**
 * Fetch an AI-generated summary of a comment thread.
 *
 * Powered by the `mgmt.comm.thread_summarize` prompt template; the backend
 * falls back to a heuristic summary when the LLM gateway is unavailable
 * (signalled via `source: "fallback"`).
 *
 * Lazy by default — pass `enabled=true` only when the summary panel is open
 * so we don't burn LLM tokens on every page load.
 */
export function useThreadSummary(
  entityType: CommentEntityType | undefined,
  entityId: string | undefined,
  enabled: boolean = false,
) {
  return useQuery({
    queryKey: [...commentKeys.list(entityType, entityId), "summary"] as const,
    queryFn: () =>
      apiFetch<ThreadSummaryOut>(`${COMMENTS_BASE}/summarize`, {
        method: "POST",
        json: { entity_type: entityType, entity_id: entityId },
      }),
    enabled: enabled && !!entityType && !!entityId,
    staleTime: 60_000,
  });
}
