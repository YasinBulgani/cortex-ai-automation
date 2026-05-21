"use client";

import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

/* ── Method badge colors ─────────────────────────────────────────────── */
const METHOD_COLORS: Record<string, string> = {
  GET: "bg-emerald-500/20 text-emerald-400 border-emerald-500/40",
  POST: "bg-blue-500/20 text-blue-400 border-blue-500/40",
  PUT: "bg-amber-500/20 text-amber-400 border-amber-500/40",
  PATCH: "bg-orange-500/20 text-orange-400 border-orange-500/40",
  DELETE: "bg-red-500/20 text-red-400 border-red-500/40",
};

/* ── Shared node wrapper ─────────────────────────────────────────────── */
function NodeShell({
  selected,
  accentClass,
  children,
}: {
  selected: boolean;
  accentClass: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`rounded-xl border bg-slate-800/90 backdrop-blur-sm min-w-[200px] max-w-[260px] transition-shadow ${
        selected
          ? "border-blue-500/60 shadow-[0_0_16px_rgba(59,130,246,0.35)]"
          : `border-slate-700/60 ${accentClass}`
      }`}
    >
      {children}
    </div>
  );
}

/* ── Request Node ────────────────────────────────────────────────────── */
export interface RequestNodeData {
  label: string;
  method: string;
  path: string;
  headers?: Record<string, string>;
  body?: string;
  extractions?: Array<{ json_path: string; variable_name: string }>;
  assertions?: Array<{ type: string; expected: unknown; operator: string }>;
}

export const RequestNode = memo(function RequestNode({
  data,
  selected,
}: NodeProps<RequestNodeData>) {
  const method = data.method ?? "GET";
  const colorCls = METHOD_COLORS[method] ?? METHOD_COLORS.GET;

  return (
    <NodeShell selected={!!selected} accentClass="hover:border-slate-600">
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-blue-500 !border-2 !border-slate-900"
      />

      <div className="px-3 py-2.5 space-y-1.5">
        {/* Header row */}
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-bold tracking-wide ${colorCls}`}
          >
            {method}
          </span>
          <span className="text-xs font-semibold text-white truncate">
            {data.label || "Request"}
          </span>
        </div>

        {/* Path */}
        {data.path && (
          <div className="text-[11px] font-mono text-slate-400 truncate">
            {data.path}
          </div>
        )}

        {/* Extraction count badge */}
        {(data.extractions?.length ?? 0) > 0 && (
          <div className="flex gap-1">
            <span className="text-[10px] bg-purple-500/15 text-purple-400 border border-purple-500/30 rounded px-1.5 py-0.5">
              {data.extractions!.length} extract
            </span>
          </div>
        )}

        {/* Assertion count badge */}
        {(data.assertions?.length ?? 0) > 0 && (
          <div className="flex gap-1">
            <span className="text-[10px] bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 rounded px-1.5 py-0.5">
              {data.assertions!.length} assert
            </span>
          </div>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-emerald-500 !border-2 !border-slate-900"
      />
    </NodeShell>
  );
});

/* ── Extract Node ────────────────────────────────────────────────────── */
export interface ExtractNodeData {
  label: string;
  extractions: Array<{ json_path: string; variable_name: string }>;
}

export const ExtractNode = memo(function ExtractNode({
  data,
  selected,
}: NodeProps<ExtractNodeData>) {
  return (
    <NodeShell selected={!!selected} accentClass="hover:border-purple-500/30">
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-blue-500 !border-2 !border-slate-900"
      />

      <div className="px-3 py-2.5 space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-bold bg-purple-500/20 text-purple-400 border-purple-500/40">
            EXTRACT
          </span>
          <span className="text-xs font-semibold text-white truncate">
            {data.label || "Variable Extract"}
          </span>
        </div>

        {data.extractions?.map((ext, i) => (
          <div key={i} className="flex items-center gap-1 text-[10px]">
            <span className="font-mono text-slate-500 truncate max-w-[100px]">
              {ext.json_path}
            </span>
            <span className="text-slate-600">-&gt;</span>
            <span className="font-mono text-purple-400 truncate max-w-[80px]">
              {ext.variable_name}
            </span>
          </div>
        ))}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-emerald-500 !border-2 !border-slate-900"
      />
    </NodeShell>
  );
});

/* ── Assertion Node ──────────────────────────────────────────────────── */
export interface AssertionNodeData {
  label: string;
  assertions: Array<{ type: string; expected: unknown; operator: string }>;
}

export const AssertionNode = memo(function AssertionNode({
  data,
  selected,
}: NodeProps<AssertionNodeData>) {
  return (
    <NodeShell selected={!!selected} accentClass="hover:border-cyan-500/30">
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-blue-500 !border-2 !border-slate-900"
      />

      <div className="px-3 py-2.5 space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-bold bg-cyan-500/20 text-cyan-400 border-cyan-500/40">
            ASSERT
          </span>
          <span className="text-xs font-semibold text-white truncate">
            {data.label || "Assertions"}
          </span>
        </div>

        {data.assertions?.map((a, i) => (
          <div key={i} className="text-[10px] text-slate-400">
            <span className="text-cyan-400">{a.type}</span>{" "}
            <span className="text-slate-600">{a.operator}</span>{" "}
            <span className="text-slate-300">{String(a.expected)}</span>
          </div>
        ))}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-emerald-500 !border-2 !border-slate-900"
      />
    </NodeShell>
  );
});

/* ── Node type map for React Flow ────────────────────────────────────── */
export const chainNodeTypes = {
  request: RequestNode,
  extract: ExtractNode,
  assertion: AssertionNode,
};
