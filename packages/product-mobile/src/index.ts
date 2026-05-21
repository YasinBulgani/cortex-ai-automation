import type { ProductPackage } from "@neurex/product-kit";

export const manifest: ProductPackage["manifest"] = {
  id: "mobile",
  name: "Neurex Mobile",
  shortName: "Mobile",
  tagline: "Mobil test orkestrasyonu",
  description: "Cihaz matrisi, mobil artefakt, paralel koşu ve canlı izleme tabanlı mobil kalite yüzeyi.",
  availability: "beta",
  defaultEntryKey: "mobile",
  routeKeys: [
    "project-overview",
    "scenarios", "manual", "requirements", "analysis", "sifir-bilgi", "wizard",
    "automation", "mobile", "automation-gen", "device-manager", "manual-to-automation",
    "runs", "reports", "executions", "analytics", "test-history",
    "regression",
    "ai-chat", "nl-test-gen", "qa-orchestrator", "ai-metrics",
  ],
};

export const landing: ProductPackage["landing"] = {
  eyebrow: "Mobil Orkestrasyon",
  headline: "Cihaz matrisi ve mobil koşuları tek karar yüzeyinde topla",
  summary: "Mobil kalite, sanal emülasyon, canlı cihaz bağlantısı ve farm tabanlı koşular için ürün bağlamlı bir başlangıç sun.",
  primaryOutcome: "Mobil koşular için doğru proje, cihaz modunu ve bağlantı yönünü öner",
  startRouteKey: "mobile",
  projectKeywords: ["mobil", "mobile", "ios", "android", "cihaz", "farm", "canlı", "fiziksel", "appium", "real"],
};

const productPackage: ProductPackage = { manifest, landing };
export default productPackage;
