/**
 * Stories for ManagementStat and ManagementPanel.
 *
 * These are the reusable structural building blocks of the Management domain.
 * Copied inline to avoid Next.js imports in Storybook context.
 */

import type { Meta, StoryObj } from "@storybook/react";
import React from "react";

// ── Inline components (copy of ManagementShell primitives) ────────────────────

function ManagementStat({
  label,
  value,
  note,
  trend,
}: {
  label: string;
  value: string;
  note: string;
  trend?: "up" | "down" | "neutral";
}) {
  const trendColors = {
    up: "text-emerald-400",
    down: "text-rose-400",
    neutral: "text-slate-400",
  };
  const trendIcon = { up: "↑", down: "↓", neutral: "→" };

  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <div className="mt-2 flex items-end gap-2">
        <p className="text-2xl font-bold text-white">{value}</p>
        {trend && (
          <span className={`mb-0.5 text-sm font-medium ${trendColors[trend]}`}>
            {trendIcon[trend]}
          </span>
        )}
      </div>
      <p className="mt-1 text-xs text-slate-400">{note}</p>
    </section>
  );
}

function ManagementPanel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-5">
      <h2 className="mb-4 text-sm font-semibold text-white">{title}</h2>
      {children}
    </section>
  );
}

// ── ManagementStat meta ───────────────────────────────────────────────────────

const statMeta: Meta<typeof ManagementStat> = {
  title: "Management / ManagementStat",
  component: ManagementStat,
  tags: ["autodocs"],
  decorators: [
    (Story) => (
      <div className="bg-slate-950 p-6 min-h-32">
        <Story />
      </div>
    ),
  ],
  argTypes: {
    trend: {
      control: "radio",
      options: ["up", "down", "neutral", undefined],
    },
  },
};

export default statMeta;
type StatStory = StoryObj<typeof ManagementStat>;

export const Default: StatStory = {
  args: {
    label: "Total Cases",
    value: "142",
    note: "active test cases",
  },
};

export const WithTrendUp: StatStory = {
  args: {
    label: "Pass Rate",
    value: "87.3%",
    note: "vs 81.2% last sprint",
    trend: "up",
  },
};

export const WithTrendDown: StatStory = {
  args: {
    label: "Blocked",
    value: "5",
    note: "up from 2 last run",
    trend: "down",
  },
};

export const Loading: StatStory = {
  args: {
    label: "Requirements",
    value: "…",
    note: "loading",
  },
};

export const DashboardGrid: StatStory = {
  render: () => (
    <div className="bg-slate-950 p-6">
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat label="Total Cases" value="142" note="active test cases" />
        <ManagementStat
          label="Pass Rate"
          value="87.3%"
          note="vs 81.2% last sprint"
          trend="up"
        />
        <ManagementStat
          label="Blocked"
          value="5"
          note="awaiting fix"
          trend="down"
        />
        <ManagementStat
          label="Stale"
          value="3"
          note="source updated after last run"
          trend="neutral"
        />
      </div>
    </div>
  ),
};

export const PanelExample: StatStory = {
  render: () => (
    <div className="bg-slate-950 p-6 space-y-4">
      <ManagementPanel title="Release Readiness">
        <div className="space-y-2 text-sm text-slate-400">
          <div className="flex items-center justify-between rounded bg-emerald-500/10 px-3 py-2">
            <span>Passed</span>
            <span className="font-semibold text-emerald-400">124 / 142</span>
          </div>
          <div className="flex items-center justify-between rounded bg-rose-500/10 px-3 py-2">
            <span>Failed</span>
            <span className="font-semibold text-rose-400">8 / 142</span>
          </div>
          <div className="flex items-center justify-between rounded bg-amber-500/10 px-3 py-2">
            <span>Blocked</span>
            <span className="font-semibold text-amber-400">5 / 142</span>
          </div>
        </div>
      </ManagementPanel>
    </div>
  ),
};
