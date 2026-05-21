"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type React from "react";
import type { IdeFile, IdeFileKind } from "./types";

// ── IDE Workbench (IntelliJ benzeri otomasyon IDE) ──────────────────────────

const FILE_ICON: Record<IdeFileKind, string> = {
  feature: "🥒",
  steps:   "📘",
  data:    "🗃️",
  locator: "🎯",
  page:    "📄",
  config:  "⚙️",
};

const FOLDER_LABEL: Record<string, string> = {
  features:    "features",
  steps:       "steps",
  "test-data": "test-data",
  locators:    "locators",
  pages:       "pages",
  config:      "config",
};

// Basit syntax highlight — dile göre satır boyar
function highlightLine(line: string, language: IdeFile["language"]): React.ReactNode {
  if (language === "gherkin") {
    for (const kw of ["Feature:", "Scenario:", "Background:", "Examples:", "Given", "When", "Then", "And", "But"]) {
      const trimmed = line.trimStart();
      if (trimmed.startsWith(kw)) {
        const indent = line.slice(0, line.length - trimmed.length);
        const rest = trimmed.slice(kw.length);
        return (
          <>
            <span className="text-slate-600">{indent}</span>
            <span className="text-sky-400 font-semibold">{kw}</span>
            <span className="text-slate-200">{rest.replace(/"([^"]*)"/g, (m) => m)}</span>
          </>
        );
      }
    }
    return <span className="text-slate-400">{line}</span>;
  }
  if (language === "json") {
    return <span className="text-slate-300">{line.replace(/"([^"]*)":/g, '"$1":')}</span>;
  }
  if (language === "typescript") {
    const ts = line
      .replace(/(\b)(import|from|export|const|let|var|function|async|await|return|class|new|this|if|else|for|of|in)(\b)/g, "§KW§$2§/KW§");
    const parts = ts.split(/§KW§|§\/KW§/);
    return (
      <>
        {parts.map((p, i) => (
          <span key={i} className={i % 2 === 1 ? "text-violet-400 font-semibold" : "text-slate-300"}>
            {p}
          </span>
        ))}
      </>
    );
  }
  return <span className="text-slate-300">{line}</span>;
}

function IdeWorkbench({
  projectName,
  projectSlug,
  environment,
  ideFiles,
  activeIdePath,
  setActiveIdePath,
  setIdeFiles,
  expandedFolders,
  toggleFolder,
  consoleLines,
  ideTab,
  setIdeTab,
  ideRunning,
  runFromIde,
  stopFromIde,
  goBack,
  goFinish,
}: {
  projectName: string;
  projectSlug: string;
  environment: string;
  ideFiles: IdeFile[];
  activeIdePath: string | null;
  setActiveIdePath: (p: string | null) => void;
  setIdeFiles: React.Dispatch<React.SetStateAction<IdeFile[]>>;
  expandedFolders: Set<string>;
  toggleFolder: (f: string) => void;
  consoleLines: string[];
  ideTab: "console" | "problems" | "run";
  setIdeTab: (t: "console" | "problems" | "run") => void;
  ideRunning: boolean;
  runFromIde: () => void;
  stopFromIde: () => void;
  goBack: () => void;
  goFinish: () => void;
}) {
  const grouped = ideFiles.reduce<Record<string, IdeFile[]>>((acc, f) => {
    (acc[f.folder] ||= []).push(f);
    return acc;
  }, {});
  const folderOrder = ["features", "steps", "test-data", "locators", "pages", "config"];
  const activeFile = ideFiles.find((f) => f.path === activeIdePath) || null;

  const [dirtyDraft, setDirtyDraft] = useState<string | null>(null);

  useEffect(() => {
    setDirtyDraft(activeFile?.content ?? null);
  }, [activeFile?.path]); // eslint-disable-line react-hooks/exhaustive-deps

  function saveDraft() {
    if (!activeFile || dirtyDraft === null) return;
    setIdeFiles((prev) =>
      prev.map((f) => (f.path === activeFile.path ? { ...f, content: dirtyDraft } : f))
    );
  }

  const problemCount = ideFiles.filter((f) => f.kind === "steps" && /TODO: implement/.test(f.content)).length;

  const [isFullscreen, setIsFullscreen] = useState(false);

  // ESC ile tam ekrandan çık + tam ekranda body scroll kilidi
  useEffect(() => {
    if (!isFullscreen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [isFullscreen]);

  return (
    <div className="space-y-3">
      {/* Üst başlık */}
      <div>
        <h2 className="text-xl font-bold">💻 Otomasyon IDE — {projectName?.trim() || "Proje"}</h2>
        <p className="mt-1 text-sm text-slate-400">
          IntelliJ benzeri çalışma alanı. Feature, step definitions, test verisi, locator ve page object dosyaları
          otomatik üretildi. Dosyaları düzenle ve <span className="text-emerald-400 font-semibold">▶ Run</span> ile koştur.
        </p>
      </div>

      {/* IDE Çerçevesi */}
      <div
        className={
          isFullscreen
            ? "fixed inset-0 z-[9999] flex flex-col overflow-hidden border border-slate-800 bg-[#1e1f22] shadow-2xl"
            : "overflow-hidden rounded-2xl border border-slate-800 bg-[#1e1f22] shadow-2xl"
        }
      >
        {/* Toolbar / titlebar */}
        <div className="flex items-center gap-2 border-b border-slate-800 bg-[#2b2d30] px-3 py-1.5">
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-red-500/80" />
            <span className="h-3 w-3 rounded-full bg-amber-400/80" />
            <span className="h-3 w-3 rounded-full bg-emerald-500/80" />
          </div>
          <div className="mx-3 flex items-center gap-1.5 rounded-md bg-[#1e1f22] px-2 py-0.5 text-[11px] text-slate-400">
            <span>📁</span>
            <span>bgts-automation</span>
            <span className="text-slate-600">›</span>
            <span className="text-slate-300">{projectSlug}</span>
            <span className="text-slate-600">·</span>
            <span className="text-amber-300">{environment}</span>
          </div>
          <div className="ml-auto flex items-center gap-1.5">
            <button
              type="button"
              onClick={runFromIde}
              disabled={ideRunning}
              className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-40"
            >
              {ideRunning ? (
                <>
                  <svg className="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Running
                </>
              ) : (
                <>▶ Run</>
              )}
            </button>
            <button
              type="button"
              onClick={stopFromIde}
              disabled={!ideRunning}
              title={ideRunning ? "Koşumu durdur" : "Aktif koşum yok"}
              aria-label="Koşumu durdur"
              className="flex items-center gap-1.5 rounded-md bg-rose-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-rose-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            >
              <span className="inline-block h-2.5 w-2.5 rounded-[2px] bg-current" aria-hidden="true" />
              Stop
            </button>
            <button
              type="button"
              onClick={saveDraft}
              disabled={!activeFile || dirtyDraft === activeFile?.content}
              className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] text-slate-300 transition hover:border-slate-600 hover:text-white disabled:opacity-40"
              title="Kaydet"
            >
              💾 Save
            </button>
            <button
              type="button"
              onClick={() => setIsFullscreen((v) => !v)}
              className="flex items-center gap-1 rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] text-slate-300 transition hover:border-slate-600 hover:text-white"
              title={isFullscreen ? "Tam ekrandan çık (Esc)" : "Tam ekran yap"}
              aria-label={isFullscreen ? "Tam ekrandan çık" : "Tam ekran yap"}
            >
              {isFullscreen ? (
                <>
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 9V5H5m14 4V5h-4M9 15v4H5m14-4v4h-4" />
                  </svg>
                  Küçült
                </>
              ) : (
                <>
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 8V4h4M20 8V4h-4M4 16v4h4m12-4v4h-4" />
                  </svg>
                  Tam ekran
                </>
              )}
            </button>
          </div>
        </div>

        {/* Ana 3-paneli çerçeve */}
        <div
          className={`grid grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)] ${
            isFullscreen ? "min-h-0 flex-1" : "min-h-[540px]"
          }`}
        >
          {/* Sol panel — Project tree */}
          <aside className="border-r border-slate-800 bg-[#242528]">
            <div className="flex items-center justify-between px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              <span>Project</span>
              <span className="text-slate-600">{ideFiles.length}</span>
            </div>
            <div
              className={`overflow-y-auto px-1 pb-3 text-[12px] ${
                isFullscreen ? "max-h-[calc(100vh-110px)]" : "max-h-[520px]"
              }`}
            >
              {/* Root klasör */}
              <div className="flex items-center gap-1 px-2 py-1 text-slate-300">
                <span>📁</span>
                <span className="font-semibold">{projectSlug}</span>
              </div>
              {folderOrder
                .filter((folder) => grouped[folder]?.length)
                .map((folder) => {
                  const isOpen = expandedFolders.has(folder);
                  const files = grouped[folder];
                  return (
                    <div key={folder} className="ml-2">
                      <button
                        type="button"
                        onClick={() => toggleFolder(folder)}
                        className="flex w-full items-center gap-1 rounded px-1.5 py-0.5 text-left text-slate-400 transition hover:bg-slate-700/40 hover:text-white"
                      >
                        <span className="text-[9px] w-3">{isOpen ? "▾" : "▸"}</span>
                        <span>{isOpen ? "📂" : "📁"}</span>
                        <span>{FOLDER_LABEL[folder] || folder}</span>
                        <span className="ml-auto text-[9px] text-slate-600">{files.length}</span>
                      </button>
                      {isOpen && (
                        <ul className="ml-4 border-l border-slate-700/50">
                          {files.map((f) => {
                            const active = f.path === activeIdePath;
                            const isFeature = f.kind === "feature";
                            const disabled = !!f.disabled;
                            const toggleDisabled = (e: React.MouseEvent) => {
                              e.stopPropagation();
                              setIdeFiles((prev) =>
                                prev.map((it) =>
                                  it.path === f.path ? { ...it, disabled: !it.disabled } : it
                                )
                              );
                            };
                            return (
                              <li key={f.path} className="flex items-center gap-1">
                                {isFeature && (
                                  <input
                                    type="checkbox"
                                    checked={!disabled}
                                    onChange={() => {}}
                                    onClick={toggleDisabled}
                                    title={
                                      disabled
                                        ? "Atlandı — Run'a dahil etmek için işaretle"
                                        : "Çıkar: Run'a dahil etme"
                                    }
                                    aria-label={
                                      disabled ? "Run'a dahil et" : "Run'dan çıkar"
                                    }
                                    className="ml-1 h-3 w-3 cursor-pointer accent-emerald-500"
                                  />
                                )}
                                <button
                                  type="button"
                                  onClick={() => setActiveIdePath(f.path)}
                                  className={`flex w-full items-center gap-1.5 rounded px-2 py-0.5 text-left transition
                                    ${active
                                      ? "bg-blue-500/20 text-blue-200"
                                      : disabled
                                        ? "text-slate-600 hover:bg-slate-700/40 hover:text-slate-400"
                                        : "text-slate-400 hover:bg-slate-700/40 hover:text-white"}`}
                                >
                                  <span className="text-[12px]">{FILE_ICON[f.kind]}</span>
                                  <span
                                    className={`truncate ${
                                      isFeature && disabled ? "line-through opacity-60" : ""
                                    }`}
                                  >
                                    {f.name}
                                  </span>
                                </button>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  );
                })}
            </div>
          </aside>

          {/* Sağ — editör + konsol */}
          <div className="flex flex-col">
            {/* Editor sekmeleri */}
            <div className="flex items-center gap-1 overflow-x-auto border-b border-slate-800 bg-[#2b2d30] px-2 py-1">
              {activeFile ? (
                <div className="flex items-center gap-2 rounded-t-md bg-[#1e1f22] px-3 py-1 text-xs text-slate-200">
                  <span>{FILE_ICON[activeFile.kind]}</span>
                  <span>{activeFile.name}</span>
                  {dirtyDraft !== null && dirtyDraft !== activeFile.content && (
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-400" title="Kaydedilmemiş değişiklik" />
                  )}
                </div>
              ) : (
                <span className="px-3 py-1 text-xs text-slate-500">Sol panelden bir dosya seç</span>
              )}
              <div className="ml-auto flex items-center gap-2 text-[10px] text-slate-500">
                {activeFile && (
                  <>
                    <span>{activeFile.language.toUpperCase()}</span>
                    <span className="text-slate-600">·</span>
                    <span>{dirtyDraft?.split("\n").length ?? 0} lines</span>
                  </>
                )}
              </div>
            </div>

            {/* Kod editörü */}
            <div className="relative flex-1 overflow-auto bg-[#1e1f22] font-mono text-[12px] leading-5">
              {activeFile ? (
                <div className="flex min-h-full">
                  {/* Satır numaraları */}
                  <div className="sticky left-0 select-none border-r border-slate-800 bg-[#1e1f22] px-2 py-3 text-right text-slate-600">
                    {(dirtyDraft ?? "").split("\n").map((_, i) => (
                      <div key={i} className="tabular-nums">{i + 1}</div>
                    ))}
                  </div>
                  {/* İçerik: hem textarea (düzenleme) hem sahte highlight overlay */}
                  <div className="relative flex-1">
                    <pre className="pointer-events-none absolute inset-0 whitespace-pre px-3 py-3 text-slate-300">
                      {(dirtyDraft ?? "").split("\n").map((line, i) => (
                        <div key={i}>{highlightLine(line || " ", activeFile.language)}</div>
                      ))}
                    </pre>
                    <textarea
                      value={dirtyDraft ?? ""}
                      onChange={(e) => setDirtyDraft(e.target.value)}
                      spellCheck={false}
                      aria-label={`${activeFile.name} editor`}
                      title={`${activeFile.name} editor`}
                      placeholder="// dosya içeriği"
                      className="relative z-10 h-full min-h-[400px] w-full resize-none bg-transparent px-3 py-3 text-transparent caret-white outline-none selection:bg-blue-500/30"
                    />
                  </div>
                </div>
              ) : (
                <div className="flex h-full min-h-[400px] items-center justify-center text-sm text-slate-600">
                  Dosya seçilmedi
                </div>
              )}
            </div>

            {/* Alt konsol */}
            <div className="border-t border-slate-800 bg-[#1e1f22]">
              <div className="flex items-center gap-0 border-b border-slate-800 bg-[#2b2d30] px-2 text-[11px]">
                {(
                  [
                    { id: "console", label: "Console", badge: consoleLines.length },
                    { id: "problems", label: "Problems", badge: problemCount },
                    { id: "run", label: "Run", badge: ideRunning ? "●" : 0 },
                  ] as const
                ).map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setIdeTab(t.id)}
                    className={`flex items-center gap-1.5 border-t-2 px-3 py-1.5 transition
                      ${ideTab === t.id
                        ? "border-blue-500 text-white"
                        : "border-transparent text-slate-500 hover:text-slate-300"}`}
                  >
                    {t.label}
                    {t.badge !== 0 && (
                      <span className="rounded-full bg-slate-700 px-1.5 py-0 text-[9px]">{t.badge}</span>
                    )}
                  </button>
                ))}
                <span className="ml-auto text-[10px] text-slate-600">
                  {ideRunning ? "● RUNNING" : "○ READY"}
                </span>
              </div>
              <div
                className={`overflow-y-auto px-3 py-2 font-mono text-[11px] ${
                  isFullscreen ? "h-56" : "h-40"
                }`}
              >
                {ideTab === "console" && (
                  <>
                    {consoleLines.length === 0 ? (
                      <p className="text-slate-600">Konsol boş. ▶ Run ile başlat.</p>
                    ) : (
                      consoleLines.map((l, i) => {
                        const color = l.includes("[error]")
                          ? "text-red-400"
                          : l.includes("✓ ")
                            ? "text-emerald-400"
                            : l.includes("✗ ")
                              ? "text-red-400"
                              : l.startsWith("▶")
                                ? "text-amber-300"
                                : "text-slate-300";
                        return (
                          <div key={i} className={color}>
                            {l}
                          </div>
                        );
                      })
                    )}
                  </>
                )}
                {ideTab === "problems" && (
                  <>
                    {problemCount === 0 ? (
                      <p className="text-emerald-400">✓ Sorun yok. Tüm step definitions dolduruldu.</p>
                    ) : (
                      <p className="text-amber-300">
                        ⚠ {problemCount} step definitions TODO içeriyor. İlgili dosyada implement edilmesi gerekiyor.
                      </p>
                    )}
                  </>
                )}
                {ideTab === "run" && (
                  <p className="text-slate-400">
                    Konfigürasyon: <span className="text-slate-200">config/cucumber.cjs</span>
                    <br />
                    Komut: <code className="text-amber-300">npx cucumber-js --config config/cucumber.cjs</code>
                  </p>
                )}
              </div>
            </div>

            {/* Status bar */}
            <div className="flex items-center gap-3 border-t border-slate-800 bg-[#2b2d30] px-3 py-1 text-[10px] text-slate-500">
              <span>UTF-8</span>
              <span>LF</span>
              <span>{activeFile?.language.toUpperCase() ?? "-"}</span>
              <span className="ml-auto flex items-center gap-2">
                {(() => {
                  const feats = ideFiles.filter((f) => f.kind === "feature");
                  const enabled = feats.filter((f) => !f.disabled).length;
                  if (feats.length === 0) return null;
                  return (
                    <span
                      className={
                        enabled === 0
                          ? "rounded bg-rose-500/20 px-1.5 py-0.5 text-rose-300"
                          : enabled < feats.length
                            ? "rounded bg-amber-500/20 px-1.5 py-0.5 text-amber-300"
                            : "rounded bg-emerald-500/20 px-1.5 py-0.5 text-emerald-300"
                      }
                      title="Run'a dahil edilecek / toplam feature sayısı"
                    >
                      ▶ {enabled}/{feats.length} feature
                    </span>
                  );
                })()}
                <span>{ideFiles.length} files · Playwright + Cucumber</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Altta adım kontrolleri */}
      <div className="flex flex-wrap gap-3 pt-2">
        <button
          type="button"
          onClick={goBack}
          className="rounded-xl border border-slate-700 px-5 py-2.5 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
        >
          ← Kuruluma dön
        </button>
        <button
          type="button"
          onClick={goFinish}
          className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
        >
          Bitir & Projeye git →
        </button>
      </div>
    </div>
  );
}

export { IdeWorkbench };
