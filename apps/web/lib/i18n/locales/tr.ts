/**
 * Turkish translations — default locale.
 * Keys are dot-separated namespaces: `namespace.key` or `namespace.sub.key`.
 */
export const tr = {
  // ── Common ────────────────────────────────────────────────────────────────
  common: {
    save: "Kaydet",
    cancel: "İptal",
    delete: "Sil",
    edit: "Düzenle",
    create: "Oluştur",
    close: "Kapat",
    confirm: "Onayla",
    search: "Ara",
    filter: "Filtrele",
    all: "Tümü",
    loading: "Yükleniyor…",
    saving: "Kaydediliyor…",
    noData: "Veri bulunamadı.",
    error: "Bir hata oluştu.",
    success: "İşlem başarılı.",
    add: "Ekle",
    remove: "Kaldır",
    view: "Görüntüle",
    back: "Geri",
    next: "İleri",
    previous: "Önceki",
    submit: "Gönder",
    reset: "Sıfırla",
    upload: "Yükle",
    download: "İndir",
    export: "Dışa Aktar",
    import: "İçe Aktar",
    refresh: "Yenile",
    settings: "Ayarlar",
    help: "Yardım",
    logout: "Çıkış Yap",
    login: "Giriş Yap",
    language: "Dil",
    status: "Durum",
    actions: "İşlemler",
    name: "İsim",
    description: "Açıklama",
    createdAt: "Oluşturma Tarihi",
    updatedAt: "Güncelleme Tarihi",
    optional: "opsiyonel",
    required: "zorunlu",
    total: "Toplam",
    yes: "Evet",
    no: "Hayır",
    unknown: "Bilinmiyor",
  },

  // ── Navigation ────────────────────────────────────────────────────────────
  nav: {
    dashboard: "Pano",
    projects: "Projeler",
    automation: "Otomasyon",
    management: "Test Yönetimi",
    settings: "Ayarlar",
    profile: "Profil",
  },

  // ── Auth ──────────────────────────────────────────────────────────────────
  auth: {
    email: "E-posta",
    password: "Şifre",
    forgotPassword: "Şifremi unuttum",
    signIn: "Giriş Yap",
    signOut: "Çıkış Yap",
    invalidCredentials: "Geçersiz e-posta veya şifre.",
    sessionExpired: "Oturumunuz sona erdi. Lütfen tekrar giriş yapın.",
  },

  // ── Test Management ───────────────────────────────────────────────────────
  management: {
    title: "Test Yönetimi",
    projects: "Projeler",
    cases: "Test Senaryoları",
    suites: "Test Paketleri",
    runs: "Test Koşuları",
    plans: "Test Planları",
    requirements: "Gereksinimler",
    defects: "Hatalar",
    importExport: "İçe/Dışa Aktar",

    // Dashboard
    dashboard: {
      title: "Yönetim Panosu",
      totalCases: "Toplam Senaryo",
      activeCases: "Aktif",
      passRate: "Geçme Oranı",
      blocked: "Engellendi",
      releaseReadiness: "Sürüm Hazırlığı",
      runBreakdown: "Koşu Dağılımı",
    },

    // Status labels
    status: {
      draft: "Taslak",
      active: "Aktif",
      archived: "Arşivlendi",
      not_run: "Koşulmadı",
      running: "Koşuluyor",
      passed: "Geçti",
      failed: "Başarısız",
      blocked: "Engellendi",
      skipped: "Atlandı",
      not_covered: "Kapsanmamış",
      covered: "Kapsandı",
      partial: "Kısmi",
      stale: "Güncel Değil",
    },

    // Cases
    cases: {
      create: "Senaryo Oluştur",
      title: "Başlık",
      key: "Anahtar",
      priority: "Öncelik",
      type: "Tür",
      automationStatus: "Otomasyon Durumu",
      steps: "Adımlar",
      preconditions: "Ön Koşullar",
      objective: "Hedef",
      tags: "Etiketler",
      archive: "Arşivle",
      archived: "Arşivlendi",
    },

    // Runs
    runs: {
      execute: "Çalıştır",
      stepResult: "Adım Sonucu",
      actualResult: "Gerçek Sonuç",
      executionNotes: "Notlar",
      evidence: "Kanıt Yükle",
      start: "Koşuyu Başlat",
      complete: "Koşuyu Tamamla",
    },

    // Requirements
    requirements: {
      matrix: "İzlenebilirlik Matrisi",
      key: "Gereksinim Anahtarı",
      source: "Kaynak",
      coverage: "Kapsam",
      cases: "Senaryolar",
      linkRequirement: "Gereksinim Bağla",
      externalKey: "Dış Anahtar",
      titleSnapshot: "Gereksinim Başlığı",
      url: "URL",
      externalSource: "Kaynak",
      noLinked: "Bu gereksinim için bağlı test senaryosu yok.",
      noRequirements: "Henüz gereksinim bağlantısı yok.",
      noResults: "Filtreyle eşleşen gereksinim bulunamadı.",
    },

    // Import
    import: {
      dropzone: "CSV veya JSON dosyasını buraya sürükleyin",
      orClick: "veya tıklayın",
      fileAccepted: "Dosya kabul edildi",
      stagingPreview: "Hazırlık Önizlemesi",
      commit: "Kaydet",
      committing: "Kaydediliyor…",
      conflict: "Çakışma",
      ready: "Hazır",
      invalid: "Geçersiz",
      duplicate: "Olası Kopya",
    },
  },

  // ── Automation ────────────────────────────────────────────────────────────
  automation: {
    monkey: "Monkey Test",
    mobile: "Mobil Otomasyon",
    apiTesting: "API Testing",
    playwright: "Playwright Konsol",
    locators: "Locator Laboratuvarı",
    recorder: "Kaydedici",
  },

  // ── Errors ────────────────────────────────────────────────────────────────
  errors: {
    notFound: "Sayfa bulunamadı.",
    forbidden: "Bu sayfaya erişim izniniz yok.",
    serverError: "Sunucu hatası. Lütfen daha sonra tekrar deneyin.",
    networkError: "Ağ hatası. İnternet bağlantınızı kontrol edin.",
    validationError: "Lütfen tüm zorunlu alanları doldurun.",
    uploadFailed: "Dosya yüklenemedi.",
    saveFailed: "Kaydetme başarısız.",
  },
} as const;

export type TranslationDictionary = typeof tr;
