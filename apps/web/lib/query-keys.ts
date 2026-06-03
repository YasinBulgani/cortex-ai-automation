/**
 * Merkezi Query Key Kayıt Dosyası
 *
 * Tüm domain query key factory'lerinin tek giriş noktası.
 * Yeni bir key eklerken:
 *   1. Hook dosyasında export const xxxKeys = { ... } tanımla
 *   2. Burada re-export et
 *   3. ROOT_KEYS'e root namespace'i ekle (çakışma kontrolü)
 *
 * Namespace çakışmalarını önlemek için ROOT_KEYS sabit listesine bakın.
 */

export { managementKeys }   from "@/lib/hooks/use-management";
export { apiTestingKeys }   from "@/lib/hooks/use-api-testing";
export { projectKeys }      from "@/lib/hooks/use-projects";
export { authKeys }         from "@/lib/hooks/use-auth";
export { notificationKeys } from "@/lib/hooks/use-mgmt-notifications";
export { commentKeys }      from "@/lib/hooks/use-mgmt-comments";
export { designKeys }       from "@/lib/hooks/use-mgmt-design";
export { dslKeys }          from "@/lib/hooks/use-dsl";
export { pipelineKeys }     from "@/lib/hooks/use-pipeline";
export { agentKeys }        from "@/lib/hooks/use-agents";
export { scenarioKeys }     from "@/lib/hooks/use-scenarios";
export { aiMetricsKeys }    from "@/lib/hooks/use-ai-metrics";
export { webDashboardKeys } from "@/lib/hooks/use-web-dashboard";

/**
 * Root namespace listesi — çakışma önlemi.
 * Her domain kendi benzersiz root string'ini buraya eklemeli.
 */
export const ROOT_KEYS = [
  "management",   // managementKeys
  "api-testing",  // apiTestingKeys
  "projects",     // projectKeys
  "auth",         // authKeys
  "notifications",// notificationKeys
  "comments",     // commentKeys
  "design",       // designKeys
  "dsl",          // dslKeys
  "pipeline",     // pipelineKeys
  "agents",       // agentKeys
  "scenarios",    // scenarioKeys
  "ai-metrics",   // aiMetricsKeys
  "web-dashboard",// webDashboardKeys
] as const;

export type RootKey = (typeof ROOT_KEYS)[number];
