"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { NODE_CONFIGS, type FlowNodeType } from "./nodeTypes";

export interface FlowNodeData {
  label: string;
  nodeType: FlowNodeType;
  config: Record<string, unknown>;
  simulationStatus?: "idle" | "running" | "success" | "error" | "skipped";
}

function FlowNodeComponent({ data, selected }: NodeProps<FlowNodeData>) {
  const cfg = NODE_CONFIGS[data.nodeType] || NODE_CONFIGS.trigger;
  const simStatus = data.simulationStatus || "idle";

  const statusRing =
    simStatus === "running"
      ? "ring-2 ring-blue-400 animate-pulse"
      : simStatus === "success"
        ? "ring-2 ring-emerald-400"
        : simStatus === "error"
          ? "ring-2 ring-red-400"
          : simStatus === "skipped"
            ? "ring-2 ring-gray-300 opacity-60"
            : "";

  const selectedRing = selected && simStatus === "idle" ? "ring-2 ring-blue-500" : "";

  return (
    <div
      className={`relative rounded-xl shadow-lg transition-all duration-200 min-w-[180px] ${statusRing} ${selectedRing}`}
      style={{
        background: cfg.bgColor,
        border: `2px solid ${cfg.borderColor}`,
      }}
    >
      {data.nodeType !== "trigger" && (
        <Handle
          type="target"
          position={Position.Left}
          className="!w-3 !h-3 !border-2 !border-white"
          style={{ background: cfg.color }}
        />
      )}

      <div className="px-4 py-3">
        <div className="flex items-center gap-2 mb-1">
          <span
            className="flex items-center justify-center w-7 h-7 rounded-lg text-sm"
            style={{ background: cfg.color + "22" }}
          >
            {cfg.icon}
          </span>
          <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: cfg.color }}>
            {cfg.label}
          </span>
        </div>
        <div className="text-sm font-medium text-gray-800 truncate max-w-[160px]">
          {data.label}
        </div>

        {simStatus === "running" && (
          <div className="mt-2 flex items-center gap-1.5">
            <div className="h-1.5 flex-1 rounded-full bg-gray-200 overflow-hidden">
              <div className="h-full bg-blue-500 rounded-full animate-[shimmer_1.5s_ease-in-out_infinite] w-2/3" />
            </div>
            <span className="text-[10px] text-blue-600 font-medium">Çalışıyor</span>
          </div>
        )}
        {simStatus === "success" && (
          <div className="mt-2 flex items-center gap-1">
            <span className="text-emerald-500 text-xs">✓</span>
            <span className="text-[10px] text-emerald-600 font-medium">Başarılı</span>
          </div>
        )}
        {simStatus === "error" && (
          <div className="mt-2 flex items-center gap-1">
            <span className="text-red-500 text-xs">✗</span>
            <span className="text-[10px] text-red-600 font-medium">Hata</span>
          </div>
        )}
      </div>

      {data.nodeType === "condition" ? (
        <>
          <Handle
            type="source"
            position={Position.Right}
            id="true"
            className="!w-3 !h-3 !border-2 !border-white !top-[35%]"
            style={{ background: "#10b981" }}
          />
          <Handle
            type="source"
            position={Position.Right}
            id="false"
            className="!w-3 !h-3 !border-2 !border-white !top-[65%]"
            style={{ background: "#ef4444" }}
          />
          <span className="absolute right-[-28px] top-[29%] text-[9px] font-bold text-emerald-600">
            Evet
          </span>
          <span className="absolute right-[-32px] top-[59%] text-[9px] font-bold text-red-500">
            Hayır
          </span>
        </>
      ) : data.nodeType !== "end" ? (
        <Handle
          type="source"
          position={Position.Right}
          className="!w-3 !h-3 !border-2 !border-white"
          style={{ background: cfg.color }}
        />
      ) : null}
    </div>
  );
}

export default memo(FlowNodeComponent);
