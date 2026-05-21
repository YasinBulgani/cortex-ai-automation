/**
 * AI üretimi testler için metadata yardımcıları.
 *
 * Her AI üretimi test dosyasının başına eklenen metadata etiketlerini yönetir.
 */

export const AI_TAG = "@generated-by: ai-test-generator" as const;

export type ReviewStatus = "pending" | "approved" | "rejected";

export interface AITestMetadata {
  generatedBy: string;
  generatedDate: string;
  requirement: string;
  reviewStatus: ReviewStatus;
  model: string;
}

export function createMetadata(
  requirement: string,
  model: string = "gpt-4o",
): AITestMetadata {
  return {
    generatedBy: "ai-test-generator",
    generatedDate: new Date().toISOString().split("T")[0],
    requirement,
    reviewStatus: "pending",
    model,
  };
}

export function metadataToComment(meta: AITestMetadata): string {
  return [
    `// ${AI_TAG}`,
    `// @generated-date: ${meta.generatedDate}`,
    `// @requirement: ${meta.requirement}`,
    `// @review-status: ${meta.reviewStatus}`,
    `// @model: ${meta.model}`,
  ].join("\n");
}
