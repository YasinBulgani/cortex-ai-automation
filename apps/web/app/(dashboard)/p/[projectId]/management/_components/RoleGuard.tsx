"use client";

import { useProjectRole } from "@/lib/hooks/use-management-role";

// ── Role hierarchy ────────────────────────────────────────────────────────────

type Role = "owner" | "admin" | "member" | "viewer";

const ROLE_RANK: Record<Role, number> = {
  owner:  4,
  admin:  3,
  member: 2,
  viewer: 1,
};

// ── Component ─────────────────────────────────────────────────────────────────

interface RoleGuardProps {
  minRole: Role;
  /** The tspm/route projectId (from useRouteParam("projectId")). */
  projectId?: string;
  children: React.ReactNode;
}

/**
 * Renders children only when the current user's role meets minRole.
 * Role is fetched from GET /api/v1/organizations/projects/{projectId}/members
 * via useProjectRole(). Falls back to "member" while loading or on error.
 * Hierarchy: owner > admin > member > viewer.
 */
export function RoleGuard({ minRole, projectId, children }: RoleGuardProps) {
  const role = useProjectRole(projectId);

  // Optimistic: while the request is in-flight the hook returns "member",
  // so children are rendered (no flash of hidden content).
  if (ROLE_RANK[role] < ROLE_RANK[minRole]) return null;

  return <>{children}</>;
}
