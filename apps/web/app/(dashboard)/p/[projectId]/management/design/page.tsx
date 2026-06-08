"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";

export default function DesignIndexPage() {
  const projectId = useRouteParam("projectId") ?? "";
  const router = useRouter();
  useEffect(() => {
    if (projectId) router.replace(`/p/${projectId}/management/design/bva`);
  }, [projectId, router]);
  return (
    <div className="flex items-center justify-center py-20">
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-teal-500" />
    </div>
  );
}
