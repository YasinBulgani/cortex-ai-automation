"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiFetch } from "@/lib/api";
import { useCoreRuntime } from "@/lib/core-runtime";
import {
  PRODUCT_FAMILY_STORAGE_KEY,
  PRODUCT_LANDING_CONTENT,
  PRODUCT_AVAILABILITY_META,
  PLATFORM_BRAND,
  PRODUCT_TAGLINE,
  getDefaultEntryRouteForProduct,
  getProductEntryHref,
  getProductFamilyMember,
  getRoutesForProduct,
  type ProductFamilyId,
} from "@/lib/product";

type Project = {
  id: string;
  name: string;
  description: string;
  archived: boolean;
  last_opened_at?: string | null;
  primary_product_id?: ProductFamilyId | string | null;
  product_tags?: string[] | null;
  default_entry_key?: string | null;
};

type RecentProjectSummary = {
  project: Project;
  last_run_id: string | null;
  last_run_status: string | null;
  last_run_created_at: string | null;
  last_run_passed: number;
  last_run_failed: number;
  last_run_total: number;
  last_run_simulated: boolean;
};

type SuggestedProject = Project & {
  score: number;
  reason: string;
};

type NexusLaunchpadModule = {
  order: string;
  title: string;
  description: string;
  path: string;
  tone: "violet" | "blue" | "emerald" | "cyan" | "amber" | "slate";
  outcome: string;
};

const NEXUS_LAUNCHPAD_MODULES: NexusLaunchpadModule[] = [
  {
    order: "00",
    title: "Neurex Autopilot",
    description: "Projeyi izler, riskleri çıkarır, öneri üretir ve güvenli aksiyonları otomatik başlatır.",
    path: "autopilot",
    tone: "violet",
    outcome: "Sıfır müdahale omurgası",
  },
  {
    order: "01",
    title: "AI Asistan",
    description: "Ürün, persona ve proje hafızasını tek sohbette birleştirir.",
    path: "ai-chat",
    tone: "violet",
    outcome: "Karar ve yönlendirme",
  },
  {
    order: "02",
    title: "LLM Metrikleri",
    description: "LLM çağrılarını, başarı oranını, parse kalitesini ve operasyon sağlığını görünür kılar.",
    path: "ai-metrics",
    tone: "blue",
    outcome: "Kalite görünürlüğü",
  },
  {
    order: "03",
    title: "QA Orkestratör",
    description: "Hedef belirler, plan çıkarır, tam kalite döngüsünü çalıştırır ve sonucu aksiyona çevirir.",
    path: "qa-orchestrator",
    tone: "emerald",
    outcome: "Otonom kalite döngüsü",
  },
  {
    order: "04",
    title: "NL Test Üretici",
    description: "Türkçe brief'ten çalıştırılabilir test kodu ve güven sinyali üretir.",
    path: "nl-test-gen",
    tone: "cyan",
    outcome: "Test üretim hızı",
  },
  {
    order: "05",
    title: "Dokümandan Otomasyon",
    description: "Manuel adımı veya dokümanı Gherkin ve Playwright artefaktına dönüştürür.",
    path: "manual-to-automation",
    tone: "amber",
    outcome: "Artefakt üretimi",
  },
  {
    order: "06",
    title: "Raporlar",
    description: "Koşu ve pipeline sonuçlarını paylaşılabilir yönetim ve denetim çıktısına dönüştürür.",
    path: "reports",
    tone: "slate",
    outcome: "Paylaşılabilir çıktı",
  },
];

const NEXUS_DECISION_STEPS = [
  "Önce LLM metrik görünürlüğü ile mevcut kalite sinyalini oku.",
  "AI Asistan ile proje bağlamını, hedefi ve sonraki aksiyonu netleştir.",
  "QA Orkestratör ile planı ve otomatik kalite döngüsünü başlat.",
  "NL Test Üretici veya Dokümandan Otomasyon ile test üretim hızını artır.",
  "Raporlar ekranında sonucu paylaşılabilir çıktıya dönüştür.",
];

const toneClassName: Record<NexusLaunchpadModule["tone"], string> = {
  violet: "border-violet-400/20 bg-violet-500/10 text-violet-100",
  blue: "border-blue-400/20 bg-blue-500/10 text-blue-100",
  emerald: "border-emerald-400/20 bg-emerald-500/10 text-emerald-100",
  cyan: "border-cyan-400/20 bg-cyan-500/10 text-cyan-100",
  amber: "border-amber-400/20 bg-amber-500/10 text-amber-100",
  slate: "border-slate-700 bg-slate-900/70 text-slate-200",
};

function formatRelative(dt: string | null | undefined): string {
  if (!dt) return "—";
  const then = new Date(dt).getTime();
  if (Number.isNaN(then)) return "—";
  const diffSec = Math.round((Date.now() - then) / 1000);
  if (diffSec < 60) return `${diffSec}sn önce`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}dk önce`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}sa önce`;
  return `${Math.floor(diffSec / 86400)}g önce`;
}

function scoreProject(productId: ProductFamilyId, project: Project, recentId: string | null): SuggestedProject {
  const config = PRODUCT_LANDING_CONTENT[productId];
  const haystack = `${project.name} ${project.description ?? ""}`.toLocaleLowerCase("tr");
  let score = 0;
  const reasons: string[] = [];

  if (project.primary_product_id === productId) {
    score += 140;
    reasons.push("Ana ürün eşleşmesi");
  } else if (project.product_tags?.includes(productId)) {
    score += 90;
    reasons.push("Etkin ürün etiketi");
  }

  if (recentId && project.id === recentId) {
    score += 80;
    reasons.push("Son aktif proje");
  }

  const keywordMatches = config.projectKeywords.filter((keyword) => haystack.includes(keyword.toLocaleLowerCase("tr")));
  if (keywordMatches.length > 0) {
    score += keywordMatches.length * 12;
    reasons.push(`Ürün bağlamı eşleşmesi (${keywordMatches.slice(0, 2).join(", ")})`);
  }

  if (project.last_opened_at) {
    score += 8;
    reasons.push("Yakın zamanda açıldı");
  }

  if (!reasons.length) {
    reasons.push("Genel kullanım için uygun");
  }

  return {
    ...project,
    score,
    reason: reasons[0],
  };
}

function RuntimeBlockingPanel({ loading, reason, error }: { loading: boolean; reason: string | null; error: string | null }) {
  // auth_required durumunda panel gösterilmez — useEffect login'e yönlendirir
  if (!loading && reason === "auth_required") return null;

  const title = loading
    ? "Runtime çekirdeği kontrol ediliyor"
    : reason === "backend_down"
      ? "Servis çekirdeği hazır değil"
      : reason === "auth_preparing"
        ? "Oturum hazırlanıyor"
        : "Runtime erişimi bekleniyor";

  const body = loading
    ? "Backend, servis health ve oturum durumu kontrol ediliyor."
    : reason === "backend_down"
      ? "Ürün çalışma alanı backend hazır olmadan proje verisi çekmez. Önce servis omurgasını ayağa kaldırın."
      : reason === "auth_preparing"
        ? "Dev oturum bootstrap işlemi tamamlandığında ürün runtime otomatik açılır."
        : "Backend hazır, ancak oturum doğrulaması tamamlanmadı.";

  return (
    <section className="rounded-[32px] border border-amber-400/20 bg-slate-950/70 p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-amber-200/80">Runtime Gate</p>
      <h1 className="mt-3 text-4xl font-black tracking-tight text-white">{title}</h1>
      <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300">{body}</p>
      {error && <p className="mt-3 text-sm text-amber-200">{error}</p>}
      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          href="/system/services"
          className="inline-flex items-center justify-center rounded-2xl border border-violet-300/30 bg-violet-500/15 px-5 py-3 text-sm font-semibold text-violet-50 transition hover:border-violet-200/40 hover:bg-violet-500/25"
        >
          Servisleri aç
        </Link>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-2xl border border-slate-700 bg-slate-900/70 px-5 py-3 text-sm font-semibold text-slate-200 transition hover:border-slate-500 hover:text-white"
        >
          Ürün seçimine dön
        </Link>
      </div>
    </section>
  );
}

export function ProductLandingPage({ productId }: { productId: ProductFamilyId }) {
  const router = useRouter();
  const runtime = useCoreRuntime();
  const product = useMemo(() => PRODUCT_LANDING_CONTENT[productId], [productId]);
  const productMember = useMemo(() => getProductFamilyMember(productId), [productId]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [recent, setRecent] = useState<RecentProjectSummary | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(PRODUCT_FAMILY_STORAGE_KEY, productId);
      window.dispatchEvent(new CustomEvent("bgts-product-family-changed", { detail: productId }));
    } catch {
      // ignore
    }

    if (!runtime.canQueryProjects) {
      setProjects([]);
      setRecent(null);
      setProjectsError(null);
      return;
    }

    apiFetch<Project[]>("/api/v1/tspm/projects?include_archived=false&sort=last_opened_at")
      .then((data) => {
        setProjects(data.filter((project) => !project.archived));
        setProjectsError(null);
      })
      .catch((err: unknown) => {
        setProjects([]);
        if (err instanceof ApiError && err.status === 403) {
          setProjectsError("Bu ürün için proje listesi görüntüleme yetkiniz bulunmuyor.");
          return;
        }
        setProjectsError(null);
      });

    apiFetch<RecentProjectSummary | null>("/api/v1/tspm/projects/recent")
      .then(setRecent)
      .catch(() => setRecent(null));
  }, [productId, runtime.canQueryProjects]);

  const recentId = recent?.project?.id ?? null;
  const suggestedProjects = useMemo(() => (
    [...projects]
      .map((project) => scoreProject(productId, project, recentId))
      .sort((left, right) => right.score - left.score || left.name.localeCompare(right.name, "tr"))
      .slice(0, 4)
  ), [productId, projects, recentId]);

  const startRoute = getDefaultEntryRouteForProduct(productId);
  const moduleCards = getRoutesForProduct(productId)
    .filter((route) => route.path !== null)
    .sort((left, right) => {
      if (left.key === product.startRouteKey) return -1;
      if (right.key === product.startRouteKey) return 1;
      return left.label.localeCompare(right.label, "tr");
    })
    .slice(0, 5);

  const primaryProject = suggestedProjects[0] ?? null;
  const isNexusCode = productId === "nexus-code";
  const primaryHref = isNexusCode
    ? "/nexus-code"
    : primaryProject
      ? getProductEntryHref(primaryProject.id, productId)
      : "/new-project";
  const primaryLabel = isNexusCode
    ? "Neurex Code Agent'ı aç"
    : primaryProject ? "Önerilen projeyle devam et" : "İlk projeyi oluştur";
  const isNexusAi = productId === "intelligence";

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#172554_0%,#020617_42%,#020617_100%)] text-white">
      <header className="border-b border-slate-800/70">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-5">
          <div className="flex items-center gap-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-violet-400/20 bg-violet-500/10 shadow-[0_0_40px_rgba(139,92,246,0.14)]">
              <span className="text-sm font-black tracking-[0.2em] text-violet-100">N</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-white">{PLATFORM_BRAND.name}</span>
                <span className="rounded-full border border-slate-700 bg-slate-900/70 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-300">
                  {productId === "intelligence" ? "Neurex AI" : "Ürün Sayfası"}
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-400">{PRODUCT_TAGLINE}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="inline-flex items-center justify-center rounded-xl border border-slate-700 bg-slate-900/60 px-4 py-2 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-white"
            >
              Ürün seçimine dön
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-7xl flex-col gap-8 px-6 py-10">
        {runtime.blockingReason && (
          <RuntimeBlockingPanel
            loading={runtime.loading}
            reason={runtime.blockingReason}
            error={runtime.error}
          />
        )}

        {!runtime.blockingReason && (
          <>
        <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950/65 p-8 shadow-[0_0_0_1px_rgba(30,41,59,0.25)]">
            <div className="inline-flex items-center gap-2 rounded-full border border-violet-400/20 bg-violet-500/10 px-3 py-1 text-xs font-medium text-violet-200">
              <span className="h-1.5 w-1.5 rounded-full bg-violet-300" />
              {product.eyebrow}
            </div>

            <h1 className="mt-6 max-w-4xl text-5xl font-black tracking-tight text-white">
              {product.headline}
            </h1>

            <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-400">
              {product.summary}
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => router.push(primaryHref)}
                className="inline-flex items-center justify-center rounded-2xl border border-violet-300/30 bg-violet-500/15 px-5 py-3 text-sm font-semibold text-violet-50 transition hover:border-violet-200/40 hover:bg-violet-500/25"
              >
                {primaryLabel}
              </button>
              <Link
                href="/projects"
                className="inline-flex items-center justify-center rounded-2xl border border-slate-700 bg-slate-900/70 px-5 py-3 text-sm font-semibold text-slate-200 transition hover:border-slate-500 hover:text-white"
              >
                Tüm projeleri görüntüle
              </Link>
            </div>

            {projectsError && (
              <div className="mt-6 rounded-2xl border border-amber-400/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
                {projectsError}
              </div>
            )}

            <div className="mt-8 grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Ana çıktı</p>
                <p className="mt-2 text-lg font-semibold text-white">{product.primaryOutcome}</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Önerilen proje</p>
                <p className="mt-2 text-lg font-semibold text-white">{primaryProject?.name ?? "Henüz yok"}</p>
                <p className="mt-1 text-sm text-slate-400">{primaryProject?.reason ?? "Yeni proje ile başlanacak"}</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">İlk durak</p>
                <p className="mt-2 text-lg font-semibold text-white">{startRoute?.label ?? "Proje Özeti"}</p>
                <p className="mt-1 text-sm text-slate-400">Bu ürün için varsayılan ilk çalışma yüzeyi</p>
              </div>
            </div>
          </div>

          <div className="rounded-[28px] border border-slate-800 bg-slate-950/65 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-300/80">Başlangıç Yolu</p>
            <h2 className="mt-3 text-2xl font-semibold text-white">
              {primaryProject ? "Hazır projeyle başlayın" : "İlk çalışma alanını kurun"}
            </h2>
            <p className="mt-2 text-sm leading-7 text-slate-400">
              Bu panel bilgi kartı değil, karar panelidir. Buradaki yol kullanıcının ürün bağlamını, proje önerisini ve ilk durağını netleştirir.
            </p>

            <div className="mt-5 space-y-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">1. Ürün seçimi</p>
                <p className="mt-2 text-sm text-white">{productMember.name}</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">2. Proje bağlamı</p>
                <p className="mt-2 text-sm text-white">{primaryProject?.name ?? "Yeni proje sihirbazı öneriliyor"}</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">3. İlk durak</p>
                <p className="mt-2 text-sm text-white">{startRoute?.label ?? "Proje Özeti"}</p>
              </div>
            </div>
          </div>
        </section>

        {isNexusAi && (
          <section className="overflow-hidden rounded-[32px] border border-violet-400/20 bg-[linear-gradient(135deg,rgba(15,23,42,0.92),rgba(30,41,59,0.72),rgba(8,47,73,0.42))] p-6 shadow-[0_0_80px_rgba(99,102,241,0.10)]">
            <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
              <div className="rounded-[28px] border border-slate-800 bg-slate-950/70 p-6">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-violet-200/80">Neurex AI Launchpad</p>
                <h2 className="mt-3 text-3xl font-black tracking-tight text-white">
                  Tek girişten bütün AI kalite hattını başlat
                </h2>
                <p className="mt-3 text-sm leading-7 text-slate-300">
                  Bu alan Neurex Intelligence için merkezi komuta panelidir. Kullanıcı hangi modüle gideceğini
                  düşünmeden; görünürlük, karar, üretim, otomasyon ve rapor çıktısını aynı sırada takip eder.
                </p>

                <div className="mt-5 space-y-3">
                  {NEXUS_DECISION_STEPS.map((step, index) => (
                    <div key={step} className="flex gap-3 rounded-2xl border border-slate-800 bg-slate-950/70 p-3">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-violet-400/20 bg-violet-500/10 text-xs font-black text-violet-100">
                        {index + 1}
                      </span>
                      <p className="text-sm leading-6 text-slate-300">{step}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-5 flex flex-wrap gap-2">
                  {primaryProject ? (
                    <>
                      <Link
                        href={`/p/${primaryProject.id}/ai-metrics`}
                        className="inline-flex items-center justify-center rounded-2xl border border-blue-300/30 bg-blue-500/15 px-5 py-3 text-sm font-semibold text-blue-50 transition hover:border-blue-200/40 hover:bg-blue-500/25"
                      >
                        LLM görünürlüğü ile başla
                      </Link>
                      <Link
                        href={`/p/${primaryProject.id}/qa-orchestrator`}
                        className="inline-flex items-center justify-center rounded-2xl border border-violet-300/30 bg-violet-500/15 px-5 py-3 text-sm font-semibold text-violet-50 transition hover:border-violet-200/40 hover:bg-violet-500/25"
                      >
                        Orkestratörü aç
                      </Link>
                    </>
                  ) : (
                    <Link
                      href="/new-project"
                      className="inline-flex items-center justify-center rounded-2xl border border-violet-300/30 bg-violet-500/15 px-5 py-3 text-sm font-semibold text-violet-50 transition hover:border-violet-200/40 hover:bg-violet-500/25"
                    >
                      Önce proje oluştur
                    </Link>
                  )}
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                {NEXUS_LAUNCHPAD_MODULES.map((module) => {
                  const href = primaryProject ? `/p/${primaryProject.id}/${module.path}` : "/projects";
                  return (
                    <Link
                      key={module.path}
                      href={href}
                      className="group rounded-[26px] border border-slate-800 bg-slate-950/68 p-5 transition hover:-translate-y-0.5 hover:border-slate-600 hover:bg-slate-950/90"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <span className={`rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] ${toneClassName[module.tone]}`}>
                          {module.order}
                        </span>
                        <span className="text-xs text-slate-500 transition group-hover:text-slate-300">Aç →</span>
                      </div>
                      <h3 className="mt-4 text-xl font-bold text-white">{module.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-slate-400">{module.description}</p>
                      <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/70 px-3 py-2">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">Çıktı</p>
                        <p className="mt-1 text-sm font-semibold text-white">{module.outcome}</p>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          </section>
        )}

        <section className="grid gap-4 rounded-[28px] border border-slate-800 bg-slate-950/65 p-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-violet-200/80">Modüller</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Bu ürün için öne çıkan duraklar</h2>
              </div>
              <span className="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-xs text-slate-300">
                {moduleCards.length} modül görünür
              </span>
            </div>

            <div className="mt-6 grid gap-3 md:grid-cols-2">
              {moduleCards.map((route) => (
                <div
                  key={route.key}
                  className={`rounded-[24px] border p-5 ${route.key === product.startRouteKey ? "border-violet-400/20 bg-violet-500/8" : "border-slate-800 bg-slate-900/60"}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-lg font-semibold text-white">{route.label}</h3>
                    {route.key === product.startRouteKey && (
                      <span className="rounded-full border border-violet-400/20 bg-violet-500/10 px-2 py-1 text-[10px] font-semibold text-violet-200">
                        İlk durak
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-sm leading-7 text-slate-400">
                    {route.label}, {productId === "intelligence" ? "QA Lead için görünürlükten aksiyona giden ürün akışının" : "ürün bağlamlı çalışma yüzeyinin"} önemli parçalarından biridir.
                  </p>
                  {primaryProject && (
                    <Link
                      href={route.path ? `/p/${primaryProject.id}/${route.path}` : `/p/${primaryProject.id}`}
                      className="mt-4 inline-flex items-center justify-center rounded-xl border border-slate-700 bg-slate-950/70 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-500 hover:text-white"
                    >
                      {route.label} aç
                    </Link>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-800 bg-slate-900/60 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-300/80">Önerilen Projeler</p>
            <h2 className="mt-2 text-2xl font-semibold text-white">Ürün bağlamına göre öncelikli girişler</h2>
            <p className="mt-2 text-sm leading-7 text-slate-400">
              Seçilen ürün odağına göre en uygun proje girişlerini öneriyoruz. Öncelik; son aktif proje, bağlam eşleşmesi ve güncelliğe göre hesaplanır.
            </p>

            <div className="mt-5 space-y-3">
              {suggestedProjects.length > 0 ? suggestedProjects.map((project) => (
                <div key={project.id} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-white">{project.name}</p>
                      <p className="mt-1 text-xs text-slate-400">{project.reason}</p>
                      <p className="mt-2 text-xs text-slate-500">{formatRelative(project.last_opened_at)}</p>
                    </div>
                    <span className="rounded-full border border-slate-700 bg-slate-900/80 px-2 py-1 text-[10px] font-semibold text-slate-300">
                      skor {project.score}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Link
                      href={getProductEntryHref(project.id, productId)}
                      className="inline-flex items-center justify-center rounded-xl border border-violet-300/30 bg-violet-500/15 px-4 py-2 text-sm font-semibold text-violet-50 transition hover:border-violet-200/40 hover:bg-violet-500/25"
                    >
                      Bu projeyle başla
                    </Link>
                    <Link
                      href={`/p/${project.id}`}
                      className="inline-flex items-center justify-center rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-500 hover:text-white"
                    >
                      Proje özeti
                    </Link>
                  </div>
                </div>
              )) : (
                <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-6 text-sm text-slate-400">
                  Bu ürün için önerilebilecek proje bulunamadı. Yeni proje başlatıp ürün bağlamını ilk kayıtta oluşturabiliriz.
                </div>
              )}
            </div>
          </div>
        </section>
          </>
        )}
      </main>
    </div>
  );
}
