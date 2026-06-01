"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { getToken } from "@/lib/api-client";

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
      { label: "Visium Farm",    segment: "mobile" },
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

export default function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { projectId: string };
}) {
  const pathname = usePathname();
  const { projectId } = params;

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
    let cancelled = false;
    (async () => {
      try {
        // Use the SAME auth path other API consumers (monkey, etc) use:
        // raw fetch with Bearer header, so we get the same view of the project.
        // Mixing apiFetch (cookie-only) with Bearer-callers could mask a
        // user-mismatch where cookie sees the project but bearer doesn't.
        const token = getToken();
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(`/api/v1/tspm/projects/${projectId}`, {
          credentials: "include",
          headers,
        });
        if (cancelled) return;
        if (res.ok) {
          setProjectState("valid");
          return;
        }
        if (res.status === 401) {
          setProjectState("auth-error");
          setProjectErrorDetail("Oturum süresi dolmuş.");
        } else if (res.status === 403) {
          setProjectState("invalid");
          setProjectErrorDetail("Bu projeye erişim yetkiniz yok.");
        } else if (res.status === 404) {
          setProjectState("invalid");
          setProjectErrorDetail("Bu proje silinmiş veya başka bir hesapta tanımlı.");
          try { localStorage.removeItem("bgts_active_project"); } catch { /* ignore */ }
        } else {
          setProjectState("invalid");
          setProjectErrorDetail(`Backend hatası: ${res.status}`);
        }
      } catch {
        if (cancelled) return;
        setProjectState("invalid");
        setProjectErrorDetail("Bağlantı hatası");
      }
    })();
    return () => { cancelled = true; };
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

  // While checking, show a tiny inline indicator so the user doesn't
  // start interacting (e.g. clicking Başlat) on a page that's about to
  // be replaced by an error banner. Avoids the "click → 404 → confusion" loop.
  if (projectState === "checking") {
    return (
      <div className="flex items-center justify-center min-h-[60vh] p-6">
        <div className="text-center">
          <div className="inline-flex gap-1.5 mb-3">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: "0.15s" }} />
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: "0.3s" }} />
          </div>
          <p className="text-xs text-slate-400">Proje doğrulanıyor…</p>
          <p className="mt-4 text-[10px] font-mono text-slate-700">layout v=2026-05-15-14:00 bearer</p>
        </div>
      </div>
    );
  }

  // Show fullscreen recovery banner instead of broken child pages
  if (projectState === "invalid" || projectState === "format-error" || projectState === "auth-error") {
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

  return (
    <div className="flex flex-col min-h-full">
      {/* Grup sekmeleri — üst bar */}
      <div className="border-b border-slate-800 bg-slate-900 sticky top-0 z-10">
        {/* Grup seçimi */}
        <div className="flex items-center gap-1 px-4 pt-2 overflow-x-auto scrollbar-none">
          {TAB_GROUPS.map(group => {
            const isActive = group.label === activeGroup.label;
            const firstHref = `/p/${projectId}/${group.tabs[0].segment}`;
            return (
              <Link
                key={group.label}
                href={firstHref}
                className={cn(
                  "shrink-0 px-3 py-1.5 text-xs font-semibold rounded-t-lg transition-colors border-b-2",
                  isActive
                    ? "text-blue-400 border-blue-400 bg-slate-800"
                    : "text-slate-500 border-transparent hover:text-slate-300 hover:bg-slate-800/50"
                )}
              >
                {group.label}
              </Link>
            );
          })}
        </div>

        {/* Aktif grubun sekmeleri */}
        <div className="flex items-center gap-0.5 px-4 py-1.5 overflow-x-auto scrollbar-none">
          {activeGroup.tabs.map(tab => {
            const href = `/p/${projectId}/${tab.segment}`;
            const isActive = activeSegment === tab.segment;
            return (
              <Link
                key={tab.segment}
                href={href}
                className={cn(
                  "shrink-0 px-3 py-1 text-xs font-medium rounded-md transition-all duration-150",
                  isActive
                    ? "bg-blue-900/30 text-blue-400"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                )}
              >
                {tab.label}
              </Link>
            );
          })}
        </div>
      </div>

      {/* Sayfa içeriği */}
      <div className="flex-1">
        {children}
      </div>
    </div>
  );
}
