import { DslProposalReview } from "@/components/dsl/DslProposalReview";

export const metadata = {
  title: "DSL Öneri İnceleme — TestwrightAI",
  description: "Pending DSL düzenleme önerilerini onayla veya reddet.",
};

export default function DslReviewPage() {
  return <DslProposalReview />;
}
