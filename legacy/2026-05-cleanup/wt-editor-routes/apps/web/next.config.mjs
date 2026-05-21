/** @type {import('next').NextConfig} */
const rawApiProxyTarget = process.env.NEXT_PUBLIC_API_BASE;
const apiProxyTarget =
  rawApiProxyTarget === undefined ? "http://127.0.0.1:8000" : rawApiProxyTarget.replace(/\/$/, "");

const backendTarget = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_APP_NAME: "Nexus QA",
    NEXT_PUBLIC_APP_VERSION: "1.0.0",
  },
  async rewrites() {
    // Proxy /api/v1/* to the backend so cookies stay on the same origin.
    // Uses API_PROXY_TARGET (server-only) when NEXT_PUBLIC_API_BASE is blank,
    // or NEXT_PUBLIC_API_BASE when set explicitly.
    const target = apiProxyTarget || backendTarget;

    return [
      {
        source: "/api/v1/:path*",
        destination: `${target}/api/v1/:path*`,
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
