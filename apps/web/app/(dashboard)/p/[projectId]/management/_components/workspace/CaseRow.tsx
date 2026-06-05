"use client";

import Link from "next/link";
import { useDraggable } from "@dnd-kit/core";
import { cn } from "@/lib/utils";
import { type TestCase } from "@/lib/hooks/use-management";
import { R_DOT, P_DOT, TYPE_COLOR, AUTO_DOT } from "./shared";

// ─── Minimal Icons ────────────────────────────────────────────────────────────

function IcCheck() {
  return <svg className="h-2.5 w-2.5" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5" /></svg>;
}
function IcGrip() {
  return <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 16 16"><circle cx="5" cy="4" r="1.2" /><circle cx="11" cy="4" r="1.2" /><circle cx="5" cy="8" r="1.2" /><circle cx="11" cy="8" r="1.2" /><circle cx="5" cy="12" r="1.2" /><circle cx="11" cy="12" r="1.2" /></svg>;
}
function IcEdit() {
  return <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>;
}
function IcCopy() {
  return <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>;
}

// ─── CaseRow ──────────────────────────────────────────────────────────────────

export function CaseRow({
  tc, selected, onSelect, checked, onCheck, projectId, onClone, cloning,
}: {
  tc: TestCase; selected: boolean; onSelect: () => void;
  checked: boolean; onCheck: (e: React.MouseEvent) => void; projectId: string;
  onClone: () => void; cloning: boolean;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `case:${tc.id}`,
    data: { kind: "case", caseId: tc.id },
  });
  const rd  = tc.last_run_status ? (R_DOT[tc.last_run_status] ?? null) : null;
  const ad  = AUTO_DOT[tc.automation_status] ?? AUTO_DOT.not_automated;

  return (
    <tr
      ref={setNodeRef}
      onClick={onSelect}
      className={cn(
        "group border-b border-border/40 cursor-pointer select-none",
        isDragging  && "opacity-30",
        selected    && "bg-brand-soft",
        !selected   && "hover:bg-surface-overlay",
      )}
    >
      {/* Grip */}
      <td className="hidden w-5 pl-1.5 sm:table-cell">
        <button type="button" {...attributes} {...listeners}
          className="invisible group-hover:visible cursor-grab active:cursor-grabbing touch-none text-fg-subtle hover:text-fg p-0.5">
          <IcGrip />
        </button>
      </td>

      {/* Checkbox */}
      <td className="w-8 px-2">
        <button type="button" onClick={onCheck}
          className={cn("flex h-4 w-4 items-center justify-center rounded border transition-colors",
            checked ? "border-brand bg-brand text-brand-fg" : "border-border-strong bg-surface-raised hover:border-brand")}>
          {checked && <IcCheck />}
        </button>
      </td>

      {/* ID — TestRail-style colored badge */}
      <td className="w-24 px-3 py-2.5">
        <Link
          href={`/p/${projectId}/management/cases/${tc.id}`}
          onClick={e => e.stopPropagation()}
          className="inline-flex items-center rounded-md border border-brand/20 bg-brand-soft px-1.5 py-0.5 font-mono text-[10px] font-semibold text-brand transition-colors hover:border-brand/35 hover:bg-surface-accent"
        >
          {tc.case_key}
        </Link>
      </td>

      {/* Title */}
      <td className="px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", ad.dot)} title={ad.label} />
          <span className="text-[13px] text-fg line-clamp-1 transition-colors">
            {tc.title}
          </span>
        </div>
        {tc.tags && tc.tags.length > 0 && (
          <div className="mt-1 flex gap-1">
            {tc.tags.slice(0, 3).map(t => (
              <span key={t} className="rounded bg-surface-accent px-1.5 py-0.5 text-[10px] text-fg-subtle">{t}</span>
            ))}
          </div>
        )}
      </td>

      {/* Priority */}
      <td className="w-14 px-3 py-2.5">
        <div className="flex items-center gap-1.5">
          <span className={cn("h-1.5 w-1.5 rounded-full", P_DOT[tc.priority] ?? P_DOT.P3)} />
          <span className="text-[11px] text-fg-subtle font-mono">{tc.priority}</span>
        </div>
      </td>

      {/* Type */}
      <td className="hidden w-24 px-3 py-2.5 lg:table-cell">
        <span className={cn("rounded-md px-1.5 py-0.5 text-[10px]",
          TYPE_COLOR[tc.type] ?? "bg-slate-500/15 text-fg-subtle")}>
          {tc.type}
        </span>
      </td>

      {/* Last Run */}
      <td className="hidden w-24 px-3 py-2.5 md:table-cell">
        {rd ? (
          <div className="flex items-center gap-1.5">
            <span className={cn("h-1.5 w-1.5 rounded-full", rd.dot)} />
            <span className="text-[11px] text-fg-subtle">{rd.label}</span>
          </div>
        ) : (
          <span className="text-[11px] text-fg-subtle">—</span>
        )}
      </td>

      {/* Steps */}
      <td className="hidden w-12 px-3 py-2.5 text-[11px] text-fg-subtle tabular-nums xl:table-cell">
        {tc.steps?.length ?? 0}
      </td>

      {/* Row actions: Clone + Edit */}
      <td className="w-16 px-2">
        <div className="invisible group-hover:visible flex items-center gap-0.5">
          <button
            type="button"
            onClick={e => { e.stopPropagation(); onClone(); }}
            disabled={cloning}
            title="Klonla"
            className="inline-flex rounded p-1 text-fg-subtle hover:bg-surface-overlay hover:text-brand transition-all disabled:opacity-40"
          >
            <IcCopy />
          </button>
          <Link href={`/p/${projectId}/management/cases/${tc.id}`}
            onClick={e => e.stopPropagation()}
            className="inline-flex rounded p-1 text-fg-subtle hover:bg-surface-overlay hover:text-fg transition-all">
            <IcEdit />
          </Link>
        </div>
      </td>
    </tr>
  );
}

// ─── ArchivedCaseRow ──────────────────────────────────────────────────────────

export function ArchivedCaseRow({
  tc, checked, onCheck, projectId, onUnarchive, unarchiving,
}: {
  tc: TestCase; checked: boolean; onCheck: (e: React.MouseEvent) => void; projectId: string;
  onUnarchive: () => void; unarchiving: boolean;
}) {
  const ad = AUTO_DOT[tc.automation_status] ?? AUTO_DOT.not_automated;
  return (
    <tr className="group border-b border-border/30 select-none opacity-60 hover:opacity-90 hover:bg-surface-overlay transition-opacity">
      <td className="hidden w-5 sm:table-cell" />
      <td className="w-8 px-2">
        <button type="button" onClick={onCheck}
          className={cn("flex h-4 w-4 items-center justify-center rounded border transition-colors",
            checked ? "border-brand bg-brand text-brand-fg" : "border-border-strong bg-surface-raised hover:border-brand")}>
          {checked && <IcCheck />}
        </button>
      </td>
      <td className="w-24 px-3 py-2.5">
        <Link
          href={`/p/${projectId}/management/cases/${tc.id}`}
          onClick={e => e.stopPropagation()}
          className="inline-flex items-center rounded-md border border-border/40 bg-surface-overlay px-1.5 py-0.5 font-mono text-[10px] font-semibold text-fg-muted transition-colors hover:border-border"
        >
          {tc.case_key}
        </Link>
      </td>
      <td className="px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full opacity-50", ad.dot)} title={ad.label} />
          <span className="text-[13px] text-fg-muted line-clamp-1 line-through">{tc.title}</span>
        </div>
      </td>
      <td className="w-14 px-3 py-2.5"><span className="text-[11px] text-fg-subtle font-mono">{tc.priority}</span></td>
      <td className="hidden w-24 px-3 py-2.5 lg:table-cell" />
      <td className="hidden w-24 px-3 py-2.5 md:table-cell" />
      <td className="hidden w-12 px-3 py-2.5 xl:table-cell" />
      <td className="w-16 px-2">
        <button
          type="button"
          onClick={e => { e.stopPropagation(); onUnarchive(); }}
          disabled={unarchiving}
          title="Geri Yükle"
          className="invisible group-hover:visible rounded border border-emerald-500/25 px-2 py-0.5 text-[10px] font-medium text-emerald-400 hover:bg-emerald-500/10 disabled:opacity-40 transition-colors whitespace-nowrap"
        >
          {unarchiving ? "…" : "Geri Yükle"}
        </button>
      </td>
    </tr>
  );
}
