/**
 * New Project Wizard — Helper Functions (pure, no JSX)
 */

import {
  actionNeedsLocator,
  type ScenarioMappingReport,
  type StepMapping,
} from "./types";

export function slugifyProjectName(name: string): string {
  const trimmed = (name || "").trim().toLowerCase();
  if (!trimmed) return "proje";
  const map: Record<string, string> = { ç: "c", ğ: "g", ı: "i", ö: "o", ş: "s", ü: "u" };
  return trimmed
    .split("")
    .map((ch) => map[ch] ?? ch)
    .join("")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 40) || "proje";
}

export function maviyakaStepLine(step: StepMapping, url: string): string {
  const lk = step.locator_key || "Element";
  const val = step.data_value ?? "";
  switch (step.action) {
    case "open":   return `    Given I open the application url "${url}"`;
    case "click":  return `    When I click on "${lk}"`;
    case "input":  return `    When I enter "${val || "+-value"}" into the input "${lk}"`;
    case "clear":  return `    When I clear the input "${lk}"`;
    case "wait":   return `    When I wait for element "${lk}" to be clickable`;
    case "verify": return `    Then I verify element "${lk}" text is "${val}"`;
    case "see":
    default:       return `    Then I see the element "${lk}"`;
  }
}

export function buildFeatureFromMapping(
  title: string,
  mapping: ScenarioMappingReport,
  url: string,
): string {
  const lines: string[] = [`Feature: ${title}`, "", `  Scenario: ${title}`];
  for (const step of mapping.steps) {
    if (step.xpath) {
      const q = step.xpath_quality;
      const tag =
        q ? ` · ${q.grade}${typeof q.score === "number" ? ` (${q.score}/100)` : ""}` : "";
      lines.push(`    # xpath=${step.xpath}${tag}`);
    }
    if (actionNeedsLocator(step.action) && !step.locator_key) {
      lines.push(
        `    # TODO: locator eşleşmedi — Step 7'deki 'AI öner' ile bu adıma locator ata`,
      );
    }
    lines.push(maviyakaStepLine(step, url));
  }
  return lines.join("\n") + "\n";
}

export function buildXPathReportMd(
  mappings: ScenarioMappingReport[],
  url: string,
  environment: string,
): string {
  const lines: string[] = [
    "# Adım → Locator → XPath Eşleşme Raporu",
    "",
    `- **URL**: ${url || "-"}`,
    `- **Ortam**: ${environment.toUpperCase()}`,
    `- **Senaryo sayısı**: ${mappings.length}`,
    "",
    "> Bu dosya Step 7'deki LLM + kural bazlı eşleştirmenin çıktısıdır.",
    "> Kırmızı (missing) satırlar için Step 7'ye dönüp 'AI öner' ile locator atayabilirsin.",
    "",
  ];
  mappings.forEach((m, mi) => {
    lines.push(`## ${mi + 1}. ${m.scenario_title}`);
    lines.push(`_LLM kullanıldı:_ **${m.llm_used ? "evet" : "hayır"}**`);
    if (m.error) lines.push(`\n> ⚠️ ${m.error}`);
    lines.push("");
    lines.push("| # | Adım | Aksiyon | Locator Key | XPath | Kalite |");
    lines.push("|---:|------|:-------:|-------------|-------|:------:|");
    m.steps.forEach((s) => {
      const needs = actionNeedsLocator(s.action);
      const key = s.locator_key
        ? `\`${s.locator_key}\``
        : needs
        ? "❌ yok"
        : "—";
      const xpath = s.xpath ? `\`${s.xpath.replace(/\|/g, "\\|")}\`` : "—";
      const q = s.xpath_quality;
      const quality = q
        ? `${q.grade === "good" ? "🟢" : q.grade === "warn" ? "🟡" : "🔴"} ${q.score}/100`
        : "—";
      const idxLabel = s.idx < 0 ? "auto" : String(s.idx + 1);
      const original = (s.original || "").replace(/\|/g, "\\|").slice(0, 80);
      lines.push(
        `| ${idxLabel} | ${original} | ${s.action} | ${key} | ${xpath} | ${quality} |`,
      );
    });
    lines.push("");
  });
  return lines.join("\n");
}
