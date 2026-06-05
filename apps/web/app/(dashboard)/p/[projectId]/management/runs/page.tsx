"use client";

import { useRouteParam } from "@/lib/use-route-param";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { WorkspaceShell } from "../_components/workspace/WorkspaceShell";
import { PageErrorBoundary } from "../_components/PageErrorBoundary";

export default function RunsPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  return (
    <PageErrorBoundary>
      <WorkspaceShell projectId={projectId ?? ""} mpid={mpid || ""} initialMode="runs" />
    </PageErrorBoundary>
  );
}
