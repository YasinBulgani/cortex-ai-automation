/**
 * Neurex AI Agents — merkezi katalog
 * Her ajan: id, isim, emoji, kategori, açıklama, hedef route (proje-bağlamlı veya global).
 */

export type AgentCategory = "test-quality" | "code-analysis" | "data" | "observability" | "automation";

export type AIAgent = {
  id: string;
  name: string;
  emoji: string;
  category: AgentCategory;
  tagline: string;
  description: string;
  /** Proje gerektirir mi? Eğer global URL ise null */
  projectRouteSegment: string | null;
  /** Global agent ise direkt URL */
  globalHref?: string;
  availability: "active" | "beta" | "experimental";
  features: string[];
};

export const AGENT_CATEGORIES: Record<AgentCategory, { label: string; emoji: string; color: string }> = {
  "test-quality": { label: "Test Kalitesi", emoji: "🛡", color: "border-emerald-400/20 bg-emerald-500/10 text-emerald-200" },
  "code-analysis": { label: "Kod Analizi", emoji: "</>", color: "border-violet-400/20 bg-violet-500/10 text-violet-200" },
  "data": { label: "Veri", emoji: "💾", color: "border-sky-400/20 bg-sky-500/10 text-sky-200" },
  "observability": { label: "Gözlemleme", emoji: "📊", color: "border-amber-400/20 bg-amber-500/10 text-amber-200" },
  "automation": { label: "Otomasyon", emoji: "⚙️", color: "border-rose-400/20 bg-rose-500/10 text-rose-200" },
};

export const AI_AGENTS: AIAgent[] = [
  {
    id: "monkey-testing",
    name: "Monkey Testing",
    emoji: "🐒",
    category: "test-quality",
    tagline: "Rastgele tıklama ile UI keşfi",
    description: "AI destekli monkey test — rastgele kullanıcı etkileşimleriyle uygulamayı tarar, beklenmedik hataları, kararsız akışları ve UX boşluklarını bulur. Stability score üretir ve senaryo önerileri çıkarır.",
    projectRouteSegment: "monkey",
    availability: "active",
    features: ["Rastgele tıklama / kaydırma / yazı girişi", "Stability score", "Bug raporu ve sınıflandırma", "Senaryo önerisi üretimi"],
  },
  {
    id: "self-healing",
    name: "Self-Healing",
    emoji: "🩹",
    category: "test-quality",
    tagline: "Otomatik test onarımı",
    description: "Testler kırıldığında otomatik kategorize eder (timeout, auth expired, rate limit, server error) ve akıllı yeniden deneme stratejisi uygular. Başarısızlık nedenini analiz eder.",
    projectRouteSegment: "healing",
    availability: "active",
    features: ["Hata kategorizasyonu", "Akıllı retry", "Başarısızlık root-cause", "İyileştirme istatistikleri"],
  },
  {
    id: "flaky-management",
    name: "Flaky Test Yönetimi",
    emoji: "🔄",
    category: "test-quality",
    tagline: "Kararsız test tespiti ve karantina",
    description: "Tutarsız başarı/başarısızlık gösteren testleri tespit eder, karantinaya alır ve trend analiziyle kalıcı çözüm önerir.",
    projectRouteSegment: "flaky",
    availability: "active",
    features: ["Flaky tespit algoritması", "Otomatik karantina", "Trend grafiği", "Çözüm önerileri"],
  },
  {
    id: "prioritize",
    name: "Test Önceliklendirme",
    emoji: "🎯",
    category: "test-quality",
    tagline: "Risk-tabanlı test seçimi",
    description: "Kod değişikliklerine göre etkilenebilecek testleri analiz eder, risk skorlamasıyla sıralar. Regression koşusu için kritik testleri öne çıkarır.",
    projectRouteSegment: "prioritize",
    availability: "beta",
    features: ["Risk skorlaması", "Test impact analysis (TIA)", "Akıllı sıralama", "Kritik path tespiti"],
  },
  {
    id: "monkey-screen",
    name: "Visual Regression",
    emoji: "📸",
    category: "test-quality",
    tagline: "Görsel değişim tespiti",
    description: "Ekran görüntülerini her sürümle karşılaştırır, görsel regresyonları AI ile sınıflandırır (gerçek bug vs. küçük varyasyon).",
    projectRouteSegment: "visual",
    availability: "active",
    features: ["Pixel-perfect karşılaştırma", "AI anomaly detection", "Diff vurgulama", "Onay akışı"],
  },
  {
    id: "accessibility",
    name: "Erişilebilirlik Denetimi",
    emoji: "♿",
    category: "test-quality",
    tagline: "WCAG uyumluluk taraması",
    description: "Uygulamanın WCAG 2.1 AA standartlarına uygunluğunu otomatik denetler. Renk kontrast, klavye navigasyonu, ekran okuyucu uyumluluğunu raporlar.",
    projectRouteSegment: "accessibility",
    availability: "active",
    features: ["WCAG 2.1 AA tarama", "Renk kontrast", "Klavye navigasyonu", "Screen reader uyumluluğu"],
  },
  {
    id: "security",
    name: "Güvenlik Taraması",
    emoji: "🔒",
    category: "test-quality",
    tagline: "Otomatik güvenlik denetimi",
    description: "API ve UI üzerinden güvenlik açıklarını tarar — XSS, SQL injection, CSRF, kimlik doğrulama bypass denemeleri yapar.",
    projectRouteSegment: "security",
    availability: "beta",
    features: ["XSS / SQLi taraması", "Auth bypass denemeleri", "OWASP Top 10", "Detaylı bug raporu"],
  },
  {
    id: "code-analyzer",
    name: "Nexus Code Agent",
    emoji: "🤖",
    category: "code-analysis",
    tagline: "Koddan QA analizi üretici",
    description: "Kaynak kodu veya web sayfası URL'i ver — sayfa analizi, manuel test senaryoları, bug tahminleri ve otomasyon önerilerini tek seferde üretir. Lokal Ollama üzerinde çalışır.",
    projectRouteSegment: null,
    globalHref: "/nexus-code",
    availability: "beta",
    features: ["Sayfa yapısı analizi", "Manuel test senaryoları", "Bug tahmini", "Otomasyon önerileri"],
  },
  {
    id: "llm-quality",
    name: "AI Quality Dashboard",
    emoji: "📊",
    category: "observability",
    tagline: "LLM metrikleri & router",
    description: "Tüm AI çağrılarının metriklerini izle: latency, başarı oranı, JSON parse rate, maliyet. Smart router, judge skorları, eval ve RAG istatistikleri tek panelde.",
    projectRouteSegment: null,
    globalHref: "/ai-quality",
    availability: "active",
    features: ["LLM call metrics", "Maliyet takibi", "LLM-as-Judge", "Smart router state", "RAG istatistikleri"],
  },
  {
    id: "data-simulator",
    name: "Sentetik Veri Üretici",
    emoji: "🪐",
    category: "data",
    tagline: "AI destekli sentetik veri",
    description: "DB şemanı yapıştır — AI ilişkileri anlar, gerçekçi sentetik veri üretir. Privacy-safe test verisi için Veri Üretici aracı.",
    projectRouteSegment: null,
    globalHref: "/veri-kaynagi",
    availability: "active",
    features: ["Sentetik veri", "Şema çıkarımı", "İlişkili tablolar", "Privacy-safe"],
  },
];

export const AGENTS_BY_CATEGORY = Object.entries(AGENT_CATEGORIES).map(([key, meta]) => ({
  key: key as AgentCategory,
  meta,
  agents: AI_AGENTS.filter((a) => a.category === key),
}));

export function getAgentById(id: string): AIAgent | undefined {
  return AI_AGENTS.find((a) => a.id === id);
}
