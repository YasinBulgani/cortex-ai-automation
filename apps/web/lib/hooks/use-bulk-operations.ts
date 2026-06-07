'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api-client'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface BulkUpdateCasesPayload {
  case_ids: string[]
  status?: string
  priority?: string
  tags_add?: string[]
}

export interface BulkUpdateResult {
  updated: number
  failed: number
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

/**
 * POST /api/v1/test-management/projects/{id}/cases/bulk-update
 *
 * Seçili case'lerin status, priority veya tag'larını toplu günceller.
 * Başarı sonrası cases cache'ini geçersiz kılar.
 */
export function useBulkUpdateCases(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: BulkUpdateCasesPayload) =>
      apiFetch<BulkUpdateResult>(
        `/api/v1/test-management/projects/${projectId}/cases/bulk-update`,
        { method: 'POST', body: JSON.stringify(payload) },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['management', 'cases', projectId] })
    },
  })
}

/**
 * POST /api/v1/test-management/projects/{id}/cases/bulk-delete
 *
 * Seçili case'leri toplu siler.
 * Başarı sonrası cases cache'ini geçersiz kılar.
 */
export function useBulkDeleteCases(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (case_ids: string[]) =>
      apiFetch<{ deleted: number }>(
        `/api/v1/test-management/projects/${projectId}/cases/bulk-delete`,
        { method: 'POST', body: JSON.stringify({ case_ids }) },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['management', 'cases', projectId] })
    },
  })
}
