// ── Types ────────────────────────────────────────────────────────────────────

export type Platform = "android" | "ios";
export type DeviceKind = "emulator" | "simulator" | "physical";
export type DeviceStatus = "idle" | "running" | "booting" | "offline" | "error";

export type Device = {
  id: string;
  name: string;
  platform: Platform;
  osVersion: string;
  profile: string;
  kind: DeviceKind;
  status: DeviceStatus;
  battery: number;
  cpuPct: number;
  ramPct: number;
  appiumPort: number;
  currentStep?: string;
  stepsDone: number;
  stepsTotal: number;
  healStreak: number;
};

export type AppiumAction = {
  action: "launch" | "find" | "tap" | "sendKeys" | "verifyVisible" | "wait" | "swipe";
  by?: "accessibilityId" | "xpath" | "predicate";
  value?: string;
  text?: string;
  timeout?: number;
  ms?: number;
  direction?: "up" | "down" | "left" | "right";
};

export type Session = {
  id: string;
  deviceId: string;
  scenarioName: string;
  status: "queued" | "running" | "passed" | "failed";
  startedAt: number;
  finishedAt?: number;
  healed: number;
};

export type LogEntry = {
  id: number;
  ts: number;
  level: "info" | "warn" | "error" | "llm" | "heal";
  deviceId?: string;
  sessionId?: string;
  message: string;
};

export type BackendDevice = {
  id: string;
  name: string;
  platform: Platform;
  os_version: string;
  profile: string;
  kind: DeviceKind;
  status: DeviceStatus;
  battery: number;
  cpu_pct: number;
  ram_pct: number;
  current_step?: string | null;
  steps_done: number;
  steps_total: number;
  heal_streak: number;
  appium_url: string;
};

export type BackendStepResp = {
  steps: AppiumAction[];
  model: string;
  fallback_used: boolean;
};

export type SeedScenario = {
  id: string;
  title: string;
  category: string;
  difficulty: "kolay" | "orta" | "zor";
  platforms: string[];
  description: string;
  prompt: string;
  expected_steps: number;
  tags: string[];
};

// ── Constants ────────────────────────────────────────────────────────────────

export const INITIAL_DEVICES: Device[] = [
  { id: "and-01", name: "Pixel 8",            platform: "android", osVersion: "14", profile: "pixel_8",       kind: "emulator",  status: "idle",    battery: 92,  cpuPct: 8,  ramPct: 34, appiumPort: 4723, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "and-02", name: "Pixel 8 Pro",        platform: "android", osVersion: "14", profile: "pixel_8_pro",   kind: "emulator",  status: "idle",    battery: 88,  cpuPct: 6,  ramPct: 38, appiumPort: 4724, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "and-03", name: "Galaxy S23 (OneUI)", platform: "android", osVersion: "13", profile: "galaxy_s23",    kind: "emulator",  status: "idle",    battery: 74,  cpuPct: 12, ramPct: 42, appiumPort: 4725, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "and-04", name: "Pixel 6",            platform: "android", osVersion: "12", profile: "pixel_6",       kind: "emulator",  status: "idle",    battery: 100, cpuPct: 4,  ramPct: 30, appiumPort: 4726, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "and-05", name: "Pixel 5 (legacy)",   platform: "android", osVersion: "11", profile: "pixel_5",       kind: "emulator",  status: "idle",    battery: 67,  cpuPct: 9,  ramPct: 40, appiumPort: 4727, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "and-06", name: "Nexus 5X (legacy)",  platform: "android", osVersion: "9",  profile: "nexus_5x",      kind: "emulator",  status: "offline", battery: 0,   cpuPct: 0,  ramPct: 0,  appiumPort: 4728, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "ios-01", name: "iPhone 15 Pro",      platform: "ios",     osVersion: "17", profile: "iphone_15_pro", kind: "simulator", status: "idle",    battery: 95,  cpuPct: 5,  ramPct: 28, appiumPort: 4730, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "ios-02", name: "iPhone 15",          platform: "ios",     osVersion: "17", profile: "iphone_15",     kind: "simulator", status: "idle",    battery: 84,  cpuPct: 7,  ramPct: 31, appiumPort: 4731, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "ios-03", name: "iPhone 14",          platform: "ios",     osVersion: "16", profile: "iphone_14",     kind: "simulator", status: "idle",    battery: 62,  cpuPct: 11, ramPct: 36, appiumPort: 4732, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "ios-04", name: "iPhone SE (3rd)",    platform: "ios",     osVersion: "15", profile: "iphone_se_3",   kind: "simulator", status: "idle",    battery: 77,  cpuPct: 6,  ramPct: 29, appiumPort: 4733, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
];

export const SAMPLE_PROMPTS = [
  "Uygulamayı aç, Giriş yap butonuna bas, email alanına test@bgts.ai yaz, şifre alanına Test123! yaz, Devam'a bas, ana sayfanın yüklendiğini doğrula.",
  "Onboarding ekranlarını geç, bildirim izinlerini reddet, dil olarak Türkçe seç, hesap oluştur sayfasının açıldığını doğrula.",
  "Ürün arama kutusuna 'kahve' yaz, filtreyi 'fiyat artan' yap, ilk ürünü sepete ekle, sepet sayacının 1 olduğunu doğrula.",
  "Profil sayfasına git, 'Çıkış Yap' butonuna bas, onay dialog'unda 'Evet' seç, login sayfasına döndüğünü doğrula.",
];
