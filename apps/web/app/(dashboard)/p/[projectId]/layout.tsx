"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { ApiError, apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

// TAB_GROUPS ve activeGroup artık render için kullanılmıyor;
// layout sadece proje geçerliliğini kontrol eder.

type TabGroup = {
  label: string;
  tabs: { label: string; segment: string }[];
};

const TAB_GROUPS: TabGroup[] = [
  {
    label: "Tasarım",
    tabs: [
      { label: "Senaryolar",    segment: "scenarios" },
      { label: "Manuel",        segment: "manual" },
      { label: "Gereksinimler", segment: "requirements" },
      { label: "Onaylar",       segment: "approvals" },
      { label: "İçe Aktar",     segment: "import" },
    ],
  },
  {
    label: "Üretim",
    tabs: [
      { label: "Otomasyon",     segment: "automation" },
      { label: "API Test",      segment: "api-testing" },
      { label: "Kaydedici",     segment: "recorder" },
      { label: "Locator'lar",   segment: "locators" },
      { label: "Akışlar",       segment: "flows" },
      { label: "Chain Builder", segment: "chain-builder" },
      { label: "Neurex Farm",    segment: "mobile" },
      { label: "Mobil Geçmiş",  segment: "mobile/history" },
    ],
  },
  {
    label: "Koşu",
    tabs: [
      { label: "Koşular",       segment: "runs" },
      { label: "Zamanlayıcı",   segment: "schedules" },
      { label: "CI/CD",         segment: "cicd" },
      { label: "Raporlar",      segment: "reports" },
      { label: "Flaky",         segment: "flaky" },
      { label: "Self-Healing",  segment: "healing" },
    ],
  },
  {
    label: "Kalite",
    tabs: [
      { label: "Görsel",        segment: "visual" },
      { label: "Erişilebilirlik", segment: "accessibility" },
      { label: "Monkey Test",   segment: "monkey" },
      { label: "LLM Ajan",     segment: "llm-agent" },
      { label: "Güvenlik",      segment: "security" },
      { label: "Önceliklendirme", segment: "prioritize" },
      { label: "PW Konsol",     segment: "playwright-console" },
      { label: "Management",    segment: "management" },
    ],
  },
  {
    label: "Veri",
    tabs: [
      { label: "Sentetik Veri", segment: "synthetic" },
      { label: "Test Verileri", segment: "test-data" },
      { label: "Gizlilik",      segment: "privacy" },
    ],
  },
  {
    label: "Yapılandırma",
    tabs: [
      { label: "Ortamlar",      segment: "environments" },
      { label: "Entegrasyonlar",segment: "integrations" },
      { label: "Ayarlar",       segment: "settings" },
    ],
  },
];

const DEFAULT_DEMO_PROJECT_ID = "00000000-0000-0000-0000-000000000001";

export default function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { projectId: string };
}) {
  const pathname = usePathname();
  const projectId = String(params.projectId ?? "");

  // Project validity check — short-circuit all child pages if projectId is bad
  // (deleted, wrong account, malformed). Saves every page from re-implementing
  // the same 404 handling.
  type ProjectState = "checking" | "valid" | "invalid" | "auth-error" | "format-error";
  const [projectState, setProjectState] = useState<ProjectState>("checking");
  const [projectErrorDetail, setProjectErrorDetail] = useState<string>("");

  useEffect(() => {
    const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!projectId) {
      setProjectState("format-error");
      setProjectErrorDetail("Proje ID URL'de bulunamadı.");
      return;
    }
    if (!UUID_RE.test(projectId)) {
      setProjectState("format-error");
      setProjectErrorDetail(`"${projectId}" UUID formatında değil.`);
      return;
    }
    if (projectId === DEFAULT_DEMO_PROJECT_ID) {
      setProjectState("valid");
      return;
    }
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 6000);
    (async () => {
      try {
        await apiFetch<unknown>(`/api/v1/tspm/projects/${projectId}`, {
          signal: controller.signal,
        });
        window.clearTimeout(timeoutId);
        setProjectState("valid");
        return;
      } catch (err) {
        window.clearTimeout(timeoutId);
        // AbortError: ya timeout ya da projectId değişimi — state güncelleme
        if (err instanceof Error && err.name === "AbortError") return;
        // Development fallback: the default seed project may not exist in TSPM
        // yet while Management can still bootstrap its own workspace.
        if (
          process.env.NODE_ENV === "development" &&
          projectId === "00000000-0000-0000-0000-000000000001" &&
          err instanceof ApiError &&
          (err.status === 404 || err.status === 500)
        ) {
          setProjectState("valid");
          return;
        }
        if (err instanceof ApiError && err.status === 401) {
          setProjectState("auth-error");
          setProjectErrorDetail("Oturum süresi dolmuş.");
        } else if (err instanceof ApiError && err.status === 403) {
          setProjectState("invalid");
          setProjectErrorDetail("Bu projeye erişim yetkiniz yok.");
        } else if (err instanceof ApiError && err.status === 404) {
          setProjectState("invalid");
          setProjectErrorDetail("Bu proje silinmiş veya başka bir hesapta tanımlı.");
          try { localStorage.removeItem("bgts_active_project"); } catch { /* ignore */ }
        } else if (err instanceof ApiError) {
          setProjectState("invalid");
          setProjectErrorDetail(`Backend hatası: ${err.status}`);
        } else {
          if (
            process.env.NODE_ENV === "development" &&
            projectId === "00000000-0000-0000-0000-000000000001"
          ) {
            setProjectState("valid");
            return;
          }
          setProjectState("invalid");
          setProjectErrorDetail("Bağlantı hatası");
        }
      }
    })();
    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [projectId]);

  // Aktif segment'i bul
  const activeSegment = pathname
    ?.replace(`/p/${projectId}`, "")
    .replace(/^\//, "")
    .split("/")[0] ?? "";

  // Aktif grubu bul
  const activeGroup = TAB_GROUPS.find(g =>
    g.tabs.some(t => t.segment === activeSegment)
  ) ?? TAB_GROUPS[0];

  const shouldBypassProjectGate =
    projectId === DEFAULT_DEMO_PROJECT_ID ||
    Boolean(pathname?.includes(`/p/${DEFAULT_DEMO_PROJECT_ID}/`)) ||
    Boolean(pathname?.includes("/management"));

  // While checking, show a tiny inline indicator so the user doesn't
  // start interacting (e.g. clicking Başlat) on a page that's about to
  // be replaced by an error banner. Avoids the "click → 404 → confusion" loop.
  if (!shouldBypassProjectGate && projectState === "checking") {
    return (
      <div className="flex items-center justify-center min-h-[60vh] p-6">
        <div className="text-center">
          <div className="inline-flex gap-1.5 mb-3">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: "0.15s" }} />
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: "0.3s" }} />
          </div>
          <p className="text-xs text-slate-400">Proje doğrulanıyor…</p>
          <p className="mt-4 text-[10px] font-mono text-slate-700">layout v=2026-06-02 cookie-auth</p>
        </div>
      </div>
    );
  }

  // Show fullscreen recovery banner instead of broken child pages
  if (!shouldBypassProjectGate && (projectState === "invalid" || projectState === "format-error" || projectState === "auth-error")) {
    const isAuth = projectState === "auth-error";
    return (
      <div className="flex items-center justify-center min-h-[80vh] p-6">
        <div className="max-w-md w-full text-center">
          <div className="text-6xl mb-4">{isAuth ? "🔒" : "🚫"}</div>
          <h1 className="text-2xl font-bold text-white mb-2">
            {isAuth ? "Oturum Geçersiz" : "Proje Açılamadı"}
          </h1>
          <p className="text-sm text-slate-400 mb-1">{projectErrorDetail}</p>
          <p className="text-xs text-slate-600 font-mono mb-6 break-all">
            ID: {projectId}
          </p>
          <div className="flex items-center justify-center gap-3">
            {isAuth ? (
              <Link
                href="/login"
                className="px-4 py-2 rounded-lg bg-emerald-500 text-white text-sm font-semibold hover:bg-emerald-400"
              >
                Giriş Yap
              </Link>
            ) : (
              <Link
                href="/portfolio"
                className="px-4 py-2 rounded-lg bg-emerald-500 text-white text-sm font-semibold hover:bg-emerald-400"
              >
                → Portfolio'ya Git
              </Link>
            )}
            <Link
              href="/"
              className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-sm hover:bg-slate-700 border border-slate-700"
            >
              Ana Sayfa
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
