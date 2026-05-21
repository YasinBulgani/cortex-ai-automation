"use client";

/**
 * Backward Compatibility — yeni hook'a yonlendir.
 * Yeni kod icin `import { useCurrentUser } from "@/lib/hooks"` kullanin.
 */
export { useCurrentUser } from "./hooks/use-auth";
export type { CurrentUser } from "./hooks/use-auth";
