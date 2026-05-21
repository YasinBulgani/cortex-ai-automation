"use client";

import React, { useCallback, useMemo, useRef, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import ReactFlow, {
  addEdge,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
  type OnSelectionChangeParams,
} from "reactflow";
import "reactflow/dist/style.css";

import { FlowGuideCard } from "@/components/FlowGuideCard";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { ServiceTestingGuide } from "@/components/ServiceTestingGuide";
import {
  useChains,
  useCreateChain,
  useDeleteChain,
  useRunChain,
  type ApiChain,
  type ChainRunResult,
} from "@/lib/hooks/use-api-testing";

import { chainNodeTypes, type RequestNodeData } from "./_components/nodes";
import { NodePanel } from "./_components/node-panel";
import { CHAIN_TEMPLATES } from "./_components/templates";

/* ── Helpers ─────────────────────────────────────────────────────────── */
let nodeCounter = 0;
function nextNodeId() {
  nodeCounter += 1;
  return `node-${Date.now()}-${nodeCounter}`;
}

function defaultRequestData(): RequestNodeData {
  return {
    label: "New Request",
    method: "GET",
    path: "/api/v1/",
    headers: { "Content-Type": "application/json" },
    body: "",
    extractions: [],
    assertions: [{ type: "status_code", expected: 200, operator: "equals" }],
  };
}

/* ── Toolbar ─────────────────────────────────────────────────────────── */
function Toolbar({
  chainName,
  onChainNameChange,
  onAddNode,
  onSave,
  onRun,
  saving,
  chains,
  onLoadChain,
  onLoadTemplate,
  onDeleteChain,
}: {
  chainName: string;
  onChainNameChange: (n: string) => void;
  onAddNode: () => void;
  onSave: () => void;
  onRun: () => void;
  saving: boolean;
  chains: ApiChain[];
  onLoadChain: (c: ApiChain) => void;
  onLoadTemplate: (idx: number) => void;
  onDeleteChain: (id: string) => void;
}) {
  const [loadOpen, setLoadOpen] = useState(false);
  const [templateOpen, setTemplateOpen] = useState(false);

  return (
    <div className="flex flex-wrap items-center gap-2 px-4 py-2.5 border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm">
      {/* Chain name input */}
      <input
        value={chainName}
        onChange={(e) => onChainNameChange(e.target.value)}
        className="rounded-lg border border-slate-700 bg-slate-800/70 px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/60 w-56"
        placeholder="Chain adi..."
      />

      {/* Divider */}
      <div className="w-px h-6 bg-slate-700" />

      {/* Add Request Node */}
      <button
        onClick={onAddNode}
        className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 transition-colors"
      >
        <span className="text-sm">+</span> Request Node
      </button>

      {/* Templates dropdown */}
      <div className="relative">
        <button
          onClick={() => { setTemplateOpen(!templateOpen); setLoadOpen(false); }}
          className="flex items-center gap-1.5 rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 transition-colors"
        >
          Templates
          <span className="text-[10px]">{templateOpen ? "\u25B2" : "\u25BC"}</span>
        </button>
        {templateOpen && (
          <div className="absolute top-full left-0 mt-1 w-72 rounded-lg border border-slate-700 bg-slate-900 shadow-xl z-50">
            {CHAIN_TEMPLATES.map((t, i) => (
              <button
                key={i}
                onClick={() => { onLoadTemplate(i); setTemplateOpen(false); }}
                className="w-full text-left px-3 py-2.5 hover:bg-slate-800 transition-colors border-b border-slate-800 last:border-b-0"
              >
                <div className="text-xs font-semibold text-white">{t.name}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">{t.description}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Load chain dropdown */}
      <div className="relative">
        <button
          onClick={() => { setLoadOpen(!loadOpen); setTemplateOpen(false); }}
          className="flex items-center gap-1.5 rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 transition-colors"
        >
          Load Chain
          {chains.length > 0 && (
            <span className="ml-1 rounded-full bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400">
              {chains.length}
            </span>
          )}
          <span className="text-[10px]">{loadOpen ? "\u25B2" : "\u25BC"}</span>
        </button>
        {loadOpen && (
          <div className="absolute top-full left-0 mt-1 w-64 max-h-60 overflow-y-auto rounded-lg border border-slate-700 bg-slate-900 shadow-xl z-50">
            {chains.length === 0 ? (
              <div className="px-3 py-3 text-xs text-slate-500">Kayitli chain yok</div>
            ) : (
              chains.map((c) => (
                <div
                  key={c.id}
                  className="flex items-center justify-between px-3 py-2 hover:bg-slate-800 transition-colors border-b border-slate-800 last:border-b-0"
                >
                  <button
                    onClick={() => { onLoadChain(c); setLoadOpen(false); }}
                    className="flex-1 text-left"
                  >
                    <div className="text-xs font-medium text-white">{c.name}</div>
                    <div className="text-[10px] text-slate-500">
                      {c.nodes.length} node, {c.edges.length} edge
                    </div>
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); onDeleteChain(c.id); }}
                    className="text-slate-600 hover:text-red-400 text-xs px-1.5 transition-colors"
                    title="Delete chain"
                  >
                    x
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Save */}
      <button
        onClick={onSave}
        disabled={saving}
        className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 transition-colors"
      >
        {saving ? "Saving..." : "Save Chain"}
      </button>

      {/* Run */}
      <button
        onClick={onRun}
        className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-4 py-1.5 text-xs font-semibold text-white hover:from-blue-500 hover:to-purple-500 transition-all"
      >
        Run Chain
      </button>
    </div>
  );
}

/* ── Edge styling ────────────────────────────────────────────────────── */
const defaultEdgeOptions = {
  animated: true,
  style: { stroke: "#6366f1", strokeWidth: 2 },
  labelBgStyle: { fill: "#1e293b", fillOpacity: 0.9 },
  labelStyle: { fill: "#a5b4fc", fontSize: 10, fontWeight: 600 },
};

/* ══════════════════════════════════════════════════════════════════════ */
/*  MAIN PAGE                                                           */
/* ══════════════════════════════════════════════════════════════════════ */

export default function ChainBuilderPage() {
  const projectId = useRouteParam("projectId");

  /* ── Chain query hooks ──────────────────────────────────────────────── */
  const { data: chains = [] } = useChains(projectId);
  const createChain = useCreateChain(projectId);
  const deleteChain = useDeleteChain(projectId);
  const runChain = useRunChain(projectId);

  /* ── Flow state ─────────────────────────────────────────────────────── */
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node<RequestNodeData> | null>(null);
  const [chainName, setChainName] = useState("Untitled Chain");
  const [loadedChainId, setLoadedChainId] = useState<string | null>(null);
  const [runOutput, setRunOutput] = useState<string | null>(null);

  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  /* Memoize node types to prevent unnecessary re-renders */
  const nodeTypes = useMemo(() => chainNodeTypes, []);

  /* ── Callbacks ──────────────────────────────────────────────────────── */
  const onConnect = useCallback(
    (connection: Connection) => {
      const newEdge: Edge = {
        ...connection,
        id: `edge-${Date.now()}`,
        animated: true,
        style: { stroke: "#6366f1", strokeWidth: 2 },
        label: "data",
      } as Edge;
      setEdges((eds) => addEdge(newEdge, eds));
    },
    [setEdges],
  );

  const onSelectionChange = useCallback(
    ({ nodes: selectedNodes }: OnSelectionChangeParams) => {
      if (selectedNodes.length === 1 && selectedNodes[0].type === "request") {
        setSelectedNode(selectedNodes[0] as Node<RequestNodeData>);
      } else {
        setSelectedNode(null);
      }
    },
    [],
  );

  /* Update node data from panel */
  const handleNodeUpdate = useCallback(
    (nodeId: string, data: Partial<RequestNodeData>) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, ...data } } : n,
        ),
      );
      setSelectedNode((prev) =>
        prev?.id === nodeId ? { ...prev, data: { ...prev.data, ...data } } : prev,
      );
    },
    [setNodes],
  );

  /* Add new request node */
  const handleAddNode = useCallback(() => {
    const newNode: Node<RequestNodeData> = {
      id: nextNodeId(),
      type: "request",
      position: {
        x: 100 + nodes.length * 60,
        y: 120 + (nodes.length % 3) * 80,
      },
      data: defaultRequestData(),
    };
    setNodes((nds) => [...nds, newNode]);
  }, [nodes.length, setNodes]);

  /* Save chain */
  const handleSave = useCallback(() => {
    const payload = {
      name: chainName,
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.type,
        position: n.position,
        data: n.data,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        data: e.data,
      })),
      global_variables: {},
      stop_on_failure: true,
      max_retries: 0,
      delay_between_ms: 0,
    };
    createChain.mutate(payload);
  }, [chainName, nodes, edges, createChain]);

  /* Run chain — gerçek API (kaydedilmiş chain gerekir) */
  const handleRun = useCallback(() => {
    if (!loadedChainId) {
      setRunOutput("⚠ Önce chain'i kaydet (💾 Kaydet), ardından çalıştır.");
      return;
    }
    setRunOutput(`Chain "${chainName}" çalıştırılıyor…`);
    runChain.mutate(loadedChainId, {
      onSuccess: (result: ChainRunResult) => {
        const lines: string[] = [
          `✓ Run ID: ${result.run_id}`,
          `Durum: ${result.status} · Süre: ${result.total_duration_ms}ms`,
          `Geçen: ${result.passed} · Başarısız: ${result.failed}`,
          "",
        ];
        for (const step of result.steps) {
          const icon = step.ok ? "✓" : "✗";
          lines.push(`  ${icon} [${step.method}] ${step.path} → ${step.status_code} (${step.duration_ms}ms)${step.error ? " — " + step.error : ""}`);
        }
        setRunOutput(lines.join("\n"));
      },
      onError: (err: unknown) => {
        const msg = err instanceof Error ? err.message : "Bilinmeyen hata";
        setRunOutput(`✗ Chain çalıştırılamadı: ${msg}`);
      },
    });
  }, [chainName, loadedChainId, runChain]);

  /* Load chain */
  const handleLoadChain = useCallback(
    (chain: ApiChain) => {
      setChainName(chain.name);
      setLoadedChainId(chain.id);
      setNodes(
        chain.nodes.map((n: Record<string, unknown>) => ({
          id: n.id as string,
          type: (n.type as string) || "request",
          position: n.position as { x: number; y: number },
          data: n.data as RequestNodeData,
        })),
      );
      setEdges(
        chain.edges.map((e: Record<string, unknown>) => ({
          id: e.id as string,
          source: e.source as string,
          target: e.target as string,
          label: e.label as string | undefined,
          data: e.data as Record<string, unknown> | undefined,
          animated: true,
          style: { stroke: "#6366f1", strokeWidth: 2 },
        })),
      );
      setSelectedNode(null);
      setRunOutput(null);
    },
    [setNodes, setEdges],
  );

  /* Load template */
  const handleLoadTemplate = useCallback(
    (idx: number) => {
      const tpl = CHAIN_TEMPLATES[idx];
      if (!tpl) return;
      setChainName(tpl.name);
      setLoadedChainId(null);
      setNodes(tpl.nodes);
      setEdges(tpl.edges);
      setSelectedNode(null);
      setRunOutput(null);
    },
    [setNodes, setEdges],
  );

  /* Delete chain */
  const handleDeleteChain = useCallback(
    (id: string) => {
      deleteChain.mutate(id);
      if (loadedChainId === id) {
        setLoadedChainId(null);
        setChainName("Untitled Chain");
        setNodes([]);
        setEdges([]);
        setSelectedNode(null);
      }
    },
    [deleteChain, loadedChainId, setNodes, setEdges],
  );

  return (
    <div className="mx-auto max-w-[1600px] space-y-4" data-testid="chain-builder-page">
      <PageHeader
        title="Zincir Oluşturucu"
        description="Surukle-birak ile API cagri zincirleri oluşturun ve test edin"
        badge={
          loadedChainId ? (
            <span className="inline-flex items-center rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
              Loaded
            </span>
          ) : undefined
        }
      />
      <FlowGuideCard projectId={projectId} stage="execute" />
      <ServiceTestingGuide projectId={projectId} stage="chain" />

      <SectionCard noPad>
        {/* Toolbar */}
        <Toolbar
          chainName={chainName}
          onChainNameChange={setChainName}
          onAddNode={handleAddNode}
          onSave={handleSave}
          onRun={handleRun}
          saving={createChain.isPending}
          chains={chains}
          onLoadChain={handleLoadChain}
          onLoadTemplate={handleLoadTemplate}
          onDeleteChain={handleDeleteChain}
        />

        {/* Canvas + Panel */}
        <div className="flex" style={{ height: "calc(100vh - 260px)", minHeight: 500 }}>
          {/* React Flow canvas */}
          <div ref={reactFlowWrapper} className="flex-1 bg-slate-950">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onSelectionChange={onSelectionChange}
              nodeTypes={nodeTypes}
              defaultEdgeOptions={defaultEdgeOptions}
              fitView
              fitViewOptions={{ padding: 0.3 }}
              deleteKeyCode={["Backspace", "Delete"]}
              className="chain-builder-flow"
            >
              <Background
                variant={BackgroundVariant.Dots}
                gap={20}
                size={1}
                color="#334155"
              />
              <Controls
                position="bottom-left"
                className="!bg-slate-800 !border-slate-700 !rounded-lg !shadow-lg [&>button]:!bg-slate-800 [&>button]:!border-slate-700 [&>button]:!text-slate-400 [&>button:hover]:!bg-slate-700"
              />
              <MiniMap
                position="bottom-right"
                nodeColor="#475569"
                maskColor="rgba(15, 23, 42, 0.7)"
                className="!bg-slate-900 !border-slate-700 !rounded-lg"
                pannable
                zoomable
              />
            </ReactFlow>
          </div>

          {/* Right panel */}
          {selectedNode && (
            <NodePanel
              node={selectedNode}
              onUpdate={handleNodeUpdate}
              onClose={() => setSelectedNode(null)}
            />
          )}
        </div>
      </SectionCard>

      {/* Run output */}
      {runOutput && (
        <SectionCard title="Chain Run Output">
          <pre className="whitespace-pre-wrap text-xs text-slate-300 font-mono bg-slate-900 rounded-lg p-4 border border-slate-800 max-h-48 overflow-y-auto">
            {runOutput}
          </pre>
        </SectionCard>
      )}

      {/* Save confirmation */}
      {createChain.isSuccess && (
        <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-3 text-xs text-emerald-300">
          Chain basariyla kaydedildi.
        </div>
      )}

      {createChain.isError && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-xs text-red-300">
          Hata: {createChain.error instanceof Error ? createChain.error.message : "Bilinmeyen hata"}
        </div>
      )}
    </div>
  );
}
