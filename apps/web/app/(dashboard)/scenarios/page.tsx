"use client";

/**
 * Top-level /scenarios entry — fixes the 404 you hit when a "Senaryo Yaz"
 * link is rendered outside a project context (sidebar shortcut, command
 * palette fallback, doc link, etc.). The canonical route is
 * /p/<projectId>/scenarios — so this page is a thin redirector:
 *
 *   1. Read the last-active project from localStorage. The canonical
 *      writer ([useProject.tsx]) stores a JSON-serialized Project object
 *      under "bgts_active_project" — we must JSON.parse and pull .id,
 *      NOT treat the value as a plain string.
 *   2. If we have a valid id → router.replace("/p/<id>/scenarios")
 *   3. Otherwise → router.replace("/portfolio") so the user can pick one.
 *
 * The redirect runs client-side because localStorage isn't available in
 * server components. While it resolves we render a tiny "Yönlendiriliyor…"
 * splash so the user sees something instead of a flash of empty page.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";

const LS_KEY = "bgts_active_project";

function readActiveProjectId(): string | null {
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { id?: unknown } | null;
    const id = parsed && typeof parsed.id === "string" ? parsed.id.trim() : "";
    return id || null;
  } catch {
    // Malformed JSON or localStorage blocked (private mode, etc.)
    return null;
  }
}

export default function ScenariosRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    const id = readActiveProjectId();
    router.replace(id ? `/p/${encodeURIComponent(id)}/scenarios` : "/portfolio");
  }, [router]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center text-slate-400">
      <div className="text-center">
        <div className="mb-3 text-2xl">📝</div>
        <p className="text-sm">Senaryolara yönlendiriliyorsunuz…</p>
        <p className="mt-1 text-xs text-slate-600">
          Proje seçili değilse Portfolio sayfasından bir proje seçin.
        </p>
      </div>
    </div>
  );
}
