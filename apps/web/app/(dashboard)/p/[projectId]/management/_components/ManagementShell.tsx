"use client";

export type ManagementShellProps = {
  projectId?: string;
  /** @deprecated navigation is now handled by management/layout.tsx */
  title?: string;
  /** @deprecated navigation is now handled by management/layout.tsx */
  description?: string;
  /** @deprecated navigation is now handled by management/layout.tsx */
  active?: string;
  children: React.ReactNode;
};

export function ManagementShell({ children }: ManagementShellProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto">
      {children}
    </div>
  );
}

export function ManagementStat({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-fg-muted">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-normal text-fg">{value}</p>
      <p className="mt-1 text-xs text-fg-subtle">{note}</p>
    </section>
  );
}

export function ManagementPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold text-fg">{title}</h2>
      {children}
    </section>
  );
}
