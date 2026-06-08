/** @type {import('next').NextConfig} */
const rawApiProxyTarget = process.env.NEXT_PUBLIC_API_BASE;
const apiProxyTarget =
  rawApiProxyTarget === undefined ? "http://127.0.0.1:8000" : rawApiProxyTarget.replace(/\/$/, "");

const backendTarget = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";
const devAssetPrefix =
  process.env.NODE_ENV === "production"
    ? ""
    : `/__next_dev_assets_${process.env.NEXT_DEV_ASSET_VERSION || Date.now().toString(36)}`;

const nextConfig = {
  reactStrictMode: true,

  assetPrefix: devAssetPrefix,

  // ── Performans: X-Powered-By header'ını kaldır (güvenlik + boyut) ──
  poweredByHeader: false,

  // ── Performans: Gzip/Brotli sıkıştırma ─────────────────────────────
  compress: true,

  env: {
    NEXT_PUBLIC_APP_NAME: "Neurex QA",
    NEXT_PUBLIC_APP_VERSION: "1.0.0",
  },

  // ── Performans: Ağır paketlerin tree-shaking'ini zorla ─────────────
  // Bu sayede yalnızca kullanılan ikonlar/bileşenler bundle'a girer.
  experimental: {
    optimizePackageImports: [
      "lucide-react",
      "framer-motion",
      "recharts",
      "@radix-ui/react-dialog",
      "@radix-ui/react-popover",
      "@radix-ui/react-select",
      "@radix-ui/react-tabs",
      "@radix-ui/react-tooltip",
      "@radix-ui/react-slot",
      "@tanstack/react-query",
      "@tanstack/react-virtual",
      "@dnd-kit/core",
      "@dnd-kit/sortable",
    ],
  },

  // ── Güvenlik + Performans: HTTP headers ────────────────────────────────
  async headers() {
    return [
      {
        // Güvenlik header'ları — tüm route'lara uygulanır
        source: "/(.*)",
        headers: [
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline'", // Next.js için gerekli
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob: https:",
              "font-src 'self'",
              "connect-src 'self' https: wss:",
              "frame-ancestors 'none'",
            ].join("; "),
          },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
      {
        // Next.js'in ürettiği statik dosyalar (/_next/static/*)
        // PROD: dosya adları content-hash'li → 1 yıl immutable cache güvenli.
        // DEV: chunk adları sabit (hash yok) → immutable cache HMR'ı kırar,
        //      tarayıcı kod değişiminden sonra eski chunk'ı sunup hydration
        //      mismatch'e yol açar. Bu yüzden dev'de cache kapatılır.
        source: "/_next/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value:
              process.env.NODE_ENV === "production"
                ? "public, max-age=31536000, immutable"
                : "no-store, must-revalidate",
          },
        ],
      },
      {
        // Public klasöründeki statik varlıklar (favicon, images, icons)
        source: "/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=86400, stale-while-revalidate=3600",
          },
        ],
      },
    ];
  },

  async rewrites() {
    // Proxy /api/v1/* to the backend so cookies stay on the same origin.
    // Uses API_PROXY_TARGET (server-only) when NEXT_PUBLIC_API_BASE is blank,
    // or NEXT_PUBLIC_API_BASE when set explicitly.
    const target = apiProxyTarget || backendTarget;

    return [
      ...(devAssetPrefix
        ? [
            {
              source: "/:devAsset(__next_dev_assets_[^/]+)/_next/static/:path*",
              destination: "/_next/static/:path*",
            },
          ]
        : []),
      {
        source: "/api/v1/:path*",
        destination: `${target}/api/v1/:path*`,
      },
      {
        // Jira entegrasyonu — /api/jira/* backend'e proxy'lenir
        source: "/api/jira/:path*",
        destination: `${target}/api/jira/:path*`,
      },
    ];
  },
};

// Sentry source map upload — sadece SENTRY_DSN varsa ve paket kuruluysa aktif
let withSentryConfig;
let hasSentry = false;
try {
  if (process.env.SENTRY_DSN) {
    const sentryModule = await import("@sentry/nextjs");
    withSentryConfig = sentryModule.withSentryConfig;
    hasSentry = true;
  }
} catch {
  // @sentry/nextjs kurulu degil — Sentry devre disi
}

export default hasSentry
  ? withSentryConfig(nextConfig, {
      // Sentry organizasyon / proje
      org: process.env.SENTRY_ORG || "bgts",
      project: process.env.SENTRY_PROJECT || "nexus-qa-web",
      authToken: process.env.SENTRY_AUTH_TOKEN,

      // CI'da source map'leri gizle
      silent: process.env.CI === "true",

      // Prod build'de source map'leri gizle
      hideSourceMaps: true,

      // Performans izleme için route'ları otomatik wrap et
      widenClientFileUpload: true,
      autoInstrumentServerFunctions: true,
    })
  : nextConfig;
