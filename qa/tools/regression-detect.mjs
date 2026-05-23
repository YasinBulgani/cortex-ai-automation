#!/usr/bin/env node
/**
 * qa/tools/regression-detect.mjs
 *
 * PR diff'inden değişen dosyalara bağlı TC'leri analiz eder ve regression
 * risk skoru üretir. test-impact.mjs'in üstünde:
 *   - TC priority + last failure history'sini katar
 *   - Risk skoru 0-100 (high/med/low kategorize)
 *   - "Bu PR'ı merge etmeden önce X TC koş" tavsiyesi
 *
 * Usage:
 *   node qa/tools/regression-detect.mjs --base=main          # PR analizi
 *   node qa/tools/regression-detect.mjs --base=main --json   # CI gate için
 *   node qa/tools/regression-detect.mjs --base=main --strict-threshold=70  # exit 1 if risk > 70
 */

import { execSync } from "node:child_process";
import { parseArgs } from "node:util";
import { REPO_ROOT, loadAllTestCases, loadAllRuns } from "./lib/files.mjs";

const { values: args } = parseArgs({
  options: {
    base: { type: "string", default: "main" },
    json: { type: "boolean", default: false },
    "strict-threshold": { type: "string" },
  },
});

let changedFiles;
try {
  changedFiles = execSync(`git diff --name-only ${args.base}...HEAD`, {
    cwd: REPO_ROOT,
    encoding: "utf8",
  })
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
} catch (err) {
  console.error(`git diff failed: ${err.message}`);
  process.exit(1);
}

if (changedFiles.length === 0) {
  console.log("No changed files vs", args.base);
  process.exit(0);
}

const tcs = (await loadAllTestCases()).filter((t) => t.data);
const runs = (await loadAllRuns()).filter((r) => r.data);

// TC history → failure rate
const tcHistory = new Map();
for (const r of runs.sort((a, b) => (a.data.started || "").localeCompare(b.data.started || ""))) {
  for (const res of r.data.results || []) {
    if (!tcHistory.has(res.tc)) tcHistory.set(res.tc, []);
    tcHistory.get(res.tc).push(res.status);
  }
}

function failureRate(tcId) {
  const h = tcHistory.get(tcId);
  if (!h || h.length === 0) return 0;
  const fails = h.filter((s) => s === "fail").length;
  return fails / h.length;
}

function lastFailureRecency(tcId) {
  const h = tcHistory.get(tcId);
  if (!h || h.length === 0) return null;
  for (let i = h.length - 1; i >= 0; i--) {
    if (h[i] === "fail") return h.length - 1 - i;
  }
  return null;
}

// Risk scoring per impacted TC
const priorityWeight = { P0: 50, P1: 30, P2: 15, P3: 5 };
const impactedTcs = [];

for (const t of tcs) {
  const refs = t.data.automation?.refs || [];
  let isImpacted = false;
  let matchedFiles = [];
  for (const ref of refs) {
    const refPath = ref.split(":")[0];
    for (const f of changedFiles) {
      if (f === refPath || f.startsWith(refPath + "/")) {
        isImpacted = true;
        matchedFiles.push(f);
      }
    }
  }
  if (!isImpacted) continue;

  const failRate = failureRate(t.data.id);
  const recency = lastFailureRecency(t.data.id);

  // Risk score: priority (50%) + failure history (30%) + recency (20%)
  const prioScore = priorityWeight[t.data.priority] || 5;
  const histScore = failRate * 30;
  const recencyScore = recency !== null && recency < 3 ? 20 - recency * 5 : 0;
  const riskScore = Math.min(100, prioScore + histScore + recencyScore);

  impactedTcs.push({
    id: t.data.id,
    title: t.data.title,
    priority: t.data.priority,
    suite: t.data.suite,
    automation: t.data.automation?.status,
    fail_rate: +failRate.toFixed(2),
    last_failure_runs_ago: recency,
    risk_score: Math.round(riskScore),
    matched_files: [...new Set(matchedFiles)],
  });
}

impactedTcs.sort((a, b) => b.risk_score - a.risk_score);

const totalRisk =
  impactedTcs.length > 0
    ? Math.round(impactedTcs.reduce((acc, t) => acc + t.risk_score, 0) / impactedTcs.length)
    : 0;

const high = impactedTcs.filter((t) => t.risk_score >= 70);
const med = impactedTcs.filter((t) => t.risk_score >= 40 && t.risk_score < 70);
const low = impactedTcs.filter((t) => t.risk_score < 40);

if (args.json) {
  console.log(
    JSON.stringify(
      {
        changed_files: changedFiles.length,
        impacted_tc: impactedTcs.length,
        avg_risk: totalRisk,
        high_risk_tc: high.length,
        recommendation: high.length > 0 ? "RUN HIGH-RISK TCs BEFORE MERGE" : "STANDARD REGRESSION OK",
        details: impactedTcs,
      },
      null,
      2,
    ),
  );
} else {
  console.log(`\n╔═══════════════════════════════════════════════════════════════╗`);
  console.log(`║  REGRESSION RISK ANALYSIS                                     ║`);
  console.log(`║  ${changedFiles.length} changed files vs ${args.base.padEnd(40)}    ║`);
  console.log(`╚═══════════════════════════════════════════════════════════════╝\n`);

  console.log(`Impacted TC: ${impactedTcs.length}`);
  console.log(`Average risk: ${totalRisk}/100`);
  console.log(`  High (≥70):   ${high.length}`);
  console.log(`  Medium (40-69): ${med.length}`);
  console.log(`  Low (<40):    ${low.length}\n`);

  if (high.length > 0) {
    console.log(`⚠ HIGH RISK TCs — run before merge:\n`);
    for (const t of high) {
      console.log(`  ${t.id} [${t.priority}] risk=${t.risk_score} fail-rate=${(t.fail_rate * 100).toFixed(0)}%`);
      console.log(`    ${t.title}`);
      console.log(`    ${t.matched_files.slice(0, 2).join(", ")}${t.matched_files.length > 2 ? ", ..." : ""}`);
    }
    console.log("");
  }

  if (impactedTcs.length === 0) {
    console.log("No automation-linked TCs impacted.");
    console.log("Tip: changed files may not have automation.refs back-link, or are non-test files.");
  } else {
    console.log("Tavsiye:");
    if (high.length > 0) {
      console.log(`  → RUN: ${high.map((t) => t.id).join(", ")} (manuel/otomatik)`);
      console.log(`  → BLOCK MERGE until those TCs pass`);
    } else if (med.length > 0) {
      console.log(`  → Smoke suite + medium-risk TC'leri koş`);
    } else {
      console.log(`  → Standart regression yeterli`);
    }
  }
}

if (args["strict-threshold"]) {
  const t = parseInt(args["strict-threshold"], 10);
  if (totalRisk > t || high.length > 0) {
    process.exit(1);
  }
}
