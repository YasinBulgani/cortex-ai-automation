"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { useProjects } from "@/lib/hooks";
import { ToastProvider, useToast } from "@/components/ui/toast";
import { ConfirmProvider } from "@/components/ui/confirm-dialog";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { CommandPalette } from "@/components/CommandPalette";
import { ProjectProvider, useProject } from "@/lib/useProject";

function DashboardInner({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: projects = [], isLoading: projectsLoading, isPending: projectsPending, error: projectsQueryError } = useProjects();
  const [dismissed, setDismissed] = useState(false);
  const { toast } = useToast();

  const projectsError = projectsQueryError?.message ?? null;

  // Hata geldiginde toast goster (bir kez)
  useEffect(() => {
    if (projectsError) {
      toast("Projeler yuklenemedi. Baglantiyi veya oturumu kontrol edin.", "error");
    }
  }, [projectsError, toast]);

  const projectId = pathname?.match(/^\/p\/([^/]+)/)?.[1];
  const { setProject } = useProject();

  // URL'deki proje degisince context'i guncelle (localStorage'a yazar)
  useEffect(() => {
    if (!projectId) return;
    const found = projects.find((p) => p.id === projectId);
    setProject(found ?? { id: projectId, name: `Proje ${projectId}` });
  }, [projectId, projects, setProject]);

  // Onboarding yönlendirmesi: proje yoksa ve daha önce tamamlanmamışsa
  useEffect(() => {
    if (projectsLoading || projectsPending) return;
    if (pathname?.startsWith("/onboarding")) return;
    const alreadyOnboarded = typeof window !== "undefined"
      ? localStorage.getItem("onboarded") === "true"
      : true;
    if (!alreadyOnboarded && projects.length === 0) {
      router.replace("/onboarding");
    }
  }, [projectsLoading, projectsPending, projects, pathname, router]);

  const topBanner =
    projectsError && !dismissed ? (
      <div
        className="shrink-0 border-b border-red-200 bg-red-50 px-6 py-2.5 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
        role="alert"
        data-testid="dashboard-banner-projects-error"
      >
        <span className="font-medium">Projeler yuklenemedi.</span>{" "}
        <span className="opacity-90">{projectsError}</span>
        <button
          type="button"
          className="ml-3 underline underline-offset-2 hover:opacity-80"
          onClick={() => setDismissed(true)}
          data-testid="dashboard-banner-projects-error-dismiss"
        >
          Kapat
        </button>
      </div>
    ) : null;

  return (
    <AppShell projects={projects} projectId={projectId} topBanner={topBanner}>
      {children}
    </AppShell>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProjectProvider>
      <ToastProvider>
        <ConfirmProvider>
          <ErrorBoundary>
            <DashboardInner>{children}</DashboardInner>
            <CommandPalette />
          </ErrorBoundary>
        </ConfirmProvider>
      </ToastProvider>
    </ProjectProvider>
  );
}
