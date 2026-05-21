"use client";

import { useEffect, useRef, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch, API_BASE } from "@/lib/api";

type Session = { id: string; title: string; created_at: string };
type Message = { id: string; role: string; content: string; created_at: string };

const STARTER_PROMPTS = [
  { label: "Sonraki adım", prompt: "Bu proje için şu an en mantıklı sonraki adım ne? Kısa ama net öner." },
  { label: "Koşu analizi", prompt: "Bu projedeki son koşuları analiz etmek için hangi ekranlara bakmalıyım ve neyi kontrol etmeliyim?" },
  { label: "API testi kur", prompt: "Bu projede servis testlerini AI destekli şekilde kurmak için adım adım bir plan çıkar." },
  { label: "Otomasyon akışı", prompt: "Dokümandan otomasyona giden en hızlı ve sağlam akış nedir?" },
];

export default function AiChatPage() {
  const projectId = useRouteParam("projectId");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiFetch<Session[]>(`/api/v1/ai/chat/sessions?project_id=${projectId}`).then((s) => {
      setSessions(s);
      if (s.length > 0) setActiveId(s[0].id);
    });
  }, [projectId]);

  useEffect(() => {
    if (!activeId) return;
    apiFetch<Message[]>(`/api/v1/ai/chat/sessions/${activeId}/messages`).then(setMessages);
  }, [activeId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function createSession() {
    const s = await apiFetch<Session>("/api/v1/ai/chat/sessions", {
      method: "POST",
      json: { project_id: projectId, title: "Yeni Sohbet" },
    });
    setSessions((prev) => [s, ...prev]);
    setActiveId(s.id);
    setMessages([]);
    return s;
  }

  async function submitMessage(content: string) {
    const trimmed = content.trim();
    if (!trimmed) return;
    setLoading(true);
    setInput("");
    let sessionId = activeId;
    if (!sessionId) {
      const created = await createSession();
      sessionId = created.id;
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
      const res = await fetch(
        `${API_BASE}/api/v1/ai/chat/sessions/${sessionId}/messages/stream`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ content: trimmed }),
        },
      );

      if (!res.ok || !res.body) {
        const syncRes = await apiFetch<{ user_message: Message; assistant_message: Message }>(
          `/api/v1/ai/chat/sessions/${sessionId}/messages`,
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
            // skip malformed JSON
          }
        }
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: `err-${Date.now()}`, role: "assistant", content: "Yanıt alınamadı.", created_at: new Date().toISOString() },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function sendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    await submitMessage(input);
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="ai-chat-page">
      <PageHeader
        title="Visium Intelligence"
        description="Proje içinden AI yardımı alın"
      />

      <div className="flex min-h-0 flex-1 gap-4">
        <aside className="w-56 shrink-0 overflow-y-auto rounded-lg border border-border p-3 flex flex-col gap-3 bg-background/60">
          <Button onClick={createSession} className="w-full" data-testid="ai-chat-btn-new">
            + Yeni Sohbet
          </Button>

          <div className="space-y-1 flex-1">
            {sessions.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => setActiveId(s.id)}
                className={`w-full rounded px-2 py-1.5 text-left text-xs truncate transition-colors ${
                  activeId === s.id
                    ? "bg-accent/10 font-medium text-accent"
                    : "hover:bg-black/5 dark:hover:bg-white/5"
                }`}
                data-testid={`ai-chat-session-${s.id}`}
              >
                {s.title}
              </button>
            ))}
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col rounded-lg border border-border">
          <div className="flex items-center border-b border-border px-4 py-2">
            <span className="text-sm font-medium">AI Asistan</span>
          </div>

          <div className="border-b border-border px-4 py-3">
            <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-muted">Hazır niyetler</p>
            <div className="flex flex-wrap gap-2">
              {STARTER_PROMPTS.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => submitMessage(item.prompt)}
                  disabled={loading}
                  className="rounded-full border border-border bg-black/5 px-3 py-1.5 text-xs text-foreground transition hover:bg-black/10 disabled:opacity-50 dark:bg-white/5 dark:hover:bg-white/10"
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-muted">Bir sohbet başlatın veya hazır niyetlerden biriyle devam edin.</p>
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[75%] rounded-lg px-4 py-2.5 text-sm ${
                    m.role === "user" ? "bg-accent text-accent-fg" : "bg-black/5 dark:bg-white/5"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{m.content}</div>
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={sendMessage} className="border-t border-border p-3 flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Mesajınızı yazın..."
              disabled={loading}
              className="flex-1"
              data-testid="ai-chat-input-message"
            />
            <Button type="submit" disabled={loading} data-testid="ai-chat-btn-send">
              {loading ? "..." : "Gönder"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
