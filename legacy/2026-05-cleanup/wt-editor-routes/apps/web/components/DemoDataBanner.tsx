import type { ReactNode } from "react";

/**
 * Örnek / mock veri kullanan ekranlarda kullanıcıyı bilgilendirir.
 */
export function DemoDataBanner({ children }: { children: ReactNode }) {
  return (
    <div
      role="status"
      className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-100"
      data-testid="demo-data-banner"
    >
      {children}
    </div>
  );
}
