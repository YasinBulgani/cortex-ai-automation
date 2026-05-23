#!/usr/bin/env node
/**
 * qa/tools/ai-suggest.mjs
 *
 * LLM-assisted test case draft generator. Reads a requirement (or freeform brief)
 * and produces N draft TC markdown files in qa/cases/<suite>/_draft/.
 *
 * Drafts MUST be human-reviewed before promotion to active TCs via:
 *   node qa/tools/tc-promote.mjs <draft-id>  (PR 4+)
 *
 * Provider resolution (in order):
 *   1. CORTEX_AI_GATEWAY_URL  → Cortex's own AI gateway (preferred, dogfood)
 *   2. ANTHROPIC_API_KEY      → Anthropic API direct
 *   3. OPENAI_API_KEY         → OpenAI API direct
 *   4. (none)                 → writes prompt-only file, prints instructions
 *
 * Cost rails:
 *   - Hard cap: --max-cases (default 5)
 *   - Per-invocation budget tracker: qa/.ai-budget.json (warns at $1/day, blocks at $5/day)
 *   - Dry-run mode: --dry-run (prints prompt, no LLM call)
 *
 * Usage:
 *   node qa/tools/ai-suggest.mjs --requirement=REQ-AUTH-005 --suite=auth
 *   node qa/tools/ai-suggest.mjs --brief="Test the new MFA flow" --suite=auth --max-cases=3
 *   node qa/tools/ai-suggest.mjs --requirement=REQ-AUTH-005 --suite=auth --dry-run
 */

import { mkdir, readFile, writeFile, stat } from "node:fs/promises";
import path from "node:path";
import { parseArgs } from "node:util";

import { QA_ROOT, loadAllRequirements, loadAllTestCases } from "./lib/files.mjs";
import { domainForSuite, isValidDomain } from "./lib/domains.mjs";
import { nextSequence, slugify } from "./lib/ids.mjs";

const { values: args } = parseArgs({
  options: {
    requirement: { type: "string" },
    brief: { type: "string" },
    suite: { type: "string" },
    "max-cases": { type: "string", default: "5" },
    "dry-run": { type: "boolean", default: false },
    model: { type: "string" },
    "save-prompt": { type: "boolean", default: false },
  },
});

if (!args.suite) {
  console.error("--suite is required");
  process.exit(2);
}
if (!args.requirement && !args.brief) {
  console.error("Provide either --requirement=REQ-... or --brief=\"...\"");
  process.exit(2);
}

const maxCases = Math.min(10, Math.max(1, parseInt(args["max-cases"], 10) || 5));
const suite = args.suite;
const domain = domainForSuite(suite);
if (!domain || !isValidDomain(domain)) {
  console.error(`Unknown suite '${suite}'. Map it in qa/tools/lib/domains.mjs.`);
  process.exit(2);
}

let briefText = args.brief;
let sourceLabel = "freeform brief";

if (args.requirement) {
  const reqs = await loadAllRequirements();
  const found = reqs.find((r) => r.data?.id === args.requirement);
  if (!found) {
    console.error(`Requirement not found: ${args.requirement}`);
    process.exit(2);
  }
  const rawReq = await readFile(found.file, "utf8");
  briefText = rawReq;
  sourceLabel = args.requirement;
}

const existingTcs = await loadAllTestCases();
const existingIds = existingTcs.map((t) => t.data?.id).filter(Boolean);
const existingTitles = existingTcs
  .filter((t) => t.data?.suite === suite)
  .map((t) => t.data.title);

const prompt = buildPrompt({
  suite,
  domain,
  briefText,
  sourceLabel,
  maxCases,
  existingTitles,
});

if (args["save-prompt"] || args["dry-run"]) {
  const promptPath = path.join(QA_ROOT, "cases", suite, "_draft", `_prompt-${Date.now()}.md`);
  await mkdir(path.dirname(promptPath), { recursive: true });
  await writeFile(promptPath, prompt, "utf8");
  console.log(`✓ Prompt saved to ${promptPath}`);
  if (args["dry-run"]) {
    console.log("\n--- DRY RUN: prompt below ---\n");
    console.log(prompt);
    process.exit(0);
  }
}

const provider = resolveProvider();
console.log(`Provider: ${provider.name}`);
console.log(`Model: ${args.model || provider.defaultModel}`);
console.log(`Max cases: ${maxCases}`);
console.log(`Source: ${sourceLabel}`);
console.log("");

const budgetOk = await checkBudget();
if (!budgetOk) {
  console.error("Daily AI budget exceeded ($5). Reset in qa/.ai-budget.json or wait.");
  process.exit(1);
}

let responseText;
try {
  responseText = await provider.call(prompt, args.model || provider.defaultModel);
} catch (err) {
  console.error(`LLM call failed: ${err.message}`);
  console.error("Falling back to prompt-only output.");
  const fallback = path.join(QA_ROOT, "cases", suite, "_draft", `_prompt-fallback-${Date.now()}.md`);
  await mkdir(path.dirname(fallback), { recursive: true });
  await writeFile(fallback, prompt, "utf8");
  console.error(`Prompt saved to ${fallback}. Run manually against your LLM, save responses to _draft/.`);
  process.exit(1);
}

await recordBudgetTick(provider.estimateCostUsd(prompt, responseText));

const drafts = parseLlmResponse(responseText, { suite, domain, existingIds });
console.log(`Parsed ${drafts.length} draft(s) from LLM response.`);

const draftDir = path.join(QA_ROOT, "cases", suite, "_draft");
await mkdir(draftDir, { recursive: true });

for (const d of drafts) {
  const out = path.join(draftDir, d.fileName);
  if (await fileExists(out)) {
    console.warn(`  skip (exists): ${out}`);
    continue;
  }
  await writeFile(out, d.content, "utf8");
  console.log(`  ✓ ${out}`);
}

console.log("");
console.log("Drafts are NOT active TCs. Human review required before promotion.");
console.log("Next steps:");
console.log(`  1. Review ${draftDir}/*.md`);
console.log("  2. Edit, refine, sanity-check");
console.log("  3. Promote: move to qa/cases/" + suite + "/ and remove DRAFT marker from filename");
console.log("  4. Update frontmatter status: draft → active");
console.log("  5. Commit");

// ─────────────────────────────────────────────────────────────────────────

function buildPrompt({ suite, domain, briefText, sourceLabel, maxCases, existingTitles }) {
  const existingBlock = existingTitles.length
    ? `\n\n## Already existing TCs in this suite (do not duplicate)\n\n${existingTitles.map((t) => `- ${t}`).join("\n")}`
    : "";

  return `You are a senior QA engineer at Cortex AI Automation. Your job is to draft high-quality manual test cases from a requirement or feature brief.

## Context

- Product: Cortex AI Automation — an AI test automation platform
- Domain prefix for this suite: ${domain}
- Suite folder: qa/cases/${suite}/
- Convention: each TC is a markdown file with YAML frontmatter and a body containing numbered steps + expected results in a table.
- Language: Turkish for body content, English for technical keywords (HTTP codes, JSON field names).

## Input source (${sourceLabel})

\`\`\`
${briefText}
\`\`\`
${existingBlock}

## Your task

Generate ${maxCases} test case drafts. Cover:
1. Happy-path (positive)
2. Negative / error handling
3. Edge cases (boundary, empty input, max length)
4. Security/permission concerns (if domain implies)
5. Integration touchpoints (if applicable)

Vary priority (P0/P1/P2) and type (functional/smoke/regression/security/integration). Do NOT mark anything 'automated' — these are drafts.

## Output format

Respond with a JSON array, no other text. Each element:

\`\`\`json
{
  "title": "string (Turkish, concise, action-oriented)",
  "priority": "P0|P1|P2|P3",
  "type": ["functional"],
  "estimated_minutes": 3,
  "preconditions": "string (free text, optional)",
  "steps": [
    { "step": "string (Turkish)", "expected": "string (Turkish)" }
  ],
  "notes": "string (optional, edge cases or rationale)"
}
\`\`\`

Aim for 3-6 steps per TC. Steps must be deterministic and reproducible. Expected results must be specific (HTTP codes, exact UI labels, JWT format etc.).

Return ONLY the JSON array, no markdown code fences, no commentary.`;
}

function resolveProvider() {
  const gatewayUrl = process.env.CORTEX_AI_GATEWAY_URL;
  const anthropicKey = process.env.ANTHROPIC_API_KEY;
  const openaiKey = process.env.OPENAI_API_KEY;

  if (gatewayUrl) {
    return {
      name: "cortex-ai-gateway",
      defaultModel: "claude-sonnet-4-6",
      async call(prompt, model) {
        const res = await fetch(`${gatewayUrl.replace(/\/$/, "")}/v1/chat/completions`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            model,
            messages: [{ role: "user", content: prompt }],
            max_tokens: 4000,
          }),
        });
        if (!res.ok) throw new Error(`Gateway HTTP ${res.status}: ${await res.text()}`);
        const json = await res.json();
        return json.choices?.[0]?.message?.content || json.content || "";
      },
      estimateCostUsd: (p, r) => estimateCost(p, r, 0.003, 0.015),
    };
  }

  if (anthropicKey) {
    return {
      name: "anthropic-direct",
      defaultModel: "claude-sonnet-4-6",
      async call(prompt, model) {
        const res = await fetch("https://api.anthropic.com/v1/messages", {
          method: "POST",
          headers: {
            "content-type": "application/json",
            "x-api-key": anthropicKey,
            "anthropic-version": "2023-06-01",
          },
          body: JSON.stringify({
            model,
            max_tokens: 4000,
            messages: [{ role: "user", content: prompt }],
          }),
        });
        if (!res.ok) throw new Error(`Anthropic HTTP ${res.status}: ${await res.text()}`);
        const json = await res.json();
        return json.content?.[0]?.text || "";
      },
      estimateCostUsd: (p, r) => estimateCost(p, r, 0.003, 0.015),
    };
  }

  if (openaiKey) {
    return {
      name: "openai-direct",
      defaultModel: "gpt-4o-mini",
      async call(prompt, model) {
        const res = await fetch("https://api.openai.com/v1/chat/completions", {
          method: "POST",
          headers: {
            "content-type": "application/json",
            authorization: `Bearer ${openaiKey}`,
          },
          body: JSON.stringify({
            model,
            messages: [{ role: "user", content: prompt }],
            max_tokens: 4000,
          }),
        });
        if (!res.ok) throw new Error(`OpenAI HTTP ${res.status}: ${await res.text()}`);
        const json = await res.json();
        return json.choices?.[0]?.message?.content || "";
      },
      estimateCostUsd: (p, r) => estimateCost(p, r, 0.00015, 0.0006),
    };
  }

  console.error("");
  console.error("No AI provider configured. Set one of:");
  console.error("  CORTEX_AI_GATEWAY_URL  (preferred — dogfoods Cortex's own gateway)");
  console.error("  ANTHROPIC_API_KEY");
  console.error("  OPENAI_API_KEY");
  console.error("");
  console.error("Run with --dry-run to inspect the prompt without calling any LLM.");
  process.exit(1);
}

function estimateCost(prompt, response, inUsdPer1k, outUsdPer1k) {
  const inTokens = Math.ceil(prompt.length / 4);
  const outTokens = Math.ceil(response.length / 4);
  return (inTokens * inUsdPer1k + outTokens * outUsdPer1k) / 1000;
}

async function checkBudget() {
  const budgetPath = path.join(QA_ROOT, ".ai-budget.json");
  const today = new Date().toISOString().slice(0, 10);
  let state = { day: today, usd: 0 };
  try {
    const raw = await readFile(budgetPath, "utf8");
    state = JSON.parse(raw);
    if (state.day !== today) state = { day: today, usd: 0 };
  } catch {
    // first run
  }
  if (state.usd >= 5) return false;
  if (state.usd >= 1) console.warn(`⚠ AI budget today: $${state.usd.toFixed(3)} (warn threshold $1, block $5)`);
  return true;
}

async function recordBudgetTick(usd) {
  const budgetPath = path.join(QA_ROOT, ".ai-budget.json");
  const today = new Date().toISOString().slice(0, 10);
  let state = { day: today, usd: 0 };
  try {
    const raw = await readFile(budgetPath, "utf8");
    state = JSON.parse(raw);
    if (state.day !== today) state = { day: today, usd: 0 };
  } catch {
    // first
  }
  state.usd += usd;
  await writeFile(budgetPath, JSON.stringify(state, null, 2), "utf8");
}

function parseLlmResponse(text, { suite, domain, existingIds }) {
  let parsed;
  try {
    const trimmed = text.trim().replace(/^```(?:json)?\s*|\s*```$/g, "");
    parsed = JSON.parse(trimmed);
  } catch (err) {
    console.error("LLM response is not valid JSON. Raw response:");
    console.error(text.slice(0, 1000));
    throw err;
  }
  if (!Array.isArray(parsed)) throw new Error("LLM response is not an array");

  const drafts = [];
  let runningIds = [...existingIds];
  for (const item of parsed) {
    const seq = nextSequence(runningIds, `TC-${domain}`);
    const id = `TC-${domain}-${seq}`;
    runningIds.push(id);
    const slug = slugify(item.title || "draft");
    const fileName = `DRAFT-${id}-${slug}.md`;
    const today = new Date().toISOString().slice(0, 10);

    const fm = `---
id: ${id}
title: "${(item.title || "").replace(/"/g, '\\"')}"
suite: ${suite}
priority: ${item.priority || "P2"}
type: ${JSON.stringify(item.type || ["functional"])}
status: draft
owner: "@ai-suggest"
created: ${today}
updated: ${today}
estimated_minutes: ${item.estimated_minutes || 5}
automation:
  status: not-automated
requirements: []
pre_conditions: []
tags: [ai-generated]
---
`;

    let body = `\n# ${id} — ${item.title}\n\n`;
    if (item.preconditions) body += `## Önkoşul\n${item.preconditions}\n\n`;
    body += "## Adımlar\n\n| # | Adım | Beklenen Sonuç |\n|---|------|----------------|\n";
    (item.steps || []).forEach((s, i) => {
      const stepText = (s.step || "").replace(/\|/g, "\\|");
      const expText = (s.expected || "").replace(/\|/g, "\\|");
      body += `| ${i + 1} | ${stepText} | ${expText} |\n`;
    });
    if (item.notes) body += `\n## Notlar\n${item.notes}\n`;
    body += `\n---\n_AI tarafından üretildi. **İnsan reviewü zorunlu.** Promote etmeden önce kontrol et._\n`;

    drafts.push({ fileName, content: fm + body });
  }
  return drafts;
}

async function fileExists(p) {
  try { await stat(p); return true; } catch { return false; }
}
