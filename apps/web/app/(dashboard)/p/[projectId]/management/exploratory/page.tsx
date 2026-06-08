"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouteParam } from "@/lib/use-route-param";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import {
  useExplorationSessions,
  useCreateExplorationSession,
  useUpdateExplorationSession,
  useAddExplorationNote,
  useDeleteExplorationNote,
  useDeleteExplorationSession,
  type ExplorationSession,
  type ExplorationNoteKind,
} from "@/lib/hooks/use-management";
import { PageErrorBoundary } from "../_components/PageErrorBoundary";

const KIND_META: Record<ExplorationNoteKind, { label: string; icon: string; cls: string }> = {
  note:     { label: "Not",   icon: "📝", cls: "text-fg-muted" },
  idea:     { label: "Fikir", icon: "💡", cls: "text-blue-400" },
  bug:      { label: "Bug",   icon: "🐛", cls: "text-red-400" },
  question: { label: "Soru",  icon: "❓", cls: "text-amber-400" },
  risk:     { label: "Risk",  icon: "⚠️", cls: "text-orange-400" },
};

const STATUS_META: Record<string, { label: string; dot: string }> = {
  planned:   { label: "Planlandı", dot: "bg-slate-500" },
  active:    { label: "Aktif",     dot: "bg-blue-500 animate-pulse" },
  paused:    { label: "Duraklatıldı", dot: "bg-amber-500" },
  completed: { label: "Tamamlandı", dot: "bg-emerald-500/70" },
  aborted:   { label: "İptal",     dot: "bg-red-500/60" },
};

function fmtDuration(totalSec: number): string {
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  return [h, m, s].map(n => String(n).padStart(2, "0")).join(":");
}

const INP = "w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-disabled outline-none focus:border-pink-500/40";

// ── Create form ──────────────────────────────────────────────────────────────

function NewSessionForm({ projectId, onCreated }: { projectId: string; onCreated: (s: ExplorationSession) => void }) {
  const create = useCreateExplorationSession(projectId);
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [charter, setCharter] = useState("");
  const [areas, setAreas] = useState("");
  const [timebox, setTimebox] = useState(60);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    const s = await create.mutateAsync({ title: title.trim(), charter: charter.trim() || null, areas: areas.trim() || null, timebox_minutes: timebox });
    setTitle(""); setCharter(""); setAreas(""); setTimebox(60); setOpen(false);
    onCreated(s);
  };

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="w-full rounded-lg border border-dashed border-border px-3 py-2 text-[12px] font-semibold text-fg-muted hover:border-pink-500/40 hover:text-fg">
        + Yeni Keşif Oturumu
      </button>
    );
  }
  return (
    <form onSubmit={submit} className="space-y-2 rounded-lg border border-border bg-surface-raised p-3">
      <input autoFocus value={title} onChange={e => setTitle(e.target.value)} placeholder="Oturum başlığı *" className={INP} />
      <textarea value={charter} onChange={e => setCharter(e.target.value)} rows={2} placeholder="Charter — neyi, neden keşfedeceksiniz?" className={`${INP} resize-none`} />
      <input value={areas} onChange={e => setAreas(e.target.value)} placeholder="Hedef alan / özellik" className={INP} />
      <div className="flex items-center gap-2">
        <label className="text-[11px] text-fg-subtle">Süre (dk)</label>
        <input type="number" min={5} max={480} value={timebox} onChange={e => setTimebox(Number(e.target.value))} className={`${INP} w-24`} />
      </div>
      <div className="flex justify-end gap-2">
        <button type="button" onClick={() => setOpen(false)} className="rounded-lg px-3 py-1.5 text-[12px] text-fg-subtle hover:text-fg">İptal</button>
        <button type="submit" disabled={create.isPending} className="rounded-lg bg-pink-600 px-3 py-1.5 text-[12px] font-semibold text-white hover:opacity-90 disabled:opacity-50">Oluştur</button>
      </div>
    </form>
  );
}

// ── Session detail ─────────────────────────────────────────────────────────────

function SessionDetail({ projectId, session }: { projectId: string; session: ExplorationSession }) {
  const update = useUpdateExplorationSession(projectId);
  const addNote = useAddExplorationNote(projectId);
  const delNote = useDeleteExplorationNote(projectId);

  const [noteKind, setNoteKind] = useState<ExplorationNoteKind>("note");
  const [noteText, setNoteText] = useState("");

  // Local ticking timer: base elapsed + seconds since the session went active locally.
  const [tick, setTick] = useState(0);
  const activeSince = useRef<number | null>(null);
  const isActive = session.status === "active";

  useEffect(() => {
    if (isActive) {
      activeSince.current = Date.now();
      const iv = setInterval(() => setTick(t => t + 1), 1000);
      return () => clearInterval(iv);
    }
    activeSince.current = null;
    setTick(0);
  }, [isActive, session.id]);

  const liveElapsed = session.elapsed_seconds + (isActive && activeSince.current ? Math.floor((Date.now() - activeSince.current) / 1000) : 0);
  // keep `tick` referenced so the display re-renders each second
  void tick;

  const timeboxSec = session.timebox_minutes * 60;
  const overTimebox = liveElapsed > timeboxSec;

  const persistElapsed = () => session.elapsed_seconds + (activeSince.current ? Math.floor((Date.now() - activeSince.current) / 1000) : 0);

  const start = () => update.mutate({ sessionId: session.id, status: "active" });
  const pause = () => update.mutate({ sessionId: session.id, status: "paused", elapsed_seconds: persistElapsed() });
  const complete = () => update.mutate({ sessionId: session.id, status: "completed", elapsed_seconds: persistElapsed() });

  const submitNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!noteText.trim()) return;
    await addNote.mutateAsync({ sessionId: session.id, kind: noteKind, text: noteText.trim() });
    setNoteText("");
  };

  const notes = useMemo(() => [...(session.notes ?? [])].reverse(), [session.notes]);
  const bugCount = (session.notes ?? []).filter(n => n.kind === "bug").length;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-border px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-[16px] font-semibold text-fg">{session.title}</h2>
            {session.areas && <p className="mt-0.5 text-[12px] text-fg-muted">🎯 {session.areas}</p>}
          </div>
          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${STATUS_META[session.status]?.dot ?? "bg-slate-500"}`} />
            <span className="text-[12px] text-fg-muted">{STATUS_META[session.status]?.label ?? session.status}</span>
          </div>
        </div>
        {session.charter && (
          <p className="mt-2 rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[12px] text-fg-muted">{session.charter}</p>
        )}

        {/* Timer + controls */}
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <div className={`font-mono text-[24px] font-bold tabular-nums ${overTimebox ? "text-red-400" : "text-fg"}`}>
            {fmtDuration(liveElapsed)}
          </div>
          <span className="text-[11px] text-fg-subtle">/ {session.timebox_minutes} dk timebox{overTimebox ? " — aşıldı" : ""}</span>
          <div className="ml-auto flex gap-2">
            {session.status !== "active" && session.status !== "completed" && (
              <button onClick={start} className="rounded-lg bg-blue-600 px-3 py-1.5 text-[12px] font-semibold text-white hover:opacity-90">▶ {session.status === "paused" ? "Devam" : "Başlat"}</button>
            )}
            {session.status === "active" && (
              <button onClick={pause} className="rounded-lg bg-amber-600 px-3 py-1.5 text-[12px] font-semibold text-white hover:opacity-90">⏸ Duraklat</button>
            )}
            {session.status !== "completed" && (
              <button onClick={complete} className="rounded-lg border border-border px-3 py-1.5 text-[12px] font-semibold text-fg-muted hover:text-fg">✓ Bitir</button>
            )}
          </div>
        </div>
        {bugCount > 0 && (
          <div className="mt-2 flex items-center gap-2 text-[11px] text-red-400">
            🐛 {bugCount} bug yakalandı
            <Link href={`/p/${projectId}/management/defects`} className="underline hover:text-red-300">Defektlere git</Link>
          </div>
        )}
      </div>

      {/* Note composer */}
      <form onSubmit={submitNote} className="border-b border-border px-5 py-3">
        <div className="flex gap-1.5">
          {(Object.keys(KIND_META) as ExplorationNoteKind[]).map(k => (
            <button key={k} type="button" onClick={() => setNoteKind(k)}
              className={`rounded-md px-2 py-1 text-[11px] font-semibold transition-colors ${noteKind === k ? "bg-surface-overlay text-fg ring-1 ring-pink-500/40" : "text-fg-subtle hover:text-fg"}`}>
              {KIND_META[k].icon} {KIND_META[k].label}
            </button>
          ))}
        </div>
        <div className="mt-2 flex gap-2">
          <input value={noteText} onChange={e => setNoteText(e.target.value)} placeholder="Gözlem, fikir veya bug ekleyin… (Enter)" className={INP} />
          <button type="submit" disabled={addNote.isPending || !noteText.trim()} className="shrink-0 rounded-lg bg-pink-600 px-4 py-2 text-[12px] font-semibold text-white hover:opacity-90 disabled:opacity-50">Ekle</button>
        </div>
      </form>

      {/* Note log */}
      <div className="flex-1 overflow-y-auto px-5 py-3">
        {notes.length === 0 ? (
          <div className="py-12 text-center text-[12px] text-fg-subtle">Henüz not yok. Keşfederken gözlemlerinizi buraya kaydedin.</div>
        ) : (
          <ul className="space-y-2">
            {notes.map(n => {
              const m = KIND_META[n.kind] ?? KIND_META.note;
              return (
                <li key={n.id} className="group flex items-start gap-2.5 rounded-lg border border-border bg-surface-raised px-3 py-2">
                  <span className="shrink-0 text-[14px]" title={m.label}>{m.icon}</span>
                  <div className="min-w-0 flex-1">
                    <p className={`text-[13px] ${n.kind === "bug" ? "text-fg" : "text-fg-muted"}`}>{n.text}</p>
                    <p className="mt-0.5 text-[10px] text-fg-disabled">{new Date(n.ts).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })} · <span className={m.cls}>{m.label}</span></p>
                  </div>
                  <button onClick={() => delNote.mutate({ sessionId: session.id, noteId: n.id })}
                    className="shrink-0 text-[12px] text-fg-disabled opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100" aria-label="Notu sil">✕</button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

// ── Page body ──────────────────────────────────────────────────────────────────

function ExploratoryBody({ projectId }: { projectId: string }) {
  const { data: sessions = [], isLoading } = useExplorationSessions(projectId);
  const delSession = useDeleteExplorationSession(projectId);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Auto-select first session when list loads / selection becomes stale
  useEffect(() => {
    if (sessions.length === 0) { setSelectedId(null); return; }
    if (!selectedId || !sessions.some(s => s.id === selectedId)) {
      setSelectedId(sessions[0].id);
    }
  }, [sessions, selectedId]);

  const selected = sessions.find(s => s.id === selectedId) ?? null;

  return (
    <div className="flex h-full">
      {/* List */}
      <aside className="flex w-72 shrink-0 flex-col gap-2 overflow-y-auto border-r border-border bg-surface-base p-3">
        <div className="mb-1">
          <h1 className="text-[15px] font-semibold text-fg">Keşif Testi</h1>
          <p className="text-[11px] text-fg-subtle">Zaman kutulu, charter tabanlı oturumlar</p>
        </div>
        <NewSessionForm projectId={projectId} onCreated={s => setSelectedId(s.id)} />
        {isLoading ? (
          <div className="py-8 text-center"><div className="mx-auto h-4 w-4 animate-spin rounded-full border-2 border-border border-t-pink-500" /></div>
        ) : (
          sessions.map(s => (
            <button key={s.id} onClick={() => setSelectedId(s.id)}
              className={`group flex items-center gap-2 rounded-lg border px-3 py-2 text-left transition-colors ${s.id === selectedId ? "border-pink-500/40 bg-surface-raised" : "border-border bg-surface-base hover:bg-surface-raised"}`}>
              <span className={`h-2 w-2 shrink-0 rounded-full ${STATUS_META[s.status]?.dot ?? "bg-slate-500"}`} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] text-fg">{s.title}</p>
                <p className="text-[10px] text-fg-subtle">{(s.notes ?? []).length} not · {fmtDuration(s.elapsed_seconds)}</p>
              </div>
              <span onClick={e => { e.stopPropagation(); if (confirm("Oturum silinsin mi?")) delSession.mutate(s.id); }}
                className="shrink-0 text-[12px] text-fg-disabled opacity-0 hover:text-red-400 group-hover:opacity-100" role="button" aria-label="Sil">✕</span>
            </button>
          ))
        )}
      </aside>

      {/* Detail */}
      <main className="min-w-0 flex-1 bg-surface-base">
        {selected ? (
          <SessionDetail projectId={projectId} session={selected} />
        ) : (
          <div className="flex h-full items-center justify-center text-center">
            <div>
              <p className="text-[14px] font-semibold text-fg">Keşif oturumu yok</p>
              <p className="mt-1 text-[12px] text-fg-muted">Soldan yeni bir oturum oluşturarak başlayın.</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function ExploratoryPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);
  if (!projectId) return null;
  return (
    <PageErrorBoundary>
      <div className="h-[calc(100vh-48px-72px)]">
        <ExploratoryBody projectId={mpid || projectId} />
      </div>
    </PageErrorBoundary>
  );
}
