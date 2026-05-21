export type PersonaId = "balanced";

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
    label: "Takım Modu",
    shortLabel: "Takım",
    description: "Tüm akışlar eşit görünür.",
    sidebarNote: "Tüm modüller eşit ağırlıkta görünür.",
    focusSegments: [],
    focusFlows: [],
    quickLinks: [
      { label: "Proje Özeti", path: "" },
      { label: "Senaryolar", path: "scenarios" },
      { label: "Koşular", path: "executions" },
    ],
  },
];

export function getPersonaPreset(_id: string | null | undefined): PersonaPreset {
  return PERSONA_PRESETS[0];
}
