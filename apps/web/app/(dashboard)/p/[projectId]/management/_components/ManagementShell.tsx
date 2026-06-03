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
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold text-white">{value}</p>
      <p className="mt-1 text-xs text-slate-400">{note}</p>
    </section>
  );
}

export function ManagementPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-5">
      <h2 className="mb-4 text-sm font-semibold text-white">{title}</h2>
      {children}
    </section>
  );
}
