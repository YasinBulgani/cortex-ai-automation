import type { ProductPackage } from "@neurex/product-kit";

export const manifest: ProductPackage["manifest"] = {
  id: "data",
  name: "Neurex Data",
  shortName: "Data",
  tagline: "Sentetik veri ve privacy",
  description: "Sentetik üretim, test verisi bağlama, maskeleme, gizlilik denetimi ve veri doğruluğu yüzeyi.",
  availability: "active",
  defaultEntryKey: "synthetic",
  routeKeys: [
    "project-overview",
    "requirements", "analysis", "sifir-bilgi", "wizard",
    "synthetic", "test-data", "privacy",
    "ai-chat", "nl-test-gen", "qa-orchestrator", "ai-metrics",
  ],
};

export const landing: ProductPackage["landing"] = {
  eyebrow: "Veri ve Gizlilik",
  headline: "Test verisini üret, bağla ve güvenli tut",
  summary: "Sentetik veri, privacy ve test verisi yönetimini ürün bağlamına göre odaklı başlat.",
  primaryOutcome: "Veri ve privacy hattını doğru projede aç",
  startRouteKey: "synthetic",
  projectKeywords: ["data", "veri", "privacy", "synthetic", "mask", "kvkk"],
};

const productPackage: ProductPackage = { manifest, landing };
export default productPackage;
