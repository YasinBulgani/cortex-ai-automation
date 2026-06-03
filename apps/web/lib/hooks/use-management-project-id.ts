"use client";

import { useEffect, useState } from "react";
import { useEnsureManagementProject } from "@/lib/hooks/use-management";

const LS_PREFIX = "neurex:mgmt_pid:";

function lsKey(projectId: string) { return `${LS_PREFIX}${projectId}`; }

/**
 * ADR-0012 backend-first pattern implementasyonu.
 *
 * Phase-1 (anında): localStorage'dan cached mpid döner — UI beklemeden render eder.
 * Phase-2 (async):  Backend'den gerçek mpid alınır, cache güncellenir ve state set edilir.
 *
 * Kullanım:
 *   const mpid = useManagementProjectId(projectId);
 *   const { data } = useManagementPlans(mpid);
 */
export function useManagementProjectId(projectId: string | undefined): string | undefined {
  const ensure = useEnsureManagementProject(projectId);

  const [mpid, setMpid] = useState<string | undefined>(() => {
    // Phase-1: localStorage cache'den anında yükle
    if (!projectId || typeof window === "undefined") return projectId;
    return localStorage.getItem(lsKey(projectId)) ?? projectId;
  });

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;

    ensure
      .mutateAsync()
      .then((p) => {
        if (cancelled) return;
        // Phase-2: backend yanıtı geldi — cache güncelle ve state set et
        try { localStorage.setItem(lsKey(projectId), p.id); } catch { /* storage dolu */ }
        setMpid(p.id);
      })
      .catch(() => {
        if (cancelled) return;
        // Backend başarısız — localStorage'daki veya projectId fallback'i geçerli kalır
        setMpid(prev => prev ?? projectId);
      });

    return () => { cancelled = true; };
    // ensure ref değişirse loop oluşur — intentionally only projectId in deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  return mpid || projectId;
}
