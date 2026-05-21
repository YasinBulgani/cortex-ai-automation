"use client";

import { useState } from "react";

type Tab = "network" | "console";

interface NetReq {
  method: string;
  url: string;
  status: number;
  ms: number;
  type: "xhr" | "doc" | "img" | "js";
}

interface ConsoleMsg {
  level: "error" | "warn" | "info";
  text: string;
  at: string;
  source: string;
}

const NETWORK: NetReq[] = [
  { method: "POST", url: "/api/auth/login",       status: 200, ms: 184,  type: "xhr" },
  { method: "GET",  url: "/api/me",               status: 200, ms: 42,   type: "xhr" },
  { method: "GET",  url: "/api/cart",             status: 200, ms: 67,   type: "xhr" },
  { method: "POST", url: "/api/checkout/session", status: 500, ms: 2104, type: "xhr" },
  { method: "GET",  url: "/api/payments/methods", status: 401, ms: 38,   type: "xhr" },
  { method: "GET",  url: "/assets/hero.webp",     status: 304, ms: 12,   type: "img" },
  { method: "POST", url: "/api/analytics/track",  status: 0,   ms: 30000, type: "xhr" },
];

const CONSOLE: ConsoleMsg[] = [
  { level: "error", at: "3.682s", text: "TypeError: Cannot read 'token' of undefined",                source: "checkout.js:142" },
  { level: "error", at: "3.685s", text: "Unhandled promise rejection: Network request failed",        source: "auth.ts:88"      },
  { level: "warn",  at: "3.421s", text: "[React] Each child should have unique key — CheckoutItems",  source: "CheckoutList.tsx:24" },
  { level: "warn",  at: "2.901s", text: "Deprecated API: document.execCommand('copy')",               source: "clipboard.ts:11" },
  { level: "info",  at: "1.205s", text: "Hydration completed in 482ms",                                source: "app.tsx"          },
];

function statusColor(s: number) {
  if (s === 0)               return "text-rose-400";
  if (s >= 500)              return "text-rose-400";
  if (s >= 400)              return "text-amber-400";
  if (s >= 300)              return "text-sky-400";
  return "text-emerald-400";
}

function levelStyle(l: ConsoleMsg["level"]) {
  if (l === "error") return { dot: "bg-rose-400",    text: "text-rose-300"   };
  if (l === "warn")  return { dot: "bg-amber-400",   text: "text-amber-300"  };
  return { dot: "bg-sky-400", text: "text-sky-300" };
}

export function NetworkConsoleInspector() {
  const [tab, setTab] = useState<Tab>("network");

  const failed   = NETWORK.filter((n) => n.status === 0 || n.status >= 400).length;
  const slowest  = Math.max(...NETWORK.map((n) => n.ms));
  const errors   = CONSOLE.filter((c) => c.level === "error").length;
  const warnings = CONSOLE.filter((c) => c.level === "warn").length;

  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-sky-500 to-cyan-600 flex items-center justify-center text-sm flex-shrink-0">
            📡
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-white truncate">Run Inspector</h2>
            <p className="text-[11px] text-slate-400 truncate">Son koşunun network + console akışı</p>
          </div>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/25">
          {failed} fail · {errors} err
        </span>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 px-3 pt-2 gap-1 text-[11px]">
        <button
          onClick={() => setTab("network")}
          className={`px-3 py-1.5 rounded-t-md font-medium ${
            tab === "network"
              ? "bg-slate-950 text-white border border-slate-800 border-b-slate-950"
              : "text-slate-500 hover:text-slate-300"
          }`}
        >
          Network <span className="ml-1 text-slate-500">{NETWORK.length}</span>
        </button>
        <button
          onClick={() => setTab("console")}
          className={`px-3 py-1.5 rounded-t-md font-medium ${
            tab === "console"
              ? "bg-slate-950 text-white border border-slate-800 border-b-slate-950"
              : "text-slate-500 hover:text-slate-300"
          }`}
        >
          Console <span className="ml-1 text-slate-500">{CONSOLE.length}</span>
        </button>
        <div className="ml-auto self-center text-[10px] text-slate-500">
          {tab === "network" ? `En yavaş ${slowest}ms` : `${errors} error · ${warnings} warning`}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto max-h-[280px]">
        {tab === "network" ? (
          <table className="w-full text-[11px]">
            <thead className="sticky top-0 bg-slate-900 text-slate-500">
              <tr className="text-left">
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Method</th>
                <th className="px-3 py-2 font-medium">URL</th>
                <th className="px-3 py-2 font-medium text-right">Süre</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {NETWORK.map((n, i) => (
                <tr key={i} className="border-t border-slate-800/60 hover:bg-slate-800/40">
                  <td className={`px-3 py-1.5 font-bold ${statusColor(n.status)}`}>
                    {n.status === 0 ? "TIMEOUT" : n.status}
                  </td>
                  <td className="px-3 py-1.5 text-slate-400">{n.method}</td>
                  <td className="px-3 py-1.5 text-slate-200 truncate max-w-[200px]" title={n.url}>{n.url}</td>
                  <td className={`px-3 py-1.5 text-right ${n.ms > 1000 ? "text-amber-300" : "text-slate-400"}`}>
                    {n.ms >= 1000 ? `${(n.ms / 1000).toFixed(1)}s` : `${n.ms}ms`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <ul className="divide-y divide-slate-800/60">
            {CONSOLE.map((c, i) => {
              const s = levelStyle(c.level);
              return (
                <li key={i} className="px-3 py-2 flex items-start gap-2.5 hover:bg-slate-800/40">
                  <span className={`mt-1 h-1.5 w-1.5 rounded-full ${s.dot} shrink-0`} />
                  <div className="min-w-0 flex-1">
                    <p className={`text-xs font-mono ${s.text} break-words`}>{c.text}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      {c.at} · <span className="font-mono">{c.source}</span>
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
        <span>Run #1284 · 3.682s'de kırıldı</span>
        <button className="text-sky-400 hover:underline">HAR indir →</button>
      </div>
    </div>
  );
}
