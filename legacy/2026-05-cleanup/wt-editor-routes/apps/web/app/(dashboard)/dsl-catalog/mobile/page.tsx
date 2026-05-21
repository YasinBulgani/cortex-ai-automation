import { DslCatalogView } from "@/components/dsl/DslCatalogView";

export const metadata = {
  title: "Mobil DSL — BGTS",
  description:
    "Android + iOS (Playwright emulation) mobil test cümlecikleri kataloğu.",
};

export default function MobileDslCatalogPage() {
  return <DslCatalogView title="Mobil DSL" forceCategory="mobile" />;
}
