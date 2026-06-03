"use client";

import { useRouteParam } from "@/lib/use-route-param";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { WorkspaceShell } from "../_components/workspace/WorkspaceShell";

export default function RunsPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  return <WorkspaceShell projectId={projectId ?? ""} mpid={mpid || ""} initialMode="runs" />;
}
