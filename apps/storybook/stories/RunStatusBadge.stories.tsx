/**
 * Stories for run-status and coverage-status badges used throughout
 * the Management domain.
 */

import type { Meta, StoryObj } from "@storybook/react";
import React from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

type RunStatus =
  | "passed"
  | "failed"
  | "blocked"
  | "not_run"
  | "skipped"
  | "running";

type CoverageStatus = "covered" | "partial" | "not_covered";

// ── RunStatusBadge ────────────────────────────────────────────────────────────

const RUN_STATUS_STYLES: Record<RunStatus, string> = {
  passed:  "bg-emerald-500/15 text-emerald-400",
  failed:  "bg-rose-500/15 text-rose-400",
  blocked: "bg-amber-500/15 text-amber-400",
  not_run: "bg-slate-700 text-slate-400",
  skipped: "bg-slate-600 text-slate-400",
  running: "bg-blue-500/15 text-blue-400",
};

const RUN_STATUS_LABELS: Record<RunStatus, string> = {
  passed:  "Passed",
  failed:  "Failed",
  blocked: "Blocked",
  not_run: "Not Run",
  skipped: "Skipped",
  running: "Running",
};

function RunStatusBadge({ status }: { status: RunStatus }) {
  return (
    <span
      className={`rounded px-2 py-0.5 text-xs font-medium ${RUN_STATUS_STYLES[status]}`}
    >
      {RUN_STATUS_LABELS[status]}
    </span>
  );
}

// ── CoverageStatusBadge ───────────────────────────────────────────────────────

const COVERAGE_STYLES: Record<CoverageStatus, string> = {
  covered:     "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400",
  partial:     "bg-amber-500/10 border border-amber-500/20 text-amber-400",
  not_covered: "bg-rose-500/10 border border-rose-500/20 text-rose-400",
};

const COVERAGE_LABELS: Record<CoverageStatus, string> = {
  covered:     "Covered",
  partial:     "Partial",
  not_covered: "Not Covered",
};

function CoverageStatusBadge({ status }: { status: CoverageStatus }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${COVERAGE_STYLES[status]}`}
    >
      {COVERAGE_LABELS[status]}
    </span>
  );
}

// ── RunStatusBadge stories ────────────────────────────────────────────────────

const meta: Meta<typeof RunStatusBadge> = {
  title: "Management / RunStatusBadge",
  component: RunStatusBadge,
  tags: ["autodocs"],
  decorators: [
    (Story) => (
      <div className="bg-slate-950 flex items-center gap-3 p-6">
        <Story />
      </div>
    ),
  ],
  argTypes: {
    status: {
      control: "radio",
      options: ["passed", "failed", "blocked", "not_run", "skipped", "running"],
    },
  },
};

export default meta;
type Story = StoryObj<typeof RunStatusBadge>;

export const Passed: Story = { args: { status: "passed" } };
export const Failed: Story = { args: { status: "failed" } };
export const Blocked: Story = { args: { status: "blocked" } };
export const NotRun: Story = { args: { status: "not_run" } };
export const Skipped: Story = { args: { status: "skipped" } };
export const Running: Story = { args: { status: "running" } };

export const AllStatuses: Story = {
  render: () => (
    <div className="bg-slate-950 p-6">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
          Run Statuses
        </p>
        <div className="flex flex-wrap gap-2">
          {(["passed", "failed", "blocked", "not_run", "skipped", "running"] as RunStatus[]).map(
            (s) => <RunStatusBadge key={s} status={s} />,
          )}
        </div>
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
          Coverage Statuses
        </p>
        <div className="flex flex-wrap gap-2">
          {(["covered", "partial", "not_covered"] as CoverageStatus[]).map(
            (s) => <CoverageStatusBadge key={s} status={s} />,
          )}
        </div>
      </div>
    </div>
  ),
};

export const InTable: Story = {
  render: () => (
    <div className="bg-slate-950 p-6">
      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-950 text-xs text-slate-500">
            <tr>
              <th className="px-3 py-2 text-left">Case</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Coverage</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {[
              { key: "TC-001", title: "User login flow", run: "passed", cov: "covered" },
              { key: "TC-002", title: "Payment checkout", run: "failed", cov: "partial" },
              { key: "TC-003", title: "Profile update", run: "not_run", cov: "not_covered" },
              { key: "TC-004", title: "2FA setup", run: "blocked", cov: "partial" },
            ].map((row) => (
              <tr key={row.key} className="hover:bg-slate-900/60">
                <td className="px-3 py-2.5">
                  <div>
                    <span className="font-mono text-xs text-slate-500">{row.key}</span>
                    <p className="text-slate-200">{row.title}</p>
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <RunStatusBadge status={row.run as RunStatus} />
                </td>
                <td className="px-3 py-2.5">
                  <CoverageStatusBadge status={row.cov as CoverageStatus} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  ),
};
