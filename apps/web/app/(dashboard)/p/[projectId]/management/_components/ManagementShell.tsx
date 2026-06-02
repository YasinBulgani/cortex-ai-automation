"use client";

import Link from "next/link";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { NotificationBell } from "@/components/management/NotificationBell";

const tabs = [
  { href: "management", label: "Dashboard" },
  { href: "management/tester", label: "Görevlerim" },
  { href: "management/repository", label: "Repository" },
  { href: "management/regression", label: "Regression" },
  { href: "management/plans", label: "Plans" },
  { href: "management/runs", label: "Runs" },
  { href: "management/requirements", label: "Requirements" },
  { href: "management/defects", label: "Defects" },
  { href: "management/reports", label: "Reports" },
  { href: "management/design/bva", label: "BVA" },
  { href: "management/design/eq", label: "EQ Partition" },
  { href: "management/standup", label: "📱 Standup" },
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
