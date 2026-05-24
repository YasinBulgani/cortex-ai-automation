#!/usr/bin/env node
/**
 * qa/tools/health-check.mjs
 *
 * qa/ klasörünün genel sağlığını 0-100 skor olarak hesaplar.
 *
 * Skor bileşenleri (toplam 100):
 *   - Validation pass    (20)
 *   - Coverage automation (20)
 *   - Requirement linkage (15)
 *   - Pre-condition linkage (10)
 *   - Run history freshness (15)
 *   - Flakiness rate (10)
 *   - Open defects (10)
 *
 * Usage:
 *   node qa/tools/health-check.mjs              # human-readable
 *   node qa/tools/health-check.mjs --json       # CI için
 *   node qa/tools/health-check.mjs --threshold=70  # exit 1 if < 70
 */

import { execSync } from "node:child_process";
import { parseArgs } from "node:util";
import { loadAllTestCases, loadAllRuns, loadAllRequirements } from "./lib/files.mjs";

const { values: args } = parseArgs({
  options: {
    json: { type: "boolean", default: false },
    threshold: { type: "string", default: "0" },
  },
});

const threshold = parseInt(args.threshold, 10) || 0;

const tcs = (await loadAllTestCases()).filter((t) => t.data);
const runs = (await loadAllRuns()).filter((r) => r.data);
const reqs = (await loadAllRequirements()).filter((r) => r.data);

// 1. Validation (20 pts)
let validateScore = 20;
let validateNote = "0 fail";
try {
  execSync("node tools/validate.mjs --quiet --json", { encoding: "utf8" });
} catch (err) {
  validateScore = 0;
  validateNote = "validate FAILED";
}

// 2. Automation coverage (20 pts)
const automated = tcs.filter((t) => t.data.automation?.status === "automated").length;
const autoPct = tcs.length > 0 ? automated / tcs.length : 0;
const automationScore = Math.round(autoPct * 20);

// 3. Requirement linkage (15 pts)
const tcWithReq = tcs.filter((t) => (t.data.requirements || []).length > 0).length;
const reqLinkPct = tcs.length > 0 ? tcWithReq / tcs.length : 0;
const reqScore = Math.round(reqLinkPct * 15);

// 4. Pre-condition linkage (10 pts)
const tcWithPre = tcs.filter((t) => (t.data.pre_conditions || []).length > 0).length;
const prePct = tcs.length > 0 ? tcWithPre / tcs.length : 0;
const preScore = Math.round(prePct * 10);

// 5. Run history freshness (15 pts)
let runFreshScore = 0;
let runFreshNote = "no runs";
if (runs.length > 0) {
  const sorted = runs.sort((a, b) => (b.data.started || "").localeCompare(a.data.started || ""));
  const lastRunDate = new Date(sorted[0].data.started || 0);
  const daysSince = (Date.now() - lastRunDate.getTime()) / (1000 * 60 * 60 * 24);
  if (daysSince < 1) runFreshScore = 15;
  else if (daysSince < 7) runFreshScore = 12;
  else if (daysSince < 30) runFreshScore = 6;
  else runFreshScore = 2;
  runFreshNote = `${daysSince.toFixed(1)} gün önce`;
}

// 6. Flakiness (10 pts)
let flakyScore = 10;
let flakyNote = "0 flaky";
const tcHistory = new Map();
for (const r of runs.sort((a, b) => (a.data.started || "").localeCompare(b.data.started || ""))) {
  for (const res of r.data.results || []) {
    if (!tcHistory.has(res.tc)) tcHistory.set(res.tc, []);
    tcHistory.get(res.tc).push(res.status);
  }
}
let flakyCount = 0;
for (const [, hist] of tcHistory) {
  if (hist.length < 3) continue;
  let flips = 0;
  for (let i = 1; i < hist.length; i++) {
    if (hist[i] !== hist[i - 1] && (hist[i] === "pass" || hist[i] === "fail")) flips++;
  }
  if (flips / (hist.length - 1) >= 0.3) flakyCount++;
}
if (tcHistory.size > 0) {
  const flakyPct = flakyCount / tcHistory.size;
  flakyScore = Math.max(0, Math.round(10 - flakyPct * 30));
  flakyNote = `${flakyCount}/${tcHistory.size} flaky (${(flakyPct * 100).toFixed(0)}%)`;
}

// 7. Open defects (10 pts)
let openDefects = 0;
for (const t of tcs) openDefects += (t.data.open_defects || []).length;
const defectScore = openDefects === 0 ? 10 : openDefects < 5 ? 6 : openDefects < 10 ? 3 : 0;

const total =
  validateScore + automationScore + reqScore + preScore + runFreshScore + flakyScore + defectScore;

const report = {
  total,
  max: 100,
  grade: total >= 90 ? "A" : total >= 75 ? "B" : total >= 60 ? "C" : total >= 40 ? "D" : "F",
  components: {
    validation: { score: validateScore, max: 20, note: validateNote },
    automation: { score: automationScore, max: 20, note: `${automated}/${tcs.length} = ${(autoPct * 100).toFixed(0)}%` },
    requirements: { score: reqScore, max: 15, note: `${tcWithReq}/${tcs.length} TC linked (${(reqLinkPct * 100).toFixed(0)}%)` },
    pre_conditions: { score: preScore, max: 10, note: `${tcWithPre}/${tcs.length} TC linked (${(prePct * 100).toFixed(0)}%)` },
    run_freshness: { score: runFreshScore, max: 15, note: runFreshNote },
    flakiness: { score: flakyScore, max: 10, note: flakyNote },
    open_defects: { score: defectScore, max: 10, note: `${openDefects} açık` },
  },
  stats: {
    test_cases: tcs.length,
    requirements: reqs.length,
    runs: runs.length,
  },
  generated_at: new Date().toISOString(),
};

if (args.json) {
  console.log(JSON.stringify(report, null, 2));
} else {
  const bar = (score, max, width = 20) => {
    const filled = Math.round((score / max) * width);
    return "█".repeat(filled) + "░".repeat(width - filled);
  };

  console.log("\n╔════════════════════════════════════════════════════════════════╗");
  console.log(`║  qa/ HEALTH SCORE   ${String(total).padStart(3)} / 100   GRADE: ${report.grade}                           ║`);
  console.log("╚════════════════════════════════════════════════════════════════╝\n");

  for (const [k, c] of Object.entries(report.components)) {
    const label = k.padEnd(18);
    console.log(`  ${label} ${bar(c.score, c.max)} ${String(c.score).padStart(3)}/${c.max}   ${c.note}`);
  }

  console.log(`\n  Stats: ${tcs.length} TC, ${reqs.length} REQ, ${runs.length} runs`);
  console.log(`  Generated: ${report.generated_at}\n`);

  if (total < 50) {
    console.log("  ⚠ Below 50 — review failing components");
  } else if (total < 75) {
    console.log("  → On track");
  } else if (total < 90) {
    console.log("  ✓ Healthy");
  } else {
    console.log("  ★ Excellent");
  }
}

process.exit(total < threshold ? 1 : 0);
