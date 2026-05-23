#!/usr/bin/env node
/**
 * qa/tools/seed-runs.mjs
 *
 * Demo amaçlı: qa/runs/'a gerçekçi sahte run YAML'ları üretir.
 *
 * Dashboard / flakiness / signoff araçları boş run history'de boş çıktı verir.
 * Bu CLI son N gün için pattern'li (mostly pass, occasional fail, 1-2 flaky)
 * demo runs üretir.
 *
 * Usage:
 *   node qa/tools/seed-runs.mjs --days=14                # son 14 günde günlük 1 smoke run
 *   node qa/tools/seed-runs.mjs --days=7 --suite=auth    # sadece auth TC'leri
 *   node qa/tools/seed-runs.mjs --clean                  # mevcut runs/'ı sil + yeniden
 */

import { mkdir, writeFile, rm } from "node:fs/promises";
import path from "node:path";
import { parseArgs } from "node:util";
import yaml from "js-yaml";
import { QA_ROOT, loadAllTestCases, loadAllPlans } from "./lib/files.mjs";

const { values: args } = parseArgs({
  options: {
    days: { type: "string", default: "14" },
    suite: { type: "string" },
    plan: { type: "string", default: "smoke-daily" },
    clean: { type: "boolean", default: false },
  },
});

const days = parseInt(args.days, 10) || 14;
const RUNS_DIR = path.join(QA_ROOT, "runs");

if (args.clean) {
  try {
    await rm(RUNS_DIR, { recursive: true, force: true });
    console.log(`Cleaned ${RUNS_DIR}`);
  } catch {}
  await mkdir(RUNS_DIR, { recursive: true });
}

const tcs = (await loadAllTestCases()).filter((t) => t.data);
const plans = (await loadAllPlans()).filter((p) => p.data);

let scopedTcs = tcs;
if (args.suite) scopedTcs = tcs.filter((t) => t.data.suite === args.suite);

// Smoke-daily plan zaten 6 P0 auth TC içeriyor — onu da kullanabilirim
const planObj = plans.find((p) => p.data.id === "TP-2026.Q2-SMOKE-DAILY")?.data;
if (planObj && !args.suite) {
  // Plan kapsamındaki TC'leri kullan
  scopedTcs = tcs.filter((t) => {
    for (const inc of planObj.scope?.include || []) {
      if (inc.suite === t.data.suite && (inc.priorities || []).includes(t.data.priority)) return true;
    }
    return false;
  });
}

if (scopedTcs.length === 0) {
  console.error("No TCs match the filter.");
  process.exit(1);
}

console.log(`Seeding ${days} days × ${scopedTcs.length} TC = up to ${days * scopedTcs.length} results`);

// Flaky pattern: TC-AUTH-007 ~%30 fail, diğerleri %95+ pass
const flakyTcs = new Set(["TC-AUTH-007"]);
const occasionalFailTcs = new Set(["TC-AUTH-003"]);

let written = 0;
const today = new Date();

for (let dayOffset = days - 1; dayOffset >= 0; dayOffset--) {
  const runDate = new Date(today);
  runDate.setUTCDate(today.getUTCDate() - dayOffset);
  runDate.setUTCHours(9, 15, 0, 0);

  const yyyy = runDate.getUTCFullYear();
  const mm = String(runDate.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(runDate.getUTCDate()).padStart(2, "0");
  const monthDir = path.join(RUNS_DIR, String(yyyy), mm);
  await mkdir(monthDir, { recursive: true });

  const runId = `TR-${yyyy}-${mm}-${dd}-SMOKE-DAILY-001`;
  const startedAt = runDate.toISOString();

  const results = [];
  let durTotal = 0;
  for (const tc of scopedTcs) {
    const tcData = tc.data;
    let status = "pass";
    if (flakyTcs.has(tcData.id) && Math.random() < 0.35) status = "fail";
    else if (occasionalFailTcs.has(tcData.id) && Math.random() < 0.08) status = "fail";
    else if (Math.random() < 0.02) status = "skipped";

    const baseDur = tcData.estimated_minutes ? tcData.estimated_minutes * 60 / 5 : 3;
    const dur = +(baseDur + Math.random() * 2).toFixed(1);
    durTotal += dur;

    const result = {
      tc: tcData.id,
      tc_commit: "abc1234",
      status,
      duration_s: dur,
    };
    if (tcData.automation?.refs?.[0]) result.automation = tcData.automation.refs[0];
    if (status === "fail") {
      result.note = "Sahte demo data — gerçek fail değil";
    }
    results.push(result);
  }

  const endedAt = new Date(runDate.getTime() + durTotal * 1000).toISOString();
  const summary = {
    total: results.length,
    passed: results.filter((r) => r.status === "pass").length,
    failed: results.filter((r) => r.status === "fail").length,
    blocked: results.filter((r) => r.status === "blocked").length,
    skipped: results.filter((r) => r.status === "skipped").length,
    untested: 0,
  };

  const yamlDoc = {
    id: runId,
    plan: args.plan,
    started: startedAt,
    ended: endedAt,
    executor: "@qa-bot",
    environment: {
      branch: "test",
      commit: "abc1234",
      browser: "chromium",
      env: "staging",
      url: "https://staging.example.com",
    },
    summary,
    results,
  };

  const outPath = path.join(monthDir, `${runId}.yml`);
  await writeFile(outPath, yaml.dump(yamlDoc, { noRefs: true, lineWidth: 120 }), "utf8");
  written++;
}

console.log(`\n✓ Wrote ${written} run YAMLs`);
console.log(`  Demo pattern: TC-AUTH-007 ~35% flaky, TC-AUTH-003 ~8% fail, rest ~95% pass`);
console.log(`\nNext: node tools/trace.mjs && node tools/flakiness.mjs && node tools/dashboard.mjs`);
