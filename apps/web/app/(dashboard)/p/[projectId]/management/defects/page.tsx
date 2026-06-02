"use client";

import { useState } from "react";

import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

const CLOSED_STATUSES = new Set(["closed", "done", "resolved", "fixed", "verified"]);
const BLOCKER_PATTERN = /blocker|critical|p0|sev0|sev1|release|prod|production|security|data loss/i;
const RETEST_STATUSES = new Set(["resolved", "fixed", "ready_for_retest", "ready for retest", "verify", "verified"]);
const AGING_TARGET_DAYS = 7;

function normalizedStatus(status: string) {
  return status.trim().toLowerCase();
}

function isClosed(defect: DefectLink) {
  return CLOSED_STATUSES.has(normalizedStatus(defect.status));
}

function isReleaseBlocker(defect: DefectLink) {
  return !isClosed(defect) && (
    BLOCKER_PATTERN.test(`${defect.title} ${defect.status} ${defect.external_key}`) ||
    ["blocker", "critical"].includes(defect.severity.toLowerCase()) ||
    ["P0", "P1"].includes(defect.priority)
  );
}

function daysSince(value?: string | null) {
  if (!value) return null;
  const time = new Date(value).getTime();
  if (Number.isNaN(time)) return null;
  return Math.max(0, Math.floor((Date.now() - time) / 86_400_000));
}

function ageTone(days: number | null, closed: boolean) {
  if (closed) return "bg-slate-800 text-slate-400 ring-slate-700";
  if (days === null) return "bg-slate-800 text-slate-300 ring-slate-700";
  if (days > 14) return "bg-rose-500/15 text-rose-200 ring-rose-400/30";
  if (days > AGING_TARGET_DAYS) return "bg-amber-500/15 text-amber-200 ring-amber-400/30";
  return "bg-emerald-500/15 text-emerald-200 ring-emerald-400/30";
}

function statusTone(status: string) {
  const normalized = normalizedStatus(status);
  if (CLOSED_STATUSES.has(normalized)) return "bg-emerald-500/15 text-emerald-200 ring-emerald-400/30";
  if (normalized.includes("block")) return "bg-rose-500/15 text-rose-200 ring-rose-400/30";
  if (normalized.includes("progress")) return "bg-sky-500/15 text-sky-200 ring-sky-400/30";
  return "bg-amber-500/15 text-amber-200 ring-amber-400/30";
}

function statusLabel(status: string) {
  return status.replace(/_/g, " ");
}

export default function ManagementDefectsPage({ params }: { params: { projectId: string } }) {
  const defects = useManagementDefects(params.projectId);
  const summary = useExecutionSummary(params.projectId);
  const updateDefect = useUpdateManagementDefect(params.projectId);
  const rows = defects.data ?? [];
  const [discussionDefectId, setDiscussionDefectId] = useState<string | null>(null);
  const activeDiscussionId = discussionDefectId ?? rows[0]?.id ?? null;
    </ManagementShell>
  );
}
