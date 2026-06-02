"use client";

/**
 * @deprecated — use `@/components/management/NotificationBell` instead.
 *
 * This file is kept as a thin re-export so existing imports (and tests) under
 * `@/app/(dashboard)/p/[projectId]/management/_components/NotificationBell`
 * continue to work. The implementation now lives at the shared global path.
 */

export { NotificationBell } from "@/components/management/NotificationBell";
export type { NotificationBellProps } from "@/components/management/NotificationBell";
