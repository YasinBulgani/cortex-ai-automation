export type PersonaId = "balanced" | "analyst" | "qa_designer" | "automation_engineer" | "testops_lead";

export type PersonaPreset = {
  id: PersonaId;
  label: string;
  shortLabel: string;
  description: string;
  sidebarNote: string;
  focusSegments: string[];
  focusFlows: string[];
  quickLinks: Array<{ label: string; path: string }>;
};

export const PERSONA_STORAGE_KEY = "bgts_persona_focus";

export const PERSONA_PRESETS: PersonaPreset[] = [
  {
    id: "balanced",
    label: "Takim Modu",
    shortLabel: "Takim",
    description: "Tüm akislar esit gorunur. Urunu genel kullanim ve demo acisindan dengeli sunar.",
    sidebarNote: "Tüm moduller esit agirlikta gorunur.",
    focusSegments: [],
    focusFlows: [],
    quickLinks: [
      { label: "Proje Özeti", path: "" },
      { label: "Senaryolar", path: "scenarios" },
      { label: "Koşular", path: "executions" },
    ],
  },
  {
    id: "analyst",
    label: "Analist Odagi",
    shortLabel: "Analist",
    description: "Doküman, gereksinim, kapsam ve onay tarafini one cikarir.",
    sidebarNote: "Manuel Senaryolar bölümünde gereksinim ve onay akışları öne çıkar.",
    focusSegments: ["import", "requirements", "coverage", "analysis", "approvals"],
    focusFlows: ["Manuel Senaryolar"],
    quickLinks: [
      { label: "İçe Aktar", path: "import" },
      { label: "Gereksinimler", path: "requirements" },
      { label: "Onaylar", path: "approvals" },
    ],
  },
  {
    id: "qa_designer",
    label: "QA Tasarımci Odagi",
    shortLabel: "QA",
    description: "Senaryo, AI test case, is akislari ve test verisi tarafini onceliklendirir.",
    sidebarNote: "Manuel Senaryolar (senaryo, test verisi, onay) daha görünür olur.",
    focusSegments: ["scenarios", "test-cases", "approvals", "workflows", "test-data", "synthetic"],
    focusFlows: ["Manuel Senaryolar"],
    quickLinks: [
      { label: "Senaryolar", path: "scenarios" },
      { label: "AI Test Case", path: "test-cases" },
      { label: "Test Verileri", path: "test-data" },
    ],
  },
  {
    id: "automation_engineer",
    label: "Otomasyon Muhendisi Odagi",
    shortLabel: "Otomasyon",
    description: "Artefakt üretimi, locator, page object ve servis testi akislarini one cikarir.",
    sidebarNote: "Otomasyon bölümünde üretim, seçici ve API test linkleri öne çıkar.",
    focusSegments: [
      "manual-to-automation",
      "automation-gen",
      "manual",
      "automation",
      "page-objects",
      "locators",
      "recorder",
      "api-testing",
      "api-tests",
    ],
    focusFlows: ["Otomasyon"],
    quickLinks: [
      { label: "AI Otomasyon Üret", path: "automation-gen" },
      { label: "Dokümandan Otomasyon", path: "manual-to-automation" },
      { label: "API Testleri", path: "api-tests" },
    ],
  },
  {
    id: "testops_lead",
    label: "TestOps / Lead Odagi",
    shortLabel: "Lead",
    description: "Koşular, raporlar, trendler ve entegrasyonlar etrafinda karar almayi hizlandirir.",
    sidebarNote: "Otomasyon bölümünde koşu, rapor ve operasyon ekranları öne çıkar.",
    focusSegments: [
      "executions",
      "runs",
      "regression",
      "schedules",
      "cicd",
      "integrations",
      "reports",
      "analytics",
      "debug-report",
      "flaky",
      "visual",
      "accessibility",
      "monkey",
    ],
    focusFlows: ["Otomasyon"],
    quickLinks: [
      { label: "Koşular", path: "executions" },
      { label: "Raporlar", path: "reports" },
      { label: "Analitik", path: "analytics" },
    ],
  },
];

export function getPersonaPreset(_id: string | null | undefined): PersonaPreset {
  return PERSONA_PRESETS[0];
}
