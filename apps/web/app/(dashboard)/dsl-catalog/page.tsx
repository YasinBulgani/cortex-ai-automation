import { DslCatalogView } from "@/components/dsl/DslCatalogView";

export const metadata = {
  title: "DSL Sözlüğü — Neurex QA",
  description: "Tüm test cümlecikleri tek merkezde: ara, filtrele, kopyala.",
};

export default function DslCatalogGlobalPage() {
  return <DslCatalogView title="DSL Sözlüğü" />;
}
