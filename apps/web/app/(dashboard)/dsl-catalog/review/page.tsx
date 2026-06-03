import { DslProposalReview } from "@/components/dsl/DslProposalReview";

export const metadata = {
  title: "DSL Öneri İnceleme — Neurex",
  description: "Pending DSL düzenleme önerilerini onayla veya reddet.",
};

export default function DslReviewPage() {
  return <DslProposalReview />;
}
