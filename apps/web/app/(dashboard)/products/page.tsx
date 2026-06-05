import Link from "next/link";

// ── Chart skeleton blocks ───────────────────────────────────────────────────

function ChartSkeleton({ label, height = "h-32" }: { label: string; height?: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 flex flex-col gap-3">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</p>
      <div className={`${height} w-full rounded-xl bg-slate-800/60 flex items-end gap-1.5 px-3 pb-3`}>
        {[55, 72, 60, 85, 68, 91, 78, 83, 65, 88, 74, 95].map((h, i) => (
          <div
            key={i}
            className="flex-1 rounded-sm bg-indigo-500/25"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
    </div>
  );
}

function SparklineSkeleton({ label }: { label: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 flex items-center gap-4">
      <div className="flex-1">
        <p className="text-xs text-slate-500 mb-1">{label}</p>
        <div className="h-2 w-20 rounded-full bg-slate-700" />
      </div>
      <div className="w-20 h-8 flex items-end gap-0.5">
        {[4, 6, 5, 8, 6, 9, 7, 10].map((h, i) => (
          <div
            key={i}
            className="flex-1 rounded-sm bg-indigo-500/30"
            style={{ height: `${h * 10}%` }}
          />
        ))}
      </div>
    </div>
  );
}

// ── Pipeline status badges ──────────────────────────────────────────────────

const PIPELINE_ITEMS = [
  { name: "Veri toplama", status: "pending" },
  { name: "Aggregation katmanı", status: "pending" },
  { name: "Gerçek zamanlı stream", status: "pending" },
  { name: "Dashboard göstergeler", status: "ready" },
];

function PipelineStatus() {
  return (
    <ul className="space-y-2">
      {PIPELINE_ITEMS.map((item) => (
        <li key={item.name} className="flex items-center gap-3 text-sm">
          <span
            className={`w-2 h-2 rounded-full flex-shrink-0 ${
              item.status === "ready" ? "bg-emerald-400" : "bg-slate-600"
            }`}
          />
          <span className={item.status === "ready" ? "text-slate-300" : "text-slate-500"}>
            {item.name}
          </span>
          <span className="ml-auto text-xs uppercase tracking-wide font-medium">
            {item.status === "ready" ? (
              <span className="text-emerald-400">Hazır</span>
            ) : (
              <span className="text-slate-600">Bekliyor</span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function ProductAnalyticsIndexPage() {
  return (
    <div className="flex flex-col gap-8 p-6 pb-16">

      {/* Hero */}
      <section className="relative overflow-hidden rounded-3xl border border-indigo-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/30 p-8 lg:p-12">
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute -top-24 -right-24 h-80 w-80 rounded-full bg-indigo-500/10 blur-3xl" />
          <div className="absolute -bottom-16 -left-16 h-56 w-56 rounded-full bg-blue-500/8 blur-2xl" />
        </div>

        <div className="relative max-w-2xl">
          <span className="inline-block mb-4 text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/25">
            Analytics Dashboard
          </span>
          <h1 className="text-4xl lg:text-5xl font-extrabold text-white mb-4 leading-tight">
            Product{" "}
            <span className="bg-gradient-to-r from-indigo-400 to-blue-400 bg-clip-text text-transparent">
              Analytics
            </span>
          </h1>
          <p className="text-base text-slate-400 leading-relaxed mb-6">
            Analytics dashboard will be available once the data pipeline is fully
            configured. Select a specific product below to view its current telemetry,
            or wait for the pipeline to complete to see aggregated cross-product metrics
            here.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/products/one"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-blue-600 text-white font-semibold text-sm hover:opacity-90 transition-opacity shadow-lg shadow-indigo-500/25"
            >
              One — Platform Overview
            </Link>
            <Link
              href="/products/web"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/8 text-white border border-white/10 font-medium text-sm hover:bg-white/12 transition-colors"
            >
              Web Analytics
            </Link>
          </div>
        </div>
      </section>

      {/* Pipeline status */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-sm font-semibold text-white mb-4">Pipeline Durumu</h2>
          <p className="text-xs text-slate-500 mb-4">
            Gerçek veriler aşağıdaki pipeline adımları tamamlandığında otomatik olarak
            görünür hale gelecektir.
          </p>
          <PipelineStatus />
        </div>

        <div className="lg:col-span-2 flex flex-col gap-4">
          <ChartSkeleton label="Cross-product pass rate trend (son 30 gün)" height="h-40" />
          <div className="grid grid-cols-2 gap-4">
            <SparklineSkeleton label="Toplam test koşusu" />
            <SparklineSkeleton label="Ortalama pass rate" />
            <SparklineSkeleton label="Açık defect sayısı" />
            <SparklineSkeleton label="AI senaryo üretimi" />
          </div>
        </div>
      </section>

      {/* Placeholder charts row */}
      <section>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-4">
          Gelecekte burada görünecek grafikler
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <ChartSkeleton label="Ürün bazlı başarı oranı" height="h-28" />
          <ChartSkeleton label="Günlük test hacmi" height="h-28" />
          <ChartSkeleton label="Defect yoğunluk haritası" height="h-28" />
        </div>
      </section>

      {/* Product quick links */}
      <section>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-4">
          Ürün sayfalarına hızlı erişim
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {[
            { id: "one",          label: "One",          color: "text-indigo-400" },
            { id: "studio",       label: "Studio",       color: "text-purple-400" },
            { id: "service",      label: "Service",      color: "text-sky-400" },
            { id: "web",          label: "Web",          color: "text-emerald-400" },
            { id: "mobile",       label: "Mobile",       color: "text-rose-400" },
            { id: "data",         label: "Data",         color: "text-amber-400" },
            { id: "management",   label: "Management",   color: "text-teal-400" },
            { id: "intelligence", label: "Intelligence", color: "text-fuchsia-400" },
            { id: "nexus-code",   label: "Nexus Code",   color: "text-cyan-400" },
          ].map((p) => (
            <Link
              key={p.id}
              href={`/products/${p.id}`}
              className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-center hover:border-slate-700 hover:bg-slate-800 transition-colors"
            >
              <p className={`text-sm font-semibold ${p.color}`}>{p.label}</p>
              <p className="text-xs text-slate-500 mt-0.5">Analytics</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
