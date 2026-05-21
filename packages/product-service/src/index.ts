import type { ProductPackage } from "@neurex/product-kit";

export const manifest: ProductPackage["manifest"] = {
  id: "service",
  name: "Neurex Service",
  shortName: "Service",
  tagline: "Servis ve API kalite mühendisliği",
  description: "Spesifikasyon alma, zincir orkestrasyonu, doğrulama, healing, flaky yönetimi, güvenlik ve API koşuları alanı.",
  availability: "active",
  defaultEntryKey: "api-testing",
  routeKeys: [
    "project-overview",
    "scenarios", "requirements", "analysis", "sifir-bilgi", "wizard",
    "api-testing", "chain-builder", "api-tests",
    "runs", "reports", "healing", "executions", "analytics", "test-history", "debug-report",
    "security", "prioritize", "regression", "coverage",
    "workflows",
    "ai-chat", "nl-test-gen", "qa-orchestrator", "ai-metrics",
  ],
};

export const landing: ProductPackage["landing"] = {
  eyebrow: "Servis Kalitesi",
  headline: "API ve zincir kalitesini operasyonel düzeyde yönet",
  summary: "API testing, chain builder, flaky yönetimi ve güvenlik taramasını servis odaklı bir hatta topla.",
  primaryOutcome: "Servis test stratejisini doğru proje üzerinden başlat",
  startRouteKey: "api-testing",
  projectKeywords: ["api", "service", "servis", "integration", "backend", "chain"],
};

const productPackage: ProductPackage = { manifest, landing };
export default productPackage;
