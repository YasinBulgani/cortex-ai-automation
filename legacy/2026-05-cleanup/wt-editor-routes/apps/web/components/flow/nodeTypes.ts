export type FlowNodeType =
  | "trigger"
  | "http_request"
  | "condition"
  | "delay"
  | "scenario"
  | "notification"
  | "transform"
  | "database"
  | "loop"
  | "end";

export interface FlowNodeConfig {
  type: FlowNodeType;
  label: string;
  icon: string;
  color: string;
  bgColor: string;
  borderColor: string;
  description: string;
  defaultData: Record<string, unknown>;
}

export const NODE_CONFIGS: Record<FlowNodeType, FlowNodeConfig> = {
  trigger: {
    type: "trigger",
    label: "Tetikleyici",
    icon: "⚡",
    color: "#f59e0b",
    bgColor: "#fffbeb",
    borderColor: "#f59e0b",
    description: "Akışı başlatan tetikleyici",
    defaultData: { triggerType: "manual", cron: "" },
  },
  http_request: {
    type: "http_request",
    label: "HTTP İstek",
    icon: "🌐",
    color: "#3b82f6",
    bgColor: "#eff6ff",
    borderColor: "#3b82f6",
    description: "API çağrısı yapın",
    defaultData: { method: "GET", url: "", headers: {}, body: "" },
  },
  condition: {
    type: "condition",
    label: "Koşul",
    icon: "🔀",
    color: "#8b5cf6",
    bgColor: "#f5f3ff",
    borderColor: "#8b5cf6",
    description: "Koşula göre dallanma",
    defaultData: { field: "", operator: "equals", value: "" },
  },
  delay: {
    type: "delay",
    label: "Bekleme",
    icon: "⏱️",
    color: "#ec4899",
    bgColor: "#fdf2f8",
    borderColor: "#ec4899",
    description: "Belirli süre bekleyin",
    defaultData: { duration: 1000, unit: "ms" },
  },
  scenario: {
    type: "scenario",
    label: "Test Senaryosu",
    icon: "🧪",
    color: "#10b981",
    bgColor: "#ecfdf5",
    borderColor: "#10b981",
    description: "Test senaryosu çalıştırın",
    defaultData: { scenarioId: "", scenarioName: "" },
  },
  notification: {
    type: "notification",
    label: "Bildirim",
    icon: "🔔",
    color: "#f97316",
    bgColor: "#fff7ed",
    borderColor: "#f97316",
    description: "Bildirim gönderin",
    defaultData: { channel: "email", message: "" },
  },
  transform: {
    type: "transform",
    label: "Dönüştür",
    icon: "🔄",
    color: "#06b6d4",
    bgColor: "#ecfeff",
    borderColor: "#06b6d4",
    description: "Veriyi dönüştürün",
    defaultData: { expression: "" },
  },
  database: {
    type: "database",
    label: "Veritabanı",
    icon: "🗄️",
    color: "#64748b",
    bgColor: "#f8fafc",
    borderColor: "#64748b",
    description: "Veritabanı sorgusu",
    defaultData: { query: "", dbType: "postgresql" },
  },
  loop: {
    type: "loop",
    label: "Döngü",
    icon: "🔁",
    color: "#a855f7",
    bgColor: "#faf5ff",
    borderColor: "#a855f7",
    description: "Elemanlar üzerinde döngü",
    defaultData: { iterations: 1 },
  },
  end: {
    type: "end",
    label: "Bitiş",
    icon: "🏁",
    color: "#ef4444",
    bgColor: "#fef2f2",
    borderColor: "#ef4444",
    description: "Akışı sonlandırın",
    defaultData: {},
  },
};

export const NODE_CATEGORIES = [
  {
    name: "Tetikleyiciler",
    types: ["trigger"] as FlowNodeType[],
  },
  {
    name: "Aksiyon",
    types: ["http_request", "scenario", "database", "notification"] as FlowNodeType[],
  },
  {
    name: "Mantık",
    types: ["condition", "loop", "delay"] as FlowNodeType[],
  },
  {
    name: "Dönüşüm",
    types: ["transform", "end"] as FlowNodeType[],
  },
];
