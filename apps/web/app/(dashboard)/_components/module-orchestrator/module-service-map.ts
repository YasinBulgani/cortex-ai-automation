import type { ServiceName } from "@/lib/dev-services";

export const CORE_SERVICES: ServiceName[] = ["postgres", "redis", "backend"];

export interface ModuleConfig {
  key: string;
  label: string;
  services: ServiceName[];
}

const MODULES: ModuleConfig[] = [
  // Sadece core yeten modüller
  { key: "management", label: "Management", services: [] },
  { key: "qa", label: "QA", services: [] },
  { key: "projects", label: "Projeler", services: [] },
  { key: "portfolio", label: "Portfolio", services: [] },
  { key: "reports", label: "Raporlar", services: [] },
  { key: "defects", label: "Defektler", services: [] },
  { key: "plans", label: "Test Planları", services: [] },
  { key: "requirements", label: "Gereksinimler", services: [] },
  { key: "notifications", label: "Bildirimler", services: [] },
  { key: "profile", label: "Profil", services: [] },
  { key: "settings", label: "Ayarlar", services: [] },
  { key: "admin", label: "Yönetim", services: [] },
  { key: "onboarding", label: "Başlangıç", services: [] },
  { key: "products", label: "Ürünler", services: [] },
  { key: "symbols", label: "Semboller", services: [] },
  { key: "task-drafts", label: "Görev Taslakları", services: [] },
  { key: "kb", label: "Bilgi Tabanı", services: [] },
  { key: "veri-kaynagi", label: "Veri Kaynağı", services: [] },

  // Otomasyon modülleri — engine + worker
  { key: "automation", label: "Otomasyon", services: ["engine", "worker"] },
  { key: "scenarios", label: "Senaryolar", services: ["engine", "worker"] },
  { key: "test-runs", label: "Test Koşuları", services: ["engine", "worker"] },
  { key: "runs", label: "Test Koşuları", services: ["engine", "worker"] },
  { key: "mobil-otomasyon", label: "Mobil Otomasyon", services: ["engine", "worker"] },
  { key: "api-testing", label: "API Testleri", services: ["engine", "worker"] },
  { key: "executions", label: "Yürütmeler", services: ["engine"] },
  { key: "dsl-catalog", label: "DSL Kataloğu", services: ["engine"] },
  { key: "bgtest-wizard", label: "Test Sihirbazı", services: ["engine", "worker", "ai-gateway"] },

  // AI modülleri — ai-gateway
  { key: "ai-agents", label: "AI Ajanları", services: ["ai-gateway"] },
  { key: "ai-workflows", label: "AI İş Akışları", services: ["ai-gateway"] },
  { key: "ai-quality", label: "AI Kalite", services: ["ai-gateway"] },
  { key: "flow-designer", label: "Akış Tasarımcısı", services: ["ai-gateway"] },
  { key: "workflows-gallery", label: "İş Akışları", services: ["ai-gateway"] },
  { key: "veri-simulatoru", label: "Veri Simülatörü", services: ["ai-gateway"] },

  // Hibrit — engine + ai-gateway
  { key: "ide", label: "IDE", services: ["engine", "ai-gateway"] },
  { key: "nexus-code", label: "Nexus Kod", services: ["engine", "ai-gateway"] },
];

const MODULE_MAP = new Map(MODULES.map((m) => [m.key, m]));
const DEFAULT_MODULE: ModuleConfig = { key: "home", label: "Ana Sayfa", services: [] };

export function getModuleFromPathname(pathname: string): ModuleConfig {
  const projectMatch = pathname.match(/^\/p\/[^/]+\/([^/]+)/);
  if (projectMatch) {
    const key = projectMatch[1];
    return MODULE_MAP.get(key) ?? { key, label: key, services: [] };
  }
  const globalMatch = pathname.match(/^\/([^/]+)/);
  if (globalMatch) {
    const key = globalMatch[1];
    return MODULE_MAP.get(key) ?? { key, label: key, services: [] };
  }
  return DEFAULT_MODULE;
}

export function getServicesToStop(from: ModuleConfig, to: ModuleConfig): ServiceName[] {
  return from.services.filter(
    (s) => !to.services.includes(s) && !CORE_SERVICES.includes(s),
  );
}

export function getServicesToStart(from: ModuleConfig, to: ModuleConfig): ServiceName[] {
  return to.services.filter(
    (s) => !from.services.includes(s) && !CORE_SERVICES.includes(s),
  );
}

export function hasServiceChange(from: ModuleConfig, to: ModuleConfig): boolean {
  return getServicesToStop(from, to).length > 0 || getServicesToStart(from, to).length > 0;
}
