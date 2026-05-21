/** @type {import('@lhci/cli').LighthouseRcConfig} */
module.exports = {
  ci: {
    collect: {
      // Statik olarak doğrulanabilen sayfalar — backend gerektirmez
      url: [
        "http://localhost:3000/login",
      ],
      numberOfRuns: 2,
      settings: {
        // Ağ simülasyonu: kullanıcıların gerçek koşulları
        throttling: {
          rttMs: 40,
          throughputKbps: 10_240,
          cpuSlowdownMultiplier: 1,
        },
        // CI'de headless Chromium
        chromeFlags: "--no-sandbox --disable-dev-shm-usage",
      },
    },
    assert: {
      // Skor eşikleri — 0–1 arası (0.8 = 80)
      assertions: {
        "categories:performance": ["warn", { minScore: 0.7 }],
        "categories:accessibility": ["error", { minScore: 0.85 }],
        "categories:best-practices": ["warn", { minScore: 0.8 }],
        "categories:seo": ["warn", { minScore: 0.75 }],

        // Core Web Vitals
        "first-contentful-paint": ["warn", { maxNumericValue: 2500 }],
        "largest-contentful-paint": ["warn", { maxNumericValue: 4000 }],
        "total-blocking-time": ["warn", { maxNumericValue: 600 }],
        "cumulative-layout-shift": ["warn", { maxNumericValue: 0.15 }],

        // Hard fail koşulları — bunlar kırılırsa build durur
        "is-on-https": "off",
        "uses-http2": "off",
        "render-blocking-resources": "off",
      },
    },
    upload: {
      // CI ortamında geçici depo (ücretsiz); kalıcı analiz için
      // LHCI_TOKEN secret'ı eklenip "lhci.server" kullanılabilir
      target: "temporary-public-storage",
    },
  },
};
