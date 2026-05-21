"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useProject } from "@/lib/useProject";
import { useProjects } from "@/lib/hooks/use-projects";

/**
 * Sidebar'ın alt kısmında oturan kompakt proje seçici.
 * - Aktif projeyi gösterir (yeşil canlı nokta + isim)
 * - Dropdown ile değiştirir; alt yolu korur (`/p/A/runs` → `/p/B/runs`)
 * - "Yeni" linki /new-project'e gider
 */
export function SidebarProjectSwitcher() {
  const { project, projectId, setProject } = useProject();
  const { data: projects } = useProjects();
  const pathname = usePathname();
  const router = useRouter();

  function deriveSubPath(currentPath: string | null, fromId: string | undefined): string {
    if (!currentPath || !fromId) return "";
    const prefix = `/p/${fromId}`;
    if (currentPath === prefix) return "";
    if (currentPath.startsWith(`${prefix}/`)) return currentPath.slice(prefix.length);
    return "";
  }

  function handleChange(id: string) {
    if (!id || id === projectId) return;
    const selected = projects?.find((p) => p.id === id) ?? null;
    setProject(selected);
    const subPath = deriveSubPath(pathname, projectId ?? undefined);
    router.push(`/p/${id}${subPath}`);
  }

  return (
    <div
      className="border-t border-gray-100 dark:border-slate-700 px-3 py-3"
      data-testid="sidebar-project-switcher"
    >
      <div className="flex items-center gap-2 mb-1.5 px-1">
        <span
          className={`h-2 w-2 shrink-0 rounded-full ${
            projectId ? "bg-emerald-400 animate-pulse" : "bg-slate-600"
          }`}
        />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Aktif Proje
        </span>
      </div>

      <div className="flex items-center gap-1.5">
        <select
          value={projectId ?? ""}
          onChange={(e) => handleChange(e.target.value)}
          className="min-w-0 flex-1 h-8 rounded-lg border border-slate-700 bg-slate-900 px-2 text-xs text-white truncate focus:outline-none focus:border-emerald-500/50"
          data-testid="sidebar-select-project"
          title={project?.name ?? "Proje seç"}
        >
          {!projectId && <option value="">Proje seç…</option>}
          {projects?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <Link
          href="/new-project"
          className="shrink-0 flex h-8 w-8 items-center justify-center rounded-lg border border-dashed border-slate-700 text-slate-400 hover:border-emerald-500/40 hover:text-emerald-300 transition-colors"
          title="Yeni proje oluştur"
          data-testid="sidebar-btn-new-project"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
        </Link>
      </div>
    </div>
  );
}
