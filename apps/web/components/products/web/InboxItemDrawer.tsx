"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { InboxItem, InboxKind } from "@/lib/hooks/use-web-dashboard";

interface DrawerProps {
  item: InboxItem | null;
  onClose: () => void;
  onResolved: (id: string, action: ActionKey) => void;
}

type ActionKey = "approve" | "reject" | "snooze" | "reassign";

const KIND_META: Record<InboxKind, { icon: string; label: string; cls: string }> = {
  review:      { icon: "👀", label: "İncele",  cls: "bg-sky-500/15 text-sky-300 border-sky-500/30" },
  approve:     { icon: "✅", label: "Onayla",  cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
  fix:         { icon: "🔧", label: "Düzelt",  cls: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  investigate: { icon: "🔎", label: "Araştır", cls: "bg-violet-500/15 text-violet-300 border-violet-500/30" },
};

const ACTION_META: Record<ActionKey, { label: string; icon: string; tone: string }> = {
  approve:  { label: "Onayla",       icon: "✓", tone: "bg-emerald-500 hover:bg-emerald-400 text-white shadow-lg shadow-emerald-500/20" },
  reject:   { label: "Reddet",       icon: "✕", tone: "bg-rose-500/15 text-rose-200 border border-rose-500/30 hover:bg-rose-500/25" },
  snooze:   { label: "Ertele 24s",   icon: "⏰", tone: "bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700" },
  reassign: { label: "Devret",       icon: "↪",  tone: "bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700" },
};

function actionsForKind(kind: InboxKind): ActionKey[] {
  if (kind === "approve") return ["approve", "reject", "snooze", "reassign"];
  if (kind === "fix")     return ["snooze", "reassign"];
  if (kind === "review")  return ["approve", "reject", "snooze", "reassign"];
  return ["snooze", "reassign"];
}

export function InboxItemDrawer({ item, onClose, onResolved }: DrawerProps) {
  const open = !!item;
  const [busy, setBusy] = useState<ActionKey | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Escape kapatır
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Body scroll lock
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, [open]);

  if (!item) return null;
  const k = KIND_META[item.kind];

  const perform = async (action: ActionKey) => {
    setBusy(action);
    setError(null);
    try {
      await apiFetch(`/api/v1/products/web/my-inbox/${encodeURIComponent(item.id)}/${action}`, {
        method: "POST",
      });
      onResolved(item.id, action);
      onClose();
    } catch (err) {
      // Endpoint yoksa veya hata varsa kullanıcıya bildir ama optimistic resolve etme
      const msg = err instanceof ApiError ? `${err.status} ${err.message}` : "bilinmeyen hata";
      setError(`Aksiyon başarısız: ${msg}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        className="fixed inset-y-0 right-0 z-50 w-full sm:w-[480px] bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col"
      >
        {/* Header */}
        <header className="flex items-start justify-between gap-3 px-5 py-4 border-b border-slate-800">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${k.cls}`}>
                {k.icon} {k.label}
              </span>
              <span className="text-[10px] text-slate-500">#{item.id} · {item.age}</span>
            </div>
            <h2 id="drawer-title" className="text-base font-semibold text-white leading-snug">
              {item.title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 h-8 w-8 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white"
            aria-label="Kapat"
          >
            ✕
          </button>
        </header>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <section>
            <p className="text-[11px] uppercase tracking-wider text-slate-500 mb-1.5">Bağlam</p>
            <p className="text-sm text-slate-200 leading-relaxed">{item.context}</p>
          </section>

          {/* Kind'a göre özel önizleme */}
          {item.kind === "approve" && (
            <section>
              <p className="text-[11px] uppercase tracking-wider text-slate-500 mb-1.5">Diff Önizleme</p>
              <div className="rounded-lg border border-slate-800 bg-slate-950/70 aspect-video flex items-center justify-center text-xs text-slate-400">
                <div className="text-center">
                  <p className="text-amber-300 font-mono text-base">Δ visual diff</p>
                  <p className="text-[11px] text-slate-500 mt-1">Baseline ↔ Current karşılaştırması burada renderlanır</p>
                </div>
              </div>
            </section>
          )}

          {item.kind === "fix" && (
            <section>
              <p className="text-[11px] uppercase tracking-wider text-slate-500 mb-1.5">Son Fail Detayı</p>
              <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2.5">
                <p className="text-[10px] uppercase tracking-wider text-rose-300 font-bold mb-1">TypeError</p>
                <p className="text-xs font-mono text-rose-200 break-all">Cannot read 'token' of undefined</p>
              </div>
              <p className="text-[11px] text-slate-500 mt-2">Son 3 koşunun 2'sinde aynı hata · pattern flaky</p>
            </section>
          )}

          {item.kind === "review" && (
            <section>
              <p className="text-[11px] uppercase tracking-wider text-slate-500 mb-1.5">Etkilenen Test'ler</p>
              <ul className="space-y-1 text-xs text-slate-300">
                <li className="flex justify-between"><span>Checkout · happy path</span><span className="text-slate-500">12 kullanım</span></li>
                <li className="flex justify-between"><span>Login · invalid creds</span><span className="text-slate-500">8 kullanım</span></li>
                <li className="flex justify-between"><span>Profile · avatar upload</span><span className="text-slate-500">5 kullanım</span></li>
                <li className="text-slate-500 text-center pt-1">+ 44 test daha</li>
              </ul>
            </section>
          )}

          {item.kind === "investigate" && (
            <section>
              <p className="text-[11px] uppercase tracking-wider text-slate-500 mb-1.5">Trend</p>
              <div className="rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-3">
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-amber-300">2.9s</span>
                  <span className="text-xs text-slate-500">↑ 0.4s (16%)</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">Son 7 gün ortalama LCP — hedef &lt;2.5s</p>
              </div>
            </section>
          )}

          {error && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
              {error}
            </div>
          )}
        </div>

        {/* Footer aksiyonlar */}
        <footer className="border-t border-slate-800 px-5 py-3 space-y-2">
          {actionsForKind(item.kind).map((a, idx) => {
            const m = ACTION_META[a];
            const isPrimary = idx === 0 && (a === "approve");
            const isBusy = busy === a;
            return (
              <button
                key={a}
                onClick={() => void perform(a)}
                disabled={!!busy}
                className={`w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-wait ${m.tone}`}
                style={isPrimary ? undefined : { }}
              >
                <span>{m.icon}</span>
                <span>{isBusy ? "Gönderiliyor…" : m.label}</span>
              </button>
            );
          })}
        </footer>
      </aside>

    </>
  );
}
