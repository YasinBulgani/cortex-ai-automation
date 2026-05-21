"use client";

import { useState } from "react";

interface ExtensionAction {
  icon: string;
  label: string;
  hint: string;
}

const ACTIONS: ExtensionAction[] = [
  { icon: "🖱️", label: "Sağ Tık → Test", hint: "Herhangi bir element için anında test" },
  { icon: "🎙️", label: "Recorder",       hint: "Akışı kaydet, otomatik test yaz" },
  { icon: "🔍", label: "Locator İncele",  hint: "Element ne kadar dayanıklı, AI skoru" },
  { icon: "📋", label: "Snapshot Al",     hint: "Mevcut DOM'u baseline olarak kaydet" },
];

const BROWSERS = [
  { name: "Chrome",  installed: true,  version: "1.4.2" },
  { name: "Firefox", installed: true,  version: "1.4.2" },
  { name: "Edge",    installed: true,  version: "1.4.2" },
  { name: "Safari",  installed: false, version: "—" },
];

export function BrowserExtensionStatus() {
  const [connected, setConnected] = useState(true);

  return (
    <div className="rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-emerald-950/20 border border-emerald-500/20 p-5">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-lg">
            🔌
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              Browser Eklentisi
              <span className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full ${
                connected
                  ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                  : "bg-slate-800 text-slate-400 border border-slate-700"
              }`}>
                <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-400 animate-pulse" : "bg-slate-500"}`} />
                {connected ? "Bağlı" : "Bağlı değil"}
              </span>
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">Test yazmak için IDE'ye değil tarayıcına git</p>
          </div>
        </div>
        <button
          onClick={() => setConnected((c) => !c)}
          className="text-[11px] text-slate-400 hover:text-white"
        >
          {connected ? "Bağlantıyı Kes" : "Yeniden Bağla"}
        </button>
      </div>

      {/* Live activity */}
      {connected && (
        <div className="rounded-lg bg-emerald-500/5 border border-emerald-500/20 px-3 py-2.5 mb-4">
          <div className="flex items-center gap-2 text-[11px]">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-emerald-300 font-mono">checkout.example.com</span>
            <span className="text-slate-500">·</span>
            <span className="text-slate-400">47 element izleniyor</span>
            <span className="text-slate-500">·</span>
            <span className="text-slate-400">3 kayıt aktif</span>
          </div>
        </div>
      )}

      {/* Actions grid */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        {ACTIONS.map((a) => (
          <button
            key={a.label}
            disabled={!connected}
            className="text-left rounded-lg bg-slate-900/60 border border-slate-800 px-3 py-2.5 hover:bg-slate-800 hover:border-emerald-500/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed group"
          >
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-base">{a.icon}</span>
              <span className="text-[12px] font-semibold text-white group-hover:text-emerald-300">{a.label}</span>
            </div>
            <p className="text-[10px] text-slate-500 leading-tight">{a.hint}</p>
          </button>
        ))}
      </div>

      {/* Browser support */}
      <div>
        <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Tarayıcı Desteği</p>
        <div className="grid grid-cols-4 gap-2">
          {BROWSERS.map((b) => (
            <div
              key={b.name}
              className={`rounded-lg border px-2 py-2 text-center ${
                b.installed
                  ? "bg-emerald-500/5 border-emerald-500/20"
                  : "bg-slate-900/40 border-slate-800"
              }`}
            >
              <div className={`text-[11px] font-semibold ${b.installed ? "text-white" : "text-slate-500"}`}>
                {b.name}
              </div>
              <div className={`text-[10px] font-mono mt-0.5 ${b.installed ? "text-emerald-400" : "text-slate-600"}`}>
                {b.installed ? `v${b.version}` : "yakında"}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer CTA */}
      <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between">
        <span className="text-[11px] text-slate-500">
          Bu sprint: <span className="text-emerald-300 font-semibold">38 test</span> tarayıcıdan üretildi
        </span>
        <button className="text-[11px] text-emerald-400 hover:text-emerald-300 font-semibold">
          Eklentiyi İndir →
        </button>
      </div>
    </div>
  );
}
