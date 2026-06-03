"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import {
  getModuleFromPathname,
  hasServiceChange,
  type ModuleConfig,
} from "./module-service-map";
import { ModuleTransitionDialog } from "./ModuleTransitionDialog";
import { ServiceLoadingScreen } from "./ServiceLoadingScreen";

type Phase = "idle" | "confirming" | "switching";

// Only active in dev (or when ENABLE_DEV_SERVICE_CONTROL is set)
const ENABLED = process.env.NODE_ENV !== "production";

export function ModuleOrchestratorProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [phase, setPhase] = useState<Phase>("idle");
  const [fromModule, setFromModule] = useState<ModuleConfig | null>(null);
  const [toModule, setToModule] = useState<ModuleConfig | null>(null);

  // Tracks the last "confirmed" module (not just the current URL)
  const activeModuleRef = useRef<ModuleConfig>(getModuleFromPathname(pathname ?? ""));

  useEffect(() => {
    if (!ENABLED || !pathname) return;

    const next = getModuleFromPathname(pathname);
    const prev = activeModuleRef.current;

    // Same module segment → nothing to do
    if (next.key === prev.key) return;

    // No service difference → just advance silently
    if (!hasServiceChange(prev, next)) {
      activeModuleRef.current = next;
      return;
    }

    setFromModule(prev);
    setToModule(next);
    setPhase("confirming");
  }, [pathname]);

  const handleConfirm = useCallback(() => {
    setPhase("switching");
  }, []);

  const handleSkip = useCallback(() => {
    // User keeps all services running — just advance the tracked module
    setToModule((to) => {
      if (to) activeModuleRef.current = to;
      return to;
    });
    setPhase("idle");
  }, []);

  const handleComplete = useCallback(() => {
    setToModule((to) => {
      if (to) activeModuleRef.current = to;
      return to;
    });
    setFromModule(null);
    setToModule(null);
    setPhase("idle");
  }, []);

  if (!ENABLED) return <>{children}</>;

  return (
    <>
      {children}

      {phase === "confirming" && fromModule && toModule && (
        <ModuleTransitionDialog
          fromModule={fromModule}
          toModule={toModule}
          onConfirm={handleConfirm}
          onSkip={handleSkip}
        />
      )}

      {phase === "switching" && fromModule && toModule && (
        <ServiceLoadingScreen
          fromModule={fromModule}
          toModule={toModule}
          onComplete={handleComplete}
        />
      )}
    </>
  );
}
