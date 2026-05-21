"use client";

import { useState } from "react";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useProjects } from "@/lib/hooks/use-projects";

// Hits Next.js /api/engine/* proxy which adds X-Internal-Key server-side
async function engineProxy<T>(
  enginePath: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const { json, headers, ...rest } = init;
  const h = new Headers(headers);
  if (json !== undefined) h.set("Content-Type", "application/json");
  const stripped = enginePath.replace(/^\/?api\//, "");
  const res = await fetch(`/api/engine/${stripped}`, {
    ...rest,
    headers: h,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new EngineError(res.status, text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

class EngineError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

type Role = "user" | "ai";
interface ChatMessage {
  id: string;
  role: Role;
  text: string;
  gherkin?: string;
  source?: "engine" | "demo";
  saved?: { projectId: string; scenarioId: string };
}

const SAMPLE_PROMPTS = [
  "Yanlış şifreyle login deneyeyim, hata mesajı görmeli",
  "Sepete 3 ürün ekle, toplam fiyat doğru olsun",
  "Mobil görünümde menü açılır mı kontrol et",
  "Kupon kodu 'SAVE10' uygulayınca %10 indirim olmalı",
];

const DEMO_GHERKIN = `Feature: Yanlış şifreyle login denemesi
  Kullanıcı geçersiz şifre girdiğinde sistem hata mesajı göstermeli

  Scenario: Geçersiz şifre ile giriş denemesi
    Given Kullanıcı login sayfasında
    When  "user@example.com" e-posta adresini girer
    And   "yanlis-sifre-123" şifresini girer
    And   "Giriş Yap" butonuna tıklar
    Then  "Geçersiz kullanıcı adı veya şifre" hata mesajı görünür
    And   Login butonu hâlâ tıklanabilir durumda kalır`;

function extractTitle(gherkin: string): string {
  const featureLine = gherkin.split("\n").find((l) => l.trim().startsWith("Feature:"));
  if (featureLine) return featureLine.replace(/^Feature:\s*/, "").trim().slice(0, 200);
  return gherkin.split("\n")[0].trim().slice(0, 200) || "AI Üretilmiş Senaryo";
}

function GherkinPreview({
  text,
  source,
  onSave,
  saving,
  saved,
  projectId,
}: {
  text: string;
  source: "engine" | "demo";
  onSave: () => void;
  saving: boolean;
  saved?: { projectId: string; scenarioId: string };
  projectId: string | "";
}) {
  return (
    <div className="mt-3 rounded-lg bg-slate-950/70 border border-slate-800 overflow-hidden">
      <div className="px-3 py-1.5 border-b border-slate-800 flex items-center justify-between text-[10px]">
        <span className="font-mono text-slate-500">feature.feature</span>
        <span className={`px-1.5 py-0.5 rounded font-semibold ${
          source === "engine"
            ? "bg-emerald-500/15 text-emerald-300"
            : "bg-amber-500/15 text-amber-300"
        }`}>
          {source === "engine" ? "🟢 Engine" : "⚠ Demo"}
        </span>
      </div>
      <pre className="p-3 text-[11px] font-mono text-slate-200 leading-relaxed overflow-x-auto whitespace-pre">
{text}
      </pre>
      <div className="flex items-center justify-end gap-2 px-3 py-2 border-t border-slate-800/80">
        <button
          onClick={() => navigator.clipboard?.writeText(text)}
          className="text-[11px] px-2 py-1 rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700"
        >
          Kopyala
        </button>
        {saved ? (
          <Link
            href={`/p/${saved.projectId}/scenarios/${saved.scenarioId}`}
            className="text-[11px] px-2 py-1 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-medium hover:bg-emerald-500/30"
          >
            ✓ Kaydedildi · Aç →
          </Link>
        ) : (
          <button
            onClick={onSave}
            disabled={saving || !projectId}
            className="text-[11px] px-2 py-1 rounded-md bg-emerald-500 text-white hover:bg-emerald-400 font-medium disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {saving ? "Kaydediliyor…" : !projectId ? "Önce proje seç" : "Senaryoya Ekle"}
          </button>
        )}
      </div>
    </div>
  );
}

export function ConversationalTestCreator() {
  const { data: projects } = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "intro",
      role: "ai",
      text: "Doğal dilde anlat, BDD/Gherkin senaryosu üreteyim. Üst kutudan hedef projeyi seç, sonra konuşmaya başla.",
    },
  ]);
  const [input, setInput] = useState("");
  const [generating, setGenerating] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);

  const send = async (text: string) => {
    if (!text.trim() || generating) return;
    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: "user", text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setGenerating(true);

    try {
      const res = await engineProxy<{ content?: string; error?: string }>(
        "/api/generate-feature",
        { method: "POST", json: { requirements: text } },
      );
      if (res?.content) {
        setMessages((m) => [...m, {
          id: `a-${Date.now()}`,
          role: "ai",
          text: "Senaryo üretildi (engine):",
          gherkin: res.content,
          source: "engine",
        }]);
      } else {
        throw new Error(res?.error || "Boş yanıt");
      }
    } catch (err) {
      const reason = err instanceof EngineError ? `${err.status}` : err instanceof Error ? err.message : "bilinmeyen";
      setMessages((m) => [...m, {
        id: `a-${Date.now()}`,
        role: "ai",
        text: `Engine'e ulaşılamadı (${reason}). Aşağıda örnek demo çıktısı:`,
        gherkin: DEMO_GHERKIN,
        source: "demo",
      }]);
    } finally {
      setGenerating(false);
    }
  };

  const saveAsScenario = async (msg: ChatMessage) => {
    if (!msg.gherkin || !selectedProjectId) return;
    setSavingId(msg.id);
    try {
      const created = await apiFetch<{ id: string }>(
        `/api/v1/tspm/projects/${selectedProjectId}/scenarios`,
        {
          method: "POST",
          json: {
            title: extractTitle(msg.gherkin),
            description: msg.gherkin,
            status: "draft",
            tags: ["ai-generated", msg.source ?? "unknown"],
          },
        },
      );
      setMessages((m) => m.map((x) =>
        x.id === msg.id
          ? { ...x, saved: { projectId: selectedProjectId, scenarioId: created.id } }
          : x,
      ));
    } catch (err) {
      const reason = err instanceof ApiError ? `${err.status} ${err.message}` : "bilinmeyen hata";
      setMessages((m) => [...m, {
        id: `e-${Date.now()}`,
        role: "ai",
        text: `Kaydetme başarısız: ${reason}`,
      }]);
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden flex flex-col h-[480px]">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-sm flex-shrink-0">
            💬
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-white truncate">Konuşan Test Yazarı</h2>
            <p className="text-[11px] text-slate-400 truncate">Doğal dil → Gherkin → Senaryo</p>
          </div>
        </div>
        {/* Project picker */}
        <select
          value={selectedProjectId}
          onChange={(e) => setSelectedProjectId(e.target.value)}
          className="bg-slate-950 border border-slate-700 rounded-lg px-2 py-1 text-[11px] text-slate-300 max-w-[140px] truncate focus:outline-none focus:border-emerald-500/50"
        >
          <option value="">Hedef proje seç…</option>
          {projects?.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[90%] rounded-2xl px-4 py-2.5 text-sm ${
              m.role === "user"
                ? "bg-emerald-500/15 text-emerald-100 border border-emerald-500/25"
                : "bg-slate-800/70 text-slate-100 border border-slate-700/60"
            }`}>
              <p className="whitespace-pre-wrap leading-relaxed">{m.text}</p>
              {m.gherkin && m.source && (
                <GherkinPreview
                  text={m.gherkin}
                  source={m.source}
                  onSave={() => void saveAsScenario(m)}
                  saving={savingId === m.id}
                  saved={m.saved}
                  projectId={selectedProjectId}
                />
              )}
            </div>
          </div>
        ))}
        {generating && (
          <div className="flex justify-start">
            <div className="bg-slate-800/70 border border-slate-700/60 rounded-2xl px-4 py-2.5 text-sm text-slate-400">
              <span className="inline-flex gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: "0.15s" }} />
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: "0.3s" }} />
              </span>
              <span className="ml-2">Engine BDD senaryosu üretiyor…</span>
            </div>
          </div>
        )}
      </div>

      {/* Suggested prompts */}
      {messages.length === 1 && (
        <div className="px-5 pb-2 flex flex-wrap gap-2">
          {SAMPLE_PROMPTS.map((p) => (
            <button
              key={p}
              onClick={() => void send(p)}
              className="text-[11px] px-2.5 py-1 rounded-full bg-slate-800/60 text-slate-300 border border-slate-700/60 hover:bg-slate-700 hover:text-white transition-colors"
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <form
        onSubmit={(e) => { e.preventDefault(); void send(input); }}
        className="px-5 py-3 border-t border-slate-800 flex items-center gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Test etmek istediğini yaz…"
          className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/50"
        />
        <button
          type="submit"
          disabled={!input.trim() || generating}
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 text-white text-sm font-semibold hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Üret
        </button>
      </form>
    </div>
  );
}
