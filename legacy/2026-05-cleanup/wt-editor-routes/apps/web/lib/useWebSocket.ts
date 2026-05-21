"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { API_BASE } from "./api-client";

export interface WSMessage {
  type: string;
  payload: Record<string, unknown>;
  timestamp?: string;
}

type MessageHandler = (msg: WSMessage) => void;

const RAW_WS_BASE = process.env.NEXT_PUBLIC_WS_BASE?.replace(/\/$/, "");

function resolveWebSocketUrl(): string {
  const suffix = "/api/v1/ws/notifications";

  if (RAW_WS_BASE) {
    return `${RAW_WS_BASE}${suffix}`;
  }

  if (typeof window !== "undefined") {
    const browserWsBase = window.location.origin.replace(/^http/, "ws");
    try {
      const resolvedApiUrl = new URL(API_BASE, window.location.origin);
      const apiWsBase = resolvedApiUrl.origin.replace(/^http/, "ws");

      // Cookie auth requires same host; fallback to browser host when env host drifts.
      if (resolvedApiUrl.host !== window.location.host) {
        return `${browserWsBase}${suffix}`;
      }
      return `${apiWsBase}${suffix}`;
    } catch {
      return `${browserWsBase}${suffix}`;
    }
  }

  return `${API_BASE.replace(/^http/, "ws")}${suffix}`;
}

export function useWebSocket(onMessage?: MessageHandler) {
  const [messages, setMessages] = useState<WSMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const handlerRef = useRef<MessageHandler | undefined>(onMessage);
  const reconnectEnabledRef = useRef(true);

  // Keep the handler ref up to date without causing reconnects
  useEffect(() => {
    handlerRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    const ws = new WebSocket(resolveWebSocketUrl());
    wsRef.current = ws;

    ws.onopen = () => { setConnected(true); retryRef.current = 0; };
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as WSMessage;
        setMessages((prev) => [msg, ...prev].slice(0, 50));
        handlerRef.current?.(msg);
      } catch { /* ignore malformed messages */ }
    };
    ws.onclose = () => {
      setConnected(false);
      if (!reconnectEnabledRef.current) return;
      const delay = Math.min(1000 * Math.pow(2, retryRef.current), 30000);
      retryRef.current += 1;
      setTimeout(connect, delay);
    };
    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    reconnectEnabledRef.current = true;
    connect();
    return () => {
      reconnectEnabledRef.current = false;
      wsRef.current?.close();
    };
  }, [connect]);

  const clearMessages = useCallback(() => setMessages([]), []);

  return { messages, connected, clearMessages };
}
