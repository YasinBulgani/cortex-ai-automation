"use client";

import { useEffect, useRef, useState } from "react";

/**
 * useLiveData — backend'den canlı veri akışı.
 *
 * Önce WebSocket dener, başarısız olursa polling'e düşer.
 * Pause/Resume desteği, error handling, son güncelleme zamanı.
 *
 * Kullanım:
 *   const { data, status, lastUpdate, pause, resume } = useLiveData<DashboardData>({
 *     wsUrl: '/ws/dashboard',
 *     pollUrl: '/api/v1/tspm/dashboard/global',
 *     interval: 30_000,
 *   });
 */

type LiveStatus = "connecting" | "connected" | "polling" | "paused" | "error" | "idle";

export interface UseLiveDataOptions<T> {
  wsUrl?: string;
  pollUrl: string;
  interval?: number;        // polling interval ms (default 30s)
  enabled?: boolean;
  parseMessage?: (msg: unknown) => T | null;
  fetcher?: (url: string) => Promise<T>;
}

export function useLiveData<T>({
  wsUrl,
  pollUrl,
  interval = 30_000,
  enabled = true,
  parseMessage,
  fetcher,
}: UseLiveDataOptions<T>) {
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<LiveStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [paused, setPaused] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Polling helper
  const doPoll = async () => {
    try {
      const result = fetcher
        ? await fetcher(pollUrl)
        : await fetch(pollUrl, {
            credentials: "include",
            headers: { Accept: "application/json" },
          }).then(r => {
            if (!r.ok) throw new Error(`${r.status}`);
            return r.json() as Promise<T>;
          });
      setData(result);
      setLastUpdate(new Date());
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Veri alınamadı");
    }
  };

  useEffect(() => {
    if (!enabled || paused) {
      if (wsRef.current) wsRef.current.close();
      if (pollRef.current) clearInterval(pollRef.current);
      setStatus(paused ? "paused" : "idle");
      return;
    }

    // WS dene
    if (wsUrl && typeof WebSocket !== "undefined") {
      try {
        setStatus("connecting");
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => setStatus("connected");
        ws.onmessage = (evt) => {
          try {
            const parsed = typeof evt.data === "string" ? JSON.parse(evt.data) : evt.data;
            const value = parseMessage ? parseMessage(parsed) : (parsed as T);
            if (value !== null && value !== undefined) {
              setData(value);
              setLastUpdate(new Date());
            }
          } catch { /* ignore parse */ }
        };
        ws.onerror = () => {
          // WS başarısız → polling'e düş
          ws.close();
        };
        ws.onclose = () => {
          if (wsRef.current === ws) {
            wsRef.current = null;
            if (!paused) startPolling();
          }
        };
        return () => { ws.close(); };
      } catch {
        startPolling();
      }
    } else {
      startPolling();
    }

    function startPolling() {
      setStatus("polling");
      doPoll();
      pollRef.current = setInterval(doPoll, interval);
    }

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollUrl, wsUrl, enabled, paused, interval]);

  return {
    data,
    status,
    error,
    lastUpdate,
    paused,
    pause:  () => setPaused(true),
    resume: () => setPaused(false),
    refetch: doPoll,
  };
}
