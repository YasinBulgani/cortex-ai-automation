#!/usr/bin/env node
/**
 * qa/tools/flakiness.mjs
 *
 * qa/runs/'taki tüm run YAML'larını analiz eder, pass↔fail dalgalanan TC'leri
 * tespit eder ve qa/coverage/flakiness.md raporu üretir.
 *
 * Flakiness skoru: bir TC'nin ardışık N run'da status değişim oranı.
 *
 * Usage:
 *   node qa/tools/flakiness.mjs                       # tüm history, top 20 flaky
 *   node qa/tools/flakiness.mjs --min-runs=5          # en az 5 run'da görünenler
 *   node qa/tools/flakiness.mjs --write               # coverage/flakiness.md
 */

import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { parseArgs } from "node:util";
import { QA_ROOT, loadAllRuns } from "./lib/files.mjs";

const { values: args } = parseArgs({
  options: {
    "min-runs": { type: "string", default: "3" },
    write: { type: "boolean", default: false },
    top: { type: "string", default: "20" },
  },
});

const minRuns = parseInt(args["min-runs"], 10) || 3;
const top = parseInt(args.top, 10) || 20;

const runs = (await loadAllRuns())
  .filter((r) => r.data)
  .sort((a, b) => (a.data.started || "").localeCompare(b.data.started || ""));

if (runs.length === 0) {
  console.log("No runs in qa/runs/. Nothing to analyze.");
  process.exit(0);
}

const tcHistory = new Map();
for (const r of runs) {
  for (const res of r.data.results || []) {
    if (!tcHistory.has(res.tc)) tcHistory.set(res.tc, []);
    tcHistory.get(res.tc).push({
      run: r.data.id,
      started: r.data.started,
      status: res.status,
      duration_s: res.duration_s,
    });
  }
}

const analysis = [];
for (const [tc, history] of tcHistory) {
  if (history.length < minRuns) continue;
  let flips = 0;
  let prev = null;
  let passes = 0;
  let fails = 0;
  let blocks = 0;
  for (const h of history) {
    if (h.status === "pass") passes++;
    else if (h.status === "fail") fails++;
    else if (h.status === "blocked") blocks++;
    if (prev !== null && prev !== h.status && (h.status === "pass" || h.status === "fail")) flips++;
    prev = h.status;
  }
  const flipRate = history.length > 1 ? flips / (history.length - 1) : 0;
  const flaky = flipRate >= 0.3 && passes > 0 && fails > 0;
  const lastStatus = history[history.length - 1].status;

  analysis.push({
    tc,
    runCount: history.length,
    passes,
    fails,
    blocks,
    flips,
    flipRate,
    flaky,
    lastStatus,
    lastRun: history[history.length - 1].run,
  });
}

analysis.sort((a, b) => b.flipRate - a.flipRate);

const flakyList = analysis.filter((a) => a.flaky).slice(0, top);
const stableList = analysis.filter((a) => !a.flaky);

const lines = [
  "# Flakiness Report",
  "",
  `_Otomatik üretildi — \`qa/tools/flakiness.mjs\`. ${new Date().toISOString().slice(0, 10)}._`,
  "",
  `Analiz edilen run: ${runs.length}`,
  `Analiz edilen TC: ${tcHistory.size} (en az ${minRuns} run'da görünmüş)`,
  `Flaky tespit edilen: **${flakyList.length}** (top ${top})`,
  "",
  "## Flaky TC'ler (pass↔fail dalgalanan)",
  "",
  flakyList.length === 0
    ? "_Yok — tüm TC'ler stabil._"
    : [
        "| TC | Run | Pass | Fail | Block | Flip oranı | Son durum |",
        "|---|---:|---:|---:|---:|---:|---|",
        ...flakyList.map(
          (a) =>
            `| \`${a.tc}\` | ${a.runCount} | ${a.passes} | ${a.fails} | ${a.blocks} | ${(a.flipRate * 100).toFixed(0)}% | ${a.lastStatus} |`,
        ),
      ].join("\n"),
  "",
  "## Stable TC'ler (özet)",
  "",
  `${stableList.length} TC stabil (flip oranı < %30 veya tek-yönlü pass/fail).`,
  "",
  "## Önerilen aksiyonlar",
  "",
  flakyList.length > 0
    ? `- Top 3 flaky'i \`e2e/quarantine.json\`'a ekle (quarantine until fixed)
- Failing run'lardaki error pattern'lerini incele (timing, race condition, env)
- Test data izolasyonunu kontrol et (paralel run'larda state sızıntı?)
- Flaky TC'lere \`flaky\` tag ekle (\`qa/tools/new-tc.mjs\` schema)`
    : "- Sistem sağlıklı, kalite gate'leri çalışıyor.",
  "",
];

const out = lines.join("\n");

if (args.write) {
  await mkdir(path.join(QA_ROOT, "coverage"), { recursive: true });
  const outPath = path.join(QA_ROOT, "coverage", "flakiness.md");
  await writeFile(outPath, out, "utf8");
  console.log(`✓ ${path.relative(process.cwd(), outPath)}`);
  console.log(`  ${flakyList.length} flaky / ${tcHistory.size} analyzed`);
} else {
  console.log(out);
}
