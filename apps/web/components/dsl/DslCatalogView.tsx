"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  useDslActions,
  useDslCategories,
  useDslFeedback,
  useDslGenerateAiAliases,
  useDslIndexInfo,
  useDslSearch,
  useDslStats,
  useDslSuggest,
  type DslAction,
  type DslSearchHit,
} from "@/lib/hooks/use-dsl";

type LangFilter = "all" | "tr" | "en";
type SearchMode = "substring" | "ai";
type StepType = "given" | "when" | "then";
type StepTypeFilter = "all" | StepType;
type DetailTab = "aliases" | "params" | "impl" | "examples" | "related" | "ai";

const CATEGORY_LABELS: Record<string, string> = {
  ui: "UI",
  api: "API",
  assert: "Doğrulama",
  bgts: "Bankacılık Domain",
  setup: "Setup",
  uncategorized: "Diğer",
};

const CATEGORY_DOTS: Record<string, string> = {
  ui: "bg-sky-400",
  api: "bg-blue-400",
  assert: "bg-amber-400",
  bgts: "bg-purple-400",
  setup: "bg-emerald-400",
  uncategorized: "bg-slate-500",
};

/** Hex colors matching CATEGORY_DOTS — used for inline border/shadow in cards */
const CATEGORY_COLORS: Record<string, string> = {
  ui: "#38bdf8",
  api: "#60a5fa",
  assert: "#fbbf24",
  bgts: "#c084fc",
  setup: "#34d399",
  uncategorized: "#475569",
};

const STEP_TYPE_FILTER_CONFIG: Record<StepType, { label: string; dot: string; badgeCls: string }> = {
  given: { label: "Ön Koşul", dot: "bg-emerald-500", badgeCls: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 ring-1 ring-inset ring-emerald-500/[0.05]" },
  when:  { label: "Eylem",    dot: "bg-blue-500",    badgeCls: "border-blue-500/30 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 ring-1 ring-inset ring-blue-500/[0.05]" },
  then:  { label: "Doğrulama",dot: "bg-amber-500",   badgeCls: "border-amber-500/30 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 ring-1 ring-inset ring-amber-500/[0.05]" },
};

const INPUT_CLS =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 shadow-inner shadow-black/10 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 focus:shadow-[0_0_0_3px_rgba(59,130,246,0.07)] transition-all";

const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-1 focus-visible:ring-offset-slate-950";

const BADGE_CLS =
  "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium";

const LANG_BADGE: Record<string, string> = {
  tr: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/[0.05]",
  en: "border-blue-500/30 bg-blue-500/10 text-blue-400 ring-1 ring-inset ring-blue-500/[0.05]",
  meta: "border-slate-600 bg-slate-800 text-slate-300 ring-1 ring-inset ring-white/[0.03]",
};

const IMPL_BADGE: Record<string, string> = {
  python: "border-yellow-500/30 bg-yellow-500/10 text-yellow-400 ring-1 ring-inset ring-yellow-500/[0.05]",
  java: "border-orange-500/30 bg-orange-500/10 text-orange-400 ring-1 ring-inset ring-orange-500/[0.05]",
  typescript: "border-sky-500/30 bg-sky-500/10 text-sky-400 ring-1 ring-inset ring-sky-500/[0.05]",
};

const STEP_TYPE_CONFIG: Record<StepType, {
  borderColor: string;
  badgeCls: string;
  label: string;
}> = {
  given: {
    borderColor: "#10b981",
    badgeCls: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/[0.06]",
    label: "Ön Koşul",
  },
  when: {
    borderColor: "#3b82f6",
    badgeCls: "border-blue-500/40 bg-blue-500/10 text-blue-400 ring-1 ring-inset ring-blue-500/[0.06]",
    label: "Eylem",
  },
  then: {
    borderColor: "#f59e0b",
    badgeCls: "border-amber-500/40 bg-amber-500/10 text-amber-400 ring-1 ring-inset ring-amber-500/[0.06]",
    label: "Doğrulama",
  },
};

function getStepType(description: string): StepType | null {
  if (!description) return null;
  const d = description.trim();
  if (d.startsWith("(Ön koşul)") || d.startsWith("(On kosul)") || d.startsWith("Given")) return "given";
  if (d.startsWith("Eylem:") || d.startsWith("When") || d.startsWith("Action:")) return "when";
  if (d.startsWith("Doğrulama:") || d.startsWith("Dogrulama:") || d.startsWith("Then") || d.startsWith("Assert:")) return "then";
  return null;
}

function isRedundantDescription(description: string, primary: string): boolean {
  const prefixes = ["Eylem: ", "(Ön koşul) ", "Doğrulama: ", "Dogrulama: ", "Given ", "When ", "Then "];
  for (const prefix of prefixes) {
    if (description === prefix + primary) return true;
  }
  return description === primary;
}

function getCategoryLabel(category: string): string {
  const parts = category.split(".");
  const topLabel = CATEGORY_LABELS[parts[0]] ?? parts[0].toUpperCase();
  return parts.length > 1 ? `${topLabel} · ${parts[1]}` : topLabel;
}

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "az önce";
  if (mins < 60) return `${mins} dk önce`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} sa önce`;
  return new Date(dateStr).toLocaleDateString("tr-TR");
}

type ToastVariant = "success" | "warning" | "info" | "favorite";

interface ToastPayload {
  msg: string;
  variant?: ToastVariant;
}

/** Dispatches a brief toast notification (picked up by ToastContainer). */
function dispatchToast(msg: string, variant: ToastVariant = "success") {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent<ToastPayload>("dsl:toast", { detail: { msg, variant } }));
  }
}

/** Self-contained toast notification container. Listens for dsl:toast events. */
function ToastContainer() {
  const [toasts, setToasts] = useState<Array<{ id: number; msg: string; variant: ToastVariant }>>([]);

  useEffect(() => {
    function onToast(e: Event) {
      const { msg, variant = "success" } = (e as CustomEvent<ToastPayload>).detail;
      const id = Date.now() + Math.random();
      setToasts((prev) => [...prev, { id, msg, variant }]);
      setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 2200);
    }
    window.addEventListener("dsl:toast", onToast);
    return () => window.removeEventListener("dsl:toast", onToast);
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="pointer-events-none fixed bottom-20 left-1/2 z-50 flex -translate-x-1/2 flex-col items-center gap-1.5">
      {toasts.map((t) => {
        const isSuccess = t.variant === "success";
        const isWarning = t.variant === "warning";
        const isFavorite = t.variant === "favorite";
        return (
          <div
            key={t.id}
            className={`animate-slide-up flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-medium backdrop-blur-md ring-1 ring-inset ${
              isFavorite
                ? "border-amber-600/50 bg-slate-900/96 text-amber-200 shadow-lg shadow-amber-500/15 ring-amber-500/[0.08]"
                : isSuccess
                ? "border-emerald-700/50 bg-slate-900/96 text-emerald-200 shadow-lg shadow-emerald-500/15 ring-emerald-500/[0.08]"
                : isWarning
                ? "border-amber-700/50 bg-slate-900/96 text-amber-200 shadow-lg shadow-amber-500/15 ring-amber-500/[0.08]"
                : "border-slate-600/60 bg-slate-800/96 text-slate-100 shadow-lg shadow-black/30 ring-white/[0.05]"
            }`}
          >
            {isFavorite && (
              <svg viewBox="0 0 10 10" fill="currentColor" className="h-2.5 w-2.5 shrink-0 text-amber-400">
                <path d="M5 1l1.2 2.5L9 3.8l-2 2 .5 2.7L5 7.2 2.5 8.5 3 5.8 1 3.8l2.8-.3L5 1z" />
              </svg>
            )}
            {isSuccess && !isFavorite && (
              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5 shrink-0 text-emerald-400">
                <circle cx="5" cy="5" r="4" />
                <path d="M3 5.5l1.5 1.5 2.5-3" />
              </svg>
            )}
            {isWarning && (
              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2.5 w-2.5 shrink-0 text-amber-400">
                <circle cx="5" cy="5" r="4" />
                <path d="M5 3v3M5 7.5v.5" />
              </svg>
            )}
            {t.msg}
          </div>
        );
      })}
    </div>
  );
}

function KeyboardShortcutsModal({ onClose }: { onClose: () => void }) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const arrowKeys = (
    <span className="flex items-center gap-0.5">
      <kbd className="inline-flex items-center justify-center rounded border border-slate-700/80 bg-slate-800/90 px-1 py-0.5 shadow-sm shadow-black/20 ring-1 ring-inset ring-white/[0.05]">
        <svg viewBox="0 0 8 8" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2 w-2 text-slate-400"><path d="M5 1.5L2.5 4 5 6.5" /></svg>
      </kbd>
      <kbd className="inline-flex items-center justify-center rounded border border-slate-700/80 bg-slate-800/90 px-1 py-0.5 shadow-sm shadow-black/20 ring-1 ring-inset ring-white/[0.05]">
        <svg viewBox="0 0 8 8" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2 w-2 text-slate-400"><path d="M3 1.5L5.5 4 3 6.5" /></svg>
      </kbd>
    </span>
  );
  const groups: Array<{ label: string; items: Array<{ shortcut: React.ReactNode; desc: string }> }> = [
    {
      label: "Liste Görünümü",
      items: [
        { shortcut: "⌘K", desc: "Aramaya odaklan" },
        { shortcut: "Enter", desc: "İlk sonucu aç (aramada)" },
        { shortcut: "Esc", desc: "Arama temizle" },
        { shortcut: arrowKeys, desc: "Önceki / sonraki sayfa" },
        { shortcut: "j / k", desc: "Sonraki / önceki kart (vim)" },
        { shortcut: "Home / End", desc: "İlk / son karta git" },
        { shortcut: "Enter", desc: "Odaktaki kartı aç" },
        { shortcut: "c", desc: "Odaktaki kartı Gherkin olarak kopyala" },
        { shortcut: "b", desc: "Toplu seçim modunu aç / kapat" },
        { shortcut: "?", desc: "Bu ekranı aç / kapat" },
      ],
    },
    {
      label: "Detay Paneli",
      items: [
        { shortcut: arrowKeys, desc: "Önceki / sonraki cümlecik" },
        { shortcut: "1–6", desc: "Sekme değiştir (Alias'lar, Param…)" },
        { shortcut: "/", desc: "Alias filtresine odaklan (Alias sekmesi)" },
        { shortcut: "f", desc: "Favori ekle / çıkar" },
        { shortcut: "Esc", desc: "Paneli kapat" },
      ],
    },
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-[2px] animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Klavye kısayolları"
    >
      <div
        className="animate-scale-in w-96 rounded-xl border border-slate-700/60 bg-slate-900 shadow-2xl shadow-black/70 ring-1 ring-inset ring-white/[0.03]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-md bg-slate-800 ring-1 ring-inset ring-white/[0.06]">
              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3 text-slate-500">
                <rect x="1" y="2.5" width="8" height="5" rx="1" />
                <path d="M3 5h.5M5 5h.5M7 5h.5M3 6.5h4" />
              </svg>
            </span>
            <h3 className="font-semibold text-white">Klavye Kısayolları</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className={`flex h-6 w-6 items-center justify-center rounded-md border border-slate-700 bg-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-600 ring-1 ring-inset ring-white/[0.04] transition-all active:scale-90 ${FOCUS_RING}`}
          >
            <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2.5 w-2.5">
              <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" />
            </svg>
          </button>
        </div>
        <div className="divide-y divide-slate-800/60 overflow-hidden rounded-b-xl">
          {groups.map(({ label, items }) => (
            <div key={label} className="px-5 py-3.5">
              <div className="mb-3 text-[10px] font-bold uppercase tracking-widest text-slate-600">
                {label}
              </div>
              <dl className="grid grid-cols-1 gap-y-2">
                {items.map(({ shortcut, desc }) => (
                  <div key={desc} className="group flex items-center justify-between gap-4">
                    <dd className="text-xs text-slate-500 group-hover:text-slate-300 transition-colors">{desc}</dd>
                    {typeof shortcut === "string" ? (
                      <kbd className="shrink-0 rounded-md border border-slate-700/80 bg-slate-800/90 px-2 py-0.5 font-mono text-[10px] text-slate-300 shadow-sm shadow-black/20 ring-1 ring-inset ring-white/[0.05]">
                        {shortcut}
                      </kbd>
                    ) : (
                      <span className="shrink-0">{shortcut}</span>
                    )}
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-center border-t border-slate-800 px-5 py-2">
          <span className="text-[10px] text-slate-600">Herhangi bir yere tıklayarak kapat</span>
          <span className="mx-1.5 text-slate-600">·</span>
          <kbd className="rounded border border-slate-700/80 bg-slate-800/90 px-1.5 py-0.5 font-mono text-[9px] text-slate-400 ring-1 ring-inset ring-white/[0.05] shadow-sm shadow-black/20">Esc</kbd>
        </div>
      </div>
    </div>
  );
}

function ShareButton() {
  const [shared, setShared] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard.writeText(window.location.href).then(() => {
          setShared(true);
          setTimeout(() => setShared(false), 2000);
        });
      }}
      className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-sm transition-all hover:scale-[1.02] active:scale-[0.98] ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
        shared
          ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300 ring-emerald-500/[0.08]"
          : "border-slate-700 bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200 ring-white/[0.03]"
      }`}
      title="Sayfa bağlantısını kopyala"
    >
      {shared ? (
        <>
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          <span>Kopyalandı</span>
        </>
      ) : (
        <>
          <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-3 w-3">
            <path d="M9 1l4 4-4 4M13 5H5a4 4 0 000 8h1" />
          </svg>
          <span>Paylaş</span>
        </>
      )}
    </button>
  );
}

function ActionCard({
  action,
  highlight,
  onOpen,
  hit,
  onVote,
  votedAs,
  onTagClick,
  activeTag,
  isSelected,
  isFavorite,
  onToggleFavorite,
  compact,
}: {
  action: DslAction;
  highlight?: string;
  onOpen: (a: DslAction) => void;
  hit?: DslSearchHit;
  onVote?: (vote: "up" | "down") => void;
  votedAs?: "up" | "down" | null;
  onTagClick?: (tag: string) => void;
  activeTag?: string | null;
  isSelected?: boolean;
  isFavorite?: boolean;
  onToggleFavorite?: (id: string) => void;
  compact?: boolean;
}) {
  const [idCopied, setIdCopied] = useState(false);
  const [bddCopied, setBddCopied] = useState(false);

  const firstTr = action.aliases?.tr?.[0];
  const firstEn = action.aliases?.en?.[0];
  const primary = firstTr ?? firstEn ?? action.description;
  const score = typeof hit?.score === "number" ? hit.score : null;
  const source = hit?.source ?? null;
  const reason = hit?.reason ?? null;

  const stepType = getStepType(action.description ?? "");
  const stepConfig = stepType ? STEP_TYPE_CONFIG[stepType] : null;
  const showDescription =
    action.description &&
    !isRedundantDescription(action.description, primary ?? "");

  const isDeprecated = !!action.deprecated;
  const paramCount = action.parameters?.length ?? 0;
  const trCount = action.aliases?.tr?.length ?? 0;
  const enCount = action.aliases?.en?.length ?? 0;
  const visibleTags = action.tags?.slice(0, 5) ?? [];

  function copyId(e: React.MouseEvent) {
    e.stopPropagation();
    navigator.clipboard.writeText(action.id).then(() => {
      setIdCopied(true);
      dispatchToast("ID kopyalandı");
      setTimeout(() => setIdCopied(false), 1500);
    });
  }

  function copyBdd(e: React.MouseEvent) {
    e.stopPropagation();
    const stepType = getStepType(action.description ?? "");
    const keyword = stepType === "given" ? "Given" : stepType === "when" ? "When" : stepType === "then" ? "Then" : "And";
    const text = `${keyword} ${primary}`;
    navigator.clipboard.writeText(text).then(() => {
      setBddCopied(true);
      dispatchToast("BDD adımı kopyalandı");
      setTimeout(() => setBddCopied(false), 1500);
    });
  }

  // Compact list-row variant
  if (compact) {
    return (
      <div
        role="listitem"
        style={
          isSelected
            ? { borderLeftColor: stepConfig?.borderColor ?? "#3b82f6", borderLeftWidth: "2px" }
            : stepConfig
            ? { borderLeftColor: stepConfig.borderColor + "80", borderLeftWidth: "2px" }
            : undefined
        }
        className={`group flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left transition-all duration-150 active:scale-[0.995] ${
          isSelected
            ? "border-blue-500/50 bg-blue-500/5 shadow-sm shadow-blue-500/10 ring-1 ring-inset ring-blue-500/[0.08]"
            : "border-slate-800/60 bg-slate-900/30 hover:bg-slate-900/70 hover:border-slate-700/60 hover:ring-1 hover:ring-inset hover:ring-white/[0.03]"
        } ${isDeprecated ? "opacity-50" : ""}`}
        data-testid={`dsl-action-card-${action.id}`}
      >
        {/* Step dot */}
        {stepConfig && (
          <span
            className="h-2 w-2 shrink-0 rounded-full"
            style={{ backgroundColor: stepConfig.borderColor }}
            title={stepConfig.label}
          />
        )}
        {/* BDD keyword + primary alias */}
        <button
          type="button"
          onClick={() => onOpen(action)}
          className={`min-w-0 flex-1 truncate text-left font-mono text-xs ${isDeprecated ? "line-through text-slate-500" : "text-white hover:text-blue-200"} ${FOCUS_RING}`}
        >
          {stepType && (
            <span className={`mr-1 text-[10px] font-semibold tracking-wider ${
              stepType === "given" ? "text-emerald-400/65" : stepType === "when" ? "text-blue-400/65" : "text-amber-400/65"
            }`}>
              {stepType === "given" ? "Given" : stepType === "when" ? "When" : "Then"}
            </span>
          )}
          {highlight ? renderHighlight(primary, highlight) : renderParams(primary)}
        </button>
        {/* Category dot + label */}
        <span className="hidden shrink-0 items-center gap-1 text-[10px] text-slate-600 sm:flex">
          <span className={`h-1.5 w-1.5 rounded-full ${CATEGORY_DOTS[action.category.split(".")[0]] ?? "bg-slate-500"}`} />
          {getCategoryLabel(action.category)}
        </span>
        {/* Alias counts (show on hover) */}
        {(trCount > 0 || enCount > 0) && (
          <span className="hidden shrink-0 items-center gap-0.5 text-[9px] opacity-0 transition-opacity group-hover:opacity-100 sm:flex">
            {trCount > 0 && (
              <span className="flex items-center gap-0.5 text-emerald-600">
                <span className="inline-flex h-3 w-3 items-center justify-center rounded-sm bg-emerald-500/15 font-bold text-[6px] text-emerald-500 leading-none">TR</span>
                {trCount}
              </span>
            )}
            {enCount > 0 && (
              <span className="flex items-center gap-0.5 text-blue-600">
                <span className="inline-flex h-3 w-3 items-center justify-center rounded-sm bg-blue-500/15 font-bold text-[6px] text-blue-500 leading-none">EN</span>
                {enCount}
              </span>
            )}
          </span>
        )}
        {/* Score pill */}
        {score !== null && (
          <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${
            score >= 0.75 ? "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/20" : score >= 0.5 ? "bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/20" : "bg-slate-700/60 text-slate-500 ring-1 ring-slate-600/20"
          }`}>
            {(score * 100).toFixed(0)}%
          </span>
        )}
        {/* Copy ID + favorite */}
        <button
          type="button"
          onClick={copyId}
          className={`shrink-0 flex items-center justify-center rounded p-0.5 transition-all active:scale-75 opacity-0 group-hover:opacity-100 ${FOCUS_RING} ${
            idCopied ? "text-emerald-400" : "text-slate-600 hover:text-slate-300"
          }`}
          title="ID kopyala"
        >
          {idCopied ? (
            <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
              <path d="M2 5.5l2 2 4-4" />
            </svg>
          ) : (
            <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
              <rect x="1" y="2" width="7" height="7" rx="1" />
              <path d="M3 1h6v7" />
            </svg>
          )}
        </button>
        {onToggleFavorite && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onToggleFavorite(action.id); }}
            className={`shrink-0 flex items-center justify-center p-0.5 transition-all active:scale-75 ${FOCUS_RING} ${
              isFavorite ? "text-amber-400" : "text-slate-600 opacity-0 group-hover:opacity-100 hover:text-amber-400"
            }`}
            title={isFavorite ? "Favorilerden çıkar" : "Favorilere ekle"}
            aria-pressed={isFavorite}
          >
            <svg viewBox="0 0 10 10" fill={isFavorite ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
              <path d="M5 1l1.2 2.5L9 3.8l-2 2 .5 2.7L5 7.2 2.5 8.5 3 5.8 1 3.8l2.8-.3L5 1z" />
            </svg>
          </button>
        )}
      </div>
    );
  }

  const topCatKey = action.category.split(".")[0];
  const catBorderColor = stepConfig
    ? stepConfig.borderColor
    : (CATEGORY_COLORS[topCatKey] ?? "#475569");

  // Step-type colored glow on hover — given=emerald, when=blue, then=amber
  const hoverShadowCls =
    stepType === "given" ? "hover:shadow-emerald-500/10" :
    stepType === "when"  ? "hover:shadow-blue-500/10" :
    stepType === "then"  ? "hover:shadow-amber-500/10" :
    "hover:shadow-black/40";

  const isAiResult = source && source !== "lexical";

  return (
    <div
      role="listitem"
      style={{ borderLeftColor: catBorderColor, borderLeftWidth: "3px" }}
      className={`group relative flex w-full flex-col gap-0 rounded-xl border text-left transition-all duration-200 hover:shadow-xl ${hoverShadowCls} hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.995] hover:ring-1 hover:ring-inset hover:ring-white/[0.05] ${
        isSelected
          ? "border-blue-500/60 bg-blue-500/5 shadow-md shadow-blue-500/10 ring-1 ring-inset ring-blue-500/10"
          : isAiResult
          ? "border-slate-800 bg-slate-900/60 hover:bg-slate-900 hover:border-violet-500/20"
          : "border-slate-800 bg-slate-900/60 hover:bg-slate-900 hover:border-slate-700/80"
      } ${isDeprecated ? "opacity-60" : ""}`}
      data-testid={`dsl-action-card-${action.id}`}
    >
      {/* Step-type tint: fades in on group-hover — non-interactive overlay */}
      {stepConfig && (
        <div
          className="pointer-events-none absolute inset-0 rounded-[11px] opacity-0 transition-opacity duration-300 group-hover:opacity-100"
          style={{ background: `linear-gradient(135deg, ${stepConfig.borderColor}05 0%, transparent 50%)` }}
          aria-hidden="true"
        />
      )}
      <button
        type="button"
        onClick={() => onOpen(action)}
        className={`relative flex flex-col gap-2 p-4 text-left ${FOCUS_RING}`}
      >
        {/* Hover indicator arrow */}
        <span className="absolute right-3 top-3 opacity-0 transition-all group-hover:opacity-100 group-hover:translate-x-0.5">
          <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5 text-slate-600">
            <path d="M2 5h6M5.5 2l3 3-3 3" />
          </svg>
        </span>
        {/* Top row: badges + score */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              {/* Step type badge */}
              {stepConfig && (
                <span className={`${BADGE_CLS} ${stepConfig.badgeCls}`}>
                  {stepConfig.label}
                </span>
              )}
              {/* Category badge */}
              <span className={`${BADGE_CLS} border-slate-700 bg-slate-800/80 text-slate-400 ring-1 ring-inset ring-white/[0.03]`}>
                <span className={`mr-1 h-1.5 w-1.5 rounded-full ${CATEGORY_DOTS[action.category.split(".")[0]] ?? "bg-slate-500"}`} />
                {getCategoryLabel(action.category)}
              </span>
              {/* Implementation badges */}
              {Object.keys(action.implementations ?? {}).map((lang) => (
                <span
                  key={lang}
                  className={`${BADGE_CLS} ${IMPL_BADGE[lang] ?? "border-slate-600 bg-slate-800 text-slate-300 ring-1 ring-inset ring-white/[0.03]"}`}
                >
                  {lang}
                </span>
              ))}
              {/* Parameter count */}
              {paramCount > 0 && (
                <span className={`${BADGE_CLS} border-slate-700/50 bg-slate-800/50 text-slate-500 ring-1 ring-inset ring-white/[0.02]`}>
                  {paramCount} param
                </span>
              )}
              {/* Since badge — "New" if version >= current cycle heuristic */}
              {action.since && (
                <span className={`${BADGE_CLS} border-slate-800/60 bg-slate-900/60 font-mono text-[9px] ring-1 ring-inset ${
                  // Treat as "new" if the version string looks recent (ends with .0 pattern or is just a number)
                  /\b(202[4-9]|0\.[89]|1\.[0-4])\b/.test(action.since)
                    ? "border-emerald-900/40 bg-emerald-900/20 text-emerald-600 ring-emerald-500/[0.04]"
                    : "text-slate-600 ring-white/[0.02]"
                }`}>
                  v{action.since}
                </span>
              )}
              {/* Deprecated */}
              {isDeprecated && (
                <span className={`${BADGE_CLS} border-red-500/30 bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/[0.06]`}>
                  Deprecated
                </span>
              )}
              {/* AI search source */}
              {source && source !== "lexical" && (
                <span
                  className={`${BADGE_CLS} ring-1 ring-inset ${
                    source === "semantic"
                      ? "border-violet-500/30 bg-violet-500/10 text-violet-300 ring-violet-500/[0.06]"
                      : source === "hybrid"
                      ? "border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-300 ring-fuchsia-500/[0.06]"
                      : "border-amber-500/30 bg-amber-500/10 text-amber-300 ring-amber-500/[0.06]"
                  }`}
                  title={`Kaynak: ${source}`}
                >
                  AI · {source}
                </span>
              )}
            </div>
          </div>

          {/* Search score */}
          {score !== null && (
            <div className="flex min-w-[68px] shrink-0 flex-col items-end gap-1.5" title={`Eşleşme skoru: ${(score * 100).toFixed(1)}%`}>
              <span
                className={`rounded-full px-2 py-0.5 text-[11px] font-bold tabular-nums ${
                  score >= 0.75
                    ? "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/20"
                    : score >= 0.5
                    ? "bg-blue-500/15 text-blue-300 ring-1 ring-blue-500/20"
                    : "bg-slate-700/60 text-slate-400 ring-1 ring-slate-600/20"
                }`}
              >
                {(score * 100).toFixed(0)}%
              </span>
              <div className="h-1 w-14 overflow-hidden rounded-full bg-slate-800/60">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    score >= 0.75 ? "bg-gradient-to-r from-emerald-500 to-emerald-400" : score >= 0.5 ? "bg-gradient-to-r from-blue-500 to-blue-400" : "bg-gradient-to-r from-slate-600 to-slate-500"
                  }`}
                  style={{ width: `${Math.max(6, Math.round(score * 100))}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* ID row with copy button + alias counts */}
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-xs truncate">{renderActionId(action.id)}</span>
          <button
            type="button"
            onClick={copyId}
            className={`shrink-0 flex items-center justify-center rounded p-0.5 opacity-0 transition-all active:scale-75 group-hover:opacity-100 hover:bg-slate-800 ${FOCUS_RING} ${
              idCopied ? "text-emerald-400" : "text-slate-600 hover:text-slate-300"
            }`}
            title="ID kopyala"
          >
            {idCopied ? (
              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                <path d="M2 5.5l2 2 4-4" />
              </svg>
            ) : (
              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                <rect x="1" y="2" width="7" height="7" rx="1" />
                <path d="M3 1h6v7" />
              </svg>
            )}
          </button>
          <button
            type="button"
            onClick={copyBdd}
            className={`shrink-0 rounded border px-1.5 py-0.5 text-[9px] font-semibold opacity-0 transition-all active:scale-[0.94] group-hover:opacity-100 ring-1 ring-inset ${FOCUS_RING} ${
              bddCopied
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 !opacity-100 ring-emerald-500/[0.08]"
                : stepType === "given"
                ? "border-emerald-500/25 bg-emerald-500/[0.06] text-emerald-500/70 hover:border-emerald-500/40 hover:text-emerald-400 ring-emerald-500/[0.04] shadow-sm shadow-black/10"
                : stepType === "when"
                ? "border-blue-500/25 bg-blue-500/[0.06] text-blue-500/70 hover:border-blue-500/40 hover:text-blue-400 ring-blue-500/[0.04] shadow-sm shadow-black/10"
                : stepType === "then"
                ? "border-amber-500/25 bg-amber-500/[0.06] text-amber-500/70 hover:border-amber-500/40 hover:text-amber-400 ring-amber-500/[0.04] shadow-sm shadow-black/10"
                : "border-slate-700/60 text-slate-600 hover:bg-slate-800 hover:text-slate-300 ring-white/[0.02] shadow-sm shadow-black/10"
            }`}
            title="BDD adımı olarak kopyala (Given/When/Then ...)"
          >
            {bddCopied ? (
              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                <path d="M2 5.5l2 2 4-4" />
              </svg>
            ) : "BDD"}
          </button>
          {onToggleFavorite && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onToggleFavorite(action.id); }}
              className={`shrink-0 flex items-center justify-center rounded p-0.5 transition-all active:scale-75 ${FOCUS_RING} ${
                isFavorite
                  ? "text-amber-400 opacity-100"
                  : "text-slate-600 opacity-0 group-hover:opacity-100 hover:text-amber-400"
              }`}
              title={isFavorite ? "Favorilerden çıkar" : "Favorilere ekle"}
              aria-label={isFavorite ? "Favorilerden çıkar" : "Favorilere ekle"}
              aria-pressed={isFavorite}
            >
              <svg viewBox="0 0 10 10" fill={isFavorite ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
                <path d="M5 1l1.2 2.5L9 3.8l-2 2 .5 2.7L5 7.2 2.5 8.5 3 5.8 1 3.8l2.8-.3L5 1z" />
              </svg>
            </button>
          )}
          <span className="ml-auto flex shrink-0 items-center gap-1 text-[10px]">
            {trCount > 0 && (
              <span className="flex items-center gap-0.5 text-emerald-600">
                <span className="inline-flex h-3 w-3 items-center justify-center rounded-sm bg-emerald-500/15 font-bold text-[7px] text-emerald-500 leading-none">TR</span>
                {trCount}
              </span>
            )}
            {enCount > 0 && (
              <span className="flex items-center gap-0.5 text-blue-600">
                <span className="inline-flex h-3 w-3 items-center justify-center rounded-sm bg-blue-500/15 font-bold text-[7px] text-blue-500 leading-none">EN</span>
                {enCount}
              </span>
            )}
          </span>
        </div>

        {/* Primary title — includes GWT keyword prefix for immediate BDD readability */}
        <div className={`font-mono text-[13px] leading-relaxed tracking-tight ${isDeprecated ? "line-through text-slate-400" : "text-white"}`}>
          {stepType && (
            <span className={`mr-1.5 select-none text-[10px] font-bold tracking-wider ${
              stepType === "given" ? "text-emerald-400/65" : stepType === "when" ? "text-blue-400/65" : "text-amber-400/65"
            }`}>
              {stepType === "given" ? "Given" : stepType === "when" ? "When" : "Then"}
            </span>
          )}
          {highlight ? renderHighlight(primary, highlight) : renderParams(primary)}
        </div>

        {/* Secondary aliases preview */}
        {!showDescription && (action.aliases?.tr?.length ?? 0) > 1 && (
          <div className="text-[10px] text-slate-500 line-clamp-1 leading-relaxed">
            {action.aliases!.tr!.slice(1, 3).map((a, i) => (
              <span key={i}>{i > 0 && <span className="mx-1 text-slate-600">·</span>}{renderParams(a)}</span>
            ))}
          </div>
        )}
        {/* Completeness indicator — subtle dots showing what data exists */}
        <div className="flex items-center gap-1.5">
          {[
            { has: trCount > 0,   label: `TR: ${trCount}`,   cls: "bg-emerald-500" },
            { has: enCount > 0,   label: `EN: ${enCount}`,   cls: "bg-blue-500" },
            { has: paramCount > 0, label: `${paramCount} param`, cls: "bg-sky-500" },
            { has: Object.keys(action.implementations ?? {}).length > 0, label: "impl", cls: "bg-violet-500" },
          ].map(({ has, label, cls }) => (
            <span
              key={label}
              className={`rounded-full transition-all duration-200 ${
                has
                  ? `h-1.5 w-1.5 ${cls} opacity-50 group-hover:opacity-90 group-hover:scale-110`
                  : "h-1 w-1 bg-slate-800/60 opacity-30"
              }`}
              title={has ? label : `${label} yok`}
            />
          ))}
        </div>
        {/* Description — only if non-redundant */}
        {showDescription && (
          <div className="text-xs text-slate-400/90 line-clamp-2 leading-relaxed">
            {highlight ? renderHighlight(action.description, highlight) : action.description}
          </div>
        )}

        {/* AI reason box */}
        {reason && (
          <div className="overflow-hidden rounded-md border border-violet-500/15 bg-violet-500/5 ring-1 ring-inset ring-violet-500/[0.05]">
            <div className="flex items-start gap-2 px-2.5 py-1.5">
              <svg viewBox="0 0 10 10" fill="currentColor" className="mt-0.5 h-2.5 w-2.5 shrink-0 text-violet-400/60">
                <path d="M5 1l.8 2.2L8 4l-2.2.8L5 7l-.8-2.2L2 4l2.2-.8L5 1z" />
              </svg>
              <div className="min-w-0 flex-1">
                <span className="text-[9px] font-semibold uppercase tracking-wider text-violet-400/50">Neden önerildi</span>
                <p className="mt-0.5 text-[11px] leading-relaxed text-violet-200/70">{reason}</p>
              </div>
            </div>
          </div>
        )}
      </button>

      {/* Tags footer */}
      {visibleTags.length > 0 && (
        <div className="flex flex-wrap items-center gap-1 border-t border-slate-800/60 px-4 py-2">
          {visibleTags.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={(e) => { e.stopPropagation(); onTagClick?.(tag); }}
              className={`rounded-md border px-1.5 py-0.5 font-mono text-[10px] transition-all active:scale-90 ring-1 ring-inset ${
                activeTag === tag
                  ? "border-blue-500/30 bg-blue-500/15 text-blue-300 ring-blue-500/[0.08]"
                  : "border-slate-800/60 bg-slate-800/60 text-slate-500 hover:border-slate-700/60 hover:bg-slate-700/60 hover:text-slate-300 ring-white/[0.02]"
              }`}
            >
              #{tag}
            </button>
          ))}
          {(action.tags?.length ?? 0) > 5 && (
            <span className="text-[10px] text-slate-600">
              +{action.tags!.length - 5}
            </span>
          )}
        </div>
      )}
      {/* Bottom gradient accent — step-type color echo of the left border */}
      {stepConfig && (
        <div
          className="h-px w-full shrink-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
          style={{ background: `linear-gradient(90deg, ${stepConfig.borderColor}40 0%, ${stepConfig.borderColor}10 60%, transparent 100%)` }}
          aria-hidden="true"
        />
      )}

      {/* Feedback voting */}
      {onVote && (
        <div className="flex items-center justify-between border-t border-slate-800/50 bg-slate-950/50 px-4 py-1.5">
          <span className="flex items-center gap-1.5 text-[10px] text-slate-600">
            <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
              <circle cx="5" cy="5" r="4" />
              <path d="M3.5 5.5l1 1 2-2.5" />
            </svg>
            Yardımcı oldu mu?
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onVote("up"); }}
              className={`flex items-center gap-1 rounded border px-2 py-0.5 text-[10px] transition-all active:scale-90 ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
                votedAs === "up"
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400 ring-emerald-500/[0.08]"
                  : "border-slate-700/60 bg-slate-900/80 text-slate-600 hover:border-emerald-500/30 hover:text-emerald-400 ring-white/[0.03]"
              }`}
              data-testid={`dsl-vote-up-${action.id}`}
              aria-label="Bu sonuç yararlı"
              aria-pressed={votedAs === "up"}
            >
              <svg viewBox="0 0 10 10" fill="currentColor" className="h-2.5 w-2.5">
                <path d="M5 1.5L8 5.5H6.5v3h-3v-3H2L5 1.5z" />
              </svg>
              {votedAs === "up" && <span>Yararlı</span>}
            </button>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onVote("down"); }}
              className={`flex items-center gap-1 rounded border px-2 py-0.5 text-[10px] transition-all active:scale-90 ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
                votedAs === "down"
                  ? "border-rose-500/40 bg-rose-500/10 text-rose-400 ring-rose-500/[0.08]"
                  : "border-slate-700/60 bg-slate-900/80 text-slate-600 hover:border-rose-500/30 hover:text-rose-400 ring-white/[0.03]"
              }`}
              data-testid={`dsl-vote-down-${action.id}`}
              aria-label="Bu sonuç yararsız"
              aria-pressed={votedAs === "down"}
            >
              <svg viewBox="0 0 10 10" fill="currentColor" className="h-2.5 w-2.5">
                <path d="M5 8.5L2 4.5H3.5v-3h3v3H8L5 8.5z" />
              </svg>
              {votedAs === "down" && <span>Yararsız</span>}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const SHIMMER_CLS =
  "relative overflow-hidden before:absolute before:inset-0 before:animate-shimmer before:bg-gradient-to-r before:from-transparent before:via-slate-700/20 before:to-transparent before:[background-size:200%_100%]";

function SkeletonCard({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <div className={`flex w-full items-center gap-3 rounded-lg border border-slate-800/50 bg-slate-900/30 px-3 py-2 ring-1 ring-inset ring-white/[0.015] ${SHIMMER_CLS}`}>
        <div className="h-2 w-2 shrink-0 rounded-full bg-slate-800/80" />
        <div className="h-3 w-2/3 rounded-md bg-slate-800/80" />
        <div className="ml-auto h-3 w-16 shrink-0 rounded-md bg-slate-800/50" />
      </div>
    );
  }
  return (
    <div className={`flex w-full flex-col gap-2.5 rounded-xl border border-slate-800/50 bg-slate-900/50 p-4 ring-1 ring-inset ring-white/[0.02] ${SHIMMER_CLS}`}
      style={{ borderLeftWidth: "3px", borderLeftColor: "rgba(71,85,105,0.3)" }}>
      {/* Badge row */}
      <div className="flex items-center gap-1.5">
        <div className="h-4 w-16 rounded-full bg-slate-800/80" />
        <div className="h-4 w-20 rounded-full bg-slate-800/60" />
        <div className="h-4 w-12 rounded-full bg-slate-800/40" />
      </div>
      {/* ID row */}
      <div className="h-2.5 w-32 rounded-md bg-slate-800/70" />
      {/* Primary title */}
      <div className="h-4 w-full rounded-md bg-slate-800/80" />
      <div className="h-3.5 w-4/5 rounded-md bg-slate-800/60" />
      {/* Completeness dots */}
      <div className="flex items-center gap-1.5 pt-0.5">
        {[0, 1, 2, 3].map((d) => (
          <div key={d} className="h-1 w-1 rounded-full bg-slate-800/60" />
        ))}
      </div>
      {/* Tags footer */}
      <div className="flex items-center gap-1 border-t border-slate-800/40 pt-2">
        <div className="h-3 w-14 rounded-md bg-slate-800/50" />
        <div className="h-3 w-10 rounded-md bg-slate-800/40" />
        <div className="h-3 w-16 rounded-md bg-slate-800/30" />
      </div>
    </div>
  );
}

function AiStatusBanner({
  indexReady,
  rows,
  model,
  activeMode,
}: {
  indexReady: boolean;
  rows: number;
  model: string;
  activeMode: string | null | undefined;
}) {
  const isFallback = activeMode === "lexical_fallback";
  if (indexReady && !isFallback) {
    return (
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-violet-500/20 bg-violet-500/5 px-3 py-2 text-[11px] text-violet-200/90 ring-1 ring-inset ring-violet-500/[0.04] animate-fade-in">
        <span className="flex items-center gap-2">
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-violet-400 opacity-40" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-violet-500" />
          </span>
          <span className="font-medium text-violet-200">AI arama aktif</span>
        </span>
        <span className="flex items-center gap-1.5 rounded-full border border-violet-500/15 bg-violet-500/[0.07] px-2 py-0.5 ring-1 ring-inset ring-violet-500/[0.04]">
          <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2 w-2 text-violet-400/70">
            <rect x="1" y="2" width="8" height="6" rx="1" />
            <path d="M3.5 5h3M5 3.5v3" />
          </svg>
          <span className="font-mono text-violet-300/80">{model || "bge-m3"}</span>
        </span>
        <span className="text-violet-400/40">·</span>
        <span className="text-violet-400/60">
          <span className="font-semibold tabular-nums text-violet-300">{rows.toLocaleString("tr-TR")}</span>
          {" "}vektör
        </span>
        {activeMode && activeMode !== "lexical_fallback" && (
          <>
            <span className="text-violet-400/40">·</span>
            <span className="rounded-full border border-violet-500/15 bg-violet-500/5 px-1.5 py-px font-mono text-[9px] uppercase tracking-wider text-violet-400/70 ring-1 ring-inset ring-violet-500/[0.03]">{activeMode}</span>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-200/80 ring-1 ring-inset ring-amber-500/[0.04] animate-fade-in">
      <span className="flex items-center gap-2">
        <span className="relative flex h-2 w-2 shrink-0">
          <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-500/60" />
        </span>
        <span>AI indeksi henüz hazır değil — alias araması kullanılıyor</span>
      </span>
      <span className="text-amber-900/60">·</span>
      <button
        type="button"
        onClick={() => navigator.clipboard.writeText("/api/v1/dsl/index/rebuild").then(() => {})}
        className={`font-mono text-[10px] text-amber-800/70 hover:text-amber-600/80 transition-all active:scale-95 ${FOCUS_RING}`}
        title="Yolu kopyala"
      >
        /api/v1/dsl/index/rebuild
      </button>
    </div>
  );
}

function renderHighlight(text: string, q: string) {
  if (!q) return renderParams(text);
  const idx = text.toLowerCase().indexOf(q.toLowerCase());
  if (idx < 0) return renderParams(text);
  return (
    <>
      {renderParams(text.slice(0, idx))}
      <mark className="rounded bg-yellow-400/20 px-0.5 py-px text-yellow-100 shadow-sm shadow-yellow-400/15 ring-1 ring-yellow-400/30 not-italic">{text.slice(idx, idx + q.length)}</mark>
      {renderParams(text.slice(idx + q.length))}
    </>
  );
}

/**
 * Renders a hierarchical action ID (e.g. "ui.click.button") with segments in different
 * visual weights — prefix segments are muted, the leaf segment is prominent.
 */
function renderActionId(id: string): React.ReactNode {
  const parts = id.split(".");
  if (parts.length <= 1) return <>{id}</>;
  return (
    <>
      {parts.map((part, i) => (
        <React.Fragment key={i}>
          {i > 0 && (
            <svg viewBox="0 0 6 8" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" className="inline-block h-2 w-1.5 select-none align-middle text-slate-500 mx-0.5">
              <path d="M1.5 1l3 3-3 3" />
            </svg>
          )}
          <span className={
            i < parts.length - 1
              ? "text-slate-600 hover:text-slate-400 transition-colors"
              : "text-slate-300 font-medium"
          }>
            {part}
          </span>
        </React.Fragment>
      ))}
    </>
  );
}

/**
 * Highlights Gherkin keywords in example text.
 * Returns a React node with colored spans for Feature/Scenario/Given/When/Then etc.
 */
function highlightGherkin(text: string): React.ReactNode {
  const lines = text.split("\n");
  return (
    <>
      {lines.map((line, i) => {
        const trimmed = line.trimStart();
        const indentLen = line.length - trimmed.length;
        const indent = line.slice(0, indentLen);

        type KwDef = { cls: string; exact?: boolean };
        const kwMap: Array<[string, KwDef]> = [
          ["Feature:", { cls: "text-violet-400 font-semibold" }],
          ["Background:", { cls: "text-violet-400 font-semibold" }],
          ["Scenario Outline:", { cls: "text-sky-400 font-semibold" }],
          ["Scenario:", { cls: "text-sky-400 font-semibold" }],
          ["Examples:", { cls: "text-amber-400 font-semibold" }],
          ["Given ", { cls: "text-emerald-400 font-medium" }],
          ["When ", { cls: "text-blue-400 font-medium" }],
          ["Then ", { cls: "text-amber-400 font-medium" }],
          ["And ", { cls: "text-slate-400 font-medium" }],
          ["But ", { cls: "text-slate-400 font-medium" }],
        ];

        // Comments
        if (trimmed.startsWith("#")) {
          return (
            <span key={i}>
              {i > 0 ? "\n" : ""}
              {indent}
              <span className="italic text-slate-600">{trimmed}</span>
            </span>
          );
        }

        // Table rows
        if (trimmed.startsWith("|")) {
          const cells = trimmed.split("|").filter((_, ci) => ci > 0 && ci < trimmed.split("|").length - 1);
          return (
            <span key={i}>
              {i > 0 ? "\n" : ""}
              {indent}
              <span className="text-slate-500">|</span>
              {cells.map((cell, ci) => (
                <span key={ci}>
                  <span className="text-slate-300">{cell}</span>
                  <span className="text-slate-500">|</span>
                </span>
              ))}
            </span>
          );
        }

        let match: [string, KwDef] | null = null;
        for (const [kw, def] of kwMap) {
          if (trimmed.startsWith(kw)) { match = [kw, def]; break; }
        }

        if (!match) {
          return <span key={i}>{i > 0 ? "\n" : ""}{line}</span>;
        }

        const [kw, { cls }] = match;
        const rest = trimmed.slice(kw.length);
        return (
          <span key={i}>
            {i > 0 ? "\n" : ""}
            {indent}
            <span className={cls}>{kw}</span>
            {renderParams(rest)}
          </span>
        );
      })}
    </>
  );
}

/** Renders {param} placeholders in aliases with a highlighted pill style. */
function renderParams(text: string): React.ReactNode {
  const parts = text.split(/(\{[^}]+\})/g);
  if (parts.length === 1) return text;
  return (
    <>
      {parts.map((part, i) =>
        part.startsWith("{") && part.endsWith("}") ? (
          <span
            key={i}
            className="inline-flex items-center rounded border border-blue-400/20 bg-blue-500/[0.07] px-1 py-px font-mono text-[0.82em] leading-none text-blue-300/85 shadow-sm shadow-blue-500/5 ring-1 ring-inset ring-blue-400/[0.08]"
          >
            {part}
          </span>
        ) : (
          part
        ),
      )}
    </>
  );
}

function AiAliasSuggestSection({ actionId }: { actionId: string }) {
  const gen = useDslGenerateAiAliases();
  const [lang, setLang] = useState<"tr" | "en">("tr");
  const [count, setCount] = useState<number>(3);
  const [lastResult, setLastResult] = useState<
    { accepted: string[]; rejected: string[]; reason?: string | null; lang: string } | null
  >(null);

  async function onGenerate() {
    try {
      const res = await gen.mutateAsync({ actionId, lang, count });
      setLastResult({
        accepted: res.accepted,
        rejected: res.rejected,
        reason: res.reason,
        lang,
      });
    } catch (err) {
      setLastResult({
        accepted: [],
        rejected: [],
        reason: err instanceof Error ? err.message : String(err),
        lang,
      });
    }
  }

  return (
    <section className="mt-5 overflow-hidden rounded-xl border border-violet-500/20 bg-violet-500/5 ring-1 ring-inset ring-violet-500/[0.04]">
      <div className="flex items-center gap-2.5 border-b border-violet-500/10 bg-violet-500/[0.04] px-4 py-3">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-violet-500/30 bg-violet-500/15 ring-1 ring-inset ring-violet-500/[0.1]">
          <svg viewBox="0 0 10 10" fill="currentColor" className="h-3 w-3 text-violet-400">
            <path d="M5 1l.8 2.2L8 4l-2.2.8L5 7l-.8-2.2L2 4l2.2-.8L5 1z" />
          </svg>
        </span>
        <div>
          <h3 className="text-sm font-semibold text-violet-200">AI Alias Önerileri</h3>
          <p className="text-[10px] text-violet-400/50">Ollama tabanlı otomatik üretim</p>
        </div>
      </div>
      <div className="p-3">
      <p className="mb-3 text-[11px] text-violet-300/70">
        Ollama, mevcut alias'lara benzer olmayan yeni adaylar üretir. Kabul
        edilenler admin onayı bekleyen &quot;pending&quot; öneri olarak
        İnceleme sayfasına düşer.
      </p>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-1 text-xs text-slate-300">
          <span>Dil:</span>
          <select
            className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white shadow-inner shadow-black/10 focus:outline-none focus:border-violet-500/40 focus:ring-1 focus:ring-violet-500/20 ring-1 ring-inset ring-white/[0.03] transition-colors"
            value={lang}
            onChange={(e) => setLang(e.target.value as "tr" | "en")}
            aria-label="Alias dili"
            title="Alias dili"
          >
            <option value="tr">Türkçe</option>
            <option value="en">İngilizce</option>
          </select>
        </label>
        <label className="flex items-center gap-1 text-xs text-slate-300">
          <span>Adet:</span>
          <input
            type="number"
            min={1}
            max={10}
            value={count}
            onChange={(e) => setCount(Math.max(1, Math.min(10, Number(e.target.value) || 3)))}
            aria-label="Kaç alias üretilsin"
            title="Kaç alias üretilsin (1-10)"
            className="w-14 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white shadow-inner shadow-black/10 focus:outline-none focus:border-violet-500/40 focus:ring-1 focus:ring-violet-500/20 ring-1 ring-inset ring-white/[0.03] transition-colors"
          />
        </label>
        <button
          type="button"
          onClick={onGenerate}
          disabled={gen.isPending}
          className={`relative flex items-center gap-2 rounded-md border border-violet-500/40 bg-violet-500/10 px-3 py-1 text-xs text-violet-200 hover:bg-violet-500/20 disabled:cursor-not-allowed transition-all active:scale-[0.97] disabled:active:scale-100 ring-1 ring-inset ring-violet-500/[0.06] ${FOCUS_RING}`}
          data-testid="dsl-ai-alias-generate"
        >
          {gen.isPending ? (
            <>
              <span className="flex items-center gap-0.5">
                {[0, 150, 300].map((delay) => (
                  <span
                    key={delay}
                    className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-violet-400"
                    style={{ animationDelay: `${delay}ms` }}
                  />
                ))}
              </span>
              <span>Üretiliyor…</span>
            </>
          ) : (
            <span className="flex items-center gap-1.5">
              <svg viewBox="0 0 10 10" fill="currentColor" className="h-2.5 w-2.5 text-violet-400">
                <path d="M5 1l.8 2.2L8 4l-2.2.8L5 7l-.8-2.2L2 4l2.2-.8L5 1z" />
              </svg>
              AI&apos;dan üret
            </span>
          )}
        </button>
      </div>

      {gen.isPending && (
        <div className="mt-3 flex items-center gap-2.5 rounded-md border border-violet-500/20 bg-violet-500/5 px-3 py-2.5 text-[11px] text-violet-300/70 ring-1 ring-inset ring-violet-500/[0.04]">
          <span className="flex shrink-0 items-center gap-0.5">
            {[0, 150, 300].map((d) => (
              <span key={d} className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-violet-400/60" style={{ animationDelay: `${d}ms` }} />
            ))}
          </span>
          <span className="leading-snug">Ollama cümlecikleri analiz ediyor, yeni adaylar üretiyor…</span>
        </div>
      )}

      {lastResult && !gen.isPending && (
        <div className="mt-2 space-y-2 text-xs">
          {lastResult.accepted.length > 0 && (
            <div>
              <div className="mb-2 flex items-center gap-2">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-300">
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
                    <circle cx="5" cy="5" r="4" />
                    <path d="M3 5.5l1.5 1.5 2.5-3" />
                  </svg>
                  Kabul edilen
                </div>
                <span className="rounded-full border border-emerald-500/20 bg-emerald-500/5 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400 ring-1 ring-inset ring-emerald-500/[0.06]">
                  {lastResult.lang} · {lastResult.accepted.length}
                </span>
              </div>
              <ul className="space-y-1">
                {lastResult.accepted.map((a) => (
                  <li key={a}>
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard.writeText(a).then(() => {
                          dispatchToast("AI alias kopyalandı");
                        });
                      }}
                      className={`group/ai-alias flex w-full items-center justify-between gap-2 rounded-md border border-emerald-500/20 bg-emerald-500/5 px-2 py-1.5 text-left font-mono text-emerald-100 transition-all active:scale-[0.99] hover:border-emerald-500/40 hover:bg-emerald-500/10 ring-1 ring-inset ring-emerald-500/[0.04] ${FOCUS_RING}`}
                      title="Kopyalamak için tıkla"
                    >
                      <span className="min-w-0 flex-1 truncate text-xs">{renderParams(a)}</span>
                      <span className="shrink-0 opacity-0 transition-opacity group-hover/ai-alias:opacity-100 text-emerald-600">
                        <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                          <rect x="1" y="2" width="7" height="7" rx="1" />
                          <path d="M3 1h6v7" />
                        </svg>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              <p className="mt-1 text-[11px] text-emerald-300/70">
                İnceleme sayfasında &quot;Pending&quot; altında görünecek. Kopyalamak için tıklayın.
              </p>
            </div>
          )}
          {lastResult.rejected.length > 0 && (
            <div>
              <div className="mb-2 flex items-center gap-2">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500">
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-3 w-3">
                    <circle cx="5" cy="5" r="4" />
                    <path d="M3 5h4" />
                  </svg>
                  Elenenler
                </div>
                <span className="rounded-full border border-slate-700/40 bg-slate-800/40 px-1.5 py-0.5 text-[10px] text-slate-600 ring-1 ring-inset ring-white/[0.02]">
                  {lastResult.rejected.length} benzer
                </span>
              </div>
              <ul className="space-y-1">
                {lastResult.rejected.map((a) => (
                  <li key={a} className="text-slate-500 line-through">
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {lastResult.reason && (
            <div className="flex items-start gap-1.5 rounded-md border border-amber-500/20 bg-amber-500/5 px-2.5 py-1.5 text-[11px] text-amber-200/80 ring-1 ring-inset ring-amber-500/[0.04]">
              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="mt-0.5 h-2.5 w-2.5 shrink-0 text-amber-400/70">
                <circle cx="5" cy="5" r="4" />
                <path d="M5 3v3M5 7.5v.5" />
              </svg>
              {lastResult.reason}
            </div>
          )}
        </div>
      )}
      </div>{/* end p-3 wrapper */}
    </section>
  );
}

function ActionDetail({
  action,
  onClose,
  onPrev,
  onNext,
  hasPrev,
  hasNext,
  position,
  onCategoryClick,
  isFavorite,
  onToggleFavorite,
  relatedActions,
  onOpenRelated,
}: {
  action: DslAction;
  onClose: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
  position?: { current: number; total: number };
  onCategoryClick?: (cat: string) => void;
  isFavorite?: boolean;
  onToggleFavorite?: (id: string) => void;
  relatedActions?: DslAction[];
  onOpenRelated?: (a: DslAction) => void;
}) {
  const [copied, setCopied] = useState<string | null>(null);
  const [aliasFilter, setAliasFilter] = useState("");
  const [activeTab, setActiveTab] = useState<DetailTab>("aliases");
  const [paramValues, setParamValues] = useState<Record<string, string>>({});
  const scrollRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const totalAliasCount = Object.values(action.aliases ?? {}).reduce((s, a) => s + a.length, 0);

  // Computed at component level (no longer in a render IIFE)
  const st = getStepType(action.description ?? "");
  const sc = st ? STEP_TYPE_CONFIG[st] : null;
  // Tab active border color matches the step type accent (Given=emerald, When=blue, Then=amber)
  const tabActiveBorderColor = sc?.borderColor ?? "#3b82f6";
  const detailPrimary = action.aliases?.tr?.[0] ?? action.aliases?.en?.[0] ?? action.id;
  const detailKw = st === "given" ? "Given" : st === "when" ? "When" : st === "then" ? "Then" : "And";
  const detailGherkin = `${detailKw} ${detailPrimary}`;

  // Focus close button when panel opens
  useEffect(() => {
    closeBtnRef.current?.focus();
  }, []);

  // Scroll to top + reset state on action change
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0, behavior: "instant" });
    setAliasFilter("");
    setActiveTab("aliases");
    setParamValues({});
  }, [action.id]);

  // ESC closes; ← → navigate between actions; 1-6 switch tabs; / focuses alias filter
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      const isTyping = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
      if (e.key === "Escape") { onClose(); return; }
      if (e.key === "ArrowLeft" && hasPrev && !isTyping) { onPrev?.(); return; }
      if (e.key === "ArrowRight" && hasNext && !isTyping) { onNext?.(); return; }
      // "/" focuses the alias filter input when in the aliases tab
      if (e.key === "/" && !isTyping && activeTab === "aliases") {
        e.preventDefault();
        panelRef.current?.querySelector<HTMLInputElement>('[aria-label="Alias\'ları filtrele"]')?.focus();
        return;
      }
      // Number keys 1-6 switch tabs
      if (!isTyping && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const tabKeys: DetailTab[] = ["aliases", "params", "impl", "examples", "related", "ai"];
        const n = parseInt(e.key, 10);
        if (n >= 1 && n <= tabKeys.length) {
          e.preventDefault();
          setActiveTab(tabKeys[n - 1]);
          scrollRef.current?.scrollTo({ top: 0, behavior: "instant" });
        }
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, onPrev, onNext, hasPrev, hasNext, activeTab]);

  // Focus trap: keep Tab navigation within the panel for accessibility
  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    function trapFocus(e: KeyboardEvent) {
      if (e.key !== "Tab") return;
      const focusable = Array.from(
        panel!.querySelectorAll<HTMLElement>(
          'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
    panel.addEventListener("keydown", trapFocus);
    return () => panel.removeEventListener("keydown", trapFocus);
  }, []);

  async function copy(text: string, key: string, toastMsg?: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      // Strip legacy unicode markers — display is handled by ToastContainer icons
      dispatchToast((toastMsg ?? "Kopyalandı").replace(/[✓★⚠]/g, "").trim());
      setTimeout(() => setCopied(null), 1500);
    } catch {
      /* yoksay */
    }
  }

  /** Fills {param} placeholders with user-typed values. Unfilled placeholders stay as-is. */
  function fillGherkin(template: string, vals: Record<string, string>): string {
    return template.replace(/\{([^}]+)\}/g, (_, key) => vals[key] || `{${key}}`);
  }

  // Tab definitions — only show tabs that have content
  const tabDefs: Array<{ key: DetailTab; label: string; count?: number }> = [
    { key: "aliases", label: "Alias'lar", count: totalAliasCount },
    ...((action.parameters?.length ?? 0) > 0
      ? [{ key: "params" as DetailTab, label: "Parametreler", count: action.parameters!.length }]
      : []),
    ...(Object.keys(action.implementations ?? {}).length > 0
      ? [{ key: "impl" as DetailTab, label: "Impl.", count: Object.keys(action.implementations!).length }]
      : []),
    ...((action.examples?.length ?? 0) > 0 || !!action.notes
      ? [{ key: "examples" as DetailTab, label: "Örnekler", count: action.examples?.length ?? undefined }]
      : []),
    ...((relatedActions?.length ?? 0) > 0
      ? [{ key: "related" as DetailTab, label: "İlgili", count: relatedActions!.length }]
      : []),
  ];

  function switchTab(tab: DetailTab) {
    setActiveTab(tab);
    scrollRef.current?.scrollTo({ top: 0, behavior: "instant" });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end bg-black/65 p-0 sm:p-4 backdrop-blur-[2px] animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`${action.id} detayı`}
    >
      <div
        ref={panelRef}
        style={sc ? { borderLeftColor: sc.borderColor, borderLeftWidth: "4px", boxShadow: `0 25px 50px -12px rgba(0,0,0,0.85), 0 0 80px -20px ${sc.borderColor}18` } : undefined}
        className="flex h-full w-full max-w-2xl flex-col overflow-hidden rounded-none border border-slate-800 bg-slate-950 shadow-2xl ring-1 ring-inset ring-white/[0.02] sm:rounded-2xl animate-slide-in-right"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Step-type colored gradient accent at very top of panel */}
        {sc && (
          <div
            className="h-px w-full shrink-0"
            style={{ background: `linear-gradient(90deg, ${sc.borderColor}60 0%, ${sc.borderColor}10 60%, transparent 100%)` }}
            aria-hidden="true"
          />
        )}
        {/* Thin progress line showing position in the result set — colored by step type */}
        {position && position.total > 1 && (
          <div className="h-0.5 w-full shrink-0 bg-slate-900">
            <div
              className="h-full transition-all duration-300"
              style={{
                width: `${Math.round((position.current / position.total) * 100)}%`,
                background: sc
                  ? `linear-gradient(90deg, ${sc.borderColor}90 0%, ${sc.borderColor}30 100%)`
                  : "linear-gradient(90deg, rgba(59,130,246,0.6) 0%, rgba(96,165,250,0.3) 100%)",
              }}
            />
          </div>
        )}

        <div className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-slate-800/80 bg-slate-950/98 p-5 backdrop-blur-md" style={sc ? { background: `linear-gradient(180deg, ${sc.borderColor}06 0%, transparent 100%), rgb(2 6 23 / 0.98)` } : undefined}>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              {sc && (
                <span className={`${BADGE_CLS} ${sc.badgeCls}`}>
                  {st === "given" ? "Ön Koşul" : st === "when" ? "Eylem" : "Doğrulama"}
                </span>
              )}
              {onCategoryClick ? (
                <button
                  type="button"
                  onClick={() => onCategoryClick(action.category.split(".")[0])}
                  className={`${BADGE_CLS} border-slate-700/80 bg-slate-800/80 text-slate-300 hover:bg-slate-700 hover:text-white hover:border-slate-600 transition-all active:scale-[0.94] ring-1 ring-inset ring-white/[0.04] hover:ring-white/[0.06] ${FOCUS_RING}`}
                  title={`${action.category} kategorisine filtrele`}
                >
                  {getCategoryLabel(action.category)}
                </button>
              ) : (
                <span className={`${BADGE_CLS} border-slate-700 bg-slate-800 text-slate-300 ring-1 ring-inset ring-white/[0.03]`}>
                  {getCategoryLabel(action.category)}
                </span>
              )}
              {action.tags?.slice(0, 4).map((t) => (
                <span
                  key={t}
                  className={`${BADGE_CLS} cursor-default border-slate-700/50 bg-slate-800/50 font-mono text-[10px] text-slate-500 ring-1 ring-inset ring-white/[0.02]`}
                  title={`Etiket: #${t}`}
                >
                  #{t}
                </span>
              ))}
              {action.source_yaml && (
                <span
                  className={`${BADGE_CLS} gap-1 border-slate-800/80 bg-slate-900/60 font-mono text-[10px] text-slate-500 ring-1 ring-inset ring-white/[0.02]`}
                  title={`Kaynak: ${action.source_yaml}`}
                >
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5 shrink-0">
                    <rect x="2" y="1" width="6" height="8" rx="1" />
                    <path d="M4 3.5h2M4 5.5h2M4 7h1.5" />
                  </svg>
                  {action.source_yaml}
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={() => copy(action.id, "id", "ID kopyalandı ✓")}
              className={`group/id mt-2 break-all text-left font-mono text-base font-semibold transition-all active:scale-[0.98] hover:text-blue-200 ${FOCUS_RING}`}
              title="ID'yi kopyalamak için tıkla"
            >
              <span className={copied === "id" ? "text-emerald-400" : ""}>{renderActionId(action.id)}</span>
              <span className={`ml-2 inline-flex items-center transition-opacity ${
                copied === "id" ? "text-emerald-400 opacity-100" : "text-slate-600 opacity-0 group-hover/id:opacity-100"
              }`}>
                {copied === "id" ? (
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
                    <path d="M2 5.5l2 2 4-4" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
                    <rect x="1" y="2" width="7" height="7" rx="1" />
                    <path d="M3 1h6v7" />
                  </svg>
                )}
              </span>
            </button>
            {action.since && (() => {
              const isNew = /\b(202[4-9]|0\.[89]|1\.[0-4])\b/.test(action.since);
              return (
                <span className={`mt-1.5 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[9px] transition-colors ring-1 ring-inset ${
                  isNew
                    ? "border-emerald-900/50 bg-emerald-900/20 text-emerald-600 hover:border-emerald-800/60 hover:bg-emerald-900/30 ring-emerald-500/[0.04]"
                    : "border-slate-800/60 bg-slate-900/60 text-slate-600 ring-white/[0.02]"
                }`}>
                  {isNew && (
                    <svg viewBox="0 0 8 8" fill="currentColor" className="h-2 w-2 text-emerald-500">
                      <path d="M4 0l.6 1.8L6.5 2.5l-1.9.7L4 5l-.6-1.8L1.5 2.5l1.9-.7L4 0z" />
                    </svg>
                  )}
                  <span>v{action.since}</span>
                  {isNew && (
                    <span className="rounded-sm bg-emerald-500/20 px-0.5 text-[7px] font-bold tracking-widest text-emerald-500 uppercase">new</span>
                  )}
                </span>
              );
            })()}
            {/* Primary alias preview with param highlights */}
            <div
              className={`mt-2 rounded-lg bg-slate-950/80 px-3 py-2.5 font-mono text-sm text-slate-100 leading-relaxed transition-all ring-1 ring-inset ring-white/[0.02]`}
              style={{
                border: `1px solid ${sc ? sc.borderColor + "30" : "rgba(71,85,105,0.3)"}`,
                boxShadow: sc ? `inset 0 0 24px ${sc.borderColor}0c, inset 1px 0 0 ${sc.borderColor}15` : undefined,
              }}
            >
              <span className={`mr-2 text-[11px] font-bold tracking-wide ${
                st === "given" ? "text-emerald-400" : st === "when" ? "text-blue-400" : st === "then" ? "text-amber-400" : "text-slate-500"
              }`}>
                {detailKw}
              </span>
              {renderParams(detailPrimary)}
            </div>
            {action.description && (
              <p className="mt-1.5 text-xs text-slate-500 leading-relaxed">{action.description}</p>
            )}
            {/* ── Interactive param fill-in widget ── */}
            {(action.parameters?.length ?? 0) > 0 && (
              <div className="mt-2.5 rounded-lg border border-blue-500/15 bg-blue-500/[0.03] p-2.5 ring-1 ring-inset ring-blue-500/[0.04]">
                <div className="mb-2 flex items-center gap-1.5">
                  <span className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-500">
                    <svg viewBox="0 0 10 10" fill="currentColor" className="h-2.5 w-2.5 text-blue-400/60">
                      <path d="M5.5 1L2 6h3.5L4.5 9l4-5H5L5.5 1z" />
                    </svg>
                    Doldur &amp; Kopyala
                  </span>
                  {Object.values(paramValues).some(Boolean) && (
                    <button
                      type="button"
                      onClick={() => setParamValues({})}
                      className={`ml-auto text-[10px] text-slate-600 hover:text-slate-400 transition-all active:scale-95 ${FOCUS_RING}`}
                    >
                      Temizle
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {action.parameters?.map((p) => (
                    <div key={p.name} className="flex overflow-hidden rounded-md border border-slate-700/50 shadow-sm shadow-black/10 ring-1 ring-inset ring-white/[0.02] transition-all focus-within:border-blue-500/40 focus-within:ring-blue-500/[0.08]">
                      <span className="shrink-0 border-r border-slate-700/50 bg-slate-900/80 px-1.5 py-1 font-mono text-[10px] text-slate-500">
                        {p.name}
                      </span>
                      <input
                        type="text"
                        value={paramValues[p.name] ?? ""}
                        onChange={(e) => setParamValues((prev) => ({ ...prev, [p.name]: e.target.value }))}
                        placeholder={
                          p.examples && p.examples.length > 0
                            ? String(p.examples[0])
                            : `${p.name}…`
                        }
                        className="w-24 bg-slate-900/80 px-2 py-1 font-mono text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none focus:bg-slate-800/60"
                        aria-label={`${p.name} parametresi`}
                      />
                    </div>
                  ))}
                </div>
                {Object.values(paramValues).some(Boolean) && (
                  <div className="mt-2 flex items-start gap-2 animate-fade-in">
                    <div className="min-w-0 flex-1 rounded border border-slate-700/30 bg-slate-900/60 px-2.5 py-1.5 font-mono text-[11px] leading-relaxed text-slate-100 break-all ring-1 ring-inset ring-white/[0.03]">
                      <span className={`mr-1.5 text-[10px] font-semibold ${
                        st === "given" ? "text-emerald-400" : st === "when" ? "text-blue-400" : st === "then" ? "text-amber-400" : "text-slate-600"
                      }`}>{detailKw}</span>
                      {fillGherkin(detailPrimary, paramValues)}
                    </div>
                    <button
                      type="button"
                      onClick={() => copy(`${detailKw} ${fillGherkin(detailPrimary, paramValues)}`, "param-filled", "Doldurulmuş adım kopyalandı ✓")}
                      className={`flex shrink-0 items-center justify-center rounded border px-2 py-1 transition-all active:scale-90 ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
                        copied === "param-filled"
                          ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400 ring-emerald-500/[0.08]"
                          : "border-slate-700 bg-slate-900 text-slate-500 hover:bg-slate-800 hover:text-slate-200 ring-white/[0.03]"
                      }`}
                      title="Doldurulmuş Gherkin adımını kopyala"
                    >
                      {copied === "param-filled" ? (
                        <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                          <path d="M2 5.5l2 2 4-4" />
                        </svg>
                      ) : (
                        <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                          <rect x="1" y="2" width="7" height="7" rx="1" />
                          <path d="M3 1h6v7" />
                        </svg>
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}
            {action.deprecated && (() => {
              const depObj = typeof action.deprecated === "object" ? action.deprecated : null;
              const depReplacement = depObj?.replacement ?? null;
              const depStr = typeof action.deprecated === "string" && action.deprecated !== "true" ? action.deprecated : null;
              return (
                <div className="mt-2 rounded-md border border-red-800/40 bg-red-900/10 px-2.5 py-2 ring-1 ring-inset ring-red-500/[0.04]">
                  <div className="flex items-start gap-2 text-xs text-red-300">
                    <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-400">
                      <path d="M5 1.5L1 8.5h8L5 1.5z" />
                      <path d="M5 4v2M5 7.5v.5" />
                    </svg>
                    <div className="min-w-0 flex-1">
                      <span className="font-semibold">Kullanımdan kaldırıldı</span>
                      {depReplacement && (
                        <span className="ml-1 text-red-300/70">
                          — yerine{" "}
                          <code className="font-mono text-red-200">{depReplacement}</code>
                          {" "}kullanın
                        </span>
                      )}
                      {depStr && (
                        <span className="ml-1 text-red-300/70">: {depStr}</span>
                      )}
                    </div>
                    {depReplacement && (
                      <button
                        type="button"
                        onClick={() => copy(depReplacement, "deprecated-replacement", "Yeni cümlecik ID'si kopyalandı ✓")}
                        className={`shrink-0 rounded border border-red-700/30 bg-red-900/20 px-1.5 py-0.5 text-[10px] transition-all active:scale-90 hover:bg-red-900/40 ring-1 ring-inset ring-red-500/[0.05] shadow-sm shadow-black/10 ${FOCUS_RING}`}
                      >
                        {copied === "deprecated-replacement" ? (
                        <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5 text-emerald-400">
                          <path d="M2 5.5l2 2 4-4" />
                        </svg>
                      ) : (
                        <span className="flex items-center gap-1">
                          <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                            <rect x="1" y="2" width="7" height="7" rx="1" />
                            <path d="M3 1h6v7" />
                          </svg>
                          ID
                        </span>
                      )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })()}
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <div className="flex items-center gap-1">
              {(hasPrev || hasNext) && (
                <>
                  <button
                    type="button"
                    onClick={onPrev}
                    disabled={!hasPrev}
                    className={`rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed active:scale-[0.93] ring-1 ring-inset ring-white/[0.03] shadow-sm shadow-black/10 transition-all ${FOCUS_RING}`}
                    title="Önceki (←)"
                    aria-label="Önceki cümlecik"
                  >
                    <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                      <path d="M6.5 2l-3 3 3 3" />
                    </svg>
                  </button>
                  {position && (
                    <span
                      className="min-w-[3.5rem] rounded border border-slate-800/60 bg-slate-900/60 px-1.5 py-0.5 text-center font-mono text-[10px] text-slate-500 ring-1 ring-inset ring-white/[0.02]"
                      title={`${position.current}. cümlecik (toplam ${position.total})`}
                    >
                      <span className="text-slate-300">{position.current}</span>
                      <span className="text-slate-500">/{position.total}</span>
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={onNext}
                    disabled={!hasNext}
                    className={`rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed active:scale-[0.93] ring-1 ring-inset ring-white/[0.03] shadow-sm shadow-black/10 transition-all ${FOCUS_RING}`}
                    title="Sonraki (→)"
                    aria-label="Sonraki cümlecik"
                  >
                    <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                      <path d="M3.5 2l3 3-3 3" />
                    </svg>
                  </button>
                </>
              )}
              <button
                ref={closeBtnRef}
                type="button"
                className={`flex h-7 w-7 items-center justify-center rounded-lg border border-slate-700/80 bg-slate-900/80 text-slate-400 transition-all hover:bg-slate-800 hover:text-slate-200 hover:border-slate-600 hover:scale-105 active:scale-95 ring-1 ring-inset ring-white/[0.04] ${FOCUS_RING}`}
                onClick={onClose}
                aria-label="Kapat (Esc)"
                title="Kapat (Esc)"
              >
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-3 w-3">
                  <path d="M2 2l6 6M8 2l-6 6" />
                </svg>
              </button>
            </div>
            {/* ── Primary action buttons (flex-wrap row) ── */}
            <div className="flex flex-wrap justify-end gap-1">
              <Link
                href={`/dsl-catalog/editor/${encodeURIComponent(action.id)}`}
                className={`flex items-center gap-1.5 rounded-lg border border-blue-500/40 bg-blue-500/10 px-2.5 py-1 text-xs text-blue-200 hover:bg-blue-500/20 active:scale-[0.97] ring-1 ring-inset ring-blue-500/[0.08] transition-all shadow-sm shadow-black/10 ${FOCUS_RING}`}
                data-testid={`dsl-edit-${action.id}`}
              >
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                  <path d="M7 1.5l1.5 1.5-5 5L2 8.5l.5-1.5 5-5z" />
                </svg>
                Düzenle
              </Link>
              <button
                type="button"
                onClick={() => copy(detailGherkin, "gherkin")}
                className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs transition-all active:scale-[0.97] ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
                  copied === "gherkin"
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300 ring-emerald-500/[0.08]"
                    : sc
                    ? "border-slate-700 bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200 ring-white/[0.03]"
                    : "border-slate-700 bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200 ring-white/[0.03]"
                }`}
                style={copied !== "gherkin" && sc ? { borderColor: sc.borderColor + "30" } : undefined}
                title={`Gherkin adımı kopyala: ${detailGherkin}`}
              >
                {copied === "gherkin" ? (
                  <>
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    <span>Kopyalandı</span>
                  </>
                ) : (
                  <>
                    <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2.5 w-2.5">
                      <rect x="1" y="2" width="7" height="7" rx="1" />
                      <path d="M3 1h6v7" />
                    </svg>
                    Gherkin
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={() => {
                  const trAliases = action.aliases?.tr ?? [];
                  const params = (action.parameters ?? []).map((p) => `      And ${detailKw} ${p.name}: <${p.name}>`).join("\n");
                  const examples = trAliases.length > 1
                    ? `\n  Examples:\n    | alias |\n${trAliases.slice(0, 3).map((a) => `    | ${a} |`).join("\n")}`
                    : "";
                  const feature = [
                    `Feature: ${action.id}`,
                    `  # ${action.description ?? ""}`,
                    ``,
                    `  Scenario: ${detailPrimary}`,
                    `    ${detailGherkin}`,
                    ...(params ? [params] : []),
                    ...(examples ? [examples] : []),
                  ].join("\n");
                  copy(feature, "feature", "Feature dosyası kopyalandı ✓");
                }}
                className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs transition-all active:scale-[0.97] ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
                  copied === "feature"
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300 ring-emerald-500/[0.08]"
                    : "border-slate-700 bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200 ring-white/[0.03]"
                }`}
                title="Feature dosyası şablonu olarak kopyala"
              >
                {copied === "feature" ? (
                  <>
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    <span>Kopyalandı</span>
                  </>
                ) : (
                  <>
                    <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                      <rect x="2" y="1" width="6" height="8" rx="1" />
                      <path d="M4 3.5h2M4 5.5h2M4 7h1.5" />
                    </svg>
                    Feature
                  </>
                )}
              </button>
              {onToggleFavorite && (
                <button
                  type="button"
                  onClick={() => onToggleFavorite(action.id)}
                  className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs transition-all active:scale-[0.97] ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
                    isFavorite
                      ? "border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 ring-amber-500/[0.08]"
                      : "border-slate-700 bg-slate-900 text-slate-400 hover:border-amber-500/30 hover:text-amber-300 ring-white/[0.03]"
                  }`}
                  title={isFavorite ? "Favorilerden çıkar (f)" : "Favorilere ekle (f)"}
                  aria-pressed={isFavorite}
                >
                  <svg viewBox="0 0 10 10" fill={isFavorite ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                    <path d="M5 1l1.2 2.5L9 3.8l-2 2 .5 2.7L5 7.2 2.5 8.5 3 5.8 1 3.8l2.8-.3L5 1z" />
                  </svg>
                  {isFavorite ? "Favoride" : "Favori"}
                </button>
              )}
            </div>
            {/* ── Secondary actions (compact text row) ── */}
            <div className="flex items-center gap-0.5">
              <button
                type="button"
                onClick={() => copy(JSON.stringify(action, null, 2), "json", "JSON kopyalandı ✓")}
                className={`flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] transition-all active:scale-95 ${FOCUS_RING} ${
                  copied === "json" ? "text-emerald-400" : "text-slate-600 hover:text-slate-400"
                }`}
                title="Cümleciği JSON olarak kopyala"
              >
                {copied === "json" ? (
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                    <path d="M2 5.5l2 2 4-4" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                    <path d="M2 3.5h1.5M2 5h3M2 6.5h2M6.5 2v6M6.5 2l1.5 1.5M6.5 8l1.5-1.5" />
                  </svg>
                )}
                <span>JSON</span>
              </button>
              <span className="text-slate-800/60 select-none">·</span>
              <button
                type="button"
                onClick={() => {
                  const url = new URL(window.location.href);
                  url.searchParams.set("action", action.id);
                  copy(url.toString(), "share", "Bağlantı kopyalandı ✓");
                }}
                className={`flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] transition-all active:scale-95 ${FOCUS_RING} ${
                  copied === "share" ? "text-emerald-400" : "text-slate-600 hover:text-slate-400"
                }`}
                title="Bu cümleciğe direkt bağlantıyı kopyala"
              >
                {copied === "share" ? (
                  <>
                    <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                      <path d="M2 5.5l2 2 4-4" />
                    </svg>
                    <span>Bağlantı</span>
                  </>
                ) : (
                  <>
                    <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                      <circle cx="2.5" cy="5" r="1.5" />
                      <circle cx="7.5" cy="2" r="1.5" />
                      <circle cx="7.5" cy="8" r="1.5" />
                      <path d="M4 4.2l2-1.5M4 5.8l2 1.5" />
                    </svg>
                    <span>Paylaş</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* ─── Tab navigation bar ─── */}
        <div
          className="sticky top-0 z-10 flex shrink-0 items-center overflow-x-auto border-b border-slate-800 bg-slate-950/95 px-3 backdrop-blur-sm [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          role="tablist"
          aria-label="Detay bölümleri (1-6 tuşlarıyla geçiş)"
        >
          {tabDefs.map(({ key, label, count }, tabIdx) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={activeTab === key}
              onClick={() => switchTab(key)}
              title={`${label} (${tabIdx + 1})`}
              className={`group/tab relative shrink-0 whitespace-nowrap px-3 py-2.5 text-xs font-medium transition-all active:scale-[0.97] ${FOCUS_RING} ${
                activeTab === key
                  ? "border-b-2 text-white"
                  : "border-b-2 border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-700/60 hover:bg-slate-900/50"
              }`}
              style={activeTab === key ? { borderBottomColor: tabActiveBorderColor } : undefined}
            >
              {label}
              <sup className="ml-0.5 select-none text-[7px] opacity-0 transition-opacity group-hover/tab:opacity-30">
                {tabIdx + 1}
              </sup>
              {count !== undefined && count > 0 && (
                <span
                  className={`ml-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold transition-colors ring-1 ring-inset ${
                    activeTab === key
                      ? "text-white/70 ring-white/[0.06]"
                      : "bg-slate-800/80 text-slate-500 ring-white/[0.02]"
                  }`}
                  style={activeTab === key ? { backgroundColor: tabActiveBorderColor + "25", color: tabActiveBorderColor } : undefined}
                >
                  {count}
                </span>
              )}
            </button>
          ))}
          {/* AI tab — always visible, right-aligned */}
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "ai"}
            onClick={() => switchTab("ai")}
            title={`AI Alias Önerileri (${tabDefs.length + 1})`}
            className={`relative ml-auto shrink-0 whitespace-nowrap px-3 py-2.5 text-xs font-medium transition-all active:scale-[0.97] ${FOCUS_RING} ${
              activeTab === "ai"
                ? "border-b-2 border-violet-500 text-violet-200"
                : "border-b-2 border-transparent text-slate-600 hover:text-violet-400 hover:border-violet-500/30"
            }`}
          >
            <span className="flex items-center gap-1">
              <svg viewBox="0 0 10 10" fill="currentColor" className={`h-2.5 w-2.5 ${activeTab === "ai" ? "text-violet-400" : "text-current"}`}>
                <path d="M5 1l.8 2.2L8 4l-2.2.8L5 7l-.8-2.2L2 4l2.2-.8L5 1z" />
              </svg>
              <span>AI</span>
            </span>
          </button>
        </div>

        {/* ─── Tab content ─── */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-5 text-sm [scrollbar-width:thin] [scrollbar-color:theme(colors.slate.800)_theme(colors.slate.950)]"
          role="tabpanel"
          aria-label={tabDefs.find((t) => t.key === activeTab)?.label ?? activeTab}
        >
        {/* keyed div so content fades in on every tab switch */}
        <div key={activeTab} className="animate-fade-in pb-2">

          {/* ── ALIASES tab ── */}
          {activeTab === "aliases" && (
            <section className="animate-fade-in">
              <div className="mb-2 flex items-center justify-between gap-2">
                <h3 className="shrink-0 font-semibold text-slate-100 tracking-tight">
                  Alias'lar
                  <span className="ml-2 text-xs font-normal text-slate-500">
                    ({totalAliasCount} toplam)
                  </span>
                </h3>
                <div className="flex items-center gap-2">
                  {totalAliasCount > 8 && (
                    <div className="relative flex items-center">
                      <input
                        type="search"
                        value={aliasFilter}
                        onChange={(e) => setAliasFilter(e.target.value)}
                        placeholder="Filtrele…"
                        className="rounded-md border border-slate-700 bg-slate-900 px-2 py-0.5 pr-6 text-xs text-slate-300 placeholder-slate-600 shadow-inner shadow-black/10 ring-1 ring-inset ring-white/[0.03] focus:outline-none focus:border-blue-500/40 focus:ring-blue-500/15 transition-colors"
                        aria-label="Alias'ları filtrele"
                      />
                      {!aliasFilter && (
                        <kbd className="pointer-events-none absolute right-1.5 rounded border border-slate-700/60 bg-slate-800/40 px-1 py-0.5 font-mono text-[8px] text-slate-600 ring-1 ring-inset ring-white/[0.03]">
                          /
                        </kbd>
                      )}
                      {aliasFilter && (
                        <button
                          type="button"
                          onClick={() => setAliasFilter("")}
                          className="absolute right-1.5 flex items-center justify-center text-slate-600 hover:text-slate-300 transition-all active:scale-75"
                          aria-label="Filtreyi temizle"
                        >
                          <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2.5 w-2.5">
                            <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" />
                          </svg>
                        </button>
                      )}
                    </div>
                  )}
                  {totalAliasCount > 0 && (
                    <>
                      <button
                        type="button"
                        className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] transition-all active:scale-[0.94] ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
                          copied === "all:all"
                            ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400 ring-emerald-500/[0.06]"
                            : "border-slate-800 text-slate-600 hover:border-emerald-500/30 hover:text-emerald-400 ring-white/[0.02]"
                        }`}
                        onClick={() => {
                          const lines = Object.values(action.aliases ?? {})
                            .flat()
                            .map((alias) => `${detailKw} ${alias}`);
                          copy(lines.join("\n"), "all:all", "Tüm Gherkin adımları kopyalandı ✓");
                        }}
                        title="Tüm alias'ları Gherkin adımları olarak kopyala"
                      >
                        {copied === "all:all" ? (
                          <span className="flex items-center gap-1">
                            <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                              <path d="M2 5.5l2 2 4-4" />
                            </svg>
                            Kopyalandı
                          </span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                              <rect x="1" y="2" width="7" height="7" rx="1" />
                              <path d="M3 1h6v7" />
                            </svg>
                            Gherkin
                          </span>
                        )}
                      </button>
                      {totalAliasCount > 3 && (
                        <span className="text-[9px] font-mono text-slate-600">
                          {totalAliasCount} alias
                        </span>
                      )}
                    </>
                  )}
                </div>
              </div>
              {Object.entries(action.aliases ?? {}).map(([lang, arr]) => {
                const filtered = aliasFilter
                  ? arr.filter((a) => a.toLowerCase().includes(aliasFilter.toLowerCase()))
                  : arr;
                if (aliasFilter && filtered.length === 0) return null;
                const langBadge = lang === "tr"
                  ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-500 ring-1 ring-inset ring-emerald-500/[0.05]"
                  : lang === "en"
                  ? "border-blue-500/20 bg-blue-500/5 text-blue-500 ring-1 ring-inset ring-blue-500/[0.05]"
                  : "border-slate-700 bg-slate-800 text-slate-400 ring-1 ring-inset ring-white/[0.03]";
                return (
                  <div key={lang} className="mb-4">
                    <div className="mb-1.5 flex items-center justify-between">
                      <span className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${langBadge}`}>
                        <span className={`inline-flex h-3 w-3 items-center justify-center rounded-sm font-bold text-[6px] leading-none ${
                          lang === "tr" ? "bg-emerald-500/20 text-emerald-400" : lang === "en" ? "bg-blue-500/20 text-blue-400" : "bg-slate-700/60 text-slate-400"
                        }`}>{lang.toUpperCase().slice(0, 2)}</span>
                        <span>{lang}</span>
                        <span className={`rounded-sm px-1 text-[9px] font-bold ${
                          lang === "tr" ? "bg-emerald-500/10" : lang === "en" ? "bg-blue-500/10" : "bg-slate-700/60"
                        }`}>
                          {aliasFilter ? `${filtered.length}/${arr.length}` : arr.length}
                        </span>
                      </span>
                      <button
                        type="button"
                        className={`rounded border px-1.5 py-0.5 text-[10px] transition-all active:scale-[0.94] ring-1 ring-inset ${FOCUS_RING} ${
                          copied === `all:${lang}` ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-400 ring-emerald-500/[0.06]" : "border-transparent text-slate-600 hover:border-slate-700/60 hover:text-slate-300 ring-transparent"
                        }`}
                        onClick={() => copy(filtered.join("\n"), `all:${lang}`, `${lang.toUpperCase()} alias'ları kopyalandı ✓`)}
                        title={`Tüm ${lang} alias'larını kopyala (${filtered.length} adet)`}
                      >
                        {copied === `all:${lang}` ? (
                          <span className="flex items-center gap-1 text-emerald-400">
                            <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                              <path d="M2 5.5l2 2 4-4" />
                            </svg>
                            Tümü
                          </span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                              <rect x="1" y="2" width="7" height="7" rx="1" />
                              <path d="M3 1h6v7" />
                            </svg>
                            Tümü
                          </span>
                        )}
                      </button>
                    </div>
                    <ul className="space-y-1">
                      {filtered.map((alias, idx) => {
                        const isPrimaryAlias = idx === 0 && !aliasFilter;
                        return (
                        <li
                          key={alias}
                          className="group/alias flex items-start gap-1.5 animate-fade-in"
                          style={{ animationDelay: `${Math.min(idx * 30, 150)}ms`, animationFillMode: "both" }}
                        >
                          <span className="mt-2 w-4 shrink-0 text-right font-mono text-[10px] text-slate-600 select-none">
                            {isPrimaryAlias ? (
                              <span className="inline-flex h-3 w-3 items-center justify-center rounded-full" style={{ backgroundColor: (lang === "tr" ? "#10b981" : "#3b82f6") + "30", color: lang === "tr" ? "#10b981" : "#3b82f6" }}>
                                <svg viewBox="0 0 6 6" fill="currentColor" className="h-1.5 w-1.5"><circle cx="3" cy="3" r="2" /></svg>
                              </span>
                            ) : idx + 1}
                          </span>
                          <button
                            type="button"
                            className={`flex-1 rounded-md border px-2 py-1.5 text-left font-mono text-xs leading-relaxed transition-all active:scale-[0.995] ring-1 ring-inset ${FOCUS_RING} ${
                              copied === `${lang}:${alias}`
                                ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-100 ring-emerald-500/[0.06]"
                                : isPrimaryAlias
                                ? "border-slate-700/60 bg-slate-900 text-white hover:border-slate-600/70 hover:bg-slate-800/70 ring-white/[0.04]"
                                : "border-slate-800/80 bg-slate-900/80 text-white hover:border-slate-700/60 hover:bg-slate-800/60 ring-white/[0.02]"
                            }`}
                            onClick={() => copy(alias, `${lang}:${alias}`, "Alias kopyalandı ✓")}
                            title={isPrimaryAlias ? "Birincil alias — kopyalamak için tıkla" : "Kopyalamak için tıkla"}
                          >
                            {aliasFilter ? renderHighlight(alias, aliasFilter) : renderParams(alias)}
                          </button>
                          {/* Copy icon — appears on hover */}
                          <span className={`self-center shrink-0 transition-all duration-150 ${
                            copied === `${lang}:${alias}`
                              ? "text-emerald-400 opacity-100"
                              : "text-slate-600 opacity-0 group-hover/alias:opacity-100"
                          }`}>
                            {copied === `${lang}:${alias}` ? (
                              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
                                <path d="M2 5.5l2 2 4-4" />
                              </svg>
                            ) : (
                              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
                                <rect x="1" y="2" width="7" height="7" rx="1" />
                                <path d="M3 1h6v7" />
                              </svg>
                            )}
                          </span>
                          {/* GWT copy button — copies "Given/When/Then alias" */}
                          <button
                            type="button"
                            className={`self-center shrink-0 rounded border px-1.5 py-0.5 text-[9px] font-semibold transition-all active:scale-90 opacity-0 group-hover/alias:opacity-100 ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
                              st === "given"
                                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 ring-emerald-500/[0.06]"
                                : st === "when"
                                ? "border-blue-500/30 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 ring-blue-500/[0.06]"
                                : st === "then"
                                ? "border-amber-500/30 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 ring-amber-500/[0.06]"
                                : "border-slate-700 bg-slate-800 text-slate-500 hover:text-slate-300 ring-white/[0.03]"
                            }`}
                            onClick={() => copy(`${detailKw} ${alias}`, `gwt:${lang}:${alias}`, `${detailKw} adımı kopyalandı ✓`)}
                            title={`"${detailKw} ${alias}" olarak kopyala`}
                          >
                            {copied === `gwt:${lang}:${alias}` ? (
                              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                                <path d="M2 5.5l2 2 4-4" />
                              </svg>
                            ) : detailKw}
                          </button>
                        </li>
                        );
                      })}
                    </ul>
                  </div>
                );
              })}
              {/* Empty alias filter state */}
              {aliasFilter && Object.values(action.aliases ?? {}).every(
                (arr) => arr.filter((a) => a.toLowerCase().includes(aliasFilter.toLowerCase())).length === 0
              ) && (
                <div className="rounded-lg border border-dashed border-slate-700/60 py-4 text-center text-xs text-slate-600">
                  <p>&ldquo;{aliasFilter}&rdquo; için eşleşen alias bulunamadı</p>
                  <button
                    type="button"
                    onClick={() => setAliasFilter("")}
                    className={`mt-1 text-slate-500 hover:text-slate-300 transition-all active:scale-95 ${FOCUS_RING}`}
                  >
                    Filtreyi temizle
                  </button>
                </div>
              )}
              {/* Empty aliases state — no aliases at all */}
              {!aliasFilter && Object.keys(action.aliases ?? {}).length === 0 && (
                <div className="flex flex-col items-center py-10 text-center animate-fade-in">
                  <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-800/60 bg-slate-900/60 ring-1 ring-inset ring-white/[0.03]">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6 text-slate-500">
                      <rect x="3" y="4" width="14" height="14" rx="2" />
                      <path d="M7 8h6M7 11h4" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-slate-500">Henüz alias yok</p>
                  <p className="mt-1 text-xs text-slate-600">Bu cümleciğe alias eklemek için düzenle</p>
                  <Link
                    href={`/dsl-catalog/editor/${encodeURIComponent(action.id)}`}
                    className={`mt-3 inline-flex items-center gap-1.5 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 text-xs text-blue-300 hover:bg-blue-500/20 ring-1 ring-inset ring-blue-500/[0.06] shadow-sm shadow-black/10 transition-all active:scale-[0.97] ${FOCUS_RING}`}
                  >
                    <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                      <path d="M7 1.5l1.5 1.5-5 5L2 8.5l.5-1.5 5-5z" />
                    </svg>
                    Alias Ekle
                  </Link>
                </div>
              )}
            </section>
          )}

          {/* ── PARAMETERS tab ── */}
          {activeTab === "params" && (action.parameters?.length ?? 0) > 0 && (
            <section className="animate-fade-in">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="font-semibold text-slate-100 tracking-tight">Parametreler</h3>
                {/* Fill completion indicator */}
                {(action.parameters?.length ?? 0) > 0 && (
                  <div className="flex items-center gap-2 text-[10px] text-slate-600">
                    <span className="tabular-nums">
                      <span className="text-blue-400 font-medium">
                        {Object.values(paramValues).filter(Boolean).length}
                      </span>
                      /{action.parameters!.length} dolu
                    </span>
                    <div className="h-1 w-16 overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-300"
                        style={{
                          width: `${Math.round((Object.values(paramValues).filter(Boolean).length / action.parameters!.length) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
              {/* Live fill preview — bridges the header fill widget to the params tab */}
              {Object.values(paramValues).some(Boolean) && (
                <div className="mb-4 flex items-start gap-2 rounded-lg border border-blue-500/20 bg-blue-500/5 px-3 py-2.5 ring-1 ring-inset ring-blue-500/[0.04] animate-fade-in">
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 text-[10px] font-semibold text-blue-400/60">Önizleme</div>
                    <div className="font-mono text-xs text-slate-100 leading-relaxed break-all">
                      <span className={`mr-1.5 text-[10px] font-semibold ${
                        st === "given" ? "text-emerald-400" : st === "when" ? "text-blue-400" : st === "then" ? "text-amber-400" : "text-slate-600"
                      }`}>{detailKw}</span>
                      {fillGherkin(detailPrimary, paramValues)}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => copy(`${detailKw} ${fillGherkin(detailPrimary, paramValues)}`, "param-filled", "Doldurulmuş adım kopyalandı ✓")}
                    className={`flex shrink-0 items-center justify-center rounded border px-2 py-1 transition-all active:scale-[0.94] ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
                      copied === "param-filled"
                        ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400 ring-emerald-500/[0.08]"
                        : "border-blue-500/20 bg-blue-500/10 text-blue-300 hover:bg-blue-500/20 ring-blue-500/[0.05]"
                    }`}
                  >
                    {copied === "param-filled" ? (
                      <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                        <path d="M2 5.5l2 2 4-4" />
                      </svg>
                    ) : (
                      <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                        <rect x="1" y="2" width="7" height="7" rx="1" />
                        <path d="M3 1h6v7" />
                      </svg>
                    )}
                  </button>
                </div>
              )}
              <div className="overflow-hidden rounded-lg border border-slate-800 ring-1 ring-inset ring-white/[0.02]">
                <table className="w-full text-xs">
                  <thead className="bg-slate-900/80 text-[11px] text-slate-500">
                    <tr className="border-b border-slate-800">
                      <th className="px-3 py-2 text-left font-semibold text-slate-400">Ad</th>
                      <th className="px-3 py-2 text-left font-semibold text-slate-400">Tip</th>
                      <th className="px-3 py-2 text-center font-semibold text-slate-400" title="Zorunlu mu?">Zorunlu</th>
                      <th className="px-3 py-2 text-left font-semibold text-slate-400">Varsayılan</th>
                      <th className="px-3 py-2 text-left font-semibold text-slate-400">Açıklama &amp; Örnekler</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(action.parameters ?? []).map((p) => (
                      <tr key={p.name} className="group/row border-t border-slate-800/60 transition-colors hover:bg-slate-800/30">
                        <td className="px-3 py-2.5 font-mono text-[11px] font-semibold text-white">
                          <div className="flex flex-col gap-1">
                            <span className="rounded border border-slate-700/50 bg-slate-800/60 px-1.5 py-0.5 ring-1 ring-inset ring-white/[0.03] shadow-sm shadow-black/10">{p.name}</span>
                            {/* Inline fill input — synced with the header fill widget */}
                            <input
                              type="text"
                              value={paramValues[p.name] ?? ""}
                              onChange={(e) => setParamValues((prev) => ({ ...prev, [p.name]: e.target.value }))}
                              placeholder={p.examples?.[0] ? String(p.examples[0]) : "değer…"}
                              className="w-24 rounded border border-slate-700/30 bg-slate-900/60 px-1.5 py-0.5 font-mono text-[10px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500/40 focus:ring-1 focus:ring-blue-500/20 opacity-0 group-hover/row:opacity-100 transition-opacity"
                              aria-label={`${p.name} değeri`}
                            />
                          </div>
                        </td>
                        <td className="px-3 py-2.5">
                          {p.type ? (
                            <code className="rounded border border-sky-500/20 bg-sky-500/[0.06] px-1.5 py-0.5 font-mono text-[10px] text-sky-400/90 ring-1 ring-inset ring-sky-500/[0.04]">
                              {p.type}
                            </code>
                          ) : <span className="font-mono text-[11px] text-slate-600">—</span>}
                        </td>
                        <td className="px-3 py-2.5 text-center">
                          {p.required === false
                            ? <span className="inline-flex items-center justify-center rounded-full border border-slate-800/60 bg-slate-900/60 px-1.5 py-0.5 text-[9px] text-slate-600 ring-1 ring-inset ring-white/[0.02]">opt</span>
                            : (
                              <span className="inline-flex items-center justify-center rounded-full border border-emerald-500/25 bg-emerald-500/[0.07] px-1.5 py-0.5 ring-1 ring-inset ring-emerald-500/[0.05]">
                                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5 text-emerald-400">
                                  <path d="M2 5.5l2 2 4-4" />
                                </svg>
                              </span>
                            )}
                        </td>
                        <td className="px-3 py-2.5 font-mono text-[11px] text-slate-500">
                          {p.default != null
                            ? <code className="rounded border border-slate-700/40 bg-slate-800/40 px-1 py-0.5 text-slate-300 shadow-sm shadow-black/10 ring-1 ring-inset ring-white/[0.03]">{String(p.default)}</code>
                            : <span className="text-slate-600">—</span>
                          }
                        </td>
                        <td className="px-3 py-2.5 text-[11px] text-slate-400">
                          {p.description ?? <span className="text-slate-600">—</span>}
                          {p.examples && p.examples.length > 0 && (
                            <div className="mt-1.5 flex flex-wrap gap-1">
                              {p.examples.slice(0, 3).map((ex, ei) => (
                                <button
                                  key={ei}
                                  type="button"
                                  onClick={() => setParamValues((prev) => ({ ...prev, [p.name]: String(ex) }))}
                                  className={`rounded border px-1 py-0.5 font-mono text-[10px] transition-all active:scale-90 hover:border-blue-500/30 hover:bg-blue-500/10 hover:text-blue-300 ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
                                    paramValues[p.name] === String(ex) ? "border-blue-500/30 bg-blue-500/10 text-blue-300 ring-blue-500/[0.06]" : "border-slate-700/50 bg-slate-800/60 text-slate-400 ring-white/[0.02]"
                                  }`}
                                  title={`"${ex}" değerini kullan`}
                                >
                                  {String(ex)}
                                </button>
                              ))}
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* ── IMPLEMENTATIONS tab ── */}
          {activeTab === "impl" && (
            <section className="animate-fade-in">
              <h3 className="mb-3 font-semibold text-slate-100 tracking-tight">Implementation'lar</h3>
              {Object.keys(action.implementations ?? {}).length === 0 ? (
                <div className="flex flex-col items-center py-10 text-center animate-fade-in">
                  <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-800/60 bg-slate-900/60 ring-1 ring-inset ring-white/[0.03]">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6 text-slate-500">
                      <rect x="2" y="4" width="16" height="12" rx="2" />
                      <path d="M7 8l2.5 2-2.5 2M11 12h2" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-slate-500">Implementation bulunamadı</p>
                  <p className="mt-1 text-xs text-slate-600">Bu cümleciğe uygulama kodu eklenmemiş</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {Object.entries(action.implementations ?? {}).map(([lang, impl]) => {
                    const fnName = impl.function ?? impl.method;
                    // Pretty-print the file path as breadcrumbs
                    const pathParts = impl.source_file?.split(/[/\\]/) ?? [];
                    const shortPath = pathParts.length > 3
                      ? `…/${pathParts.slice(-3).join("/")}`
                      : impl.source_file;
                    return (
                      <div key={lang} className="overflow-hidden rounded-lg border border-slate-800 ring-1 ring-inset ring-white/[0.02]">
                        {/* Header: lang badge + function name */}
                        <div className={`flex items-center justify-between gap-3 border-b border-slate-800/60 px-3 py-2.5 ${
                          lang === "python"
                            ? "bg-gradient-to-r from-yellow-900/25 via-yellow-900/10 to-slate-900"
                            : lang === "java"
                            ? "bg-gradient-to-r from-orange-900/25 via-orange-900/10 to-slate-900"
                            : lang === "typescript"
                            ? "bg-gradient-to-r from-sky-900/25 via-sky-900/10 to-slate-900"
                            : "bg-slate-900"
                        }`}>
                          <span className={`${BADGE_CLS} ${IMPL_BADGE[lang] ?? "border-slate-600 bg-slate-800 text-slate-300 ring-1 ring-inset ring-white/[0.03]"}`}>
                            {lang}
                          </span>
                          {fnName && (
                            <code className="flex-1 truncate rounded border border-slate-700/30 bg-slate-900/60 px-1.5 py-0.5 text-right font-mono text-[11px] text-slate-300 ring-1 ring-inset ring-white/[0.02]">
                              {fnName}
                            </code>
                          )}
                        </div>
                        {/* Pattern — styled as regex code block with basic coloring */}
                        {impl.pattern && (
                          <div className="group/pattern relative bg-slate-950 px-3 py-2.5 shadow-inner shadow-black/25 ring-1 ring-inset ring-white/[0.015]">
                            <div className="mb-2 flex items-center gap-2">
                              <span className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest text-slate-600">
                                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5 text-slate-600">
                                  <path d="M3.5 3L1.5 5l2 2M6.5 3l2 2-2 2M5 2l-1 6" />
                                </svg>
                                Pattern
                              </span>
                              <span className="rounded border border-slate-800/60 bg-slate-900/60 px-1 py-0.5 text-[8px] font-mono text-slate-500 ring-1 ring-inset ring-white/[0.03]">Regex</span>
                            </div>
                            <code className="block font-mono text-[11px] break-all leading-relaxed">
                              {(() => {
                                // Basic regex syntax coloring: groups (), quantifiers *+?{}, char classes []
                                const pat = impl.pattern!;
                                const tokens: Array<{ text: string; cls: string }> = [];
                                let i = 0;
                                while (i < pat.length) {
                                  const ch = pat[i];
                                  if (ch === "(" || ch === ")") {
                                    tokens.push({ text: ch, cls: "text-violet-400" });
                                  } else if (ch === "[") {
                                    let j = i + 1;
                                    while (j < pat.length && pat[j] !== "]") j++;
                                    tokens.push({ text: pat.slice(i, j + 1), cls: "text-amber-400/80" });
                                    i = j;
                                  } else if ("*+?".includes(ch) || (ch === "{" && /\{[0-9,]+\}/.test(pat.slice(i)))) {
                                    tokens.push({ text: ch, cls: "text-blue-400" });
                                  } else if (ch === "." || ch === "^" || ch === "$" || ch === "|") {
                                    tokens.push({ text: ch, cls: "text-rose-400/80" });
                                  } else if (ch === "\\" && i + 1 < pat.length) {
                                    tokens.push({ text: pat.slice(i, i + 2), cls: "text-sky-400/80" });
                                    i++;
                                  } else {
                                    const last = tokens[tokens.length - 1];
                                    if (last && last.cls === "text-emerald-300/80") {
                                      last.text += ch;
                                    } else {
                                      tokens.push({ text: ch, cls: "text-emerald-300/80" });
                                    }
                                  }
                                  i++;
                                }
                                return tokens.map((t, idx) => (
                                  <span key={idx} className={t.cls}>{t.text}</span>
                                ));
                              })()}
                            </code>
                            <button
                              type="button"
                              onClick={() => copy(impl.pattern!, `pat:${lang}`, "Pattern kopyalandı ✓")}
                              className={`absolute right-2 top-2 rounded border border-slate-800 bg-slate-900/90 px-1.5 py-0.5 text-[9px] text-slate-600 opacity-0 transition-all active:scale-[0.94] group-hover/pattern:opacity-100 hover:text-slate-300 ring-1 ring-inset ring-white/[0.04] shadow-sm shadow-black/20 backdrop-blur-sm ${FOCUS_RING}`}
                            >
                              {copied === `pat:${lang}` ? (
                                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5 text-emerald-400">
                                  <path d="M2 5.5l2 2 4-4" />
                                </svg>
                              ) : (
                                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                                  <rect x="1" y="2" width="7" height="7" rx="1" />
                                  <path d="M3 1h6v7" />
                                </svg>
                              )}
                            </button>
                          </div>
                        )}
                        {/* Source file path */}
                        <div className="flex items-center gap-2 border-t border-slate-800/60 bg-slate-900/50 px-3 py-1.5">
                          <span className="min-w-0 flex-1 truncate font-mono text-[10px] text-slate-500" title={impl.source_file}>
                            {shortPath}
                          </span>
                          <button
                            type="button"
                            onClick={() => copy(impl.source_file, `src:${lang}`, "Dosya yolu kopyalandı ✓")}
                            className={`shrink-0 rounded border border-transparent px-1 py-0.5 text-[10px] text-slate-600 transition-all active:scale-90 hover:border-slate-700/50 hover:text-slate-300 ring-1 ring-inset ring-transparent hover:ring-white/[0.02] ${FOCUS_RING}`}
                            title="Tam dosya yolunu kopyala"
                          >
                            {copied === `src:${lang}` ? (
                              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5 text-emerald-400">
                                <path d="M2 5.5l2 2 4-4" />
                              </svg>
                            ) : (
                              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                                <rect x="1" y="2" width="7" height="7" rx="1" />
                                <path d="M3 1h6v7" />
                              </svg>
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          )}

          {/* ── EXAMPLES + NOTES tab ── */}
          {activeTab === "examples" && (
            <section className="space-y-4 animate-fade-in">
              {action.notes && (
                <div className="group/notes overflow-hidden rounded-xl border border-amber-500/20 bg-amber-500/[0.06] ring-1 ring-inset ring-amber-500/[0.03]">
                  <div className="flex items-center justify-between border-b border-amber-500/10 bg-amber-500/[0.04] px-3 py-2">
                    <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-amber-500/70">
                      <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3 text-amber-400/70">
                        <circle cx="5" cy="4" r="2.5" />
                        <path d="M3.5 6.5c0 1 .7 1.5 1.5 1.5s1.5-.5 1.5-1.5M5 8.5v.5" />
                      </svg>
                      <span>Notlar</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => copy(action.notes!, "notes", "Notlar kopyalandı ✓")}
                      className={`rounded border border-amber-700/20 bg-transparent px-1.5 py-0.5 text-[10px] text-amber-700/50 opacity-0 transition-all active:scale-90 group-hover/notes:opacity-100 hover:bg-amber-500/10 hover:text-amber-400 ring-1 ring-inset ring-amber-500/[0.03] hover:ring-amber-500/[0.06] shadow-sm shadow-black/10 ${FOCUS_RING}`}
                    >
                      {copied === "notes" ? (
                        <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5 text-emerald-400">
                          <path d="M2 5.5l2 2 4-4" />
                        </svg>
                      ) : (
                        <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                          <rect x="1" y="2" width="7" height="7" rx="1" />
                          <path d="M3 1h6v7" />
                        </svg>
                      )}
                    </button>
                  </div>
                  <p className="px-3 pb-3 pt-2.5 text-xs leading-relaxed text-amber-200/90">{action.notes}</p>
                </div>
              )}
              {(action.examples?.length ?? 0) > 0 && (
                <div>
                  <div className="mb-3 flex items-center gap-2">
                    <h3 className="font-semibold text-slate-100 tracking-tight">Örnekler</h3>
                    {(action.examples?.length ?? 0) > 1 && (
                      <span className="rounded-full border border-slate-700/50 bg-slate-800/50 px-1.5 py-0.5 text-[10px] text-slate-500 ring-1 ring-inset ring-white/[0.02]">
                        {action.examples!.length}
                      </span>
                    )}
                  </div>
                  {(action.examples ?? []).map((ex, i) => {
                    const lineCount = ex.split("\n").filter(Boolean).length;
                    return (
                      <div key={i} className="group/ex relative mb-4">
                        <div className="mb-1.5 flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {(action.examples?.length ?? 0) > 1 && (
                              <span className="flex h-4 w-4 items-center justify-center rounded-full border border-slate-700/60 bg-slate-800/60 text-[9px] font-semibold text-slate-500 ring-1 ring-inset ring-white/[0.02]">
                                {i + 1}
                              </span>
                            )}
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                              {(action.examples?.length ?? 0) > 1 ? `Senaryo` : "Örnek"}
                            </span>
                          </div>
                          <span className="flex items-center gap-1 rounded border border-slate-800/60 bg-slate-900/60 px-1.5 py-0.5 font-mono text-[9px] text-slate-500 ring-1 ring-inset ring-white/[0.02]">
                            <svg viewBox="0 0 10 10" fill="currentColor" className="h-1.5 w-1.5 opacity-50">
                              <rect x="0" y="0.5" width="10" height="1" rx="0.5" />
                              <rect x="0" y="3.5" width="8" height="1" rx="0.5" />
                              <rect x="0" y="6.5" width="10" height="1" rx="0.5" />
                              <rect x="0" y="9" width="6" height="1" rx="0.5" />
                            </svg>
                            {lineCount} satır
                          </span>
                        </div>
                        <pre className="overflow-x-auto rounded-xl border border-slate-800/60 bg-slate-950 p-3 font-mono text-xs leading-relaxed shadow-inner shadow-black/30 ring-1 ring-inset ring-white/[0.015] [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-track]:bg-slate-900 [&::-webkit-scrollbar-thumb]:bg-slate-700 [&::-webkit-scrollbar-thumb:hover]:bg-slate-600">
                          {highlightGherkin(ex)}
                        </pre>
                        <button
                          type="button"
                          onClick={() => copy(ex, `ex:${i}`, "Örnek kopyalandı ✓")}
                          className={`absolute right-2 bottom-2 rounded border border-slate-700 bg-slate-800/90 px-1.5 py-0.5 text-[10px] text-slate-400 opacity-0 transition-all active:scale-90 group-hover/ex:opacity-100 hover:text-slate-200 ring-1 ring-inset ring-white/[0.04] shadow-sm shadow-black/20 backdrop-blur-sm ${FOCUS_RING}`}
                        >
                          {copied === `ex:${i}` ? (
                            <span className="flex items-center gap-1 text-emerald-400">
                              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                                <path d="M2 5.5l2 2 4-4" />
                              </svg>
                              Kopyalandı
                            </span>
                          ) : (
                            <span className="flex items-center gap-1">
                              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                                <rect x="1" y="2" width="7" height="7" rx="1" />
                                <path d="M3 1h6v7" />
                              </svg>
                              Kopyala
                            </span>
                          )}
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
              {!action.notes && !(action.examples?.length) && (
                <div className="flex flex-col items-center py-10 text-center animate-fade-in">
                  <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-800/60 bg-slate-900/60 ring-1 ring-inset ring-white/[0.03]">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6 text-slate-500">
                      <rect x="3" y="3" width="14" height="14" rx="2" />
                      <path d="M7 7h6M7 10h4M7 13h2" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-slate-500">Örnek veya not bulunmuyor</p>
                  <p className="mt-1 text-xs text-slate-600">Bu cümleciğe örnek senaryo eklenmemiş</p>
                </div>
              )}
            </section>
          )}

          {/* ── RELATED tab ── */}
          {activeTab === "related" && (
            <section className="animate-fade-in">
              <h3 className="mb-3 font-semibold text-slate-100 tracking-tight">
                İlgili Cümlecikler
                <span className="ml-2 text-xs font-normal text-slate-500">
                  {getCategoryLabel(action.category.split(".")[0])} kategorisinden
                </span>
              </h3>
              {(relatedActions ?? []).length > 0 ? (
                <ul className="space-y-1">
                  {(relatedActions ?? []).map((rel, relIdx) => {
                    const relSt = getStepType(rel.description ?? "");
                    const relSc = relSt ? STEP_TYPE_CONFIG[relSt] : null;
                    const relPrimary = rel.aliases?.tr?.[0] ?? rel.aliases?.en?.[0] ?? rel.id;
                    const relKw = relSt === "given" ? "Given" : relSt === "when" ? "When" : relSt === "then" ? "Then" : null;
                    const relTrCount = rel.aliases?.tr?.length ?? 0;
                    const relEnCount = rel.aliases?.en?.length ?? 0;
                    return (
                      <li key={rel.id} className="animate-fade-in" style={{ animationDelay: `${relIdx * 40}ms`, animationFillMode: "both" }}>
                        <button
                          type="button"
                          onClick={() => onOpenRelated?.(rel)}
                          style={relSc ? { borderLeftColor: relSc.borderColor, borderLeftWidth: "2px" } : undefined}
                          className={`group/rel flex w-full items-center gap-2.5 rounded-lg border border-slate-800/60 bg-slate-900/40 px-2.5 py-2 text-left transition-all active:scale-[0.99] hover:bg-slate-900 hover:border-slate-700/70 hover:-translate-y-px hover:shadow-sm hover:ring-1 hover:ring-inset hover:ring-white/[0.03] ${FOCUS_RING}`}
                        >
                          {relKw && (
                            <span className={`shrink-0 text-[10px] font-bold ${
                              relSt === "given" ? "text-emerald-500/70" : relSt === "when" ? "text-blue-500/70" : "text-amber-500/70"
                            }`}>
                              {relKw}
                            </span>
                          )}
                          <span className="min-w-0 flex-1 truncate font-mono text-xs text-slate-300">
                            {renderParams(relPrimary)}
                          </span>
                          <span className="flex shrink-0 items-center gap-1 text-[9px]">
                            {relTrCount > 0 && (
                              <span className="flex items-center gap-0.5 text-emerald-600">
                                <span className="inline-flex h-3 w-3 items-center justify-center rounded-sm bg-emerald-500/15 font-bold text-[6px] text-emerald-500 leading-none">TR</span>
                                {relTrCount}
                              </span>
                            )}
                            {relEnCount > 0 && (
                              <span className="flex items-center gap-0.5 text-blue-600">
                                <span className="inline-flex h-3 w-3 items-center justify-center rounded-sm bg-blue-500/15 font-bold text-[6px] text-blue-500 leading-none">EN</span>
                                {relEnCount}
                              </span>
                            )}
                          </span>
                          <span className="shrink-0 transition-transform group-hover/rel:translate-x-0.5">
                            <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5 text-slate-600">
                              <path d="M2 5h6M5.5 2l3 3-3 3" />
                            </svg>
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <div className="flex flex-col items-center py-10 text-center animate-fade-in">
                  <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-800/60 bg-slate-900/60 ring-1 ring-inset ring-white/[0.03]">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6 text-slate-500">
                      <circle cx="6" cy="7" r="3" />
                      <circle cx="14" cy="13" r="3" />
                      <path d="M9 7.5h2a2 2 0 012 2v1" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-slate-500">İlgili cümlecik bulunamadı</p>
                  <p className="mt-1 text-xs text-slate-600">Aynı kategoride başka cümlecik yok</p>
                </div>
              )}
            </section>
          )}

          {/* ── AI ALIAS SUGGESTIONS tab ── */}
          {activeTab === "ai" && (
            <AiAliasSuggestSection actionId={action.id} />
          )}

        </div>{/* end keyed tab wrapper */}
        </div>
        {/* Scroll fade gradient at bottom of content area */}
        <div className="pointer-events-none relative h-6 shrink-0 -mt-6" aria-hidden="true"
          style={{ background: "linear-gradient(to top, rgb(2 6 23) 0%, transparent 100%)" }} />

        {/* ── Panel footer: keyboard hint strip ── */}
        <div className="shrink-0 border-t border-slate-800/40 bg-slate-950/80 px-4 py-1.5">
          <div className="flex items-center justify-center gap-4 text-[9px]">
            {([
              { k: "Esc", d: "kapat" },
              { k: null, d: "gezin", arrows: true },
              { k: "1-6", d: "sekme" },
              { k: "f", d: "favori" },
              { k: "/", d: "filtrele" },
            ] as Array<{ k: string | null; d: string; arrows?: boolean }>).map(({ k, d, arrows }) => (
              <span key={d} className="flex items-center gap-1 text-slate-600 hover:text-slate-400 transition-colors">
                {arrows ? (
                  <span className="flex items-center gap-0.5">
                    <kbd className="inline-flex items-center justify-center rounded border border-slate-700/60 bg-slate-900 px-1 py-0.5 shadow-sm ring-1 ring-inset ring-white/[0.04]">
                      <svg viewBox="0 0 8 8" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2 w-2 text-slate-500"><path d="M5 1.5L2.5 4 5 6.5" /></svg>
                    </kbd>
                    <kbd className="inline-flex items-center justify-center rounded border border-slate-700/60 bg-slate-900 px-1 py-0.5 shadow-sm ring-1 ring-inset ring-white/[0.04]">
                      <svg viewBox="0 0 8 8" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2 w-2 text-slate-500"><path d="M3 1.5L5.5 4 3 6.5" /></svg>
                    </kbd>
                  </span>
                ) : (
                  <kbd className="rounded border border-slate-700/60 bg-slate-900 px-1.5 py-0.5 font-mono text-[9px] text-slate-500 shadow-sm ring-1 ring-inset ring-white/[0.04]">{k}</kbd>
                )}
                <span>{d}</span>
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function DslCatalogView({
  title = "DSL Sözlüğü",
  forceCategory,
}: {
  title?: string;
  /**
   * Verildiğinde kategori filtresi bu değere kilitlenir ve sol panelde
   * yalnızca bu üst kategorinin alt ağacı gösterilir. "/dsl-catalog/mobile"
   * gibi özel sekmelerde kullanılır.
   */
  forceCategory?: string;
} = {}) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [search, setSearch] = useState(() => searchParams.get("q") ?? "");
  // Auto-open action from ?action= param (deep link)
  const deepLinkActionId = searchParams.get("action") ?? null;
  const [category, setCategory] = useState<string | null>(() =>
    forceCategory ?? searchParams.get("cat") ?? null,
  );
  const [langFilter, setLangFilter] = useState<LangFilter>(
    () => (searchParams.get("lang") as LangFilter) ?? "all",
  );
  const [stepTypeFilter, setStepTypeFilter] = useState<StepTypeFilter>(
    () => (searchParams.get("step") as StepTypeFilter) ?? "all",
  );
  const [selected, setSelected] = useState<DslAction | null>(null);
  const [page, setPage] = useState(() => Math.max(1, Number(searchParams.get("p") ?? "1")));
  const [searchMode, setSearchMode] = useState<SearchMode>("substring");
  const [votes, setVotes] = useState<Record<string, "up" | "down">>({});
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [tagFilter, setTagFilter] = useState<string | null>(() => searchParams.get("tag") ?? null);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [recentActions, setRecentActions] = useState<Array<{ action: DslAction; viewedAt: number }>>([]);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [searchFocused, setSearchFocused] = useState(false);
  const [favorites, setFavorites] = useState<Set<string>>(() => {
    try { return new Set(JSON.parse(localStorage.getItem("dsl_favorites") ?? "[]") as string[]); }
    catch { return new Set<string>(); }
  });
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [cardScrolled, setCardScrolled] = useState(false);
  const [showHints, setShowHints] = useState(() => {
    try { return localStorage.getItem("dsl_hints_dismissed") !== "1"; }
    catch { return true; }
  });
  const [batchMode, setBatchMode] = useState(false);
  const [selectedBatchIds, setSelectedBatchIds] = useState<Set<string>>(new Set());
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [focusedIdx, setFocusedIdx] = useState(-1);
  const [viewMode, setViewMode] = useState<"grid" | "list">(
    () => (searchParams.get("view") as "grid" | "list") ?? "grid",
  );
  const [gridCols, setGridCols] = useState<1 | 2 | 3>(
    () => (Number(searchParams.get("cols") || "2") as 1 | 2 | 3) ?? 2,
  );
  const [sortOrder, setSortOrder] = useState<"default" | "az" | "za" | "step">(
    () => (searchParams.get("sort") as "default" | "az" | "za" | "step") ?? "default",
  );
  const cardScrollRef = useRef<HTMLDivElement>(null);

  // Scroll card grid to top when page changes
  useEffect(() => {
    cardScrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [page]);

  // Reset focused card when filters/page change
  useEffect(() => {
    setFocusedIdx(-1);
  }, [page, category, stepTypeFilter, tagFilter, search, showFavoritesOnly]);

  // Open a detail panel and track recently viewed; scroll selected card into view
  const openAction = useCallback((action: DslAction) => {
    setSelected(action);
    setRecentActions((prev) =>
      [{ action, viewedAt: Date.now() }, ...prev.filter((r) => r.action.id !== action.id)].slice(0, 5),
    );
    // Gently scroll the card into view (non-blocking)
    setTimeout(() => {
      document
        .querySelector(`[data-testid="dsl-action-card-${action.id}"]`)
        ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }, 50);
  }, []);

  // Toggle favorite — persisted to localStorage
  const toggleFavorite = useCallback((id: string) => {
    setFavorites((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
        dispatchToast("Favorilerden çıkarıldı");
      } else {
        next.add(id);
        dispatchToast("Favorilere eklendi", "favorite");
      }
      try { localStorage.setItem("dsl_favorites", JSON.stringify([...next])); } catch { /* ignore */ }
      return next;
    });
  }, []);

  // Sync filters → URL query params (shareable/bookmarkable links)
  useEffect(() => {
    const p = new URLSearchParams();
    if (search) p.set("q", search);
    if (category && !forceCategory) p.set("cat", category);
    if (langFilter !== "all") p.set("lang", langFilter);
    if (stepTypeFilter !== "all") p.set("step", stepTypeFilter);
    if (tagFilter) p.set("tag", tagFilter);
    if (page > 1) p.set("p", String(page));
    if (viewMode !== "grid") p.set("view", viewMode);
    if (gridCols !== 2) p.set("cols", String(gridCols));
    if (sortOrder !== "default") p.set("sort", sortOrder);
    const qs = p.toString();
    router.replace(`${window.location.pathname}${qs ? "?" + qs : ""}`, { scroll: false });
  }, [search, category, langFilter, stepTypeFilter, tagFilter, page, viewMode, gridCols, sortOrder, forceCategory, router]);

  const stats = useDslStats();
  const categories = useDslCategories();
  const feedback = useDslFeedback();
  const indexInfo = useDslIndexInfo(searchMode === "ai");

  const isSearching = search.trim().length >= 2;
  const aiEnabled = searchMode === "ai";

  // Substring modu — hızlı alias araması
  const searchResults = useDslSearch(
    isSearching && !aiEnabled ? search : "",
    langFilter === "all" ? undefined : langFilter,
    100,
  );
  // AI modu — doğal dil öneri (auto: index varsa hybrid, yoksa lexical fallback)
  const aiSuggest = useDslSuggest(search, {
    enabled: isSearching && aiEnabled,
    mode: "auto",
    limit: 25,
    minLength: 2,
  });

  const listQuery = useDslActions({
    category: category ?? undefined,
    lang: langFilter === "all" ? undefined : langFilter,
    step_type: stepTypeFilter === "all" ? undefined : stepTypeFilter,
    tag: tagFilter ?? undefined,
    page,
    page_size: 50,
  });

  const activeHits = useMemo(() => {
    if (!isSearching) return [];
    return aiEnabled ? aiSuggest.data?.items ?? [] : searchResults.data?.items ?? [];
  }, [isSearching, aiEnabled, aiSuggest.data, searchResults.data]);

  const activeActions: DslAction[] = useMemo(() => {
    let base: DslAction[] = isSearching
      ? activeHits.map((h) => h.action)
      : listQuery.data?.items ?? [];
    // When searching, also apply category filter client-side
    if (isSearching && category) {
      base = base.filter(
        (a) => a.category === category || a.category.startsWith(category + "."),
      );
    }
    const filtered = showFavoritesOnly ? base.filter((a) => favorites.has(a.id)) : base;
    if (sortOrder === "default") return filtered;
    const STEP_ORDER: Record<string, number> = { given: 0, when: 1, then: 2 };
    return [...filtered].sort((a, b) => {
      if (sortOrder === "step") {
        const sa = getStepType(a.description ?? "") ?? "then";
        const sb = getStepType(b.description ?? "") ?? "then";
        return (STEP_ORDER[sa] ?? 3) - (STEP_ORDER[sb] ?? 3);
      }
      const pa = a.aliases?.tr?.[0] ?? a.aliases?.en?.[0] ?? a.id;
      const pb = b.aliases?.tr?.[0] ?? b.aliases?.en?.[0] ?? b.id;
      return sortOrder === "az" ? pa.localeCompare(pb, "tr") : pb.localeCompare(pa, "tr");
    });
  }, [isSearching, activeHits, listQuery.data, showFavoritesOnly, favorites, sortOrder, category]);

  // Record successful searches to history
  useEffect(() => {
    if (isSearching && activeActions.length > 0) {
      setSearchHistory((prev) =>
        [search.trim(), ...prev.filter((s) => s !== search.trim())].slice(0, 6),
      );
    }
  }, [search, isSearching, activeActions.length]);

  // Auto-open from ?action= deep link
  useEffect(() => {
    if (!deepLinkActionId || selected) return;
    const found = activeActions.find((a) => a.id === deepLinkActionId);
    if (found) openAction(found);
  }, [deepLinkActionId, activeActions, selected, openAction]);

  // Scroll focused card into view when navigating with j/k
  useEffect(() => {
    if (focusedIdx >= 0 && activeActions[focusedIdx]) {
      document
        .querySelector(`[data-testid="dsl-action-card-${activeActions[focusedIdx].id}"]`)
        ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [focusedIdx, activeActions]);

  const hitByActionId = useMemo(() => {
    const m = new Map<string, DslSearchHit>();
    for (const hit of activeHits) m.set(hit.action.id, hit);
    return m;
  }, [activeHits]);

  const activeTotal = isSearching
    ? aiEnabled
      ? aiSuggest.data?.total ?? 0
      : searchResults.data?.total ?? 0
    : listQuery.data?.total ?? 0;

  const activeMode = aiEnabled ? aiSuggest.data?.mode ?? null : null;
  const isAiLoading = aiEnabled && aiSuggest.isFetching;

  const selectedIdx = selected
    ? activeActions.findIndex((a) => a.id === selected.id)
    : -1;

  // Pre-compute step type group counts for the sorted card header (avoids O(n²) in render)
  const stepGroupCounts = useMemo(() => {
    if (sortOrder !== "step") return {} as Record<string, number>;
    const counts: Record<string, number> = {};
    for (const a of activeActions) {
      const st = getStepType(a.description ?? "");
      if (st) counts[st] = (counts[st] ?? 0) + 1;
    }
    return counts;
  }, [activeActions, sortOrder]);

  // Related actions: same top-level category, excluding selected, up to 5
  const relatedActions = useMemo(() => {
    if (!selected) return [];
    const topCat = selected.category.split(".")[0];
    const pool = listQuery.data?.items ?? activeActions;
    return pool
      .filter((a) => a.id !== selected.id && a.category.split(".")[0] === topCat)
      .slice(0, 5);
  }, [selected, listQuery.data, activeActions]);

  // Update document title based on search/filter state
  useEffect(() => {
    if (isSearching && activeActions.length > 0) {
      document.title = `${activeActions.length} sonuç · "${search}" — DSL Sözlüğü`;
    } else if (isSearching) {
      document.title = `"${search}" — DSL Sözlüğü`;
    } else if (category) {
      document.title = `${getCategoryLabel(category)} — DSL Sözlüğü`;
    } else {
      document.title = title;
    }
    return () => { document.title = "DSL Sözlüğü"; };
  }, [isSearching, search, activeActions.length, category, title]);

  // ⌘K / Ctrl+K → focus search; ←/→ → prev/next page (when not typing)
  useEffect(() => {
    const totalPages = Math.ceil(activeTotal / 50);
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      const isTyping = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        document.querySelector<HTMLInputElement>("[data-testid='dsl-search-input']")?.focus();
      } else if (!isTyping && !selected) {
        if (!isSearching) {
          if (e.key === "ArrowRight" && page < totalPages) setPage((p) => p + 1);
          if (e.key === "ArrowLeft" && page > 1) setPage((p) => p - 1);
        }
        if (e.key === "?") { e.preventDefault(); setShowShortcuts((s) => !s); }
        if (e.key === "b") { e.preventDefault(); setBatchMode((v) => { if (v) setSelectedBatchIds(new Set()); return !v; }); }
        if (e.key === "Escape" && batchMode) { e.preventDefault(); setBatchMode(false); setSelectedBatchIds(new Set()); }
        // vim-style j/k navigation through visible cards
        if (e.key === "j" && !batchMode) {
          e.preventDefault();
          setFocusedIdx((prev) => Math.min(prev + 1, activeActions.length - 1));
        }
        if (e.key === "k" && !batchMode) {
          e.preventDefault();
          setFocusedIdx((prev) => Math.max(0, prev - 1));
        }
        if (e.key === "Home" && !batchMode && focusedIdx >= 0) {
          e.preventDefault();
          setFocusedIdx(0);
        }
        if (e.key === "End" && !batchMode && focusedIdx >= 0) {
          e.preventDefault();
          setFocusedIdx(activeActions.length - 1);
        }
        if (e.key === "Enter" && focusedIdx >= 0 && focusedIdx < activeActions.length && !batchMode) {
          e.preventDefault();
          openAction(activeActions[focusedIdx]);
          setFocusedIdx(-1);
        }
        // c = copy Gherkin of focused or first card
        if (e.key === "c" && !batchMode) {
          const targetAction = focusedIdx >= 0 ? activeActions[focusedIdx] : null;
          if (targetAction) {
            e.preventDefault();
            const cSt = getStepType(targetAction.description ?? "");
            const cKw = cSt === "given" ? "Given" : cSt === "when" ? "When" : cSt === "then" ? "Then" : "And";
            const cAlias = targetAction.aliases?.tr?.[0] ?? targetAction.aliases?.en?.[0] ?? targetAction.id;
            navigator.clipboard.writeText(`${cKw} ${cAlias}`).then(() => {
              dispatchToast("Gherkin kopyalandı");
            });
          }
        }
      } else if (!isTyping && selected) {
        if (e.key === "f") { e.preventDefault(); toggleFavorite(selected.id); }
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [activeTotal, isSearching, page, selected, batchMode, focusedIdx, activeActions, openAction, toggleFavorite]);

  function handleVote(actionId: string, vote: "up" | "down") {
    // Optimistic işaretleme — backend hata verirse geri alınır
    setVotes((prev) => ({ ...prev, [actionId]: vote }));
    const hit = hitByActionId.get(actionId);
    feedback.mutate(
      {
        query: search.trim(),
        action_id: actionId,
        vote,
        search_mode: (hit?.source ?? "lexical") as
          | "lexical"
          | "semantic"
          | "hybrid"
          | "llm_rerank",
        rank: activeActions.findIndex((a) => a.id === actionId),
        raw_score: typeof hit?.score === "number" ? hit.score : undefined,
      },
      {
        onError: () => {
          setVotes((prev) => {
            const { [actionId]: _, ...rest } = prev;
            return rest;
          });
        },
      },
    );
  }

  const topCats = categories.data
    ? Array.from(
        categories.data
          .filter((c) => !forceCategory || c.top_level === forceCategory)
          .reduce((m, c) => {
            m.set(c.top_level, (m.get(c.top_level) ?? 0) + c.count);
            return m;
          }, new Map<string, number>()),
      )
        .map(([id, count]) => ({ id, count }))
        .sort((a, b) => b.count - a.count)
    : [];

  const maxCatCount = topCats.reduce((m, c) => Math.max(m, c.count), 1);

  const subCats = categories.data?.filter((c) => {
    if (!category) return false;
    return c.top_level === category || c.id.startsWith(category + ".");
  });

  return (
    <div className="relative flex h-full flex-col gap-4 p-4 sm:p-6 motion-reduce:[&_.animate-fade-in]:animate-none motion-reduce:[&_.animate-scale-in]:animate-none motion-reduce:[&_.animate-slide-in-right]:animate-none motion-reduce:[&_.animate-slide-down]:animate-none motion-reduce:[&_.animate-slide-up]:animate-none motion-reduce:[&_.animate-shimmer]:animate-none motion-reduce:[&_.animate-bounce]:animate-none motion-reduce:[&_.animate-pulse]:animate-none motion-reduce:[&_.animate-ping]:animate-none">
      {/* Subtle dot-grid background texture */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.018]"
        style={{ backgroundImage: "radial-gradient(circle, #94a3b8 1px, transparent 1px)", backgroundSize: "28px 28px" }}
        aria-hidden="true"
      />
      {/* Ambient depth glows */}
      <div className="pointer-events-none absolute left-0 top-0 h-96 w-96 -translate-x-1/3 -translate-y-1/4 rounded-full bg-blue-500/[0.04] blur-3xl" aria-hidden="true" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-72 w-72 translate-x-1/4 translate-y-1/4 rounded-full bg-violet-500/[0.025] blur-3xl" aria-hidden="true" />
      {/* Subtle top gradient bar — brand accent */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-transparent via-blue-500/40 to-transparent" aria-hidden="true" />
      {/* Header */}
      <header className="flex flex-wrap items-start justify-between gap-4 pb-2">
        <div>
          <h1 className="bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-2xl font-bold tracking-tight text-transparent">{title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {stats.data ? (
              <>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-800/50 px-2.5 py-1 text-xs ring-1 ring-inset ring-white/[0.04]">
                  <span className="font-semibold text-white">{stats.data.total}</span>
                  <span className="text-slate-400">cümlecik</span>
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/5 px-2.5 py-1 text-xs ring-1 ring-inset ring-emerald-500/[0.06]">
                  <span className="font-semibold text-emerald-400">{stats.data.aliases.tr}</span>
                  <span className="text-emerald-600">TR</span>
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-500/20 bg-blue-500/5 px-2.5 py-1 text-xs ring-1 ring-inset ring-blue-500/[0.06]">
                  <span className="font-semibold text-blue-400">{stats.data.aliases.en}</span>
                  <span className="text-blue-600">EN</span>
                </span>
                {/* Favorites count pill */}
                {favorites.size > 0 && (
                  <button
                    type="button"
                    onClick={() => { setShowFavoritesOnly((v) => !v); setPage(1); }}
                    className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs transition-all active:scale-[0.95] ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
                      showFavoritesOnly
                        ? "border-amber-500/40 bg-amber-500/10 text-amber-300 ring-amber-500/[0.08]"
                        : "border-amber-500/20 bg-amber-500/5 text-amber-400/70 hover:border-amber-500/40 hover:text-amber-300 ring-amber-500/[0.04]"
                    }`}
                    title={showFavoritesOnly ? "Favori filtresini kaldır" : "Yalnızca favorileri göster"}
                    aria-pressed={showFavoritesOnly}
                  >
                    <svg viewBox="0 0 10 10" fill="currentColor" stroke="currentColor" strokeWidth="0.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                      <path d="M5 1l1.2 2.5L9 3.8l-2 2 .5 2.7L5 7.2 2.5 8.5 3 5.8 1 3.8l2.8-.3L5 1z" />
                    </svg>
                    <span className="font-semibold">{favorites.size}</span>
                  </button>
                )}
                {/* Step-type distribution segmented bar */}
                {stats.data.by_step_type && stats.data.total > 0 && (() => {
                  const st = stats.data.by_step_type;
                  const total = stats.data.total;
                  const segs: Array<{ key: StepType; pct: number; count: number }> = [
                    { key: "given", pct: Math.round(((st.given ?? 0) / total) * 100), count: st.given ?? 0 },
                    { key: "when",  pct: Math.round(((st.when  ?? 0) / total) * 100), count: st.when  ?? 0 },
                    { key: "then",  pct: Math.round(((st.then  ?? 0) / total) * 100), count: st.then  ?? 0 },
                  ];
                  return (
                    <span className="group/distbar flex items-center gap-px overflow-hidden rounded-md" title="Adım tipi dağılımı — tıklayarak filtrele">
                      {segs.map(({ key, pct, count }, segIdx) => {
                        const cfg = STEP_TYPE_CONFIG[key];
                        const isFirst = segIdx === 0;
                        const isLast = segIdx === segs.length - 1;
                        return (
                          <button
                            key={key}
                            type="button"
                            onClick={() => { setStepTypeFilter(stepTypeFilter === key ? "all" : key); setPage(1); }}
                            title={`${cfg.label}: ${count} cümlecik (${pct}%)`}
                            className={`group/seg h-5 transition-all ${FOCUS_RING} ${
                              stepTypeFilter === key ? "opacity-100 scale-y-110" : "opacity-55 hover:opacity-90"
                            } ${isFirst ? "rounded-l-sm" : ""} ${isLast ? "rounded-r-sm" : ""}`}
                            style={{ width: `${Math.max(10, pct * 0.9)}px`, backgroundColor: cfg.borderColor }}
                            aria-pressed={stepTypeFilter === key}
                          />
                        );
                      })}
                    </span>
                  );
                })()}
              </>
            ) : (
              <div className="flex gap-2">
                {[20, 24, 24, 20].map((w, i) => (
                  <div
                    key={i}
                    className={`h-6 rounded-full bg-slate-800 ${SHIMMER_CLS}`}
                    style={{ width: `${w * 4}px` }}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {stats.data?.loaded_at && (
            <span
              className="flex items-center gap-1 rounded border border-slate-800/50 bg-slate-900/40 px-1.5 py-0.5 text-[10px] text-slate-600 transition-colors hover:text-slate-500 ring-1 ring-inset ring-white/[0.02]"
              title={`Son yükleme: ${new Date(stats.data.loaded_at).toLocaleString("tr-TR")}`}
            >
              <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2.5 w-2.5 opacity-50">
                <circle cx="6" cy="6" r="5" />
                <path d="M6 3.5V6l2 1.5" />
              </svg>
              {relativeTime(stats.data.loaded_at)}
            </span>
          )}
          {activeActions.length > 0 && (
            <button
              type="button"
              onClick={() => {
                const idx = Math.floor(Math.random() * activeActions.length);
                openAction(activeActions[idx]);
              }}
              className={`flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700 bg-slate-900 text-base transition-all hover:bg-slate-800 hover:border-slate-600 hover:scale-105 hover:rotate-6 active:scale-95 ring-1 ring-inset ring-white/[0.03] shadow-sm shadow-black/10 ${FOCUS_RING}`}
              title={`Rastgele cümlecik aç (${activeActions.length} arasından)`}
              aria-label="Rastgele cümlecik"
            >
              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5">
                <rect x="1" y="1" width="8" height="8" rx="1.5" />
                <circle cx="3.2" cy="3.2" r="0.6" fill="currentColor" stroke="none" />
                <circle cx="6.8" cy="3.2" r="0.6" fill="currentColor" stroke="none" />
                <circle cx="3.2" cy="6.8" r="0.6" fill="currentColor" stroke="none" />
                <circle cx="6.8" cy="6.8" r="0.6" fill="currentColor" stroke="none" />
                <circle cx="5" cy="5" r="0.6" fill="currentColor" stroke="none" />
              </svg>
            </button>
          )}
          <Link
            href="/dsl-catalog/editor/new"
            className={`relative flex items-center gap-1.5 overflow-hidden rounded-lg border border-blue-500/50 bg-gradient-to-r from-blue-600/20 via-blue-500/15 to-blue-400/10 px-3 py-1.5 text-sm text-blue-200 shadow-sm shadow-blue-500/10 transition-all hover:border-blue-400/60 hover:from-blue-600/30 hover:via-blue-500/25 hover:to-blue-400/15 hover:text-white hover:shadow-md hover:shadow-blue-500/20 hover:-translate-y-px active:translate-y-0 active:scale-[0.97] ring-1 ring-inset ring-blue-400/[0.1] ${FOCUS_RING}`}
            data-testid="dsl-new-action"
          >
            <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="h-3 w-3">
              <path d="M7 1v12M1 7h12" />
            </svg>
            Yeni Cümlecik
          </Link>
          <Link
            href="/dsl-catalog/review"
            className={`flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-400 transition-all active:scale-[0.97] hover:bg-slate-800 hover:text-slate-200 hover:border-slate-600 ring-1 ring-inset ring-white/[0.03] shadow-sm shadow-black/10 ${FOCUS_RING}`}
            data-testid="dsl-review-link"
          >
            <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
              <circle cx="7" cy="7" r="6" />
              <path d="M5 7l2 2 3-3" />
            </svg>
            İnceleme
          </Link>
          <ShareButton />
          <button
            type="button"
            onClick={() => setShowShortcuts((s) => !s)}
            className={`flex h-8 w-8 items-center justify-center rounded-lg border font-mono text-sm font-semibold transition-all active:scale-90 ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
              showShortcuts
                ? "border-slate-600 bg-slate-700 text-slate-200 ring-white/[0.06]"
                : "border-slate-700 bg-slate-900 text-slate-600 hover:bg-slate-800 hover:text-slate-300 hover:border-slate-600 ring-white/[0.03]"
            }`}
            title="Klavye kısayolları (?)"
            aria-label="Klavye kısayollarını göster"
          >
            ?
          </button>
        </div>
      </header>

      {/* Filters */}
      <div className="relative flex flex-col gap-3 rounded-xl border border-slate-800/80 bg-slate-900/40 p-3 shadow-sm shadow-black/20 ring-1 ring-inset ring-white/[0.02] sm:flex-row sm:items-center backdrop-blur-sm overflow-hidden">
        {/* Subtle top-edge accent line */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-slate-700/60 to-transparent" aria-hidden="true" />
        <div className="flex-1">
          <div className="relative">
            <svg className={`pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 transition-colors ${aiEnabled ? "text-violet-400/50" : "text-slate-500"}`} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="6.5" cy="6.5" r="5" />
              <path d="M10.5 10.5L14 14" strokeLinecap="round" />
            </svg>
            <input
              type="search"
              className={`${INPUT_CLS} pl-9 pr-16 ${aiEnabled ? "border-violet-500/20 focus:border-violet-500/50 focus:ring-violet-500/20 placeholder-violet-400/40 shadow-[0_0_0_1px_rgba(139,92,246,0.07)]" : ""}`}
              placeholder={
                aiEnabled
                  ? category
                    ? `AI: ${getCategoryLabel(category)} içinde doğal dil ara…`
                    : "Doğal dil: 'login butonuna tıkla ve anasayfa açılsın'"
                  : category
                    ? `${getCategoryLabel(category)} içinde ara…`
                    : "Ara: 'tikla', 'yazar', 'I click on', 'onay'..."
              }
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setTimeout(() => setSearchFocused(false), 150)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && isSearching && activeActions.length > 0) {
                  e.preventDefault();
                  openAction(activeActions[0]);
                  (e.target as HTMLInputElement).blur();
                } else if (e.key === "Escape" && search) {
                  e.preventDefault();
                  setSearch("");
                  setPage(1);
                }
              }}
              data-testid="dsl-search-input"
            />
            {/* 1-char hint */}
            {search.length === 1 && (
              <div className="absolute left-0 right-0 top-full z-20 mt-1 flex items-center gap-1.5 rounded-lg border border-slate-700/40 bg-slate-900/98 px-3 py-2 text-[11px] shadow-lg shadow-black/30 ring-1 ring-inset ring-white/[0.03] backdrop-blur-sm animate-fade-in">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-500/40" />
                <span className="text-slate-500">Aramak için</span>
                <kbd className="rounded border border-slate-700 bg-slate-800/80 px-1.5 py-0.5 font-mono text-[9px] text-slate-300 shadow-sm ring-1 ring-inset ring-white/[0.05]">1</kbd>
                <span className="text-slate-500">karakter daha yaz</span>
              </div>
            )}
            {/* Search history dropdown + category suggestions */}
            {searchFocused && !search && (searchHistory.length > 0 || topCats.length > 0) && (
              <div className="absolute left-0 right-0 top-full z-20 mt-1 rounded-lg border border-slate-700 bg-slate-900 py-1 shadow-xl shadow-black/40 ring-1 ring-inset ring-white/[0.03] animate-slide-down">
                {topCats.length > 0 && (
                  <>
                    <div className="px-3 py-1 text-[10px] uppercase tracking-wider text-slate-600">Kategoriler</div>
                    <div className="flex flex-wrap gap-1 px-3 pb-2">
                      {topCats.slice(0, 6).map((c) => (
                        <button
                          key={c.id}
                          type="button"
                          onMouseDown={(e) => e.preventDefault()}
                          onClick={() => { setCategory(c.id); setPage(1); setSearchFocused(false); }}
                          className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] transition-all active:scale-[0.94] ring-1 ring-inset ${FOCUS_RING} ${
                            category === c.id
                              ? "border-blue-500/40 bg-blue-500/10 text-blue-300 ring-blue-500/[0.08]"
                              : "border-slate-700 bg-slate-800/60 text-slate-400 hover:bg-slate-700 hover:text-slate-200 ring-white/[0.02]"
                          }`}
                        >
                          <span className={`h-1.5 w-1.5 rounded-full ${CATEGORY_DOTS[c.id] ?? "bg-slate-500"}`} />
                          {CATEGORY_LABELS[c.id] ?? c.id}
                          <span className="text-slate-500">{c.count}</span>
                        </button>
                      ))}
                    </div>
                  </>
                )}
                {searchHistory.length > 0 && (
                  <div className="flex items-center justify-between px-3 py-1">
                    <span className="text-[10px] uppercase tracking-wider text-slate-600">Son aramalar</span>
                    <button
                      type="button"
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => setSearchHistory([])}
                      className={`text-[10px] text-slate-600 hover:text-slate-400 transition-all active:scale-95 ${FOCUS_RING}`}
                    >
                      Temizle
                    </button>
                  </div>
                )}
                {searchHistory.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => { setSearch(q); setPage(1); setSearchFocused(false); }}
                    className={`group/hist flex w-full items-center gap-2 px-3 py-1.5 text-sm text-slate-400 hover:bg-slate-800/80 hover:text-slate-200 text-left transition-all active:scale-[0.99] ${FOCUS_RING}`}
                  >
                    <svg className="h-3 w-3 shrink-0 text-slate-600 group-hover/hist:text-slate-500 transition-colors" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M8 4v4l3 3" strokeLinecap="round" strokeLinejoin="round" />
                      <circle cx="8" cy="8" r="6" />
                    </svg>
                    <span className="flex-1 truncate text-xs">{q}</span>
                    <span className="shrink-0 opacity-0 group-hover/hist:opacity-100 transition-opacity text-slate-600">
                      <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                        <path d="M8.5 2.5v3H2M4.5 4l-2.5 1.5L4.5 7" />
                      </svg>
                    </span>
                  </button>
                ))}
              </div>
            )}
            <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1.5">
              {isAiLoading && (
                <span className="flex items-center gap-1 text-xs text-violet-300">
                  <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-violet-400" style={{ animationDelay: "0ms" }} />
                  <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-violet-400" style={{ animationDelay: "150ms" }} />
                  <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-violet-400" style={{ animationDelay: "300ms" }} />
                </span>
              )}
              {isSearching && !isAiLoading && activeActions.length > 0 && (
                <span className={`tabular-nums text-[10px] font-medium ${
                  activeActions.length > 0 ? "text-slate-500" : "text-slate-600"
                }`}>
                  {activeActions.length}
                </span>
              )}
              {!search && (
                <kbd className="hidden rounded border border-slate-700 bg-slate-800/60 px-1.5 py-0.5 font-mono text-[10px] text-slate-500 sm:inline ring-1 ring-inset ring-white/[0.04] shadow-sm shadow-black/15">
                  ⌘K
                </kbd>
              )}
              {search && (
                <button
                  type="button"
                  onClick={() => { setSearch(""); setPage(1); }}
                  className={`flex items-center justify-center rounded p-1 text-slate-600 hover:bg-slate-800 hover:text-slate-300 transition-all active:scale-90 ${FOCUS_RING}`}
                  title="Aramayı temizle"
                >
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2.5 w-2.5">
                    <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Arama modu toggle */}
        <div className={`flex items-center gap-0.5 rounded-lg border p-0.5 transition-colors ring-1 ring-inset shadow-sm shadow-black/10 ${
          searchMode === "ai" ? "border-violet-500/20 bg-violet-950/30 ring-violet-500/[0.06]" : "border-slate-700 bg-slate-900 ring-white/[0.03]"
        }`}>
          <button
            type="button"
            onClick={() => {
              setSearchMode("substring");
              setPage(1);
            }}
            className={`flex items-center gap-1 rounded-md px-3 py-1 text-xs font-medium transition-all active:scale-[0.94] ${FOCUS_RING} ${
              searchMode === "substring"
                ? "bg-slate-700 text-white shadow-sm ring-1 ring-inset ring-slate-500/20"
                : "text-slate-500 hover:text-slate-300 hover:ring-1 hover:ring-inset hover:ring-white/[0.02]"
            }`}
            data-testid="dsl-search-mode-substring"
            title="Alias metinlerinde substring araması (hızlı)"
          >
            <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2.5 w-2.5">
              <circle cx="5" cy="5" r="4" />
              <path d="M8 8l2.5 2.5" />
            </svg>
            Alias
          </button>
          <button
            type="button"
            onClick={() => {
              setSearchMode("ai");
              setPage(1);
            }}
            className={`relative flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-all active:scale-[0.94] ${FOCUS_RING} ${
              searchMode === "ai"
                ? "bg-violet-600/90 text-white shadow-lg shadow-violet-500/25 ring-1 ring-inset ring-violet-400/[0.2]"
                : "text-slate-400 hover:text-violet-300 hover:ring-1 hover:ring-inset hover:ring-violet-500/[0.06]"
            }`}
            data-testid="dsl-search-mode-ai"
            title="Doğal dil — Ollama tabanlı anlamsal arama"
          >
            {searchMode === "ai" && (
              <>
                <span className="absolute inset-0 -z-0 rounded-md bg-gradient-to-r from-violet-600 to-violet-500" />
                <span className="absolute inset-0 -z-0 animate-pulse rounded-md opacity-30 bg-violet-400" />
              </>
            )}
            <span className="relative z-10 flex items-center gap-1">
              <svg viewBox="0 0 10 10" fill="currentColor" className="h-2.5 w-2.5">
                <path d="M5 1l.8 2.2L8 4l-2.2.8L5 7l-.8-2.2L2 4l2.2-.8L5 1z" />
              </svg>
              <span>AI</span>
            </span>
          </button>
        </div>

        <div className="hidden h-5 w-px bg-slate-700/60 sm:block" aria-hidden="true" />
        <div className="flex items-center gap-0.5 rounded-lg border border-slate-700 bg-slate-900 p-0.5 ring-1 ring-inset ring-white/[0.03] shadow-sm shadow-black/10">
          {(["all", "tr", "en"] as LangFilter[]).map((l) => (
            <button
              type="button"
              key={l}
              onClick={() => {
                setLangFilter(l);
                setPage(1);
              }}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-all active:scale-[0.94] ${FOCUS_RING} ${
                langFilter === l
                  ? l === "tr"
                    ? "bg-emerald-500/15 text-emerald-200 shadow-sm ring-1 ring-emerald-500/20"
                    : l === "en"
                    ? "bg-blue-500/15 text-blue-200 shadow-sm ring-1 ring-blue-500/20"
                    : "bg-slate-700 text-white shadow-sm ring-1 ring-slate-600/30"
                  : "text-slate-500 hover:text-slate-300"
              }`}
              data-testid={`dsl-lang-${l}`}
            >
              {l === "all" ? "Tümü" : (
                <span className="flex items-center gap-1">
                  <span className={`inline-flex h-3 w-3 items-center justify-center rounded-sm font-bold text-[6px] leading-none ${
                    l === "tr" ? "bg-emerald-500/20 text-emerald-400" : "bg-blue-500/20 text-blue-400"
                  }`}>{l.toUpperCase()}</span>
                  {l.toUpperCase()}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* AI modunda index durumu + mod göstergesi */}
      {aiEnabled && (
        <AiStatusBanner
          indexReady={indexInfo.data?.ready ?? false}
          rows={indexInfo.data?.rows ?? 0}
          model={indexInfo.data?.model ?? "-"}
          activeMode={activeMode}
        />
      )}

      {/* Mobile sidebar toggle */}
      <button
        type="button"
        onClick={() => setSidebarOpen((o) => !o)}
        className={`flex items-center gap-2 self-start rounded-lg border bg-slate-900 px-3 py-1.5 text-xs transition-all active:scale-[0.97] hover:bg-slate-800 lg:hidden ring-1 ring-inset shadow-sm shadow-black/10 ${FOCUS_RING} ${
          sidebarOpen
            ? "border-blue-500/30 text-blue-300 ring-blue-500/[0.07]"
            : "border-slate-700 text-slate-300 ring-white/[0.03]"
        }`}
        aria-expanded={sidebarOpen}
      >
        <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="currentColor">
          <rect y="2" width="16" height="1.5" rx="1" />
          <rect y="7" width="10" height="1.5" rx="1" />
          <rect y="12" width="13" height="1.5" rx="1" />
        </svg>
        Filtreler
        {(category || stepTypeFilter !== "all" || langFilter !== "all" || showFavoritesOnly || tagFilter) && (
          <span className="flex h-4 w-4 items-center justify-center rounded-full bg-blue-500/25 text-[10px] font-bold text-blue-300 ring-1 ring-blue-500/20">
            {[category, stepTypeFilter !== "all", langFilter !== "all", showFavoritesOnly, tagFilter].filter(Boolean).length}
          </span>
        )}
      </button>

      <div className="flex flex-1 min-h-0 flex-col gap-4 lg:flex-row">
        {/* Sol: Filtreler */}
        <aside
          role="complementary"
          aria-label="Filtreler"
          className={`flex-shrink-0 rounded-xl border border-slate-800 bg-slate-900/50 ring-1 ring-inset ring-white/[0.02] shadow-sm shadow-black/20 transition-all duration-200 ${sidebarOpen ? "block" : "hidden"} ${sidebarCollapsed ? "lg:block lg:w-10 p-1.5" : "lg:block lg:w-60 p-3"}`}
        >
          {/* Collapse toggle */}
          <div className={`mb-2 ${sidebarCollapsed ? "flex justify-center" : "flex justify-end"}`}>
            <button
              type="button"
              onClick={() => setSidebarCollapsed((v) => !v)}
              className={`hidden rounded-md border border-slate-800 bg-slate-900/60 p-1 text-slate-600 hover:text-slate-300 hover:border-slate-700 ring-1 ring-inset ring-white/[0.02] transition-all active:scale-90 lg:flex ${FOCUS_RING}`}
              title={sidebarCollapsed ? "Kenar çubuğunu genişlet" : "Kenar çubuğunu daralt"}
              aria-label={sidebarCollapsed ? "Genişlet" : "Daralt"}
            >
              <svg viewBox="0 0 16 16" fill="currentColor" className="h-3 w-3">
                {sidebarCollapsed
                  ? <path d="M5 2l6 6-6 6" />
                  : <path d="M11 2L5 8l6 6" />}
              </svg>
            </button>
          </div>

          {/* Show only icons when collapsed */}
          {sidebarCollapsed ? (
            <div className="flex flex-col items-center gap-2 pt-1">
              {topCats.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => { setCategory(c.id === category ? null : c.id); setPage(1); }}
                  className={`flex h-7 w-7 items-center justify-center rounded-lg text-[10px] font-bold transition-all active:scale-90 ${FOCUS_RING} ${
                    category === c.id
                      ? "opacity-100 ring-1 ring-white/10"
                      : "opacity-40 hover:opacity-80"
                  }`}
                  style={{
                    backgroundColor: category === c.id
                      ? CATEGORY_COLORS[c.id] + "30"
                      : CATEGORY_COLORS[c.id] + "15",
                    color: CATEGORY_COLORS[c.id] ?? "#94a3b8",
                    borderColor: CATEGORY_COLORS[c.id] + "40",
                    border: "1px solid",
                  }}
                  title={CATEGORY_LABELS[c.id] ?? c.id}
                  aria-label={CATEGORY_LABELS[c.id] ?? c.id}
                  aria-pressed={category === c.id}
                >
                  {(CATEGORY_LABELS[c.id] ?? c.id).slice(0, 2).toUpperCase()}
                </button>
              ))}
              {favorites.size > 0 && (
                <button
                  type="button"
                  onClick={() => { setShowFavoritesOnly((v) => !v); setPage(1); }}
                  className={`flex items-center justify-center transition-all active:scale-90 ${FOCUS_RING} ${showFavoritesOnly ? "text-amber-400" : "text-slate-600 hover:text-amber-400"}`}
                  title={`Favoriler (${favorites.size})`}
                >
                  <svg viewBox="0 0 10 10" fill={showFavoritesOnly ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
                    <path d="M5 1l1.2 2.5L9 3.8l-2 2 .5 2.7L5 7.2 2.5 8.5 3 5.8 1 3.8l2.8-.3L5 1z" />
                  </svg>
                </button>
              )}
            </div>
          ) : (
          <>
          {/* Parent category breadcrumb when subcategory is selected */}
          {category && category.includes(".") && (
            <button
              type="button"
              onClick={() => { setCategory(category.split(".")[0]); setPage(1); }}
              className={`mb-3 flex w-full items-center gap-1.5 rounded-lg border border-slate-800/60 bg-slate-900/40 px-2 py-1.5 text-xs text-slate-500 hover:bg-slate-800/60 hover:text-slate-300 hover:border-slate-700/60 ring-1 ring-inset ring-white/[0.02] hover:ring-white/[0.03] transition-all active:scale-[0.98] ${FOCUS_RING}`}
            >
              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2.5 w-2.5 text-slate-600">
                <path d="M7 5H2M4 2.5L2 5l2 2.5" />
              </svg>
              <span className={`h-1.5 w-1.5 rounded-full`} style={{ backgroundColor: CATEGORY_COLORS[category.split(".")[0]] ?? "#475569" }} />
              <span>{CATEGORY_LABELS[category.split(".")[0]] ?? category.split(".")[0]}</span>
              <span className="ml-auto flex items-center gap-0.5 text-[9px] text-slate-600">
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2 w-2">
                  <path d="M5 8V2M2.5 4.5L5 2l2.5 2.5" />
                </svg>
                üst
              </span>
            </button>
          )}

          {/* Adım Tipi Filtresi */}
          <div className="mb-3">
            <div className="mb-2.5 flex items-center gap-2">
              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2.5 w-2.5 text-slate-600">
                <path d="M1 3h8M1 5h5M1 7h7" />
              </svg>
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Adım Tipi</span>
              {stepTypeFilter !== "all" && (
                <button
                  type="button"
                  onClick={() => { setStepTypeFilter("all"); setPage(1); }}
                  className={`ml-auto flex items-center gap-0.5 text-[9px] text-slate-600 hover:text-slate-400 transition-all active:scale-90 ${FOCUS_RING}`}
                  title="Adım tipi filtresini temizle"
                >
                  <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: STEP_TYPE_CONFIG[stepTypeFilter].borderColor + "80" }} />
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2 w-2">
                    <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" />
                  </svg>
                </button>
              )}
            </div>
            <div className="space-y-0.5">
              <button
                type="button"
                onClick={() => { setStepTypeFilter("all"); setPage(1); }}
                className={`flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-sm transition-all active:scale-[0.97] ${FOCUS_RING} ${
                  stepTypeFilter === "all"
                    ? "border-l-2 border-slate-500/60 bg-slate-800/50 pl-[6px] pr-2 text-slate-200 ring-1 ring-inset ring-white/[0.03]"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-200 hover:ring-1 hover:ring-inset hover:ring-white/[0.02]"
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${stepTypeFilter === "all" ? "bg-slate-400/60" : "bg-slate-600/60"}`} />
                  Tümü
                </span>
                <span className={`text-xs ${stepTypeFilter === "all" ? "text-slate-400/60 font-semibold" : "text-slate-600"}`}>{stats.data?.total ?? ""}</span>
              </button>
              {(Object.entries(STEP_TYPE_FILTER_CONFIG) as [StepType, typeof STEP_TYPE_FILTER_CONFIG[StepType]][]).map(([key, cfg]) => {
                const count = stats.data?.by_step_type?.[key] ?? 0;
                const total = stats.data?.total ?? 0;
                const pct = total > 0 && count > 0 ? Math.round((count / total) * 100) : null;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => { setStepTypeFilter(key === stepTypeFilter ? "all" : key); setPage(1); }}
                    style={stepTypeFilter === key ? { borderLeftColor: STEP_TYPE_CONFIG[key].borderColor } : undefined}
                    className={`flex w-full flex-col rounded-lg px-2 py-1.5 text-sm transition-all active:scale-[0.97] ${FOCUS_RING} ${
                      stepTypeFilter === key
                        ? "border-l-2 pl-[6px] bg-slate-800/80 text-white ring-1 ring-inset ring-white/[0.04]"
                        : "text-slate-400 hover:bg-slate-800 hover:text-slate-200 hover:ring-1 hover:ring-inset hover:ring-white/[0.02]"
                    }`}
                    aria-pressed={stepTypeFilter === key}
                  >
                    <span className="flex w-full items-center justify-between">
                      <span className="flex items-center gap-2">
                        <span className={`h-2 w-2 rounded-full ${cfg.dot}`} />
                        {cfg.label}
                      </span>
                      <span className="flex items-center gap-1.5 text-xs text-slate-600">
                        {count || ""}
                        {pct !== null && (
                          <span className="text-[10px] text-slate-600">{pct}%</span>
                        )}
                      </span>
                    </span>
                    {pct !== null && (
                      <div className="mt-1 h-0.5 w-full overflow-hidden rounded-full bg-slate-800">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${pct}%`,
                            background: `linear-gradient(90deg, ${STEP_TYPE_CONFIG[key].borderColor}70 0%, ${STEP_TYPE_CONFIG[key].borderColor}20 100%)`,
                          }}
                        />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Favorites filter toggle */}
          {favorites.size > 0 && (
            <div className="mb-3 border-t border-slate-800/70 pt-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <svg viewBox="0 0 10 10" fill="currentColor" className="h-2.5 w-2.5 text-amber-400/60">
                    <path d="M5 1l1.2 2.5L9 3.8l-2 2 .5 2.7L5 7.2 2.5 8.5 3 5.8 1 3.8l2.8-.3L5 1z" />
                  </svg>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Favoriler</span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setFavorites(new Set());
                    setShowFavoritesOnly(false);
                    try { localStorage.removeItem("dsl_favorites"); } catch { /* */ }
                  }}
                  className={`text-[9px] text-slate-600 hover:text-slate-400 transition-all active:scale-90 ${FOCUS_RING}`}
                  title="Tüm favorileri temizle"
                >
                  Temizle
                </button>
              </div>
              <button
                type="button"
                onClick={() => { setShowFavoritesOnly((v) => !v); setPage(1); }}
                className={`flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-sm transition-all active:scale-[0.97] ${FOCUS_RING} ${
                  showFavoritesOnly
                    ? "bg-amber-500/10 text-amber-300 border border-amber-500/20 ring-1 ring-inset ring-amber-500/[0.06]"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-200 hover:ring-1 hover:ring-inset hover:ring-white/[0.02]"
                }`}
                aria-pressed={showFavoritesOnly}
              >
                <span className="flex items-center gap-2">
                  <svg viewBox="0 0 10 10" fill={showFavoritesOnly ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3 text-amber-400">
                    <path d="M5 1l1.2 2.5L9 3.8l-2 2 .5 2.7L5 7.2 2.5 8.5 3 5.8 1 3.8l2.8-.3L5 1z" />
                  </svg>
                  <span>Yalnızca favoriler</span>
                </span>
                <span className="text-xs text-slate-600">{favorites.size}</span>
              </button>
            </div>
          )}

          <div className="mb-2 flex items-center justify-between border-t border-slate-800/50 pt-3">
            <div className="flex items-center gap-1.5">
              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2.5 w-2.5 text-slate-600">
                <rect x="1" y="1" width="4" height="4" rx="1" />
                <rect x="5.5" y="1" width="3.5" height="1.5" rx="0.5" />
                <rect x="5.5" y="4" width="3.5" height="1" rx="0.5" />
                <rect x="1" y="6.5" width="8" height="1.5" rx="0.5" />
                <rect x="1" y="8.5" width="6" height="1" rx="0.5" />
              </svg>
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Kategoriler</span>
            </div>
            {category && (
              <button
                type="button"
                onClick={() => { setCategory(null); setPage(1); }}
                className={`flex items-center justify-center text-slate-600 hover:text-slate-400 transition-all active:scale-90 ${FOCUS_RING}`}
                title="Kategori seçimini kaldır"
              >
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2 w-2">
                  <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" />
                </svg>
              </button>
            )}
          </div>
          {categories.isLoading && (
            <div className="space-y-1 mb-2">
              {[70, 55, 65, 60, 50].map((w, i) => (
                <div
                  key={i}
                  className={`h-7 rounded-lg bg-slate-800/60 ${SHIMMER_CLS}`}
                  style={{ width: `${w}%` }}
                />
              ))}
            </div>
          )}
          <ul className="space-y-0.5 text-sm">
            <li>
              <button
                type="button"
                onClick={() => { setCategory(null); setPage(1); }}
                className={`flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left transition-all active:scale-[0.97] ${FOCUS_RING} ${
                  category === null
                    ? "border-l-2 border-slate-500/60 bg-slate-800/50 pl-[6px] pr-2 text-slate-200 ring-1 ring-inset ring-white/[0.03]"
                    : "pl-2 text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 hover:ring-1 hover:ring-inset hover:ring-white/[0.02]"
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${category === null ? "bg-slate-400/60" : "bg-slate-600/60"}`} />
                  <span className="text-sm">Hepsi</span>
                </span>
                <span className={`font-mono text-xs ${category === null ? "font-semibold text-slate-400/60" : "text-slate-600"}`}>
                  {stats.data?.total ?? "—"}
                </span>
              </button>
            </li>
            {topCats.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => { setCategory(c.id); setPage(1); }}
                  style={category === c.id
                    ? { borderLeftColor: CATEGORY_COLORS[c.id] ?? "#3b82f6", backgroundColor: (CATEGORY_COLORS[c.id] ?? "#3b82f6") + "12" }
                    : undefined}
                  className={`group/cat flex w-full flex-col rounded-lg pr-2 py-1.5 text-left transition-all active:scale-[0.97] ${
                    category === c.id
                      ? "border-l-2 pl-[6px] text-white ring-1 ring-inset ring-white/[0.04]"
                      : "pl-2 text-slate-300 hover:bg-slate-800 hover:ring-1 hover:ring-inset hover:ring-white/[0.02]"
                  } ${FOCUS_RING}`}
                  data-testid={`dsl-cat-${c.id}`}
                >
                  <span className="flex w-full items-center justify-between">
                    <span className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${CATEGORY_DOTS[c.id] ?? "bg-slate-500"}`} />
                      {CATEGORY_LABELS[c.id] ?? c.id}
                    </span>
                    <span className="text-xs text-slate-500">{c.count}</span>
                  </span>
                  <div className="mt-1 h-0.5 w-full overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.round((c.count / maxCatCount) * 100)}%`,
                        background: `linear-gradient(90deg, ${CATEGORY_COLORS[c.id] ?? "#475569"}70 0%, ${CATEGORY_COLORS[c.id] ?? "#475569"}20 100%)`,
                      }}
                    />
                  </div>
                </button>
                {category === c.id && subCats && subCats.length > 0 && (
                  <ul className="mt-1 ml-4 space-y-0.5 border-l border-slate-800/80 pl-2 text-xs">
                    {subCats.filter(s => s.id !== c.id).map((s) => (
                      <li key={s.id}>
                        <button
                          type="button"
                          onClick={() => { setCategory(s.id); setPage(1); }}
                          style={category === s.id
                            ? { borderLeftColor: CATEGORY_COLORS[c.id] ?? "#475569", backgroundColor: (CATEGORY_COLORS[c.id] ?? "#475569") + "10" }
                            : undefined}
                          className={`flex w-full items-center justify-between rounded px-2 py-1 text-left transition-all active:scale-[0.96] ${FOCUS_RING} ${
                            category === s.id
                              ? "border-l-2 pl-[5px] text-white ring-1 ring-inset ring-white/[0.03]"
                              : "text-slate-500 hover:bg-slate-800/40 hover:text-slate-300 hover:ring-1 hover:ring-inset hover:ring-white/[0.02]"
                          }`}
                        >
                          <span className="flex items-center gap-1.5 truncate">
                            <span className="h-1 w-1 shrink-0 rounded-full" style={{ backgroundColor: (CATEGORY_COLORS[c.id] ?? "#475569") + "80" }} />
                            {s.id.includes(".") ? s.id.split(".").slice(1).join(".") : s.id}
                          </span>
                          <span className="ml-2 shrink-0 text-slate-600">{s.count}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>

          {/* Popular tags section */}
          {stats.data?.top_tags && stats.data.top_tags.length > 0 && (
            <>
              <div className="mb-2 mt-3 flex items-center gap-2 border-t border-slate-800/70 pt-3">
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5 text-slate-600">
                  <path d="M1.5 5.5L5.5 1.5l3 0 0 3L4.5 8.5l-3-3zM7 3.5v.01" />
                </svg>
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Etiketler</span>
                {tagFilter && (
                  <button
                    type="button"
                    onClick={() => { setTagFilter(null); setPage(1); }}
                    className={`ml-auto flex items-center gap-0.5 text-[9px] text-slate-600 hover:text-slate-400 transition-all active:scale-90 ${FOCUS_RING}`}
                    title="Etiket filtresini kaldır"
                  >
                    <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2 w-2">
                      <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" />
                    </svg>
                    {tagFilter}
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-1">
                {stats.data.top_tags.slice(0, 12).map(({ tag, count }) => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => { setTagFilter(tagFilter === tag ? null : tag); setPage(1); }}
                    className={`rounded-md border px-1.5 py-0.5 font-mono text-[10px] transition-all active:scale-90 ring-1 ring-inset ${FOCUS_RING} ${
                      tagFilter === tag
                        ? "border-blue-500/30 bg-blue-500/15 text-blue-300 ring-blue-500/[0.08]"
                        : "border-slate-800/60 bg-slate-800/60 text-slate-500 hover:border-slate-700/60 hover:bg-slate-700/60 hover:text-slate-300 ring-white/[0.02]"
                    }`}
                    title={`${tag}: ${count} cümlecik`}
                  >
                    #{tag}
                    <span className="ml-0.5 opacity-50">{count}</span>
                  </button>
                ))}
              </div>
            </>
          )}

          {/* Recently viewed actions */}
          {recentActions.length > 0 && (
            <>
              <div className="mb-1.5 mt-3 flex items-center justify-between border-t border-slate-800/70 pt-3">
                <div className="flex items-center gap-1.5">
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" className="h-2.5 w-2.5 text-slate-600">
                    <circle cx="5" cy="5" r="4" />
                    <path d="M5 3v2.5l1.5 1" />
                  </svg>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Son Görüntülenenler</span>
                </div>
                <button
                  type="button"
                  onClick={() => setRecentActions([])}
                  className={`text-[9px] text-slate-600 hover:text-slate-400 transition-all active:scale-90 ${FOCUS_RING}`}
                  title="Geçmişi temizle"
                >
                  Temizle
                </button>
              </div>
              <ul className="space-y-0.5">
                {recentActions.map(({ action: a, viewedAt }) => {
                  const aSt = getStepType(a.description ?? "");
                  const aConfig = aSt ? STEP_TYPE_CONFIG[aSt] : null;
                  const aAlias = a.aliases?.tr?.[0] ?? a.aliases?.en?.[0] ?? a.id;
                  const aKw = aSt === "given" ? "Given" : aSt === "when" ? "When" : aSt === "then" ? "Then" : "And";
                  return (
                    <li key={a.id} className="group/recent-item">
                      <div className="flex items-center">
                        <button
                          type="button"
                          onClick={() => openAction(a)}
                          className={`flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-all active:scale-[0.99] hover:bg-slate-800 ${FOCUS_RING} ${
                            selected?.id === a.id ? "bg-slate-800/60 text-slate-200 ring-1 ring-inset ring-white/[0.04]" : "text-slate-500 hover:text-slate-200 hover:ring-1 hover:ring-inset hover:ring-white/[0.02]"
                          }`}
                        >
                          <span
                            className="h-1.5 w-1.5 shrink-0 rounded-full"
                            style={{ backgroundColor: aConfig?.borderColor ?? (CATEGORY_COLORS[a.category.split(".")[0]] ?? "#475569") }}
                          />
                          <span className="min-w-0 flex-1 truncate text-[11px]">{aAlias}</span>
                          <span className="shrink-0 text-[9px] text-slate-600" title={new Date(viewedAt).toLocaleTimeString("tr-TR")}>
                            {relativeTime(new Date(viewedAt).toISOString())}
                          </span>
                        </button>
                        {/* Quick-copy Gherkin on hover */}
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(`${aKw} ${aAlias}`).then(() => {
                              dispatchToast("Gherkin kopyalandı");
                            });
                          }}
                          className={`flex shrink-0 items-center justify-center rounded p-1 text-slate-600 opacity-0 transition-all active:scale-75 group-hover/recent-item:opacity-100 hover:text-slate-300 ${FOCUS_RING}`}
                          title={`"${aKw} ${aAlias}" kopyala`}
                        >
                          <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                            <rect x="1" y="2" width="7" height="7" rx="1" />
                            <path d="M3 1h6v7" />
                          </svg>
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </>
          )}
          </>
          )}
        </aside>

        {/* Sağ: Cümlecik listesi */}
        <main role="main" className="flex flex-1 min-h-0 flex-col">
          <div
            className={`mb-2 flex flex-wrap items-center gap-2 text-xs text-slate-500 transition-all duration-200 ${
              batchMode ? "rounded-lg border border-blue-500/20 bg-blue-500/5 px-2 py-1.5 shadow-sm shadow-blue-500/5 ring-1 ring-inset ring-blue-500/[0.05]" : ""
            }`}
            data-testid="dsl-result-count"
            aria-live="polite"
            aria-atomic="true"
          >
            <span className="flex items-center gap-1.5 font-medium">
              {isSearching ? (
                <>
                  <span className="text-base font-bold text-slate-200">{activeActions.length}</span>
                  <span className="text-slate-500">sonuç</span>
                </>
              ) : activeTotal > 50 ? (
                <>
                  <span className="font-semibold text-slate-300">{(page - 1) * 50 + 1}–{Math.min(page * 50, activeTotal)}</span>
                  <span className="text-slate-600">/ {activeTotal}</span>
                </>
              ) : (
                <>
                  <span className="font-semibold text-slate-300">{activeTotal}</span>
                  <span className="text-slate-500">cümlecik</span>
                </>
              )}
              {listQuery.isFetching && !isSearching && (
                <span className="inline-block h-3 w-3 animate-spin rounded-full border-[1.5px] border-slate-700/70 border-t-blue-400/90 shadow-sm shadow-blue-500/10" />
              )}
            </span>
            {isSearching && (
              <span className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[10px] transition-all ring-1 ring-inset ${
                aiEnabled
                  ? "border-violet-500/20 bg-violet-500/5 text-violet-300/80 ring-violet-500/[0.04]"
                  : "border-slate-700 bg-slate-800/60 text-slate-400 ring-white/[0.02]"
              }`}>
                {aiEnabled ? (
                  <svg viewBox="0 0 10 10" fill="currentColor" className="h-2 w-2 text-violet-400/60">
                    <path d="M5 1l.8 2.2L8 4l-2.2.8L5 7l-.8-2.2L2 4l2.2-.8L5 1z" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2 w-2 text-slate-600">
                    <circle cx="4.5" cy="4.5" r="3.5" />
                    <path d="M7 7l2 2" />
                  </svg>
                )}
                {search}
              </span>
            )}
            {category && (
              <button
                type="button"
                onClick={() => { setCategory(null); setPage(1); }}
                className={`flex items-center gap-1 rounded-full border border-slate-700 bg-slate-800/60 px-2 py-0.5 text-[10px] text-slate-400 hover:border-slate-600 hover:text-slate-200 transition-all active:scale-[0.95] ring-1 ring-inset ring-white/[0.02] ${FOCUS_RING}`}
                title="Kategori filtresini kaldır"
              >
                <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: CATEGORY_COLORS[category.split(".")[0]] ?? "#475569" }} />
                {getCategoryLabel(category)}
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2 w-2 text-slate-600">
                  <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" />
                </svg>
              </button>
            )}
            {stepTypeFilter !== "all" && (
              <button
                type="button"
                onClick={() => { setStepTypeFilter("all"); setPage(1); }}
                className={`flex items-center gap-1 rounded-full border border-slate-700 bg-slate-800/60 px-2 py-0.5 text-[10px] text-slate-400 hover:border-slate-600 hover:text-slate-200 transition-all active:scale-[0.95] ring-1 ring-inset ring-white/[0.02] ${FOCUS_RING}`}
                title="Adım tipi filtresini kaldır"
              >
                <span className={`h-1.5 w-1.5 rounded-full ${STEP_TYPE_FILTER_CONFIG[stepTypeFilter].dot}`} />
                {STEP_TYPE_FILTER_CONFIG[stepTypeFilter].label}
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2 w-2 text-slate-600">
                  <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" />
                </svg>
              </button>
            )}
            {tagFilter && (
              <button
                type="button"
                onClick={() => { setTagFilter(null); setPage(1); }}
                className={`flex items-center gap-1 rounded-full border border-blue-500/25 bg-blue-500/[0.07] px-2 py-0.5 text-[10px] text-blue-400/80 hover:border-blue-500/40 hover:text-blue-300 transition-all active:scale-[0.95] ring-1 ring-inset ring-blue-500/[0.04] ${FOCUS_RING}`}
                title="Etiket filtresini kaldır"
              >
                <span className="font-mono">#{tagFilter}</span>
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2 w-2 text-slate-600">
                  <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" />
                </svg>
              </button>
            )}
            {showFavoritesOnly && (
              <button
                type="button"
                onClick={() => setShowFavoritesOnly(false)}
                className={`flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-400 hover:border-amber-500/50 hover:text-amber-300 transition-all active:scale-[0.95] ring-1 ring-inset ring-amber-500/[0.06] ${FOCUS_RING}`}
                title="Favoriler filtresini kaldır"
              >
                <svg viewBox="0 0 10 10" fill="currentColor" className="h-2 w-2">
                  <path d="M5 1l1.2 2.5L9 3.8l-2 2 .5 2.7L5 7.2 2.5 8.5 3 5.8 1 3.8l2.8-.3L5 1z" />
                </svg>
                <span>Favoriler</span>
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2 w-2 text-amber-600">
                  <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" />
                </svg>
              </button>
            )}
            {isSearching && aiEnabled && activeMode && (
              <span className="rounded-full border border-violet-500/15 bg-violet-500/5 px-1.5 py-px font-mono text-[9px] uppercase tracking-wider text-violet-400/60 ring-1 ring-inset ring-violet-500/[0.03]">
                {activeMode}
              </span>
            )}
            {/* Export visible actions as text */}
            {activeActions.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  const lines = activeActions.flatMap((a) => {
                    const tr = a.aliases?.tr ?? [];
                    const en = a.aliases?.en ?? [];
                    const parts: string[] = [`# ${a.id} (${a.category})`];
                    if (tr.length) parts.push(`TR: ${tr.join(" | ")}`);
                    if (en.length) parts.push(`EN: ${en.join(" | ")}`);
                    return parts;
                  });
                  const blob = new Blob([lines.join("\n")], { type: "text/plain" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url; a.download = "dsl-export.txt"; a.click();
                  URL.revokeObjectURL(url);
                }}
                className={`flex items-center gap-1 rounded-full border border-slate-700/60 px-2 py-0.5 text-[10px] text-slate-500 hover:border-slate-600 hover:text-slate-300 transition-all active:scale-[0.95] ring-1 ring-inset ring-white/[0.02] hover:ring-white/[0.03] ${FOCUS_RING}`}
                title={`${activeActions.length} cümleciği .txt olarak indir`}
              >
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2 w-2">
                  <path d="M5 1v5M2.5 4l2.5 3L7.5 4M1 8.5h8" />
                </svg>
                TXT
              </button>
            )}
            {/* Export as Gherkin scenario */}
            {activeActions.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  const lines = activeActions.map((a) => {
                    const st = getStepType(a.description ?? "");
                    const kw = st === "given" ? "Given" : st === "when" ? "When" : st === "then" ? "Then" : "And";
                    const alias = a.aliases?.tr?.[0] ?? a.aliases?.en?.[0] ?? a.id;
                    return `${kw} ${alias}`;
                  });
                  navigator.clipboard.writeText(lines.join("\n")).then(() => {
                    dispatchToast("Gherkin senaryosu kopyalandı");
                  });
                }}
                className={`flex items-center gap-1 rounded-full border border-slate-700/60 px-2 py-0.5 text-[10px] text-slate-500 hover:border-emerald-500/30 hover:text-emerald-400 transition-all active:scale-[0.95] ring-1 ring-inset ring-white/[0.02] hover:ring-emerald-500/[0.04] ${FOCUS_RING}`}
                title={`${activeActions.length} adımı Gherkin olarak kopyala`}
              >
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2 w-2">
                  <rect x="1" y="2" width="7" height="7" rx="1" />
                  <path d="M3 1h6v7" />
                </svg>
                Gherkin
              </button>
            )}
            {/* CSV export */}
            {activeActions.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  const header = "ID,Category,StepType,TR_Aliases,EN_Aliases,Parameters,Tags";
                  const rows = activeActions.map((a) => {
                    const st = getStepType(a.description ?? "") ?? "";
                    const tr = (a.aliases?.tr ?? []).join(";").replace(/"/g, '""');
                    const en = (a.aliases?.en ?? []).join(";").replace(/"/g, '""');
                    const params = (a.parameters ?? []).map((p) => p.name).join(";");
                    const tags = (a.tags ?? []).join(";");
                    return `${a.id},${a.category},${st},"${tr}","${en}","${params}","${tags}"`;
                  });
                  const csv = [header, ...rows].join("\n");
                  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
                  const url = URL.createObjectURL(blob);
                  const el = document.createElement("a");
                  el.href = url; el.download = "dsl-export.csv"; el.click();
                  URL.revokeObjectURL(url);
                }}
                className={`flex items-center gap-1 rounded-full border border-slate-700/60 px-2 py-0.5 text-[10px] text-slate-500 hover:border-sky-500/30 hover:text-sky-400 transition-all active:scale-[0.95] ring-1 ring-inset ring-white/[0.02] hover:ring-sky-500/[0.04] ${FOCUS_RING}`}
                title={`${activeActions.length} cümleciği CSV olarak indir`}
              >
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2 w-2">
                  <path d="M5 1v5M2.5 4l2.5 3L7.5 4M1 8.5h8" />
                </svg>
                CSV
              </button>
            )}

            {/* Batch mode toggle + actions */}
            {activeActions.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  setBatchMode((v) => !v);
                  setSelectedBatchIds(new Set());
                }}
                className={`rounded-full border px-2 py-0.5 text-[10px] transition-all active:scale-[0.95] ring-1 ring-inset ${FOCUS_RING} ${
                  batchMode
                    ? "border-blue-500/40 bg-blue-500/10 text-blue-300 ring-blue-500/[0.06]"
                    : "border-slate-700/60 text-slate-500 hover:border-slate-600 hover:text-slate-300 ring-white/[0.02]"
                }`}
                title="Toplu seçim modunu aç/kapat"
                aria-pressed={batchMode}
              >
                <span className="flex items-center gap-1">
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                    <rect x="1" y="1" width="8" height="8" rx="1" />
                    <path d="M3 5l1.5 1.5 2.5-3" />
                  </svg>
                  Seç
                </span>
              </button>
            )}
            {batchMode && (
              <>
                <span className="flex items-center gap-1 text-[10px] text-blue-400/70">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
                  Seçim modu
                </span>
                <button
                  type="button"
                  onClick={() => {
                    if (selectedBatchIds.size === activeActions.length) {
                      setSelectedBatchIds(new Set());
                    } else {
                      setSelectedBatchIds(new Set(activeActions.map((a) => a.id)));
                    }
                  }}
                  className={`rounded-full border border-blue-500/20 bg-blue-500/5 px-2 py-0.5 text-[10px] text-blue-400/70 hover:border-blue-500/40 hover:text-blue-300 transition-all active:scale-[0.95] ring-1 ring-inset ring-blue-500/[0.04] ${FOCUS_RING}`}
                >
                  {selectedBatchIds.size === activeActions.length ? "Seçimi kaldır" : "Tümünü seç"}
                </button>
              </>
            )}
            {batchMode && selectedBatchIds.size > 0 && (
              <>
                <span className="text-[10px] text-blue-400">{selectedBatchIds.size} seçili</span>
                <button
                  type="button"
                  onClick={() => {
                    const lines = activeActions
                      .filter((a) => selectedBatchIds.has(a.id))
                      .flatMap((a) => {
                        const st = getStepType(a.description ?? "");
                        const kw = st === "given" ? "Given" : st === "when" ? "When" : st === "then" ? "Then" : "And";
                        return [
                          ...(a.aliases?.tr?.map((al) => `${kw} ${al}`) ?? []),
                          ...(a.aliases?.en?.map((al) => `${kw} ${al}`) ?? []),
                        ];
                      });
                    navigator.clipboard.writeText(lines.join("\n")).then(() => {
                      dispatchToast(`${selectedBatchIds.size} adım kopyalandı`);
                      setBatchMode(false);
                      setSelectedBatchIds(new Set());
                    });
                  }}
                  className={`flex items-center gap-1 rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[10px] text-blue-300 hover:bg-blue-500/20 transition-all active:scale-[0.95] ring-1 ring-inset ring-blue-500/[0.06] ${FOCUS_RING}`}
                >
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2 w-2">
                    <rect x="1" y="2" width="7" height="7" rx="1" />
                    <path d="M3 1h6v7" />
                  </svg>
                  Kopyala
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setFavorites((prev) => {
                      const next = new Set(prev);
                      let added = 0;
                      for (const id of selectedBatchIds) { if (!next.has(id)) { next.add(id); added++; } }
                      try { localStorage.setItem("dsl_favorites", JSON.stringify([...next])); } catch { /* */ }
                      dispatchToast(`${added > 0 ? added : selectedBatchIds.size} cümlecik favorilere eklendi`, "favorite");
                      return next;
                    });
                    setBatchMode(false);
                    setSelectedBatchIds(new Set());
                  }}
                  className={`flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-400 hover:bg-amber-500/20 transition-all active:scale-[0.95] ring-1 ring-inset ring-amber-500/[0.06] ${FOCUS_RING}`}
                  title="Seçilenleri favorilere ekle"
                >
                  <svg viewBox="0 0 10 10" fill="currentColor" className="h-2 w-2">
                    <path d="M5 1l1.2 2.5L9 3.8l-2 2 .5 2.7L5 7.2 2.5 8.5 3 5.8 1 3.8l2.8-.3L5 1z" />
                  </svg>
                  Favori
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedBatchIds(new Set())}
                  className={`text-[10px] text-slate-600 hover:text-slate-400 transition-all active:scale-95 ${FOCUS_RING}`}
                >
                  Seçimi temizle
                </button>
              </>
            )}

            {/* Sort order + View controls */}
            <div className="ml-auto flex items-center gap-0.5">
              {/* Sort buttons */}
              <span className="hidden text-[10px] text-slate-600 sm:mr-1 sm:inline">Sırala:</span>
              {([
                { key: "default", label: (
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                    <path d="M5 2v6M3 4l2-2 2 2M3 6l2 2 2-2" />
                  </svg>
                ), title: "Varsayılan sıra" },
                { key: "az", label: (
                  <span className="flex items-center gap-0.5">
                    A
                    <svg viewBox="0 0 8 6" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-1.5 w-2"><path d="M1 3h6M5 1l2 2-2 2" /></svg>
                    Z
                  </span>
                ), title: "A'dan Z'ye" },
                { key: "za", label: (
                  <span className="flex items-center gap-0.5">
                    Z
                    <svg viewBox="0 0 8 6" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-1.5 w-2"><path d="M1 3h6M5 1l2 2-2 2" /></svg>
                    A
                  </span>
                ), title: "Z'den A'ya" },
                { key: "step", label: "G·W·T", title: "Adım tipine göre (Given→When→Then)" },
              ] as const).map(({ key, label, title }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setSortOrder(key)}
                  className={`flex items-center rounded px-2 py-1 text-[10px] transition-all active:scale-[0.92] ${FOCUS_RING} ${
                    sortOrder === key
                      ? "bg-slate-700 text-white ring-1 ring-slate-600/30 shadow-sm"
                      : "text-slate-600 hover:bg-slate-800/60 hover:text-slate-400"
                  }`}
                  title={title}
                >
                  {label}
                </button>
              ))}

              {/* Divider */}
              <span className="mx-1.5 h-3.5 w-px bg-slate-800" aria-hidden="true" />

              {/* View mode: grid/list toggle */}
              <button
                type="button"
                onClick={() => setViewMode(viewMode === "list" ? "grid" : "list")}
                className={`flex h-6 w-6 items-center justify-center rounded transition-all active:scale-90 ${FOCUS_RING} ${
                  viewMode === "list"
                    ? "bg-slate-700 text-white ring-1 ring-slate-600/30 shadow-sm"
                    : "text-slate-600 hover:bg-slate-800/60 hover:text-slate-400"
                }`}
                title={viewMode === "list" ? "Izgara görünümüne geç" : "Liste görünümüne geç"}
              >
                {viewMode === "list" ? (
                  <svg viewBox="0 0 14 14" fill="currentColor" className="h-3 w-3">
                    <rect x="0" y="0" width="6" height="6" rx="1"/>
                    <rect x="8" y="0" width="6" height="6" rx="1"/>
                    <rect x="0" y="8" width="6" height="6" rx="1"/>
                    <rect x="8" y="8" width="6" height="6" rx="1"/>
                  </svg>
                ) : (
                  <svg viewBox="0 0 14 14" fill="currentColor" className="h-3 w-3">
                    <rect x="0" y="1" width="14" height="2.5" rx="1"/>
                    <rect x="0" y="5.75" width="14" height="2.5" rx="1"/>
                    <rect x="0" y="10.5" width="14" height="2.5" rx="1"/>
                  </svg>
                )}
              </button>

              {/* Grid column count (only in grid mode) */}
              {viewMode === "grid" && (
                <>
                  <span className="mx-0.5 h-3.5 w-px bg-slate-800" aria-hidden="true" />
                  {([1, 2, 3] as const).map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setGridCols(n)}
                      className={`flex h-6 w-6 items-center justify-center rounded text-[10px] font-mono transition-all active:scale-90 ${FOCUS_RING} ${
                        gridCols === n
                          ? "bg-slate-700 text-white ring-1 ring-slate-600/30 shadow-sm"
                          : "text-slate-600 hover:bg-slate-800/60 hover:text-slate-400"
                      }`}
                      title={`${n} sütun`}
                    >
                      {n}
                    </button>
                  ))}
                </>
              )}
            </div>

            {/* Reset all filters */}
            {(category || stepTypeFilter !== "all" || langFilter !== "all" || isSearching || tagFilter || showFavoritesOnly) && (
              <button
                type="button"
                onClick={() => {
                  setSearch(""); setCategory(forceCategory ?? null);
                  setLangFilter("all"); setStepTypeFilter("all"); setTagFilter(null);
                  setShowFavoritesOnly(false); setPage(1);
                }}
                className={`flex items-center gap-1 rounded-full border border-slate-600/50 bg-slate-800/40 px-2.5 py-0.5 text-[10px] text-slate-400 hover:border-slate-500 hover:bg-slate-800 hover:text-slate-200 transition-all active:scale-[0.95] ring-1 ring-inset ring-white/[0.03] ${FOCUS_RING}`}
              >
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2 w-2">
                  <path d="M8 2L2 8M2 2l6 6" />
                </svg>
                Sıfırla
              </button>
            )}
          </div>

          {/* Recently-viewed quick-access strip (shows when not searching, and there are recent items) */}
          {!isSearching && !selected && recentActions.length > 0 && (
            <div className="mb-2 flex items-center gap-1.5 overflow-x-auto pb-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              <span className="shrink-0 text-[9px] font-semibold uppercase tracking-widest text-slate-600">Son:</span>
              {recentActions.slice(0, 5).map(({ action: ra }, raIdx) => {
                const raSt = getStepType(ra.description ?? "");
                const raConfig = raSt ? STEP_TYPE_CONFIG[raSt] : null;
                const raKw = raSt === "given" ? "G" : raSt === "when" ? "W" : raSt === "then" ? "T" : null;
                return (
                  <button
                    key={ra.id}
                    type="button"
                    onClick={() => openAction(ra)}
                    className={`group/recent flex shrink-0 items-center gap-1.5 rounded-full border border-slate-800/50 bg-slate-900/30 px-2.5 py-0.5 text-[10px] text-slate-500 transition-all hover:border-slate-700/60 hover:bg-slate-900/60 hover:text-slate-300 hover:-translate-y-px active:translate-y-0 active:scale-[0.96] ring-1 ring-inset ring-white/[0.02] hover:ring-white/[0.03] animate-fade-in ${FOCUS_RING}`}
                    style={{ animationDelay: `${raIdx * 40}ms`, animationFillMode: "both" }}
                  >
                    {raKw && raConfig ? (
                      <span
                        className="shrink-0 text-[9px] font-bold"
                        style={{ color: raConfig.borderColor + "CC" }}
                      >
                        {raKw}
                      </span>
                    ) : (
                      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${CATEGORY_DOTS[ra.category.split(".")[0]] ?? "bg-slate-500"}`} />
                    )}
                    <span className="max-w-[140px] truncate font-mono text-[10px]">
                      {ra.aliases?.tr?.[0] ?? ra.aliases?.en?.[0] ?? ra.id}
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          {/* Category context banner */}
          {category && !isSearching && (
            <div
              className="mb-3 flex items-center gap-3 rounded-lg border border-slate-800/60 px-3 py-2.5 shadow-sm shadow-black/20 ring-1 ring-inset ring-white/[0.02] animate-fade-in"
              style={{
                borderLeftColor: CATEGORY_COLORS[category.split(".")[0]] ?? "#475569",
                borderLeftWidth: "3px",
                background: `linear-gradient(90deg, ${(CATEGORY_COLORS[category.split(".")[0]] ?? "#475569")}0d 0%, transparent 60%)`,
              }}
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-slate-200">{getCategoryLabel(category)}</span>
                  {activeTotal > 0 && (
                    <span className="rounded-full border border-slate-700/60 bg-slate-800/60 px-2 py-0.5 text-[10px] text-slate-400 ring-1 ring-inset ring-white/[0.02]">
                      {activeTotal} cümlecik
                    </span>
                  )}
                  {/* Step-type mini-breakdown for this category */}
                  {stats.data?.by_step_type && (
                    <span className="flex items-center gap-1 text-[10px] text-slate-600">
                      {(["given", "when", "then"] as StepType[]).map((s) => {
                        const c = STEP_TYPE_CONFIG[s];
                        return (
                          <button
                            key={s}
                            type="button"
                            onClick={() => { setStepTypeFilter(stepTypeFilter === s ? "all" : s); setPage(1); }}
                            className={`flex items-center gap-0.5 rounded px-1 py-0.5 transition-all active:scale-90 ${FOCUS_RING} ${
                              stepTypeFilter === s ? "bg-slate-700/60 text-slate-200 ring-1 ring-inset ring-white/[0.04]" : "hover:bg-slate-800/60 hover:text-slate-400"
                            }`}
                            title={`${c.label} olarak filtrele`}
                          >
                            <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: c.borderColor }} />
                            <span>{c.label.slice(0, 3)}</span>
                          </button>
                        );
                      })}
                    </span>
                  )}
                </div>
              </div>
              {!forceCategory && (
                <button
                  type="button"
                  onClick={() => { setCategory(null); setPage(1); }}
                  className={`shrink-0 rounded-md border border-slate-700/50 bg-slate-800/50 px-2 py-0.5 text-[10px] text-slate-500 transition-all active:scale-[0.95] hover:border-slate-600 hover:bg-slate-800 hover:text-slate-300 ring-1 ring-inset ring-white/[0.02] shadow-sm shadow-black/10 ${FOCUS_RING}`}
                  title="Kategori filtresini kaldır"
                >
                  <span className="flex items-center gap-1">
                    Tümü
                    <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2 w-2">
                      <path d="M2 5h6M5.5 2l3 3-3 3" />
                    </svg>
                  </span>
                </button>
              )}
            </div>
          )}

          {/* First-visit hints panel */}
          {showHints && recentActions.length === 0 && !isSearching && (
            <div className="mb-3 overflow-hidden rounded-xl border border-slate-800/80 bg-slate-900/60 ring-1 ring-inset ring-white/[0.02] shadow-sm shadow-black/20 animate-fade-in">
              <div className="flex items-center justify-between border-b border-slate-800/60 px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-md bg-blue-500/15 ring-1 ring-inset ring-blue-500/[0.12]">
                    <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3 text-blue-400">
                      <circle cx="5" cy="4" r="2.5" />
                      <path d="M3.5 6.5c0 1 .7 1.5 1.5 1.5s1.5-.5 1.5-1.5M5 8.5v.5" />
                    </svg>
                  </span>
                  <span className="text-xs font-semibold text-slate-300">Hızlı Başlangıç</span>
                  <span className="text-[10px] text-slate-600">— Klavye kısayolları</span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setShowHints(false);
                    try { localStorage.setItem("dsl_hints_dismissed", "1"); } catch { /* */ }
                  }}
                  className={`flex h-5 w-5 items-center justify-center rounded-md border border-slate-800 bg-slate-900 text-slate-600 hover:text-slate-300 hover:border-slate-700 ring-1 ring-inset ring-white/[0.03] transition-all active:scale-90 ${FOCUS_RING}`}
                  title="İpuçlarını kapat"
                  aria-label="İpuçlarını kapat"
                >
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2 w-2">
                    <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" />
                  </svg>
                </button>
              </div>
              <div className="grid grid-cols-2 gap-px bg-slate-800/30 sm:grid-cols-3 lg:grid-cols-6">
                {[
                  { key: "⌘K", desc: "Ara", icon: <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-3.5 w-3.5"><circle cx="4.5" cy="4.5" r="3.5" /><path d="M7.5 7.5l2 2" /></svg> },
                  { key: "j / k", desc: "Gezin", icon: <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-3.5 w-3.5"><path d="M5 1v8M2 4l3-3 3 3M2 6l3 3 3-3" /></svg> },
                  { key: "Enter", desc: "Aç", icon: <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M1 5h6M5 2l3 3-3 3" /></svg> },
                  { key: "b", desc: "Toplu seç", icon: <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><rect x="1" y="1" width="8" height="8" rx="1" /><path d="M3 5l1.5 1.5 2.5-3" /></svg> },
                  { key: "c", desc: "Kopyala", icon: <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><rect x="1" y="2.5" width="6.5" height="7" rx="1" /><path d="M3.5 2.5V1.5A.5.5 0 014 1h5a.5.5 0 01.5.5v7a.5.5 0 01-.5.5h-1" /></svg> },
                  { key: "?", desc: "Kısayollar", icon: <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-3.5 w-3.5"><circle cx="5" cy="5" r="4" /><path d="M3.8 3.5A1.5 1.5 0 016.5 4.8C6.5 6 5 6 5 7M5 8.5v.5" /></svg> },
                ].map(({ key, desc, icon }) => (
                  <div key={key} className="flex flex-col items-center gap-1.5 bg-slate-900/40 px-3 py-3 text-center transition-colors hover:bg-slate-800/50 group/hint">
                    <span className="text-slate-400 transition-colors group-hover/hint:text-slate-300">{icon}</span>
                    <kbd className="rounded border border-slate-700/70 bg-slate-800/90 px-2 py-0.5 font-mono text-[10px] text-slate-200 shadow-sm ring-1 ring-inset ring-white/[0.04]">{key}</kbd>
                    <span className="text-[10px] text-slate-400 group-hover/hint:text-slate-300 transition-colors">{desc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div
            ref={cardScrollRef}
            className="relative flex-1 overflow-y-auto pr-1 [scrollbar-width:thin] [scrollbar-color:theme(colors.slate.800)_transparent]"
            onScroll={(e) => setCardScrolled((e.currentTarget as HTMLDivElement).scrollTop > 200)}
          >
            {listQuery.isError && !isSearching ? (
              <div className="flex flex-col items-center justify-center rounded-xl border border-red-800/30 bg-red-900/[0.08] p-12 text-center ring-1 ring-inset ring-red-500/[0.04] animate-fade-in">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-red-800/40 bg-red-900/20 ring-1 ring-inset ring-red-500/[0.06]">
                  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6 text-red-400/70">
                    <circle cx="10" cy="10" r="8" />
                    <path d="M10 6v5M10 14v.5" />
                  </svg>
                </div>
                <p className="text-sm font-semibold text-red-300">Veriler yüklenemedi</p>
                <p className="mt-1.5 max-w-xs text-xs leading-relaxed text-red-400/60">
                  {listQuery.error instanceof Error ? listQuery.error.message : "Sunucuya ulaşılamıyor. Lütfen ağ bağlantınızı kontrol edin."}
                </p>
                <button
                  type="button"
                  onClick={() => listQuery.refetch()}
                  className={`mt-4 flex items-center gap-1.5 rounded-lg border border-red-700/40 bg-red-900/20 px-3 py-1.5 text-xs text-red-300 hover:bg-red-900/40 transition-all active:scale-[0.97] ring-1 ring-inset ring-red-500/[0.06] shadow-sm shadow-black/10 ${FOCUS_RING}`}
                >
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2.5 w-2.5">
                    <path d="M1.5 5A3.5 3.5 0 108 2M1.5 1v4h4" />
                  </svg>
                  Tekrar dene
                </button>
              </div>
            ) : (listQuery.isLoading && !isSearching) || (isAiLoading && isSearching && activeActions.length === 0) ? (
              <div className={
                viewMode === "list"
                  ? "flex flex-col gap-1.5"
                  : gridCols === 1
                  ? "flex flex-col gap-3"
                  : gridCols === 2
                  ? "grid gap-3 grid-cols-1 xl:grid-cols-2"
                  : "grid gap-3 grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3"
              }>
                {Array.from({ length: isAiLoading ? 3 : 6 }).map((_, i) => <SkeletonCard key={i} compact={viewMode === "list"} />)}
              </div>
            ) : activeActions.length === 0 ? (
              <div className="flex flex-col items-center justify-center rounded-xl border border-slate-800/40 bg-slate-900/20 p-12 text-center ring-1 ring-inset ring-white/[0.015] animate-fade-in">
                <div className={`mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border ring-1 ring-inset shadow-lg ${
                  showFavoritesOnly
                    ? "border-amber-500/20 bg-amber-500/5 text-amber-400/50 ring-amber-500/[0.05] shadow-amber-500/[0.06]"
                    : isSearching
                    ? "border-slate-700/40 bg-slate-800/30 text-slate-500/50 ring-white/[0.02] shadow-black/20"
                    : "border-slate-700/40 bg-slate-800/30 text-slate-600/50 ring-white/[0.02] shadow-black/20"
                }`}>
                  {showFavoritesOnly ? (
                    <svg viewBox="0 0 20 20" fill="currentColor" className="h-7 w-7 opacity-60">
                      <path d="M10 2l2.4 5L18 7.6l-4 4 1 5.5L10 14.4l-5 2.7 1-5.5-4-4 5.6-.6L10 2z" />
                    </svg>
                  ) : isSearching ? (
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-7 w-7 opacity-60">
                      <circle cx="9" cy="9" r="6" />
                      <path d="M15 15l4 4" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-7 w-7 opacity-60">
                      <rect x="3" y="4" width="14" height="13" rx="2" />
                      <path d="M8 4V2M12 4V2M3 8h14" />
                    </svg>
                  )}
                </div>
                <p className="text-sm font-semibold text-slate-300">
                  {showFavoritesOnly
                    ? "Favori bulunamadı"
                    : isSearching
                    ? "Sonuç bulunamadı"
                    : "Cümlecik yok"}
                </p>
                <p className="mt-1.5 max-w-xs text-xs leading-relaxed text-slate-500">
                  {showFavoritesOnly
                    ? "Henüz favori eklenmedi. Kartlarda yıldız ikonuna tıklayarak ekleyebilirsiniz."
                    : isSearching
                    ? <>
                        <span className="font-mono text-slate-400">&ldquo;{search}&rdquo;</span>
                        {" "}için eşleşen cümlecik bulunamadı
                      </>
                    : stepTypeFilter !== "all"
                    ? <><span className="font-medium">{STEP_TYPE_FILTER_CONFIG[stepTypeFilter].label}</span> adım tipi ve seçili kategoride cümlecik yok</>
                    : "Bu filtre kombinasyonu için kayıtlı cümlecik bulunmuyor"}
                </p>
                {isSearching && stats.data?.top_tags && stats.data.top_tags.length > 0 && (
                  <div className="mt-4 text-center">
                    <p className="mb-2 text-[10px] uppercase tracking-wider text-slate-600">Etiketle filtrele</p>
                    <div className="flex flex-wrap justify-center gap-1.5">
                      {stats.data.top_tags.slice(0, 8).map(({ tag }) => (
                        <button
                          key={tag}
                          type="button"
                          onClick={() => { setSearch(""); setTagFilter(tag); setPage(1); }}
                          className={`rounded-full border border-slate-700/60 bg-slate-800/50 px-2.5 py-1 font-mono text-[11px] text-slate-400 hover:border-blue-500/30 hover:bg-blue-500/[0.07] hover:text-blue-300 transition-all active:scale-[0.95] ring-1 ring-inset ring-white/[0.02] hover:ring-blue-500/[0.05] ${FOCUS_RING}`}
                        >
                          #{tag}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {isSearching && !aiEnabled && (
                  <div className="mt-4">
                    <button
                      type="button"
                      onClick={() => { setSearchMode("ai"); }}
                      className={`rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-1.5 text-xs text-violet-300 hover:bg-violet-500/20 ring-1 ring-inset ring-violet-500/[0.08] transition-all active:scale-[0.97] ${FOCUS_RING}`}
                    >
                      <span className="flex items-center gap-1.5">
                        <svg viewBox="0 0 10 10" fill="currentColor" className="h-2.5 w-2.5 text-violet-400">
                          <path d="M5 1l.8 2.2L8 4l-2.2.8L5 7l-.8-2.2L2 4l2.2-.8L5 1z" />
                        </svg>
                        AI arama ile dene
                      </span>
                    </button>
                  </div>
                )}
                {(category || stepTypeFilter !== "all") && (
                  <button
                    type="button"
                    onClick={() => { setCategory(forceCategory ?? null); setStepTypeFilter("all"); setTagFilter(null); setPage(1); }}
                    className={`mt-3 rounded-lg border border-slate-700/80 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:border-slate-600 ring-1 ring-inset ring-white/[0.03] shadow-sm shadow-black/10 transition-all active:scale-[0.97] ${FOCUS_RING}`}
                  >
                    Filtreleri temizle
                  </button>
                )}
              </div>
            ) : (
              <div
                role="list"
                aria-label="DSL cümleciği listesi"
                className={`transition-opacity duration-200 animate-fade-in ${
                  listQuery.isFetching && !isSearching ? "opacity-50" : "opacity-100"
                } ${
                  viewMode === "list"
                    ? "flex flex-col gap-1.5"
                    : gridCols === 1
                    ? "flex flex-col gap-3"
                    : gridCols === 2
                    ? "grid gap-3 grid-cols-1 xl:grid-cols-2"
                    : "grid gap-3 grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3"
                }`}
              >
                {activeActions.map((a, i) => {
                  const hit = hitByActionId.get(a.id);
                  const canVote = isSearching && aiEnabled && !!hit;
                  const isBatchSelected = selectedBatchIds.has(a.id);
                  // Section header when sorted by step type
                  const prevA = i > 0 ? activeActions[i - 1] : null;
                  const currSt = getStepType(a.description ?? "");
                  const prevSt = prevA ? getStepType(prevA.description ?? "") : null;
                  const showStepHeader = sortOrder === "step" && currSt && currSt !== prevSt;
                  return (
                    <React.Fragment key={a.id}>
                    {showStepHeader && currSt && (() => {
                      const cfg = STEP_TYPE_CONFIG[currSt];
                      const groupCount = stepGroupCounts[currSt] ?? 0;
                      return (
                        <div
                          className={`${viewMode === "list" ? "" : "col-span-full"} flex items-center gap-2 py-2 text-xs font-semibold`}
                          style={{ color: cfg.borderColor }}
                        >
                          <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: cfg.borderColor }} />
                          <span>{cfg.label}</span>
                          <div className="flex-1 h-px opacity-20 rounded-full" style={{ backgroundColor: cfg.borderColor }} />
                          <span
                            className="shrink-0 rounded-full border px-2 py-0.5 text-[9px] font-semibold"
                            style={{
                              borderColor: cfg.borderColor + "30",
                              backgroundColor: cfg.borderColor + "10",
                              color: cfg.borderColor + "CC",
                            }}
                          >
                            {groupCount}
                          </span>
                        </div>
                      );
                    })()}
                    <div
                      className={`relative animate-fade-in ${batchMode ? "cursor-pointer" : ""} ${
                        focusedIdx === i && !batchMode
                          ? "rounded-xl ring-2 ring-blue-500/50 ring-offset-2 ring-offset-slate-950 shadow-lg shadow-blue-500/10"
                          : ""
                      }`}
                      style={{ animationDelay: `${Math.min(i * 25, 200)}ms`, animationFillMode: "both" }}
                      onClick={batchMode ? () => {
                        setSelectedBatchIds((prev) => {
                          const next = new Set(prev);
                          if (next.has(a.id)) next.delete(a.id);
                          else next.add(a.id);
                          return next;
                        });
                      } : undefined}
                    >
                      {batchMode && (
                        <div className={`absolute -top-1 -left-1 z-10 flex h-5 w-5 items-center justify-center rounded-full border-2 transition-all shadow-sm ${
                          isBatchSelected
                            ? "border-blue-500 bg-blue-500 text-white shadow-blue-500/30"
                            : "border-slate-600 bg-slate-900 text-slate-600 hover:border-blue-500/60"
                        }`}>
                          {isBatchSelected && (
                            <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
                              <path d="M2 5.5l2 2 4-4" />
                            </svg>
                          )}
                        </div>
                      )}
                      <ActionCard
                        action={a}
                        highlight={isSearching ? search : undefined}
                        onOpen={batchMode ? () => {} : openAction}
                        hit={hit}
                        onVote={canVote ? (v) => handleVote(a.id, v) : undefined}
                        votedAs={votes[a.id] ?? null}
                        onTagClick={(tag) => { setTagFilter(tag); setPage(1); }}
                        activeTag={tagFilter}
                        isSelected={batchMode ? isBatchSelected : selected?.id === a.id}
                        isFavorite={favorites.has(a.id)}
                        onToggleFavorite={!batchMode ? toggleFavorite : undefined}
                        compact={viewMode === "list"}
                      />
                    </div>
                    </React.Fragment>
                  );
                })}
              </div>
            )}
          </div>

          {!isSearching && activeTotal > 50 && (
            <div className="mt-3 rounded-lg border border-slate-800/50 bg-slate-900/30 p-3 shadow-sm shadow-black/20 ring-1 ring-inset ring-white/[0.02]">
              {/* Progress bar showing position in full result set */}
              <div className="mb-3 flex items-center gap-2">
                <div className="flex-1 h-0.5 overflow-hidden rounded-full bg-slate-800/80">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-500/70 via-blue-400/50 to-blue-400/20 transition-all duration-700"
                    style={{ width: `${Math.min(100, Math.round((page / Math.ceil(activeTotal / 50)) * 100))}%` }}
                  />
                </div>
                <span className="shrink-0 rounded border border-slate-800/60 bg-slate-900/60 px-1.5 py-0.5 font-mono text-[9px] text-slate-500 ring-1 ring-inset ring-white/[0.02]">
                  {page} / {Math.ceil(activeTotal / 50)}
                </span>
              </div>
            <div className="flex items-center justify-center gap-2">
              <button
                type="button"
                className={`flex items-center justify-center rounded-lg border border-slate-700 bg-slate-900 p-1.5 text-xs text-slate-300 transition-all hover:bg-slate-800 hover:text-white active:scale-[0.93] disabled:cursor-not-allowed disabled:opacity-30 ring-1 ring-inset ring-white/[0.03] shadow-sm shadow-black/10 ${FOCUS_RING}`}
                onClick={() => setPage(1)}
                disabled={page === 1}
                title="İlk sayfa"
              >
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
                  <path d="M7 2L4 5l3 3M4 2L1 5l3 3" />
                </svg>
              </button>
              <button
                type="button"
                className={`flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 transition-all hover:bg-slate-800 hover:text-white active:scale-[0.95] disabled:cursor-not-allowed disabled:opacity-30 ring-1 ring-inset ring-white/[0.03] shadow-sm shadow-black/10 ${FOCUS_RING}`}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                title="Önceki sayfa"
              >
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                  <path d="M6.5 2l-3 3 3 3" />
                </svg>
                Önceki
              </button>
              {/* Smart page number buttons */}
              {(() => {
                const total = Math.ceil(activeTotal / 50);
                const range: Array<number | "..."> = [];
                if (total <= 7) {
                  for (let i = 1; i <= total; i++) range.push(i);
                } else {
                  range.push(1);
                  if (page > 3) range.push("...");
                  for (let i = Math.max(2, page - 1); i <= Math.min(total - 1, page + 1); i++) range.push(i);
                  if (page < total - 2) range.push("...");
                  range.push(total);
                }
                return (
                  <div className="flex items-center gap-1">
                    {range.map((r, i) =>
                      r === "..." ? (
                        <span key={`dot-${i}`} className="px-0.5 text-xs text-slate-600">…</span>
                      ) : (
                        <button
                          key={r}
                          type="button"
                          onClick={() => setPage(r as number)}
                          className={`h-7 min-w-[1.75rem] rounded-md border px-1.5 text-xs transition-all active:scale-[0.92] ${FOCUS_RING} ${
                            page === r
                              ? "border-blue-500/40 bg-blue-500/15 font-semibold text-blue-300 ring-1 ring-blue-500/20 shadow-sm shadow-blue-500/10"
                              : "border-slate-700 bg-slate-900 text-slate-500 hover:bg-slate-800 hover:text-slate-200 ring-1 ring-inset ring-white/[0.02] shadow-sm shadow-black/10"
                          }`}
                          aria-current={page === r ? "page" : undefined}
                          aria-label={`Sayfa ${r}`}
                        >
                          {r}
                        </button>
                      )
                    )}
                  </div>
                );
              })()}
              <button
                type="button"
                className={`flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 transition-all hover:bg-slate-800 hover:text-white active:scale-[0.95] disabled:cursor-not-allowed disabled:opacity-30 ring-1 ring-inset ring-white/[0.03] shadow-sm shadow-black/10 ${FOCUS_RING}`}
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= Math.ceil(activeTotal / 50)}
                title="Sonraki sayfa"
              >
                Sonraki
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                  <path d="M3.5 2l3 3-3 3" />
                </svg>
              </button>
              <button
                type="button"
                className={`flex items-center justify-center rounded-lg border border-slate-700 bg-slate-900 p-1.5 text-xs text-slate-300 transition-all hover:bg-slate-800 hover:text-white active:scale-[0.93] disabled:cursor-not-allowed disabled:opacity-30 ring-1 ring-inset ring-white/[0.03] shadow-sm shadow-black/10 ${FOCUS_RING}`}
                onClick={() => setPage(Math.ceil(activeTotal / 50))}
                disabled={page >= Math.ceil(activeTotal / 50)}
                title="Son sayfa"
              >
                <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
                  <path d="M3 2l3 3-3 3M6 2l3 3-3 3" />
                </svg>
              </button>
              {/* Jump-to-page input */}
              {Math.ceil(activeTotal / 50) > 5 && (
                <form
                  className="ml-2 hidden items-center gap-1 sm:flex"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const val = (e.currentTarget.elements.namedItem("pg") as HTMLInputElement).value;
                    const n = Math.max(1, Math.min(Math.ceil(activeTotal / 50), parseInt(val, 10) || 1));
                    setPage(n);
                    (e.currentTarget.elements.namedItem("pg") as HTMLInputElement).value = "";
                  }}
                >
                  <span className="text-[10px] text-slate-600">Git:</span>
                  <input
                    name="pg"
                    type="number"
                    min={1}
                    max={Math.ceil(activeTotal / 50)}
                    placeholder="—"
                    className="w-12 rounded border border-slate-800 bg-slate-900/60 px-1.5 py-0.5 text-center font-mono text-[10px] text-slate-500 placeholder-slate-600 shadow-inner shadow-black/10 ring-1 ring-inset ring-white/[0.02] focus:outline-none focus:border-blue-500/40 focus:ring-blue-500/20 focus:text-slate-200 transition-colors"
                    aria-label="Sayfaya git"
                  />
                </form>
              )}
              <span className="ml-2 hidden items-center gap-1 text-[10px] text-slate-600 sm:flex">
                <kbd className="inline-flex items-center justify-center rounded border border-slate-800/70 bg-slate-900/80 px-1 py-px font-mono text-[8px] text-slate-600 shadow-sm ring-1 ring-inset ring-white/[0.03]">
                  <svg viewBox="0 0 8 8" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2 w-2"><path d="M5 1.5L2 4l3 2.5" /></svg>
                </kbd>
                <kbd className="inline-flex items-center justify-center rounded border border-slate-800/70 bg-slate-900/80 px-1 py-px font-mono text-[8px] text-slate-600 shadow-sm ring-1 ring-inset ring-white/[0.03]">
                  <svg viewBox="0 0 8 8" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2 w-2"><path d="M3 1.5L6 4l-3 2.5" /></svg>
                </kbd>
                gezin
              </span>
            </div>
            </div>
          )}
          {/* Keyboard hint strip */}
          <div className="mt-2 hidden items-center justify-center gap-4 text-[9px] text-slate-600 sm:flex">
            {([
              { k: "⌘K", d: "ara" },
              { k: "j / k", d: "seç" },
              { k: null, d: "sayfa", arrows: true },
              { k: "b", d: "toplu seç" },
              { k: "c", d: "kopyala" },
              { k: "?", d: "kısayollar" },
            ] as Array<{ k: string | null; d: string; arrows?: boolean }>).map(({ k, d, arrows }) => (
              <span key={d} className="flex items-center gap-1 hover:text-slate-500 transition-colors">
                {arrows ? (
                  <span className="flex items-center gap-0.5">
                    <kbd className="inline-flex items-center justify-center rounded border border-slate-800/70 bg-slate-900/80 px-1 py-px shadow-sm ring-1 ring-inset ring-white/[0.03]">
                      <svg viewBox="0 0 8 8" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2 w-2 text-slate-600"><path d="M5 1.5L2.5 4 5 6.5" /></svg>
                    </kbd>
                    <kbd className="inline-flex items-center justify-center rounded border border-slate-800/70 bg-slate-900/80 px-1 py-px shadow-sm ring-1 ring-inset ring-white/[0.03]">
                      <svg viewBox="0 0 8 8" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-2 w-2 text-slate-600"><path d="M3 1.5L5.5 4 3 6.5" /></svg>
                    </kbd>
                  </span>
                ) : (
                  <kbd className="rounded border border-slate-800/70 bg-slate-900/80 px-1.5 py-0.5 font-mono text-[8px] text-slate-600 shadow-sm ring-1 ring-inset ring-white/[0.03]">{k}</kbd>
                )}
                <span>{d}</span>
              </span>
            ))}
          </div>
        </main>
      </div>

      {/* Back-to-top floating button — fixed bottom-right */}
      {cardScrolled && (
        <button
          type="button"
          onClick={() => cardScrollRef.current?.scrollTo({ top: 0, behavior: "smooth" })}
          className={`group/top fixed bottom-6 right-6 z-40 flex h-9 w-9 items-center justify-center rounded-full border border-slate-700/70 bg-slate-900/95 text-slate-500 shadow-2xl shadow-black/60 backdrop-blur-md transition-all hover:border-blue-500/40 hover:bg-slate-800 hover:text-blue-300 hover:shadow-blue-500/15 hover:scale-110 active:scale-95 ring-1 ring-inset ring-white/[0.04] animate-fade-in ${FOCUS_RING}`}
          title="Başa dön"
          aria-label="Başa dön"
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5 transition-transform group-hover/top:-translate-y-0.5">
            <path d="M8 13V3M3 8l5-5 5 5" />
          </svg>
        </button>
      )}

      {/* ── Floating batch action bar ── */}
      {batchMode && selectedBatchIds.size > 0 && (
        <div className="pointer-events-auto fixed bottom-6 left-1/2 z-40 -translate-x-1/2 animate-slide-up">
          <div className="flex items-center gap-2 rounded-full border border-blue-500/25 bg-slate-900/97 px-4 py-2 shadow-2xl shadow-blue-500/[0.12] ring-1 ring-blue-500/[0.08] backdrop-blur-md">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-500/20 text-[11px] font-bold text-blue-300 ring-1 ring-blue-500/30 shadow-sm shadow-blue-500/20">
              {selectedBatchIds.size}
            </span>
            <span className="text-[11px] text-slate-400">seçili</span>
            <span className="text-slate-600">·</span>
            <button
              type="button"
              onClick={() => {
                const lines = activeActions
                  .filter((a) => selectedBatchIds.has(a.id))
                  .flatMap((a) => {
                    const cSt = getStepType(a.description ?? "");
                    const cKw = cSt === "given" ? "Given" : cSt === "when" ? "When" : cSt === "then" ? "Then" : "And";
                    return [...(a.aliases?.tr?.map((al) => `${cKw} ${al}`) ?? []), ...(a.aliases?.en?.map((al) => `${cKw} ${al}`) ?? [])];
                  });
                navigator.clipboard.writeText(lines.join("\n")).then(() => {
                  dispatchToast(`${selectedBatchIds.size} adım kopyalandı`);
                  setBatchMode(false); setSelectedBatchIds(new Set());
                });
              }}
              className={`flex items-center gap-1 rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-[11px] text-blue-300 transition-all active:scale-[0.96] hover:bg-blue-500/20 ring-1 ring-inset ring-blue-500/[0.06] ${FOCUS_RING}`}
            >
              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="h-2.5 w-2.5">
                <rect x="1" y="2" width="7" height="7" rx="1" />
                <path d="M3 1h6v7" />
              </svg>
              Gherkin
            </button>
            <button
              type="button"
              onClick={() => {
                setFavorites((prev) => {
                  const next = new Set(prev);
                  let added = 0;
                  for (const id of selectedBatchIds) { if (!next.has(id)) { next.add(id); added++; } }
                  try { localStorage.setItem("dsl_favorites", JSON.stringify([...next])); } catch { /* */ }
                  dispatchToast(`${added > 0 ? added : selectedBatchIds.size} cümlecik favorilere eklendi`, "favorite");
                  return next;
                });
                setBatchMode(false); setSelectedBatchIds(new Set());
              }}
              className={`flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-[11px] text-amber-400 transition-all active:scale-[0.96] hover:bg-amber-500/20 ring-1 ring-inset ring-amber-500/[0.06] ${FOCUS_RING}`}
            >
              <svg viewBox="0 0 10 10" fill="currentColor" className="h-2.5 w-2.5">
                <path d="M5 1l1.2 2.5L9 3.8l-2 2 .5 2.7L5 7.2 2.5 8.5 3 5.8 1 3.8l2.8-.3L5 1z" />
              </svg>
              Favori
            </button>
            <button
              type="button"
              onClick={() => { setBatchMode(false); setSelectedBatchIds(new Set()); }}
              className={`flex items-center justify-center rounded-full border border-slate-700 bg-slate-800 px-2 py-1 text-slate-400 transition-all active:scale-90 hover:bg-slate-700 hover:text-slate-200 ring-1 ring-inset ring-white/[0.03] ${FOCUS_RING}`}
              title="Toplu seçimi kapat"
            >
              <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-2.5 w-2.5">
                <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {selected && (
        <ActionDetail
          action={selected}
          onClose={() => setSelected(null)}
          hasPrev={selectedIdx > 0}
          hasNext={selectedIdx < activeActions.length - 1 && selectedIdx >= 0}
          onPrev={() => selectedIdx > 0 && openAction(activeActions[selectedIdx - 1])}
          onNext={() => selectedIdx >= 0 && selectedIdx < activeActions.length - 1 && openAction(activeActions[selectedIdx + 1])}
          position={selectedIdx >= 0 ? { current: selectedIdx + 1, total: activeActions.length } : undefined}
          onCategoryClick={(cat) => { setCategory(cat); setSelected(null); setPage(1); }}
          isFavorite={favorites.has(selected.id)}
          onToggleFavorite={toggleFavorite}
          relatedActions={relatedActions}
          onOpenRelated={openAction}
        />
      )}
      {showShortcuts && <KeyboardShortcutsModal onClose={() => setShowShortcuts(false)} />}
      <ToastContainer />
    </div>
  );
}
