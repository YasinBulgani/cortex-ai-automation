#!/usr/bin/env node
/**
 * Playwright JSON raporunu okur, flaky testleri (retry sonrası geçen) tespit eder.
 * quarantine.json ile karşılaştırarak yeni vs bilinen flaky ayrımı yapar.
 *
 * Çıktı: reports/flakiness-report.{json,md}
 *
 * Kullanım:
 *   npx tsx e2e/utils/flaky-tracker.ts
 *   npx tsx e2e/utils/flaky-tracker.ts --json-report=reports/e2e-results.json --threshold=0
 *
 * Exit codes:
 *   0 — yeni flaky yok (veya threshold altında)
 *   1 — report dosyası bulunamadı
 *   2 — yeni flaky count threshold'u aştı
 */

import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(__dirname, "../..");
const REPORTS_DIR = path.join(ROOT, "reports");
const QUARANTINE_FILE = path.join(ROOT, "e2e", "quarantine.json");

// ── Types ─────────────────────────────────────────────────────────────────────

interface QuarantineEntry {
  testTitle: string;
  file: string;
  reason: string;
  since: string;
  owner?: string;
  expiresAfter?: string;
}

interface QuarantineRegistry {
  version: number;
  entries: QuarantineEntry[];
}

interface PWTestResult {
  status: "passed" | "failed" | "timedOut" | "skipped";
  retry: number;
  duration: number;
}

interface PWSpec {
  title: string;
  tests: Array<{
    status: "passed" | "failed" | "flaky" | "skipped";
    results: PWTestResult[];
  }>;
}

interface PWSuite {
  title: string;
  file?: string;
  suites?: PWSuite[];
  specs?: PWSpec[];
}

interface PWReport {
  stats: {
    total: number;
    passed: number;
    failed: number;
    flaky: number;
    skipped: number;
  };
  suites: PWSuite[];
}

interface FlakyInfo {
  title: string;
  fullTitle: string;
  file: string;
  retries: number;
  isQuarantined: boolean;
  quarantineReason?: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function collect(suite: PWSuite, fileFallback: string, out: FlakyInfo[], titlePath: string[]): void {
  const file = suite.file ?? fileFallback;
  for (const spec of suite.specs ?? []) {
    for (const t of spec.tests) {
      if (t.status !== "flaky") continue;
      out.push({
        title: spec.title,
        fullTitle: [...titlePath, suite.title, spec.title].filter(Boolean).join(" > "),
        file,
        retries: t.results.filter((r) => r.retry > 0).length,
        isQuarantined: false,
      });
    }
  }
  for (const sub of suite.suites ?? []) {
    collect(sub, file, out, [...titlePath, suite.title].filter(Boolean));
  }
}

function loadQuarantine(): QuarantineRegistry {
  if (!fs.existsSync(QUARANTINE_FILE)) return { version: 1, entries: [] };
  return JSON.parse(fs.readFileSync(QUARANTINE_FILE, "utf-8")) as QuarantineRegistry;
}

function applyQuarantine(tests: FlakyInfo[], registry: QuarantineRegistry): void {
  const today = new Date().toISOString().split("T")[0];
  for (const t of tests) {
    const entry = registry.entries.find(
      (e) => t.title === e.testTitle || t.fullTitle.includes(e.testTitle)
    );
    if (!entry) continue;
    if (entry.expiresAfter && entry.expiresAfter < today) {
      t.quarantineReason = `EXPIRED (was: ${entry.reason})`;
    } else {
      t.isQuarantined = true;
      t.quarantineReason = entry.reason;
    }
  }
}

function toMarkdown(tests: FlakyInfo[], stats: PWReport["stats"]): string {
  const newFlaky = tests.filter((t) => !t.isQuarantined);
  const known = tests.filter((t) => t.isQuarantined);
  const lines: string[] = [
    "# Flakiness Report",
    "",
    `**Tarih:** ${new Date().toISOString()}`,
    `**Toplam:** ${stats.total} | **Flaky:** ${stats.flaky} | **Hatalı:** ${stats.failed}`,
    "",
  ];

  if (newFlaky.length === 0 && known.length === 0) {
    lines.push("✅ **Flaky test yok.**");
    return lines.join("\n");
  }

  if (newFlaky.length > 0) {
    lines.push(`## ⚠️ Yeni Flaky Testler (${newFlaky.length})`);
    lines.push("");
    lines.push("| Test | Dosya | Retry |");
    lines.push("|------|-------|-------|");
    for (const t of newFlaky) {
      lines.push(`| ${t.fullTitle} | \`${t.file}\` | ${t.retries} |`);
    }
    lines.push("");
    lines.push("> `e2e/quarantine.json`'a ekle veya kök nedeni düzelt.");
    lines.push("");
  }

  if (known.length > 0) {
    lines.push(`## 🔒 Karantinada (${known.length})`);
    lines.push("");
    lines.push("| Test | Dosya | Neden | Retry |");
    lines.push("|------|-------|-------|-------|");
    for (const t of known) {
      lines.push(`| ${t.fullTitle} | \`${t.file}\` | ${t.quarantineReason ?? ""} | ${t.retries} |`);
    }
    lines.push("");
  }

  return lines.join("\n");
}

// ── Main ──────────────────────────────────────────────────────────────────────

function main(): void {
  const argv = process.argv.slice(2);
  const reportPath = argv.find((a) => a.startsWith("--json-report="))?.split("=")[1]
    ?? path.join(REPORTS_DIR, "e2e-results.json");
  const threshold = parseInt(
    argv.find((a) => a.startsWith("--threshold="))?.split("=")[1] ?? "0",
    10
  );

  if (!fs.existsSync(reportPath)) {
    console.error(`Report not found: ${reportPath}`);
    process.exit(1);
  }

  const report: PWReport = JSON.parse(fs.readFileSync(reportPath, "utf-8"));
  const quarantine = loadQuarantine();

  const tests: FlakyInfo[] = [];
  for (const suite of report.suites) {
    collect(suite, "", tests, []);
  }
  applyQuarantine(tests, quarantine);

  const md = toMarkdown(tests, report.stats);
  const json = {
    generatedAt: new Date().toISOString(),
    stats: report.stats,
    flakyTests: tests,
    newFlaky: tests.filter((t) => !t.isQuarantined).length,
    quarantinedFlaky: tests.filter((t) => t.isQuarantined).length,
  };

  fs.mkdirSync(REPORTS_DIR, { recursive: true });
  fs.writeFileSync(path.join(REPORTS_DIR, "flakiness-report.json"), JSON.stringify(json, null, 2));
  fs.writeFileSync(path.join(REPORTS_DIR, "flakiness-report.md"), md);

  console.log(md);

  if (json.newFlaky > threshold) {
    console.error(`\n❌ Gate: ${json.newFlaky} yeni flaky test, threshold ${threshold}'ı aşıyor`);
    process.exit(2);
  }
  console.log(`\n✅ Flakiness check geçti (${json.newFlaky} yeni, eşik: ${threshold})`);
}

main();
