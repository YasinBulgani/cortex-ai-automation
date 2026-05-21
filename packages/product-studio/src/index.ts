import type { ProductPackage } from "@neurex/product-kit";

export const manifest: ProductPackage["manifest"] = {
  id: "studio",
  name: "Neurex Studio",
  shortName: "Studio",
  tagline: "Test tasarımı ve yönetişim",
  description: "İçe aktarma, gereksinim, kapsam, senaryo, onay ve regresyon planlama çalışma alanı.",
  availability: "active",
  defaultEntryKey: "import",
  routeKeys: [
    "project-overview",
    "scenarios", "manual", "import", "requirements", "analysis", "approvals", "test-cases", "sifir-bilgi", "wizard",
    "reports", "executions", "analytics", "test-history",
    "regression", "coverage",
    "dsl-catalog-project", "workflows", "banking-team",
    "ai-chat", "nl-test-gen", "qa-orchestrator", "ai-metrics",
  ],
};

export const landing: ProductPackage["landing"] = {
  eyebrow: "Test Tasarımı",
  headline: "Gereksinimden senaryoya giden akışı netleştir",
  summary: "İçe aktarma, gereksinim analizi, senaryo tasarımı ve onay hattını aynı ürün sayfasında topla.",
  primaryOutcome: "İlk durakta senaryo ve gereksinim görünürlüğü sağla",
  startRouteKey: "import",
  projectKeywords: ["gereksinim", "senaryo", "approval", "tasarim", "analiz"],
};

const productPackage: ProductPackage = { manifest, landing };
export default productPackage;
