"use client";

/**
 * AiAssistant — Header'dan açılan AI sohbet paneli
 *
 * - Header'daki butona basinca sagdan drawer olarak acilir
 * - Aktif projeye bagli oturumla calisir (/api/v1/ai/chat)
 * - SSE streaming destekli, yoksa senkron endpoint'e duser
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, API_BASE, getToken } from "@/lib/api";
import { useProject } from "@/lib/useProject";
import { cn } from "@/lib/utils";

type Session = { id: string; title: string; created_at: string };
type Message = { id: string; role: string; content: string; created_at: string };

const QUICK_PROMPTS = [
  { label: "Sonraki adım", prompt: "Bu proje için şu an en mantıklı sonraki adım ne? Kısa ve net öner." },
  { label: "Koşu analizi", prompt: "Son koşuları analiz etmek için hangi ekranlara bakmalıyım?" },
  { label: "Eksik testler", prompt: "Bu projede eksik negatif ve edge-case testleri nasıl bulurum?" },
  { label: "Kalite KPI", prompt: "Yönetim seviyesinde takip edilmesi gereken en kritik kalite KPI'larını çıkar." },
];

export function AiAssistant() {
  const { projectId } = useProject();
  const [open, setOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 120);
    }
  }, [open]);

  /* Drawer acildiginda aktif oturumu yukle (yoksa bos birak) */
  useEffect(() => {
    if (!open || !projectId) return;
    let cancelled = false;
    apiFetch<Session[]>(`/api/v1/ai/chat/sessions?project_id=${projectId}`)
      .then((sessions) => {
        if (cancelled) return;
        if (sessions && sessions.length > 0) {
          setSessionId(sessions[0].id);
          apiFetch<Message[]>(`/api/v1/ai/chat/sessions/${sessions[0].id}/messages`)
            .then((msgs) => !cancelled && setMessages(msgs))
            .catch(() => null);
        }
      })
      .catch(() => null);
    return () => {
      cancelled = true;
    };
  }, [open, projectId]);

  async function ensureSession(): Promise<string> {
    if (sessionId) return sessionId;
    const created = await apiFetch<Session>("/api/v1/ai/chat/sessions", {
      method: "POST",
      json: { project_id: projectId, title: "Hızlı Sohbet" },
    });
    setSessionId(created.id);
    return created.id;
  }

  async function submitMessage(content: string) {
    const trimmed = content.trim();
    if (!trimmed || loading) return;
    if (!projectId) {
      setError("Önce bir proje seçin.");
      return;
    }
    setError(null);
    setLoading(true);
    setInput("");

    let sid: string;
    try {
      sid = await ensureSession();
    } catch {
      setError("Oturum oluşturulamadı.");
      setLoading(false);
      return;
    }

    const userMsg: Message = {
      id: `tmp-${Date.now()}`,
      role: "user",
      content: trimmed,
      created_at: new Date().toISOString(),
    };
    const assistantId = `stream-${Date.now()}`;
    setMessages((prev) => [...prev, userMsg]);

    try {
      const token = getToken();
      const res = await fetch(
        `${API_BASE}/api/v1/ai/chat/sessions/${sid}/messages/stream`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ content: trimmed }),
        },
      );

      if (!res.ok || !res.body) {
        const syncRes = await apiFetch<{ user_message: Message; assistant_message: Message }>(
          `/api/v1/ai/chat/sessions/${sid}/messages`,
          { method: "POST", json: { content: trimmed } },
        );
        setMessages((prev) => [
          ...prev.filter((m) => !m.id.startsWith("tmp-")),
          syncRes.user_message,
          syncRes.assistant_message,
        ]);
        return;
      }

      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", content: "", created_at: new Date().toISOString() },
      ]);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;
          try {
            const evt = JSON.parse(raw);
            if (evt.token) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: m.content + evt.token } : m,
                ),
              );
            }
            if (evt.done && evt.message_id) {
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantId ? { ...m, id: evt.message_id } : m)),
              );
            }
            if (evt.error) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content || `Hata: ${evt.error}` }
                    : m,
                ),
              );
            }
          } catch {
            /* skip malformed JSON */
          }
        }
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: "Yanıt alınamadı. Tekrar deneyin.",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submitMessage(input);
    }
  }

  function resetSession() {
    setSessionId(null);
    setMessages([]);
    setError(null);
  }

  return (
    <>
      {/* ── Trigger butonu ── */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="relative flex items-center gap-1.5 rounded-lg bg-violet-600/15 px-3 py-1.5 text-xs font-semibold text-violet-300 transition-colors hover:bg-violet-600/25"
        title="AI Asistan"
        aria-label="AI Asistan'ı aç"
        data-testid="btn-open-ai-assistant"
      >
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.847.814a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
        </svg>
        AI Asistan
      </button>

      {/* ── Backdrop (sadece mobile/dokunmatikte anlamli) ── */}
      {open && (
        <div
          className="fixed left-0 right-0 top-14 bottom-0 z-40 bg-black/30 backdrop-blur-sm md:bg-transparent md:backdrop-blur-0"
          onClick={() => setOpen(false)}
        />
      )}

      {/* ── Drawer ── */}
      <div
        className={cn(
          "fixed right-0 top-14 bottom-0 z-50 flex w-[420px] max-w-[min(90vw,420px)] flex-col border-l border-slate-800 bg-slate-900 shadow-2xl transition-transform duration-300",
          open ? "translate-x-0" : "translate-x-full",
        )}
        role="dialog"
        aria-label="AI Asistan"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-500/15 text-violet-300">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.847.814a4.5 4.5 0 0 0-3.09 3.09Z" />
              </svg>
            </div>
            <div className="leading-tight">
              <p className="text-sm font-semibold text-white">AI Asistan</p>
              <p className="text-[10px] text-slate-400">Proje bağlamında yanıtlar</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={resetSession}
              className="rounded p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
              title="Yeni sohbet"
              aria-label="Yeni sohbet"
              data-testid="btn-ai-assistant-new"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
            </button>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
              title="Kapat"
              aria-label="Kapat"
              data-testid="btn-ai-assistant-close"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Mesajlar */}
        <div className="flex-1 overflow-y-auto px-4 py-3" data-testid="ai-assistant-messages">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-violet-500/10 text-violet-300">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.847.814a4.5 4.5 0 0 0-3.09 3.09Z" />
                </svg>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-white">Nasıl yardımcı olabilirim?</p>
                <p className="text-xs text-slate-400">Bir soru yazın ya da hızlı niyetlerden birini seçin.</p>
              </div>
              <div className="flex flex-wrap justify-center gap-1.5">
                {QUICK_PROMPTS.map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => submitMessage(item.prompt)}
                    disabled={loading || !projectId}
                    className="rounded-full border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-[11px] text-slate-300 transition-colors hover:border-violet-400/40 hover:bg-violet-500/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              {!projectId && (
                <p className="text-[11px] text-amber-300">Sohbet için önce bir proje seçin.</p>
              )}
            </div>
          )}
          <div className="space-y-3">
            {messages.map((m) => (
              <div
                key={m.id}
                className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
              >
                <div
                  className={cn(
                    "max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed",
                    m.role === "user"
                      ? "bg-violet-600 text-white"
                      : "bg-slate-800 text-slate-100",
                  )}
                >
                  <div className="whitespace-pre-wrap break-words">{m.content || "…"}</div>
                </div>
              </div>
            ))}
            {loading && messages[messages.length - 1]?.role !== "assistant" && (
              <div className="flex justify-start">
                <div className="rounded-2xl bg-slate-800 px-3 py-2 text-sm text-slate-400">
                  <span className="inline-flex gap-1">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-500 [animation-delay:-0.3s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-500 [animation-delay:-0.15s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-500" />
                  </span>
                </div>
              </div>
            )}
          </div>
          <div ref={bottomRef} />
        </div>

        {/* Hata */}
        {error && (
          <div className="border-t border-red-500/30 bg-red-500/10 px-4 py-2 text-xs text-red-300">
            {error}
          </div>
        )}

        {/* Girdi */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submitMessage(input);
          }}
          className="border-t border-slate-800 p-3"
        >
          <div className="flex items-end gap-2 rounded-xl border border-slate-700 bg-slate-950/60 px-2 py-1.5 focus-within:border-violet-500/60">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder={projectId ? "AI Asistan'a sorun..." : "Önce bir proje seçin"}
              disabled={loading || !projectId}
              className="max-h-32 flex-1 resize-none bg-transparent px-1.5 py-1 text-sm text-white placeholder:text-slate-500 focus:outline-none disabled:opacity-50"
              data-testid="ai-assistant-input"
            />
            <button
              type="submit"
              disabled={loading || !input.trim() || !projectId}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600 text-white transition-colors hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Gönder"
              data-testid="ai-assistant-send"
            >
              {loading ? (
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                  <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                </svg>
              ) : (
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                </svg>
              )}
            </button>
          </div>
          <p className="mt-1.5 px-1 text-[10px] text-slate-500">
            Enter ile gönder · Shift+Enter yeni satır
          </p>
        </form>
      </div>
    </>
  );
}
