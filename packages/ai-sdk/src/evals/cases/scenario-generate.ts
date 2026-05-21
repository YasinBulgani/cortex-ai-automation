/**
 * Eval cases — scenario.generate-bdd promptu için.
 * Modelden bağımsız beklenti: output minimum kalite eşiği geçer.
 */

import { renderPrompt } from "../../prompts/registry";
import { generateBddScenario } from "../../prompts/library";
import type { EvalCase } from "../types";

export const scenarioGenerateBddCases: EvalCase[] = [
  {
    id: "scenario.generate-bdd.happy-login",
    description: "Login akışı için 3 senaryo üretir, Gherkin formatında",
    prompt_ref: { id: generateBddScenario.id, version: generateBddScenario.version },
    tags: ["scenario", "happy-path"],
    messages: [
      {
        role: "user",
        content: renderPrompt(generateBddScenario, {
          project_name: "Banka Müşteri Portalı",
          domain_context: "Şube-bağımsız bireysel müşteri girişi",
          requirement: "Kullanıcı, 3 yanlış şifre denemesinde 15 dk için kilitlenir.",
        }),
      },
    ],
    assertions: [
      { type: "min_length", length: 200 },
      { type: "contains", value: "Given", case_insensitive: true },
      { type: "contains", value: "When", case_insensitive: true },
      { type: "contains", value: "Then", case_insensitive: true },
      // PII'lik şüphesi yok beklenir
      { type: "not_contains", value: "TR12345678901" },
      { type: "max_latency_ms", limit: 20_000 },
    ],
  },
  {
    id: "scenario.generate-bdd.transfer-limits",
    description: "Para transfer limitleri akışı",
    prompt_ref: { id: generateBddScenario.id, version: generateBddScenario.version },
    tags: ["scenario", "edge-case"],
    messages: [
      {
        role: "user",
        content: renderPrompt(generateBddScenario, {
          project_name: "Mobil Bankacılık",
          domain_context: "EFT/HAVALE limit yönetimi",
          requirement: "Günlük limit 50.000 TL. Üzerine çıkan transfer reddedilir.",
        }),
      },
    ],
    assertions: [
      { type: "min_length", length: 200 },
      { type: "contains", value: "Given", case_insensitive: true },
      { type: "matches", pattern: "(limit|tutar)", flags: "i" },
    ],
  },
];
