"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { useProjects } from "@/lib/hooks";
import { useProject } from "@/lib/useProject";
import { getSegmentLabel } from "@/lib/product";

interface SearchResult {
  type: "project" | "page" | "project-page";
  label: string;
  href: string;
  hint: string;
  keywords: string[];
}

const GLOBAL_PAGES: SearchResult[] = [
  { type: "page", label: "Visium Giriş", href: "/", hint: "Başlangıç noktası", keywords: ["home", "landing", "giris", "portfoy"] },
  { type: "page", label: "Portföy Görünümü", href: "/portfolio", hint: "Operasyon özeti ve genel sağlık görünümü", keywords: ["dashboard", "portfoy", "operasyon", "ozet"] },
  { type: "page", label: "Projeler", href: "/projects", hint: "Tüm projeleri görüntüle", keywords: ["portfoy", "workspace", "projeler"] },
  { type: "page", label: "Yeni Proje", href: "/new-project", hint: "Yeni çalışma alanı oluştur", keywords: ["olustur", "wizard", "baslat"] },
  { type: "page", label: "Akış Sihirbazı", href: "/bgtest-wizard", hint: "Adım adım başlangıç", keywords: ["wizard", "akilli", "setup", "kurulum"] },
  { type: "page", label: "Veri Kaynağı", href: "/veri-kaynagi", hint: "Veri kaynaklarını yönet", keywords: ["data", "veri"] },
  { type: "page", label: "Veri Simülatörü", href: "/veri-simulatoru", hint: "Sentetik veri yüzeyi", keywords: ["simulator", "sentetik"] },
  { type: "page", label: "Profil", href: "/profile", hint: "Hesap ve oturum bilgileri", keywords: ["account", "profil", "user"] },
  { type: "page", label: "Yenilikler", href: "/info/whats-new", hint: "Son değişiklikler", keywords: ["duyuru", "release", "news"] },
  { type: "page", label: "Sistem Bilgileri", href: "/info", hint: "Platform ve sürüm bilgileri", keywords: ["info", "sistem", "status"] },
];

const PROJECT_SEGMENTS = [
  "",
  "import",
  "scenarios",
  "test-data",
  "automation-gen",
  "api-testing",
  "executions",
  "reports",
  "ai-chat",
  "ai-metrics",
  "settings",
] as const;

function normalizeSearchText(value: string): string {
  return value
    .toLocaleLowerCase("tr-TR")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "");
}

function matchesQuery(result: SearchResult, query: string): boolean {
  if (!query) return true;
  const normalizedQuery = normalizeSearchText(query);
  return [result.label, result.hint, ...result.keywords].some((entry) =>
    normalizeSearchText(entry).includes(normalizedQuery),
  );
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { data: projects = [] } = useProjects();
  const { project } = useProject();

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
      setSelectedIndex(0);
    }
  }, [open]);

  const projectResults = useMemo<SearchResult[]>(
    () =>
      projects.map((item) => ({
        type: "project",
        label: item.name,
        href: `/p/${item.id}`,
        hint: "Proje özeti",
        keywords: ["project", "proje", item.description ?? ""],
      })),
    [projects],
  );

  const activeProjectResults = useMemo<SearchResult[]>(() => {
    if (!project?.id) return [];
    return PROJECT_SEGMENTS.map((segment) => ({
      type: "project-page",
      label: segment ? `${project.name} · ${getSegmentLabel(segment)}` : `${project.name} · Proje Özeti`,
      href: segment ? `/p/${project.id}/${segment}` : `/p/${project.id}`,
      hint: "Aktif proje içinde gezin",
      keywords: [project.name, segment, getSegmentLabel(segment), "aktif proje"],
    }));
  }, [project]);

  const results = useMemo(() => {
    const merged = [...activeProjectResults, ...projectResults, ...GLOBAL_PAGES];
    const unique = merged.filter((result, index) => merged.findIndex((item) => item.href === result.href) === index);
    return unique.filter((result) => matchesQuery(result, query)).slice(0, 12);
  }, [activeProjectResults, projectResults, query]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query, open]);

  const navigate = useCallback(
    (href: string) => {
      setOpen(false);
      router.push(href);
    },
    [router],
  );

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, Math.max(results.length - 1, 0)));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results[selectedIndex]) {
      navigate(results[selectedIndex].href);
    }
  }

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 z-[9997] bg-black/40" onClick={() => setOpen(false)} />
      <div
        className="fixed left-1/2 top-[20%] z-[9998] w-full max-w-xl -translate-x-1/2 rounded-lg border border-slate-800 bg-slate-900 shadow-2xl"
        data-testid="command-palette"
      >
        <div className="border-b border-slate-800 px-3 py-2">
          <Input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ara... (projeler, sayfalar, çalışma alanları)"
            className="border-0 bg-transparent focus:ring-0"
            data-testid="command-palette-input-search"
          />
        </div>
        <div className="max-h-72 overflow-y-auto py-1">
          {results.length === 0 && (
            <p className="px-4 py-6 text-center text-sm text-slate-400">Sonuç bulunamadı</p>
          )}
          {results.map((result, index) => (
            <button
              key={result.href}
              type="button"
              onClick={() => navigate(result.href)}
              className={`flex w-full items-start gap-3 px-4 py-3 text-left text-sm transition-colors ${
                index === selectedIndex ? "bg-blue-500/10 text-blue-300" : "hover:bg-white/5"
              }`}
              data-testid={`command-palette-result-${index}`}
            >
              <span className="mt-0.5 text-[11px] uppercase tracking-[0.18em] text-slate-500">
                {result.type === "project" ? "Proje" : result.type === "project-page" ? "Alan" : "Sayfa"}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-white">{result.label}</span>
                <span className="block truncate text-xs text-slate-400">{result.hint}</span>
              </span>
            </button>
          ))}
        </div>
        <div className="border-t border-slate-800 px-4 py-2 text-[10px] text-slate-400">
          <kbd className="rounded border border-slate-800 px-1.5 py-0.5">↑↓</kbd> gezin{" "}
          <kbd className="rounded border border-slate-800 px-1.5 py-0.5">Enter</kbd> seç{" "}
          <kbd className="rounded border border-slate-800 px-1.5 py-0.5">Esc</kbd> kapat
        </div>
      </div>
    </>
  );
}
