"use client";

import { useCallback, useEffect, useState } from "react";

// Engine proxy hits Next.js /api/engine/* which forwards to Flask :5001
// with the X-Internal-Key server-side. Keeps the secret out of the browser.
async function engineProxy<T>(
  enginePath: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const { json, headers, ...rest } = init;
  const h = new Headers(headers);
  if (json !== undefined) h.set("Content-Type", "application/json");
  // strip leading "/api/" if present so we don't double-prefix
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

interface RecorderSession {
  file: string;
  path: string;
  name: string;
  domain: string;
  action_count: number;
  started_at: string;
}

interface ListResponse {
  ok: boolean;
  sessions: RecorderSession[];
  count: number;
}

interface GenerateResponse {
  ok: boolean;
  code?: string;
  format?: string;
  error?: string;
}

interface StartResponse {
  ok: boolean;
  session_id?: string;
  name?: string;
  domain?: string;
  error?: string;
}

type Format = "playwright" | "cucumber" | "pom_python" | "pom_java" | "pom_typescript";

const FORMATS: { key: Format; label: string; ext: string }[] = [
  { key: "playwright",     label: "Playwright Python", ext: ".py" },
  { key: "cucumber",       label: "Cucumber Feature",  ext: ".feature" },
  { key: "pom_python",     label: "POM Python",        ext: ".py" },
  { key: "pom_java",       label: "POM Java",          ext: ".java" },
  { key: "pom_typescript", label: "POM TypeScript",    ext: ".ts" },
];

function downloadText(content: string, filename: string) {
  const blob = new Blob([content], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function formatRelative(iso: string): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("tr-TR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
}

export function RecorderStudio() {
  const [sessions, setSessions] = useState<RecorderSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<RecorderSession | null>(null);
  const [format, setFormat] = useState<Format>("playwright");
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState<{ code: string; format: string } | null>(null);
  const [startOpen, setStartOpen] = useState(false);

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    try {
      const res = await engineProxy<ListResponse>("/api/recorder/sessions");
      setSessions(res.sessions ?? []);
      setError(null);
    } catch (err) {
      setError(err instanceof EngineError ? `Engine: ${err.status}` : "Engine'e ulaşılamadı (port 5001)");
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void fetchSessions(); }, [fetchSessions]);

  const generateCode = useCallback(async () => {
    if (!selected) return;
    setGenerating(true);
    setGenerated(null);
    try {
      const res = await engineProxy<GenerateResponse>("/api/recorder/generate", {
        method: "POST",
        json: { session_path: selected.path, format },
      });
      if (res?.code) {
        setGenerated({ code: res.code, format });
      } else {
        throw new Error(res?.error || "Boş yanıt");
      }
    } catch (err) {
      const msg = err instanceof EngineError ? err.message : err instanceof Error ? err.message : "Bilinmeyen hata";
      setGenerated({ code: `// Hata: ${msg}\n// Engine /api/recorder/generate başarısız oldu.`, format });
    } finally {
      setGenerating(false);
    }
  }, [selected, format]);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-rose-500 to-pink-600 flex items-center justify-center text-sm">
            🎙️
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Recorder Studio</h2>
            <p className="text-[11px] text-slate-400">Kayıtlı oturumları yönet, Playwright/Cucumber/POM koduna dönüştür</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setStartOpen(true)}
            className="text-[11px] px-2.5 py-1.5 rounded-lg bg-emerald-500 text-white font-semibold hover:bg-emerald-400"
          >
            + Yeni Kayıt
          </button>
          <button
            onClick={() => void fetchSessions()}
            className="text-[11px] px-2.5 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700"
          >
            ⟳
          </button>
        </div>
      </div>

      {/* Start dialog */}
      {startOpen && <StartRecordingDialog
        onClose={() => setStartOpen(false)}
        onStarted={() => { setStartOpen(false); void fetchSessions(); }}
      />}

      {/* Two-pane layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 min-h-[420px]">
        {/* Sessions list */}
        <div className="lg:col-span-2 border-r border-slate-800 max-h-[420px] overflow-y-auto">
          {loading ? (
            <div className="p-8 text-center text-slate-500 text-sm">Yükleniyor…</div>
          ) : error ? (
            <div className="p-6 text-center">
              <div className="text-rose-400 text-xs mb-2">⚠ {error}</div>
              <button onClick={() => void fetchSessions()} className="text-[11px] text-emerald-400 hover:underline">
                Yeniden dene
              </button>
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-xs">
              Kayıt yok. "Yeni Kayıt" ile başlat.
            </div>
          ) : (
            <div className="divide-y divide-slate-800">
              {sessions.map((s) => (
                <button
                  key={s.file}
                  onClick={() => { setSelected(s); setGenerated(null); }}
                  className={`w-full text-left px-4 py-3 hover:bg-slate-800/40 transition-colors ${
                    selected?.file === s.file ? "bg-slate-800/60 border-l-2 border-rose-500" : ""
                  }`}
                >
                  <div className="text-sm text-white font-medium truncate">{s.name || s.file}</div>
                  <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500">
                    <span className="font-mono">{s.action_count} aksiyon</span>
                    {s.domain && <span>· {s.domain}</span>}
                    <span>· {formatRelative(s.started_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Detail / code generation */}
        <div className="lg:col-span-3 flex flex-col">
          {!selected ? (
            <div className="flex-1 flex items-center justify-center p-8 text-slate-500 text-sm text-center">
              <div>
                <div className="text-3xl mb-2 opacity-50">🎬</div>
                <div>Soldaki listeden bir oturum seç</div>
                <div className="text-xs mt-1 text-slate-600">Aksiyonları gör, koda dönüştür</div>
              </div>
            </div>
          ) : (
            <>
              {/* Session header */}
              <div className="px-5 py-3 border-b border-slate-800">
                <div className="text-sm font-semibold text-white">{selected.name}</div>
                <div className="text-[11px] text-slate-400 mt-0.5 font-mono">{selected.file}</div>
              </div>

              {/* Format selector */}
              <div className="px-5 py-3 border-b border-slate-800 flex items-center gap-2 flex-wrap">
                <span className="text-[11px] text-slate-500 uppercase tracking-wide">Format:</span>
                {FORMATS.map((f) => (
                  <button
                    key={f.key}
                    onClick={() => { setFormat(f.key); setGenerated(null); }}
                    className={`text-[11px] px-2.5 py-1 rounded-full transition-colors ${
                      format === f.key
                        ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                        : "bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700 hover:text-slate-200"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
                <button
                  onClick={() => void generateCode()}
                  disabled={generating}
                  className="ml-auto text-[11px] px-3 py-1 rounded-lg bg-gradient-to-r from-rose-500 to-pink-600 text-white font-semibold hover:opacity-90 disabled:opacity-40"
                >
                  {generating ? "Üretiliyor…" : "Kod Üret"}
                </button>
              </div>

              {/* Generated code */}
              <div className="flex-1 overflow-hidden flex flex-col">
                {!generated ? (
                  <div className="flex-1 flex items-center justify-center text-slate-500 text-xs">
                    Format seç → "Kod Üret" tıkla
                  </div>
                ) : (
                  <>
                    <pre className="flex-1 overflow-auto p-4 bg-slate-950 text-[11px] text-slate-200 font-mono leading-relaxed whitespace-pre">
{generated.code}
                    </pre>
                    <div className="px-4 py-2 border-t border-slate-800 flex items-center justify-end gap-2">
                      <button
                        onClick={() => navigator.clipboard?.writeText(generated.code)}
                        className="text-[11px] px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700"
                      >
                        Kopyala
                      </button>
                      <button
                        onClick={() => {
                          const ext = FORMATS.find((f) => f.key === generated.format)?.ext ?? ".txt";
                          downloadText(generated.code, `${selected.name}_${generated.format}${ext}`);
                        }}
                        className="text-[11px] px-2.5 py-1 rounded-md bg-emerald-500 text-white font-medium hover:bg-emerald-400"
                      >
                        ↓ İndir
                      </button>
                    </div>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function StartRecordingDialog({
  onClose,
  onStarted,
}: {
  onClose: () => void;
  onStarted: () => void;
}) {
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("default");
  const [baseUrl, setBaseUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<StartResponse | null>(null);

  const start = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const res = await engineProxy<StartResponse>("/api/recorder/start", {
        method: "POST",
        json: { name: name.trim(), domain: domain.trim() || "default", base_url: baseUrl.trim() },
      });
      setResult(res);
    } catch (err) {
      setResult({ ok: false, error: err instanceof EngineError ? err.message : "Engine'e ulaşılamadı" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-white">Yeni Kayıt Oturumu</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">×</button>
        </div>

        {result?.ok ? (
          <div className="space-y-4">
            <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 p-4">
              <div className="text-sm text-emerald-300 font-semibold mb-2">✓ Oturum başlatıldı</div>
              <div className="font-mono text-xs text-slate-300">
                <div>Session ID: <span className="text-emerald-400">{result.session_id}</span></div>
                <div>Name: {result.name}</div>
                <div>Domain: {result.domain}</div>
              </div>
              <p className="text-[11px] text-slate-400 mt-3 leading-relaxed">
                Bu session ID'yi kopyala. Tarayıcı eklentinden veya CLI'dan aksiyon göndermek için kullan.
                Bittiğinde "Stop" çağrısı yap.
              </p>
            </div>
            <button
              onClick={onStarted}
              className="w-full px-4 py-2 rounded-lg bg-emerald-500 text-white text-sm font-semibold hover:bg-emerald-400"
            >
              Tamam
            </button>
          </div>
        ) : (
          <>
            <div className="space-y-3 mb-4">
              <div>
                <label className="text-[11px] text-slate-400 uppercase tracking-wide block mb-1">Oturum Adı *</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Örn: Checkout Flow Test"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-rose-500/50"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-400 uppercase tracking-wide block mb-1">Domain</label>
                <input
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder="default"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-rose-500/50"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-400 uppercase tracking-wide block mb-1">Base URL</label>
                <input
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://example.com"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-rose-500/50"
                />
              </div>
            </div>

            {result?.error && (
              <div className="text-xs text-rose-400 mb-3">⚠ {result.error}</div>
            )}

            <div className="flex items-center justify-end gap-2">
              <button
                onClick={onClose}
                className="px-3 py-1.5 rounded-lg text-sm text-slate-300 hover:bg-slate-800"
              >
                İptal
              </button>
              <button
                onClick={() => void start()}
                disabled={!name.trim() || busy}
                className="px-4 py-1.5 rounded-lg bg-gradient-to-r from-rose-500 to-pink-600 text-white text-sm font-semibold hover:opacity-90 disabled:opacity-40"
              >
                {busy ? "Başlatılıyor…" : "Başlat"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
