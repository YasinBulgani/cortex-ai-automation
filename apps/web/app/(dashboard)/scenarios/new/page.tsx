"use client";

/**
 * Top-level /scenarios/new entry — same redirect pattern as /scenarios/page.tsx
 * but lands on the project's "new scenario" route.
 *
 * Common trigger: user clicks "Senaryo Yaz" / "Yeni Senaryo" from a place
 * that doesn't carry project context (command palette without an active
 * project, sidebar shortcut, doc link in markdown, etc.) — without this
 * page they'd see a Next.js 404 even though the canonical
 * /p/<projectId>/scenarios/new route exists.
 *
 * Falls back to /task-drafts (the dedicated "no-project scenario drafts"
 * surface) rather than /portfolio, because the user's intent is "I want to
 * write a scenario right now" — task-drafts is the closest thing without
 * forcing them to pick a project first.
 *
 * Implementation notes:
 *  - `bgts_active_project` localStorage holds a JSON Project, not a bare id
 *    (see [useProject.tsx]). We must JSON.parse and pick .id.
 *  - `useSearchParams()` requires a Suspense boundary in Next 14 client
 *    pages, otherwise `next build` throws. We split the search-param
 *    consumer into a child component wrapped in <Suspense>.
 */

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const LS_KEY = "bgts_active_project";

function readActiveProjectId(): string | null {
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { id?: unknown } | null;
    const id = parsed && typeof parsed.id === "string" ? parsed.id.trim() : "";
    return id || null;
  } catch {
    return null;
  }
}

function NewScenarioRedirector() {
  const router = useRouter();
  const sp = useSearchParams();
  const qs = sp?.toString() ?? "";
  const suffix = qs ? `?${qs}` : "";

  useEffect(() => {
    const id = readActiveProjectId();
    const target = id
      ? `/p/${encodeURIComponent(id)}/scenarios/new${suffix}`
      : `/task-drafts${suffix}`;
    router.replace(target);
  }, [router, suffix]);

  return null;
}

function Splash() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center text-slate-400">
      <div className="text-center">
        <div className="mb-3 text-2xl">✍️</div>
        <p className="text-sm">Yeni senaryo sayfasına yönlendiriliyorsunuz…</p>
        <p className="mt-1 text-xs text-slate-600">
          Aktif proje yoksa "Senaryo Oluşturucu"ya düşersiniz.
        </p>
      </div>
    </div>
  );
}

export default function NewScenarioRedirectPage() {
  return (
    <Suspense fallback={<Splash />}>
      <NewScenarioRedirector />
      <Splash />
    </Suspense>
  );
}
