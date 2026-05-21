/**
 * Workflow templates — tipik QA akışları.
 *
 * Her template bir "starter pack" — kullanıcı uygulayınca senaryo + schedule
 * + integration konfigürasyonu hazır gelir.
 */

export type WorkflowTemplateStep = {
  title: string;
  description: string;
  page: string; // örn: "scenarios/new"
};

export type WorkflowTemplate = {
  id: string;
  title: string;
  description: string;
  icon: string;
  difficulty: "beginner" | "intermediate" | "advanced";
  estimatedTime: string; // örn "10 dk"
  tags: string[];
  steps: WorkflowTemplateStep[];
  outcome: string;
};

export const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [
  {
    id: "smoke-suite",
    title: "Smoke Suite",
    description: "Her deploy'da koşan kısa & kritik test paketi. Login, ana akış, ödeme.",
    icon: "🔥",
    difficulty: "beginner",
    estimatedTime: "15 dk",
    tags: ["smoke", "ci", "günlük"],
    steps: [
      {
        title: "5 kritik senaryo seç",
        description: "Login + ana akış + ödeme + logout + kritik form",
        page: "scenarios",
      },
      {
        title: "'smoke' tag'i ekle",
        description: "Senaryoları gruplandır",
        page: "scenarios",
      },
      {
        title: "Schedule oluştur — her deploy'da",
        description: "GitHub Actions webhook tetikleyicisiyle",
        page: "schedules",
      },
      {
        title: "Slack notification ekle",
        description: "Fail durumunda #qa-alerts'e mesaj",
        page: "integrations",
      },
    ],
    outcome: "Her deploy'dan sonra 5 dakika içinde durum bilirsin.",
  },
  {
    id: "regression-suite",
    title: "Regression Suite",
    description: "Haftalık tam regresyon — tüm özellikleri kapsayan büyük paket.",
    icon: "🔄",
    difficulty: "intermediate",
    estimatedTime: "45 dk",
    tags: ["regression", "haftalık"],
    steps: [
      {
        title: "Tüm önemli senaryoları topla",
        description: "Genelde 50-200 test",
        page: "scenarios",
      },
      {
        title: "Regresyon seti oluştur",
        description: "Kategorilere böl: auth, payment, dashboard, ...",
        page: "regression",
      },
      {
        title: "Cuma akşamı schedule yap",
        description: "Hafta sonu boyunca koşsun",
        page: "schedules",
      },
      {
        title: "Pazartesi rapor incele",
        description: "Allure report + AI debug",
        page: "reports",
      },
    ],
    outcome: "Pazartesi sabahı tüm sistem durumunu görürsün.",
  },
  {
    id: "api-contract",
    title: "API Contract Testing",
    description: "OpenAPI spec'inden otomatik test üret + her commit'te koş.",
    icon: "🔌",
    difficulty: "intermediate",
    estimatedTime: "30 dk",
    tags: ["api", "contract"],
    steps: [
      {
        title: "OpenAPI spec'ini içe aktar",
        description: "Swagger URL veya JSON dosyası",
        page: "api-tests",
      },
      {
        title: "Endpoint'ler için otomatik test üret",
        description: "Positive + negative + auth varyantları",
        page: "api-tests",
      },
      {
        title: "Chain builder ile multi-step",
        description: "Login → Create → Update → Delete sırası",
        page: "chain-builder",
      },
      {
        title: "CI/CD webhook bağla",
        description: "Her commit sonrası tetikle",
        page: "cicd",
      },
    ],
    outcome: "API contract değişikliklerini otomatik yakalarsın.",
  },
  {
    id: "mobile-smoke",
    title: "Mobil Smoke",
    description: "iOS + Android paralel temel akış kontrolü.",
    icon: "📱",
    difficulty: "intermediate",
    estimatedTime: "25 dk",
    tags: ["mobile", "ios", "android", "smoke"],
    steps: [
      {
        title: "Mobil senaryo yaz (cross-platform)",
        description: "Appium ile native + hybrid",
        page: "mobile",
      },
      {
        title: "Device matrix tanımla",
        description: "iPhone 14, Pixel 7, vb.",
        page: "device-manager",
      },
      {
        title: "Paralel koşum etkinleştir",
        description: "Her cihaz aynı anda",
        page: "executions/new",
      },
    ],
    outcome: "Her platformda çalışma onayı 10 dakikada.",
  },
  {
    id: "flaky-management",
    title: "Flaky Yönetimi",
    description: "Kararsız testleri tespit et + otomatik quarantine.",
    icon: "🎲",
    difficulty: "advanced",
    estimatedTime: "20 dk",
    tags: ["flaky", "quality"],
    steps: [
      {
        title: "Flaky dashboard'u incele",
        description: "Score > %50 olanlar tehlikeli",
        page: "flaky",
      },
      {
        title: "Auto-quarantine threshold ayarla",
        description: "Settings → flakiness > %60 → quarantine",
        page: "settings",
      },
      {
        title: "Slack alert kur",
        description: "Yeni quarantine olduğunda bildirim",
        page: "integrations",
      },
      {
        title: "Healer agent'ı aktif et",
        description: "Otomatik fix önerisi + PR",
        page: "healing",
      },
    ],
    outcome: "Flaky test bakımı %80 otomatize.",
  },
  {
    id: "visual-regression",
    title: "Görsel Regresyon",
    description: "UI değişiklikleri pixel-perfect + perceptual diff ile kontrol.",
    icon: "👀",
    difficulty: "intermediate",
    estimatedTime: "20 dk",
    tags: ["visual", "ui"],
    steps: [
      {
        title: "Baseline screenshot'lar yükle",
        description: "Her sayfa için 1 referans",
        page: "visual",
      },
      {
        title: "Diff threshold ayarla",
        description: "%2 üstü = fail",
        page: "visual",
      },
      {
        title: "PR webhook'a bağla",
        description: "PR açılınca otomatik koş",
        page: "cicd",
      },
    ],
    outcome: "UI bozulmalarını PR sırasında yakalayan kanit.",
  },
  {
    id: "compliance-suite",
    title: "KVKK/BDDK Uyum Paketi",
    description: "Yasal gereklilikler için özel test paketi — Türk fintech.",
    icon: "🛡️",
    difficulty: "advanced",
    estimatedTime: "60 dk",
    tags: ["compliance", "kvkk", "bddk"],
    steps: [
      {
        title: "Privacy test seti kur",
        description: "PII handling, KVKK Md.11(e) erasure flow",
        page: "privacy",
      },
      {
        title: "Audit log doğrulama testleri",
        description: "BDDK Md.14 audit trail",
        page: "test-cases",
      },
      {
        title: "RBAC senaryoları",
        description: "Her rol için izin testleri",
        page: "scenarios",
      },
      {
        title: "Aylık compliance raporu",
        description: "PDF export + paydaş paylaşımı",
        page: "reports",
      },
    ],
    outcome: "Yıllık denetim öncesi otomatik kontrol mekanizması.",
  },
  {
    id: "ai-driven",
    title: "AI-Driven Test Generation",
    description: "Manuel test yazmadan, AI'a tüm üretimi bırak.",
    icon: "🤖",
    difficulty: "beginner",
    estimatedTime: "15 dk",
    tags: ["ai", "9-agent"],
    steps: [
      {
        title: "Sıfır Bilgi pipeline'ı başlat",
        description: "URL/PDF/Swagger gir",
        page: "sifir-bilgi",
      },
      {
        title: "9 ajanın çıktısını incele",
        description: "Generated scenarios + reviewer feedback",
        page: "qa-orchestrator",
      },
      {
        title: "Üretileni approve et",
        description: "Approval workflow",
        page: "approvals",
      },
    ],
    outcome: "Manuel test yazımına gerek kalmadan kapsamlı paket.",
  },
];

export function getTemplate(id: string): WorkflowTemplate | undefined {
  return WORKFLOW_TEMPLATES.find((t) => t.id === id);
}

export function templatesByDifficulty(difficulty: WorkflowTemplate["difficulty"]): WorkflowTemplate[] {
  return WORKFLOW_TEMPLATES.filter((t) => t.difficulty === difficulty);
}

export function templatesByTag(tag: string): WorkflowTemplate[] {
  return WORKFLOW_TEMPLATES.filter((t) => t.tags.includes(tag));
}
