"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/tooltip";

type AiHealth = {
  status: string;
  providers: Record<string, boolean>;
};

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  vllm:      "vLLM",
  groq:      "Groq",
  gemini:    "Gemini",
  ollama:    "Ollama",
  g4f:       "g4f",
};

const REFRESH_INTERVAL = 30_000; // 30s

/**
 * Header'da küçük AI durum chip'i — aktif sağlayıcı sayısı + sağlık.
 *
 * Sağlıklı: yeşil dot + ilk aktif sağlayıcı adı
 * Sorunlu:  sarı/kırmızı dot + durum
 *
 * Tooltip hover: tüm sağlayıcıların durumunu listeler.
 */
export function AiStatusChip() {
  const [health, setHealth] = useState<AiHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const fetchHealth = () => {
      fetch("/api/ai/health")
        .then(r => r.ok ? r.json() : null)
        .then((data: AiHealth | null) => {
          if (!cancelled) {
            setHealth(data);
            setLoading(false);
          }
        })
        .catch(() => {
          if (!cancelled) setLoading(false);
        });
    };
    fetchHealth();
    const t = setInterval(fetchHealth, REFRESH_INTERVAL);
    return () => { cancelled = true; clearInterval(t); };
  }, []);

  if (loading) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-subtle">
        <span className="h-1.5 w-1.5 rounded-full bg-fg-subtle animate-pulse" />
        AI ...
      </span>
    );
  }

  const active = health ? Object.entries(health.providers).filter(([, v]) => v).map(([k]) => k) : [];
  const activeCount = active.length;
  const totalCount = health ? Object.keys(health.providers).length : 0;

  const tone =
    !health        ? "danger" :
    activeCount === 0 ? "danger" :
    activeCount < 2 ? "warning" : "success";

  const toneClasses = {
    success: "border-success/30 bg-success-subtle text-success",
    warning: "border-warning/30 bg-warning-subtle text-warning",
    danger:  "border-danger/30 bg-danger-subtle text-danger",
  };

  const dotClasses = {
    success: "bg-success animate-pulse",
    warning: "bg-warning",
    danger:  "bg-danger",
  };

  const primary = active[0] ?? "Pasif";
  const label = activeCount > 1 ? `${PROVIDER_LABELS[primary] ?? primary} +${activeCount - 1}` : (PROVIDER_LABELS[primary] ?? primary);

  return (
    <Tooltip
      placement="bottom"
      content={
        <div className="flex flex-col gap-1 min-w-[140px]">
          <p className="font-semibold text-fg">AI Sağlayıcıları</p>
          {health && Object.entries(health.providers).map(([name, ok]) => (
            <div key={name} className="flex items-center justify-between gap-2">
              <span className="text-fg-muted">{PROVIDER_LABELS[name] ?? name}</span>
              <span className={cn("text-[10px] font-semibold", ok ? "text-success" : "text-fg-disabled")}>
                {ok ? "Aktif" : "Pasif"}
              </span>
            </div>
          ))}
          {!health && <p className="text-danger text-xs">Gateway erişilemiyor</p>}
        </div>
      }
    >
      <button
        type="button"
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium transition-colors",
          toneClasses[tone],
        )}
        data-testid="ai-status-chip"
      >
        <span className={cn("h-1.5 w-1.5 rounded-full", dotClasses[tone])} />
        AI: {label}
        {activeCount > 0 && <span className="text-fg-subtle">/ {totalCount}</span>}
      </button>
    </Tooltip>
  );
}
