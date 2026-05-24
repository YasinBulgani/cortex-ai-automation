"use client";

import Link from "next/link";

const tabs = [
  { href: "management", label: "Dashboard" },
  { href: "management/repository", label: "Repository" },
  { href: "management/plans", label: "Plans" },
  { href: "management/runs", label: "Runs" },
  { href: "management/requirements", label: "Requirements" },
  { href: "management/defects", label: "Defects" },
  { href: "management/reports", label: "Reports" },
  { href: "management/import-export", label: "Import / Export" },
  { href: "management/settings", label: "Settings" },
];

export type ManagementShellProps = {
  projectId: string;
  title: string;
  description: string;
  active: string;
  children: React.ReactNode;
};

export function ManagementShell({ projectId, title, description, active, children }: ManagementShellProps) {
  return (
    <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <div className="mb-6 flex flex-col gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-teal-300">Neurex Management</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-white">{title}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{description}</p>
        </div>
        <nav className="flex gap-2 overflow-x-auto border-b border-slate-800 pb-3">
          {tabs.map((tab) => {
            const isActive = tab.href === active;
            return (
              <Link
                key={tab.href}
                href={`/p/${projectId}/${tab.href}`}
                className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? "bg-teal-500/15 text-teal-200 ring-1 ring-teal-400/30"
                    : "text-slate-400 hover:bg-slate-900 hover:text-white"
                }`}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>
      </div>
      {children}
    </main>
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
