/**
 * Merkezi route katalogu — ürün-agnostik.
 *
 * Her route'un hangi ürüne ait olduğu burada DEĞİL, her ürünün kendi
 * manifest.routeKeys listesinde tanımlanır. compose() bunları birleştirir.
 */

import type { NavGroupKey, RouteCatalogEntry } from "./types";

export const NAV_GROUP_LABELS: Record<string, string> = {
  "Tasarım": "✏️ Tasarım",
  "Üretim": "⚙️ Üretim",
  "Koşu & Gözlem": "▶️ Koşu & Gözlem",
  "Kalite": "🛡 Kalite",
  "Veri": "💾 Veri",
  "Yapılandırma": "🔧 Yapılandırma",
  "AI": "🤖 AI",
};

export const NAV_GROUP_ORDER: NavGroupKey[] = [
  "Tasarım",
  "Üretim",
  "Koşu & Gözlem",
  "Kalite",
  "Veri",
  "Yapılandırma",
  "AI",
];

export const ROUTE_CATALOG: RouteCatalogEntry[] = [
  { key: "project-overview", path: "", segment: "", label: "Proje Özeti", group: "" },

  // Tasarım
  { key: "scenarios", path: "scenarios", segment: "scenarios", label: "Senaryolar", group: "Tasarım" },
  { key: "manual", path: "manual", segment: "manual", label: "Manuel Testler", group: "Tasarım" },
  { key: "import", path: "import", segment: "import", label: "İçe Aktar", group: "Tasarım" },
  { key: "requirements", path: "requirements", segment: "requirements", label: "Gereksinimler", group: "Tasarım" },
  { key: "analysis", path: "analysis", segment: "analysis", label: "📄 Analiz", group: "Tasarım" },
  { key: "approvals", path: "approvals", segment: "approvals", label: "Onaylar", group: "Tasarım" },
  { key: "test-cases", path: "test-cases", segment: "test-cases", label: "AI Test Case", group: "Tasarım" },
  { key: "sifir-bilgi", path: "sifir-bilgi", segment: "sifir-bilgi", label: "🤖 Sıfır Bilgi", group: "Tasarım" },
  { key: "wizard", path: "wizard", segment: "wizard", label: "🪄 Sihirbaz", group: "Tasarım" },

  // Üretim
  { key: "automation", path: "automation", segment: "automation", label: "Otomasyon", group: "Üretim" },
  { key: "recorder", path: "recorder", segment: "recorder", label: "Kaydedici", group: "Üretim" },
  { key: "locators", path: "locators", segment: "locators", label: "Locator'lar", group: "Üretim" },
  { key: "flows", path: "flows", segment: "flows", label: "Akışlar", group: "Üretim" },
  { key: "api-testing", path: "api-testing", segment: "api-testing", label: "API Test", group: "Üretim" },
  { key: "chain-builder", path: "chain-builder", segment: "chain-builder", label: "Chain Builder", group: "Üretim" },
  { key: "mobile", path: "mobile", segment: "mobile", label: "Mobil", group: "Üretim" },
  { key: "automation-gen", path: "automation-gen", segment: "automation-gen", label: "Otomasyon Üret", group: "Üretim" },
  { key: "api-tests", path: "api-tests", segment: "api-tests", label: "API Koleksiyonu", group: "Üretim" },
  { key: "page-objects", path: "page-objects", segment: "page-objects", label: "Page Objects", group: "Üretim" },
  { key: "device-manager", path: "device-manager", segment: "device-manager", label: "Cihaz Yöneticisi", group: "Üretim" },
  { key: "manual-to-automation", path: "manual-to-automation", segment: "manual-to-automation", label: "Manuel→Otomasyon", group: "Üretim" },

  // Koşu & Gözlem
  { key: "runs", path: "runs", segment: "runs", label: "Koşular", group: "Koşu & Gözlem" },
  { key: "schedules", path: "schedules", segment: "schedules", label: "Zamanlayıcı", group: "Koşu & Gözlem" },
  { key: "cicd", path: "cicd", segment: "cicd", label: "CI/CD", group: "Koşu & Gözlem" },
  { key: "reports", path: "reports", segment: "reports", label: "Raporlar", group: "Koşu & Gözlem" },
  { key: "flaky", path: "flaky", segment: "flaky", label: "Flaky Testler", group: "Koşu & Gözlem" },
  { key: "healing", path: "healing", segment: "healing", label: "Self-Healing", group: "Koşu & Gözlem" },
  { key: "executions", path: "executions", segment: "executions", label: "Koşular", group: "Koşu & Gözlem" },
  { key: "analytics", path: "analytics", segment: "analytics", label: "Analitik", group: "Koşu & Gözlem" },
  { key: "test-history", path: "test-history", segment: "test-history", label: "Test Geçmişi", group: "Koşu & Gözlem" },
  { key: "debug-report", path: "debug-report", segment: "debug-report", label: "Debug Raporu", group: "Koşu & Gözlem" },

  // Kalite
  { key: "visual", path: "visual", segment: "visual", label: "Görsel Regresyon", group: "Kalite" },
  { key: "accessibility", path: "accessibility", segment: "accessibility", label: "Erişilebilirlik", group: "Kalite" },
  { key: "monkey", path: "monkey", segment: "monkey", label: "Monkey Test", group: "Kalite" },
  { key: "security", path: "security", segment: "security", label: "Güvenlik", group: "Kalite" },
  { key: "prioritize", path: "prioritize", segment: "prioritize", label: "Önceliklendirme", group: "Kalite" },
  { key: "playwright-console", path: "playwright-console", segment: "playwright-console", label: "Playwright Konsol", group: "Kalite" },
  { key: "regression", path: "regression", segment: "regression", label: "Regresyon Setleri", group: "Kalite" },
  { key: "coverage", path: "coverage", segment: "coverage", label: "Kapsam", group: "Kalite" },

  // Veri
  { key: "synthetic", path: "synthetic", segment: "synthetic", label: "Sentetik Veri", group: "Veri" },
  { key: "test-data", path: "test-data", segment: "test-data", label: "Test Verileri", group: "Veri" },
  { key: "privacy", path: "privacy", segment: "privacy", label: "Gizlilik", group: "Veri" },

  // Yapılandırma
  { key: "environments", path: "environments", segment: "environments", label: "Ortamlar", group: "Yapılandırma" },
  { key: "integrations", path: "integrations", segment: "integrations", label: "Entegrasyonlar", group: "Yapılandırma" },
  { key: "settings", path: "settings", segment: "settings", label: "Ayarlar", group: "Yapılandırma" },
  { key: "dsl-catalog-project", path: "dsl-catalog", segment: "dsl-catalog", label: "DSL Kataloğu", group: "Yapılandırma" },
  { key: "workflows", path: "workflows", segment: "workflows", label: "Workflows", group: "Yapılandırma" },
  { key: "banking-team", path: "banking-team", segment: "banking-team", label: "Bankacılık Ekibi", group: "Yapılandırma" },

  // AI
  { key: "ai-chat", path: "ai-chat", segment: "ai-chat", label: "AI Asistan", group: "AI" },
  { key: "nl-test-gen", path: "nl-test-gen", segment: "nl-test-gen", label: "NL Test Üretici", group: "AI" },
  { key: "qa-orchestrator", path: "qa-orchestrator", segment: "qa-orchestrator", label: "QA Orkestratör", group: "AI" },
  { key: "ai-metrics", path: "ai-metrics", segment: "ai-metrics", label: "LLM Metrikleri", group: "AI" },

  // Saklı / yardımcı
  { key: "live-devices", path: "mobile", segment: "mobile", label: "Canlı Cihazlar", group: "" },
  { key: "mobile-history", path: "mobile/history", segment: "mobile", label: "Mobil Geçmiş", group: "" },
  { key: "whats-new", path: null, segment: "whats-new", label: "✨ Yenilikler", group: "" },
];

export const ROUTE_BY_KEY: Record<string, RouteCatalogEntry> = Object.fromEntries(
  ROUTE_CATALOG.map((r) => [r.key, r]),
);
