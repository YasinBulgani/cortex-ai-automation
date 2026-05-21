import type { Metadata, Viewport } from "next";
import { QueryProvider } from "@/lib/query-provider";
import { PLATFORM_BRAND, PRODUCT_NAME } from "@/lib/product";
import "./globals.css";

export const metadata: Metadata = {
  title: `${PLATFORM_BRAND.name} | ${PRODUCT_NAME}`,
  description:
    `${PLATFORM_BRAND.name}; test tasarımı, servis kalitesi, web otomasyonu, mobil kalite ve sentetik veri akışlarını ${PRODUCT_NAME} üzerinden birleştiren birleşik kalite platformu.`,
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
