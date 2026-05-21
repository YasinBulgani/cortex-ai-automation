"use client";

import { cn } from "../utils/cn";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
  variant?: "default" | "compact" | "hero";
}

/**
 * EmptyState — sayfada veri yokken gösterilen panel.
 *
 * Variants:
 *   - default: dikey, orta hizalı, açıklayıcı (önerilen)
 *   - compact: yatay, minimal (tabloda kullanılabilir)
 *   - hero:    büyük, illüstrasyon vurgulu (landing'lerde)
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
  variant = "default",
}: EmptyStateProps) {
  if (variant === "compact") {
    return (
      <div className={cn("flex items-center gap-3 py-6 px-4 text-sm text-fg-muted", className)}>
        {icon && <span className="shrink-0 text-fg-subtle">{icon}</span>}
        <span className="min-w-0 flex-1">
          <span className="font-medium text-fg-muted">{title}</span>
          {description && <span className="ml-2 text-fg-subtle">— {description}</span>}
        </span>
        {action && <span className="shrink-0">{action}</span>}
      </div>
    );
  }

  if (variant === "hero") {
    return (
      <div className={cn("flex flex-col items-center justify-center py-20 px-6 text-center", className)}>
        {icon && (
          <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-brand-soft text-brand-primary text-3xl">
            {icon}
          </div>
        )}
        <h2 className="text-xl font-bold text-fg tracking-tight">{title}</h2>
        {description && (
          <p className="mt-2 max-w-md text-sm text-fg-muted leading-relaxed">{description}</p>
        )}
        {action && <div className="mt-6">{action}</div>}
      </div>
    );
  }

  // default
  return (
    <div className={cn("flex flex-col items-center justify-center py-16 px-6 text-center", className)}>
      {icon && (
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-surface-overlay text-fg-subtle">
          {icon}
        </div>
      )}
      <h3 className="text-sm font-semibold text-fg">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-xs text-fg-muted">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
