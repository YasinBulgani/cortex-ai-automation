"use client";

/**
 * useProject — Aktif proje context'i
 *
 * - Seçili proje localStorage'a yazılır (sayfa yenilemede korunur)
 * - useProject() hook'u ile her bileşenden erişilebilir
 * - setProject() ile proje değiştirilir (router navigate edilmez — çağıran yapar)
 *
 * Kullanım:
 *   const { project, setProject } = useProject();
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";

export interface Project {
  id: string;
  name: string;
  target_url?: string;
  llm_provider?: string;
  llm_model?: string;
}

interface ProjectContextValue {
  project: Project | null;
  setProject: (p: Project | null) => void;
  projectId: string | null;
}

const LS_KEY = "bgts_active_project";

const ProjectContext = createContext<ProjectContextValue>({
  project: null,
  setProject: () => {},
  projectId: null,
});

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [project, setProjectState] = useState<Project | null>(null);

  // localStorage'dan yükle (hydration sonrası)
  useEffect(() => {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) setProjectState(JSON.parse(raw));
    } catch {
      // bozuk veri → yok say
    }
  }, []);

  const setProject = useCallback((p: Project | null) => {
    setProjectState(p);
    try {
      if (p) localStorage.setItem(LS_KEY, JSON.stringify(p));
      else localStorage.removeItem(LS_KEY);
    } catch {
      // Private browsing, storage dolu vb.
    }
  }, []);

  return (
    <ProjectContext.Provider
      value={{ project, setProject, projectId: project?.id ?? null }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  return useContext(ProjectContext);
}
