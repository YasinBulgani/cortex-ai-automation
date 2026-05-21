"use client";

import { type DragEvent } from "react";
import { NODE_CATEGORIES, NODE_CONFIGS, type FlowNodeType } from "./nodeTypes";

export function NodePalette() {
  function onDragStart(e: DragEvent, nodeType: FlowNodeType) {
    e.dataTransfer.setData("application/reactflow-type", nodeType);
    e.dataTransfer.effectAllowed = "move";
  }

  return (
    <div className="w-56 border-r border-slate-800 bg-slate-900 overflow-y-auto">
      <div className="p-3 border-b border-slate-800">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Düğümler
        </h3>
        <p className="text-[10px] text-slate-400 mt-0.5">Sürükleyip bırakın</p>
      </div>

      {NODE_CATEGORIES.map((cat) => (
        <div key={cat.name} className="p-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 px-1 mb-1.5">
            {cat.name}
          </p>
          <div className="space-y-1">
            {cat.types.map((t) => {
              const cfg = NODE_CONFIGS[t];
              return (
                <div
                  key={t}
                  draggable
                  onDragStart={(e) => onDragStart(e, t)}
                  className="flex items-center gap-2.5 rounded-lg px-2.5 py-2 cursor-grab active:cursor-grabbing border border-transparent hover:border-slate-800 hover:shadow-sm transition-all select-none"
                  style={{ background: cfg.bgColor + "80" }}
                >
                  <span
                    className="flex items-center justify-center w-8 h-8 rounded-lg text-sm shrink-0"
                    style={{ background: cfg.color + "20", border: `1px solid ${cfg.color}30` }}
                  >
                    {cfg.icon}
                  </span>
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-white truncate">{cfg.label}</div>
                    <div className="text-[10px] text-slate-400 truncate">{cfg.description}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
