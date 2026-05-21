"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { getPersonaPreset, PERSONA_STORAGE_KEY, type PersonaId } from "@/lib/persona-focus";
import {
  DEFAULT_PRODUCT_FAMILY_ID,
  PRODUCT_FAMILY,
  PRODUCT_FAMILY_STORAGE_KEY,
  getProductFamilyMember,
  type ProductFamilyId,
} from "@/lib/product";

export type FlowStageId =
  | "discover"
  | "design"
  | "data"
  | "generate"
  | "execute"
  | "observe";

type FlowStageConfig = {
  flowKey: string;
  label: string;
  summary: string;
  checklist: string[];
  priorityProducts: ProductFamilyId[];
  productNotes: Partial<Record<ProductFamilyId, string>>;
  previous?: { label: string; path: string };
  next?: { label: string; path: string };
  supportLinks: Array<{ label: string; path: string }>;
  accent: string;
};

const STAGE_CONFIG: Record<FlowStageId, FlowStageConfig> = {
  discover: {
    flowKey: "Manuel Senaryolar",
    label: "Keşfet",
    summary: "Bu asamada proje baglamini toplar, dokümanlari yükler ve gereksinim tabanini netlestirirsiniz.",
    checklist: [
      "Dosya veya kaynaklari içeri alin.",
      "Gereksinim ve kapsam bosluklarini gozden gecirin.",
      "Sonraki tasarım asamasi için temiz baglam oluşturun.",
    ],
    priorityProducts: ["one", "studio"],
    productNotes: {
      one: "Platform omurgasinda bu asama proje baglamini standartlastirir.",
      studio: "Studio lensinde bu asama requirement ve coverage kalitesinin temelidir.",
      service: "Servis testleri için spec ve doküman baglami burada netlesir.",
      data: "Veri odaginda import edilen baglam sentetik veri ihtiyacini dogru kurar.",
      intelligence: "AI kalite katmani için kaynak ve grounding temeli burada oluşur.",
    },
    next: { label: "Tasarlamaya Gec", path: "scenarios" },
    supportLinks: [
      { label: "Gereksinimler", path: "requirements" },
      { label: "Kapsam", path: "coverage" },
      { label: "Analiz", path: "analysis" },
    ],
    accent: "border-sky-500/20 bg-sky-500/8",
  },
  design: {
    flowKey: "Manuel Senaryolar",
    label: "Tasarla",
    summary: "Senaryolari, AI test case'leri ve onay akislarini burada olgunlastirirsiniz.",
    checklist: [
      "Senaryolari netlestirin ve etiketleyin.",
      "AI test case sonuçunu gozden gecirin.",
      "Onay gerektiren kayitlari kuyruga alin veya karara baglayin.",
    ],
    priorityProducts: ["one", "studio"],
    productNotes: {
      one: "Platform seviyesinde ortak test dili ve onay mekanizmasi burada olgunlasir.",
      studio: "Studio için bu ekran ana deger alanidir; senaryo ve onay kalitesi burada sekillenir.",
      web: "Web otomasyonunun dogru artefakta donusmesi için kaynak senaryolar burada temizlenir.",
      intelligence: "AI önerilerinin dogru geri beslenmesi için tasarım kalitesi kritiktir.",
    },
    previous: { label: "Keşfet'e Don", path: "import" },
    next: { label: "Veri Asamasina Gec", path: "test-data" },
    supportLinks: [
      { label: "AI Test Case", path: "test-cases" },
      { label: "Onaylar", path: "approvals" },
      { label: "Is Akislari", path: "workflows" },
    ],
    accent: "border-indigo-500/20 bg-indigo-500/8",
  },
  data: {
    flowKey: "Manuel Senaryolar",
    label: "Veri",
    summary: "Sentetik veri ve fixture setleri burada hazırlanir; otomasyon ve servis koşulari bu veriyle bağlanir.",
    checklist: [
      "Gerekli veri setlerini oluşturun veya duzenleyin.",
      "Sentetik veri ihtiyacini belirleyin.",
      "Koşularda kullanilacak veri setlerini netlestirin.",
    ],
    priorityProducts: ["data"],
    productNotes: {
      studio: "Tasarım kalitesinin çalışabilir olmasi için veri baglami burada netlesir.",
      service: "Servis assertion ve zincir akislari guvenilir veriye dayanir.",
      data: "Data lensinde bu asama ana deger alanidir; sentetik ve fixture stratejisi burada kurulur.",
      web: "Web koşularinin kirilmamasi için test verisi burada saglamlastirilir.",
    },
    previous: { label: "Tasarla'ya Don", path: "scenarios" },
    next: { label: "Üret Asamasina Gec", path: "automation-gen" },
    supportLinks: [
      { label: "Sentetik Veri", path: "synthetic" },
      { label: "Test Verileri", path: "test-data" },
    ],
    accent: "border-emerald-500/20 bg-emerald-500/8",
  },
  generate: {
    flowKey: "Otomasyon",
    label: "Üret",
    summary: "Bu asama manuel, doküman ve AI kaynaklarindan çalışan otomasyon artefaktlari üretmek içindir.",
    checklist: [
      "Kaynak senaryolari veya onayli test case'leri secin.",
      "Gerekirse locator ve page object yardimlarini tamamlayin.",
      "Oluşan artefakti koşu oncesi gozden gecirin.",
    ],
    priorityProducts: ["web", "mobile"],
    productNotes: {
      studio: "Tasarımda verilen kararlar burada çalışan artefakta donusur.",
      web: "Web lensinde bu asama ana üretim hattidir; kod ve locator kalitesi burada belirlenir.",
      mobile: "Mobil odakta bile tekrar kullanilabilir otomasyon artefakti burada sekillenir.",
      intelligence: "AI üretim kalitesi ve artifact kaliciligi burada gorunur hale gelir.",
    },
    previous: { label: "Veri'ye Don", path: "test-data" },
    next: { label: "Çalıştırmaya Gec", path: "executions" },
    supportLinks: [
      { label: "Dokümandan Otomasyon", path: "manual-to-automation" },
      { label: "Otomasyonlar", path: "automation" },
      { label: "Kaydedici", path: "recorder" },
    ],
    accent: "border-fuchsia-500/20 bg-fuchsia-500/8",
  },
  execute: {
    flowKey: "Otomasyon",
    label: "Çalıştır",
    summary: "UI, servis ve regresyon koşularini burada başlatir, izler ve tekrar çalıştırirsiniz.",
    checklist: [
      "Uygun koşu tipini secin.",
      "Veri ve artefakt baglaminin hazır oldugunu dogrulayin.",
      "Aktif koşulari ve hata durumlarini takip edin.",
    ],
    priorityProducts: ["one", "service", "web", "mobile"],
    productNotes: {
      one: "Platform cekirdegi için koşu gorunurlugu ekiplerin ortak ritmini belirler.",
      service: "Servis lensinde assertion ve zincirlerin gerçek degeri bu asamada gorulur.",
      web: "Web otomasyonunun üretim kalitesi koşu sonuçunda dogrulanir.",
      mobile: "Mobil cihaz matrisi ve paralel run kabiliyeti burada anlam kazanir.",
      intelligence: "AI hata analizi için taze execution verisi bu asamada toplanir.",
    },
    previous: { label: "Üret'e Don", path: "automation-gen" },
    next: { label: "Raporlara Gec", path: "reports" },
    supportLinks: [
      { label: "API Testleri", path: "api-tests" },
      { label: "Koşu Gecmisi", path: "runs" },
      { label: "Regresyon", path: "regression" },
    ],
    accent: "border-amber-500/20 bg-amber-500/8",
  },
  observe: {
    flowKey: "Otomasyon",
    label: "Gözlemle",
    summary: "Raporlar, trendler ve AI debug cikarimlari bu asamada karar destegine donusur.",
    checklist: [
      "Koşu raporlarini ve trendleri karsilastirin.",
      "Hata kaliplarini inceleyin.",
      "Bir sonraki iyilestirme dongusunu belirleyin.",
    ],
    priorityProducts: ["one", "service", "web", "mobile", "intelligence"],
    productNotes: {
      one: "Platform genelinde kalite ritmi rapor ve trendlerle yonetilir.",
      service: "Servis kalite borcu ve flaky davranislar burada netlesir.",
      web: "Web regresyonlarinin is etkisi rapor katmaninda gorunur olur.",
      mobile: "Cihaz bazli kirilimlar ve stream sonuçlari burada okunur.",
      intelligence: "AI kalite katmani için asil karar destegi burada üretilir.",
    },
    previous: { label: "Çalıştır'a Don", path: "executions" },
    supportLinks: [
      { label: "Analitik", path: "analytics" },
      { label: "AI Debug Rapor", path: "debug-report" },
      { label: "Flaky Testler", path: "flaky" },
    ],
    accent: "border-rose-500/20 bg-rose-500/8",
  },
};

function getSafeProductId(value: string | null | undefined): ProductFamilyId {
  return PRODUCT_FAMILY.some((product) => product.id === value)
    ? (value as ProductFamilyId)
    : DEFAULT_PRODUCT_FAMILY_ID;
}

export function FlowGuideCard({
  projectId,
  stage,
  className,
  title: _title,
  description: _description,
  nextLabel: _nextLabel,
  nextHref: _nextHref,
  supportLinks: _supportLinks,
}: {
  projectId: string;
  stage: FlowStageId;
  className?: string;
  /** Override props — sayfalar kendi başlık/açıklama geçebilir (opsiyonel). */
  title?: string;
  description?: string;
  nextLabel?: string;
  nextHref?: string;
  supportLinks?: { label: string; href: string }[];
}) {
  const [personaId, setPersonaId] = useState<PersonaId>("balanced");
  const [activeProductId, setActiveProductId] = useState<ProductFamilyId>(DEFAULT_PRODUCT_FAMILY_ID);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(PERSONA_STORAGE_KEY);
      if (raw) setPersonaId(getPersonaPreset(raw).id);
    } catch { /* ignore */ }

    const syncPersona = (event?: Event) => {
      const nextId = event instanceof CustomEvent ? String(event.detail ?? "") : null;
      try {
        const raw = nextId || localStorage.getItem(PERSONA_STORAGE_KEY);
        setPersonaId(getPersonaPreset(raw).id);
      } catch { /* ignore */ }
    };

    window.addEventListener("storage", syncPersona);
    window.addEventListener("bgts-persona-changed", syncPersona as EventListener);
    return () => {
      window.removeEventListener("storage", syncPersona);
      window.removeEventListener("bgts-persona-changed", syncPersona as EventListener);
    };
  }, []);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(PRODUCT_FAMILY_STORAGE_KEY);
      setActiveProductId(getSafeProductId(raw));
    } catch { /* ignore */ }

    const syncProduct = (event?: Event) => {
      const nextId = event instanceof CustomEvent ? String(event.detail ?? "") : null;
      try {
        const raw = nextId || localStorage.getItem(PRODUCT_FAMILY_STORAGE_KEY);
        setActiveProductId(getSafeProductId(raw));
      } catch { /* ignore */ }
    };

    window.addEventListener("storage", syncProduct);
    window.addEventListener("bgts-product-family-changed", syncProduct as EventListener);
    return () => {
      window.removeEventListener("storage", syncProduct);
      window.removeEventListener("bgts-product-family-changed", syncProduct as EventListener);
    };
  }, []);

  const persona = getPersonaPreset(personaId);
  const config = STAGE_CONFIG[stage];
  const personaFocused = persona.focusFlows.includes(config.flowKey);
  const selectedProduct = getProductFamilyMember(activeProductId);
  const productFocused = config.priorityProducts.includes(activeProductId);
  const productNote = config.productNotes[activeProductId] ?? "Bu asama seçili urunu destekleyen genel kalite akisinin bir parcasi.";
  const orderedSupportLinks = [...config.supportLinks].sort((left, right) => {
    const leftScore = selectedProduct.routeSegments.includes(left.path) ? 0 : 1;
    const rightScore = selectedProduct.routeSegments.includes(right.path) ? 0 : 1;
    return leftScore - rightScore;
  });

  return (
    <section
      className={cn(
        "rounded-2xl border p-4 shadow-[0_0_0_1px_rgba(30,41,59,0.12)]",
        config.accent,
        className
      )}
      data-testid={`flow-guide-${stage}`}
    >
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-white/10 bg-slate-950/40 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300">
              {config.label}
            </span>
            <span className="rounded-full border border-violet-400/20 bg-violet-500/10 px-2.5 py-1 text-[11px] font-medium text-violet-100">
              {selectedProduct.name}
            </span>
            <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-1 text-[11px] font-medium text-emerald-100">
              {persona.label}
            </span>
            {productFocused && (
              <span className="rounded-full border border-amber-300/20 bg-amber-400/10 px-2.5 py-1 text-[11px] font-medium text-amber-100">
                Bu urunde oncelikli
              </span>
            )}
            {personaFocused && (
              <span className="rounded-full border border-sky-300/20 bg-sky-400/10 px-2.5 py-1 text-[11px] font-medium text-sky-100">
                Bu asama seçili personada odakta
              </span>
            )}
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-300">{config.summary}</p>
          <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/45 px-3 py-2.5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Secili urun icin anlami</p>
            <p className="mt-1 text-sm leading-6 text-slate-300">{productNote}</p>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {orderedSupportLinks.map(link => (
              <Link
                key={link.path}
                href={`/p/${projectId}/${link.path}`}
                className="rounded-full border border-slate-700 bg-slate-950/50 px-2.5 py-1 text-xs text-slate-300 transition hover:border-slate-500 hover:text-white"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>

        <div className="min-w-[18rem] rounded-xl border border-slate-800 bg-slate-950/45 p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Bu Ekranda Bitir</p>
          <div className="mt-2 space-y-2">
            {config.checklist.map(item => (
              <div key={item} className="flex items-start gap-2 text-sm text-slate-300">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400" />
                <span>{item}</span>
              </div>
            ))}
          </div>
          <div className="mt-3 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Asama Rolu</p>
            <p className="mt-1 text-xs leading-5 text-slate-300">
              {productFocused
                ? `${selectedProduct.shortName} için bu ekran ana akis içinde kritik bir durak.`
                : `${selectedProduct.shortName} için bu ekran destekleyici; gerekli kadar ilerleyip sonraki asamaya gecebilirsiniz.`}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {config.previous && (
          <Link
            href={`/p/${projectId}/${config.previous.path}`}
            className="rounded-xl border border-slate-700 bg-slate-950/55 px-3 py-2 text-sm text-slate-300 transition hover:border-slate-500 hover:text-white"
          >
            {config.previous.label}
          </Link>
        )}
        {config.next && (
          <Link
            href={`/p/${projectId}/${config.next.path}`}
            className="rounded-xl border border-blue-400/20 bg-blue-500/10 px-3 py-2 text-sm font-medium text-blue-100 transition hover:border-blue-300/40 hover:bg-blue-500/15"
          >
            {config.next.label}
          </Link>
        )}
      </div>
    </section>
  );
}
