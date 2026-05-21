"use client";

/**
 * AiAssistantPanel — Cmd+J ile sağdan açılan AI sohbet paneli.
 *
 * - Klavye: Cmd+J / Ctrl+J = toggle, Escape = kapat
 * - Bağlam farkındalığı: aktif sayfa + aktif proje
 * - Streaming: SSE üzerinden token akışı (varsa)
 * - Quick prompts: bağlama göre dinamik
 * - Konuşma geçmişi: backend session ile veya localStorage fallback
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { apiFetch, API_BASE, getToken } from "@/lib/api";
import { useProject } from "@/lib/useProject";
import { cn } from "@/lib/utils";
import { Kbd, KbdGroup } from "@/components/ui/kbd";

type Message = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  ts: number;
  pending?: boolean;
};

type Session = { id: string; title: string };

const QUICK_PROMPTS_CONTEXTUAL: Record<string, { label: string; prompt: string }[]> = {
  "/":               [
    { label: "Sistem durumu",    prompt: "Şu anki sistem durumunu özetle: çalışan koşular, AI sağlığı, dikkat çeken metrikler." },
    { label: "Son aktiviteler",  prompt: "Son aktiviteleri yorumla — neler dikkat çekiyor?" },
  ],
  "/portfolio":      [
    { label: "Sağlık raporu",    prompt: "Proje portföyümün genel sağlığını özetle." },
    { label: "Riskli projeler",  prompt: "Hangi projeler riskli durumda görünüyor?" },
  ],
  "/task-drafts":    [
    { label: "Senaryo öner",     prompt: "Aktif proje için 3 BDD senaryosu öner — Gherkin formatında." },
    { label: "Eksik testler",    prompt: "Bu projede eksik kritik test senaryolarını listele." },
  ],
  "/flow-designer":  [
    { label: "Akış öner",        prompt: "Test otomasyon akışı için en uygun şablonu öner ve gerekçesini açıkla." },
  ],
  "/ai-agents":      [
    { label: "Hangi ajan?",      prompt: "Hangi AI ajanını ne zaman kullanmalıyım? Kısa rehber." },
  ],
  "/nexus-code":     [
    { label: "Code analizi",     prompt: "Bana hızlı bir kod analizi yap — odak alanları ne olmalı?" },
  ],
  default: [
    { label: "Sonraki adım",     prompt: "Şu an en mantıklı sonraki adım ne? Kısa ve net öner." },
    { label: "Yardım et",        prompt: "Bu sayfada ne yapabilirim? 3 maddede özetle." },
  ],
};

function getQuickPrompts(pathname: string | null) {
  if (!pathname) return QUICK_PROMPTS_CONTEXTUAL.default;
  return QUICK_PROMPTS_CONTEXTUAL[pathname] ?? QUICK_PROMPTS_CONTEXTUAL.default;
}

function pageContext(pathname: string | null): string {
  if (!pathname) return "ana sayfa";
  if (pathname === "/") return "Aktivite Monitörü";
  if (pathname.startsWith("/portfolio")) return "Proje Portfolyosu";
  if (pathname.startsWith("/task-drafts")) return "Senaryo Oluşturucu";
  if (pathname.startsWith("/flow-designer")) return "Akış Tasarımcısı";
  if (pathname.startsWith("/ai-agents")) return "AI Ajanları";
  if (pathname.startsWith("/nexus-code")) return "Prompt Kütüphanesi";
  if (pathname.startsWith("/ide")) return "Senaryo IDE";
  if (pathname.startsWith("/p/")) {
    const sub = pathname.split("/")[3] ?? "proje";
    return `Proje › ${sub}`;
  }
  return pathname;
}

export function AiAssistantPanel() {
  const pathname = usePathname();
  const { project, projectId } = useProject();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // ── Cmd+J / Ctrl+J toggle ─────────────────────────────────────────────
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "j") {
        e.preventDefault();
        setOpen(prev => !prev);
      }
      if (e.key === "Escape" && open) setOpen(false);
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open]);

  // ── Açıldığında input focus + scroll bottom ──────────────────────────
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // ── Session başlat (lazy, ilk mesajda) ───────────────────────────────
  const ensureSession = useCallback(async (): Promise<string | null> => {
    if (sessionIdRef.current) return sessionIdRef.current;
    try {
      const s = await apiFetch<Session>("/api/v1/ai/chat/sessions", {
        method: "POST",
        json: {
          title: `${pageContext(pathname)} · ${new Date().toLocaleString("tr-TR", { hour: "2-digit", minute: "2-digit" })}`,
          project_id: projectId,
        },
      });
      sessionIdRef.current = s.id;
      return s.id;
    } catch {
      return null;
    }
  }, [pathname, projectId]);

  // ── Mesaj gönder + stream ────────────────────────────────────────────
  const send = useCallback(async (text: string) => {
    if (!text.trim() || sending) return;
    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      content: text.trim(),
      ts: Date.now(),
    };
    const assistantMsg: Message = {
      id: `a-${Date.now()}`,
      role: "assistant",
      content: "",
      ts: Date.now() + 1,
      pending: true,
    };
    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setInput("");
    setSending(true);
    setError(null);

    try {
      const sid = await ensureSession();
      if (!sid) throw new Error("Oturum oluşturulamadı");

      const url = `${API_BASE}/api/v1/ai/chat/sessions/${sid}/messages/stream`;
      const token = getToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const ctxPrefix = `[Bağlam: ${pageContext(pathname)}${project ? ` / Proje: ${project.name}` : ""}]\n\n`;

      const res = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify({ content: ctxPrefix + text }),
      });

      if (!res.ok || !res.body) {
        throw new Error(`AI yanıt hatası (${res.status})`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        // SSE format: "data: <text>\n\n"
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6).trim();
            if (data === "[DONE]") continue;
            try {
              const parsed = JSON.parse(data);
              if (parsed.delta || parsed.content) {
                accumulated += parsed.delta ?? parsed.content;
                setMessages(prev => prev.map(m =>
                  m.id === assistantMsg.id ? { ...m, content: accumulated, pending: true } : m
                ));
              }
            } catch {
              // Plain text chunk
              accumulated += data;
              setMessages(prev => prev.map(m =>
                m.id === assistantMsg.id ? { ...m, content: accumulated, pending: true } : m
              ));
            }
          }
        }
      }

      setMessages(prev => prev.map(m =>
        m.id === assistantMsg.id ? { ...m, content: accumulated || "(boş yanıt)", pending: false } : m
      ));
    } catch (e: unknown) {
      const errMsg = e instanceof Error ? e.message : "AI yanıt alınamadı";
      setError(errMsg);
      setMessages(prev => prev.map(m =>
        m.id === assistantMsg.id
          ? { ...m, content: `⚠️ ${errMsg}`, pending: false }
          : m
      ));
    } finally {
      setSending(false);
    }
  }, [sending, ensureSession, pathname, project]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  const reset = () => {
    setMessages([]);
    sessionIdRef.current = null;
    setError(null);
  };

  const quickPrompts = getQuickPrompts(pathname);

  return (
    <>
      {/* Floating AI button — sağ alt, her zaman görünür */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={cn(
          "fixed bottom-6 right-6 z-overlay flex items-center gap-2 rounded-full px-4 py-3 shadow-elevated transition-all duration-base",
          "bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:scale-105",
          open && "opacity-0 pointer-events-none scale-90"
        )}
        aria-label="AI asistan aç"
        data-testid="ai-fab"
      >
        <span className="text-lg leading-none">✨</span>
        <span className="hidden sm:inline text-sm font-medium">AI Asistan</span>
        <KbdGroup className="hidden md:inline-flex">
          <Kbd size="sm" className="bg-white/20 text-white border-white/30">⌘</Kbd>
          <Kbd size="sm" className="bg-white/20 text-white border-white/30">J</Kbd>
        </KbdGroup>
      </button>

      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-overlay bg-black/40 backdrop-blur-sm animate-fade-in"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Panel */}
      <aside
        className={cn(
          "fixed top-0 right-0 bottom-0 z-modal w-full sm:w-[440px] bg-surface-overlay border-l border-border-strong shadow-xl flex flex-col transition-transform duration-slow",
          open ? "translate-x-0" : "translate-x-full"
        )}
        aria-label="AI Asistan"
        role="dialog"
        data-testid="ai-panel"
      >
        {/* Header */}
        <header className="flex items-center gap-2 border-b border-border px-4 py-3">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-indigo-600 text-sm">✨</span>
          <div className="min-w-0 flex-1">
            <h2 className="text-sm font-semibold text-fg">AI Asistan</h2>
            <p className="text-[10px] text-fg-subtle truncate">{pageContext(pathname)}{project && ` · ${project.name}`}</p>
          </div>
          <button
            type="button"
            onClick={reset}
            className="rounded-md p-1.5 text-fg-subtle hover:bg-surface-accent hover:text-fg transition-colors"
            aria-label="Konuşmayı sıfırla"
            title="Yeni konuşma"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="rounded-md p-1.5 text-fg-subtle hover:bg-surface-accent hover:text-fg transition-colors"
            aria-label="Kapat"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </header>

        {/* Konuşma alanı */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center text-center py-8">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 text-2xl">
                ✨
              </div>
              <h3 className="text-sm font-semibold text-fg mb-1">Bu sayfa için size nasıl yardımcı olabilirim?</h3>
              <p className="text-xs text-fg-muted mb-6">
                Bağlam: <span className="text-fg-muted font-medium">{pageContext(pathname)}</span>
                {project && <> · <span className="text-fg-muted font-medium">{project.name}</span></>}
              </p>
              {/* Quick prompts */}
              <div className="grid grid-cols-1 gap-2 w-full max-w-sm">
                {quickPrompts.map(qp => (
                  <button
                    key={qp.label}
                    type="button"
                    onClick={() => send(qp.prompt)}
                    className="flex items-start gap-2 text-left rounded-lg border border-border bg-surface-raised px-3 py-2 hover:border-brand-primary hover:bg-brand-soft transition-colors group"
                  >
                    <span className="text-violet-400 group-hover:text-brand-primary mt-0.5">→</span>
                    <span className="text-xs text-fg-muted group-hover:text-fg">{qp.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map(m => (
              <MessageBubble key={m.id} message={m} />
            ))
          )}
        </div>

        {/* Input */}
        <div className="border-t border-border p-3">
          {error && messages.length === 0 && (
            <p className="text-xs text-danger mb-2">{error}</p>
          )}
          <div className="relative rounded-lg border border-border bg-surface-raised focus-within:border-brand-primary transition-colors">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              placeholder="Bir şey sor..."
              className="block w-full resize-none bg-transparent px-3 pt-2.5 pb-8 text-sm text-fg placeholder-fg-subtle focus:outline-none"
              disabled={sending}
            />
            <div className="absolute bottom-2 left-3 right-3 flex items-center justify-between text-[10px] text-fg-subtle">
              <span className="flex items-center gap-1">
                <Kbd size="sm">↵</Kbd>
                gönder
                <span className="mx-1">·</span>
                <Kbd size="sm">⇧↵</Kbd>
                yeni satır
              </span>
              <button
                type="button"
                onClick={() => send(input)}
                disabled={!input.trim() || sending}
                className="rounded-md bg-gradient-to-r from-violet-600 to-indigo-600 px-2.5 py-1 text-[10px] font-semibold text-white disabled:opacity-40 hover:opacity-90 transition-opacity"
              >
                {sending ? "..." : "Gönder"}
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}

// ─── Message Bubble ─────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex gap-2.5", isUser && "flex-row-reverse")}>
      <span className={cn(
        "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold",
        isUser
          ? "bg-surface-accent text-fg-muted"
          : "bg-gradient-to-br from-violet-600 to-indigo-600 text-white"
      )}>
        {isUser ? "Sen" : "✨"}
      </span>
      <div className={cn(
        "min-w-0 flex-1 max-w-[85%]",
        isUser && "text-right"
      )}>
        <div className={cn(
          "inline-block rounded-xl px-3 py-2 text-sm",
          isUser
            ? "bg-brand-soft text-fg"
            : "bg-surface-raised text-fg border border-border"
        )}>
          {message.content || <span className="inline-block w-2 h-4 bg-fg-subtle animate-pulse" />}
        </div>
      </div>
    </div>
  );
}
