"use client";
import { useCurrentUser } from "@/lib/useCurrentUser";

export function PermissionGate({
  permission,
  children,
  fallback = null,
}: {
  permission: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { hasPermission, loading } = useCurrentUser();
  if (loading) {
    return (
      <div
        className="h-9 max-w-xs animate-pulse rounded-md bg-slate-800 bg-slate-700"
        aria-busy="true"
        aria-label="İzin bilgisi yükleniyor"
        data-testid="permission-gate-loading"
      />
    );
  }
  if (!hasPermission(permission)) return <>{fallback}</>;
  return <>{children}</>;
}
