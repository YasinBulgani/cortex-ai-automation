import type { ProductPackage } from "@neurex/product-kit";

export const manifest: ProductPackage["manifest"] = {
  id: "management",
  name: "Neurex Management",
  shortName: "Management",
  tagline: "Manuel test operasyon yönetimi",
  description:
    "Manuel test case havuzu, test planı, koşum, kanıt, defect, coverage ve tester iş yükünü yöneten QA operasyon alanı.",
  availability: "active",
  defaultEntryKey: "management-dashboard",
  routeKeys: [
    "project-overview",
    "management-dashboard",
    "management-repository",
    "management-test-plans",
    "management-test-runs",
    "management-requirements",
    "management-defects",
    "management-reports",
    "management-import-export",
    "management-settings",
    "manual",
    "requirements",
    "reports",
    "coverage",
    "integrations",
    "ai-chat",
    "qa-orchestrator",
  ],
};

export const landing: ProductPackage["landing"] = {
  eyebrow: "Manuel QA Yönetimi",
  headline: "Manuel test hafızasını ve koşum operasyonunu tek merkezde yönet",
  summary:
    "Test case repository, plan, cycle, run, evidence, defect ve coverage görünürlüğünü Neurex ürün ailesinin yönetim katmanında birleştir.",
  primaryOutcome: "Manuel testleri sakla, tester atamalarını yönet ve release kararını raporla",
  startRouteKey: "management-dashboard",
  projectKeywords: [
    "management",
    "manuel",
    "manual",
    "test case",
    "test run",
    "qa lead",
    "coverage",
    "defect",
    "regression",
  ],
};

const productPackage: ProductPackage = { manifest, landing };
export default productPackage;
