"use client";

import { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

type RestartResponse = {
  ok: boolean;
  message: string;
  mode?: "restart" | "up";
  services?: string[];
};

type Status = "idle" | "loading" | "success" | "error";

export function ServiceRestartButton() {
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (status === "idle" || status === "loading") return;
    const timer = window.setTimeout(() => {
      setStatus("idle");
      setMessage("");
    }, 7000);
    return () => window.clearTimeout(timer);
  }, [status]);

  const buttonLabel = useMemo(() => {
    if (status === "loading") return "Yeniden Başlatılıyor";
    return "Servisleri Yeniden Başlat";
  }, [status]);

  async function handleRestart() {
    if (status === "loading") return;

    const ok = window.confirm(
      "PostgreSQL, Redis, AI Gateway, Engine, Backend ve Worker yeniden başlatılacak. Devam etmek istiyor musun?"
    );
    if (!ok) return;

    setStatus("loading");
    setMessage("Servisler yeniden başlatılıyor...");

    try {
      const res = await fetch("/api/dev/restart-services", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      const data = (await res.json()) as RestartResponse & { error?: string };
      if (!res.ok) {
        throw new Error(data.error || data.message || "Servisler yeniden başlatılamadı.");
      }

      setStatus("success");
      setMessage(data.message || "Servisler yeniden başlatıldı.");
    } catch (error) {
      setStatus("error");
      setMessage(
        error instanceof Error
          ? error.message
          : "Beklenmeyen bir hata oluştu."
      );
    }
  }

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      onClick={handleRestart}
      disabled={status === "loading"}
      title={message || buttonLabel}
      aria-label={buttonLabel}
      data-testid="header-btn-restart-services"
      className={cn(
        "rounded-lg",
        status === "success"
          ? "text-emerald-400 hover:bg-emerald-500/10"
          : status === "error"
          ? "text-red-400 hover:bg-red-500/10"
          : "text-amber-400/70 hover:bg-amber-500/10 hover:text-amber-300"
      )}
    >
      {status === "loading" ? (
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-6.219-8.56"/>
        </svg>
      ) : status === "success" ? (
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
        </svg>
      ) : status === "error" ? (
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
        </svg>
      ) : (
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v6h6M20 20v-6h-6"/>
          <path strokeLinecap="round" strokeLinejoin="round" d="M20 9a8 8 0 00-13.657-3.657L4 7m16 10-2.343 2.343A8 8 0 014 15"/>
        </svg>
      )}
    </Button>
  );
}
