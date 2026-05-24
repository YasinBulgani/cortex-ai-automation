#!/usr/bin/env node
/**
 * qa/tools/run-record.mjs
 *
 * Interactive manual test run recorder.
 *
 * Flow:
 *   1. Pick a plan (--plan=foo or interactive)
 *   2. Resolve plan scope → list of TCs
 *   3. Ask environment (branch auto, browser, env, url)
 *   4. For each TC: show steps, ask pass/fail/blocked/skipped, optional note + evidence
 *   5. Write qa/runs/YYYY/MM/TR-*.yml
 *
 * Usage:
 *   node qa/tools/run-record.mjs                           # fully interactive
 *   node qa/tools/run-record.mjs --plan=smoke-daily        # pick plan via arg
 *   node qa/tools/run-record.mjs --plan=smoke-daily --quick  # only pass/fail, no notes
 */

import { mkdir, readFile, writeFile, readdir } from "node:fs/promises";
import path from "node:path";
import { execSync } from "node:child_process";
import { parseArgs } from "node:util";
import { intro, outro, select, text, confirm, isCancel, cancel, log, note } from "@clack/prompts";
import yaml from "js-yaml";
import matter from "gray-matter";
import {
  QA_ROOT,
  REPO_ROOT,
  loadAllTestCases,
  loadAllPlans,
} from "./lib/files.mjs";

const { values: args } = parseArgs({
  options: {
    plan: { type: "string" },
    quick: { type: "boolean", default: false },
    name: { type: "string" },
  },
});

intro("qa/ run recorder");

const plans = await loadAllPlans();
if (plans.length === 0) {
  cancel("No plans found in qa/plans/. Create a plan YAML first.");
  process.exit(1);
}

let chosenPlan;
if (args.plan) {
  chosenPlan = plans.find((p) => {
    if (!p.data) return false;
    if (p.data.id === args.plan) return true;
    if (path.basename(p.file, ".yml") === args.plan) return true;
    return false;
  });
  if (!chosenPlan) {
    cancel(`Plan not found: ${args.plan}`);
    process.exit(1);
  }
} else {
  const choice = await select({
    message: "Pick a plan",
    options: plans
      .filter((p) => p.data)
      .map((p) => ({
        value: p.file,
        label: `${p.data.id} — ${p.data.title}`,
        hint: p.data.milestone,
      })),
  });
  if (isCancel(choice)) {
    cancel("Cancelled.");
    process.exit(0);
  }
  chosenPlan = plans.find((p) => p.file === choice);
}

log.info(`Plan: ${chosenPlan.data.id}`);

const allTcs = await loadAllTestCases();
const tcsByDataId = new Map(allTcs.filter((t) => t.data).map((t) => [t.data.id, t]));

const scopedTcs = resolveScope(chosenPlan.data, allTcs);

if (scopedTcs.length === 0) {
  cancel(`Plan scope resolved to 0 TCs. Check ${chosenPlan.data.id} include/exclude.`);
  process.exit(1);
}
log.success(`${scopedTcs.length} TC in scope`);

const branch = safeGit("git rev-parse --abbrev-ref HEAD") || "main";
const commit = safeGit("git rev-parse --short HEAD") || "unknown";

const browser = args.quick
  ? "chromium"
  : (await text({
      message: "Browser",
      defaultValue: "chromium",
      placeholder: "chromium",
    })) || "chromium";
if (isCancel(browser)) return cancelExit();

const envName = args.quick
  ? "staging"
  : (await text({
      message: "Environment",
      defaultValue: "staging",
      placeholder: "staging | prod | local",
    })) || "staging";
if (isCancel(envName)) return cancelExit();

const url = args.quick
  ? ""
  : (await text({
      message: "URL (optional)",
      placeholder: "https://staging.example.com",
      defaultValue: "",
    })) || "";
if (isCancel(url)) return cancelExit();

const startedAt = new Date();
const results = [];

for (let i = 0; i < scopedTcs.length; i++) {
  const tcInfo = scopedTcs[i];
  const tc = tcInfo.data;
  const num = `${i + 1}/${scopedTcs.length}`;

  if (!args.quick) {
    const steps = await extractStepsTable(tcInfo.file);
    note(
      `${tc.id} — ${tc.title}\n` +
        `Priority: ${tc.priority}    Type: ${(tc.type || []).join(", ")}\n` +
        `Automation: ${tc.automation?.status}\n` +
        (steps ? `\nAdımlar:\n${steps}\n` : ""),
      `[${num}] ${tc.suite}`,
    );
  }

  const status = await select({
    message: `[${num}] ${tc.id} — sonuç?`,
    options: [
      { value: "pass", label: "✓ Pass" },
      { value: "fail", label: "✗ Fail" },
      { value: "blocked", label: "⊘ Blocked (dış engel)" },
      { value: "skipped", label: "↪ Skip (kasıtlı atlandı)" },
      { value: "untested", label: "○ Untested (henüz koşmadım)" },
    ],
  });
  if (isCancel(status)) return cancelExit();

  const result = {
    tc: tc.id,
    tc_commit: commit,
    status,
  };

  if (!args.quick && (status === "fail" || status === "blocked")) {
    const noteText = await text({
      message: "Not (kısa açıklama)",
      placeholder: "Ne oldu?",
      defaultValue: "",
    });
    if (isCancel(noteText)) return cancelExit();
    if (noteText) result.note = noteText;

    const evidence = await text({
      message: "Kanıt yolu (opsiyonel — screenshot, log)",
      placeholder: "evidence/screenshot.png",
      defaultValue: "",
    });
    if (isCancel(evidence)) return cancelExit();
    if (evidence) result.evidence = evidence;

    if (status === "fail") {
      const wantDefect = await confirm({
        message: "GitHub Issue (defect) açmak ister misin?",
        initialValue: false,
      });
      if (isCancel(wantDefect)) return cancelExit();
      if (wantDefect) {
        const issueNum = await text({
          message: "Issue numarası (varsa)",
          placeholder: "1234",
          defaultValue: "",
        });
        if (isCancel(issueNum)) return cancelExit();
        if (issueNum && /^\d+$/.test(issueNum)) result.defect = `GH-${issueNum}`;
      }
    }
  }

  results.push(result);
}

const endedAt = new Date();
const summary = { total: 0, passed: 0, failed: 0, blocked: 0, skipped: 0, untested: 0 };
for (const r of results) {
  summary.total++;
  switch (r.status) {
    case "pass": summary.passed++; break;
    case "fail": summary.failed++; break;
    case "blocked": summary.blocked++; break;
    case "skipped": summary.skipped++; break;
    default: summary.untested++;
  }
}

const yyyy = startedAt.getUTCFullYear();
const mm = String(startedAt.getUTCMonth() + 1).padStart(2, "0");
const dd = String(startedAt.getUTCDate()).padStart(2, "0");
const monthDir = path.join(QA_ROOT, "runs", String(yyyy), mm);
await mkdir(monthDir, { recursive: true });

const baseName = args.name || chosenPlan.data.id.replace(/^TP-/, "").replace(/[^A-Z0-9-]/g, "-");
const existingFiles = await readdir(monthDir).catch(() => []);
const dayPrefix = `TR-${yyyy}-${mm}-${dd}-${baseName.toUpperCase()}-`;
const seq = String(existingFiles.filter((f) => f.startsWith(dayPrefix)).length + 1).padStart(3, "0");
const runId = `${dayPrefix}${seq}`;
const outPath = path.join(monthDir, `${runId}.yml`);

const executor = safeGit("git config user.name").toLowerCase().replace(/\s+/g, "-") || "anonymous";

const yamlDoc = {
  id: runId,
  plan: chosenPlan.data.id,
  started: startedAt.toISOString(),
  ended: endedAt.toISOString(),
  executor: `@${executor}`,
  environment: {
    branch,
    commit,
    browser,
    env: envName,
    ...(url && { url }),
  },
  summary,
  results,
};

const yamlOut = yaml.dump(yamlDoc, { noRefs: true, lineWidth: 120 });
await writeFile(outPath, yamlOut, "utf8");

note(
  `Run ID: ${runId}\n` +
    `Total: ${summary.total} (pass=${summary.passed}, fail=${summary.failed}, blocked=${summary.blocked}, skipped=${summary.skipped}, untested=${summary.untested})\n` +
    `Output: ${path.relative(REPO_ROOT, outPath)}`,
  "Run recorded",
);

if (summary.failed > 0) {
  log.warn(`${summary.failed} TC failed. Consider opening GitHub Issues and re-running 'node tools/trace.mjs'.`);
}

outro("Done. Run 'node tools/trace.mjs' to refresh coverage.");

function cancelExit() {
  cancel("Cancelled. No run YAML written.");
  process.exit(0);
}

function safeGit(cmd) {
  try {
    return execSync(cmd, { cwd: REPO_ROOT, encoding: "utf8" }).trim();
  } catch {
    return "";
  }
}

function resolveScope(plan, allTcs) {
  const includeMatches = new Set();
  for (const inc of plan.scope?.include || []) {
    for (const tcInfo of allTcs) {
      if (!tcInfo.data) continue;
      const tc = tcInfo.data;
      let match = true;
      if (inc.suite && tc.suite !== inc.suite) match = false;
      if (inc.priorities && !inc.priorities.includes(tc.priority)) match = false;
      if (inc.tags && !(tc.tags || []).some((t) => inc.tags.includes(t))) match = false;
      if (inc.cases && !inc.cases.includes(tc.id)) match = false;
      if (match && (inc.suite || inc.priorities || inc.tags || inc.cases)) {
        includeMatches.add(tc.id);
      }
    }
  }

  for (const exc of plan.scope?.exclude || []) {
    for (const tcInfo of allTcs) {
      if (!tcInfo.data) continue;
      const tc = tcInfo.data;
      if (exc.tags && (tc.tags || []).some((t) => exc.tags.includes(t))) includeMatches.delete(tc.id);
      if (exc.cases && exc.cases.includes(tc.id)) includeMatches.delete(tc.id);
    }
  }

  return allTcs
    .filter((t) => t.data && includeMatches.has(t.data.id))
    .sort((a, b) => {
      const prio = { P0: 0, P1: 1, P2: 2, P3: 3 };
      const dp = (prio[a.data.priority] ?? 9) - (prio[b.data.priority] ?? 9);
      if (dp !== 0) return dp;
      return a.data.id.localeCompare(b.data.id);
    });
}

async function extractStepsTable(filePath) {
  try {
    const raw = await readFile(filePath, "utf8");
    const parsed = matter(raw, { engines: { yaml: { parse: (i) => yaml.load(i, { schema: yaml.JSON_SCHEMA }), stringify: yaml.dump } } });
    const body = parsed.content;
    const stepsHeader = /##\s+Adımlar/i.exec(body);
    if (!stepsHeader) return null;
    const tail = body.slice(stepsHeader.index);
    const tableMatch = /(\|[^\n]+\|\n\|[\s|:-]+\|\n(?:\|[^\n]+\|\n?)+)/m.exec(tail);
    return tableMatch ? tableMatch[1].trim() : null;
  } catch {
    return null;
  }
}
