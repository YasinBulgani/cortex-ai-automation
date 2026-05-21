import type { ProductPackage } from "@neurex/product-kit";

export const manifest: ProductPackage["manifest"] = {
  id: "intelligence",
  name: "Neurex Intelligence",
  shortName: "Intelligence",
  tagline: "Yatay AI kalite katmanı",
  description: "AI sohbeti, orkestrasyon, öneriler, doğal dilden test üretimi ve kalite metrikleri katmanı.",
  availability: "embedded",
  defaultEntryKey: "scenarios",
  routeKeys: [
    "project-overview",
    "requirements", "analysis", "sifir-bilgi", "wizard",
    "ai-chat", "nl-test-gen", "qa-orchestrator", "ai-metrics",
  ],
};

export const landing: ProductPackage["landing"] = {
  eyebrow: "Neurex AI Karar Katmanı",
  headline: "LLM görünürlüğü ile başla, aksiyonu aynı sayfadan yürüt",
  summary: "QA Lead için ilk değer noktası sohbet değil görünürlüktür. Bu sayfa LLM metrikleri, önerilen projeler ve aksiyon modüllerini tek kararda birleştirir.",
  primaryOutcome: "İlk 5 dakikada LLM metrik görünürlüğü sağla",
  startRouteKey: "scenarios",
  projectKeywords: ["ai", "llm", "quality", "kalite", "orchestrator", "metric", "metrik", "test"],
};

const productPackage: ProductPackage = { manifest, landing };
export default productPackage;
