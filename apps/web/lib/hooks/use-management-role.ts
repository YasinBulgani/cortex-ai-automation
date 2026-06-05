"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { useCurrentUser } from "@/lib/hooks/use-auth";

// ── Types ────────────────────────────────────────────────────────────────────

export type ProjectRole = "owner" | "admin" | "member" | "viewer";

interface ProjectMember {
  user_id: string;
  email: string;
  full_name?: string;
  role: ProjectRole;
}

// ── Query Keys ────────────────────────────────────────────────────────────────

export const projectMembersKey = (projectId: string) =>
  ["organizations", "projects", projectId, "members"] as const;

// ── Hook ─────────────────────────────────────────────────────────────────────

/**
 * Returns the current user's role in the given project.
 *
 * Calls GET /api/v1/organizations/projects/{project_id}/members
 * and matches the response against useCurrentUser().user.id.
 *
 * Falls back to "member" if:
 *   - projectId is not yet known
 *   - the request fails (e.g. network error, 404, 403)
 *   - the current user is not found in the members list
 */
export function useProjectRole(
  projectId: string | undefined,
): ProjectRole {
  const { user } = useCurrentUser();

  const query = useQuery({
    queryKey: projectMembersKey(projectId ?? ""),
    queryFn: () =>
      apiFetch<ProjectMember[]>(
        `/api/v1/organizations/projects/${projectId}/members`,
      ),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 dk — membership değişimi nadir
    retry: false,            // yetki hatalarında sonsuz döngü olmasın
  });

  if (!user || !query.data) return "member";

  const me = query.data.find((m) => m.user_id === user.id);
  return me?.role ?? "member";
}
