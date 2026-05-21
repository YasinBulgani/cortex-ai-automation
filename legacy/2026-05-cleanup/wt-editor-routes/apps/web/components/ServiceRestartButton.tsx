"use client";

import { useEffect, useMemo, useState } from "react";
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

  const statusColor =
    status === "success"
      ? "text-emerald-400"
      : status === "error"
        ? "text-red-400"
        : "text-slate-500";

  return (
    <div className="flex items-center gap-2">
      <Button
        type="button"
        variant="secondary"
        size="sm"
        onClick={handleRestart}
        disabled={status === "loading"}
        className="border-amber-600/40 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20 hover:text-amber-100"
        data-testid="header-btn-restart-services"
      >
        <span className="mr-1.5 inline-flex h-3.5 w-3.5 items-center justify-center">
          {status === "loading" ? (
            <svg
              className="h-3.5 w-3.5 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 12a9 9 0 11-6.219-8.56"
              />
            </svg>
          ) : (
            <svg
              className="h-3.5 w-3.5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 4v6h6M20 20v-6h-6"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M20 9a8 8 0 00-13.657-3.657L4 7m16 10-2.343 2.343A8 8 0 014 15"
              />
            </svg>
          )}
        </span>
        <span className="hidden md:inline">{buttonLabel}</span>
        <span className="md:hidden">Yeniden Başlat</span>
      </Button>

      {message && (
        <span
          className={`hidden max-w-[280px] truncate text-xs xl:inline ${statusColor}`}
          data-testid="header-restart-services-status"
          title={message}
        >
          {message}
        </span>
      )}
    </div>
  );
}
