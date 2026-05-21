"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { nexusCodeStream, type NexusCodeInput } from "@/lib/ai-gateway";
import * as XLSX from "xlsx";

type Mode = "code" | "web" | "bitbucket";
type Domain = "banking" | "finance" | "general";
type Status = "idle" | "fetching" | "running" | "done" | "error";

const DOMAIN_OPTIONS: { value: Domain; label: string; color: string }[] = [
  { value: "banking", label: "Bankacılık", color: "border-sky-400/40 bg-sky-500/15 text-sky-100" },
  { value: "finance", label: "Finans", color: "border-emerald-400/40 bg-emerald-500/15 text-emerald-100" },
  { value: "general", label: "Genel", color: "border-slate-500/40 bg-slate-500/15 text-slate-200" },
];

const MODE_META: Record<Mode, { label: string; icon: string; desc: string }> = {
  code: { label: "Kod Analizi", icon: "</>", desc: "Yapıştır & analiz et" },
  web: { label: "Web Analizi", icon: "⊕", desc: "URL veya sayfa açıkla" },
  bitbucket: { label: "Bitbucket", icon: "⑃", desc: "Private repo'dan çek" },
};

const QUICK_SUGGESTIONS: { label: string; icon: string; prompt: string }[] = [
  {
    label: "Sayfa Yapısı Analizi",
    icon: "🏗",
    prompt: "Sadece SAYFA / KOD YAPISI ANALİZİ bölümünü üret: bileşen hiyerarşisi, input tipleri, aksiyonlar, loading/error state, responsive yapı ve UI/UX dikkat noktaları.",
  },
  {
    label: "İçerik Envanteri",
    icon: "📋",
    prompt: "Sadece İÇERİK ENVANTERİ bölümünü üret: başlıklar, buton metinleri, placeholder, hata/başarı mesajları, tablo kolonları ve yetki mesajları.",
  },
  {
    label: "Kod Analizi",
    icon: "</>",
    prompt: "Sadece KOD ANALİZİ bölümünü üret: teknoloji stack, API çağrıları, validasyon noktaları, auth/rol kontrolleri, state yönetimi ve riskli alanlar.",
  },
  {
    label: "Kullanıcı Akışları",
    icon: "🔀",
    prompt: "Sadece KULLANICI AKIŞLARI bölümünü üret: giriş/çıkış, listeleme, CRUD, dosya işlemleri, onay/red ve hata akışları.",
  },
  {
    label: "Manuel Test Senaryoları",
    icon: "🧪",
    prompt: "Sadece MANUEL TEST SENARYOLARI bölümünü üret. Pozitif, negatif, boundary, validasyon, yetki ve hata senaryolarını TC-XXX formatında tam olarak listele.",
  },
  {
    label: "Bug Tahminleri",
    icon: "🐛",
    prompt: "Sadece BUG TAHMİNİ bölümünü üret: edge case hataları, validasyon açıkları, yetki bypass riskleri, performans riskleri, veri tutarsızlığı ve bankacılık bağlamı riskleri.",
  },
  {
    label: "Otomasyon Önerileri",
    icon: "🤖",
    prompt: "Sadece OTOMASYON ÖNERİSİ bölümünü üret: her kritik senaryo için araç seçimi (Playwright/Cypress/Selenium/Karate), gerekçe ve örnek test kodu.",
  },
  {
    label: "Özet & Aksiyon",
    icon: "📊",
    prompt: "Sadece ÇIKTI ÖZETİ bölümünü üret: toplam senaryo sayısı, yüksek riskli alanlar, smoke test seti (3-5 senaryo), otomasyon öncelik sırası ve QA aksiyon listesi.",
  },
];

const CODE_PLACEHOLDER = `// Analiz etmek istediğiniz kodu yapıştırın
// Örnek: React component, API servisi, route, validation...

export function TransferForm() {
  // ...
}`;

const WEB_PLACEHOLDER = `URL: https://uygulama.example.com/transfer
Sayfa: Para transferi formu
Rol: Yetkili kullanıcı (bireysel bankacılık)
Açıklama: Hesaplar arası EFT / havale işlemi yapılan sayfa.
Form alanları: IBAN, tutar, açıklama, tarih seçici.
Butonlar: Gönder, İptal.`;

function parseBitbucketUrl(raw: string): { workspace: string; repo: string; branch: string; path: string } | null {
  try {
    const url = new URL(raw.trim());
    if (!url.hostname.includes("bitbucket.org")) return null;
    const parts = url.pathname.replace(/^\//, "").split("/");
    if (parts.length < 2) return null;
    const workspace = parts[0];
    const repo = parts[1];
    const branch = parts[4] ?? "main";
    const path = parts.slice(5).join("/") ?? "";
    return { workspace, repo, branch, path };
  } catch {
    return null;
  }
}

async function fetchBitbucketContent(
  workspace: string,
  repo: string,
  branch: string,
  path: string,
  username: string,
  appPassword: string
): Promise<string> {
  const base = `https://api.bitbucket.org/2.0/repositories/${encodeURIComponent(workspace)}/${encodeURIComponent(repo)}`;
  const srcPath = path ? `${branch}/${path}` : branch;
  const url = `${base}/src/${srcPath}`;
  const auth = btoa(`${username}:${appPassword}`);

  const res = await fetch(url, {
    headers: { Authorization: `Basic ${auth}` },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Bitbucket API hatası (${res.status}): ${text.slice(0, 200)}`);
  }

  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const json = await res.json() as { values?: Array<{ path: string; type: string }> };
    if (json.values) {
      const listing = json.values
        .map((f) => `${f.type === "commit_directory" ? "📁" : "📄"} ${f.path}`)
        .join("\n");
      return `Repo: ${workspace}/${repo} (${branch})\nDizin: /${path || "kök"}\n\n${listing}`;
    }
  }

  return res.text();
}

// ── History ──────────────────────────────────────────────────────────────────
const HISTORY_KEY = "nexus_code_history";
const HISTORY_MAX = 20;

interface HistoryEntry {
  id: string;
  title: string;
  timestamp: string;
  output: string;
  mode: Mode;
  domain: Domain;
}

function loadHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]");
  } catch { return []; }
}

function saveHistory(entry: HistoryEntry) {
  const history = loadHistory().filter((e) => e.id !== entry.id);
  history.unshift(entry);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, HISTORY_MAX)));
}

export default function NexusCodePage() {
  const [mode, setMode] = useState<Mode>("code");
  const [domain, setDomain] = useState<Domain>("banking");
  const [content, setContent] = useState("");
  const [extraContext, setExtraContext] = useState("");
  const [showExtra, setShowExtra] = useState(false);
  const [output, setOutput] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => { setHistory(loadHistory()); }, []);

  // Bitbucket state
  const [bbUrl, setBbUrl] = useState("");
  const [bbWorkspace, setBbWorkspace] = useState("");
  const [bbRepo, setBbRepo] = useState("");
  const [bbBranch, setBbBranch] = useState("main");
  const [bbPath, setBbPath] = useState("");
  const [bbUsername, setBbUsername] = useState("");
  const [bbPassword, setBbPassword] = useState("");
  const [bbFetched, setBbFetched] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  const handleUrlParse = (raw: string) => {
    setBbUrl(raw);
    const parsed = parseBitbucketUrl(raw);
    if (parsed) {
      setBbWorkspace(parsed.workspace);
      setBbRepo(parsed.repo);
      setBbBranch(parsed.branch);
      setBbPath(parsed.path);
    }
  };

  const fetchFromBitbucket = useCallback(async () => {
    if (!bbUsername || !bbPassword || !bbWorkspace || !bbRepo) return;
    setStatus("fetching");
    setError(null);
    setBbFetched(false);
    try {
      const text = await fetchBitbucketContent(bbWorkspace, bbRepo, bbBranch, bbPath, bbUsername, bbPassword);
      setContent(text);
      setBbFetched(true);
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [bbUsername, bbPassword, bbWorkspace, bbRepo, bbBranch, bbPath]);

  const startAnalysis = useCallback(async () => {
    if (!content.trim()) return;
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setStatus("running");
    setError(null);
    setOutput("");

    const input: NexusCodeInput = {
      mode: mode === "bitbucket" ? "code" : mode,
      content: content.trim(),
      domain,
      extraContext: extraContext.trim() || undefined,
    };

    try {
      await nexusCodeStream(
        input,
        (token, done) => {
          if (done) {
            setStatus("done");
            setOutput((finalOut) => {
              if (finalOut.trim()) {
                const entry: HistoryEntry = {
                  id: Date.now().toString(),
                  title: content.trim().slice(0, 80).replace(/\n/g, " ") || "Adsız Analiz",
                  timestamp: new Date().toISOString(),
                  output: finalOut,
                  mode,
                  domain,
                };
                saveHistory(entry);
                setHistory(loadHistory());
              }
              return finalOut;
            });
            return;
          }
          setOutput((prev) => {
            const next = prev + token;
            requestAnimationFrame(() => {
              outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight, behavior: "smooth" });
            });
            return next;
          });
        },
        abortRef.current.signal
      );
    } catch (err: unknown) {
      if ((err as { name?: string }).name === "AbortError") return;
      setStatus("error");
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [content, domain, extraContext, mode]);

  const stopAnalysis = () => { abortRef.current?.abort(); setStatus("idle"); };
  const copyOutput = () => { navigator.clipboard.writeText(output).catch(() => null); };

  const exportExcel = useCallback(() => {
    if (!output) return;

    // Test senaryolarını parse et — "Test ID:" ile başlayan bloklar
    const blocks = output.split(/(?=\*\*Test ID:|Test ID:)/g).filter((b) => b.trim());
    type Row = Record<string, string>;
    const rows: Row[] = [];

    for (const block of blocks) {
      const get = (label: string) => {
        const re = new RegExp(`(?:\\*\\*)?${label}(?:\\*\\*)?:?\\s*(.+?)(?=\\n(?:\\*\\*)?[A-ZÇĞİÖŞÜa-zçğışöü ]+(?:\\*\\*)?:|$)`, "s");
        const m = block.match(re);
        return m ? m[1].trim().replace(/\n/g, " ") : "";
      };

      // Adımları özel al — numaralı liste
      const stepsMatch = block.match(/(?:\*\*)?Adımlar(?:\*\*)?:?\s*([\s\S]*?)(?=\n(?:\*\*)?Beklenen|$)/);
      const steps = stepsMatch ? stepsMatch[1].trim().replace(/\n/g, " | ") : "";

      rows.push({
        "Test ID": get("Test ID"),
        "Modül": get("Modül"),
        "Sayfa": get("Sayfa"),
        "Senaryo": get("Senaryo"),
        "Ön Koşul": get("Ön Koşul"),
        "Test Verisi": get("Test Verisi"),
        "Adımlar": steps || get("Adımlar"),
        "Beklenen Sonuç": get("Beklenen Sonuç"),
        "Öncelik": get("Öncelik"),
        "Test Tipi": get("Test Tipi"),
        "Otomasyon Adayı": get("Otomasyon Adayı"),
        "Önerilen Araç": get("Önerilen Araç"),
        "Bug Riski": get("Bug Riski"),
        "Not": get("Not"),
      });
    }

    // Senaryo parse edilemezse tüm çıktıyı tek sütunda yaz
    const sheetData = rows.length > 0 && rows[0]["Test ID"]
      ? rows
      : [{ "Analiz Çıktısı": output }];

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(sheetData);

    // Sütun genişlikleri
    ws["!cols"] = Object.keys(sheetData[0]).map((k) =>
      k === "Adımlar" || k === "Senaryo" || k === "Analiz Çıktısı"
        ? { wch: 60 }
        : { wch: 22 }
    );

    XLSX.utils.book_append_sheet(wb, ws, "Test Senaryoları");
    const timestamp = new Date().toISOString().slice(0, 16).replace("T", "_").replace(":", "-");
    XLSX.writeFile(wb, `nexus-code-analiz-${timestamp}.xlsx`);
  }, [output]);

  const exportMarkdown = useCallback(() => {
    if (!output) return;
    const blob = new Blob([output], { type: "text/markdown; charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const ts = new Date().toISOString().slice(0, 16).replace("T", "_").replace(":", "-");
    a.download = `nexus-analiz-${ts}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [output]);

  const restoreFromHistory = (entry: HistoryEntry) => {
    setOutput(entry.output);
    setMode(entry.mode);
    setDomain(entry.domain);
    setStatus("done");
    setShowHistory(false);
  };

  const clearAll = () => {
    abortRef.current?.abort();
    setOutput(""); setContent(""); setExtraContext("");
    setBbFetched(false); setStatus("idle"); setError(null);
  };

  const isRunning = status === "running";
  const isFetching = status === "fetching";
  const hasOutput = output.length > 0;
  const canAnalyze = content.trim().length > 0 && !isRunning && !isFetching;

  return (
    <div className="flex min-h-screen flex-col bg-[radial-gradient(ellipse_at_top,#1e1b4b_0%,#020617_50%)] text-white">

      {/* ── Hero Header ─────────────────────────────────────────── */}
      <div className="relative overflow-hidden border-b border-slate-800/70 bg-slate-950/60 px-6 py-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(139,92,246,0.12)_0%,transparent_60%)]" />
        <div className="mx-auto max-w-screen-2xl">
          <div className="flex flex-wrap items-center justify-between gap-6">
            <div className="flex items-center gap-5">
              <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border border-violet-400/30 bg-gradient-to-br from-violet-600/30 to-violet-900/30 shadow-[0_0_40px_rgba(139,92,246,0.25)]">
                <span className="text-xl font-black tracking-tight text-violet-100">N</span>
                <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full border-2 border-slate-950 bg-emerald-400" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl font-black tracking-tight text-white">Neurex Code</h1>
                  <span className="rounded-full border border-violet-400/20 bg-violet-500/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-violet-300">Beta</span>
                </div>
                <p className="mt-0.5 text-sm text-slate-400">Senior QA · Automation Architect · Product Analyst — Lokal Ollama</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-900/60 px-3 py-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                <span className="text-xs text-slate-300">qwen2.5-coder · local</span>
              </div>
              <div className="flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-900/60 px-3 py-1.5">
                <span className="h-2 w-2 rounded-full bg-violet-400" />
                <span className="text-xs text-slate-300">Ollama bağlı</span>
              </div>
            </div>
          </div>

          {/* Mod seçici — header içinde */}
          <div className="mt-6 flex flex-wrap gap-2">
            {(Object.keys(MODE_META) as Mode[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => { setMode(m); if (m !== "bitbucket") setContent(""); setBbFetched(false); }}
                className={`flex items-center gap-2 rounded-xl border px-5 py-2.5 text-sm font-semibold transition ${
                  mode === m
                    ? "border-violet-300/50 bg-violet-500/20 text-violet-50 shadow-[0_0_20px_rgba(139,92,246,0.2)]"
                    : "border-slate-700/80 bg-slate-900/40 text-slate-400 hover:border-slate-600 hover:bg-slate-900/70 hover:text-slate-200"
                }`}
              >
                <span className="font-mono text-base">{MODE_META[m].icon}</span>
                <span>{MODE_META[m].label}</span>
                <span className={`text-[10px] font-normal ${mode === m ? "text-violet-300" : "text-slate-600"}`}>
                  {MODE_META[m].desc}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Ana İçerik ───────────────────────────────────────────── */}
      <div className="mx-auto flex w-full max-w-screen-2xl flex-1 flex-col gap-6 px-6 py-8 lg:flex-row lg:items-start">

        {/* Sol panel */}
        <div className="flex flex-col gap-4 lg:w-[480px] lg:shrink-0">

          {/* Domain */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Domain / Perspektif</p>
            <div className="flex flex-wrap gap-2">
              {DOMAIN_OPTIONS.map((d) => (
                <button
                  key={d.value}
                  type="button"
                  onClick={() => setDomain(d.value)}
                  className={`rounded-full border px-4 py-1.5 text-xs font-semibold transition ${
                    domain === d.value ? d.color : "border-slate-700 bg-slate-900/40 text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          {/* Kod / Web input */}
          {(mode === "code" || mode === "web") && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                {mode === "code" ? "Kaynak Kod" : "URL / Sayfa Açıklaması"}
              </p>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder={mode === "code" ? CODE_PLACEHOLDER : WEB_PLACEHOLDER}
                rows={16}
                className="w-full resize-none rounded-xl border border-slate-700/80 bg-slate-950/70 px-4 py-3 font-mono text-xs leading-6 text-slate-200 placeholder-slate-700 outline-none transition focus:border-violet-500/60 focus:ring-2 focus:ring-violet-500/10"
              />
              <div className="mt-2 flex justify-between">
                <span className="text-[10px] text-slate-700">
                  {mode === "code" ? "React, Vue, Angular, API, Java, Python..." : "URL + sayfa açıklaması yeterli"}
                </span>
                <span className="text-[10px] text-slate-600">{content.length.toLocaleString("tr")} karakter</span>
              </div>
            </div>
          )}

          {/* Bitbucket panel */}
          {mode === "bitbucket" && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
              <div className="mb-4 flex items-center gap-2">
                <span className="font-mono text-lg text-slate-400">⑃</span>
                <p className="text-sm font-semibold text-slate-200">Bitbucket Bağlantısı</p>
                {bbFetched && (
                  <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
                    Dosya yüklendi
                  </span>
                )}
              </div>

              <div className="flex flex-col gap-3">
                <div>
                  <label className="mb-1.5 block text-[11px] font-medium text-slate-500">
                    Bitbucket URL <span className="text-slate-600">(otomatik parse edilir)</span>
                  </label>
                  <input
                    type="url"
                    value={bbUrl}
                    onChange={(e) => handleUrlParse(e.target.value)}
                    placeholder="https://bitbucket.org/workspace/repo/src/main/src/components"
                    className="w-full rounded-xl border border-slate-700/80 bg-slate-950/70 px-4 py-2.5 text-xs text-slate-200 placeholder-slate-700 outline-none focus:border-violet-500/60"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1.5 block text-[11px] font-medium text-slate-500">Workspace</label>
                    <input
                      value={bbWorkspace}
                      onChange={(e) => setBbWorkspace(e.target.value)}
                      placeholder="my-workspace"
                      className="w-full rounded-xl border border-slate-700/80 bg-slate-950/70 px-3 py-2.5 text-xs text-slate-200 placeholder-slate-700 outline-none focus:border-violet-500/60"
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-[11px] font-medium text-slate-500">Repository</label>
                    <input
                      value={bbRepo}
                      onChange={(e) => setBbRepo(e.target.value)}
                      placeholder="repo-adi"
                      className="w-full rounded-xl border border-slate-700/80 bg-slate-950/70 px-3 py-2.5 text-xs text-slate-200 placeholder-slate-700 outline-none focus:border-violet-500/60"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1.5 block text-[11px] font-medium text-slate-500">Branch</label>
                    <input
                      value={bbBranch}
                      onChange={(e) => setBbBranch(e.target.value)}
                      placeholder="main"
                      className="w-full rounded-xl border border-slate-700/80 bg-slate-950/70 px-3 py-2.5 text-xs text-slate-200 placeholder-slate-700 outline-none focus:border-violet-500/60"
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-[11px] font-medium text-slate-500">
                      Dosya Yolu <span className="text-slate-700">(boş = kök)</span>
                    </label>
                    <input
                      value={bbPath}
                      onChange={(e) => setBbPath(e.target.value)}
                      placeholder="src/components/Form.tsx"
                      className="w-full rounded-xl border border-slate-700/80 bg-slate-950/70 px-3 py-2.5 text-xs text-slate-200 placeholder-slate-700 outline-none focus:border-violet-500/60"
                    />
                  </div>
                </div>

                <div className="rounded-xl border border-amber-400/10 bg-amber-500/5 p-3">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-amber-400/70">
                    Kimlik Doğrulama — saklanmaz
                  </p>
                  <div className="flex flex-col gap-2">
                    <input
                      value={bbUsername}
                      onChange={(e) => setBbUsername(e.target.value)}
                      placeholder="Bitbucket kullanıcı adı"
                      className="w-full rounded-lg border border-slate-700/60 bg-slate-950/70 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-amber-500/40"
                    />
                    <input
                      type="password"
                      value={bbPassword}
                      onChange={(e) => setBbPassword(e.target.value)}
                      placeholder="App Password (Settings → App Passwords)"
                      className="w-full rounded-lg border border-slate-700/60 bg-slate-950/70 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-amber-500/40"
                    />
                  </div>
                </div>

                <button
                  type="button"
                  onClick={fetchFromBitbucket}
                  disabled={!bbUsername || !bbPassword || !bbWorkspace || !bbRepo || isFetching}
                  className="w-full rounded-xl border border-sky-400/20 bg-sky-500/10 px-4 py-3 text-sm font-semibold text-sky-100 transition hover:bg-sky-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {isFetching ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-sky-400/30 border-t-sky-300" />
                      Bitbucket'tan çekiliyor...
                    </span>
                  ) : bbFetched ? "Tekrar Çek" : "Dosyaları Getir"}
                </button>

                {bbFetched && content && (
                  <div className="rounded-xl border border-slate-700/60 bg-slate-950/60 p-3">
                    <p className="mb-1 text-[10px] font-semibold text-slate-500">Yüklenen içerik önizleme</p>
                    <pre className="max-h-32 overflow-y-auto text-[10px] leading-5 text-slate-400">
                      {content.slice(0, 600)}{content.length > 600 ? "\n..." : ""}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Ek Bağlam */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
            <button
              type="button"
              onClick={() => setShowExtra((v) => !v)}
              className="flex w-full items-center justify-between text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 hover:text-slate-300 transition"
            >
              <span>Ek Bağlam / İş Kuralları</span>
              <span>{showExtra ? "▲" : "▼"}</span>
            </button>
            {showExtra && (
              <textarea
                value={extraContext}
                onChange={(e) => setExtraContext(e.target.value)}
                placeholder="Rol tanımları, yetki seviyeleri, iş kuralları, limit değerleri, KVKK kısıtlamaları..."
                rows={5}
                className="mt-3 w-full resize-none rounded-xl border border-slate-700/80 bg-slate-950/70 px-4 py-3 text-xs leading-6 text-slate-200 placeholder-slate-700 outline-none focus:border-violet-500/60"
              />
            )}
          </div>

          {/* Aksiyon */}
          <div className="flex gap-2">
            {isRunning ? (
              <button
                type="button"
                onClick={stopAnalysis}
                className="flex-1 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3.5 text-sm font-semibold text-red-200 transition hover:bg-red-500/20"
              >
                ■ Durdur
              </button>
            ) : (
              <button
                type="button"
                onClick={startAnalysis}
                disabled={!canAnalyze}
                className="flex-1 rounded-xl border border-violet-300/40 bg-gradient-to-r from-violet-600/20 to-violet-500/10 px-4 py-3.5 text-sm font-semibold text-violet-50 shadow-[0_0_20px_rgba(139,92,246,0.15)] transition hover:from-violet-600/30 hover:to-violet-500/20 disabled:cursor-not-allowed disabled:opacity-40"
              >
                ▶ Analizi Başlat
              </button>
            )}
            {(hasOutput || content) && (
              <button
                type="button"
                onClick={clearAll}
                className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3.5 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-slate-200"
              >
                Temizle
              </button>
            )}
          </div>

          {error && (
            <div className="rounded-2xl border border-red-400/20 bg-red-500/8 p-4">
              <p className="text-xs font-semibold text-red-300">Hata</p>
              <p className="mt-1 text-xs leading-5 text-red-400">{error}</p>
            </div>
          )}
        </div>

        {/* Sağ panel — Output */}
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <p className="text-base font-bold text-slate-100">Analiz Çıktısı</p>
              {isRunning && (
                <span className="flex items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-semibold text-emerald-300">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
                  Üretiyor
                </span>
              )}
              {status === "done" && (
                <span className="rounded-full border border-sky-400/20 bg-sky-500/10 px-2.5 py-0.5 text-[10px] font-semibold text-sky-300">
                  ✓ Tamamlandı
                </span>
              )}
            </div>
            <div className="flex gap-2 items-center">
              {history.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowHistory((v) => !v)}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-1.5 text-xs font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
                >
                  🕐 Geçmiş ({history.length})
                </button>
              )}
              {hasOutput && (
                <>
                  <button
                    type="button"
                    onClick={exportMarkdown}
                    className="flex items-center gap-1.5 rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-1.5 text-xs font-semibold text-violet-200 transition hover:bg-violet-500/20"
                  >
                    ↓ .md
                  </button>
                  <button
                    type="button"
                    onClick={exportExcel}
                    className="flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-500/20"
                  >
                    ↓ Excel
                  </button>
                  <button
                    type="button"
                    onClick={copyOutput}
                    className="rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-slate-500 hover:text-white"
                  >
                    Kopyala
                  </button>
                </>
              )}
            </div>
          </div>

          {/* History panel */}
          {showHistory && history.length > 0 && (
            <div className="rounded-2xl border border-slate-700 bg-slate-900/80 overflow-hidden">
              <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
                <p className="text-xs font-semibold text-slate-400">Analiz Geçmişi</p>
                <button onClick={() => setShowHistory(false)} className="text-slate-600 hover:text-slate-400 text-xs">✕ Kapat</button>
              </div>
              <div className="max-h-60 overflow-y-auto divide-y divide-slate-800">
                {history.map((entry) => (
                  <button
                    key={entry.id}
                    type="button"
                    onClick={() => restoreFromHistory(entry)}
                    className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-slate-800/60 transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium text-white">{entry.title}</p>
                      <div className="mt-0.5 flex gap-2 text-[10px] text-slate-500">
                        <span className="capitalize">{entry.mode}</span>
                        <span>·</span>
                        <span>{entry.domain}</span>
                        <span>·</span>
                        <span>{new Date(entry.timestamp).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
                      </div>
                    </div>
                    <span className="shrink-0 text-[10px] text-violet-400">Geri Yükle →</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div
            ref={outputRef}
            className="relative flex-1 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900/40 p-6"
            style={{ minHeight: "calc(100vh - 320px)" }}
          >
            {!hasOutput && !isRunning && (
              <div className="flex h-full flex-col items-center justify-center gap-6 py-20 text-center">
                <div className="relative flex h-20 w-20 items-center justify-center rounded-3xl border border-violet-400/20 bg-gradient-to-br from-violet-600/20 to-violet-900/20 shadow-[0_0_60px_rgba(139,92,246,0.15)]">
                  <span className="text-3xl font-black text-violet-200">N</span>
                </div>
                <div>
                  <p className="text-lg font-bold text-slate-200">Neurex Code hazır</p>
                  <p className="mt-1.5 text-sm text-slate-500">
                    {mode === "code" && "Kodu yapıştırın ve analizi başlatın."}
                    {mode === "web" && "URL ve sayfa açıklamasını girin."}
                    {mode === "bitbucket" && "Bitbucket bağlantısını yapılandırın ve dosyaları getirin."}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2.5 text-xs sm:grid-cols-4">
                  {QUICK_SUGGESTIONS.map((s) => (
                    <button
                      key={s.label}
                      type="button"
                      onClick={() => {
                        setExtraContext(s.prompt);
                        setShowExtra(true);
                      }}
                      className="flex flex-col items-start gap-1.5 rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-left transition hover:border-violet-500/40 hover:bg-violet-500/8 hover:text-violet-200 text-slate-500"
                    >
                      <span className="text-base leading-none">{s.icon}</span>
                      <span className="leading-snug">{s.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {!hasOutput && isRunning && (
              <div className="flex h-full flex-col items-center justify-center gap-4 py-20">
                <div className="h-10 w-10 animate-spin rounded-full border-2 border-violet-500/30 border-t-violet-400" />
                <p className="text-sm text-slate-400">Analiz başlatılıyor...</p>
                <p className="text-xs text-slate-600">qwen2.5-coder model üretiyor</p>
              </div>
            )}

            {hasOutput && (
              <pre className="whitespace-pre-wrap font-mono text-xs leading-6 text-slate-200">
                {output}
                {isRunning && (
                  <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-pulse bg-violet-400" />
                )}
              </pre>
            )}
          </div>

          {hasOutput && (
            <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-2 text-[11px] text-slate-500">
              <span>{output.length.toLocaleString("tr")} karakter üretildi</span>
              <span>
                {DOMAIN_OPTIONS.find((d) => d.value === domain)?.label} perspektifi ·{" "}
                {mode === "bitbucket" ? "Bitbucket repo analizi" : mode === "code" ? "Kod analizi" : "Web analizi"}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
