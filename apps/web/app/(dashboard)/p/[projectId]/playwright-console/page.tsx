"use client";

import { useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { EmptyState } from "@/components/nexus/EmptyState";
import { cn } from "@/lib/utils";
import {
  usePlaywrightHealth,
  useCreateSession,
  useCloseSession,
  useNavigate,
  useScreenshot,
  useValidateSelectors,
  useDOMSnapshot,
  useVerifyHeal,
  useRunHealPipeline,
  useHealStats,
  type PlaywrightSession,
  type SelectorValidationItem,
  type VerifyHealResponse,
  type DOMSnapshotResponse,
  type DOMNode,
  type RunHealPipelineRequest,
} from "@/lib/hooks/use-playwright-mcp";
import {
  TAB_KEYS,
  TAB_LABELS,
  stabilityColor,
  confidenceColor,
  Spinner,
  RetryButton,
  PlaywrightUnavailable,
  type TabKey,
} from "./_components/helpers";

// ── Tab 1: Session & Navigation ──────────────────────────────────────

function SessionTab({
  activeSession,
  onSessionCreated,
}: {
  activeSession: PlaywrightSession | null;
  onSessionCreated: (sid: string) => void;
}) {
  const [url, setUrl] = useState("");
  const createSession = useCreateSession();
  const closeSession = useCloseSession();
  const sessionId = activeSession?.session_id ?? "";
  const navigate = useNavigate(sessionId);
  const queryClient = useQueryClient();
  const {
    data: screenshot,
    isLoading: ssLoading,
    refetch: refetchSs,
  } = useScreenshot(sessionId);

  const handleCreate = useCallback(() => {
    createSession.mutate(undefined, {
      onSuccess: (res) => onSessionCreated(res.session_id),
    });
  }, [createSession, onSessionCreated]);

  const handleNavigate = useCallback(() => {
    if (!url.trim() || !sessionId) return;
    const target = url.startsWith("http") ? url : `https://${url}`;
    navigate.mutate(
      { url: target },
      {
        onSuccess: () => {
          void refetchSs();
        },
      },
    );
  }, [url, sessionId, navigate, refetchSs]);

  const handleClose = useCallback(() => {
    if (!sessionId) return;
    closeSession.mutate(sessionId);
  }, [sessionId, closeSession]);

  const handleRefreshScreenshot = useCallback(() => {
    void queryClient.invalidateQueries({
      queryKey: ["playwright-mcp", "screenshot", sessionId],
    });
  }, [queryClient, sessionId]);

  if (!activeSession) {
    return (
      <div className="flex flex-col items-center gap-4 py-12">
        <EmptyState
          icon="🎭"
          title="Aktif oturum yok"
          description="Yeni bir browser oturumu başlatarak element kesfine baslayabilirsiniz"
        />
        <button
          type="button"
          onClick={handleCreate}
          disabled={createSession.isPending}
          className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50 transition-colors"
        >
          {createSession.isPending ? <Spinner /> : (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
          )}
          Yeni Oturum Başlat
        </button>
        {createSession.isError && (
          <p className="text-xs text-red-400">Oturum olusturulamadi. Tekrar deneyin.</p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* URL bar */}
      <div className="flex gap-2">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleNavigate()}
          placeholder="https://ornek.com"
          className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:border-blue-500 focus:outline-none"
        />
        <button
          type="button"
          onClick={handleNavigate}
          disabled={navigate.isPending || !url.trim()}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
        >
          {navigate.isPending ? <Spinner /> : "Git"}
        </button>
      </div>

      {navigate.isError && (
        <p className="text-xs text-red-400">Navigasyon basarisiz: {(navigate.error as Error).message}</p>
      )}

      {/* Session info */}
      <SectionCard
        title="Oturum Bilgisi"
        icon={
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        }
        right={
          <button
            type="button"
            onClick={handleClose}
            disabled={closeSession.isPending}
            className="rounded border border-red-500/30 bg-red-500/10 px-2 py-1 text-xs text-red-400 hover:bg-red-500/20 transition-colors"
          >
            {closeSession.isPending ? "Kapatiliyor..." : "Oturumu Kapat"}
          </button>
        }
      >
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-slate-500">ID:</span>{" "}
            <span className="text-slate-300 font-mono text-xs">{activeSession.session_id.slice(0, 12)}...</span>
          </div>
          <div>
            <span className="text-slate-500">Durum:</span>{" "}
            <span className={activeSession.status === "active" ? "text-emerald-400" : "text-red-400"}>
              {activeSession.status === "active" ? "Aktif" : "Kapalı"}
            </span>
          </div>
          <div>
            <span className="text-slate-500">URL:</span>{" "}
            <span className="text-blue-400 truncate">{activeSession.url ?? "—"}</span>
          </div>
          <div>
            <span className="text-slate-500">Baslik:</span>{" "}
            <span className="text-slate-300">{activeSession.title ?? "—"}</span>
          </div>
          <div className="col-span-2">
            <span className="text-slate-500">Olusturulma:</span>{" "}
            <span className="text-slate-300">{new Date(activeSession.created_at).toLocaleString("tr-TR")}</span>
          </div>
        </div>
      </SectionCard>

      {/* Screenshot */}
      <SectionCard
        title="Sayfa Görüntüsu"
        icon={
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        }
        right={
          <button
            type="button"
            onClick={handleRefreshScreenshot}
            className="flex items-center gap-1 rounded border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700 transition-colors"
          >
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Yenile
          </button>
        }
      >
        {ssLoading ? (
          <div className="flex items-center justify-center py-12">
            <Spinner className="h-6 w-6" />
          </div>
        ) : screenshot?.image_base64 ? (
          <div className="overflow-hidden rounded-lg border border-slate-700">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`data:image/${screenshot.format ?? "png"};base64,${screenshot.image_base64}`}
              alt="Sayfa görüntüsu"
              className="w-full"
            />
          </div>
        ) : (
          <p className="py-6 text-center text-sm text-slate-500">
            Henuz görüntü yok. Bir sayfaya gidin.
          </p>
        )}
      </SectionCard>
    </div>
  );
}

// ── Tab 2: Selector Validation ───────────────────────────────────────

function SelectorTab({ sessionId }: { sessionId: string }) {
  const [input, setInput] = useState("");
  const validate = useValidateSelectors(sessionId);
  const results = validate.data?.results;

  const handleValidate = useCallback(() => {
    const selectors = input
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    if (selectors.length === 0) return;
    validate.mutate({ selectors });
  }, [input, validate]);

  return (
    <div className="space-y-4">
      <SectionCard title="Selector Giriş">
        <div className="space-y-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={5}
            placeholder={"#login-btn\n.form-input[name='email']\ndata-testid=submit-button\n// Her satira bir selector yazin"}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white placeholder:text-slate-600 focus:border-blue-500 focus:outline-none resize-y"
          />
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleValidate}
              disabled={validate.isPending || !input.trim() || !sessionId}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              {validate.isPending ? <Spinner /> : "Dogrula"}
            </button>
            {!sessionId && <p className="text-xs text-amber-400">Oncelikle bir oturum baslatmaniz gerekiyor.</p>}
          </div>
          {validate.isError && (
            <div className="flex items-center gap-2">
              <p className="text-xs text-red-400">Dogrulama basarisiz.</p>
              <RetryButton onClick={handleValidate} />
            </div>
          )}
        </div>
      </SectionCard>

      {results && results.length > 0 && (
        <SectionCard title="Dogrulama Sonuçlari" noPad>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left">
                  <th className="px-4 py-2 text-xs font-semibold text-slate-400">Selector</th>
                  <th className="px-4 py-2 text-xs font-semibold text-slate-400 text-center">Bulundu</th>
                  <th className="px-4 py-2 text-xs font-semibold text-slate-400 text-center">Adet</th>
                  <th className="px-4 py-2 text-xs font-semibold text-slate-400 text-center">Gorunur</th>
                  <th className="px-4 py-2 text-xs font-semibold text-slate-400">Tag</th>
                  <th className="px-4 py-2 text-xs font-semibold text-slate-400 text-center">Stabilite</th>
                  <th className="px-4 py-2 text-xs font-semibold text-slate-400">Alternatifler</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r: SelectorValidationItem) => (
                  <tr key={r.selector} className="border-b border-slate-800/60 hover:bg-slate-800/30">
                    <td className="px-4 py-2 font-mono text-xs text-slate-300 max-w-[200px] truncate" title={r.selector}>
                      {r.selector}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {r.found ? (
                        <span className="text-emerald-400 text-base">&#10003;</span>
                      ) : (
                        <span className="text-red-400 text-base">&#10007;</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-center text-slate-300">{r.count}</td>
                    <td className="px-4 py-2 text-center">
                      {r.visible ? (
                        <span className="text-emerald-400 text-base">&#10003;</span>
                      ) : (
                        <span className="text-slate-600 text-base">&#10007;</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-xs text-slate-400">{r.tag ?? "—"}</td>
                    <td className="px-4 py-2 text-center">
                      <span className={cn("inline-block rounded-full border px-2 py-0.5 text-xs font-semibold", stabilityColor(r.stability_score))}>
                        {r.stability_score}/5
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      {r.alternatives && r.alternatives.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {r.alternatives.slice(0, 3).map((alt) => (
                            <span key={alt} className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
                              {alt}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-600">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      )}
    </div>
  );
}

// ── Tab 3: DOM Explorer ──────────────────────────────────────────────

const DOM_MAX_DEPTH = 20;

function DOMNodeView({
  node,
  depth,
  onSelect,
}: {
  node: DOMNode;
  depth: number;
  onSelect: (node: DOMNode) => void;
}) {
  const [expanded, setExpanded] = useState(depth < 2);

  if (depth >= DOM_MAX_DEPTH) {
    return (
      <div className="ml-3 border-l border-slate-800 pl-2 py-0.5 text-[10px] text-slate-600 italic">
        … (max derinlik {DOM_MAX_DEPTH})
      </div>
    );
  }
  const hasChildren = node.children && node.children.length > 0;

  const keyAttrs = ["id", "class", "data-testid", "role", "aria-label"];
  const displayAttrs = keyAttrs
    .filter((k) => node.attributes[k])
    .map((k) => `${k}="${node.attributes[k]}"`)
    .join(" ");

  return (
    <div className="ml-3 border-l border-slate-800">
      <div
        className="flex items-center gap-1 py-0.5 pl-2 hover:bg-slate-800/40 rounded cursor-pointer group"
        onClick={() => onSelect(node)}
        onKeyDown={(e) => e.key === "Enter" && onSelect(node)}
        role="button"
        tabIndex={0}
      >
        {hasChildren ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            className="flex items-center text-slate-600 hover:text-slate-400 shrink-0"
          >
            <svg
              className={cn("h-3 w-3 transition-transform", expanded && "rotate-90")}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        ) : (
          <span className="w-3 shrink-0" />
        )}
        <span className="text-blue-400 text-xs font-mono font-semibold">&lt;{node.tag}&gt;</span>
        {displayAttrs && (
          <span className="text-slate-500 text-[10px] font-mono truncate max-w-[300px]">
            {displayAttrs}
          </span>
        )}
        {node.text && (
          <span className="text-slate-600 text-[10px] truncate max-w-[150px] italic">
            &quot;{node.text.slice(0, 40)}&quot;
          </span>
        )}
      </div>
      {expanded && hasChildren && (
        <div>
          {node.children!.map((child, i) => (
            <DOMNodeView key={`${child.tag}-${i}`} node={child} depth={depth + 1} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  );
}

function DOMTab({ sessionId }: { sessionId: string }) {
  const [selector, setSelector] = useState("");
  const [maxDepth, setMaxDepth] = useState(5);
  const [selectedNode, setSelectedNode] = useState<DOMNode | null>(null);
  const domSnapshot = useDOMSnapshot(sessionId);
  const snapshotData = domSnapshot.data as DOMSnapshotResponse | undefined;

  const handleFetch = useCallback(() => {
    if (!sessionId) return;
    domSnapshot.mutate({
      selector: selector.trim() || undefined,
      max_depth: maxDepth,
    });
  }, [sessionId, selector, maxDepth, domSnapshot]);

  return (
    <div className="space-y-4">
      <SectionCard title="DOM Sorgusu">
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">
              CSS Selector (opsiyonel — bos birakilirsa tüm sayfa)
            </label>
            <input
              type="text"
              value={selector}
              onChange={(e) => setSelector(e.target.value)}
              placeholder="#main-content, .app-root"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white placeholder:text-slate-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 flex items-center justify-between text-xs font-medium text-slate-400">
              <span>Maksimum Derinlik</span>
              <span className="text-white font-semibold">{maxDepth}</span>
            </label>
            <input
              type="range"
              min={1}
              max={15}
              value={maxDepth}
              onChange={(e) => setMaxDepth(Number(e.target.value))}
              className="w-full accent-blue-500"
            />
            <div className="flex justify-between text-[10px] text-slate-600">
              <span>1</span>
              <span>15</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleFetch}
              disabled={domSnapshot.isPending || !sessionId}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              {domSnapshot.isPending ? <Spinner /> : "DOM Al"}
            </button>
            {!sessionId && <p className="text-xs text-amber-400">Oncelikle bir oturum baslatmaniz gerekiyor.</p>}
          </div>
          {domSnapshot.isError && (
            <div className="flex items-center gap-2">
              <p className="text-xs text-red-400">DOM alinamadi.</p>
              <RetryButton onClick={handleFetch} />
            </div>
          )}
        </div>
      </SectionCard>

      {snapshotData && (
        <div className="grid grid-cols-3 gap-4">
          {/* Tree */}
          <div className="col-span-2">
            <SectionCard
              title={`DOM Agaci (${snapshotData.node_count} node)`}
              icon={
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
                </svg>
              }
            >
              <div className="max-h-[500px] overflow-y-auto -ml-3">
                <DOMNodeView node={snapshotData.root} depth={0} onSelect={setSelectedNode} />
              </div>
            </SectionCard>
          </div>

          {/* Node detail */}
          <div className="col-span-1">
            <SectionCard title="Node Detay">
              {selectedNode ? (
                <div className="space-y-3">
                  <div>
                    <p className="text-xs font-semibold text-slate-400 mb-1">Tag</p>
                    <p className="text-sm text-blue-400 font-mono">&lt;{selectedNode.tag}&gt;</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-400 mb-1">Ozellikler</p>
                    <div className="space-y-1">
                      {Object.entries(selectedNode.attributes).length > 0 ? (
                        Object.entries(selectedNode.attributes).map(([k, v]) => (
                          <div key={k} className="flex gap-1 text-xs">
                            <span className="text-violet-400 font-mono shrink-0">{k}:</span>
                            <span className="text-slate-300 font-mono truncate" title={v}>
                              {v}
                            </span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-slate-600">Ozellik yok</p>
                      )}
                    </div>
                  </div>
                  {selectedNode.text && (
                    <div>
                      <p className="text-xs font-semibold text-slate-400 mb-1">Metin</p>
                      <p className="text-xs text-slate-300 italic">&quot;{selectedNode.text}&quot;</p>
                    </div>
                  )}
                  {selectedNode.suggested_selectors && selectedNode.suggested_selectors.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-slate-400 mb-1">Onerilen Selector&apos;lar</p>
                      <div className="space-y-1">
                        {selectedNode.suggested_selectors.map((s) => (
                          <div
                            key={s}
                            className="rounded bg-slate-800 px-2 py-1 font-mono text-[11px] text-emerald-400 cursor-pointer hover:bg-slate-700 transition-colors"
                            onClick={() => navigator.clipboard.writeText(s)}
                            title="Kopyalamak için tiklayin"
                          >
                            {s}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="py-4 text-center text-xs text-slate-500">
                  Detay gormek için soldaki agactan bir node secin.
                </p>
              )}
            </SectionCard>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Tab 4: Heal Verification + Pipeline ──────────────────────────────

function HealTab({ sessionId }: { sessionId: string }) {
  const [original, setOriginal] = useState("");
  const [healed, setHealed] = useState("");
  const [expectedTag, setExpectedTag] = useState("");
  const [expectedText, setExpectedText] = useState("");
  const [pipelineTestCaseId, setPipelineTestCaseId] = useState("");
  const [pipelineSelectors, setPipelineSelectors] = useState("");
  const verifyHeal = useVerifyHeal(sessionId);
  const result = verifyHeal.data as VerifyHealResponse | undefined;
  const runPipeline = useRunHealPipeline();
  const { data: healStats } = useHealStats();

  const handleVerify = useCallback(() => {
    if (!original.trim() || !healed.trim() || !sessionId) return;
    verifyHeal.mutate({
      original_selector: original.trim(),
      healed_selector: healed.trim(),
      expected_tag: expectedTag.trim() || undefined,
      expected_text: expectedText.trim() || undefined,
    });
  }, [original, healed, expectedTag, expectedText, sessionId, verifyHeal]);

  const handleRunPipeline = useCallback(() => {
    const selectors = pipelineSelectors
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((s) => ({ selector: s }));
    if (!pipelineTestCaseId.trim() || selectors.length === 0) return;
    const req: RunHealPipelineRequest = {
      test_case_id: pipelineTestCaseId.trim(),
      broken_selectors: selectors,
      session_id: sessionId || undefined,
    };
    runPipeline.mutate(req);
  }, [pipelineTestCaseId, pipelineSelectors, sessionId, runPipeline]);

  return (
    <div className="space-y-4">
      {/* Stats overview */}
      {healStats && (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-5">
          {[
            { label: "Pipeline", value: healStats.total_pipelines },
            { label: "İyileştirildi", value: healStats.total_selectors_healed, color: "text-emerald-400" },
            { label: "Başarısız", value: healStats.total_selectors_failed, color: "text-red-400" },
            { label: "Ortalama Güven", value: `${Math.round((healStats.avg_confidence ?? 0) * 100)}%`, color: "text-blue-400" },
            { label: "Ort. Süre", value: `${Math.round((healStats.avg_duration_ms ?? 0) / 1000)}s` },
          ].map(({ label, value, color }) => (
            <div key={label} className="rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-2 text-center">
              <p className="text-[10px] text-slate-500">{label}</p>
              <p className={`mt-0.5 text-lg font-bold ${color ?? "text-white"}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Run pipeline section */}
      <SectionCard title="AI Heal Pipeline">
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Test Case ID</label>
            <input
              type="text"
              value={pipelineTestCaseId}
              onChange={(e) => setPipelineTestCaseId(e.target.value)}
              placeholder="tc-abc123"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white placeholder:text-slate-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Bozuk Selector&apos;lar (her satıra bir tane)</label>
            <textarea
              rows={4}
              value={pipelineSelectors}
              onChange={(e) => setPipelineSelectors(e.target.value)}
              placeholder={"#eski-buton\n.kopuk-input[name='email']"}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white placeholder:text-slate-600 focus:border-blue-500 focus:outline-none resize-y"
            />
          </div>
          <button
            type="button"
            onClick={handleRunPipeline}
            disabled={runPipeline.isPending || !pipelineTestCaseId.trim() || !pipelineSelectors.trim()}
            className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50 transition-colors"
          >
            {runPipeline.isPending ? <Spinner /> : "Pipeline Çalıştır"}
          </button>
          {runPipeline.isError && (
            <p className="text-xs text-red-400">Pipeline başarısız: {(runPipeline.error as Error).message}</p>
          )}
        </div>
        {runPipeline.data && (
          <div className="mt-4 space-y-3">
            <div className="flex flex-wrap gap-3 text-xs">
              <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-emerald-300">
                {runPipeline.data.healed} iyileştirildi
              </span>
              <span className="rounded-full border border-red-500/20 bg-red-500/10 px-2 py-0.5 text-red-300">
                {runPipeline.data.failed} başarısız
              </span>
              <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-slate-300">
                {Math.round(runPipeline.data.duration_ms / 1000)}s
              </span>
            </div>
            <div className="space-y-2">
              {runPipeline.data.results.map((r, i) => (
                <div key={i} className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-[10px] font-semibold ${r.verified ? "text-emerald-400" : "text-amber-400"}`}>
                      {r.verified ? "✓ Doğrulandı" : "⚠ Doğrulanmadı"}
                    </span>
                    <span className="text-[10px] text-slate-500">{r.strategy} · %{Math.round(r.confidence * 100)}</span>
                  </div>
                  <div className="mt-1 grid grid-cols-2 gap-2 font-mono text-[11px]">
                    <span className="text-red-400 line-through truncate" title={r.original_selector}>{r.original_selector}</span>
                    <span className="text-emerald-400 truncate" title={r.healed_selector}>{r.healed_selector}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Heal Dogrulama">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-400">
                Orijinal Selector (bozuk)
              </label>
              <input
                type="text"
                value={original}
                onChange={(e) => setOriginal(e.target.value)}
                placeholder="#eski-buton-id"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white placeholder:text-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-400">
                Iyilestirilmis Selector (yeni)
              </label>
              <input
                type="text"
                value={healed}
                onChange={(e) => setHealed(e.target.value)}
                placeholder="[data-testid='submit-btn']"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white placeholder:text-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-400">
                Beklenen Tag (opsiyonel)
              </label>
              <input
                type="text"
                value={expectedTag}
                onChange={(e) => setExpectedTag(e.target.value)}
                placeholder="button"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white placeholder:text-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-400">
                Beklenen Metin (opsiyonel)
              </label>
              <input
                type="text"
                value={expectedText}
                onChange={(e) => setExpectedText(e.target.value)}
                placeholder="Giriş Yap"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white placeholder:text-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleVerify}
              disabled={verifyHeal.isPending || !original.trim() || !healed.trim() || !sessionId}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              {verifyHeal.isPending ? <Spinner /> : "Dogrula"}
            </button>
            {!sessionId && <p className="text-xs text-amber-400">Oncelikle bir oturum baslatmaniz gerekiyor.</p>}
          </div>
          {verifyHeal.isError && (
            <div className="flex items-center gap-2">
              <p className="text-xs text-red-400">Dogrulama basarisiz.</p>
              <RetryButton onClick={handleVerify} />
            </div>
          )}
        </div>
      </SectionCard>

      {result && (
        <SectionCard title="Dogrulama Sonuçu">
          <div className="space-y-4">
            {/* Status indicators */}
            <div className="grid grid-cols-3 gap-3">
              <div className={cn(
                "rounded-xl border p-3 text-center",
                result.original_found
                  ? "border-emerald-500/20 bg-emerald-500/5"
                  : "border-red-500/20 bg-red-500/5",
              )}>
                <p className="text-xs text-slate-400 mb-1">Orijinal Bulundu?</p>
                <p className={cn("text-lg font-bold", result.original_found ? "text-emerald-400" : "text-red-400")}>
                  {result.original_found ? "Evet" : "Hayir"}
                </p>
              </div>
              <div className={cn(
                "rounded-xl border p-3 text-center",
                result.healed_found
                  ? "border-emerald-500/20 bg-emerald-500/5"
                  : "border-red-500/20 bg-red-500/5",
              )}>
                <p className="text-xs text-slate-400 mb-1">Heal Bulundu?</p>
                <p className={cn("text-lg font-bold", result.healed_found ? "text-emerald-400" : "text-red-400")}>
                  {result.healed_found ? "Evet" : "Hayir"}
                </p>
              </div>
              <div className={cn(
                "rounded-xl border p-3 text-center",
                result.matches_expected
                  ? "border-emerald-500/20 bg-emerald-500/5"
                  : "border-amber-500/20 bg-amber-500/5",
              )}>
                <p className="text-xs text-slate-400 mb-1">Beklenenle Eslesme?</p>
                <p className={cn("text-lg font-bold", result.matches_expected ? "text-emerald-400" : "text-amber-400")}>
                  {result.matches_expected ? "Evet" : "Hayir"}
                </p>
              </div>
            </div>

            {/* Confidence gauge */}
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-4">
              <div className="flex items-end justify-between mb-2">
                <p className="text-sm font-medium text-slate-400">Guven Skoru</p>
                <span className={cn("text-3xl font-bold tabular-nums", confidenceColor(result.confidence))}>
                  {Math.round(result.confidence * 100)}%
                </span>
              </div>
              <div className="h-3 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    result.confidence >= 0.8 ? "bg-emerald-500" : result.confidence >= 0.5 ? "bg-amber-500" : "bg-red-500",
                  )}
                  style={{ width: `${Math.round(result.confidence * 100)}%` }}
                />
              </div>
            </div>

            {/* Recommendation */}
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-4">
              <p className="text-xs font-semibold text-slate-400 mb-1">Oneri</p>
              <p className="text-sm text-white">{result.recommendation}</p>
            </div>

            {/* Details */}
            {result.details && (
              <div className="grid grid-cols-2 gap-3 text-xs">
                {result.details.original_tag && (
                  <div>
                    <span className="text-slate-500">Orijinal Tag:</span>{" "}
                    <span className="font-mono text-slate-300">{result.details.original_tag}</span>
                  </div>
                )}
                {result.details.healed_tag && (
                  <div>
                    <span className="text-slate-500">Heal Tag:</span>{" "}
                    <span className="font-mono text-slate-300">{result.details.healed_tag}</span>
                  </div>
                )}
                {result.details.original_text && (
                  <div>
                    <span className="text-slate-500">Orijinal Metin:</span>{" "}
                    <span className="text-slate-300">{result.details.original_text}</span>
                  </div>
                )}
                {result.details.healed_text && (
                  <div>
                    <span className="text-slate-500">Heal Metin:</span>{" "}
                    <span className="text-slate-300">{result.details.healed_text}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </SectionCard>
      )}
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────

export default function PlaywrightConsolePage() {
  const { data: health, isLoading } = usePlaywrightHealth();
  const [activeTab, setActiveTab] = useState<TabKey>("session");
  const [activeSession, setActiveSession] = useState<PlaywrightSession | null>(null);
  const sessionId = activeSession?.session_id ?? "";

  const available = health?.status === "ok";

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="playwright-console-page">
      <PageHeader
        title="Playwright Konsol"
        description="Canlı browser oturumu ile element keşfet, selector doğrula ve heal pipeline çalıştır"
        badge={
          isLoading ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-emerald-400" />
          ) : available ? (
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
              AKTIF
            </span>
          ) : (
            <span className="rounded-full border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[10px] font-semibold text-red-400">
              BAĞLI DEĞİL
            </span>
          )
        }
      />

      {!isLoading && !available && (
        <SectionCard title="Playwright Bulunamadı">
          <p className="text-sm text-slate-300">
            Playwright MCP servisi şu anda kullanılamıyor. Backend&apos;de Playwright kurulu olduğundan emin olun.
          </p>
          <code className="mt-2 block rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs text-emerald-400 font-mono">
            pip install playwright && playwright install chromium
          </code>
        </SectionCard>
      )}

      {/* Tab navigation */}
      <div className="flex gap-1 border-b border-slate-800">
        {TAB_KEYS.map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            className={cn(
              "rounded-t-lg border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              activeTab === key
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-slate-400 hover:text-slate-200",
            )}
          >
            {TAB_LABELS[key]}
          </button>
        ))}
        {activeSession && (
          <span className="ml-auto self-center rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
            Oturum Aktif
          </span>
        )}
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "session" && (
          <SessionTab
            activeSession={activeSession}
            onSessionCreated={(sid) => {
              setActiveSession({ session_id: sid, status: "active", created_at: new Date().toISOString() } as PlaywrightSession);
            }}
          />
        )}
        {activeTab === "selectors" && <SelectorTab sessionId={sessionId} />}
        {activeTab === "dom" && <DOMTab sessionId={sessionId} />}
        {activeTab === "heal" && <HealTab sessionId={sessionId} />}
      </div>
    </div>
  );
}
