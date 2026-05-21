"use client";

/**
 * SchemaERD — WizardTable[] şemasını interaktif ER diyagramı olarak gösterir.
 * ReactFlow v11 kullanır (zaten yüklü).
 *
 * Özellikler:
 * - Her tablo → özel node (sütun listesi, tip badge, PK/FK/PII ikonları)
 * - FK ilişkileri → animasyonlu ok (kaynak → hedef)
 * - Otomatik katmanlı yerleşim (bağımsız tablolar solda, bağımlılar sağda)
 * - Zoom, pan, minimap, fit-view
 */

import { useEffect, useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  BackgroundVariant,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";

/* ─── Types ───────────────────────────────────────────────── */
type WizardColumn = {
  id: number; name: string; type: string; unique: boolean;
  references?: string;
};
type WizardTable = {
  id: number; name: string; rowCount: number; columns: WizardColumn[];
};

/* ─── Type → badge style ──────────────────────────────────── */
const TYPE_BG: Record<string, string> = {
  auto_increment: "#ede9fe", uuid: "#ede9fe",
  foreign_key: "#dbeafe",
  email: "#dcfce7", phone: "#dcfce7",
  tc_kimlik: "#fee2e2", iban: "#fee2e2",
  enum: "#ffedd5",
  integer: "#f1f5f9", decimal: "#f1f5f9",
  date: "#cffafe", boolean: "#fef9c3",
  string: "#f9fafb", text: "#f9fafb",
};
const TYPE_FG: Record<string, string> = {
  auto_increment: "#7c3aed", uuid: "#7c3aed",
  foreign_key: "#2563eb",
  email: "#16a34a", phone: "#16a34a",
  tc_kimlik: "#dc2626", iban: "#dc2626",
  enum: "#ea580c",
  integer: "#475569", decimal: "#475569",
  date: "#0891b2", boolean: "#ca8a04",
  string: "#6b7280", text: "#6b7280",
};

const PII_TYPES  = new Set(["email", "phone", "tc_kimlik", "iban"]);
const MAX_COLS   = 12;
const NODE_W     = 252;
const NODE_GAP_X = 90;
const NODE_GAP_Y = 36;
const COL_H      = 24;
const HEADER_H   = 40;
const FOOTER_H   = 8;

/* ─── Auto-layout (topological layers) ───────────────────── */
function buildLayout(tables: WizardTable[]): Record<string, { x: number; y: number }> {
  const names    = new Set(tables.map((t) => t.name));
  const deps     = new Map<string, Set<string>>(); // table → tables it FK-references
  const rdeps    = new Map<string, Set<string>>(); // table → tables that FK it

  for (const t of tables) {
    deps.set(t.name, new Set());
    rdeps.set(t.name, new Set());
  }
  for (const t of tables) {
    for (const c of t.columns) {
      if (c.type === "foreign_key" && c.references) {
        const ref = c.references.split(".")[0];
        if (names.has(ref) && ref !== t.name) {
          deps.get(t.name)!.add(ref);
          rdeps.get(ref)!.add(t.name);
        }
      }
    }
  }

  // Kahn's BFS → assign layer index
  const layer = new Map<string, number>();
  const inDeg = new Map<string, number>();
  for (const t of tables) inDeg.set(t.name, deps.get(t.name)!.size);

  let queue = tables.map((t) => t.name).filter((n) => inDeg.get(n) === 0);
  let lvl = 0;
  const processed = new Set<string>();

  while (queue.length > 0) {
    for (const n of queue) { layer.set(n, lvl); processed.add(n); }
    const next: string[] = [];
    for (const n of queue) {
      for (const child of rdeps.get(n) || []) {
        if (!processed.has(child)) {
          const nd = (inDeg.get(child) || 0) - 1;
          inDeg.set(child, nd);
          if (nd === 0) next.push(child);
        }
      }
    }
    queue = next;
    lvl++;
  }
  // Cyclic remainder
  for (const t of tables) {
    if (!layer.has(t.name)) layer.set(t.name, lvl);
  }

  // Group by layer
  const byLayer = new Map<number, string[]>();
  for (const [name, l] of layer) {
    if (!byLayer.has(l)) byLayer.set(l, []);
    byLayer.get(l)!.push(name);
  }

  // Compute positions
  const pos: Record<string, { x: number; y: number }> = {};
  let x = 0;
  const sortedLayers = Array.from(byLayer.keys()).sort((a, b) => a - b);

  for (const l of sortedLayers) {
    const group = byLayer.get(l)!;
    let y = 0;
    for (const name of group) {
      pos[name] = { x, y };
      const tbl = tables.find((t) => t.name === name)!;
      const shownCols = Math.min(tbl.columns.length, MAX_COLS);
      const nodeH = HEADER_H + shownCols * COL_H + FOOTER_H + 8;
      y += nodeH + NODE_GAP_Y;
    }
    x += NODE_W + NODE_GAP_X;
  }
  return pos;
}

/* ─── Custom Table Node ───────────────────────────────────── */
function TableNode({ data }: NodeProps<{ table: WizardTable; highlighted: boolean }>) {
  const t = data.table;
  const shown = t.columns.slice(0, MAX_COLS);
  const rest  = t.columns.length - MAX_COLS;

  const hasFKIn  = t.columns.some((c) => c.type === "foreign_key");
  const hasFKOut = true; // every table can be referenced

  return (
    <div
      style={{
        width: NODE_W,
        borderRadius: 12,
        border: data.highlighted ? "2px solid #6366f1" : "1.5px solid #cbd5e1",
        background: "#fff",
        boxShadow: "0 4px 16px 0 rgba(0,0,0,0.08)",
        overflow: "hidden",
        fontFamily: "inherit",
      }}
    >
      {/* Source handle (right) — other tables can FK into this one */}
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: "#6366f1", width: 8, height: 8, border: "2px solid #fff" }}
      />
      {/* Target handle (left) — this table has FK columns */}
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: "#3b82f6", width: 8, height: 8, border: "2px solid #fff" }}
      />

      {/* Header */}
      <div
        style={{
          background: "linear-gradient(135deg, #1e293b 0%, #334155 100%)",
          padding: "8px 12px",
          display: "flex",
          alignItems: "center",
          gap: 6,
          height: HEADER_H,
        }}
      >
        <span style={{ fontSize: 16 }}>🗃️</span>
        <span
          style={{
            flex: 1,
            fontWeight: 700,
            fontSize: 11,
            color: "#f8fafc",
            letterSpacing: "0.02em",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
          title={t.name}
        >
          {t.name}
        </span>
        <span
          style={{
            fontSize: 9,
            color: "#94a3b8",
            background: "#0f172a",
            borderRadius: 4,
            padding: "1px 5px",
            whiteSpace: "nowrap",
            flexShrink: 0,
          }}
        >
          {t.rowCount} satır
        </span>
      </div>

      {/* Columns */}
      <div style={{ background: "#fff" }}>
        {shown.map((c, idx) => {
          const isPII = PII_TYPES.has(c.type);
          const isFK  = c.type === "foreign_key";
          const isPK  = c.type === "auto_increment" || c.type === "uuid";
          const bg    = isPII ? "#fff5f5" : isFK ? "#eff6ff" : idx % 2 === 0 ? "#fff" : "#f8fafc";

          return (
            <div
              key={c.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                padding: "3px 10px",
                background: bg,
                height: COL_H,
                borderBottom: "1px solid #f1f5f9",
              }}
            >
              <span style={{ fontSize: 11, width: 14, textAlign: "center", flexShrink: 0 }}>
                {isPK ? "🔑" : isFK ? "🔗" : isPII ? "⚠️" : "·"}
              </span>
              <span
                style={{
                  flex: 1,
                  fontSize: 10,
                  color: isPII ? "#991b1b" : "#334155",
                  fontWeight: isPK || isFK ? 600 : 400,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
                title={c.name}
              >
                {c.name}
              </span>
              {c.unique && !isPK && (
                <span style={{ fontSize: 8, color: "#94a3b8" }}>U</span>
              )}
              <span
                style={{
                  fontSize: 8,
                  fontFamily: "monospace",
                  fontWeight: 600,
                  padding: "1px 4px",
                  borderRadius: 3,
                  background: TYPE_BG[c.type] || "#f9fafb",
                  color: TYPE_FG[c.type] || "#6b7280",
                  flexShrink: 0,
                  maxWidth: 64,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
                title={c.type + (c.references ? ` → ${c.references}` : "")}
              >
                {c.type}
              </span>
            </div>
          );
        })}
        {rest > 0 && (
          <div
            style={{
              padding: "4px 10px",
              fontSize: 9,
              color: "#94a3b8",
              textAlign: "center",
              background: "#f8fafc",
            }}
          >
            +{rest} kolon daha
          </div>
        )}
        {/* Bottom padding */}
        <div style={{ height: FOOTER_H }} />
      </div>
    </div>
  );
}

const NODE_TYPES = { tableNode: TableNode };

/* ─── FK edge builder ─────────────────────────────────────── */
function buildEdges(tables: WizardTable[], names: Set<string>): Edge[] {
  const edges: Edge[] = [];
  const seen = new Set<string>();
  for (const t of tables) {
    for (const c of t.columns) {
      if (c.type !== "foreign_key" || !c.references) continue;
      const refTable = c.references.split(".")[0];
      if (!names.has(refTable) || refTable === t.name) continue;
      const id = `${refTable}→${t.name}:${c.name}`;
      if (seen.has(id)) continue;
      seen.add(id);
      edges.push({
        id,
        source: refTable,
        target: t.name,
        label: c.name,
        type: "smoothstep",
        animated: true,
        style: { stroke: "#6366f1", strokeWidth: 1.5 },
        labelStyle: { fontSize: 8, fill: "#4f46e5", fontWeight: 600 },
        labelBgStyle: { fill: "#eef2ff", borderRadius: 4 },
        labelBgPadding: [3, 5] as [number, number],
        markerEnd: { type: MarkerType.ArrowClosed, color: "#6366f1", width: 14, height: 14 },
      });
    }
  }
  return edges;
}

/* ─── Main Export ─────────────────────────────────────────── */
export function SchemaERD({ tables }: { tables: WizardTable[] }) {
  const names = new Set(tables.map((t) => t.name));
  const positions = buildLayout(tables);

  const makeNodes = useCallback(
    (tbls: WizardTable[]): Node[] =>
      tbls.map((t) => ({
        id: t.name,
        type: "tableNode",
        position: positions[t.name] || { x: 0, y: 0 },
        data: { table: t, highlighted: false },
        draggable: true,
        selectable: true,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(tables.map((t) => t.name))]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(makeNodes(tables));
  const [edges, setEdges, onEdgesChange] = useEdgesState(buildEdges(tables, names));

  useEffect(() => {
    const pos = buildLayout(tables);
    setNodes(
      tables.map((t) => ({
        id: t.name,
        type: "tableNode",
        position: pos[t.name] || { x: 0, y: 0 },
        data: { table: t, highlighted: false },
        draggable: true,
        selectable: true,
      }))
    );
    setEdges(buildEdges(tables, new Set(tables.map((t) => t.name))));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(tables)]);

  if (!tables.length) return null;

  const fkCount = edges.length;
  const piiCount = tables.flatMap((t) => t.columns).filter((c) => PII_TYPES.has(c.type)).length;

  return (
    <div className="space-y-2">
      {/* Legend */}
      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 px-1">
        <span className="font-medium text-white">ER Diyagramı</span>
        <span className="flex items-center gap-1">🗃️ {tables.length} tablo</span>
        <span className="flex items-center gap-1">🔗 {fkCount} ilişki</span>
        {piiCount > 0 && (
          <span className="flex items-center gap-1 text-red-500">⚠️ {piiCount} PII kolon</span>
        )}
        <span className="ml-auto text-slate-400/60">Sürükleyebilir · Zoom: ⌘+scroll</span>
      </div>

      {/* Legend pills */}
      <div className="flex flex-wrap gap-1.5 px-1">
        {[
          { icon: "🔑", label: "Primary Key", bg: "#ede9fe", fg: "#7c3aed" },
          { icon: "🔗", label: "Foreign Key", bg: "#dbeafe", fg: "#2563eb" },
          { icon: "⚠️", label: "PII (kişisel veri)", bg: "#fee2e2", fg: "#dc2626" },
          { icon: "→",  label: "FK ilişkisi (animasyonlu)", bg: "#eef2ff", fg: "#4f46e5" },
        ].map((l) => (
          <span
            key={l.label}
            style={{ background: l.bg, color: l.fg }}
            className="rounded-full px-2 py-0.5 text-[10px] font-medium border border-current/20"
          >
            {l.icon} {l.label}
          </span>
        ))}
      </div>

      {/* Diagram */}
      <div
        style={{ height: Math.min(Math.max(tables.length * 40 + 200, 400), 640) }}
        className="w-full rounded-xl border border-slate-800 overflow-hidden shadow-sm"
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={NODE_TYPES}
          fitView
          fitViewOptions={{ padding: 0.18, includeHiddenNodes: false }}
          minZoom={0.1}
          maxZoom={2.5}
          proOptions={{ hideAttribution: true }}
          deleteKeyCode={null}
          nodesConnectable={false}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={18}
            size={1}
            color="#e2e8f0"
          />
          <Controls showInteractive={false} position="bottom-right" />
          <MiniMap
            nodeColor={() => "#94a3b8"}
            maskColor="rgba(248,250,252,0.75)"
            style={{ borderRadius: 8, bottom: 48, right: 8 }}
            zoomable
            pannable
          />
        </ReactFlow>
      </div>
    </div>
  );
}
