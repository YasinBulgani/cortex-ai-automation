"use client";

import { SectionCard } from "@/components/nexus/SectionCard";
import type { PlaywrightSession } from "@/lib/hooks/use-playwright-mcp";

// ── Props ────────────────────────────────────────────────────────────

export interface SessionInfoCardProps {
  session: PlaywrightSession;
  screenshotBase64?: string;
  screenshotFormat?: string;
  screenshotLoading?: boolean;
  closePending?: boolean;
  onClose: () => void;
  onRefreshScreenshot: () => void;
}

// ── Sub-components ───────────────────────────────────────────────────

function Spinner({ className = "" }: { className?: string }) {
  return (
    <div
      className={`h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-emerald-400 ${className}`}
    />
  );
}

// ── Component ────────────────────────────────────────────────────────

export function SessionInfoCard({
  session,
  screenshotBase64,
  screenshotFormat,
  screenshotLoading,
  closePending,
  onClose,
  onRefreshScreenshot,
}: SessionInfoCardProps) {
  return (
    <div className="space-y-4">
      {/* Session info */}
      <SectionCard
        title="Oturum Bilgisi"
        icon={
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          </svg>
        }
        right={
          <button
            type="button"
            onClick={onClose}
            disabled={closePending}
            className="rounded border border-red-500/30 bg-red-500/10 px-2 py-1 text-xs text-red-400 hover:bg-red-500/20 transition-colors"
          >
            {closePending ? "Kapatiliyor..." : "Oturumu Kapat"}
          </button>
        }
      >
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-slate-500">ID:</span>{" "}
            <span className="text-slate-300 font-mono text-xs">
              {session.session_id.slice(0, 12)}...
            </span>
          </div>
          <div>
            <span className="text-slate-500">Durum:</span>{" "}
            <span className={session.status === "active" ? "text-emerald-400" : "text-red-400"}>
              {session.status === "active" ? "Aktif" : "Kapalı"}
            </span>
          </div>
          <div>
            <span className="text-slate-500">URL:</span>{" "}
            <span className="text-blue-400 truncate">{session.url ?? "—"}</span>
          </div>
          <div>
            <span className="text-slate-500">Baslik:</span>{" "}
            <span className="text-slate-300">{session.title ?? "—"}</span>
          </div>
          <div className="col-span-2">
            <span className="text-slate-500">Olusturulma:</span>{" "}
            <span className="text-slate-300">
              {new Date(session.created_at).toLocaleString("tr-TR")}
            </span>
          </div>
        </div>
      </SectionCard>

      {/* Screenshot */}
      <SectionCard
        title="Sayfa Görüntüsu"
        icon={
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
        }
        right={
          <button
            type="button"
            onClick={onRefreshScreenshot}
            className="flex items-center gap-1 rounded border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700 transition-colors"
          >
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Yenile
          </button>
        }
      >
        {screenshotLoading ? (
          <div className="flex items-center justify-center py-12">
            <Spinner className="h-6 w-6" />
          </div>
        ) : screenshotBase64 ? (
          <div className="overflow-hidden rounded-lg border border-slate-700">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`data:image/${screenshotFormat ?? "png"};base64,${screenshotBase64}`}
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
