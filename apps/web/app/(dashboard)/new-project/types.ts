/**
 * New Project Wizard — Type Definitions
 *
 * 9 adımlı proje oluşturma sihirbazı için ortak tip tanımları.
 */

export type ManualTest = {
  title: string;
  steps: { action: string; expected: string }[];
};

export type BddScenario = {
  title: string;
  description?: string;
  gherkin?: string;
  tags?: string[];
  steps?: { keyword: string; text: string }[];
};

export type RegSet = {
  name: string;
  description: string;
  scenario_ids: string[];
  priority: "critical" | "high" | "medium" | "low";
};

export type SavedScenario = { id: string; title: string; status: string };

export type AutomationFile = { name: string; content: string; scenario_title?: string };
export type LocatorAlternative = { type: string; value: string };
export type LocatorEntry = {
  key: string;
  type: string;
  value: string;
  alternatives?: LocatorAlternative[];
  tag?: string;
  text?: string;
};
export type LocatorFile = { name: string; module: string; locators: LocatorEntry[] };

export type LocatorMatch = {
  scenario_id: string;
  scenario_title: string;
  step_index: number;
  step_text: string;
  element_phrase: string;
  suggested_key: string;
  suggested_locator: LocatorAlternative;
  /** XPath stabilite analizi — sadece type === "xpath" için dolu */
  xpath_quality?: XPathQuality | null;
  confidence: number;
  reason: string;
  /**
   * "llm": AI semantic match · "heuristic": PascalCase token overlap fallback ·
   * "manual": kullanıcı UI'dan başka bir locator key seçti
   */
  source?: "llm" | "heuristic" | "manual";
};

/** Match listesi filter/sort sonrası yeniden sıralansa da durum korunsun diye composite key */
export function matchKey(m: Pick<LocatorMatch, "scenario_id" | "step_index" | "suggested_key">): string {
  return `${m.scenario_id}::${m.step_index}::${m.suggested_key}`;
}

export type LocatorMatchLlmStatus = {
  available: boolean;
  match_count: number;
  error: string | null;
};

export type LocatorMatchStatus = "pending" | "approved" | "rejected";
export type MaviyakaFeature = { title: string; content: string };

// Step 7 — Manuel senaryo ↔ locator tam eşleştirme (LLM destekli, XPath bağlamalı)
export type XPathQuality = {
  score: number;                           // 0-100
  grade: "good" | "warn" | "bad" | "invalid";
  issues: string[];                        // kırılganlık sebepleri
  strengths: string[];                     // stabilite sebepleri
};

export type StepMapping = {
  idx: number;
  original: string;
  action: "open" | "click" | "input" | "clear" | "see" | "verify" | "wait";
  locator_key: string | null;
  xpath: string | null;
  xpath_quality?: XPathQuality | null;
  data_value: string | null;
  source: "llm" | "rule" | "auto" | "derived";
  score?: number | null;
};

export type ScenarioMappingReport = {
  scenario_id: string;
  scenario_title: string;
  steps: StepMapping[];
  llm_used: boolean;
  error?: string;
};

// URL tabanlı ya da element gerektirmeyen aksiyonlar → locator gerekmez
export const NO_LOCATOR_ACTIONS = new Set<StepMapping["action"]>(["open"]);
export const actionNeedsLocator = (a: StepMapping["action"]) => !NO_LOCATOR_ACTIONS.has(a);

// IDE için dosya tipi (IntelliJ benzeri proje ağacı)
export type IdeFileKind = "feature" | "steps" | "data" | "locator" | "config" | "page";
export type IdeFile = {
  path: string;
  name: string;
  folder: string;
  kind: IdeFileKind;
  content: string;
  language: "gherkin" | "typescript" | "python" | "json" | "yaml";
  /**
   * Sadece `kind === "feature"` için anlamlı. `true` olduğunda ▶ Run basıldığında
   * bu feature pytest'e gönderilmez; diğer dosya türleri için yok sayılır.
   */
  disabled?: boolean;
};
