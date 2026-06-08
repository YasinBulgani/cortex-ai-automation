"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import { useProjects } from "@/lib/hooks";
import { ToastProvider, useToast } from "@/components/ui/toast";
import { ConfirmProvider } from "@/components/ui/confirm-dialog";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { CommandPalette } from "@/components/CommandPalette";
import { HelpWidget } from "@/components/HelpWidget";
import { PageFeedbackWidget } from "@/components/PageFeedbackWidget";
import { WebVitalsReporter } from "@/components/WebVitalsReporter";
import { ProjectProvider, useProject } from "@/lib/useProject";
import { ModuleOrchestratorProvider } from "./_components/module-orchestrator/ModuleOrchestratorProvider";

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
      toast("Projeler yüklenemedi. Bağlantıyi veya oturumu kontrol edin.", "error");
    }
  }, [projectsError, toast]);

  // Oturum sona erince kullanıcıyı bilgilendir ve login'e yönlendir
  useEffect(() => {
    function handleSessionExpired() {
      toast("Oturum süreniz doldu. Lütfen tekrar giriş yapın.", "error");
      setTimeout(() => router.replace("/login"), 2000);
    }
    window.addEventListener("neurex:session-expired", handleSessionExpired);
    return () => window.removeEventListener("neurex:session-expired", handleSessionExpired);
  }, [toast, router]);

  const projectId = pathname?.match(/^\/p\/([^/]+)/)?.[1];
  const { project: activeProject, setProject } = useProject();
  const touchedRef = useRef<string | null>(null);

  // URL'deki proje değişince context'i guncelle (localStorage'a yazar).
  // Guard: context zaten bu projectId'deyse tekrar set etme — aksi halde
  // `found` bulunamayan (kullanıcıya ait olmayan) projelerde her render yeni
  // {id,name} objesi set edilip sonsuz render döngüsü (Maximum update depth) oluşur.
  useEffect(() => {
    if (!projectId) return;
    if (activeProject?.id === projectId) return;
    const found = projects.find((p) => p.id === projectId);
    setProject(found ?? { id: projectId, name: `Proje ${projectId}` });
  }, [projectId, projects, setProject, activeProject?.id]);

  // Ana sayfa "Son Açılan Proje" kartı için: proje değişince bir kez touch et.
  // Idempotent ama tekrarlanan renderlarda ağı boşa yormamak için ref ile dedupe.
  useEffect(() => {
    if (!projectId) return;
    if (touchedRef.current === projectId) return;
    touchedRef.current = projectId;
    apiFetch(`/api/v1/tspm/projects/${projectId}/touch`, { method: "POST" }).catch(() => {
      // touch başarısızlığı kullanıcı akışını etkilemez — sessiz yut.
    });
  }, [projectId]);

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
            <ModuleOrchestratorProvider>
              <DashboardInner>{children}</DashboardInner>
              <CommandPalette />
              <HelpWidget />
              <PageFeedbackWidget />
              <WebVitalsReporter />
            </ModuleOrchestratorProvider>
          </ErrorBoundary>
        </ConfirmProvider>
      </ToastProvider>
    </ProjectProvider>
  );
}
