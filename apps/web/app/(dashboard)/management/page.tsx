"use client";

import Link from "next/link";
import { useMemo } from "react";
import { FolderKanban, Plus, Search, TestTube2 } from "lucide-react";
import { useProjects } from "@/lib/hooks/use-projects";

const DEFAULT_PROJECT_ID = "00000000-0000-0000-0000-000000000001";

export default function ManagementLandingPage() {
  const projects = useProjects();
  const sortedProjects = useMemo(
    () =>
      [...(projects.data ?? [])].sort((a, b) =>
        String(b.updated_at ?? b.created_at ?? "").localeCompare(String(a.updated_at ?? a.created_at ?? "")),
      ),
    [projects.data],
  );
  const primaryProject = sortedProjects[0];
  const primaryHref = primaryProject
    ? `/p/${primaryProject.id}/management`
    : `/p/${DEFAULT_PROJECT_ID}/management`;

  return (
    <main className="min-h-full bg-slate-950 px-6 py-6 text-slate-100">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <section className="border-b border-slate-800 pb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-300">
            Test Yönetimi
          </p>
          <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-normal text-white">
                Management çalışma alanı
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
                Gereksinimden test havuzuna, koşumdan release raporuna kadar manuel test operasyonunu proje bazında yönetin.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href={primaryHref}
                className="inline-flex items-center gap-2 rounded-md bg-teal-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-teal-400"
              >
                <FolderKanban className="h-4 w-4" />
                Management Aç
              </Link>
              <Link
                href="/new-project"
                className="inline-flex items-center gap-2 rounded-md border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-900"
              >
                <Plus className="h-4 w-4" />
                Yeni Proje
              </Link>
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          {[
            ["Requirements", "Kapsamı ve kabul kriterlerini netleştir."],
            ["Test Repository", "Case, öncelik, owner ve traceability bilgisini tek yerde tut."],
            ["Runs & Reports", "Koşumları yönet, blocker ve release readiness kararını çıkar."],
          ].map(([title, text]) => (
            <div key={title} className="rounded-md border border-slate-800 bg-slate-900/60 p-4">
              <p className="text-sm font-semibold text-white">{title}</p>
              <p className="mt-2 text-sm leading-6 text-slate-400">{text}</p>
            </div>
          ))}
        </section>

        <section className="rounded-md border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold text-white">Projeler</h2>
              <p className="mt-1 text-xs text-slate-500">
                Management proje bağlamında çalışır. Bir proje seçerek başlayın.
              </p>
            </div>
            <Search className="h-4 w-4 text-slate-500" />
          </div>

          {projects.isLoading ? (
            <div className="p-6 text-sm text-slate-400">Projeler yükleniyor...</div>
          ) : sortedProjects.length > 0 ? (
            <div className="divide-y divide-slate-800">
              {sortedProjects.slice(0, 8).map((project) => (
                <Link
                  key={project.id}
                  href={`/p/${project.id}/management`}
                  className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-slate-900"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-white">{project.name}</p>
                    <p className="mt-1 truncate text-xs text-slate-500">{project.description || project.id}</p>
                  </div>
                  <span className="shrink-0 rounded-full border border-teal-500/30 px-2 py-1 text-xs font-semibold text-teal-200">
                    Aç
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-start gap-4 p-6">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-slate-800 text-teal-300">
                <TestTube2 className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">Henüz proje yok</p>
                <p className="mt-1 max-w-xl text-sm leading-6 text-slate-400">
                  Yeni proje oluşturabilir veya geliştirme/demo workspace'ini açıp Management akışını deneyebilirsiniz.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link href="/new-project" className="rounded-md bg-teal-500 px-3 py-2 text-sm font-semibold text-slate-950 hover:bg-teal-400">
                  Proje Oluştur
                </Link>
                <Link href={`/p/${DEFAULT_PROJECT_ID}/management`} className="rounded-md border border-slate-700 px-3 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-900">
                  Demo Workspace Aç
                </Link>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
