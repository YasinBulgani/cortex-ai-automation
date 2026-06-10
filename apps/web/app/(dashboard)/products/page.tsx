"use client";

import Link from "next/link";
import { PRODUCT_AVAILABILITY_META, PRODUCT_FAMILY, getProductEntryHref, getProductLandingHref, type ProductFamilyId } from "@/lib/product";
import { PRODUCT_BRAND } from "@/lib/products/brand";
import { useProject } from "@/lib/useProject";

const WORKSTREAMS = [
  {
    title: "Tasarla",
    description: "Gereksinim, coverage ve AI destekli test tasarımı için Studio ve Intelligence yüzeylerine gir.",
    href: "/products/studio",
  },
  {
    title: "Otomasyona Dönüştür",
    description: "Web, Mobile ve Service ürünleriyle senaryoları çalışan akışlara taşı.",
    href: "/products/web",
  },
  {
    title: "Çalıştır",
    description: "Projeye göre senaryo, run, cihaz ve servis akışlarını tek omurgada başlat.",
    href: "/portfolio",
  },
  {
    title: "İyileştir",
    description: "Flaky, görsel fark, erişilebilirlik ve AI öngörülerini ürün bazlı incele.",
    href: "/products/one",
  },
];

function ProductCard({ productId, name, shortName, tagline, availability }: {
  productId: ProductFamilyId;
  name: string;
  shortName: string;
  tagline: string;
  availability: keyof typeof PRODUCT_AVAILABILITY_META;
}) {
  const brand = PRODUCT_BRAND[productId];
  const meta = PRODUCT_AVAILABILITY_META[availability];
  const { projectId } = useProject();
  const primaryHref = getProductEntryHref(projectId, productId);
  const landingHref = getProductLandingHref(productId);

  return (
    <article className={`rounded-2xl border ${brand.border} bg-slate-900/70 p-5 transition-colors hover:bg-slate-900`}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className={`flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br ${brand.gradient} text-sm font-bold text-white shadow-lg ${brand.glow}`}>
          {shortName.slice(0, 2).toUpperCase()}
        </div>
        <span className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${meta.className}`}>
          {meta.label}
        </span>
      </div>

      <div className="space-y-2">
        <h2 className="text-lg font-semibold text-white">{name}</h2>
        <p className="text-sm leading-relaxed text-slate-400">{tagline}</p>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        <Link
          href={primaryHref}
          className={`inline-flex items-center gap-2 rounded-xl bg-gradient-to-r ${brand.gradient} px-4 py-2 text-sm font-semibold text-white shadow-lg ${brand.glow} hover:opacity-90`}
        >
          {projectId ? "Projede Aç" : "Projeyle Aç"}
        </Link>
        <Link
          href={landingHref}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700"
        >
          Ürün yüzeyi
        </Link>
      </div>

      <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-xs text-slate-500">
        {projectId
          ? "Aktif proje seçili. İlk düğme doğrudan proje içindeki ana modülü açar."
          : "Aktif proje yok. İlk düğme sizi proje seçimine götürür, ardından bu ürünün doğru modülü açılır."}
      </div>
    </article>
  );
}

export default function ProductsIndexPage() {
  const { project, projectId } = useProject();

  return (
    <div className="flex flex-col gap-8 p-6 pb-16">
      <section className="relative overflow-hidden rounded-3xl border border-indigo-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/30 p-8 lg:p-10">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-20 -right-20 h-72 w-72 rounded-full bg-indigo-500/10 blur-3xl" />
          <div className="absolute -bottom-20 -left-10 h-56 w-56 rounded-full bg-cyan-500/10 blur-3xl" />
        </div>

        <div className="relative grid gap-8 lg:grid-cols-[1.6fr_1fr]">
          <div>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-indigo-500/25 bg-indigo-500/15 px-3 py-1 text-xs font-bold uppercase tracking-widest text-indigo-300">
                Ürün Suite Girişi
              </span>
              {project ? (
                <span className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200">
                  Aktif proje: <span className="font-semibold text-white">{project.name}</span>
                </span>
              ) : (
                <span className="rounded-full border border-slate-700 bg-slate-800/80 px-3 py-1 text-xs text-slate-300">
                  Henüz aktif proje seçilmedi
                </span>
              )}
            </div>

            <h1 className="max-w-3xl text-4xl font-extrabold leading-tight text-white lg:text-5xl">
              Tüm ürün ailesi için
              <span className="bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent"> tek giriş yüzeyi</span>
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-relaxed text-slate-400">
              Bu sayfa artık “yakında” vitrini değil. Hangi ürüne gireceğini seç, aktif proje varsa doğru modüle düş, yoksa proje seçip aynı niyetle devam et.
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href={projectId ? "/products/web" : "/portfolio"}
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 hover:opacity-90"
              >
                {projectId ? "LLM-first Web workbench'e git" : "Önce proje seç"}
              </Link>
              <Link
                href="/portfolio"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-5 py-3 text-sm font-medium text-slate-200 hover:bg-slate-700"
              >
                Portföyü aç
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Ürün</p>
              <p className="mt-2 text-2xl font-bold text-white">{PRODUCT_FAMILY.length}</p>
              <p className="mt-1 text-xs text-slate-500">tek shell altında</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Çalışma modu</p>
              <p className="mt-2 text-2xl font-bold text-white">{projectId ? "Bağlı" : "Hazır"}</p>
              <p className="mt-1 text-xs text-slate-500">{projectId ? "proje context'i bulundu" : "proje seçimi bekleniyor"}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">İlk hedef</p>
              <p className="mt-2 text-sm font-semibold text-white">{projectId ? "doğru modüle git" : "niyetini koruyarak proje seç"}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Odak</p>
              <p className="mt-2 text-sm font-semibold text-white">tasarım, otomasyon, çalıştırma, kalite</p>
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">Çalışma akışı</h2>
            <p className="mt-1 text-sm text-slate-400">Ürünleri iş adımına göre düşünmek için hızlı harita.</p>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {WORKSTREAMS.map((item) => (
            <Link
              key={item.title}
              href={item.href}
              className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 transition-colors hover:border-slate-700 hover:bg-slate-900"
            >
              <p className="text-sm font-semibold text-white">{item.title}</p>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{item.description}</p>
              <p className="mt-4 text-xs font-medium text-indigo-300">Aç →</p>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">Ürünler</h2>
            <p className="mt-1 text-sm text-slate-400">Her ürün kartı landing yüzeyini ve proje içi ana girişini birlikte sunar.</p>
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          {PRODUCT_FAMILY.map((product) => (
            <ProductCard
              key={product.id}
              productId={product.id as ProductFamilyId}
              name={product.name}
              shortName={product.shortName}
              tagline={product.tagline}
              availability={product.availability}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
