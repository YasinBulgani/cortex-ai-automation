"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";

// Management kök rotası — Dashboard'a yönlendirir.
export default function ManagementRoot() {
  const router = useRouter();
  const projectId = useRouteParam("projectId");

  useEffect(() => {
    if (projectId) router.replace(`/p/${projectId}/management/dashboard`);
  }, [projectId, router]);

  return (
    <div className="flex h-full items-center justify-center bg-bg">
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-teal-500" />
    </div>
  );
}
