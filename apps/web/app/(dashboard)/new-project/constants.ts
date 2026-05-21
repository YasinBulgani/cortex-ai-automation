/**
 * New Project Wizard — Constants & Configuration
 */

import type { ProductFamilyId } from "@/lib/product";

export const STEPS = [
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

export const PRIORITY_COLOR: Record<string, string> = {
  critical: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  high:     "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  medium:   "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  low:      "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

export const PRODUCT_AVAILABILITY_META = {
  core: { label: "Core", className: "border-sky-400/20 bg-sky-500/10 text-sky-200" },
  active: { label: "Active", className: "border-emerald-400/20 bg-emerald-500/10 text-emerald-200" },
  beta: { label: "Beta", className: "border-amber-400/20 bg-amber-500/10 text-amber-200" },
  embedded: { label: "Embedded", className: "border-violet-400/20 bg-violet-500/10 text-violet-200" },
} as const;

export const PRODUCT_FLOW_GUIDE: Record<ProductFamilyId, { title: string; description: string; recommendedPath: string }> = {
  one: {
    title: "Platform cekirdegini kur",
    description: "Ortam, entegrasyon ve ortak proje omurgasini oturtup ekibin geri kalan akislarini besle.",
    recommendedPath: "settings",
  },
  studio: {
    title: "Tasarım ve yonetisimi one al",
    description: "Doküman, gereksinim, kapsam ve onay akislarini merkezi sekilde yönet.",
    recommendedPath: "requirements",
  },
  service: {
    title: "Servis kalitesine hizli gir",
    description: "Spec import, assertion, chain orchestration ve servis koşularina agirlik ver.",
    recommendedPath: "api-testing",
  },
  web: {
    title: "Web otomasyonunu hizlandir",
    description: "Dokümandan otomasyon, locator, page object ve execution hattini one cikar.",
    recommendedPath: "automation",
  },
  mobile: {
    title: "Mobil kalite hattini ac",
    description: "Cihaz matrisi, paralel run ve artifact akisini projeyle birlikte hazırla.",
    recommendedPath: "mobile",
  },
  data: {
    title: "Veri baglamiyla basla",
    description: "Sentetik veri, masking ve test verisi baglama adımlarini daha erken asamada guclendir.",
    recommendedPath: "test-data",
  },
  intelligence: {
    title: "AI kalite katmanini etkinlestir",
    description: "Copilot, kalite metrikleri ve yonlendirilmis AI akislarini proje merkezine yerlestir.",
    recommendedPath: "scenarios",
  },
  "nexus-code": {
    title: "Neurex Code ile QA analizini baslat",
    description: "Kaynak kodu veya web sayfasi ver — test senaryolari, bug tahminleri ve otomasyon onerileri tek seferde gelsin.",
    recommendedPath: "scenarios",
  },
};

export const PRODUCT_WIZARD_PROFILE: Record<
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
    dbNote: "Platform cekirdegi için DB baglami faydali ama bu kurulumda zorunlu degil.",
    automationPrimary: false,
    automationNote: "Web otomasyonu bu ürün için ikincil. Asil hedef platform omurgasini hazırlamak.",
  },
  studio: {
    analysisSeed: "Requirement, coverage gap, approval ve regression planning acisindan daha derin dusun.",
    analysisFocus: ["requirement coverage", "onay kuyrugu", "regresyon planlama"],
    dbPriorityLabel: "Destekleyici",
    dbNote: "Studio odaginda asil değer doküman ve senaryo tasarımında. DB bağlantısi varsa analiz daha zengin olur.",
    automationPrimary: false,
    automationNote: "Studio odaginda web otomasyonu opsiyonel; tasarım ve yonetisim daha oncelikli.",
  },
  service: {
    analysisSeed: "API kontrati, auth, validation, negative path, rate limit ve edge-case senaryolarina agirlik ver.",
    analysisFocus: ["auth ve yetki", "negative servis senaryolari", "assertion ve contract riskleri"],
    dbPriorityLabel: "Yuksek oncelik",
    dbNote: "Servis kalite akislarinda DB baglami ve gerçek veri iliskileri daha kritik olabilir.",
    automationPrimary: false,
    automationNote: "Bu wizardin sonundaki web otomasyon adımi servis urunu için opsiyonel; asil hedef servis test kurgusu.",
  },
  web: {
    analysisSeed: "UI akislarini, locator bagimliliklarini, page object ihtiyaclarini ve E2E regresyonu one cikar.",
    analysisFocus: ["UI akislari", "locator bagimliliklari", "E2E regresyon"],
    dbPriorityLabel: "Orta oncelik",
    dbNote: "Web otomasyonunda DB baglami yardimci olabilir; ama asıl kritik kisim kullanıcı akislaridir.",
    automationPrimary: true,
    automationNote: "Bu urun odaginda web otomasyon adımlari ana akis olarak önerilir.",
  },
  mobile: {
    analysisSeed: "Mobil cihaz varyasyonlari, bağlantı koşullari, cihaz matrisi ve artefact risklerine dikkat et.",
    analysisFocus: ["cihaz varyasyonlari", "ag koşullari", "mobil artefact riski"],
    dbPriorityLabel: "Destekleyici",
    dbNote: "Mobil kalitede veri baglami onemli olabilir ama cihaz ve run orkestrasyonu daha baskin olur.",
    automationPrimary: true,
    automationNote: "Mobil odakta da otomasyon kurulumu degerli; bu web tabanli adımlar hizli başlangic için kullanilabilir.",
  },
  data: {
    analysisSeed: "Test verisi bagimliliklari, masking ihtiyaci, sentetik veri senaryolari ve privacy risklerini vurgula.",
    analysisFocus: ["test verisi ihtiyaci", "privacy ve masking", "sentetik veri akislari"],
    dbPriorityLabel: "Yuksek oncelik",
    dbNote: "Data odaginda DB iliskileri ve veri baglami genelde daha yuksek deger üretir.",
    automationPrimary: false,
    automationNote: "Bu urunde asil hedef veri ve privacy akislarini guclendirmek; web otomasyonu ikincil kalabilir.",
  },
  intelligence: {
    analysisSeed: "AI copilot, explanation quality, source grounding ve kalite metriklerini dusunen senaryolar da cikar.",
    analysisFocus: ["copilot yardimi", "source grounding", "kalite metrikleri"],
    dbPriorityLabel: "Opsiyonel",
    dbNote: "Intelligence odaginda DB bağlantısi faydali olabilir ama temel deger AI yonlendirmesinden gelir.",
    automationPrimary: false,
    automationNote: "Neurex Intelligence için bu web otomasyon adımlari yardimci ama zorunlu degil.",
  },
  "nexus-code": {
    analysisSeed: "Kaynak kod ve web sayfasi analizi odakli: test edilebilirlik, bug riski, validasyon boslukları ve otomasyon onerileri.",
    analysisFocus: ["kod kalitesi", "test senaryolari", "otomasyon adayi"],
    dbPriorityLabel: "Dusuk oncelik",
    dbNote: "Neurex Code için kaynak kod ve web analizi on plandadir; DB baglantisi zorunlu degil.",
    automationPrimary: true,
    automationNote: "Neurex Code projelerinde Playwright / Cypress otomasyon onerisi birincil ciktıdır.",
  },
};

export const GHERKIN_KW = ["Feature:", "Scenario:", "Background:", "Examples:", "Given", "When", "Then", "And", "But"];
