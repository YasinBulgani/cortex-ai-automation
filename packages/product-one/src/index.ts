import type { ProductPackage } from "@neurex/product-kit";

export const manifest: ProductPackage["manifest"] = {
  id: "one",
  name: "Neurex One",
  shortName: "One",
  tagline: "Platform çekirdeği",
  description: "Test otomasyon platformu.",
  availability: "core",
  defaultEntryKey: "settings",
  // 'one' tüm route'lara erişir (platform çekirdeği).
  routeKeys: [
    "project-overview",
    "scenarios", "manual", "import", "requirements", "analysis", "approvals", "test-cases", "sifir-bilgi", "wizard",
    "automation", "recorder", "locators", "flows", "api-testing", "chain-builder", "mobile", "automation-gen",
    "api-tests", "page-objects", "device-manager", "manual-to-automation",
    "runs", "schedules", "cicd", "reports", "flaky", "healing", "executions", "analytics", "test-history", "debug-report",
    "visual", "accessibility", "monkey", "security", "prioritize", "playwright-console", "regression", "coverage",
    "management-dashboard", "management-repository", "management-test-plans", "management-test-runs",
    "management-requirements", "management-defects", "management-reports", "management-import-export", "management-settings",
    "synthetic", "test-data", "privacy",
    "environments", "integrations", "settings", "dsl-catalog-project", "workflows", "banking-team",
    "ai-chat", "nl-test-gen", "qa-orchestrator", "ai-metrics",
  ],
};

export const landing: ProductPackage["landing"] = {
  eyebrow: "Platform Çekirdeği",
  headline: "Operasyon omurgasını görünür hale getir",
  summary: "Çok ürünlü yapının temel yönetişim, entegrasyon ve platform ayarlarını tek bakışta topla.",
  primaryOutcome: "Platform çekirdeğini doğru proje ve entegrasyonlarla aç",
  startRouteKey: "settings",
  projectKeywords: ["platform", "operasyon", "core", "entegrasyon", "genel"],
};

const productPackage: ProductPackage = { manifest, landing };
export default productPackage;
