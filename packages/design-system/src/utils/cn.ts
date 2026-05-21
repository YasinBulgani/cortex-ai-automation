/**
 * cn — Tailwind class merger.
 * Tüm UI komponentlerinin temel class composition helper'ı.
 *
 * Kullanım:
 *   cn("base", isActive && "active", className)
 */

type ClassValue = string | number | boolean | undefined | null | ClassValue[];

export function cn(...inputs: ClassValue[]): string {
  const out: string[] = [];
  for (const input of inputs) {
    if (!input) continue;
    if (typeof input === "string" || typeof input === "number") {
      out.push(String(input));
    } else if (Array.isArray(input)) {
      out.push(cn(...input));
    }
  }
  return out.join(" ");
}
