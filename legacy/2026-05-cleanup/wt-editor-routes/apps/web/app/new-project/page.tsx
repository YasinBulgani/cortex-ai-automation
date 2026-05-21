"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { DocumentUploader, type UploadedDocument } from "@/components/DocumentUploader";
import {
  DEFAULT_PRODUCT_FAMILY_ID,
  PRODUCT_FAMILY,
  PRODUCT_FAMILY_STORAGE_KEY,
  getProductFamilyMember,
  type ProductFamilyId,
} from "@/lib/product";

// ── Types ────────────────────────────────────────────────────────────────────

type ManualTest = {
  title: string;
  steps: { action: string; expected: string }[];
};

type BddScenario = {
  title: string;
  description?: string;
  gherkin?: string;
  tags?: string[];
  steps?: { keyword: string; text: string }[];
};

type RegSet = {
  name: string;
  description: string;
  scenario_ids: string[];
  priority: "critical" | "high" | "medium" | "low";
};

type SavedScenario = { id: string; title: string; status: string };

type AutomationFile = { name: string; content: string; scenario_title?: string };
type LocatorEntry = { key: string; type: string; value: string };
type LocatorFile = { name: string; module: string; locators: LocatorEntry[] };
type MaviyakaFeature = { title: string; content: string };

// IDE için dosya tipi (IntelliJ benzeri proje ağacı)
type IdeFileKind = "feature" | "steps" | "data" | "locator" | "config" | "page";
type IdeFile = {
  path: string;
  name: string;
  folder: string;
  kind: IdeFileKind;
  content: string;
  language: "gherkin" | "typescript" | "python" | "json" | "yaml";
};

// ── Step tanımları ───────────────────────────────────────────────────────────

const STEPS = [
  { id: 1, label: "Proje Oluştur",      icon: "🎯", desc: "Ad ve açıklama gir" },
  { id: 2, label: "DB Bağlantısı",       icon: "🗄️",  desc: "Veri tabanı bağlan" },
  { id: 3, label: "Analiz Dokümanı",     icon: "📄", desc: "Doküman yükle & AI analiz" },
  { id: 4, label: "Manuel Testler",      icon: "📋", desc: "Üretilen testleri kaydet" },
  { id: 5, label: "Regresyon Seti",      icon: "🔁", desc: "AI önerilerini onayla" },
  { id: 6, label: "Otomasyon Seç",       icon: "☑️",  desc: "Otomasyona alınacakları seç" },
  { id: 7, label: "Otomasyon Kurulumu",  icon: "🚀", desc: "Lokator & Feature üret" },
  { id: 8, label: "Otomasyon IDE",       icon: "💻", desc: "Kod editörü & test koşumu" },
  { id: 9, label: "Tamamlandı",          icon: "✅", desc: "Projen hazır!" },
];

const PRIORITY_COLOR: Record<string, string> = {
  critical: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  high:     "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  medium:   "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  low:      "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

const PRODUCT_AVAILABILITY_META = {
  core: { label: "Core", className: "border-sky-400/20 bg-sky-500/10 text-sky-200" },
  active: { label: "Active", className: "border-emerald-400/20 bg-emerald-500/10 text-emerald-200" },
  beta: { label: "Beta", className: "border-amber-400/20 bg-amber-500/10 text-amber-200" },
  embedded: { label: "Embedded", className: "border-violet-400/20 bg-violet-500/10 text-violet-200" },
} as const;

const PRODUCT_FLOW_GUIDE: Record<ProductFamilyId, { title: string; description: string; recommendedPath: string }> = {
  one: {
    title: "Platform cekirdegini kur",
    description: "Ortam, entegrasyon ve ortak proje omurgasini oturtup ekibin geri kalan akislarini besle.",
    recommendedPath: "settings",
  },
  studio: {
    title: "Tasarim ve yonetisimi one al",
    description: "Dokuman, gereksinim, kapsam ve onay akislarini merkezi sekilde yonet.",
    recommendedPath: "requirements",
  },
  service: {
    title: "Servis kalitesine hizli gir",
    description: "Spec import, assertion, chain orchestration ve servis kosularina agirlik ver.",
    recommendedPath: "api-testing",
  },
  web: {
    title: "Web otomasyonunu hizlandir",
    description: "Dokumandan otomasyon, locator, page object ve execution hattini one cikar.",
    recommendedPath: "automation-gen",
  },
  mobile: {
    title: "Mobil kalite hattini ac",
    description: "Cihaz matrisi, paralel run ve artifact akisini projeyle birlikte hazirla.",
    recommendedPath: "mobile",
  },
  data: {
    title: "Veri baglamiyla basla",
    description: "Sentetik veri, masking ve test verisi baglama adimlarini daha erken asamada guclendir.",
    recommendedPath: "test-data",
  },
  intelligence: {
    title: "AI kalite katmanini etkinlestir",
    description: "Copilot, kalite metrikleri ve yonlendirilmis AI akislarini proje merkezine yerlestir.",
    recommendedPath: "ai-chat",
  },
};

const PRODUCT_WIZARD_PROFILE: Record<
  ProductFamilyId,
  {
    analysisSeed: string;
    analysisFocus: string[];
    dbPriorityLabel: string;
    dbNote: string;
    automationPrimary: boolean;
    automationNote: string;
  }
> = {
  one: {
    analysisSeed: "Platform, entegrasyon, ortam ve yonetim tarafindaki riskleri de dikkate al.",
    analysisFocus: ["ortam baglamı", "entegrasyon riski", "platform akışları"],
    dbPriorityLabel: "Orta oncelik",
    dbNote: "Platform cekirdegi icin DB baglami faydali ama bu kurulumda zorunlu degil.",
    automationPrimary: false,
    automationNote: "Web otomasyonu bu ürün için ikincil. Asil hedef platform omurgasini hazirlamak.",
  },
  studio: {
    analysisSeed: "Requirement, coverage gap, approval ve regression planning acisindan daha derin dusun.",
    analysisFocus: ["requirement coverage", "onay kuyrugu", "regresyon planlama"],
    dbPriorityLabel: "Destekleyici",
    dbNote: "Studio odaginda asil değer dokuman ve senaryo tasariminda. DB baglantisi varsa analiz daha zengin olur.",
    automationPrimary: false,
    automationNote: "Studio odaginda web otomasyonu opsiyonel; tasarim ve yonetisim daha oncelikli.",
  },
  service: {
    analysisSeed: "API kontrati, auth, validation, negative path, rate limit ve edge-case senaryolarina agirlik ver.",
    analysisFocus: ["auth ve yetki", "negative servis senaryolari", "assertion ve contract riskleri"],
    dbPriorityLabel: "Yuksek oncelik",
    dbNote: "Servis kalite akislarinda DB baglami ve gercek veri iliskileri daha kritik olabilir.",
    automationPrimary: false,
    automationNote: "Bu wizardin sonundaki web otomasyon adimi servis urunu icin opsiyonel; asil hedef servis test kurgusu.",
  },
  web: {
    analysisSeed: "UI akislarini, locator bagimliliklarini, page object ihtiyaclarini ve E2E regresyonu one cikar.",
    analysisFocus: ["UI akislari", "locator bagimliliklari", "E2E regresyon"],
    dbPriorityLabel: "Orta oncelik",
    dbNote: "Web otomasyonunda DB baglami yardimci olabilir; ama asıl kritik kisim kullanici akislaridir.",
    automationPrimary: true,
    automationNote: "Bu urun odaginda web otomasyon adimlari ana akis olarak onerilir.",
  },
  mobile: {
    analysisSeed: "Mobil cihaz varyasyonlari, baglanti kosullari, cihaz matrisi ve artefact risklerine dikkat et.",
    analysisFocus: ["cihaz varyasyonlari", "ag kosullari", "mobil artefact riski"],
    dbPriorityLabel: "Destekleyici",
    dbNote: "Mobil kalitede veri baglami onemli olabilir ama cihaz ve run orkestrasyonu daha baskin olur.",
    automationPrimary: true,
    automationNote: "Mobil odakta da otomasyon kurulumu degerli; bu web tabanli adimlar hizli baslangic icin kullanilabilir.",
  },
  data: {
    analysisSeed: "Test verisi bagimliliklari, masking ihtiyaci, sentetik veri senaryolari ve privacy risklerini vurgula.",
    analysisFocus: ["test verisi ihtiyaci", "privacy ve masking", "sentetik veri akislari"],
    dbPriorityLabel: "Yuksek oncelik",
    dbNote: "Data odaginda DB iliskileri ve veri baglami genelde daha yuksek deger uretir.",
    automationPrimary: false,
    automationNote: "Bu urunde asil hedef veri ve privacy akislarini guclendirmek; web otomasyonu ikincil kalabilir.",
  },
  intelligence: {
    analysisSeed: "AI copilot, explanation quality, source grounding ve kalite metriklerini dusunen senaryolar da cikar.",
    analysisFocus: ["copilot yardimi", "source grounding", "kalite metrikleri"],
    dbPriorityLabel: "Opsiyonel",
    dbNote: "Intelligence odaginda DB baglantisi faydali olabilir ama temel deger AI yonlendirmesinden gelir.",
    automationPrimary: false,
    automationNote: "Visium Intelligence icin bu web otomasyon adimlari yardimci ama zorunlu degil.",
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function slugifyProjectName(name: string): string {
  const trimmed = (name || "").trim().toLowerCase();
  if (!trimmed) return "proje";
  const map: Record<string, string> = { ç: "c", ğ: "g", ı: "i", ö: "o", ş: "s", ü: "u" };
  return trimmed
    .split("")
    .map((ch) => map[ch] ?? ch)
    .join("")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 40) || "proje";
}

// ── MaviyakaFeatureViewer ─────────────────────────────────────────────────────
const GHERKIN_KW = ["Feature:", "Scenario:", "Background:", "Examples:", "Given", "When", "Then", "And", "But"];

function MaviyakaFeatureViewer({
  content,
  allLocators,
  onRedKeyClick,
}: {
  content: string;
  allLocators: LocatorEntry[];
  onRedKeyClick: (key: string) => void;
}) {
  const keySet = new Set(allLocators.map((l) => l.key));
  return (
    <pre className="rounded-lg bg-slate-950 p-4 text-xs font-mono whitespace-pre-wrap overflow-auto max-h-96 leading-5">
      {content.split("\n").map((line, li) => {
        const parts = line.split('"');
        return (
          <div key={li}>
            {parts.map((part, pi) => {
              if (pi % 2 === 0) {
                const trimmed = part.trimStart();
                for (const kw of GHERKIN_KW) {
                  if (trimmed.startsWith(kw)) {
                    const indent = part.slice(0, part.length - trimmed.length);
                    const after = trimmed.slice(kw.length);
                    return (
                      <span key={pi}>
                        <span className="text-slate-600">{indent}</span>
                        <span className="text-blue-400 font-semibold">{kw}</span>
                        <span className="text-slate-300">{after}</span>
                      </span>
                    );
                  }
                }
                return <span key={pi} className="text-slate-300">{part}</span>;
              }
              // quoted value
              if (keySet.has(part)) {
                return <span key={pi} className="text-emerald-400">&quot;{part}&quot;</span>;
              }
              return (
                <button
                  key={pi}
                  type="button"
                  onClick={() => onRedKeyClick(part)}
                  className="text-red-400 hover:text-red-300 underline underline-offset-2 cursor-pointer"
                  title={`"${part}" lokator bulunamadı — tıkla AI önerisi`}
                >
                  &quot;{part}&quot;
                </button>
              );
            })}
          </div>
        );
      })}
    </pre>
  );
}

// ── IDE Workbench (IntelliJ benzeri otomasyon IDE) ──────────────────────────

const FILE_ICON: Record<IdeFileKind, string> = {
  feature: "🥒",
  steps:   "📘",
  data:    "🗃️",
  locator: "🎯",
  page:    "📄",
  config:  "⚙️",
};

const FOLDER_LABEL: Record<string, string> = {
  features:    "features",
  steps:       "steps",
  "test-data": "test-data",
  locators:    "locators",
  pages:       "pages",
  config:      "config",
};

// Basit syntax highlight — dile göre satır boyar
function highlightLine(line: string, language: IdeFile["language"]): React.ReactNode {
  if (language === "gherkin") {
    for (const kw of ["Feature:", "Scenario:", "Background:", "Examples:", "Given", "When", "Then", "And", "But"]) {
      const trimmed = line.trimStart();
      if (trimmed.startsWith(kw)) {
        const indent = line.slice(0, line.length - trimmed.length);
        const rest = trimmed.slice(kw.length);
        return (
          <>
            <span className="text-slate-600">{indent}</span>
            <span className="text-sky-400 font-semibold">{kw}</span>
            <span className="text-slate-200">{rest.replace(/"([^"]*)"/g, (m) => m)}</span>
          </>
        );
      }
    }
    return <span className="text-slate-400">{line}</span>;
  }
  if (language === "json") {
    return <span className="text-slate-300">{line.replace(/"([^"]*)":/g, '"$1":')}</span>;
  }
  if (language === "typescript") {
    const ts = line
      .replace(/(\b)(import|from|export|const|let|var|function|async|await|return|class|new|this|if|else|for|of|in)(\b)/g, "§KW§$2§/KW§");
    const parts = ts.split(/§KW§|§\/KW§/);
    return (
      <>
        {parts.map((p, i) => (
          <span key={i} className={i % 2 === 1 ? "text-violet-400 font-semibold" : "text-slate-300"}>
            {p}
          </span>
        ))}
      </>
    );
  }
  return <span className="text-slate-300">{line}</span>;
}

function IdeWorkbench({
  projectName,
  projectSlug,
  environment,
  ideFiles,
  activeIdePath,
  setActiveIdePath,
  setIdeFiles,
  expandedFolders,
  toggleFolder,
  consoleLines,
  ideTab,
  setIdeTab,
  ideRunning,
  runFromIde,
  goBack,
  goFinish,
}: {
  projectName: string;
  projectSlug: string;
  environment: string;
  ideFiles: IdeFile[];
  activeIdePath: string | null;
  setActiveIdePath: (p: string | null) => void;
  setIdeFiles: React.Dispatch<React.SetStateAction<IdeFile[]>>;
  expandedFolders: Set<string>;
  toggleFolder: (f: string) => void;
  consoleLines: string[];
  ideTab: "console" | "problems" | "run";
  setIdeTab: (t: "console" | "problems" | "run") => void;
  ideRunning: boolean;
  runFromIde: () => void;
  goBack: () => void;
  goFinish: () => void;
}) {
  const grouped = ideFiles.reduce<Record<string, IdeFile[]>>((acc, f) => {
    (acc[f.folder] ||= []).push(f);
    return acc;
  }, {});
  const folderOrder = ["features", "steps", "test-data", "locators", "pages", "config"];
  const activeFile = ideFiles.find((f) => f.path === activeIdePath) || null;

  const [dirtyDraft, setDirtyDraft] = useState<string | null>(null);

  useEffect(() => {
    setDirtyDraft(activeFile?.content ?? null);
  }, [activeFile?.path]); // eslint-disable-line react-hooks/exhaustive-deps

  function saveDraft() {
    if (!activeFile || dirtyDraft === null) return;
    setIdeFiles((prev) =>
      prev.map((f) => (f.path === activeFile.path ? { ...f, content: dirtyDraft } : f))
    );
  }

  const problemCount = ideFiles.filter((f) => f.kind === "steps" && /TODO: implement/.test(f.content)).length;

  return (
    <div className="space-y-3">
      {/* Üst başlık */}
      <div>
        <h2 className="text-xl font-bold">💻 Otomasyon IDE — {projectName?.trim() || "Proje"}</h2>
        <p className="mt-1 text-sm text-slate-400">
          IntelliJ benzeri çalışma alanı. Feature, step definitions, test verisi, locator ve page object dosyaları
          otomatik üretildi. Dosyaları düzenle ve <span className="text-emerald-400 font-semibold">▶ Run</span> ile koştur.
        </p>
      </div>

      {/* IDE Çerçevesi */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-[#1e1f22] shadow-2xl">
        {/* Toolbar / titlebar */}
        <div className="flex items-center gap-2 border-b border-slate-800 bg-[#2b2d30] px-3 py-1.5">
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-red-500/80" />
            <span className="h-3 w-3 rounded-full bg-amber-400/80" />
            <span className="h-3 w-3 rounded-full bg-emerald-500/80" />
          </div>
          <div className="mx-3 flex items-center gap-1.5 rounded-md bg-[#1e1f22] px-2 py-0.5 text-[11px] text-slate-400">
            <span>📁</span>
            <span>bgts-automation</span>
            <span className="text-slate-600">›</span>
            <span className="text-slate-300">{projectSlug}</span>
            <span className="text-slate-600">·</span>
            <span className="text-amber-300">{environment}</span>
          </div>
          <div className="ml-auto flex items-center gap-1.5">
            <button
              type="button"
              onClick={runFromIde}
              disabled={ideRunning}
              className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-40"
            >
              {ideRunning ? (
                <>
                  <svg className="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Running
                </>
              ) : (
                <>▶ Run</>
              )}
            </button>
            <button
              type="button"
              onClick={saveDraft}
              disabled={!activeFile || dirtyDraft === activeFile?.content}
              className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] text-slate-300 transition hover:border-slate-600 hover:text-white disabled:opacity-40"
              title="Kaydet"
            >
              💾 Save
            </button>
          </div>
        </div>

        {/* Ana 3-paneli çerçeve */}
        <div className="grid min-h-[540px] grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)]">
          {/* Sol panel — Project tree */}
          <aside className="border-r border-slate-800 bg-[#242528]">
            <div className="flex items-center justify-between px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              <span>Project</span>
              <span className="text-slate-600">{ideFiles.length}</span>
            </div>
            <div className="max-h-[520px] overflow-y-auto px-1 pb-3 text-[12px]">
              {/* Root klasör */}
              <div className="flex items-center gap-1 px-2 py-1 text-slate-300">
                <span>📁</span>
                <span className="font-semibold">{projectSlug}</span>
              </div>
              {folderOrder
                .filter((folder) => grouped[folder]?.length)
                .map((folder) => {
                  const isOpen = expandedFolders.has(folder);
                  const files = grouped[folder];
                  return (
                    <div key={folder} className="ml-2">
                      <button
                        type="button"
                        onClick={() => toggleFolder(folder)}
                        className="flex w-full items-center gap-1 rounded px-1.5 py-0.5 text-left text-slate-400 transition hover:bg-slate-700/40 hover:text-white"
                      >
                        <span className="text-[9px] w-3">{isOpen ? "▾" : "▸"}</span>
                        <span>{isOpen ? "📂" : "📁"}</span>
                        <span>{FOLDER_LABEL[folder] || folder}</span>
                        <span className="ml-auto text-[9px] text-slate-600">{files.length}</span>
                      </button>
                      {isOpen && (
                        <ul className="ml-4 border-l border-slate-700/50">
                          {files.map((f) => {
                            const active = f.path === activeIdePath;
                            return (
                              <li key={f.path}>
                                <button
                                  type="button"
                                  onClick={() => setActiveIdePath(f.path)}
                                  className={`flex w-full items-center gap-1.5 rounded px-2 py-0.5 text-left transition
                                    ${active
                                      ? "bg-blue-500/20 text-blue-200"
                                      : "text-slate-400 hover:bg-slate-700/40 hover:text-white"}`}
                                >
                                  <span className="text-[12px]">{FILE_ICON[f.kind]}</span>
                                  <span className="truncate">{f.name}</span>
                                </button>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  );
                })}
            </div>
          </aside>

          {/* Sağ — editör + konsol */}
          <div className="flex flex-col">
            {/* Editor sekmeleri */}
            <div className="flex items-center gap-1 overflow-x-auto border-b border-slate-800 bg-[#2b2d30] px-2 py-1">
              {activeFile ? (
                <div className="flex items-center gap-2 rounded-t-md bg-[#1e1f22] px-3 py-1 text-xs text-slate-200">
                  <span>{FILE_ICON[activeFile.kind]}</span>
                  <span>{activeFile.name}</span>
                  {dirtyDraft !== null && dirtyDraft !== activeFile.content && (
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-400" title="Kaydedilmemiş değişiklik" />
                  )}
                </div>
              ) : (
                <span className="px-3 py-1 text-xs text-slate-500">Sol panelden bir dosya seç</span>
              )}
              <div className="ml-auto flex items-center gap-2 text-[10px] text-slate-500">
                {activeFile && (
                  <>
                    <span>{activeFile.language.toUpperCase()}</span>
                    <span className="text-slate-600">·</span>
                    <span>{dirtyDraft?.split("\n").length ?? 0} lines</span>
                  </>
                )}
              </div>
            </div>

            {/* Kod editörü */}
            <div className="relative flex-1 overflow-auto bg-[#1e1f22] font-mono text-[12px] leading-5">
              {activeFile ? (
                <div className="flex min-h-full">
                  {/* Satır numaraları */}
                  <div className="sticky left-0 select-none border-r border-slate-800 bg-[#1e1f22] px-2 py-3 text-right text-slate-600">
                    {(dirtyDraft ?? "").split("\n").map((_, i) => (
                      <div key={i} className="tabular-nums">{i + 1}</div>
                    ))}
                  </div>
                  {/* İçerik: hem textarea (düzenleme) hem sahte highlight overlay */}
                  <div className="relative flex-1">
                    <pre className="pointer-events-none absolute inset-0 whitespace-pre px-3 py-3 text-slate-300">
                      {(dirtyDraft ?? "").split("\n").map((line, i) => (
                        <div key={i}>{highlightLine(line || " ", activeFile.language)}</div>
                      ))}
                    </pre>
                    <textarea
                      value={dirtyDraft ?? ""}
                      onChange={(e) => setDirtyDraft(e.target.value)}
                      spellCheck={false}
                      aria-label={`${activeFile.name} editor`}
                      title={`${activeFile.name} editor`}
                      placeholder="// dosya içeriği"
                      className="relative z-10 h-full min-h-[400px] w-full resize-none bg-transparent px-3 py-3 text-transparent caret-white outline-none selection:bg-blue-500/30"
                    />
                  </div>
                </div>
              ) : (
                <div className="flex h-full min-h-[400px] items-center justify-center text-sm text-slate-600">
                  Dosya seçilmedi
                </div>
              )}
            </div>

            {/* Alt konsol */}
            <div className="border-t border-slate-800 bg-[#1e1f22]">
              <div className="flex items-center gap-0 border-b border-slate-800 bg-[#2b2d30] px-2 text-[11px]">
                {(
                  [
                    { id: "console", label: "Console", badge: consoleLines.length },
                    { id: "problems", label: "Problems", badge: problemCount },
                    { id: "run", label: "Run", badge: ideRunning ? "●" : 0 },
                  ] as const
                ).map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setIdeTab(t.id)}
                    className={`flex items-center gap-1.5 border-t-2 px-3 py-1.5 transition
                      ${ideTab === t.id
                        ? "border-blue-500 text-white"
                        : "border-transparent text-slate-500 hover:text-slate-300"}`}
                  >
                    {t.label}
                    {t.badge !== 0 && (
                      <span className="rounded-full bg-slate-700 px-1.5 py-0 text-[9px]">{t.badge}</span>
                    )}
                  </button>
                ))}
                <span className="ml-auto text-[10px] text-slate-600">
                  {ideRunning ? "● RUNNING" : "○ READY"}
                </span>
              </div>
              <div className="h-40 overflow-y-auto px-3 py-2 font-mono text-[11px]">
                {ideTab === "console" && (
                  <>
                    {consoleLines.length === 0 ? (
                      <p className="text-slate-600">Konsol boş. ▶ Run ile başlat.</p>
                    ) : (
                      consoleLines.map((l, i) => {
                        const color = l.includes("[error]")
                          ? "text-red-400"
                          : l.includes("✓ ")
                            ? "text-emerald-400"
                            : l.includes("✗ ")
                              ? "text-red-400"
                              : l.startsWith("▶")
                                ? "text-amber-300"
                                : "text-slate-300";
                        return (
                          <div key={i} className={color}>
                            {l}
                          </div>
                        );
                      })
                    )}
                  </>
                )}
                {ideTab === "problems" && (
                  <>
                    {problemCount === 0 ? (
                      <p className="text-emerald-400">✓ Sorun yok. Tüm step definitions dolduruldu.</p>
                    ) : (
                      <p className="text-amber-300">
                        ⚠ {problemCount} step definitions TODO içeriyor. İlgili dosyada implement edilmesi gerekiyor.
                      </p>
                    )}
                  </>
                )}
                {ideTab === "run" && (
                  <p className="text-slate-400">
                    Konfigürasyon: <span className="text-slate-200">config/cucumber.cjs</span>
                    <br />
                    Komut: <code className="text-amber-300">npx cucumber-js --config config/cucumber.cjs</code>
                  </p>
                )}
              </div>
            </div>

            {/* Status bar */}
            <div className="flex items-center gap-3 border-t border-slate-800 bg-[#2b2d30] px-3 py-1 text-[10px] text-slate-500">
              <span>UTF-8</span>
              <span>LF</span>
              <span>{activeFile?.language.toUpperCase() ?? "-"}</span>
              <span className="ml-auto">
                {ideFiles.length} files · Playwright + Cucumber
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Altta adım kontrolleri */}
      <div className="flex flex-wrap gap-3 pt-2">
        <button
          type="button"
          onClick={goBack}
          className="rounded-xl border border-slate-700 px-5 py-2.5 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
        >
          ← Kuruluma dön
        </button>
        <button
          type="button"
          onClick={goFinish}
          className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
        >
          Bitir & Projeye git →
        </button>
      </div>
    </div>
  );
}

// ── Component ────────────────────────────────────────────────────────────────

export default function NewProjectPage() {
  const router = useRouter();
  const [projectName, setProjectName] = useState("");
  const [projectDesc, setProjectDesc] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step 2 — DB bağlantısı
  const [dbType, setDbType]       = useState("postgresql");
  const [dbHost, setDbHost]       = useState("localhost");
  const [dbPort, setDbPort]       = useState("5432");
  const [dbName, setDbName]       = useState("");
  const [dbUser, setDbUser]       = useState("");
  const [dbPass, setDbPass]       = useState("");
  const [dbConnected, setDbConnected] = useState<boolean | null>(null);

  // Step 3 — Analiz dokümanı
  const [docText, setDocText]             = useState("");
  const [extraInstructions, setExtraInstructions] = useState("");
  const [manualTests, setManualTests]     = useState<ManualTest[]>([]);
  const [bddScenarios, setBddScenarios]   = useState<BddScenario[]>([]);
  // Nexus QA Faz 2 — Yüklenen doküman
  const [uploadedDoc, setUploadedDoc]     = useState<UploadedDocument | null>(null);
  const [aiAnalysis, setAiAnalysis]       = useState<{
    modules: Array<{ name: string; description: string; test_areas: string[]; risk_level: string; estimated_test_cases: number }>;
    critical_flows: string[];
    total_estimated_cases: number;
  } | null>(null);
  const [analyzeMode, setAnalyzeMode]     = useState<"upload" | "paste">("upload");

  // Step 4 — Kayıt durumu
  const [savedScenarios, setSavedScenarios] = useState<SavedScenario[]>([]);
  const [savedIds, setSavedIds]             = useState<string[]>([]);

  // Step 5 — Regresyon setleri
  const [regSets, setRegSets]         = useState<RegSet[]>([]);
  const [acceptedSets, setAcceptedSets] = useState<RegSet[]>([]);

  // Step 6 — Otomasyon seçimi
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Step 7 — Otomasyon çıktısı (fallback)
  const [featureFiles, setFeatureFiles] = useState<AutomationFile[]>([]);
  const [testFiles, setTestFiles]       = useState<AutomationFile[]>([]);
  const [activeFile, setActiveFile]     = useState<AutomationFile | null>(null);

  // Step 7 — Otomasyon kurulumu
  const [maviyakaUrl, setMaviyakaUrl]       = useState("");
  const [environment, setEnvironment]       = useState<"dev" | "test" | "qa" | "preprod" | "prod">("test");
  const [locatorFiles, setLocatorFiles]     = useState<LocatorFile[]>([]);
  const [activeLocatorFile, setActiveLocatorFile] = useState<LocatorFile | null>(null);
  const [crawling, setCrawling]             = useState(false);
  const [maviyakaFeatures, setMaviyakaFeatures] = useState<MaviyakaFeature[]>([]);
  const [activeFeatureIdx, setActiveFeatureIdx] = useState(0);
  const [testDataMap, setTestDataMap]       = useState<Record<string, string>>({});
  const [locatorModal, setLocatorModal]     = useState<{ key: string; aiSuggestion: string | null } | null>(null);
  const [running, setRunning]               = useState(false);
  const [runOutput, setRunOutput]           = useState<string | null>(null);

  // Step 8 — Otomasyon IDE (IntelliJ benzeri)
  const [ideFiles, setIdeFiles]             = useState<IdeFile[]>([]);
  const [activeIdePath, setActiveIdePath]   = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(
    new Set(["features", "steps", "test-data", "locators", "pages", "config"])
  );
  const [consoleLines, setConsoleLines]     = useState<string[]>([]);
  const [ideRunning, setIdeRunning]         = useState(false);
  const [ideTab, setIdeTab]                 = useState<"console" | "problems" | "run">("console");

  // ── helpers ───────────────────────────────────────────────────────────────

  useEffect(() => {
    try {
      const storedProduct = localStorage.getItem(PRODUCT_FAMILY_STORAGE_KEY);
      if (storedProduct) setActiveProductId(getProductFamilyMember(storedProduct as ProductFamilyId).id);
    } catch {
      // ignore
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<{ id: string }>("/api/v1/tspm/projects", {
        method: "POST",
        json: { name: projectName, description: projectDesc },
      });
      try {
        localStorage.setItem(
          "bgts_active_project",
          JSON.stringify({ id: res.id, name: projectName }),
        );
      } catch {
        // ignore
      }
      router.push(`/p/${res.id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Proje oluşturulamadı");
    } finally {
      setLoading(false);
    }
  }

  // 2 — DB bağlantısı test et
  async function testDbConnection() {
    if (!dbName || !dbUser) { err("Veritabanı adı ve kullanıcı zorunlu"); return; }
    setLoading(true); setError(null); setDbConnected(null);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/database/test-connection`, {
        method: "POST",
        json: { connection_string: dbConnectionString, db_type: dbType },
      });
      setDbConnected(true);
      notify("Veritabanı bağlantısı başarılı");
    } catch {
      // Bağlantı endpoint'i yoksa veya bağlantı başarısızsa devam et
      setDbConnected(false);
    } finally {
      setLoading(false);
    }
  }

  function skipDb() {
    setDbConnected(null);
    setStep(3);
  }

  // 3 — Analiz & AI senaryo üretimi (Nexus QA Faz 2)
  async function runAnalysis() {
    const textToAnalyze = uploadedDoc ? uploadedDoc.full_text : docText;
    if (!textToAnalyze.trim()) {
      err(analyzeMode === "upload" ? "Önce bir doküman yükleyin" : "Doküman içeriği boş");
      return;
    }
    const mergedExtraInstructions = [wizardProfile.analysisSeed, extraInstructions.trim()]
      .filter(Boolean)
      .join("\n");
    setLoading(true); setError(null);
    try {
      // Chunk pipeline: büyük dokümanlar için chunked analiz
      if (uploadedDoc?.needs_chunking && uploadedDoc.chunk_count > 1) {
        // 1) Chunk analizi — modülleri çıkar
        const analysisRes = await apiFetch<{
          modules: Array<{ name: string; description: string; test_areas: string[]; risk_level: string; estimated_test_cases: number }>;
          critical_flows: string[];
          total_estimated_cases: number;
        }>(`/api/v1/tspm/projects/${projectId}/wizard/analyze-chunked`, {
          method: "POST",
          json: {
            chunks: [textToAnalyze.slice(0, 12000), textToAnalyze.slice(12000, 24000)].filter(Boolean),
            filename: uploadedDoc.filename,
            extra_instructions: mergedExtraInstructions,
          },
        });
        setAiAnalysis(analysisRes);

        // 2) Test case üretimi — normal analiz endpoint
        const res = await apiFetch<{
          manual_tests: ManualTest[];
          bdd_scenarios: BddScenario[];
          analysis_summary?: { modules: number; total_estimated: number };
          ai_provider?: string;
        }>(`/api/v1/tspm/projects/${projectId}/wizard/analyze`, {
          method: "POST",
          json: {
            text: textToAnalyze.slice(0, 12000), // İlk chunk
            extra_instructions: mergedExtraInstructions,
          },
        });
        setManualTests(res.manual_tests || []);
        setBddScenarios(res.bdd_scenarios || []);
        const total = (res.manual_tests?.length || 0) + (res.bdd_scenarios?.length || 0);
        notify(`${total} senaryo üretildi (${analysisRes.modules.length} modül analiz edildi)`);
      } else {
        // Normal analiz — küçük doküman
        const res = await apiFetch<{
          manual_tests: ManualTest[];
          bdd_scenarios: BddScenario[];
          analysis_summary?: { modules: number; total_estimated: number };
          ai_provider?: string;
        }>(`/api/v1/tspm/projects/${projectId}/wizard/analyze`, {
          method: "POST",
          json: { text: textToAnalyze, extra_instructions: mergedExtraInstructions },
        });
        setManualTests(res.manual_tests || []);
        setBddScenarios(res.bdd_scenarios || []);
        const total = (res.manual_tests?.length || 0) + (res.bdd_scenarios?.length || 0);
        if (total === 0) { err("Senaryo üretilemedi — dokümanı detaylandırın"); return; }
        const providerInfo = res.ai_provider ? ` (${res.ai_provider})` : "";
        notify(`${total} senaryo üretildi${providerInfo}`);
      }
      setStep(4);
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Analiz hatası");
    } finally {
      setLoading(false);
    }
  }

  // 4 — Tüm senaryoları DB'ye kaydet
  async function saveAllScenarios() {
    setLoading(true); setError(null);
    const ids: string[] = [];
    const saved: SavedScenario[] = [];

    const allTests = [
      ...manualTests.map((t) => ({
        title: t.title,
        steps: t.steps.map((s, i) => ({
          keyword: i === 0 ? "Olduğu gibi" : i === t.steps.length - 1 ? "O zaman" : "Eğer",
          text: `${s.action} → ${s.expected}`,
        })),
      })),
      ...bddScenarios.map((s) => ({
        title: s.title,
        steps: s.steps || [],
      })),
    ];

    for (const t of allTests) {
      try {
        const res = await apiFetch<{ id: string; title: string; status: string }>(
          `/api/v1/tspm/projects/${projectId}/scenarios`,
          { method: "POST", json: { title: t.title, description: "AI ile üretildi", status: "draft", steps: t.steps } }
        );
        ids.push(res.id);
        saved.push({ id: res.id, title: res.title, status: res.status });
      } catch { /* devam */ }
    }

    setSavedIds(ids);
    setSavedScenarios(saved);
    notify(`${saved.length} senaryo kaydedildi`);
    setStep(5);
    setLoading(false);
  }

  // 5 — Regresyon seti öner
  async function suggestRegSets() {
    setLoading(true); setError(null);
    try {
      const res = await apiFetch<{ sets: RegSet[] }>(
        `/api/v1/tspm/projects/${projectId}/regression-sets/suggest`,
        { method: "POST", json: { extra_instructions: "" } }
      );
      setRegSets(res.sets || []);
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Öneri hatası");
    } finally {
      setLoading(false);
    }
  }

  async function acceptSets() {
    if (acceptedSets.length === 0) { err("En az bir set seçin"); return; }
    setLoading(true); setError(null);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/regression-sets/accept-suggestions`, {
        method: "POST",
        json: { sets: acceptedSets },
      });
      notify(`${acceptedSets.length} regresyon seti kaydedildi`);
      setStep(6);
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Kaydetme hatası");
    } finally {
      setLoading(false);
    }
  }

  function toggleSet(set: RegSet) {
    setAcceptedSets((prev) =>
      prev.some((s) => s.name === set.name)
        ? prev.filter((s) => s.name !== set.name)
        : [...prev, set]
    );
  }

  // 6 — Otomasyon için case seç
  function toggleScenario(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function selectAll()   { setSelectedIds(new Set(savedIds)); }
  function deselectAll() { setSelectedIds(new Set()); }

  // 6 → 7: Seçili senaryolarla otomasyon kurulumuna geç
  function goToMaviyaka() {
    if (selectedIds.size === 0) { err("En az bir senaryo seçin"); return; }
    setStep(7);
  }

  // 7 — Lokator JSON dosyası yükle (multiple, module-based)
  function handleLocatorUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files) return;
    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const parsed = JSON.parse(ev.target?.result as string);
          const locators: LocatorEntry[] = Array.isArray(parsed) ? parsed : [];
          const module = file.name.replace(/\.json$/i, "");
          const lf: LocatorFile = { name: file.name, module, locators };
          setLocatorFiles((prev) => {
            const idx = prev.findIndex((f) => f.name === file.name);
            if (idx >= 0) { const next = [...prev]; next[idx] = lf; return next; }
            return [...prev, lf];
          });
          setActiveLocatorFile(lf);
          notify(`${file.name} yüklendi — ${locators.length} lokator`);
        } catch {
          err(`${file.name} geçerli JSON değil`);
        }
      };
      reader.readAsText(file);
    });
    e.target.value = "";
  }

  // Aktif proje için tekrar kullanılabilir domain/modül slug'ı
  const projectSlug = slugifyProjectName(projectName);

  // 7 — URL'yi crawl et → lokatorları öner
  async function crawlLocators() {
    if (!maviyakaUrl.trim()) { err("URL giriniz"); return; }
    setCrawling(true); setError(null);
    try {
      const res = await apiFetch<{ locators: LocatorEntry[] }>(
        `/api/v1/tspm/projects/${projectId}/wizard/crawl-locators`,
        { method: "POST", json: { url: maviyakaUrl, domain: projectSlug, environment } }
      );
      const lf: LocatorFile = {
        name: `${projectSlug}_${environment}_crawled.json`,
        module: projectSlug,
        locators: res.locators || [],
      };
      setLocatorFiles((prev) => [...prev, lf]);
      setActiveLocatorFile(lf);
      notify(`${lf.locators.length} lokator bulundu`);
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Crawl hatası");
    } finally {
      setCrawling(false);
    }
  }

  // 7 — Feature dosyaları üret (AI)
  async function generateMaviyakaFeatures() {
    if (!projectId) return;
    setLoading(true); setError(null);
    try {
      const allLocators = locatorFiles.flatMap((f) => f.locators);
      const res = await apiFetch<{ features: MaviyakaFeature[]; test_data: Record<string, string> }>(
        `/api/v1/tspm/projects/${projectId}/wizard/generate-maviyaka`,
        {
          method: "POST",
          json: {
            scenario_ids: Array.from(selectedIds),
            url: maviyakaUrl,
            domain: projectSlug,
            environment,
            locators: allLocators,
          },
        }
      );
      setMaviyakaFeatures(res.features || []);
      setTestDataMap(res.test_data || {});
      setActiveFeatureIdx(0);
      notify(`${(res.features || []).length} feature dosyası üretildi`);
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Feature üretim hatası");
    } finally {
      setLoading(false);
    }
  }

  // 7 — Kırmızı key'e tıkla → AI lokator öner
  async function suggestLocatorForKey(key: string) {
    setLocatorModal({ key, aiSuggestion: null });
    try {
      const res = await apiFetch<{ suggestion: LocatorEntry }>(
        `/api/v1/tspm/projects/${projectId}/wizard/suggest-locator`,
        { method: "POST", json: { key, url: maviyakaUrl, domain: projectSlug, environment } }
      );
      setLocatorModal({ key, aiSuggestion: JSON.stringify(res.suggestion, null, 2) });
    } catch {
      setLocatorModal({
        key,
        aiSuggestion: JSON.stringify({ key, type: "id", value: "" }, null, 2),
      });
    }
  }

  // 7 — Lokator onayla → aktif dosyaya ekle + object repo'ya kaydet
  async function confirmLocator(entry: LocatorEntry) {
    const targetFile = activeLocatorFile ?? locatorFiles[0];
    if (!targetFile) {
      // Hiç dosya yoksa yeni bir tane oluştur
      const lf: LocatorFile = { name: "custom.json", module: "custom", locators: [entry] };
      setLocatorFiles([lf]);
      setActiveLocatorFile(lf);
    } else {
      const updated: LocatorFile = { ...targetFile, locators: [...targetFile.locators, entry] };
      setLocatorFiles((prev) => prev.map((f) => f.name === targetFile.name ? updated : f));
      setActiveLocatorFile(updated);
    }
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/locators`, {
        method: "POST",
        json: { name: entry.key, locator_value: `${entry.type}=${entry.value}`, page_url: maviyakaUrl },
      });
    } catch { /* fail silently */ }
    setLocatorModal(null);
    notify(`"${entry.key}" kaydedildi`);
  }

  // 7 → 8: IDE dosya iskeletini üret ve editor'a geç
  function buildIdeFiles(): IdeFile[] {
    const files: IdeFile[] = [];
    const allLocators = locatorFiles.flatMap((f) => f.locators);

    // 1) .feature dosyaları
    maviyakaFeatures.forEach((feat) => {
      const slug = feat.title.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40) || "scenario";
      files.push({
        path: `features/${slug}.feature`,
        name: `${slug}.feature`,
        folder: "features",
        kind: "feature",
        language: "gherkin",
        content: feat.content,
      });
    });

    // 2) Step definitions (TS iskelet) — her feature için bir step defs dosyası
    maviyakaFeatures.forEach((feat) => {
      const slug = feat.title.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40) || "scenario";
      const steps = (feat.content.match(/^\s*(Given|When|Then|And|But|Eğer|Olduğu gibi|O zaman|Ve)\s+.+$/gm) || [])
        .slice(0, 20)
        .map((line) => {
          const trimmed = line.trim();
          const kw = trimmed.split(/\s+/)[0] || "Given";
          const body = trimmed.slice(kw.length).trim();
          const pattern = body.replace(/"[^"]*"/g, '{string}');
          return `${kw}(/^${pattern.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$/, async function () {\n  // TODO: implement\n  await this.page.waitForLoadState("networkidle");\n});`;
        })
        .join("\n\n");
      files.push({
        path: `steps/${slug}.steps.ts`,
        name: `${slug}.steps.ts`,
        folder: "steps",
        kind: "steps",
        language: "typescript",
        content: `import { Given, When, Then } from "@cucumber/cucumber";\nimport { expect } from "@playwright/test";\nimport locators from "../locators/${projectSlug}_${environment}.json";\nimport testData from "../test-data/${projectSlug}.data.json";\n\n${steps || "// Senaryodan step çıkarılamadı"}\n`,
      });
    });

    // 3) test-data JSON — hem test data map hem örnek
    const dataBody = {
      ...testDataMap,
      __meta: {
        url: maviyakaUrl,
        domain: projectSlug,
        environment,
        generated_at: new Date().toISOString(),
      },
    };
    files.push({
      path: `test-data/${projectSlug}.data.json`,
      name: `${projectSlug}.data.json`,
      folder: "test-data",
      kind: "data",
      language: "json",
      content: JSON.stringify(dataBody, null, 2),
    });

    // 4) locators — mevcut tüm lokator dosyalarını birleştir
    if (allLocators.length > 0) {
      files.push({
        path: `locators/${projectSlug}_${environment}.json`,
        name: `${projectSlug}_${environment}.json`,
        folder: "locators",
        kind: "locator",
        language: "json",
        content: JSON.stringify(allLocators, null, 2),
      });
    }
    locatorFiles.forEach((lf) => {
      files.push({
        path: `locators/${lf.name}`,
        name: lf.name,
        folder: "locators",
        kind: "locator",
        language: "json",
        content: JSON.stringify(lf.locators, null, 2),
      });
    });

    // 5) pages — basit bir page object iskeleti
    files.push({
      path: `pages/${projectSlug}.page.ts`,
      name: `${projectSlug}.page.ts`,
      folder: "pages",
      kind: "page",
      language: "typescript",
      content: `import type { Page } from "@playwright/test";\nimport locators from "../locators/${projectSlug}_${environment}.json";\n\nexport class ${projectSlug.replace(/(^\w|_\w)/g, (m) => m.replace("_", "").toUpperCase())}Page {\n  constructor(private page: Page) {}\n\n  async goto() {\n    await this.page.goto(${JSON.stringify(maviyakaUrl)});\n  }\n\n${allLocators.slice(0, 12).map((l) => `  get ${l.key}() {\n    return this.page.locator(${JSON.stringify(`${l.type}=${l.value}`)});\n  }`).join("\n\n") || "  // lokator tanımlanmadı"}\n}\n`,
    });

    // 6) config — cucumber.js ve playwright.config.ts iskeletleri
    files.push({
      path: `config/cucumber.cjs`,
      name: `cucumber.cjs`,
      folder: "config",
      kind: "config",
      language: "typescript",
      content: `module.exports = {\n  default: {\n    paths: ["features/**/*.feature"],\n    require: ["steps/**/*.ts"],\n    requireModule: ["ts-node/register"],\n    format: ["progress-bar", "html:reports/cucumber.html"],\n  },\n};\n`,
    });
    files.push({
      path: `config/playwright.config.ts`,
      name: `playwright.config.ts`,
      folder: "config",
      kind: "config",
      language: "typescript",
      content: `import { defineConfig } from "@playwright/test";\n\nexport default defineConfig({\n  testDir: "./tests",\n  timeout: 30_000,\n  use: {\n    baseURL: ${JSON.stringify(maviyakaUrl)},\n    headless: true,\n    screenshot: "only-on-failure",\n    video: "retain-on-failure",\n  },\n});\n`,
    });

    return files;
  }

  function openIdeForRun() {
    if (maviyakaFeatures.length === 0) {
      err("Önce feature dosyaları üretilmeli");
      return;
    }
    const files = buildIdeFiles();
    setIdeFiles(files);
    // varsayılan açık dosya: ilk .feature
    const firstFeature = files.find((f) => f.kind === "feature");
    setActiveIdePath(firstFeature?.path || files[0]?.path || null);
    setConsoleLines([
      `[${new Date().toLocaleTimeString()}] BGTS Automation IDE hazırlandı`,
      `[info] ${files.length} dosya üretildi (feature + steps + data + locators + pages + config)`,
      `[info] Hedef URL: ${maviyakaUrl || "-"}  ·  Ortam: ${environment.toUpperCase()}`,
      `[hint] Sol panelden bir dosya seç, üstteki "▶ Run" ile koştur.`,
    ]);
    setStep(8);
    notify(`Otomasyon IDE açıldı — ${files.length} dosya hazır`);
  }

  function toggleFolder(folder: string) {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folder)) next.delete(folder);
      else next.add(folder);
      return next;
    });
  }

  async function runFromIde() {
    if (!projectId || ideFiles.filter((f) => f.kind === "feature").length === 0) return;
    setIdeRunning(true);
    setIdeTab("console");
    const featureDocs = ideFiles
      .filter((f) => f.kind === "feature")
      .map((f) => ({ title: f.name.replace(/\.feature$/, ""), content: f.content }));

    const prepend = (line: string) =>
      setConsoleLines((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${line}`]);

    prepend("▶ npx cucumber-js --config config/cucumber.cjs");
    prepend(`[run] ${featureDocs.length} feature dosyası koşturuluyor…`);
    try {
      const res = await apiFetch<{ output: string; passed: number; failed: number }>(
        `/api/v1/tspm/projects/${projectId}/wizard/run-maviyaka`,
        {
          method: "POST",
          json: {
            features: featureDocs,
            url: maviyakaUrl,
            domain: projectSlug,
            environment,
            locators: locatorFiles.flatMap((f) => f.locators),
            test_data: testDataMap,
          },
        }
      );
      const out = (res.output || "").split("\n").filter(Boolean);
      out.slice(0, 200).forEach((l) => prepend(l));
      const passed = res.passed ?? 0;
      const failed = res.failed ?? 0;
      prepend(`───────────────────────────────────────────`);
      prepend(`✓ ${passed} passed   ✗ ${failed} failed`);
      prepend(failed === 0 ? `[done] Tüm senaryolar başarılı` : `[done] ${failed} senaryo başarısız`);
      setRunOutput(res.output || `${passed} passed, ${failed} failed`);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Koşum hatası";
      prepend(`[error] ${msg}`);
    } finally {
      setIdeRunning(false);
    }
  }

  // 7 — Testleri Başlat (Python Playwright engine) — eski yol, ide geçişi için kullanılmıyor
  async function runMaviyaka() {
    if (!projectId || maviyakaFeatures.length === 0) return;
    setRunning(true); setRunOutput(null); setError(null);
    try {
      const res = await apiFetch<{ output: string; passed: number; failed: number }>(
        `/api/v1/tspm/projects/${projectId}/wizard/run-maviyaka`,
        {
          method: "POST",
          json: {
            features: maviyakaFeatures,
            url: maviyakaUrl,
            domain: projectSlug,
            environment,
            locators: locatorFiles.flatMap((f) => f.locators),
            test_data: testDataMap,
          },
        }
      );
      setRunOutput(res.output || `${res.passed ?? 0} passed, ${res.failed ?? 0} failed`);
      setStep(9);
    } catch (e: unknown) {
      err(e instanceof Error ? e.message : "Çalıştırma hatası");
    } finally {
      setRunning(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm">
        <div className="mx-auto flex w-full max-w-[1600px] items-center gap-4 px-8 py-3">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"
            data-testid="new-project-back"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Ana Sayfa
          </button>
          <span className="text-slate-700">/</span>
          <span className="text-sm font-medium">Yeni Proje</span>
          <span className="ml-auto flex items-center gap-3 text-xs text-slate-500">
            <span className="hidden sm:inline">
              Adım <span className="font-semibold text-slate-300">{step}</span> / {STEPS.length}
            </span>
            <span className="h-1.5 w-32 overflow-hidden rounded-full bg-slate-800">
              <span
                className="block h-full bg-gradient-to-r from-blue-500 to-violet-500 transition-all"
                style={{ width: `${(step / STEPS.length) * 100}%` }}
              />
            </span>
          </span>
        </div>
      </div>

      <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
        {/* Bildirimler */}
        {error && (
          <div className="mb-6 rounded-xl border border-red-800 bg-red-950/50 px-4 py-3 text-sm text-red-400">
            ⚠️ {error}
            <button className="ml-3 opacity-60 hover:opacity-100" onClick={() => setError(null)}>✕</button>
          </div>
        )}
        {success && (
          <div className="mb-6 rounded-xl border border-emerald-800 bg-emerald-950/50 px-4 py-3 text-sm text-emerald-400">
            ✓ {success}
          </div>
        )}

        {/* Mobile ürün bandı — sadece md altı */}
        <div className="mb-6 rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/10 via-slate-900 to-slate-950 p-4 md:hidden">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-violet-200/80">Visium Product Focus</p>
          <div className="mt-2 flex items-center gap-2">
            <h2 className="text-lg font-semibold text-white">{selectedProduct.name}</h2>
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${PRODUCT_AVAILABILITY_META[selectedProduct.availability].className}`}>
              {PRODUCT_AVAILABILITY_META[selectedProduct.availability].label}
            </span>
          </div>
          <p className="mt-1 text-sm text-violet-200/90">{selectedProduct.tagline}</p>
          <div className="mt-3 grid grid-cols-2 gap-1.5">
            {PRODUCT_FAMILY.map((product) => (
              <button
                key={product.id}
                type="button"
                onClick={() => applyProduct(product.id)}
                className={`rounded-lg border px-2 py-1.5 text-left transition ${
                  product.id === selectedProduct.id
                    ? "border-violet-300/40 bg-violet-400/15 text-violet-50"
                    : "border-slate-800 bg-slate-900/60 text-slate-300"
                }`}
              >
                <span className="block text-[10px] font-semibold uppercase tracking-[0.16em]">{product.shortName}</span>
                <span className="mt-0.5 block text-[11px] leading-snug">{product.tagline}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Mobile horizontal step rail — sadece md altı */}
        <div className="mb-6 overflow-x-auto pb-1 md:hidden">
          <div className="flex items-center min-w-max">
            {STEPS.map((s, i) => (
              <div key={s.id} className="flex items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold
                      ${step === s.id ? "bg-blue-600 ring-2 ring-blue-600/30 text-white" :
                        step > s.id  ? "bg-emerald-600 text-white" :
                                       "bg-slate-800 text-slate-500"}`}
                  >
                    {step > s.id ? (
                      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    ) : s.id}
                  </div>
                  <span className={`mt-1 w-14 text-center text-[9px] leading-tight
                    ${step === s.id ? "text-blue-400 font-medium" : step > s.id ? "text-emerald-600" : "text-slate-700"}`}>
                    {s.label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`mx-0.5 mb-4 h-px w-5 shrink-0 ${step > s.id ? "bg-emerald-600" : "bg-slate-800"}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 3-kolon grid: sol step rail | orta form | sağ context paneli */}
        <div className="grid gap-6 md:grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)_320px] xl:gap-8 2xl:grid-cols-[280px_minmax(0,1fr)_360px]">
          {/* Sol sticky step rail (md+) */}
          <aside className="hidden md:block">
            <div className="sticky top-6 space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Kurulum Adımları
                </p>
                <ol className="mt-3 space-y-1">
                  {STEPS.map((s) => {
                    const isActive = step === s.id;
                    const isDone = step > s.id;
                    return (
                      <li key={s.id}>
                        <button
                          type="button"
                          onClick={() => { if (isDone) setStep(s.id); }}
                          disabled={!isDone}
                          className={`flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left transition ${
                            isActive
                              ? "bg-blue-500/10 ring-1 ring-inset ring-blue-500/30"
                              : isDone
                                ? "hover:bg-slate-800/60 cursor-pointer"
                                : "opacity-60 cursor-not-allowed"
                          }`}
                        >
                          <span
                            className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold
                              ${isActive ? "bg-blue-600 text-white ring-2 ring-blue-600/30" :
                                isDone  ? "bg-emerald-600 text-white" :
                                          "bg-slate-800 text-slate-500"}`}
                          >
                            {isDone ? (
                              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                              </svg>
                            ) : s.id}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className={`block text-xs font-semibold leading-tight ${
                              isActive ? "text-blue-300" : isDone ? "text-emerald-400" : "text-slate-300"
                            }`}>
                              {s.label}
                            </span>
                            <span className="mt-0.5 block text-[10px] leading-tight text-slate-500">
                              {s.desc}
                            </span>
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ol>
                <div className="mt-3 border-t border-slate-800 pt-3">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500 transition-all"
                        style={{ width: `${(step / STEPS.length) * 100}%` }}
                      />
                    </div>
                    <span className="text-[10px] font-semibold text-slate-400">
                      {Math.round((step / STEPS.length) * 100)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </aside>

          {/* Orta — asıl form içeriği */}
          <div className="min-w-0">

        {/* ── STEP 1: Proje Oluştur ── */}
        {step === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold">Projeyi Tanımla</h2>
              <p className="mt-1.5 text-sm text-slate-400">
                Projen için bir ad ve açıklama gir. Kurulum sonunda{" "}
                <span className="font-medium text-violet-300">{selectedProduct.name}</span> çalışma alanı açılacak.
              </p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 xl:hidden">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Odak akışı</p>
              <p className="mt-2 text-sm font-medium text-white">{productGuide.title}</p>
              <p className="mt-2 text-sm leading-6 text-slate-400">{selectedProduct.description}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {selectedProduct.routeSegments.slice(0, 5).map((segment) => (
                  <span
                    key={segment}
                    className="rounded-full border border-slate-700 bg-slate-950 px-2 py-0.5 text-[10px] font-medium text-slate-300"
                  >
                    {segment}
                  </span>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-300">Proje Adı *</label>
                <input
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="Ör: Ödeme API Test Projesi"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-300">Açıklama</label>
                <textarea
                  value={projectDesc}
                  onChange={(e) => setProjectDesc(e.target.value)}
                  placeholder="Projenin amacı ve kapsamı..."
                  rows={3}
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none resize-none"
                />
              </div>
            </div>
            <button
              onClick={createProject}
              disabled={loading || !projectName.trim()}
              className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-40"
            >
              {loading ? "Oluşturuluyor…" : "Projeyi Oluştur →"}
            </button>
          </div>
        )}

        <div className="mt-8 space-y-4 rounded-xl border border-slate-800 bg-slate-900 p-6">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">Proje Adı *</label>
            <input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="Ör: Ödeme API Test Projesi"
              data-testid="new-project-input-name"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
            />
          </div>
        )}

        {/* ── STEP 3: Analiz Dokümanı ── */}
        {step === 3 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-xl font-bold">Analiz Dokümanı</h2>
              <p className="mt-1 text-sm text-slate-400">
                Gereksinim belgenizi yukleyin veya yapistirin. AI; secili urun odagini koruyarak test senaryolari ve BDD uretecek.
              </p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Varsayilan AI odagi</p>
              <p className="mt-2 text-sm text-slate-300">{wizardProfile.analysisSeed}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {wizardProfile.analysisFocus.map((item) => (
                  <span
                    key={item}
                    className="rounded-full border border-slate-700 bg-slate-950 px-2 py-0.5 text-[10px] font-medium text-slate-300"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>

            {/* Mod Seçici */}
            <div className="flex rounded-xl border border-slate-800 bg-slate-900/60 p-1">
              <button
                onClick={() => setAnalyzeMode("upload")}
                className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition ${
                  analyzeMode === "upload"
                    ? "bg-blue-600 text-white shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                </svg>
                Dosya Yükle
              </button>
              <button
                onClick={() => setAnalyzeMode("paste")}
                className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition ${
                  analyzeMode === "paste"
                    ? "bg-blue-600 text-white shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
                </svg>
                Metin Yapıştır
              </button>
            </div>

            {/* Dosya Yükleme Modu */}
            {analyzeMode === "upload" && projectId && (
              <DocumentUploader
                projectId={projectId}
                onUploaded={(doc) => {
                  setUploadedDoc(doc);
                  setDocText(doc.full_text); // Hem upload hem paste için text
                  notify(`"${doc.filename}" yüklendi — ${doc.word_count.toLocaleString()} kelime`);
                }}
                onError={err}
              />
            )}

            {/* Metin Yapıştır Modu */}
            {analyzeMode === "paste" && (
              <div className="space-y-3">
                <textarea
                  value={docText}
                  onChange={(e) => setDocText(e.target.value)}
                  placeholder={"Dokümanı buraya yapıştır…\n\nÖrnek:\n• Kullanıcı sisteme e-posta ve şifresiyle giriş yapabilmeli\n• Geçersiz şifre girilince hata mesajı görünmeli\n• Şifremi Unuttum akışı çalışmalı\n• Oturum 30 dakika sonra otomatik kapanmalı"}
                  rows={12}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none resize-none font-mono"
                />
                <p className="text-right text-xs text-slate-600">{docText.length.toLocaleString()} karakter</p>
              </div>
            )}

            {/* AI Analiz Sonucu — modül özeti */}
            {aiAnalysis && aiAnalysis.modules.length > 0 && (
              <div className="rounded-xl border border-violet-700/30 bg-violet-950/20 p-4">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-violet-400">
                  AI Analiz Özeti — {aiAnalysis.modules.length} Modül Tespit Edildi
                </p>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {aiAnalysis.modules.slice(0, 6).map((m, i) => (
                    <div key={i} className="rounded-lg bg-slate-900/60 p-2.5">
                      <p className="text-xs font-semibold text-white truncate">{m.name}</p>
                      <div className="mt-1 flex items-center justify-between">
                        <span className={`text-[10px] font-medium ${
                          m.risk_level === "high" ? "text-red-400" :
                          m.risk_level === "medium" ? "text-yellow-400" : "text-emerald-400"
                        }`}>
                          {m.risk_level} risk
                        </span>
                        <span className="text-[10px] text-slate-500">~{m.estimated_test_cases} test</span>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-xs text-slate-500">
                  Tahmini toplam: <span className="font-semibold text-slate-300">{aiAnalysis.total_estimated_cases} test case</span>
                </p>
              </div>
            )}

            {/* Ek Talimatlar */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400 uppercase tracking-wide">
                Ek Talimatlar (opsiyonel)
              </label>
              <input
                value={extraInstructions}
                onChange={(e) => setExtraInstructions(e.target.value)}
                placeholder="Ör: Negatif senaryolara ağırlık ver, sadece login akışına odaklan"
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>

            {/* Analiz Butonu */}
            <div className="flex items-center gap-3">
              <button
                onClick={runAnalysis}
                disabled={loading || (analyzeMode === "upload" ? !uploadedDoc : !docText.trim())}
                className="flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-40"
              >
                {loading ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    AI Analiz Ediyor…
                  </>
                ) : (
                  <>
                    <span>🤖</span>
                    AI ile Analiz Et →
                  </>
                )}
              </button>
              {uploadedDoc && (
                <span className="text-xs text-emerald-400">
                  ✓ {uploadedDoc.filename} ({uploadedDoc.word_count.toLocaleString()} kelime)
                </span>
              )}
            </div>
          </div>
        )}

        {/* ── STEP 4: Manuel Testler ── */}
        {step === 4 && (
          <div className="space-y-5">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-bold">Üretilen Testler</h2>
                <p className="mt-1 text-sm text-slate-400">
                  AI <span className="text-blue-400 font-medium">{manualTests.length} manuel test</span> ve{" "}
                  <span className="text-purple-400 font-medium">{bddScenarios.length} BDD senaryo</span> üretti.
                </p>
              </div>
              <button
                onClick={saveAllScenarios}
                disabled={loading}
                className="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-40"
              >
                {loading ? "Kaydediliyor…" : `Tümünü Kaydet (${manualTests.length + bddScenarios.length})`}
              </button>
            </div>

            {/* Manuel testler */}
            {manualTests.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Manuel Testler</h3>
                {manualTests.map((t, i) => (
                  <div key={i} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <p className="text-sm font-semibold text-white mb-3">{t.title}</p>
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-slate-500">
                          <th className="w-6 text-left pb-2">#</th>
                          <th className="text-left pb-2">Aksiyon</th>
                          <th className="text-left pb-2">Beklenen Sonuç</th>
                        </tr>
                      </thead>
                      <tbody>
                        {t.steps.map((s, j) => (
                          <tr key={j} className="border-t border-slate-800">
                            <td className="py-2 text-slate-600">{j + 1}</td>
                            <td className="py-2 text-slate-300">{s.action}</td>
                            <td className="py-2 text-emerald-400">{s.expected}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            )}

            {/* BDD Senaryolar */}
            {bddScenarios.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">BDD Senaryolar</h3>
                {bddScenarios.map((s, i) => (
                  <div key={i} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <p className="text-sm font-semibold text-white mb-2">{s.title}</p>
                    {s.gherkin && (
                      <pre className="rounded-lg bg-slate-950 p-3 text-xs text-purple-300 overflow-auto">{s.gherkin}</pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── STEP 5: Regresyon Seti ── */}
        {step === 5 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-xl font-bold">Regresyon Seti</h2>
              <p className="mt-1 text-sm text-slate-400">AI, senaryoları öncelik ve kapsama göre grupluyor. Onaylamak istediklerini seç.</p>
            </div>

            {regSets.length === 0 ? (
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 flex flex-col items-center gap-4 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-600/10 text-2xl">🔁</div>
                <div>
                  <p className="text-sm font-medium text-white">AI ile Regresyon Seti Öner</p>
                  <p className="mt-1 text-xs text-slate-500">Senaryolarını önceliğe göre gruplandırıyor</p>
                </div>
                <button
                  onClick={suggestRegSets}
                  disabled={loading}
                  className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-40"
                >
                  {loading ? (
                    <>
                      <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      AI Gruplandırıyor…
                    </>
                  ) : "Regresyon Setleri Öner"}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {regSets.map((set, i) => {
                  const isSelected = acceptedSets.some((s) => s.name === set.name);
                  return (
                    <button
                      key={i}
                      onClick={() => toggleSet(set)}
                      className={`w-full rounded-xl border p-5 text-left transition-all
                        ${isSelected
                          ? "border-blue-500 bg-blue-950/30"
                          : "border-slate-800 bg-slate-900 hover:border-slate-600"}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-semibold text-white">{set.name}</span>
                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${PRIORITY_COLOR[set.priority]}`}>
                              {set.priority}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400">{set.description}</p>
                          <p className="mt-2 text-xs text-slate-600">{set.scenario_ids.length} senaryo</p>
                        </div>
                        <div className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition
                          ${isSelected ? "border-blue-500 bg-blue-500" : "border-slate-600"}`}>
                          {isSelected && (
                            <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })}

                <div className="flex gap-3">
                  <button
                    onClick={() => setAcceptedSets(regSets)}
                    className="text-xs text-blue-400 hover:underline"
                  >
                    Tümünü Seç
                  </button>
                  <button
                    onClick={() => setAcceptedSets([])}
                    className="text-xs text-slate-500 hover:underline"
                  >
                    Tümünü Kaldır
                  </button>
                </div>

                <button
                  onClick={acceptSets}
                  disabled={loading || acceptedSets.length === 0}
                  className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-40"
                >
                  {loading ? "Kaydediliyor…" : `Seçilenleri Kaydet (${acceptedSets.length}) →`}
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── STEP 6: Otomasyon Seç ── */}
        {step === 6 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-xl font-bold">Otomasyona Alınacakları Seç</h2>
              <p className="mt-1 text-sm text-slate-400">
                {wizardProfile.automationPrimary
                  ? "Hangi senaryolar için otomasyon kodu uretilsin? Sec ve devam et."
                  : wizardProfile.automationNote}
              </p>
            </div>
            {!wizardProfile.automationPrimary && (
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-100">
                Bu adim secili urunde opsiyonel. Istersen dogrudan kurulumu tamamlayip daha sonra web otomasyonu ekleyebilirsin.
              </div>
            )}
            <div className="flex gap-3">
              <button onClick={selectAll}   className="text-xs text-blue-400 hover:underline">Tümünü Seç</button>
              <button onClick={deselectAll} className="text-xs text-slate-500 hover:underline">Tümünü Kaldır</button>
              <span className="text-xs text-slate-600">{selectedIds.size} / {savedScenarios.length} seçili</span>
            </div>
            <div className="space-y-2 rounded-2xl border border-slate-800 bg-slate-900 p-4">
              {savedScenarios.map((s) => {
                const isSelected = selectedIds.has(s.id);
                return (
                  <button
                    key={s.id}
                    onClick={() => toggleScenario(s.id)}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition
                      ${isSelected ? "bg-blue-950/40 text-white" : "text-slate-400 hover:bg-slate-800"}`}
                  >
                    <div className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition
                      ${isSelected ? "border-blue-500 bg-blue-500" : "border-slate-600"}`}>
                      {isSelected && (
                        <svg className="h-2.5 w-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                    {s.title}
                  </button>
                );
              })}
            </div>
            <div className="flex flex-wrap gap-3">
              {!wizardProfile.automationPrimary && (
                <button
                  onClick={() => setStep(9)}
                  className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
                >
                  {selectedProduct.shortName} odagiyla kurulumu tamamla →
                </button>
              )}
              <button
                onClick={goToMaviyaka}
                disabled={selectedIds.size === 0}
                className="flex items-center gap-2 rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-semibold text-white transition hover:border-blue-500 hover:text-blue-300 disabled:opacity-40 disabled:hover:border-slate-700 disabled:hover:text-white"
              >
                🚀 Web otomasyonuna gec ({selectedIds.size} senaryo)
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 7: Otomasyon Kurulumu ── */}
        {step === 7 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-xl font-bold">
                🚀 {projectName?.trim() || "Proje"} — Otomasyon Kurulumu
              </h2>
              <p className="mt-1 text-sm text-slate-400">
                Hedef URL, ortam ve lokator dosyalarını tanımla; AI Gherkin feature dosyalarını üretecek.
              </p>
            </div>
            {!wizardProfile.automationPrimary && (
              <div className="rounded-xl border border-violet-500/20 bg-violet-500/10 p-4 text-sm text-violet-100">
                Secili urun: <span className="font-semibold">{selectedProduct.name}</span>. Bu adim yardimci bir web otomasyon uzantisidir; kurulum bitsin diye zorunlu degil.
              </div>
            )}

            {/* URL + Domain */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-3">
              <h3 className="text-sm font-semibold text-slate-300">Hedef Uygulama</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2">
                  <label className="mb-1.5 block text-xs font-medium text-slate-400 uppercase tracking-wide">URL</label>
                  <input
                    value={maviyakaUrl}
                    onChange={(e) => setMaviyakaUrl(e.target.value)}
                    placeholder="https://app.example.com"
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label htmlFor="wizard-environment" className="mb-1.5 block text-xs font-medium text-slate-400 uppercase tracking-wide">Ortam</label>
                  <select
                    id="wizard-environment"
                    aria-label="Ortam"
                    value={environment}
                    onChange={(e) => setEnvironment(e.target.value as typeof environment)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white focus:border-blue-500 focus:outline-none"
                  >
                    <option value="dev">DEV</option>
                    <option value="test">TEST</option>
                    <option value="qa">QA</option>
                    <option value="preprod">PREPROD</option>
                    <option value="prod">PROD</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Lokator Dosyaları */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-300">Lokator Dosyaları (JSON)</h3>
                <span className="text-xs text-slate-500">
                  {locatorFiles.reduce((a, f) => a + f.locators.length, 0)} lokator
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-300 transition hover:border-slate-500 hover:text-white">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                  </svg>
                  JSON Yükle (birden fazla)
                  <input type="file" accept=".json" multiple onChange={handleLocatorUpload} className="hidden" />
                </label>
                <span className="text-xs text-slate-600">veya</span>
                <button
                  type="button"
                  onClick={crawlLocators}
                  disabled={crawling || !maviyakaUrl.trim()}
                  className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-300 transition hover:border-blue-500 hover:text-blue-400 disabled:opacity-40"
                >
                  {crawling ? (
                    <>
                      <svg className="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Tarıyor…
                    </>
                  ) : "🕷 URL'yi Otomatik Tara"}
                </button>
              </div>

              {locatorFiles.length > 0 && (
                <div className="space-y-2">
                  {locatorFiles.map((lf, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setActiveLocatorFile(lf)}
                      className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-sm transition
                        ${activeLocatorFile?.name === lf.name
                          ? "border-blue-500 bg-blue-950/20 text-blue-400"
                          : "border-slate-700 bg-slate-800 text-slate-300 hover:border-slate-500"}`}
                    >
                      <span>📋 {lf.name}</span>
                      <span className="text-xs text-slate-500">{lf.locators.length} lokator</span>
                    </button>
                  ))}
                </div>
              )}

              {activeLocatorFile && (
                <div className="rounded-lg border border-slate-700 bg-slate-950 p-3 space-y-1 max-h-36 overflow-y-auto">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-2">
                    {activeLocatorFile.name}
                  </p>
                  {activeLocatorFile.locators.slice(0, 10).map((l, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span className="text-emerald-400 font-mono">{l.key}</span>
                      <span className="text-slate-600">→</span>
                      <span className="text-slate-400">{l.type}=&quot;{l.value}&quot;</span>
                    </div>
                  ))}
                  {activeLocatorFile.locators.length > 10 && (
                    <p className="text-xs text-slate-600">+{activeLocatorFile.locators.length - 10} daha…</p>
                  )}
                </div>
              )}
            </div>

            {/* Feature Üret Butonu */}
            <button
              type="button"
              onClick={generateMaviyakaFeatures}
              disabled={loading || !maviyakaUrl.trim()}
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-40"
            >
              {loading ? (
                <>
                  <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Üretiliyor…
                </>
              ) : "🤖 Feature Dosyaları Üret"}
            </button>

            {/* Feature Dosyaları + Syntax Highlight */}
            {maviyakaFeatures.length > 0 && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-4">
                  <h3 className="text-sm font-semibold text-slate-300">Üretilen Feature Dosyaları</h3>
                  <span className="text-[11px] text-slate-500">
                    <span className="text-blue-400 font-semibold">keyword</span>
                    &nbsp;·&nbsp;
                    <span className="text-emerald-400">mevcut lokator</span>
                    &nbsp;·&nbsp;
                    <span className="text-red-400 underline">eksik lokator (tıkla → AI)</span>
                  </span>
                </div>

                {/* Sekme seçici */}
                <div className="flex flex-wrap gap-1.5">
                  {maviyakaFeatures.map((f, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setActiveFeatureIdx(i)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-medium transition
                        ${activeFeatureIdx === i ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}
                    >
                      {f.title}
                    </button>
                  ))}
                </div>

                {maviyakaFeatures[activeFeatureIdx] && (
                  <MaviyakaFeatureViewer
                    content={maviyakaFeatures[activeFeatureIdx].content}
                    allLocators={locatorFiles.flatMap((f) => f.locators)}
                    onRedKeyClick={suggestLocatorForKey}
                  />
                )}

                {/* AI Test Verisi */}
                {Object.keys(testDataMap).length > 0 && (
                  <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
                      AI Üretilen Test Verisi
                    </p>
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                      {Object.entries(testDataMap).map(([k, v]) => (
                        <div key={k} className="rounded-lg bg-slate-950 px-3 py-2 text-xs">
                          <span className="text-yellow-400 font-mono">@{k}</span>
                          <span className="text-slate-600 mx-1">=</span>
                          <span className="text-slate-300">{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Başlat / Atla */}
                <div className="flex flex-wrap gap-3 pt-2">
                  <button
                    type="button"
                    onClick={openIdeForRun}
                    disabled={running || ideRunning}
                    className="flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-40"
                  >
                    💻 Testleri Başlat — IDE&apos;de aç
                  </button>
                  <button
                    type="button"
                    onClick={() => setStep(9)}
                    className="rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
                  >
                    Atla & Bitir →
                  </button>
                </div>
              </div>
            )}

            {/* Geri butonu (feature üretilmediyse) */}
            {maviyakaFeatures.length === 0 && (
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setStep(6)}
                  className="rounded-xl border border-slate-700 px-5 py-2.5 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
                >
                  ← Geri
                </button>
                <button
                  type="button"
                  onClick={() => setStep(9)}
                  className="rounded-xl border border-slate-700 px-5 py-2.5 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
                >
                  Atla →
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── STEP 8: Otomasyon IDE ── */}
        {step === 8 && (
          <IdeWorkbench
            projectName={projectName}
            projectSlug={projectSlug}
            environment={environment}
            ideFiles={ideFiles}
            activeIdePath={activeIdePath}
            setActiveIdePath={setActiveIdePath}
            setIdeFiles={setIdeFiles}
            expandedFolders={expandedFolders}
            toggleFolder={toggleFolder}
            consoleLines={consoleLines}
            ideTab={ideTab}
            setIdeTab={setIdeTab}
            ideRunning={ideRunning}
            runFromIde={runFromIde}
            goBack={() => setStep(7)}
            goFinish={() => setStep(9)}
          />
        )}

        {/* ── STEP 9: Tamamlandı ── */}
        {step === 9 && (
          <div className="space-y-5">
            <div>
              <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-600/20">
                <svg className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-xl font-bold">Proje Hazır!</h2>
              <p className="mt-1 text-sm text-slate-400">
                {featureFiles.length + testFiles.length > 0
                  ? `${featureFiles.length} feature + ${testFiles.length} test dosyası üretildi. Dosyaları incele ve projeye git.`
                  : "Otomasyon kodu üretildi. Dosyaları incele ve projeye git."}
              </p>
            </div>

            <div className="rounded-xl border border-violet-500/20 bg-violet-500/10 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-200/80">Hazir acilis noktasi</p>
                  <p className="mt-2 text-lg font-semibold text-white">{selectedProduct.name}</p>
                  <p className="mt-1 text-sm text-slate-300">{productGuide.title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-400">{productGuide.description}</p>
                </div>
                <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${PRODUCT_AVAILABILITY_META[selectedProduct.availability].className}`}>
                  {PRODUCT_AVAILABILITY_META[selectedProduct.availability].label}
                </span>
              </div>
            </div>

            {/* Dosya yoksa yeniden üret */}
            {featureFiles.length === 0 && testFiles.length === 0 && (
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 text-center space-y-3">
                <p className="text-sm text-slate-400">
                  Dosyalar yüklenemedi. Tekrar denemek için aşağıdaki butonu kullanın.
                </p>
                <button
                  onClick={() => setStep(6)}
                  className="rounded-xl border border-slate-700 px-5 py-2 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-white"
                >
                  ← Otomasyon adımına dön
                </button>
              </div>
            )}

            {/* Dosya gezgini */}
            {(featureFiles.length > 0 || testFiles.length > 0) && (
            <div className="flex gap-4 rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden" style={{ minHeight: 400 }}>
              {/* Sol panel — dosya listesi */}
              <div className="w-56 shrink-0 border-r border-slate-800 p-3 space-y-1">
                {featureFiles.length > 0 && (
                  <>
                    <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-slate-600">Feature Dosyaları</p>
                    {featureFiles.map((f, i) => (
                      <button
                        key={i}
                        onClick={() => setActiveFile(f)}
                        className={`w-full rounded-lg px-3 py-2 text-left text-xs transition
                          ${activeFile?.name === f.name ? "bg-blue-600/20 text-blue-400" : "text-slate-400 hover:bg-slate-800"}`}
                      >
                        📄 {f.name}
                      </button>
                    ))}
                  </>
                )}
                {testFiles.length > 0 && (
                  <>
                    <p className="mt-3 px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-slate-600">Test Dosyaları</p>
                    {testFiles.map((f, i) => (
                      <button
                        key={i}
                        onClick={() => setActiveFile(f)}
                        className={`w-full rounded-lg px-3 py-2 text-left text-xs transition
                          ${activeFile?.name === f.name ? "bg-blue-600/20 text-blue-400" : "text-slate-400 hover:bg-slate-800"}`}
                      >
                        🧪 {f.name}
                      </button>
                    ))}
                  </>
                )}
              </div>

              {/* Sağ panel — kod görüntüleyici */}
              <div className="flex-1 overflow-auto p-4">
                {activeFile ? (
                  <>
                    <p className="mb-3 text-xs font-medium text-slate-500">{activeFile.name}</p>
                    <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                      {activeFile.content}
                    </pre>
                  </>
                ) : (
                  <p className="text-sm text-slate-600 mt-4">Sol panelden bir dosya seç</p>
                )}
              </div>
            </div>
            )}

            {/* Çalıştırma çıktısı */}
            {runOutput && (
              <div className="rounded-xl border border-emerald-800 bg-emerald-950/30 p-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-emerald-400">Test Sonucu</p>
                <pre className="text-xs text-emerald-300 whitespace-pre-wrap">{runOutput}</pre>
              </div>
            )}

            {/* CTA butonları */}
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => router.push(projectEntryHref(projectId, selectedProduct.id))}
                className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500"
              >
                {selectedProduct.shortName} calisma alanini ac →
              </button>
              <button
                onClick={() => router.push(`/p/${projectId}`)}
                className="rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-white"
              >
                Proje Özetine git
              </button>
              <button
                onClick={() => router.push(`/p/${projectId}/${productGuide.recommendedPath}`)}
                className="rounded-xl border border-violet-500/20 bg-violet-500/10 px-6 py-2.5 text-sm font-medium text-violet-100 transition hover:border-violet-400/30 hover:bg-violet-500/15"
              >
                Onerilen adim: {selectedProduct.shortName}
              </button>
              <button
                onClick={() => router.push("/")}
                className="rounded-xl border border-slate-700 px-6 py-2.5 text-sm font-medium text-slate-400 transition hover:border-slate-500 hover:text-white"
              >
                Ana Sayfa
              </button>
            </div>
          </div>
        )}
          </div>

          {/* Sağ sticky context paneli (xl+) */}
          <aside className="hidden xl:block">
            <div className="sticky top-6 space-y-4">
              {/* Aktif ürün kartı */}
              <div className="rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/10 via-slate-900 to-slate-950 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-violet-200/80">
                  Product Focus
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <h3 className="text-base font-semibold text-white">{selectedProduct.name}</h3>
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${PRODUCT_AVAILABILITY_META[selectedProduct.availability].className}`}>
                    {PRODUCT_AVAILABILITY_META[selectedProduct.availability].label}
                  </span>
                </div>
                <p className="mt-1 text-xs text-violet-200/90">{selectedProduct.tagline}</p>
                <p className="mt-3 text-xs leading-5 text-slate-400">{productGuide.description}</p>
                <p className="mt-3 rounded-lg border border-slate-800 bg-slate-950/60 px-2.5 py-2 text-[11px] leading-5 text-slate-400">
                  Wizard sonunda önce{" "}
                  <span className="font-semibold text-slate-200">{selectedProduct.shortName}</span>{" "}
                  yüzeyine indireceğim.
                </p>
              </div>

              {/* Ürün değiştirici */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Ürünü değiştir
                </p>
                <div className="mt-3 grid grid-cols-2 gap-1.5">
                  {PRODUCT_FAMILY.map((product) => (
                    <button
                      key={product.id}
                      type="button"
                      onClick={() => applyProduct(product.id)}
                      className={`rounded-lg border px-2 py-1.5 text-left transition ${
                        product.id === selectedProduct.id
                          ? "border-violet-300/40 bg-violet-400/15 text-violet-50"
                          : "border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                      }`}
                    >
                      <span className="block text-[9px] font-semibold uppercase tracking-[0.14em]">
                        {product.shortName}
                      </span>
                      <span className="mt-0.5 block text-[10px] leading-tight">{product.tagline}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Bu adımda kartı */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Bu adımda
                </p>
                <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-white">
                  <span className="text-base">{STEPS[step - 1]?.icon}</span>
                  {STEPS[step - 1]?.label}
                </p>
                <p className="mt-1 text-xs leading-5 text-slate-400">
                  {STEPS[step - 1]?.desc}
                </p>
                <div className="mt-3 border-t border-slate-800 pt-3">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    Odak akışı
                  </p>
                  <p className="mt-1.5 text-xs font-medium text-slate-200">{productGuide.title}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {selectedProduct.routeSegments.slice(0, 4).map((segment) => (
                      <span
                        key={segment}
                        className="rounded-full border border-slate-700 bg-slate-950 px-1.5 py-0.5 text-[9px] font-medium text-slate-400"
                      >
                        {segment}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>

      {/* ── Lokator Modal ── */}
      {locatorModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div>
              <h3 className="text-base font-semibold text-white">🤖 AI Lokator Önerisi</h3>
              <p className="mt-1 text-sm text-slate-400">
                <span className="text-red-400 font-mono">&quot;{locatorModal.key}&quot;</span> için AI önerisi:
              </p>
            </div>

            {locatorModal.aiSuggestion === null ? (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                AI lokator arıyor…
              </div>
            ) : (
              <pre className="rounded-lg bg-slate-950 p-3 text-xs text-emerald-400 font-mono overflow-auto max-h-48">
                {locatorModal.aiSuggestion}
              </pre>
            )}

            <div className="flex gap-3">
              {locatorModal.aiSuggestion !== null && (() => {
                let entry: LocatorEntry | null = null;
                try { entry = JSON.parse(locatorModal.aiSuggestion); } catch { /* */ }
                return entry ? (
                  <button
                    type="button"
                    onClick={() => confirmLocator(entry!)}
                    className="flex-1 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500"
                  >
                    ✓ Onayla & Kaydet
                  </button>
                ) : null;
              })()}
              <button
                type="button"
                onClick={() => setLocatorModal(null)}
                className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-400 transition hover:border-slate-500 hover:text-white"
              >
                Kapat
              </button>
            </div>
          </div>
        </div>

        <button
          onClick={handleCreate}
          disabled={loading || !projectName.trim()}
          data-testid="new-project-btn-create"
          className="mt-6 rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-40"
        >
          {loading ? "Oluşturuluyor…" : "Projeyi Oluştur"}
        </button>
      </div>
    </div>
  );
}
