import type { ProductPackage } from "@neurex/product-kit";

export const manifest: ProductPackage["manifest"] = {
  id: "nexus-code",
  name: "Neurex Code",
  shortName: "Neurex Code",
  tagline: "QA + Kod + Web Analiz Agent'ı",
  description:
    "Lokal Ollama üzerinde çalışan tam analiz motoru. Web sayfası veya repo ver — sayfa yapısı, kod analizi, kullanıcı akışları, manuel test senaryoları, bug tahminleri ve otomasyon önerilerini tek seferde üretir.",
  availability: "beta",
  defaultEntryKey: "project-overview",
  // Neurex Code orijinalde sidebar nav listelerinde yer almıyordu; sadece kendi ana sayfası.
  routeKeys: ["project-overview"],
};

export const landing: ProductPackage["landing"] = {
  eyebrow: "QA + Kod + Web Analiz Agent'ı",
  headline: "URL ya da kodu ver — tam QA analizini tek seferde al",
  summary:
    "Neurex Code; kaynak kodu, web sayfası URL'ini veya DOM yapısını alır ve sayfa analizi, manuel test senaryoları, bug tahminleri ile otomasyon önerilerini tek seferde üretir. Lokal Ollama üzerinde çalışır, veri dışarı çıkmaz.",
  primaryOutcome: "Neurex Code agent sayfasını aç ve analizi başlat",
  startRouteKey: "project-overview",
  projectKeywords: ["nexus", "code", "qa", "analiz", "test", "otomasyon", "web", "kod"],
};

const productPackage: ProductPackage = { manifest, landing };
export default productPackage;
