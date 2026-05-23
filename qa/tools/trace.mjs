#!/usr/bin/env node
/**
 * qa/tools/trace.mjs
 *
 * Produces traceability artifacts:
 *   - coverage/traceability.csv     (TC × automation × requirement × last_run × open_defects)
 *   - coverage/coverage-matrix.md   (domain × priority pivot)
 *   - coverage/orphans.md           (gaps: TC without automation, automation without TC, etc.)
 *
 * Usage:
 *   node qa/tools/trace.mjs            # write artifacts
 *   node qa/tools/trace.mjs --check    # exit 1 if artifacts would change (CI gate)
 */

import { mkdir, readFile, writeFile, stat } from "node:fs/promises";
import path from "node:path";
import fg from "fast-glob";
import { parseArgs } from "node:util";

import {
  QA_ROOT,
  REPO_ROOT,
  loadAllTestCases,
  loadAllRequirements,
  loadAllRuns,
} from "./lib/files.mjs";

const { values: args } = parseArgs({
  options: {
    check: { type: "boolean", default: false },
  },
});

const COVERAGE_DIR = path.join(QA_ROOT, "coverage");
await mkdir(COVERAGE_DIR, { recursive: true });

const tcs = await loadAllTestCases();
const reqs = await loadAllRequirements();
const runs = await loadAllRuns();

const tcById = new Map();
for (const t of tcs) if (t.data?.id) tcById.set(t.data.id, t.data);

const lastResultByTc = new Map();
const runsSorted = runs.filter((r) => r.data?.started).sort((a, b) => a.data.started.localeCompare(b.data.started));
for (const r of runsSorted) {
  if (!r.data) continue;
  for (const res of r.data.results || []) {
    lastResultByTc.set(res.tc, { runId: r.data.id, status: res.status, started: r.data.started });
  }
}

const openDefectsByTc = new Map();
for (const t of tcs) {
  if (!t.data) continue;
  if (t.data.open_defects?.length) openDefectsByTc.set(t.data.id, t.data.open_defects);
}

const requirementsByTc = new Map();
for (const t of tcs) {
  if (!t.data) continue;
  if (t.data.requirements?.length) requirementsByTc.set(t.data.id, t.data.requirements);
}

// CSV
const csvLines = [
  "tc_id,suite,priority,type,automation_status,automation_ref,requirements,last_run,last_status,open_defects",
];
for (const [id, data] of tcById) {
  const refs = (data.automation?.refs || []).join(" | ");
  const last = lastResultByTc.get(id);
  const reqs = (data.requirements || []).join(" | ");
  const defs = (data.open_defects || []).join(" | ");
  csvLines.push(
    [
      id,
      data.suite,
      data.priority,
      (data.type || []).join("+"),
      data.automation?.status || "",
      refs,
      reqs,
      last?.runId || "",
      last?.status || "",
      defs,
    ]
      .map((v) => (typeof v === "string" && v.includes(",") ? `"${v}"` : v))
      .join(","),
  );
}
const csvOut = csvLines.join("\n") + "\n";

// Coverage matrix
const matrix = {};
const priorities = ["P0", "P1", "P2", "P3"];
for (const [, data] of tcById) {
  matrix[data.suite] ??= { P0: 0, P1: 0, P2: 0, P3: 0, total: 0, automated: 0 };
  matrix[data.suite][data.priority]++;
  matrix[data.suite].total++;
  if (data.automation?.status === "automated") matrix[data.suite].automated++;
}

const mxLines = [
  "# Coverage Matrix",
  "",
  "_Otomatik üretildi — `qa/tools/trace.mjs` ile._",
  "",
  "| Suite | P0 | P1 | P2 | P3 | Total | Automated | % |",
  "|---|---:|---:|---:|---:|---:|---:|---:|",
];
const sortedSuites = Object.keys(matrix).sort();
for (const suite of sortedSuites) {
  const m = matrix[suite];
  const pct = m.total > 0 ? Math.round((m.automated / m.total) * 100) : 0;
  mxLines.push(`| ${suite} | ${m.P0} | ${m.P1} | ${m.P2} | ${m.P3} | ${m.total} | ${m.automated} | ${pct}% |`);
}
mxLines.push("");
const matrixOut = mxLines.join("\n");

// Orphans
const featureFiles = await fg(
  [
    "e2e/bdd/features/**/*.feature",
    "backend/tests/bdd/features/**/*.feature",
    "e2e/**/*.spec.ts",
  ],
  { cwd: REPO_ROOT, absolute: true },
);

const taggedTcs = new Set();
const tagRegex = /@(TC-[A-Z0-9]+-\d{3,})/g;
for (const f of featureFiles) {
  try {
    const text = await readFile(f, "utf8");
    let m;
    while ((m = tagRegex.exec(text)) !== null) taggedTcs.add(m[1]);
  } catch {
    // ignore
  }
}

const tcsClaimingAutomation = new Set();
for (const [id, data] of tcById) {
  if (data.automation?.status === "automated") tcsClaimingAutomation.add(id);
}

const tcsTaggedButNotAutomated = [];
for (const id of taggedTcs) {
  const data = tcById.get(id);
  if (!data) tcsTaggedButNotAutomated.push({ id, reason: "tagged-but-missing-tc" });
  else if (data.automation?.status !== "automated")
    tcsTaggedButNotAutomated.push({ id, reason: "tagged-but-status-not-automated" });
}

const tcsAutomatedButNotTagged = [];
for (const id of tcsClaimingAutomation) {
  if (!taggedTcs.has(id)) tcsAutomatedButNotTagged.push(id);
}

const tcsWithoutRequirement = [];
for (const [id, data] of tcById) {
  if (!data.requirements?.length) tcsWithoutRequirement.push(id);
}

const reqsWithoutTc = [];
const reqsById = new Set(reqs.map((r) => r.data?.id).filter(Boolean));
const reqsCoveredByTc = new Set();
for (const [, data] of tcById) {
  for (const r of data.requirements || []) reqsCoveredByTc.add(r);
}
for (const rid of reqsById) {
  if (!reqsCoveredByTc.has(rid)) reqsWithoutTc.push(rid);
}

const orphanLines = [
  "# Orphans & Gaps",
  "",
  "_Otomatik üretildi — `qa/tools/trace.mjs` ile._",
  "",
  `## Tagged in code but missing in qa/cases/ (${tcsTaggedButNotAutomated.filter((o) => o.reason === "tagged-but-missing-tc").length})`,
  "",
  ...tcsTaggedButNotAutomated
    .filter((o) => o.reason === "tagged-but-missing-tc")
    .map((o) => `- ${o.id}`),
  "",
  `## TC marked 'automated' but no @TC tag found (${tcsAutomatedButNotTagged.length})`,
  "",
  ...tcsAutomatedButNotTagged.map((id) => `- ${id}`),
  "",
  `## TC without requirement link (${tcsWithoutRequirement.length})`,
  "",
  ...tcsWithoutRequirement.map((id) => `- ${id}`),
  "",
  `## Requirements not covered by any TC (${reqsWithoutTc.length})`,
  "",
  ...reqsWithoutTc.map((id) => `- ${id}`),
  "",
];
const orphansOut = orphanLines.join("\n");

const csvPath = path.join(COVERAGE_DIR, "traceability.csv");
const matrixPath = path.join(COVERAGE_DIR, "coverage-matrix.md");
const orphansPath = path.join(COVERAGE_DIR, "orphans.md");

async function readSafe(p) {
  try { return await readFile(p, "utf8"); } catch { return null; }
}

if (args.check) {
  let changed = false;
  for (const [p, want] of [
    [csvPath, csvOut],
    [matrixPath, matrixOut],
    [orphansPath, orphansOut],
  ]) {
    const cur = await readSafe(p);
    if (cur !== want) {
      changed = true;
      console.error(`Would change: ${p}`);
    }
  }
  process.exit(changed ? 1 : 0);
}

await writeFile(csvPath, csvOut, "utf8");
await writeFile(matrixPath, matrixOut, "utf8");
await writeFile(orphansPath, orphansOut, "utf8");

console.log(`✓ ${csvPath}`);
console.log(`✓ ${matrixPath}`);
console.log(`✓ ${orphansPath}`);
console.log(`  ${tcById.size} test cases, ${runs.length} runs, ${reqs.length} requirements`);
