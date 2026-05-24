import type { ProductTelemetry } from "./telemetry-types";
import type { ProductFamilyId } from "@/lib/product";

function spark(seed: number, len = 8, variance = 10): number[] {
  const result: number[] = [];
  let v = 40 + (seed % 40);
  for (let i = 0; i < len; i++) {
    v = Math.max(0, Math.min(100, v + ((seed * (i + 1) * 7) % (variance * 2)) - variance));
    result.push(Math.round(v));
  }
  return result;
}

const now = new Date().toISOString();
const ago = (mins: number) => new Date(Date.now() - mins * 60000).toISOString();

export const DEMO_TELEMETRY: Record<ProductFamilyId, ProductTelemetry> = {
  one: {
    productId: "one",
    isDemo: true,
    lastUpdated: now,
    stats: [
      { key: "projects", label: "Aktif Proje", value: 24, trend: "up", delta: 3, deltaLabel: "bu ay", sparkline: spark(11) },
      { key: "products", label: "Aktif Ürün", value: 8, unit: "/9", trend: "stable", sparkline: spark(22) },
      { key: "pass_rate", label: "Platform Pass Rate", value: "94.2", unit: "%", delta: 1.8, trend: "up", sparkline: spark(33) },
      { key: "integrations", label: "Entegrasyon", value: 12, trend: "stable", sparkline: spark(44) },
      { key: "users", label: "Aktif Kullanıcı", value: 38, trend: "up", delta: 5, sparkline: spark(55) },
      { key: "health", label: "Platform Sağlık", value: "99.1", unit: "%", severity: "ok", trend: "stable", sparkline: spark(66) },
    ],
    aiInsights: [
      { id: "one-1", title: "3 projede kapsam açığı tespit edildi", description: "Studio analizi, 'ödeme akışı' ve 'sepet' senaryolarının kritik edge case'leri kapsamadığını gösteriyor. Otomasyon tamamlama oranı %67.", severity: "warning", category: "Kapsam", ctaLabel: "Açıkları gör", ctaHref: "/portfolio", createdAt: ago(15), confidence: 87 },
      { id: "one-2", title: "CI/CD pipeline ortalama %23 hızlandı", description: "Son 2 haftada paralel koşu optimizasyonu sayesinde pipeline süresi 12 dakikadan 9.2 dakikaya indi.", severity: "success", category: "Performans", ctaLabel: "Pipeline raporları", ctaHref: "/portfolio", createdAt: ago(45), confidence: 95 },
      { id: "one-3", title: "Redis bağlantı havuzu kapasiteye yakın", description: "Pik saatlerde bağlantı havuzu %91 dolulukta. Ölçekleme önerisi: max_connections değerini 100→150 artır.", severity: "critical", category: "Altyapı", ctaLabel: "Sistem sağlık", ctaHref: "/system-health", createdAt: ago(8), confidence: 92 },
      { id: "one-4", title: "Yeni entegrasyon önerisi: GitHub Actions v4", description: "Mevcut workflow'larınız v3 Actions kullanıyor. v4'e geçiş %15 build süresi kazancı sağlayabilir.", severity: "info", category: "Entegrasyon", ctaLabel: "Entegrasyonlar", createdAt: ago(120), confidence: 74 },
    ],
    recentActivity: [
      { id: "a1", ts: ago(3), actor: "Elif K.", verb: "oluşturdu", object: "proje", objectName: "E-Ticaret v2", href: "/portfolio" },
      { id: "a2", ts: ago(12), actor: "Mehmet A.", verb: "entegre etti", object: "sistem", objectName: "GitHub Actions", href: "/portfolio" },
      { id: "a3", ts: ago(28), actor: "Zeynep S.", verb: "güncelledi", object: "ortam", objectName: "Production Config", href: "/portfolio" },
      { id: "a4", ts: ago(55), actor: "AI Agent", verb: "önerdi", object: "senaryo grubu", objectName: "Checkout Edge Cases", href: "/task-drafts" },
      { id: "a5", ts: ago(90), actor: "Kadir B.", verb: "arşivledi", object: "proje", objectName: "Legacy Mobile v1" },
    ],
    onboarding: [
      { id: "o1", title: "İlk projeyi oluştur", description: "Portfolio'da projenizi tanımlayın ve ürün bağlamını seçin.", done: true, ctaLabel: "Portfolio", href: "/portfolio" },
      { id: "o2", title: "CI/CD entegrasyonu bağla", description: "GitHub Actions veya Jenkins pipeline'ını platforma bağlayın.", done: true, ctaLabel: "Entegrasyonlar", href: "/portfolio" },
      { id: "o3", title: "İlk koşuyu çalıştır", description: "Bir senaryoyu seçip platform üzerinden ilk test koşunuzu başlatın.", done: false, ctaLabel: "Koşular", href: "/portfolio" },
      { id: "o4", title: "AI analizini etkinleştir", description: "Neurex Intelligence katmanını açarak akıllı önerileri aktif edin.", done: false, ctaLabel: "Intelligence", href: "/products/intelligence" },
    ],
  },

  studio: {
    productId: "studio",
    isDemo: true,
    lastUpdated: now,
    stats: [
      { key: "scenarios", label: "Senaryo", value: 312, trend: "up", delta: 28, deltaLabel: "bu hafta", sparkline: spark(12) },
      { key: "coverage", label: "Kapsam", value: "71.4", unit: "%", delta: 3.2, trend: "up", sparkline: spark(23) },
      { key: "approved", label: "Onaylı", value: 187, trend: "up", sparkline: spark(34) },
      { key: "draft", label: "Taslak", value: 64, trend: "down", sparkline: spark(45) },
      { key: "ai_generated", label: "AI Üretimi", value: 43, unit: "%", trend: "up", sparkline: spark(56) },
      { key: "requirements", label: "Gereksinim", value: 89, trend: "stable", sparkline: spark(67) },
    ],
    aiInsights: [
      { id: "s1", title: "Ödeme akışında 8 senaryo boşluğu", description: "Gereksinim analizi '3D Secure' ve 'kart reddi' akışları için senaryo olmadığını gösteriyor. Risk seviyesi: Yüksek.", severity: "critical", category: "Kapsam", ctaLabel: "Senaryo oluştur", createdAt: ago(20), confidence: 91 },
      { id: "s2", title: "AI %43 senaryo üretim oranına ulaştı", description: "Son 30 günde 134 senaryodan 57'si AI tarafından üretildi. İnsan onay süresi ortalama 4 dakika.", severity: "success", category: "AI Üretim", ctaLabel: "Task Drafts", ctaHref: "/task-drafts", createdAt: ago(60), confidence: 88 },
      { id: "s3", title: "12 senaryo 90 gündür güncellenmedi", description: "Eski senaryolar güncel UI değişiklerini yansıtmıyor olabilir. Gözden geçirme önerilir.", severity: "warning", category: "Bakım", ctaLabel: "Gözden geçir", createdAt: ago(240), confidence: 79 },
    ],
    recentActivity: [
      { id: "sa1", ts: ago(5), actor: "AI Studio", verb: "üretti", object: "senaryo", objectName: "Login - E2E Güvenlik Testi" },
      { id: "sa2", ts: ago(18), actor: "Ayşe N.", verb: "onayladı", object: "senaryo grubu", objectName: "Sepet Akışı (12 senaryo)" },
      { id: "sa3", ts: ago(35), actor: "Burak T.", verb: "içe aktardı", object: "gereksinim seti", objectName: "JIRA Sprint 24" },
      { id: "sa4", ts: ago(70), actor: "Zeynep S.", verb: "gönderdi", object: "onay talebi", objectName: "Profil Güncelleme Senaryoları" },
    ],
    onboarding: [
      { id: "so1", title: "Gereksinimler içe aktar", description: "JIRA, Confluence veya CSV dosyasından gereksinimlerinizi platforma aktarın.", done: true, ctaLabel: "İçe Aktar", href: "/portfolio" },
      { id: "so2", title: "İlk senaryo setini tasarla", description: "Gereksinimlerden otomatik senaryo taslakları oluşturun.", done: true, ctaLabel: "Senaryolar" },
      { id: "so3", title: "Onay akışını yapılandır", description: "Takım üyelerine senaryo onay yetkisi atayın.", done: false, ctaLabel: "Onaylar" },
      { id: "so4", title: "Kapsam raporunu gör", description: "Gereksinim-senaryo eşleşme oranınızı analiz edin.", done: false, ctaLabel: "Analiz" },
    ],
  },

  service: {
    productId: "service",
    isDemo: true,
    lastUpdated: now,
    stats: [
      { key: "endpoints", label: "API Endpoint", value: 156, trend: "up", delta: 12, sparkline: spark(13) },
      { key: "pass_rate", label: "Pass Rate", value: "96.8", unit: "%", delta: 0.5, trend: "up", sparkline: spark(24) },
      { key: "avg_latency", label: "Ort. Latency", value: "142", unit: "ms", delta: -18, trend: "up", sparkline: spark(35) },
      { key: "chains", label: "Chain", value: 23, trend: "stable", sparkline: spark(46) },
      { key: "security_issues", label: "Güvenlik Uyarısı", value: 3, severity: "warn", trend: "down", sparkline: spark(57) },
      { key: "contracts", label: "Kontrat", value: 41, trend: "up", sparkline: spark(68) },
    ],
    aiInsights: [
      { id: "svc1", title: "Auth servisi P99 latency spike", description: "Son 24 saatte /auth/token endpoint'i P99'da 890ms'e çıktı. Normal baseline 120ms. DB bağlantı havuzu doluluk oranı %94.", severity: "critical", category: "Performans", ctaLabel: "Endpoint detay", createdAt: ago(10), confidence: 94 },
      { id: "svc2", title: "3 kontrat drift tespit edildi", description: "Payment API'nin response schema'sı son deploy sonrası kontrat tanımıyla uyuşmuyor. Breaking change riski var.", severity: "warning", category: "Kontrat", ctaLabel: "Kontratlar", createdAt: ago(35), confidence: 88 },
      { id: "svc3", title: "SQL injection açığı kapatıldı", description: "Güvenlik taraması 2/5 endpoint'te input sanitization eksikliği tespit etti. Patch önerildi ve uygulandı.", severity: "success", category: "Güvenlik", ctaLabel: "Güvenlik raporu", createdAt: ago(180), confidence: 96 },
    ],
    recentActivity: [
      { id: "svca1", ts: ago(6), actor: "API Scanner", verb: "tespit etti", object: "kontrat drift", objectName: "Payment v2 Schema" },
      { id: "svca2", ts: ago(22), actor: "Mert C.", verb: "oluşturdu", object: "chain", objectName: "Order → Payment → Inventory" },
      { id: "svca3", ts: ago(48), actor: "Auto-Heal", verb: "onardı", object: "flaky test", objectName: "User Profile GET" },
      { id: "svca4", ts: ago(95), actor: "Selin T.", verb: "bağladı", object: "mock servis", objectName: "Payment Gateway Stub" },
    ],
    onboarding: [
      { id: "svco1", title: "OpenAPI spec yükle", description: "Swagger veya OpenAPI 3.x dosyanızı yükleyerek endpoint listesini otomatik oluşturun.", done: true, ctaLabel: "API Test" },
      { id: "svco2", title: "İlk API chain kur", description: "Birbirine bağlı API akışlarınızı Chain Builder'da modelleyin.", done: false, ctaLabel: "Chain Builder" },
      { id: "svco3", title: "Güvenlik taraması başlat", description: "OWASP Top 10 kontrollerini API'larınız üzerinde çalıştırın.", done: false, ctaLabel: "Güvenlik" },
      { id: "svco4", title: "Mock servisleri yapılandır", description: "Bağımlı servisleri mock'layarak izole test ortamı oluşturun.", done: false, ctaLabel: "Chain Builder" },
    ],
  },

  web: {
    productId: "web",
    isDemo: true,
    lastUpdated: now,
    stats: [
      { key: "locators", label: "Locator", value: 1847, trend: "up", delta: 124, sparkline: spark(14) },
      { key: "pass_rate", label: "Pass Rate", value: "91.3", unit: "%", delta: -1.2, trend: "down", severity: "warn", sparkline: spark(25) },
      { key: "heal_rate", label: "Self-Heal Oran", value: "88.4", unit: "%", delta: 2.1, trend: "up", sparkline: spark(36) },
      { key: "visual_diffs", label: "Görsel Diff", value: 7, severity: "warn", trend: "up", sparkline: spark(47) },
      { key: "a11y_issues", label: "A11y Uyarı", value: 14, severity: "warn", trend: "down", sparkline: spark(58) },
      { key: "flaky", label: "Flaky Test", value: 9, severity: "warn", trend: "down", sparkline: spark(69) },
    ],
    aiInsights: [
      { id: "w1", title: "7 görsel regresyon tespit edildi", description: "Son deploy sonrası checkout sayfasında button rengi ve spacing değişimi var. 3'ü kritik akışta.", severity: "critical", category: "Görsel", ctaLabel: "Görsel regresyon", createdAt: ago(12), confidence: 97 },
      { id: "w2", title: "Locator sağlık puanı %88 — iyileştirme mümkün", description: "124 locator kırılgan XPath kullanıyor. AI 89'u data-testid bazlı locator'a dönüştürebilir.", severity: "warning", category: "Locator", ctaLabel: "Locator sağlık", createdAt: ago(40), confidence: 85 },
      { id: "w3", title: "Self-healing başarı oranı arttı", description: "Son 7 günde 134 locator otomatik onarıldı. Manuel müdahale %67 azaldı.", severity: "success", category: "Self-Heal", ctaLabel: "Healing raporu", createdAt: ago(120), confidence: 91 },
    ],
    recentActivity: [
      { id: "wa1", ts: ago(4), actor: "AI Recorder", verb: "kaydetti", object: "akış", objectName: "Sepet → Ödeme (47 adım)" },
      { id: "wa2", ts: ago(19), actor: "Self-Heal", verb: "onardı", object: "locator", objectName: "CheckoutButton #btn-checkout" },
      { id: "wa3", ts: ago(38), actor: "Can A.", verb: "çalıştırdı", object: "görsel test", objectName: "Homepage Regression Suite" },
      { id: "wa4", ts: ago(72), actor: "Accessibility Bot", verb: "tespit etti", object: "a11y ihlali", objectName: "Form label eksik — 5 alan" },
    ],
    onboarding: [
      { id: "wo1", title: "İlk akışı kaydet", description: "Browser'da gerçek kullanıcı akışını kaydederek otomasyon tabanı oluşturun.", done: true, ctaLabel: "Recorder" },
      { id: "wo2", title: "Locator analizi çalıştır", description: "Tüm locator'larınızın kırılganlık skorunu görün ve iyileştirin.", done: false, ctaLabel: "Locator'lar" },
      { id: "wo3", title: "Görsel baseline al", description: "Kritik sayfaların görsel referanslarını kaydedin.", done: false, ctaLabel: "Görsel Regresyon" },
      { id: "wo4", title: "A11y taraması başlat", description: "WCAG 2.1 uyumluluk kontrollerini çalıştırın.", done: false, ctaLabel: "Erişilebilirlik" },
    ],
    browsers: [
      { name: "Chrome",        icon: "🌐", version: "124",  passRate: 96, runs: 1204, status: "passing" },
      { name: "Firefox",       icon: "🦊", version: "125",  passRate: 93, runs: 876,  status: "passing" },
      { name: "Safari",        icon: "🍎", version: "17.4", passRate: 88, runs: 543,  status: "warning" },
      { name: "Edge",          icon: "🔷", version: "124",  passRate: 95, runs: 421,  status: "passing" },
      { name: "Mobile Chrome", icon: "📱", version: "124",  passRate: 91, runs: 287,  status: "passing" },
      { name: "Mobile Safari", icon: "📱", version: "17.4", passRate: 84, runs: 198,  status: "warning" },
    ],
  },

  mobile: {
    productId: "mobile",
    isDemo: true,
    lastUpdated: now,
    stats: [
      { key: "devices", label: "Aktif Cihaz", value: 12, trend: "stable", sparkline: spark(15) },
      { key: "running", label: "Koşan Test", value: 3, trend: "up", sparkline: spark(26) },
      { key: "pass_rate", label: "Pass Rate", value: "87.4", unit: "%", delta: -2.1, trend: "down", severity: "warn", sparkline: spark(37) },
      { key: "avg_duration", label: "Ort. Süre", value: "4.2", unit: "dk", trend: "stable", sparkline: spark(48) },
      { key: "ios_pass", label: "iOS Pass", value: "91.2", unit: "%", trend: "up", sparkline: spark(59) },
      { key: "android_pass", label: "Android Pass", value: "83.6", unit: "%", delta: -3.1, trend: "down", sparkline: spark(70) },
    ],
    aiInsights: [
      { id: "m1", title: "3 flaky test — iPhone 13 Mini", description: "'Checkout flow' senaryosu iPhone 13 Mini'de %22 fail oranıyla dikkat çekiyor. Cihaz-spesifik race condition şüphesi var.", severity: "warning", category: "Flaky", ctaLabel: "Detayları gör", createdAt: ago(18), confidence: 88 },
      { id: "m2", title: "Android pass rate düşüşü izleniyor", description: "Galaxy S23 ve A54 serisi son 3 günde %6 düşüş gösterdi. OS güncellemesi sonrası animasyon timing değişimi şüpheli.", severity: "critical", category: "Platform", ctaLabel: "Android raporu", createdAt: ago(35), confidence: 82 },
      { id: "m3", title: "4 yeni mobil senaryo önerisi", description: "Background → foreground geçişi ve push notification permission akışları için senaryo eksik.", severity: "info", category: "Kapsam", ctaLabel: "Senaryolar oluştur", createdAt: ago(90), confidence: 76 },
    ],
    recentActivity: [
      { id: "ma1", ts: ago(2), actor: "Pixel 8", verb: "tamamladı", object: "test koşusu", objectName: "Smoke Suite v2.1" },
      { id: "ma2", ts: ago(14), actor: "Funda K.", verb: "ekledi", object: "cihaz", objectName: "iPhone 15 Pro Max" },
      { id: "ma3", ts: ago(33), actor: "CI Pipeline", verb: "tetikledi", object: "test koşusu", objectName: "Nightly — 47 test" },
      { id: "ma4", ts: ago(67), actor: "AI Agent", verb: "önerdi", object: "senaryo", objectName: "Orientation Change Testi" },
    ],
    onboarding: [
      { id: "mo1", title: "Cihaz matrisi tanımla", description: "Test cihazlarınızı platforma ekleyin ve durumlarını izleyin.", done: true, ctaLabel: "Cihaz Matrisi" },
      { id: "mo2", title: "İlk mobil test koşusunu başlat", description: "Bir senaryo seçip gerçek cihazda çalıştırın.", done: true, ctaLabel: "Koşular" },
      { id: "mo3", title: "Paralel koşu kur", description: "Birden fazla cihazda eş zamanlı test çalıştırın.", done: false, ctaLabel: "Koşular" },
      { id: "mo4", title: "CI pipeline entegrasyonu", description: "Mobile testleri CI/CD akışınıza bağlayın.", done: false, ctaLabel: "CI/CD" },
    ],
  },

  data: {
    productId: "data",
    isDemo: true,
    lastUpdated: now,
    stats: [
      { key: "records", label: "Üretilen Kayıt", value: "2.4M", trend: "up", delta: 340000, sparkline: spark(16) },
      { key: "schemas", label: "Aktif Şema", value: 34, trend: "up", sparkline: spark(27) },
      { key: "pii_masked", label: "PII Maskeleme", value: "99.7", unit: "%", delta: 0.2, trend: "up", sparkline: spark(38) },
      { key: "datasets", label: "Dataset", value: 127, trend: "up", sparkline: spark(49) },
      { key: "quality_score", label: "Kalite Skoru", value: "94.1", unit: "%", trend: "stable", sparkline: spark(50) },
      { key: "compliance", label: "KVKK Uyum", value: "100", unit: "%", severity: "ok", trend: "stable", sparkline: spark(61) },
    ],
    aiInsights: [
      { id: "d1", title: "Kredi kartı numaraları maskelenmemiş", description: "3 dataset'te payment.card_number alanı düz metin olarak kaydedilmiş. KVKK ihlali riski.", severity: "critical", category: "PII/KVKK", ctaLabel: "Gizlilik taraması", createdAt: ago(8), confidence: 97 },
      { id: "d2", title: "Yeni şema anomalisi: users tablosu", description: "users.email alanında %2.3 null değer ve %0.8 format ihlali tespit edildi. Veri kalitesi skoru etkileniyor.", severity: "warning", category: "Kalite", ctaLabel: "Şema görüntüle", createdAt: ago(45), confidence: 84 },
      { id: "d3", title: "2.4M kayıt başarıyla üretildi", description: "Bu ayki sentetik veri üretimi tamamlandı. Tüm şemalar doğrulandı, distribution testleri geçti.", severity: "success", category: "Üretim", ctaLabel: "Dataset raporu", createdAt: ago(180), confidence: 99 },
    ],
    recentActivity: [
      { id: "da1", ts: ago(7), actor: "AI Generator", verb: "üretti", object: "dataset", objectName: "e_commerce_users_v3 (500K kayıt)" },
      { id: "da2", ts: ago(23), actor: "PII Scanner", verb: "tespit etti", object: "gizlilik ihlali", objectName: "payment.card_number — 3 dataset" },
      { id: "da3", ts: ago(52), actor: "Hasan K.", verb: "oluşturdu", object: "şema", objectName: "subscription_events_v2" },
      { id: "da4", ts: ago(88), actor: "Lineage Bot", verb: "güncelledi", object: "veri soyu", objectName: "orders → analytics pipeline" },
    ],
    onboarding: [
      { id: "do1", title: "İlk şemayı tanımla", description: "Veri yapınızı ve alanlarınızı platforma kaydedin.", done: true, ctaLabel: "Sentetik Veri" },
      { id: "do2", title: "PII taraması çalıştır", description: "Mevcut verilerinizde kişisel veri tespiti yapın.", done: true, ctaLabel: "Gizlilik" },
      { id: "do3", title: "İlk sentetik veri üret", description: "Şemanızdan gerçekçi, KVKK uyumlu test verisi üretin.", done: false, ctaLabel: "Sentetik Veri" },
      { id: "do4", title: "Maskeleme kuralları tanımla", description: "Hangi alanların nasıl maskeleneceğini yapılandırın.", done: false, ctaLabel: "Gizlilik" },
    ],
  },

  management: {
    productId: "management",
    isDemo: true,
    lastUpdated: now,
    stats: [
      { key: "cases", label: "Manuel Test Case", value: 341, trend: "up", delta: 24, deltaLabel: "bu hafta", sparkline: spark(19) },
      { key: "active_runs", label: "Aktif Run", value: 9, trend: "stable", sparkline: spark(31) },
      { key: "pass_rate", label: "Pass Rate", value: "88.1", unit: "%", delta: 2.4, trend: "up", sparkline: spark(42) },
      { key: "blocked", label: "Blocked", value: 7, severity: "warn", trend: "down", sparkline: spark(53) },
      { key: "coverage", label: "Req. Coverage", value: "76.5", unit: "%", trend: "up", sparkline: spark(64) },
      { key: "workload", label: "Tester İş Yükü", value: 42, trend: "stable", sparkline: spark(75) },
    ],
    aiInsights: [
      { id: "mg1", title: "Checkout suite coverage düşük", description: "Checkout requirement setinde 11 requirement yalnızca kısmi manuel test coverage'a sahip. Regression planına 8 test case eklenmesi öneriliyor.", severity: "warning", category: "Coverage", ctaLabel: "Coverage matrisi", createdAt: ago(16), confidence: 86 },
      { id: "mg2", title: "7 blocked test release kararını etkiliyor", description: "Blocked testlerin 4'ü ödeme ortamı, 3'ü mobil doğrulama verisi bekliyor. QA Lead aksiyonu önerilir.", severity: "critical", category: "Run Riski", ctaLabel: "Run detayları", createdAt: ago(28), confidence: 91 },
      { id: "mg3", title: "24 yeni manuel test case eklendi", description: "Sprint 12 kapsamında Login ve Customer modüllerine yeni manuel testler eklendi. 19'u ready durumunda.", severity: "success", category: "Repository", ctaLabel: "Repository", createdAt: ago(90), confidence: 93 },
    ],
    recentActivity: [
      { id: "mga1", ts: ago(5), actor: "QA Lead", verb: "oluşturdu", object: "test planı", objectName: "Sprint 12 Regression" },
      { id: "mga2", ts: ago(14), actor: "Ece T.", verb: "koştu", object: "manuel test", objectName: "TC-1042 Checkout ödeme doğrulama" },
      { id: "mga3", ts: ago(34), actor: "Murat K.", verb: "linkledi", object: "defect", objectName: "PAY-381 kart reddi mesajı" },
      { id: "mga4", ts: ago(72), actor: "Import Wizard", verb: "aktardı", object: "test case", objectName: "Login Regression Excel - 46 case" },
    ],
    onboarding: [
      { id: "mgo1", title: "Test repository oluştur", description: "Suite ve folder yapısını kurarak manuel test case havuzunu başlat.", done: true, ctaLabel: "Repository" },
      { id: "mgo2", title: "Excel'den testleri içe aktar", description: "Mevcut manuel test Excel'lerini mapping ekranıyla Management'a taşı.", done: true, ctaLabel: "Import" },
      { id: "mgo3", title: "İlk test planını oluştur", description: "Release veya sprint kapsamındaki testleri plana ekle.", done: false, ctaLabel: "Test Planları" },
      { id: "mgo4", title: "Tester atamalarını yap", description: "Run içindeki test case'leri manual tester'lara dağıt.", done: false, ctaLabel: "Test Runs" },
    ],
  },

  intelligence: {
    productId: "intelligence",
    isDemo: true,
    lastUpdated: now,
    stats: [
      { key: "ai_calls", label: "AI Çağrısı", value: "18.4K", trend: "up", delta: 2100, sparkline: spark(17) },
      { key: "success_rate", label: "Başarı Oranı", value: "97.3", unit: "%", delta: 1.1, trend: "up", sparkline: spark(28) },
      { key: "avg_latency", label: "Ort. Latency", value: "1.2", unit: "s", delta: -0.3, trend: "up", sparkline: spark(39) },
      { key: "scenarios_gen", label: "AI Üretim", value: 247, trend: "up", sparkline: spark(40) },
      { key: "provider_uptime", label: "Provider Uptime", value: "99.6", unit: "%", trend: "stable", sparkline: spark(51) },
      { key: "token_cost", label: "Token Maliyet", value: "$12.4", trend: "stable", sparkline: spark(62) },
    ],
    aiInsights: [
      { id: "i1", title: "Groq provider latency spike — Gemini fallback aktif", description: "Son 45 dakikada Groq P95 latency 2.8s'e çıktı. Otomatik fallback Gemini'ye geçti. %97.3 başarı devam ediyor.", severity: "warning", category: "Provider", ctaLabel: "AI Gateway durumu", createdAt: ago(45), confidence: 93 },
      { id: "i2", title: "247 senaryo AI tarafından üretildi", description: "Bu ay Studio modülüne AI tarafından 247 senaryo gönderildi. 91 onaylandı, 156 incelemede.", severity: "success", category: "Üretim", ctaLabel: "Task Drafts", ctaHref: "/task-drafts", createdAt: ago(120), confidence: 98 },
      { id: "i3", title: "Hallucination uyarısı: 4 senaryo geri çekildi", description: "LLM-as-Judge kontrolü 4 senaryo'da gerçek dışı assertion tespit etti. Otomatik geri çekildi.", severity: "warning", category: "Kalite", ctaLabel: "LLM denetim", createdAt: ago(200), confidence: 86 },
    ],
    recentActivity: [
      { id: "ia1", ts: ago(5), actor: "Groq llama3", verb: "üretim", object: "senaryo paketi", objectName: "E-Ticaret Checkout (15 senaryo)" },
      { id: "ia2", ts: ago(20), actor: "LLM Judge", verb: "doğruladı", object: "senaryo", objectName: "Login Flow — Güvenlik Testi" },
      { id: "ia3", ts: ago(46), actor: "AI Gateway", verb: "fallback uyguladı", object: "provider", objectName: "Groq → Gemini" },
      { id: "ia4", ts: ago(85), actor: "Gemini Flash", verb: "analiz etti", object: "test paketi", objectName: "Sprint 24 Risk Analizi" },
    ],
    onboarding: [
      { id: "io1", title: "AI Gateway'i yapılandır", description: "LLM provider tercihlerinizi ve fallback zincirini ayarlayın.", done: true, ctaLabel: "AI Gateway" },
      { id: "io2", title: "İlk AI senaryo üretimi", description: "Doğal dil açıklamasından test senaryoları oluşturun.", done: true, ctaLabel: "Task Drafts", href: "/task-drafts" },
      { id: "io3", title: "LLM-as-Judge etkinleştir", description: "AI tarafından üretilen içeriği otomatik kalite kontrolünden geçirin.", done: false, ctaLabel: "AI Agents", href: "/ai-agents" },
      { id: "io4", title: "Token bütçesi tanımla", description: "Aylık AI maliyetini kontrol altına almak için limit belirleyin.", done: false, ctaLabel: "Ayarlar" },
    ],
  },

  "nexus-code": {
    productId: "nexus-code",
    isDemo: true,
    lastUpdated: now,
    stats: [
      { key: "analyses", label: "Analiz", value: 89, trend: "up", delta: 12, sparkline: spark(18) },
      { key: "pages_scanned", label: "Sayfa Tarandı", value: 1247, trend: "up", sparkline: spark(29) },
      { key: "bugs_found", label: "Bug Tahmini", value: 342, trend: "up", sparkline: spark(30) },
      { key: "scenarios_gen", label: "Üretilen Senaryo", value: 567, trend: "up", sparkline: spark(41) },
      { key: "privacy_issues", label: "Gizlilik İhlali", value: 8, severity: "warn", trend: "down", sparkline: spark(52) },
      { key: "avg_duration", label: "Analiz Süresi", value: "2.4", unit: "dk", trend: "down", sparkline: spark(63) },
    ],
    aiInsights: [
      { id: "nc1", title: "Ödeme sayfasında 12 kritik bug tahmini", description: "DOM analizi ve kullanıcı akışı verisi, ödeme formunda 12 potansiyel bug noktası tespit etti. En kritik: timeout handling eksikliği.", severity: "critical", category: "Bug Tahmini", ctaLabel: "Analiz aç", ctaHref: "/nexus-code", createdAt: ago(15), confidence: 83 },
      { id: "nc2", title: "Test kapsamı %43 artış gösterdi", description: "Neurex Code analizleri sayesinde daha önce kapsanmayan 89 yeni test senaryosu tespit edildi.", severity: "success", category: "Kapsam", ctaLabel: "Senaryoları gör", createdAt: ago(90), confidence: 91 },
      { id: "nc3", title: "8 gizlilik sızıntısı tespit edildi", description: "3 sayfada kişisel veri URL parametrelerine ekleniyor. KVKK uyum riski.", severity: "warning", category: "Gizlilik", ctaLabel: "Gizlilik taraması", createdAt: ago(210), confidence: 88 },
    ],
    recentActivity: [
      { id: "nca1", ts: ago(9), actor: "Neurex Code", verb: "analiz etti", object: "URL", objectName: "checkout.example.com/payment" },
      { id: "nca2", ts: ago(27), actor: "Neurex Code", verb: "üretti", object: "senaryo paketi", objectName: "HomePage — 34 test" },
      { id: "nca3", ts: ago(54), actor: "Caner M.", verb: "çalıştırdı", object: "analiz", objectName: "GitHub: my-app/src/checkout" },
      { id: "nca4", ts: ago(110), actor: "Privacy Scanner", verb: "tespit etti", object: "gizlilik ihlali", objectName: "URL'de email parametresi" },
    ],
    onboarding: [
      { id: "nco1", title: "İlk URL analizini çalıştır", description: "Analiz etmek istediğiniz web sayfasının URL'ini Neurex Code'a verin.", done: true, ctaLabel: "Neurex Code", href: "/nexus-code" },
      { id: "nco2", title: "Repo analizi yap", description: "GitHub repository URL'ini girerek kod analizi başlatın.", done: false, ctaLabel: "Neurex Code", href: "/nexus-code" },
      { id: "nco3", title: "Üretilen senaryoları incele", description: "AI'ın önerdiği test senaryolarını gözden geçirin ve onaylayın.", done: false, ctaLabel: "Task Drafts", href: "/task-drafts" },
      { id: "nco4", title: "Gizlilik raporunu al", description: "Sayfalarınızdaki kişisel veri sızıntılarını raporlayın.", done: false, ctaLabel: "Neurex Code", href: "/nexus-code" },
    ],
  },
};
