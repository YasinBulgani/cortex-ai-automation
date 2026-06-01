import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { QueryProvider } from "@/lib/query-provider";
import { PLATFORM_BRAND, PRODUCT_NAME } from "@/lib/product";
import AuthBootstrap from "@/components/AuthBootstrap";
import { PWARegister } from "@/components/PWARegister";
import { I18nProvider } from "@/lib/i18n";
import { CookieConsentBanner } from "@/components/CookieConsentBanner";
import "./globals.css";

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  display: "swap",
  variable: "--font-sans-loaded",
  weight: ["400", "500", "600", "700", "800"],
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono-loaded",
  weight: ["400", "500", "700"],
});

export const metadata: Metadata = {
  title: `${PLATFORM_BRAND.name} | ${PRODUCT_NAME}`,
  description:
    `${PLATFORM_BRAND.name}; test tasarımı, servis kalitesi, web otomasyonu, mobil kalite ve sentetik veri akışlarını ${PRODUCT_NAME} üzerinden birleştiren birleşik kalite platformu.`,
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    title: PLATFORM_BRAND.name,
    statusBarStyle: "black-translucent",
  },
  icons: {
    icon: [
      { url: "/icon-192.svg", type: "image/svg+xml", sizes: "192x192" },
      { url: "/icon-512.svg", type: "image/svg+xml", sizes: "512x512" },
    ],
    apple: "/icon-512.svg",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)",  color: "#0c0e14" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" className={`dark ${inter.variable} ${jetbrains.variable}`} suppressHydrationWarning>
      <body className="font-sans antialiased">
        <AuthBootstrap />
        <PWARegister />
        <I18nProvider>
          <QueryProvider>{children}</QueryProvider>
        </I18nProvider>
        <CookieConsentBanner />
      </body>
    </html>
  );
}
