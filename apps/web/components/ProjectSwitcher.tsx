"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useProject } from "@/lib/useProject";

type Project = { id: string; name: string };

/**
 * Proje değiştirme kontrolü.
 *
 * Aynı alt sayfa bağlamını korur: `/p/A/runs` üzerindeyken B projesi seçilirse
 * `/p/B/runs` adresine gider (sayfa yoksa graceful fallback ile `/p/B`'ye düşer).
 */
export function ProjectSwitcher({
  projects,
  currentId,
}: {
  projects: Project[];
  currentId?: string;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { setProject } = useProject();

  function deriveSubPath(currentPath: string | null, fromId: string | undefined): string {
    if (!currentPath || !fromId) return "";
    // `/p/{fromId}/...` ise `/...` kısmını çıkar, yoksa boş
    const prefix = `/p/${fromId}`;
    if (currentPath === prefix) return "";
    if (currentPath.startsWith(`${prefix}/`)) return currentPath.slice(prefix.length);
    return "";
  }

  function handleChange(id: string) {
    if (!id || id === currentId) return;
    const selected = projects.find((p) => p.id === id) ?? null;
    setProject(selected);
    const subPath = deriveSubPath(pathname, currentId);
    router.push(`/p/${id}${subPath}`);
  }

  return (
    <div className="flex items-center gap-2" data-testid="header-project-switcher">
      <span className="text-xs text-slate-400 hidden sm:inline">Proje</span>
      <select
        className="h-8 max-w-[180px] rounded border border-slate-800 bg-slate-900 px-2 text-sm"
        value={currentId || ""}
        data-testid="header-select-project"
        onChange={(e) => handleChange(e.target.value)}
      >
        <option value="">Seçin…</option>
        {projects.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
      <Link
        href="/new-project"
        className="flex h-8 items-center gap-1 rounded border border-dashed border-slate-800 px-2 text-xs text-slate-400 hover:border-blue-500 hover:text-blue-400 transition-colors"
        title="Yeni proje oluştur"
        data-testid="header-btn-new-project"
      >
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        <span className="hidden sm:inline">Yeni</span>
      </Link>
    </div>
  );
}
