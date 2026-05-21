import { BgtestLogo } from "@/components/BgtestLogo";
import { PageHeader } from "@/components/nexus/PageHeader";

const systemInfo = {
  version: "1.0.0-beta",
  buildDate: "2026-04-03",
  environment: "Geliştirme",
  apiUrl: "http://127.0.0.1:8000",
  nextVersion: "14.2.21",
  reactVersion: "18.3.x",
};

const systemInfoLabels: Record<string, string> = {
  version: "Sürüm",
  buildDate: "Derleme Tarihi",
  environment: "Ortam",
  apiUrl: "API Adresi",
  nextVersion: "Next.js",
  reactVersion: "React",
};

const features = [
  { name: "Test Senaryosu Yönetimi", status: "Aktif" },
  { name: "Otomatik Test Koşulları", status: "Aktif" },
  { name: "Akış Tabanlı Test Tasarımı", status: "Aktif" },
  { name: "Regresyon Analizi", status: "Aktif" },
  { name: "Onay Mekanizması", status: "Aktif" },
  { name: "BDD Senaryo Üretimi", status: "Aktif" },
  { name: "Kullanıcı Yönetimi", status: "Aktif" },
  { name: "Raporlama", status: "Aktif" },
  { name: "AI Asistan", status: "Aktif" },
  { name: "Denetim Günlüğü", status: "Aktif" },
  { name: "E-posta Bildirimleri", status: "Pasif" },
];

export default function InfoPage() {
  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-6" data-testid="info-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        }
        title="Sistem Bilgileri"
        description="Platform sürümü, yapılandırma ve özellik durumları."
        data-testid="info-heading"
      />

      {/* Platform card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
        <div className="flex items-center gap-4 border-b border-slate-800 pb-6 mb-6">
          <BgtestLogo className="h-10" />
          <div>
            <h2 className="text-lg font-semibold text-white">
              Neurex QA Operations
            </h2>
            <p className="text-sm text-slate-400">
              Neurex ürün ailesi için operasyonel kalite çekirdeği
            </p>
          </div>
        </div>

        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Sistem
        </h3>
        <div className="grid gap-2 sm:grid-cols-2">
          {Object.entries(systemInfo).map(([key, value]) => (
            <div
              key={key}
              className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3"
            >
              <span className="text-sm text-slate-400">{systemInfoLabels[key]}</span>
              <span className="text-sm font-medium text-white font-mono">{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Features card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Özellikler
        </h3>
        <div className="divide-y divide-slate-800/50">
          {features.map((f) => (
            <div
              key={f.name}
              className="flex items-center justify-between py-3"
            >
              <span className="text-sm text-slate-300">{f.name}</span>
              <span
                className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                  f.status === "Aktif"
                    ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                    : "border-slate-700 bg-slate-800/50 text-slate-400"
                }`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${f.status === "Aktif" ? "bg-emerald-400" : "bg-slate-500"}`} />
                {f.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      <p className="text-center text-xs text-slate-700">
        © {new Date().getFullYear()} Neurex — Tüm hakları saklıdır.
      </p>
    </div>
  );
}
