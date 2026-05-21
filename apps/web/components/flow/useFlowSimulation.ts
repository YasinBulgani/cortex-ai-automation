"use client";

import { useCallback, useRef, useState } from "react";
import type { Node, Edge } from "reactflow";
import type { FlowNodeData } from "./FlowNode";

export type SimulationState = "idle" | "running" | "paused" | "completed" | "error";

interface SimulationLog {
  nodeId: string;
  nodeLabel: string;
  status: "running" | "success" | "error" | "skipped";
  message: string;
  timestamp: number;
  duration?: number;
}

export function useFlowSimulation(
  nodes: Node<FlowNodeData>[],
  edges: Edge[],
  setNodes: React.Dispatch<React.SetStateAction<Node<FlowNodeData>[]>>
) {
  const [simState, setSimState] = useState<SimulationState>("idle");
  const [logs, setLogs] = useState<SimulationLog[]>([]);
  const [progress, setProgress] = useState(0);
  const abortRef = useRef(false);
  const pauseRef = useRef(false);

  const resetSimulation = useCallback(() => {
    setSimState("idle");
    setLogs([]);
    setProgress(0);
    abortRef.current = false;
    pauseRef.current = false;
    setNodes((prev) =>
      prev.map((n) => ({
        ...n,
        data: { ...n.data, simulationStatus: "idle" as const },
      }))
    );
  }, [setNodes]);

  const stopSimulation = useCallback(() => {
    abortRef.current = true;
    setSimState("idle");
    setNodes((prev) =>
      prev.map((n) => ({
        ...n,
        data: { ...n.data, simulationStatus: "idle" as const },
      }))
    );
  }, [setNodes]);

  const pauseSimulation = useCallback(() => {
    pauseRef.current = true;
    setSimState("paused");
  }, []);

  const resumeSimulation = useCallback(() => {
    pauseRef.current = false;
    setSimState("running");
  }, []);

  const runSimulation = useCallback(async () => {
    abortRef.current = false;
    pauseRef.current = false;
    setSimState("running");
    setLogs([]);
    setProgress(0);

    setNodes((prev) =>
      prev.map((n) => ({
        ...n,
        data: { ...n.data, simulationStatus: "idle" as const },
      }))
    );

    const triggerNodes = nodes.filter((n) => n.data.nodeType === "trigger");
    if (triggerNodes.length === 0) {
      setLogs([{
        nodeId: "",
        nodeLabel: "Sistem",
        status: "error",
        message: "Tetikleyici düğüm bulunamadı. Akışa bir Tetikleyici ekleyin.",
        timestamp: Date.now(),
      }]);
      setSimState("error");
      return;
    }

    const adjacencyMap = new Map<string, { edgeId: string; target: string; sourceHandle: string | null }[]>();
    for (const edge of edges) {
      const list = adjacencyMap.get(edge.source) ?? [];
      list.push({ edgeId: edge.id, target: edge.target, sourceHandle: edge.sourceHandle ?? null });
      adjacencyMap.set(edge.source, list);
    }

    const queue: string[] = triggerNodes.map((n) => n.id);
    const visited = new Set<string>();
    let processed = 0;
    const totalToProcess = nodes.length;

    async function waitForResume() {
      while (pauseRef.current && !abortRef.current) {
        await new Promise((r) => setTimeout(r, 200));
      }
    }

    async function processNode(nodeId: string) {
      if (abortRef.current) return;
      if (visited.has(nodeId)) return;
      visited.add(nodeId);

      await waitForResume();
      if (abortRef.current) return;

      const node = nodes.find((n) => n.id === nodeId);
      if (!node) return;

      setNodes((prev) =>
        prev.map((n) =>
          n.id === nodeId
            ? { ...n, data: { ...n.data, simulationStatus: "running" as const } }
            : n
        )
      );

      const startTime = Date.now();
      setLogs((prev) => [
        ...prev,
        {
          nodeId,
          nodeLabel: node.data.label,
          status: "running",
          message: `"${node.data.label}" çalışıyor...`,
          timestamp: startTime,
        },
      ]);

      const delayMs = getNodeDelay(node);
      await new Promise((r) => setTimeout(r, delayMs));
      if (abortRef.current) return;

      const success = simulateNodeExecution(node);

      setNodes((prev) =>
        prev.map((n) =>
          n.id === nodeId
            ? { ...n, data: { ...n.data, simulationStatus: success ? ("success" as const) : ("error" as const) } }
            : n
        )
      );

      const duration = Date.now() - startTime;
      setLogs((prev) => {
        const updated = [...prev];
        const idx = updated.findLastIndex((l) => l.nodeId === nodeId && l.status === "running");
        if (idx !== -1) {
          updated[idx] = {
            ...updated[idx],
            status: success ? "success" : "error",
            message: success
              ? `"${node.data.label}" başarıyla tamamlandı (${duration}ms)`
              : `"${node.data.label}" hata ile sonuçlandı`,
            duration,
          };
        }
        return updated;
      });

      processed++;
      setProgress(Math.round((processed / totalToProcess) * 100));

      if (success) {
        const outgoing = adjacencyMap.get(nodeId) ?? [];
        if (node.data.nodeType === "condition") {
          const condResult = Math.random() > 0.3;
          for (const edge of outgoing) {
            const isMatch =
              (condResult && edge.sourceHandle === "true") ||
              (!condResult && edge.sourceHandle === "false");
            if (isMatch) {
              queue.push(edge.target);
            } else {
              visited.add(edge.target);
              setNodes((prev) =>
                prev.map((n) =>
                  n.id === edge.target
                    ? { ...n, data: { ...n.data, simulationStatus: "skipped" as const } }
                    : n
                )
              );
              setLogs((prev) => [
                ...prev,
                {
                  nodeId: edge.target,
                  nodeLabel: nodes.find((n) => n.id === edge.target)?.data.label ?? "",
                  status: "skipped",
                  message: `"${nodes.find((n) => n.id === edge.target)?.data.label}" atlandı (koşul ${condResult ? "doğru" : "yanlış"})`,
                  timestamp: Date.now(),
                },
              ]);
            }
          }
        } else {
          for (const edge of outgoing) {
            queue.push(edge.target);
          }
        }
      }
    }

    while (queue.length > 0) {
      if (abortRef.current) break;
      const nextId = queue.shift()!;
      await processNode(nextId);
    }

    if (!abortRef.current) {
      setSimState("completed");
      setProgress(100);
    }
  }, [nodes, edges, setNodes]);

  return {
    simState,
    logs,
    progress,
    runSimulation,
    stopSimulation,
    pauseSimulation,
    resumeSimulation,
    resetSimulation,
  };
}

function getNodeDelay(node: Node<FlowNodeData>): number {
  switch (node.data.nodeType) {
    case "trigger":
      return 600;
    case "http_request":
      return 1200 + Math.random() * 800;
    case "condition":
      return 500;
    case "delay": {
      const dur = (node.data.config.duration as number) || 1000;
      const unit = (node.data.config.unit as string) || "ms";
      const ms = unit === "s" ? dur * 1000 : unit === "m" ? dur * 60000 : dur;
      return Math.min(ms, 3000);
    }
    case "scenario":
      return 1500 + Math.random() * 1000;
    case "notification":
      return 800;
    case "transform":
      return 600;
    case "database":
      return 1000 + Math.random() * 500;
    case "loop":
      return 700;
    case "end":
      return 400;
    default:
      return 800;
  }
}

function simulateNodeExecution(node: Node<FlowNodeData>): boolean {
  if (node.data.nodeType === "end") return true;
  return Math.random() > 0.08;
}
