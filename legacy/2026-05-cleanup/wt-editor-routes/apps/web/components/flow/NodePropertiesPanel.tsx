"use client";

import { type Node } from "reactflow";
import { NODE_CONFIGS } from "./nodeTypes";
import type { FlowNodeData } from "./FlowNode";

interface Props {
  node: Node<FlowNodeData>;
  onChange: (id: string, data: Partial<FlowNodeData>) => void;
  onDelete: (id: string) => void;
  onClose: () => void;
}

export function NodePropertiesPanel({ node, onChange, onDelete, onClose }: Props) {
  const cfg = NODE_CONFIGS[node.data.nodeType];
  if (!cfg) return null;

  const updateConfig = (key: string, value: unknown) => {
    onChange(node.id, {
      ...node.data,
      config: { ...node.data.config, [key]: value },
    });
  };

  return (
    <div className="w-72 border-l border-slate-800 bg-slate-900 overflow-y-auto flex flex-col">
      <div className="flex items-center justify-between p-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span
            className="flex items-center justify-center w-7 h-7 rounded-lg text-sm"
            style={{ background: cfg.color + "22" }}
          >
            {cfg.icon}
          </span>
          <span className="text-sm font-semibold" style={{ color: cfg.color }}>
            {cfg.label}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white transition-colors text-lg leading-none"
        >
          ×
        </button>
      </div>

      <div className="flex-1 p-3 space-y-4">
        <Field label="Düğüm Adı">
          <input
            type="text"
            value={node.data.label}
            onChange={(e) => onChange(node.id, { label: e.target.value })}
            placeholder="Düğüm adı"
            className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/40"
          />
        </Field>

        {node.data.nodeType === "trigger" && (
          <>
            <Field label="Tetikleyici Tipi">
              <select
                value={(node.data.config.triggerType as string) || "manual"}
                onChange={(e) => updateConfig("triggerType", e.target.value)}
                title="Tetikleyici tipi"
                className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white"
              >
                <option value="manual">Manuel</option>
                <option value="cron">Zamanlama (Cron)</option>
                <option value="webhook">Webhook</option>
                <option value="event">Olay Tabanlı</option>
              </select>
            </Field>
            {(node.data.config.triggerType as string) === "cron" && (
              <Field label="Cron İfadesi">
                <input
                  type="text"
                  value={(node.data.config.cron as string) || ""}
                  onChange={(e) => updateConfig("cron", e.target.value)}
                  placeholder="*/5 * * * *"
                  className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                />
              </Field>
            )}
          </>
        )}

        {node.data.nodeType === "http_request" && (
          <>
            <Field label="Metod">
              <select
                value={(node.data.config.method as string) || "GET"}
                onChange={(e) => updateConfig("method", e.target.value)}
                title="HTTP metod"
                className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white"
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="DELETE">DELETE</option>
                <option value="PATCH">PATCH</option>
              </select>
            </Field>
            <Field label="URL">
              <input
                type="text"
                value={(node.data.config.url as string) || ""}
                onChange={(e) => updateConfig("url", e.target.value)}
                placeholder="https://api.example.com/..."
                className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/40"
              />
            </Field>
          </>
        )}

        {node.data.nodeType === "condition" && (
          <>
            <Field label="Alan">
              <input
                type="text"
                value={(node.data.config.field as string) || ""}
                onChange={(e) => updateConfig("field", e.target.value)}
                placeholder="data.status"
                className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/40"
              />
            </Field>
            <Field label="Operatör">
              <select
                value={(node.data.config.operator as string) || "equals"}
                onChange={(e) => updateConfig("operator", e.target.value)}
                title="Operatör"
                className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white"
              >
                <option value="equals">Eşittir (==)</option>
                <option value="not_equals">Eşit Değildir (!=)</option>
                <option value="contains">İçerir</option>
                <option value="gt">Büyüktür (&gt;)</option>
                <option value="lt">Küçüktür (&lt;)</option>
                <option value="exists">Mevcut</option>
              </select>
            </Field>
            <Field label="Değer">
              <input
                type="text"
                value={(node.data.config.value as string) || ""}
                onChange={(e) => updateConfig("value", e.target.value)}
                placeholder="success"
                className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/40"
              />
            </Field>
          </>
        )}

        {node.data.nodeType === "delay" && (
          <Field label="Bekleme Süresi">
            <div className="flex gap-2">
              <input
                type="number"
                min={0}
                value={(node.data.config.duration as number) || 1000}
                onChange={(e) => updateConfig("duration", Number(e.target.value))}
                placeholder="1000"
                className="flex-1 rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/40"
              />
              <select
                value={(node.data.config.unit as string) || "ms"}
                onChange={(e) => updateConfig("unit", e.target.value)}
                title="Birim"
                className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1.5 text-sm text-white"
              >
                <option value="ms">ms</option>
                <option value="s">saniye</option>
                <option value="m">dakika</option>
              </select>
            </div>
          </Field>
        )}

        {node.data.nodeType === "scenario" && (
          <Field label="Senaryo Adı">
            <input
              type="text"
              value={(node.data.config.scenarioName as string) || ""}
              onChange={(e) => updateConfig("scenarioName", e.target.value)}
              placeholder="Giriş testi…"
              className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/40"
            />
          </Field>
        )}

        {node.data.nodeType === "notification" && (
          <>
            <Field label="Kanal">
              <select
                value={(node.data.config.channel as string) || "email"}
                onChange={(e) => updateConfig("channel", e.target.value)}
                title="Bildirim kanalı"
                className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white"
              >
                <option value="email">E-posta</option>
                <option value="slack">Slack</option>
                <option value="teams">Teams</option>
                <option value="webhook">Webhook</option>
              </select>
            </Field>
            <Field label="Mesaj">
              <textarea
                value={(node.data.config.message as string) || ""}
                onChange={(e) => updateConfig("message", e.target.value)}
                placeholder="Test sonuçları..."
                rows={3}
                className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/40"
              />
            </Field>
          </>
        )}

        {node.data.nodeType === "transform" && (
          <Field label="İfade">
            <textarea
              value={(node.data.config.expression as string) || ""}
              onChange={(e) => updateConfig("expression", e.target.value)}
              placeholder="data.map(d => d.result)"
              rows={4}
              className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white font-mono resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/40"
            />
          </Field>
        )}

        {node.data.nodeType === "database" && (
          <>
            <Field label="Veritabanı">
              <select
                value={(node.data.config.dbType as string) || "postgresql"}
                onChange={(e) => updateConfig("dbType", e.target.value)}
                title="Veritabanı tipi"
                className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white"
              >
                <option value="postgresql">PostgreSQL</option>
                <option value="mysql">MySQL</option>
                <option value="mongodb">MongoDB</option>
                <option value="redis">Redis</option>
              </select>
            </Field>
            <Field label="Sorgu">
              <textarea
                value={(node.data.config.query as string) || ""}
                onChange={(e) => updateConfig("query", e.target.value)}
                placeholder="SELECT * FROM ..."
                rows={4}
                className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white font-mono resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/40"
              />
            </Field>
          </>
        )}

        {node.data.nodeType === "loop" && (
          <Field label="İterasyon Sayısı">
            <input
              type="number"
              min={1}
              value={(node.data.config.iterations as number) || 1}
              onChange={(e) => updateConfig("iterations", Number(e.target.value))}
              placeholder="1"
              className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/40"
            />
          </Field>
        )}
      </div>

      <div className="p-3 border-t border-slate-800">
        <button
          onClick={() => onDelete(node.id)}
          className="w-full rounded-md bg-red-50 border border-red-200 text-red-600 text-sm py-1.5 hover:bg-red-100 transition-colors dark:bg-red-950 dark:border-red-800 "
        >
          Düğümü Sil
        </button>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <span className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
        {label}
      </span>
      {children}
    </div>
  );
}
