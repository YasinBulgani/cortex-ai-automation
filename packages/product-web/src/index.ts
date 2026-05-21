import type { ProductPackage } from "@neurex/product-kit";

export const manifest: ProductPackage["manifest"] = {
  id: "web",
  name: "Neurex Web",
  shortName: "Web",
  tagline: "Web UI otomasyonu",
  description: "Kaydedici, locator, otomasyon üretimi, görsel regresyon, erişilebilirlik ve web koşuları alanı.",
  availability: "active",
  defaultEntryKey: "scenarios",
  routeKeys: [
    "project-overview",
    "scenarios", "manual", "requirements", "analysis", "test-cases", "sifir-bilgi", "wizard",
    "automation", "recorder", "locators", "flows", "automation-gen", "api-tests", "page-objects", "manual-to-automation",
    "runs", "reports", "flaky", "executions", "analytics", "test-history", "debug-report",
    "visual", "accessibility", "monkey", "playwright-console", "regression", "coverage",
    "workflows",
    "ai-chat", "nl-test-gen", "qa-orchestrator", "ai-metrics",
  ],
};

export const landing: ProductPackage["landing"] = {
  eyebrow: "Web Otomasyonu",
  headline: "Web akışlarını ölç, üret ve çalıştır",
  summary: "Dokümandan otomasyon, locator yönetimi, recorder ve görsel kalite akışlarını tek yüzeyde sun.",
  primaryOutcome: "İlk durakta web otomasyon hattını görünür kıl",
  startRouteKey: "scenarios",
  projectKeywords: ["web", "portal", "ui", "frontend", "otomasyon", "locator"],
};

const productPackage: ProductPackage = { manifest, landing };
export default productPackage;
