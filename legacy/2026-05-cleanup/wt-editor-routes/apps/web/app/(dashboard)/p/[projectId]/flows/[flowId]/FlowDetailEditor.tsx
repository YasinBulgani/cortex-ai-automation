"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { useRouteParam } from "@/lib/use-route-param";
import Link from "next/link";
import ReactFlow, {
  addEdge,
  Background,
  Controls,
  MiniMap,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
  type ReactFlowInstance,
  BackgroundVariant,
  MarkerType,
  Panel,
} from "reactflow";
import "reactflow/dist/style.css";

import { apiFetch } from "@/lib/api";
import FlowNode, { type FlowNodeData } from "@/components/flow/FlowNode";
import { NodePalette } from "@/components/flow/NodePalette";
import { NodePropertiesPanel } from "@/components/flow/NodePropertiesPanel";
import { SimulationPanel } from "@/components/flow/SimulationPanel";
import { useFlowSimulation } from "@/components/flow/useFlowSimulation";
import { NODE_CONFIGS, type FlowNodeType } from "@/components/flow/nodeTypes";
import { Button } from "@/components/ui/button";

type FlowDetail = {
  id: string;
  name: string;
  description: string | null;
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
};

const nodeTypes = { flowNode: FlowNode };

const defaultEdgeOptions = {
  animated: true,
  style: { strokeWidth: 2, stroke: "#94a3b8" },
  markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8" },
};

let nodeIdCounter = 0;
function nextNodeId() {
  return `node_${Date.now()}_${++nodeIdCounter}`;
}

export default function FlowDetailEditor() {
  const projectId = useRouteParam("projectId");
  const flowId = useRouteParam("flowId");

  const [flowData, setFlowData] = useState<FlowDetail | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node<FlowNodeData> | null>(null);
  const [showSimulation, setShowSimulation] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "error">("idle");

  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null);

  const {
    simState,
    logs,
    progress,
    runSimulation,
    stopSimulation,
    pauseSimulation,
    resumeSimulation,
    resetSimulation,
  } = useFlowSimulation(nodes, edges, setNodes);

  const load = useCallback(() => {
    apiFetch<FlowDetail>(
      `/api/v1/tspm/projects/${projectId}/flows/${flowId}`
    ).then((data) => {
      setFlowData(data);

      const rfNodes: Node<FlowNodeData>[] = (data.nodes ?? []).map((n: Record<string, unknown>) => ({
        id: n.id as string,
        type: "flowNode",
        position: { x: (n.position_x as number) ?? 0, y: (n.position_y as number) ?? 0 },
        data: {
          label: (n.label as string) || (n.node_type as string) || "Düğüm",
          nodeType: ((n.node_type as string) || "trigger") as FlowNodeType,
          config: (n.config as Record<string, unknown>) || {},
          simulationStatus: "idle" as const,
        },
      }));

      const rfEdges: Edge[] = (data.edges ?? []).map((e: Record<string, unknown>) => ({
        id: e.id as string,
        source: (e.source_node_id ?? e.source) as string,
        target: (e.target_node_id ?? e.target) as string,
        sourceHandle: (e.sourceHandle as string) || undefined,
        label: (e.label as string) || undefined,
        ...defaultEdgeOptions,
      }));

      setNodes(rfNodes);
      setEdges(rfEdges);
    });
  }, [projectId, flowId, setNodes, setEdges]);

  useEffect(() => {
    load();
  }, [load]);

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge(
          { ...connection, ...defaultEdgeOptions, id: `edge_${Date.now()}` },
          eds
        )
      );
    },
    [setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const nodeType = event.dataTransfer.getData("application/reactflow-type") as FlowNodeType;
      if (!nodeType || !rfInstance || !reactFlowWrapper.current) return;

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = rfInstance.project({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      });

      const cfg = NODE_CONFIGS[nodeType];
      const newNode: Node<FlowNodeData> = {
        id: nextNodeId(),
        type: "flowNode",
        position,
        data: {
          label: cfg.label,
          nodeType,
          config: { ...cfg.defaultData },
          simulationStatus: "idle",
        },
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [rfInstance, setNodes]
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node<FlowNodeData>) => {
      setSelectedNode(node);
    },
    []
  );

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleNodeDataChange = useCallback(
    (nodeId: string, newData: Partial<FlowNodeData>) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, ...newData } } : n
        )
      );
      setSelectedNode((prev) =>
        prev && prev.id === nodeId
          ? { ...prev, data: { ...prev.data, ...newData } }
          : prev
      );
    },
    [setNodes]
  );

  const handleNodeDelete = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
      setSelectedNode(null);
    },
    [setNodes, setEdges]
  );

  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaveStatus("idle");
    try {
      const saveNodes = nodes.map((n) => ({
        id: n.id,
        node_type: n.data.nodeType,
        label: n.data.label,
        position_x: n.position.x,
        position_y: n.position.y,
        config: n.data.config,
      }));
      const saveEdges = edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle || null,
        label: e.label || "",
      }));
      await apiFetch(`/api/v1/tspm/projects/${projectId}/flows/${flowId}/graph`, {
        method: "PUT",
        json: { nodes: saveNodes, edges: saveEdges },
      });
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch {
      setSaveStatus("error");
    } finally {
      setSaving(false);
    }
  }, [nodes, edges, projectId, flowId]);

  const selectedNodeData = useMemo(
    () => (selectedNode ? nodes.find((n) => n.id === selectedNode.id) ?? null : null),
    [selectedNode, nodes]
  );

  if (!flowData) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          <p className="mt-2 text-sm text-slate-400">Akış yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem-3rem)]" data-testid="flow-editor-page">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-900 shrink-0" data-testid="flow-editor-toolbar">
        <div className="flex items-center gap-3">
          <Link href={`/p/${projectId}/flows`}>
            <Button variant="ghost" className="text-xs px-2 py-1">
              ← Geri
            </Button>
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-white">{flowData.name}</h1>
            <p className="text-[11px] text-slate-400">
              {nodes.length} düğüm · {edges.length} bağlantı
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            className="text-xs"
            onClick={() => {
              if (showSimulation) {
                resetSimulation();
              }
              setShowSimulation(!showSimulation);
            }}
          >
            {showSimulation ? "Simülasyonu Kapat" : "⚡ Simülasyon"}
          </Button>
          <Button
            className="text-xs"
            onClick={handleSave}
            disabled={saving}
            data-testid="flow-editor-btn-save"
          >
            {saving ? "Kaydediliyor..." : saveStatus === "saved" ? "✓ Kaydedildi" : "Kaydet"}
          </Button>
        </div>
      </div>

      {/* Main area */}
      <div className="flex flex-1 min-h-0 relative">
        {/* Left: Node palette */}
        <NodePalette />

        {/* Center: React Flow canvas */}
        <div className="flex-1 relative" ref={reactFlowWrapper} data-testid="flow-editor">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setRfInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            defaultEdgeOptions={defaultEdgeOptions}
            fitView
            proOptions={{ hideAttribution: true }}
            deleteKeyCode={["Backspace", "Delete"]}
            className="bg-[#fafbfc] dark:bg-[#111]"
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#ddd" />
            <Controls
              className="!bg-slate-900 !border-slate-800 !shadow-md"
              showInteractive={false}
            />
            <MiniMap
              nodeColor={(n) => {
                const nd = n.data as FlowNodeData;
                return NODE_CONFIGS[nd?.nodeType]?.color ?? "#94a3b8";
              }}
              className="!bg-slate-900 !border-slate-800"
              maskColor="rgba(0,0,0,0.08)"
            />
            {nodes.length === 0 && (
              <Panel position="top-center" className="!mt-20">
                <div className="text-center bg-slate-900/90 backdrop-blur rounded-xl border border-slate-800 p-8 shadow-lg">
                  <p className="text-3xl mb-3">🔧</p>
                  <p className="text-sm font-medium text-white mb-1">Akışınızı oluşturun</p>
                  <p className="text-xs text-slate-400 max-w-[260px]">
                    Soldaki panelden düğümleri sürükleyip bu alana bırakın.
                    Bir Tetikleyici ile başlayın.
                  </p>
                </div>
              </Panel>
            )}
          </ReactFlow>

          {/* Simulation panel */}
          {showSimulation && (
            <SimulationPanel
              simState={simState}
              logs={logs}
              progress={progress}
              onRun={runSimulation}
              onStop={stopSimulation}
              onPause={pauseSimulation}
              onResume={resumeSimulation}
              onReset={resetSimulation}
              onClose={() => {
                resetSimulation();
                setShowSimulation(false);
              }}
            />
          )}
        </div>

        {/* Right: Properties panel */}
        {selectedNodeData && (
          <NodePropertiesPanel
            node={selectedNodeData}
            onChange={handleNodeDataChange}
            onDelete={handleNodeDelete}
            onClose={() => setSelectedNode(null)}
          />
        )}
      </div>
    </div>
  );
}
