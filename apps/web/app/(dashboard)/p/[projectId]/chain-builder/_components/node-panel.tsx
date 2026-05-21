"use client";

import React, { useCallback } from "react";
import type { Node } from "reactflow";
import type { RequestNodeData } from "./nodes";

/* ── Method badge colors (same palette as nodes) ─────────────────────── */
const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"] as const;
const EMPTY_EXTRACTIONS: NonNullable<RequestNodeData["extractions"]> = [];
const EMPTY_ASSERTIONS: NonNullable<RequestNodeData["assertions"]> = [];

interface NodePanelProps {
  node: Node<RequestNodeData> | null;
  onUpdate: (id: string, data: Partial<RequestNodeData>) => void;
  onClose: () => void;
}

/* ── JSON Editor Field ───────────────────────────────────────────────── */
function JsonField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1">
      <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
        {label}
      </label>
      <textarea
        aria-label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={4}
        className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs text-slate-300 font-mono placeholder-slate-600 focus:outline-none focus:border-blue-500/60 resize-y"
        spellCheck={false}
      />
    </div>
  );
}

/* ── Extraction Row ──────────────────────────────────────────────────── */
function ExtractionRow({
  ext,
  idx,
  onChange,
  onRemove,
}: {
  ext: { json_path: string; variable_name: string };
  idx: number;
  onChange: (idx: number, field: "json_path" | "variable_name", val: string) => void;
  onRemove: (idx: number) => void;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <input
        value={ext.json_path}
        onChange={(e) => onChange(idx, "json_path", e.target.value)}
        placeholder="$.data.token"
        className="flex-1 rounded border border-slate-700 bg-slate-800/80 px-2 py-1 text-[11px] text-slate-300 font-mono placeholder-slate-600 focus:outline-none focus:border-blue-500/60"
      />
      <span className="text-slate-600 text-xs">-&gt;</span>
      <input
        value={ext.variable_name}
        onChange={(e) => onChange(idx, "variable_name", e.target.value)}
        placeholder="auth_token"
        className="flex-1 rounded border border-slate-700 bg-slate-800/80 px-2 py-1 text-[11px] text-purple-400 font-mono placeholder-slate-600 focus:outline-none focus:border-blue-500/60"
      />
      <button
        onClick={() => onRemove(idx)}
        className="text-slate-600 hover:text-red-400 text-xs px-1 transition-colors"
        title="Remove"
      >
        x
      </button>
    </div>
  );
}

/* ── Assertion Row ───────────────────────────────────────────────────── */
function AssertionRow({
  assertion,
  idx,
  onChange,
  onRemove,
}: {
  assertion: { type: string; expected: unknown; operator: string };
  idx: number;
  onChange: (idx: number, field: string, val: string) => void;
  onRemove: (idx: number) => void;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <select
        aria-label="Assertion type"
        value={assertion.type}
        onChange={(e) => onChange(idx, "type", e.target.value)}
        className="rounded border border-slate-700 bg-slate-800/80 px-1.5 py-1 text-[11px] text-slate-300 focus:outline-none focus:border-blue-500/60"
      >
        <option value="status_code">status_code</option>
        <option value="json_path">json_path</option>
        <option value="header">header</option>
        <option value="response_time">response_time</option>
        <option value="exists">exists</option>
      </select>
      <select
        aria-label="Assertion operator"
        value={assertion.operator}
        onChange={(e) => onChange(idx, "operator", e.target.value)}
        className="rounded border border-slate-700 bg-slate-800/80 px-1.5 py-1 text-[11px] text-slate-300 focus:outline-none focus:border-blue-500/60"
      >
        <option value="equals">equals</option>
        <option value="not_equals">not_equals</option>
        <option value="contains">contains</option>
        <option value="gt">gt</option>
        <option value="lt">lt</option>
        <option value="exists">exists</option>
      </select>
      <input
        value={String(assertion.expected ?? "")}
        onChange={(e) => onChange(idx, "expected", e.target.value)}
        placeholder="expected"
        className="flex-1 rounded border border-slate-700 bg-slate-800/80 px-2 py-1 text-[11px] text-slate-300 font-mono placeholder-slate-600 focus:outline-none focus:border-blue-500/60"
      />
      <button
        onClick={() => onRemove(idx)}
        className="text-slate-600 hover:text-red-400 text-xs px-1 transition-colors"
        title="Remove"
      >
        x
      </button>
    </div>
  );
}

/* ── Main Panel ──────────────────────────────────────────────────────── */
export function NodePanel({ node, onUpdate, onClose }: NodePanelProps) {
  const d = node?.data;
  const nodeId = node?.id ?? "";

  const update = useCallback(
    (patch: Partial<RequestNodeData>) => onUpdate(nodeId, patch),
    [nodeId, onUpdate],
  );

  /* -- Extraction helpers -- */
  const extractions = d?.extractions ?? EMPTY_EXTRACTIONS;
  const handleExtChange = useCallback(
    (idx: number, field: "json_path" | "variable_name", val: string) => {
      const next = [...extractions];
      next[idx] = { ...next[idx], [field]: val };
      update({ extractions: next });
    },
    [extractions, update],
  );

  const addExtraction = useCallback(() => {
    update({ extractions: [...extractions, { json_path: "", variable_name: "" }] });
  }, [extractions, update]);

  const removeExtraction = useCallback(
    (idx: number) => {
      const next = [...extractions];
      next.splice(idx, 1);
      update({ extractions: next });
    },
    [extractions, update],
  );

  /* -- Assertion helpers -- */
  const assertions = d?.assertions ?? EMPTY_ASSERTIONS;
  const handleAssertChange = useCallback(
    (idx: number, field: string, val: string) => {
      const next = [...assertions];
      next[idx] = { ...next[idx], [field]: field === "expected" ? val : val };
      update({ assertions: next });
    },
    [assertions, update],
  );

  const addAssertion = useCallback(() => {
    update({
      assertions: [...assertions, { type: "status_code", expected: 200, operator: "equals" }],
    });
  }, [assertions, update]);

  const removeAssertion = useCallback(
    (idx: number) => {
      const next = [...assertions];
      next.splice(idx, 1);
      update({ assertions: next });
    },
    [assertions, update],
  );

  if (!node || !d) return null;

  /* -- Headers / Body as JSON strings -- */
  const headersStr = d.headers ? JSON.stringify(d.headers, null, 2) : "{}";
  const bodyStr = d.body ?? "";

  return (
    <div className="w-80 border-l border-slate-800 bg-slate-900/95 backdrop-blur-sm flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 shrink-0">
        <h3 className="text-sm font-semibold text-white">Node Properties</h3>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-slate-300 text-sm transition-colors"
        >
          x
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Label */}
        <div className="space-y-1">
          <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
            Label
          </label>
          <input
            value={d.label ?? ""}
            onChange={(e) => update({ label: e.target.value })}
            className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/60"
            placeholder="Node label"
          />
        </div>

        {/* Method */}
        <div className="space-y-1">
          <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
            Method
          </label>
          <div className="flex gap-1">
            {METHODS.map((m) => (
              <button
                key={m}
                onClick={() => update({ method: m })}
                className={`rounded-lg px-2.5 py-1 text-[10px] font-bold transition-colors ${
                  d.method === m
                    ? m === "GET" ? "bg-emerald-600 text-white"
                    : m === "POST" ? "bg-blue-600 text-white"
                    : m === "PUT" ? "bg-amber-600 text-white"
                    : m === "PATCH" ? "bg-orange-600 text-white"
                    : "bg-red-600 text-white"
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        {/* Path */}
        <div className="space-y-1">
          <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
            Path / URL
          </label>
          <input
            value={d.path ?? ""}
            onChange={(e) => update({ path: e.target.value })}
            className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs text-slate-300 font-mono placeholder-slate-600 focus:outline-none focus:border-blue-500/60"
            placeholder="/api/v1/auth/login"
          />
        </div>

        {/* Headers (JSON) */}
        <JsonField
          label="Headers (JSON)"
          value={headersStr}
          onChange={(v) => {
            try {
              update({ headers: JSON.parse(v) });
            } catch {
              /* invalid JSON — keep editing */
            }
          }}
        />

        {/* Body (JSON) */}
        <JsonField
          label="Body (JSON)"
          value={bodyStr}
          onChange={(v) => update({ body: v })}
        />

        {/* Variable Extractions */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              Variable Extractions
            </label>
            <button
              onClick={addExtraction}
              className="text-[10px] text-purple-400 hover:text-purple-300 transition-colors"
            >
              + Add
            </button>
          </div>
          {(d.extractions ?? []).map((ext, i) => (
            <ExtractionRow
              key={i}
              ext={ext}
              idx={i}
              onChange={handleExtChange}
              onRemove={removeExtraction}
            />
          ))}
        </div>

        {/* Assertions */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              Assertions
            </label>
            <button
              onClick={addAssertion}
              className="text-[10px] text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              + Add
            </button>
          </div>
          {(d.assertions ?? []).map((a, i) => (
            <AssertionRow
              key={i}
              assertion={a}
              idx={i}
              onChange={handleAssertChange}
              onRemove={removeAssertion}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
