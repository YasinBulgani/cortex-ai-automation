"use client";

import { useEffect, useRef } from "react";
import { useWebSocket } from "@/lib/useWebSocket";

/**
 * Execution tablosunu WebSocket üzerinden otomatik yeniler.
 * WebSocket'ten "execution.completed" veya "execution.updated" olayı geldiğinde
 * `onRefresh` callback'ini tetikler.
 */
export function useRealtimeExecution(projectId: string, onRefresh: () => void) {
  const { messages } = useWebSocket();
  const onRefreshRef = useRef(onRefresh);
  onRefreshRef.current = onRefresh;

  useEffect(() => {
    if (messages.length === 0) return;
    const latest = messages[0];
    const payload = latest.payload as { project_id?: string };
    if (
      ["execution.completed", "execution.updated", "execution.failed"].includes(latest.type) &&
      (!payload.project_id || payload.project_id === projectId)
    ) {
      onRefreshRef.current();
    }
  }, [messages, projectId]);
}
