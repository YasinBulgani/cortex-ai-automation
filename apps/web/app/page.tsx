import Link from "next/link";
import type { Metadata } from "next";

// ── SEO ───────────────────────────────────────────────────────────────────────

export const metadata: Metadata = {
  title: "Cortex AI — Birleşik Kalite Otomasyon Platformu",
  description:
    "Test tasarımı, web & mobil otomasyon, AI destekli senaryo üretimi ve sentetik veri — tek platformda. Cortex AI ile kalite süreçlerinizi modernleştirin.",
  openGraph: {
    title: "Cortex AI — Birleşik Kalite Otomasyon Platformu",
    description: "Test tasarımı, web & mobil otomasyon ve AI — tek platformda.",
    type: "website",
  },
};

// ── Data ──────────────────────────────────────────────────────────────────────

const FEATURES = [
  {
    icon: "🧪",
    title: "Test Yönetimi",
    desc: "Test case'lerini tasarla, organize et ve gereksinimlerle izleyin. Semantic arama ile benzer testleri anında bulun.",
  },
  {
    icon: "🤖",
    title: "Web Otomasyonu",
    desc: "Playwright tabanlı otomasyon. NL komutlarından adım üretin, görsel doğrulama yapın, CI/CD'ye entegre edin.",
  },
  {
    icon: "📱",
    title: "Mobil Otomasyon",
    desc: "iOS ve Android cihazlarda Appium tabanlı testler. AWS Device Farm, BrowserStack, Sauce Labs desteği.",
  },
  {
    icon: "✨",
    title: "AI Destekli Üretim",
    desc: "Doğal dil açıklamalarından test senaryoları oluşturun. Gherkin, Playwright ve Appium adımlarına otomatik dönüştürün.",
  },
  {
    icon: "🔍",
    title: "Semantik Arama",
    desc: "AI embed vektörleriyle benzer test case'lerini anında bulun. Mükerrer testleri önleyin, coverage'ı artırın.",
  },
  {
    icon: "📊",
    title: "Veri & Raporlama",
    desc: "Sentetik test verisi üretin, koşu sonuçlarını analiz edin, kalite metriklerini takip edin.",
  },
];

const INTEGRATIONS = [
  "Jira", "GitHub", "GitLab", "Jenkins", "AWS Device Farm",
  "BrowserStack", "Sauce Labs", "Slack", "OpenAPI/Swagger",
];

const STATS = [
  { value: "10×", label: "Daha hızlı test yazımı" },
  { value: "60%", label: "Daha az bakım maliyeti" },
  { value: "99.9%", label: "CI/CD uptime" },
  { value: "4+", label: "Cloud provider" },
];

// ── Components ────────────────────────────────────────────────────────────────

function NavBar() {
  return (
    <nav className="sticky top-0 z-40 border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600 text-sm font-bold text-white">
            C
          </div>
          <span className="text-lg font-bold text-white">Cortex AI</span>
        </div>
        <div className="hidden items-center gap-6 md:flex">
          <a href="#features" className="text-sm text-slate-400 hover:text-white transition">Özellikler</a>
          <a href="#integrations" className="text-sm text-slate-400 hover:text-white transition">Entegrasyonlar</a>
          <a href="#pricing" className="text-sm text-slate-400 hover:text-white transition">Fiyatlandırma</a>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="text-sm text-slate-400 hover:text-white transition"
          >
            Giriş Yap
          </Link>
          <Link
            href="/onboarding"
            className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 transition"
          >
            Ücretsiz Başla
          </Link>
        </div>
      </div>
    </nav>
  );
}

function HeroSection() {
  return (
    <section className="relative overflow-hidden py-24 md:py-36">
      {/* Gradient blob */}
      <div
        className="pointer-events-none absolute inset-0 flex items-center justify-center"
        aria-hidden="true"
      >
        <div className="h-[600px] w-[900px] rounded-full bg-violet-600/10 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-4xl px-6 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-violet-500/20 bg-violet-500/5 px-4 py-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-violet-400" />
          <span className="text-xs font-semibold text-violet-300 uppercase tracking-wide">
            AI Destekli Kalite Platformu
          </span>
        </div>

        <h1 className="mb-6 text-5xl font-extrabold leading-tight tracking-tight text-white md:text-6xl lg:text-7xl">
          Test Operasyonlarını{" "}
          <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
            Yeniden Tanımlayın
          </span>
        </h1>

        <p className="mx-auto mb-10 max-w-2xl text-lg leading-relaxed text-slate-400">
          Test tasarımı, web & mobil otomasyon, AI destekli senaryo üretimi ve sentetik veri yönetimini
          tek bir entegre platformda birleştirin. Manuel iş yükünü azaltın, kaliteyi artırın.
        </p>

        <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <Link
            href="/onboarding"
            className="w-full rounded-xl bg-violet-600 px-8 py-3.5 text-base font-semibold text-white hover:bg-violet-500 transition sm:w-auto"
          >
            Ücretsiz Başla →
          </Link>
          <Link
            href="/login"
            className="w-full rounded-xl border border-slate-700 px-8 py-3.5 text-base font-semibold text-slate-300 hover:bg-slate-800 transition sm:w-auto"
          >
            Demo Talep Et
          </Link>
        </div>

        <p className="mt-4 text-xs text-slate-600">Kredi kartı gerekmez · 14 gün ücretsiz</p>
      </div>
    </section>
  );
}

function StatsRow() {
  return (
    <section className="border-y border-slate-800 bg-slate-900/50 py-12">
      <div className="mx-auto max-w-5xl px-6">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-3xl font-extrabold text-white">{s.value}</p>
              <p className="mt-1 text-sm text-slate-400">{s.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FeaturesSection() {
  return (
    <section id="features" className="py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div className="mb-14 text-center">
          <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-violet-400">
            Platform Yetenekleri
          </p>
          <h2 className="text-4xl font-bold text-white">
            Kalite süreçlerinizin her adımı
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-slate-400">
            Test planlamasından otomasyona, CI/CD entegrasyonundan raporlamaya kadar ihtiyacınız olan her şey tek çatı altında.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="group rounded-2xl border border-slate-800 bg-slate-900 p-6 hover:border-violet-500/40 transition"
            >
              <div className="mb-4 text-4xl">{f.icon}</div>
              <h3 className="mb-2 text-base font-semibold text-white">{f.title}</h3>
              <p className="text-sm leading-relaxed text-slate-400">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function IntegrationsSection() {
  return (
    <section id="integrations" className="border-t border-slate-800 py-20">
      <div className="mx-auto max-w-4xl px-6 text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-violet-400">
          Entegrasyonlar
        </p>
        <h2 className="mb-4 text-3xl font-bold text-white">
          Mevcut araçlarınızla mükemmel uyum
        </h2>
        <p className="mb-12 text-slate-400">
          Halihazırda kullandığınız araçlara bağlanın — günler içinde değil, dakikalar içinde.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {INTEGRATIONS.map((name) => (
            <span
              key={name}
              className="rounded-full border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium text-slate-300"
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function PricingSection() {
  const plans = [
    {
      name: "Starter",
      price: "Ücretsiz",
      sub: "Sonsuza kadar",
      features: [
        "3 proje",
        "500 test case",
        "Web otomasyonu",
        "Temel raporlama",
        "Community destek",
      ],
      cta: "Hemen Başla",
      ctaHref: "/onboarding",
      highlight: false,
    },
    {
      name: "Pro",
      price: "₺990",
      sub: "/ ay · kullanıcı başına",
      features: [
        "Sınırsız proje",
        "Sınırsız test case",
        "Mobil otomasyon",
        "AI senaryo üretimi",
        "BrowserStack / Sauce Labs",
        "Semantic arama",
        "E-posta desteği",
      ],
      cta: "Pro Başla",
      ctaHref: "/onboarding",
      highlight: true,
    },
    {
      name: "Enterprise",
      price: "Özel Fiyat",
      sub: "Büyük ekipler için",
      features: [
        "Tüm Pro özellikler",
        "SSO / SAML",
        "On-premise deployment",
        "SLA garantisi",
        "Dedicated CSM",
        "Özel entegrasyonlar",
      ],
      cta: "İletişime Geç",
      ctaHref: "mailto:sales@cortexai.io",
      highlight: false,
    },
  ];

  return (
    <section id="pricing" className="border-t border-slate-800 py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div className="mb-14 text-center">
          <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-violet-400">
            Fiyatlandırma
          </p>
          <h2 className="text-4xl font-bold text-white">Şeffaf, öngörülebilir fiyatlar</h2>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {plans.map((p) => (
            <div
              key={p.name}
              className={`flex flex-col rounded-2xl border p-8 ${
                p.highlight
                  ? "border-violet-500/60 bg-violet-600/10"
                  : "border-slate-800 bg-slate-900"
              }`}
            >
              {p.highlight && (
                <div className="mb-4 inline-block self-start rounded-full bg-violet-600 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-white">
                  Önerilen
                </div>
              )}
              <h3 className="mb-1 text-lg font-bold text-white">{p.name}</h3>
              <p className="mb-1 text-3xl font-extrabold text-white">{p.price}</p>
              <p className="mb-6 text-xs text-slate-500">{p.sub}</p>
              <ul className="mb-8 flex-1 space-y-2">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="mt-0.5 text-emerald-400 flex-shrink-0">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <a
                href={p.ctaHref}
                className={`block w-full rounded-xl py-3 text-center text-sm font-semibold transition ${
                  p.highlight
                    ? "bg-violet-600 text-white hover:bg-violet-500"
                    : "border border-slate-700 text-white hover:bg-slate-800"
                }`}
              >
                {p.cta}
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CtaSection() {
  return (
    <section className="border-t border-slate-800 py-24">
      <div className="mx-auto max-w-3xl px-6 text-center">
        <div className="mb-6 text-5xl">🚀</div>
        <h2 className="mb-4 text-4xl font-extrabold text-white">
          Bugün başlayın
        </h2>
        <p className="mb-8 text-slate-400">
          14 günlük ücretsiz deneme. Kredi kartı gerekmez. Kurulum 5 dakika.
        </p>
        <Link
          href="/onboarding"
          className="inline-block rounded-xl bg-violet-600 px-10 py-4 text-base font-bold text-white hover:bg-violet-500 transition"
        >
          Ücretsiz Hesap Oluştur →
        </Link>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-slate-800 bg-slate-950 py-12">
      <div className="mx-auto max-w-6xl px-6">
        <div className="grid gap-8 md:grid-cols-4">
          <div>
            <div className="mb-3 flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-600 text-xs font-bold text-white">
                C
              </div>
              <span className="font-bold text-white">Cortex AI</span>
            </div>
            <p className="text-xs leading-relaxed text-slate-500">
              Birleşik kalite otomasyon platformu. Test operasyonlarınızı modernleştirin.
            </p>
          </div>
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Platform</p>
            <ul className="space-y-2 text-sm text-slate-500">
              <li><a href="#features" className="hover:text-white transition">Özellikler</a></li>
              <li><a href="#integrations" className="hover:text-white transition">Entegrasyonlar</a></li>
              <li><a href="#pricing" className="hover:text-white transition">Fiyatlandırma</a></li>
            </ul>
          </div>
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Şirket</p>
            <ul className="space-y-2 text-sm text-slate-500">
              <li><a href="/status" className="hover:text-white transition">Sistem Durumu</a></li>
              <li><a href="/privacy" className="hover:text-white transition">Gizlilik Politikası</a></li>
              <li><a href="/terms" className="hover:text-white transition">Kullanım Koşulları</a></li>
            </ul>
          </div>
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Hesap</p>
            <ul className="space-y-2 text-sm text-slate-500">
              <li><Link href="/login" className="hover:text-white transition">Giriş Yap</Link></li>
              <li><Link href="/onboarding" className="hover:text-white transition">Kayıt Ol</Link></li>
            </ul>
          </div>
        </div>
        <div className="mt-10 border-t border-slate-800 pt-6 text-center text-xs text-slate-600">
          © {new Date().getFullYear()} Cortex AI. Tüm hakları saklıdır.
        </div>
      </div>
    </footer>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <NavBar />
      <main>
        <HeroSection />
        <StatsRow />
        <FeaturesSection />
        <IntegrationsSection />
        <PricingSection />
        <CtaSection />
      </main>
      <Footer />
    </div>
  );
}
