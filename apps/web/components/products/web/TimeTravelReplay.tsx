"use client";

import { useMemo, useState } from "react";

interface ReplayFrame {
  t: number;             // ms from test start
  label: string;
  domSize: number;       // # of nodes
  network: number;       // pending requests
  console: "info" | "warn" | "error";
  consoleMsg?: string;
  isFailure?: boolean;
}

interface FailedTest {
  id: string;
  name: string;
  browser: string;
  duration: number;       // ms
  failedAt: number;       // ms (frame index target)
  reason: string;
  frames: ReplayFrame[];
}

const FAILED_TESTS: FailedTest[] = [
  {
    id: "checkout-3",
    name: "Checkout · Kart ile ödeme",
    browser: "Safari 17.4",
    duration: 4820,
    failedAt: 7,
    reason: "TypeError: Cannot read 'token' of undefined",
    frames: [
      { t: 0,    label: "Sayfa açıldı",                  domSize: 412,  network: 4, console: "info" },
      { t: 240,  label: "Login formu dolduruldu",        domSize: 418,  network: 0, console: "info" },
      { t: 580,  label: "Sepete gidildi",                domSize: 524,  network: 2, console: "info" },
      { t: 1100, label: "Adres seçildi",                 domSize: 612,  network: 1, console: "info" },
      { t: 1820, label: "Kart bilgileri girildi",        domSize: 678,  network: 0, console: "info" },
      { t: 2400, label: "3DS pop-up açıldı",             domSize: 712,  network: 3, console: "info" },
      { t: 3200, label: "3DS doğrulandı",                domSize: 720,  network: 1, console: "warn", consoleMsg: "Stripe webhook 800ms gecikti" },
      { t: 3680, label: "Kırılma anı",                   domSize: 718,  network: 1, console: "error", consoleMsg: "TypeError: Cannot read 'token' of undefined", isFailure: true },
      { t: 4100, label: "Hata sayfası gösterildi",       domSize: 220,  network: 0, console: "error" },
      { t: 4820, label: "Test sonlandı",                 domSize: 220,  network: 0, console: "error" },
    ],
  },
  {
    id: "search-2",
    name: "Arama · Otomatik tamamlama",
    browser: "Firefox 125",
    duration: 2140,
    failedAt: 4,
    reason: "Element not found: .suggestion-list",
    frames: [
      { t: 0,    label: "Sayfa açıldı",        domSize: 388, network: 2, console: "info" },
      { t: 320,  label: "Arama kutusu odaklandı", domSize: 388, network: 0, console: "info" },
      { t: 680,  label: "İlk harf yazıldı",     domSize: 392, network: 1, console: "info" },
      { t: 1280, label: "5 karakter yazıldı",   domSize: 396, network: 1, console: "warn", consoleMsg: "Suggestion API yavaşlıyor" },
      { t: 1820, label: "Kırılma anı",          domSize: 396, network: 1, console: "error", consoleMsg: "Selector .suggestion-list bulunamadı", isFailure: true },
      { t: 2140, label: "Test sonlandı",        domSize: 396, network: 0, console: "error" },
    ],
  },
  {
    id: "profile-1",
    name: "Profil · Avatar yükleme",
    browser: "Chrome 124",
    duration: 3280,
    failedAt: 5,
    reason: "Network timeout: PUT /api/avatar (10s)",
    frames: [
      { t: 0,    label: "Profil sayfası açıldı",  domSize: 502, network: 3, console: "info" },
      { t: 420,  label: "Avatar yükle tıklandı",  domSize: 510, network: 0, console: "info" },
      { t: 880,  label: "Dosya seçildi (2.4MB)",  domSize: 514, network: 0, console: "info" },
      { t: 1240, label: "Yükleme başladı",        domSize: 516, network: 1, console: "info" },
      { t: 2400, label: "İlerleme %47",           domSize: 516, network: 1, console: "warn", consoleMsg: "PUT /api/avatar yavaş" },
      { t: 3160, label: "Kırılma anı",            domSize: 516, network: 1, console: "error", consoleMsg: "Network timeout: PUT /api/avatar (10s)", isFailure: true },
      { t: 3280, label: "Test sonlandı",          domSize: 516, network: 0, console: "error" },
    ],
  },
];

function ScrubberMarker({ pct, isFailure }: { pct: number; isFailure?: boolean }) {
  return (
    <div
      className={`absolute top-0 h-full w-0.5 ${isFailure ? "bg-rose-500" : "bg-slate-600"}`}
      style={{ left: `${pct}%` }}
    />
  );
}

export function TimeTravelReplay() {
  const [activeId, setActiveId] = useState(FAILED_TESTS[0].id);
  const active = useMemo(() => FAILED_TESTS.find((t) => t.id === activeId)!, [activeId]);
  const [frameIdx, setFrameIdx] = useState(active.failedAt);
  const frame = active.frames[Math.min(frameIdx, active.frames.length - 1)];

  const switchTest = (id: string) => {
    const t = FAILED_TESTS.find((x) => x.id === id)!;
    setActiveId(id);
    setFrameIdx(t.failedAt);
  };

  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden h-[480px] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-rose-500 to-orange-600 flex items-center justify-center text-sm">
            🎬
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Time-Travel Replay</h2>
            <p className="text-[11px] text-slate-400">Kırılma anına git, DOM + network + console durumunu gör</p>
          </div>
        </div>
        <span className="text-[11px] px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-300 border border-rose-500/25">
          3 başarısız
        </span>
      </div>

      {/* Failed test selector */}
      <div className="px-5 pt-3 flex gap-2 overflow-x-auto pb-2 border-b border-slate-800">
        {FAILED_TESTS.map((t) => (
          <button
            key={t.id}
            onClick={() => switchTest(t.id)}
            className={`flex-shrink-0 text-left px-3 py-1.5 rounded-lg border text-[11px] transition-colors ${
              t.id === activeId
                ? "bg-rose-500/10 border-rose-500/30 text-white"
                : "bg-slate-800/40 border-slate-800 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            }`}
          >
            <div className="font-semibold truncate max-w-[160px]">{t.name}</div>
            <div className="text-[10px] opacity-80">{t.browser}</div>
          </button>
        ))}
      </div>

      {/* Replay viewer */}
      <div className="flex-1 px-5 py-4 flex flex-col gap-3 overflow-hidden">
        {/* Mock browser viewport */}
        <div className={`relative rounded-lg border overflow-hidden flex-1 min-h-0 ${
          frame.isFailure ? "border-rose-500/40 bg-rose-500/5" : "border-slate-700 bg-slate-950"
        }`}>
          <div className="absolute top-0 left-0 right-0 h-7 bg-slate-900/90 border-b border-slate-700 flex items-center px-3 gap-1.5">
            <span className="h-2 w-2 rounded-full bg-rose-400/70" />
            <span className="h-2 w-2 rounded-full bg-amber-400/70" />
            <span className="h-2 w-2 rounded-full bg-emerald-400/70" />
            <span className="ml-3 text-[10px] font-mono text-slate-500 truncate">
              t = {frame.t.toString().padStart(4, " ")}ms · {frame.label}
            </span>
          </div>
          <div className="h-full pt-7 flex items-center justify-center">
            {frame.isFailure ? (
              <div className="text-center px-4">
                <div className="text-4xl mb-2">⚠️</div>
                <div className="text-rose-300 text-sm font-semibold mb-1">Kırılma Anı</div>
                <div className="text-rose-400/80 text-[11px] font-mono">{frame.consoleMsg}</div>
              </div>
            ) : (
              <div className="text-center text-slate-500 text-xs">
                <div className="font-mono">{active.browser}</div>
                <div className="mt-1">Snapshot · {frame.domSize} DOM nodes</div>
              </div>
            )}
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-2">
          <div className="rounded-lg bg-slate-950 border border-slate-800 px-3 py-2">
            <div className="text-[10px] text-slate-500 uppercase tracking-wide">DOM</div>
            <div className="text-sm font-mono font-semibold text-white">{frame.domSize}</div>
          </div>
          <div className="rounded-lg bg-slate-950 border border-slate-800 px-3 py-2">
            <div className="text-[10px] text-slate-500 uppercase tracking-wide">Network</div>
            <div className={`text-sm font-mono font-semibold ${frame.network > 0 ? "text-amber-300" : "text-emerald-300"}`}>
              {frame.network} pending
            </div>
          </div>
          <div className="rounded-lg bg-slate-950 border border-slate-800 px-3 py-2">
            <div className="text-[10px] text-slate-500 uppercase tracking-wide">Console</div>
            <div className={`text-sm font-mono font-semibold ${
              frame.console === "error" ? "text-rose-400" :
              frame.console === "warn"  ? "text-amber-300" :
                                          "text-slate-300"
            }`}>{frame.console}</div>
          </div>
        </div>

        {/* Scrubber */}
        <div>
          <div className="relative h-2 rounded-full bg-slate-800 mb-2">
            <div
              className="absolute top-0 left-0 h-full rounded-full bg-gradient-to-r from-emerald-500 via-amber-400 to-rose-500"
              style={{ width: `${(frameIdx / (active.frames.length - 1)) * 100}%` }}
            />
            {active.frames.map((f, i) => (
              <ScrubberMarker
                key={i}
                pct={(i / (active.frames.length - 1)) * 100}
                isFailure={f.isFailure}
              />
            ))}
          </div>
          <input
            type="range"
            min={0}
            max={active.frames.length - 1}
            value={frameIdx}
            onChange={(e) => setFrameIdx(Number(e.target.value))}
            className="w-full accent-rose-500"
          />
          <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 mt-1">
            <span>0ms</span>
            <span>Kare {frameIdx + 1} / {active.frames.length}</span>
            <span>{active.duration}ms</span>
          </div>
        </div>
      </div>
    </div>
  );
}
