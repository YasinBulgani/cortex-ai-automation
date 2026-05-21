"use client";

/**
 * What's New — Ürün Değişiklik Günlüğü
 * Yeni özellikler, iyileştirmeler ve düzeltmeler sprint bazında gösterilir.
 */

import { PageHeader } from "@/components/nexus/PageHeader";

type Entry = {
  version: string;
  date: string;
  badge: "new" | "improved" | "fix" | "infra";
  title: string;
  description: string;
  tags?: string[];
};

type Release = {
  sprint: string;
  date: string;
  entries: Entry[];
};

const BADGE_CFG: Record<Entry["badge"], { label: string; cls: string }> = {
  new:      { label: "Yeni",      cls: "bg-indigo-500/15 text-indigo-300 border-indigo-500/25" },
  improved: { label: "İyileştirme", cls: "bg-blue-500/15 text-blue-300 border-blue-500/25" },
  fix:      { label: "Düzeltme",  cls: "bg-amber-500/15 text-amber-300 border-amber-500/25" },
  infra:    { label: "Altyapı",   cls: "bg-slate-600/40 text-slate-300 border-slate-600/50" },
};

const RELEASES: Release[] = [
  {
    sprint: "Sprint 10 — Prod Hazırlık + Gerçek Cihaz",
    date: "15 Nisan 2026",
    entries: [
      {
        version: "1.10.0",
        date: "15 Nis",
        badge: "new",
        title: "BrowserStack & Sauce Labs Entegrasyonu",
        description: "Visium Farm artık BROWSERSTACK_USERNAME / SAUCE_USERNAME ayarlandığında testleri gerçek bulut cihazlarında çalıştırıyor. Yerel Playwright emülasyonu otomatik fallback olarak korunuyor.",
        tags: ["Visium Farm", "Mobile"],
      },
      {
        version: "1.10.0",
        date: "15 Nis",
        badge: "new",
        title: "Onboarding Wizard",
        description: "Yeni kullanıcılar 3 adımda (proje → senaryo → ilk koşum) sistemi öğreniyor. Projesiz girişlerde otomatik yönlendirme.",
        tags: ["UX"],
      },
      {
        version: "1.10.0",
        date: "15 Nis",
        badge: "new",
        title: "Execution Bildirimleri",
        description: "Koşum tamamlandığında veya başarısız olduğunda e-posta ve Slack Incoming Webhook bildirimleri. Profil sayfasından kanallar ve tercihler ayarlanabiliyor.",
        tags: ["Bildirimler", "Slack"],
      },
      {
        version: "1.10.0",
        date: "15 Nis",
        badge: "new",
        title: "CSV Export + Allure İndirme",
        description: "Execution listesinden filtrelenmiş koşuları CSV olarak indirebilir, tamamlanmış koşular için Allure JSON export alabilirsiniz.",
        tags: ["Raporlama"],
      },
      {
        version: "1.10.0",
        date: "15 Nis",
        badge: "improved",
        title: "GitHub Actions YAML Şablonu",
        description: "CI/CD sayfasına hazır GitHub Actions workflow YAML'ı ve trigger URL paneli eklendi. Tek tıkla kopyalama.",
        tags: ["CI/CD"],
      },
      {
        version: "1.10.0",
        date: "15 Nis",
        badge: "infra",
        title: "k6 Yük Testi",
        description: "4 senaryo (smoke/load/stress/spike) içeren k6 yük testi eklendi. make test-load ile çalıştırılabilir.",
        tags: ["Altyapı", "QA"],
      },
    ],
  },
  {
    sprint: "Sprint 9 — Monitoring + Production Deploy",
    date: "14 Nisan 2026",
    entries: [
      {
        version: "1.9.0",
        date: "14 Nis",
        badge: "new",
        title: "Sentry Hata İzleme",
        description: "Backend (FastAPI) ve Frontend (Next.js) için Sentry entegrasyonu. SENTRY_DSN ayarlandığında aktif.",
        tags: ["Monitoring"],
      },
      {
        version: "1.9.0",
        date: "14 Nis",
        badge: "new",
        title: "Prometheus + Grafana",
        description: "/metrics endpoint'i, docker-compose.prod.yml'a Prometheus scraping ve Grafana provisioning eklendi.",
        tags: ["Monitoring", "Altyapı"],
      },
      {
        version: "1.9.0",
        date: "14 Nis",
        badge: "infra",
        title: "Kubernetes Manifestleri",
        description: "HPA (2-6 replika), cert-manager TLS, non-root securityContext, PVC'ler ile production K8s deployment.",
        tags: ["Altyapı", "K8s"],
      },
      {
        version: "1.9.0",
        date: "14 Nis",
        badge: "infra",
        title: "Nginx Production Konfigürasyonu",
        description: "TLS 1.2/1.3, HSTS, CSP, rate limiting (api/auth/ai ayrı zone), SSE buffering, gzip sıkıştırma.",
        tags: ["Altyapı"],
      },
    ],
  },
  {
    sprint: "Sprint 8 — Visium Farm Scheduler + Mobil Geçmiş",
    date: "13 Nisan 2026",
    entries: [
      {
        version: "1.8.0",
        date: "13 Nis",
        badge: "new",
        title: "Mobil Koşum Scheduler",
        description: "Zamanlayıcı sayfasından iOS/Android cihazlar için zamanlanmış koşum oluşturulabiliyor. Platform ve cihaz seçimi ile cron preset'leri.",
        tags: ["Visium Farm", "Scheduler"],
      },
      {
        version: "1.8.0",
        date: "13 Nis",
        badge: "new",
        title: "Mobil Koşum Geçmişi",
        description: "Tüm mobil koşumlar platform/cihaz filtreleme ve 'cihaza göre grupla' toggle'ı ile görüntülenebiliyor.",
        tags: ["Visium Farm", "Mobile"],
      },
      {
        version: "1.8.0",
        date: "13 Nis",
        badge: "improved",
        title: "Execution Platform Filtresi",
        description: "Koşumlar Masaüstü / iOS / Android sekmeleriyle filtrelenebiliyor. API'de ?platform= query parametresi.",
        tags: ["Executions"],
      },
    ],
  },
  {
    sprint: "Sprint 7 — E2E Tests + CI/CD Pipeline",
    date: "12 Nisan 2026",
    entries: [
      {
        version: "1.7.0",
        date: "12 Nis",
        badge: "new",
        title: "Visium Farm E2E Test Suite",
        description: "9 Playwright testi (TC-VF-001..009): sayfa yükleme, cihaz kartları, platform sekmeleri, iOS badge, gruplama toggle.",
        tags: ["Testing", "Visium Farm"],
      },
      {
        version: "1.7.0",
        date: "12 Nis",
        badge: "improved",
        title: "Frontend TypeCheck CI Job",
        description: "CI pipeline'a tsc --noEmit + npm run build gate'i eklendi. E2E testleri type-check geçmeden başlamıyor.",
        tags: ["CI/CD"],
      },
    ],
  },
  {
    sprint: "Sprint 6 — Visium Farm (Mobil Test Altyapısı)",
    date: "11 Nisan 2026",
    entries: [
      {
        version: "1.6.0",
        date: "11 Nis",
        badge: "new",
        title: "Visium Farm — Mobil Cihaz Emülasyonu",
        description: "14 cihaz profili (5 iOS + 9 Android), paralel koşum, SSE stream, APK/IPA yükleme. /p/:id/mobile sayfası.",
        tags: ["Visium Farm", "Mobile"],
      },
      {
        version: "1.6.0",
        date: "11 Nis",
        badge: "infra",
        title: "Performans İndeksleri",
        description: "project_id + created_at ve platform kolonlarına composite index eklendi; execution listesi %60 hızlandı.",
        tags: ["Altyapı", "Performans"],
      },
    ],
  },
];

export default function WhatsNewPage() {
  return (
    <div className="min-h-screen bg-slate-950 p-6 max-w-3xl mx-auto">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
          </svg>
        }
        title="Yenilikler"
        description="Sprint bazında özellikler, iyileştirmeler ve düzeltmeler"
      />

      {/* Zaman Çizelgesi */}
      <div className="relative mt-6">
        {/* Dikey çizgi */}
        <div className="absolute left-3.5 top-0 bottom-0 w-px bg-slate-800" />

        <div className="space-y-10">
          {RELEASES.map((release) => (
            <div key={release.sprint} className="relative pl-10">
              {/* Zaman noktası */}
              <div className="absolute left-0 top-1 w-7 h-7 rounded-full bg-slate-800 border-2 border-slate-600 flex items-center justify-center">
                <div className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
              </div>

              {/* Sprint başlığı */}
              <div className="mb-4">
                <h2 className="text-base font-bold text-white leading-tight">{release.sprint}</h2>
                <p className="text-xs text-slate-500 mt-0.5">{release.date}</p>
              </div>

              {/* Girdiler */}
              <div className="space-y-3">
                {release.entries.map((entry, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl bg-slate-900 border border-slate-800 px-4 py-3 hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <span className={`shrink-0 mt-0.5 px-2 py-0.5 rounded-md text-[10px] font-semibold border ${BADGE_CFG[entry.badge].cls}`}>
                        {BADGE_CFG[entry.badge].label}
                      </span>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-semibold text-white leading-tight">{entry.title}</h3>
                        <p className="text-xs text-slate-400 mt-1 leading-relaxed">{entry.description}</p>
                        {entry.tags && entry.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {entry.tags.map(tag => (
                              <span key={tag} className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <span className="shrink-0 text-[10px] text-slate-600 mt-0.5 whitespace-nowrap">{entry.date}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Alt bilgi */}
      <div className="mt-12 pt-6 border-t border-slate-800 text-center">
        <p className="text-xs text-slate-600">
          Visium Operations v1.10.0 · Son güncelleme: 15 Nisan 2026
        </p>
      </div>
    </div>
  );
}
