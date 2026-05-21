import { notFound } from "next/navigation";
import { isValidProductFamilyId, type ProductFamilyId } from "@/lib/product";
import { OneProductPage } from "@/components/products/OneProductPage";
import { StudioProductPage } from "@/components/products/StudioProductPage";
import { ServiceProductPage } from "@/components/products/ServiceProductPage";
import { WebProductPage } from "@/components/products/WebProductPage";
import { MobileProductPage } from "@/components/products/MobileProductPage";
import { DataProductPage } from "@/components/products/DataProductPage";
import { IntelligenceProductPage } from "@/components/products/IntelligenceProductPage";
import { NexusCodeProductPage } from "@/components/products/NexusCodeProductPage";

const PAGE_MAP: Record<ProductFamilyId, React.ComponentType> = {
  one:          OneProductPage,
  studio:       StudioProductPage,
  service:      ServiceProductPage,
  web:          WebProductPage,
  mobile:       MobileProductPage,
  data:         DataProductPage,
  intelligence: IntelligenceProductPage,
  "nexus-code": NexusCodeProductPage,
};

export default function ProductPage({ params }: { params: { productId: string } }) {
  if (!isValidProductFamilyId(params.productId)) {
    notFound();
  }

  const productId = params.productId as ProductFamilyId;
  const Component = PAGE_MAP[productId];
  return <Component />;
}
