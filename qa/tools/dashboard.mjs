#!/usr/bin/env node
/**
 * qa/tools/dashboard.mjs
 *
 * Builds a self-contained HTML dashboard from qa/cases, qa/runs, qa/coverage.
 * No external dependencies — inline CSS + vanilla JS for filtering.
 *
 * Output: qa/coverage/dashboard.html  (or --out=...)
 *
 * Usage:
 *   node qa/tools/dashboard.mjs
 *   node qa/tools/dashboard.mjs --out=reports/qa-dashboard/index.html
 */

import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { parseArgs } from "node:util";
import { QA_ROOT, loadAllTestCases, loadAllRuns, loadAllRequirements, loadAllPlans } from "./lib/files.mjs";

const { values: args } = parseArgs({
  options: { out: { type: "string" } },
});

const outPath = args.out
  ? path.resolve(QA_ROOT, "..", args.out)
  : path.join(QA_ROOT, "coverage", "dashboard.html");

const tcs = (await loadAllTestCases()).filter((t) => t.data);
const runs = (await loadAllRuns()).filter((r) => r.data);
const reqs = (await loadAllRequirements()).filter((r) => r.data);
const plans = (await loadAllPlans()).filter((p) => p.data);

const totalTcs = tcs.length;
const automatedCount = tcs.filter((t) => t.data.automation?.status === "automated").length;
const automationPct = totalTcs > 0 ? Math.round((automatedCount / totalTcs) * 100) : 0;
const priorityCounts = { P0: 0, P1: 0, P2: 0, P3: 0 };
for (const t of tcs) priorityCounts[t.data.priority] = (priorityCounts[t.data.priority] || 0) + 1;

const suites = {};
for (const t of tcs) {
  const s = t.data.suite;
  suites[s] ??= { total: 0, automated: 0, P0: 0, P1: 0, P2: 0, P3: 0 };
  suites[s].total++;
  if (t.data.automation?.status === "automated") suites[s].automated++;
  suites[s][t.data.priority]++;
}

const sortedRuns = runs
  .slice()
  .sort((a, b) => (b.data.started || "").localeCompare(a.data.started || ""));
const recentRuns = sortedRuns.slice(0, 10);

const lastResultByTc = new Map();
for (const r of runs.slice().sort((a, b) => (a.data.started || "").localeCompare(b.data.started || ""))) {
  for (const res of r.data.results || []) {
    lastResultByTc.set(res.tc, { runId: r.data.id, status: res.status, started: r.data.started });
  }
}

const lastStatusCounts = { pass: 0, fail: 0, blocked: 0, skipped: 0, untested: 0, never: 0 };
for (const t of tcs) {
  const last = lastResultByTc.get(t.data.id);
  if (!last) lastStatusCounts.never++;
  else lastStatusCounts[last.status] = (lastStatusCounts[last.status] || 0) + 1;
}

const tcRows = tcs.map((t) => {
  const last = lastResultByTc.get(t.data.id);
  return {
    id: t.data.id,
    title: t.data.title,
    suite: t.data.suite,
    priority: t.data.priority,
    type: (t.data.type || []).join("+"),
    auto: t.data.automation?.status || "unknown",
    lastRun: last?.runId || "",
    lastStatus: last?.status || "",
    openDefects: (t.data.open_defects || []).length,
  };
});

const generatedAt = new Date().toISOString();

const html = `<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>qa/ — Cortex AI Automation</title>
<style>
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;margin:0;background:#0b0d10;color:#e6e8eb;font-size:14px;line-height:1.5}
header{padding:24px 32px;border-bottom:1px solid #1f2329;background:#11141a;display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:12px}
h1{margin:0;font-size:20px;font-weight:600}
.meta{color:#8a929c;font-size:12px}
main{max-width:1400px;margin:0 auto;padding:24px 32px}
section{margin-bottom:36px}
section>h2{font-size:13px;text-transform:uppercase;letter-spacing:0.08em;color:#8a929c;font-weight:600;margin:0 0 12px 0;padding-bottom:8px;border-bottom:1px solid #1f2329}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.kpi{background:#11141a;border:1px solid #1f2329;border-radius:8px;padding:16px;display:flex;flex-direction:column;gap:6px}
.kpi-label{font-size:11px;color:#8a929c;text-transform:uppercase;letter-spacing:0.06em}
.kpi-value{font-size:28px;font-weight:600;font-variant-numeric:tabular-nums}
.kpi-sub{font-size:12px;color:#a8b1bd}
.kpi.good .kpi-value{color:#3fb950}
.kpi.warn .kpi-value{color:#d29922}
.kpi.bad .kpi-value{color:#f85149}
table{width:100%;border-collapse:collapse;background:#11141a;border:1px solid #1f2329;border-radius:8px;overflow:hidden}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #1f2329;font-size:13px}
th{background:#0f1217;font-size:11px;text-transform:uppercase;letter-spacing:0.06em;color:#8a929c;font-weight:600;position:sticky;top:0}
tr:last-child td{border-bottom:none}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.04em}
.b-P0{background:#5a1e1e;color:#ffb4ad}
.b-P1{background:#5a3e1e;color:#ffd29c}
.b-P2{background:#2e3a4e;color:#a8c6f0}
.b-P3{background:#2a2e34;color:#a8b1bd}
.s-pass{background:#0d3a18;color:#3fb950}
.s-fail{background:#4a1414;color:#f85149}
.s-blocked{background:#4a3818;color:#d29922}
.s-skipped{background:#2a2e34;color:#a8b1bd}
.s-untested{background:#1f2329;color:#6e7682}
.a-automated{background:#0d3a18;color:#3fb950}
.a-not-automated{background:#1f2329;color:#a8b1bd}
.a-in-progress{background:#4a3818;color:#d29922}
.a-out-of-scope{background:#2a2e34;color:#6e7682}
.bar-container{position:relative;height:6px;background:#1f2329;border-radius:3px;overflow:hidden}
.bar-fill{position:absolute;top:0;left:0;height:100%;background:linear-gradient(90deg,#3fb950,#56d364);transition:width 0.3s}
.controls{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.controls input,.controls select{background:#11141a;border:1px solid #1f2329;border-radius:6px;padding:6px 12px;color:#e6e8eb;font-size:13px;font-family:inherit}
.controls input{flex:1;min-width:200px}
.empty{text-align:center;padding:32px;color:#6e7682;font-style:italic}
.run-row{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid #1f2329;background:#11141a}
.run-row:first-child{border-top-left-radius:8px;border-top-right-radius:8px}
.run-row:last-child{border-bottom-left-radius:8px;border-bottom-right-radius:8px;border-bottom:none}
.run-bar{display:flex;height:8px;width:160px;border-radius:4px;overflow:hidden;background:#1f2329}
.run-bar>div{height:100%}
.run-meta{display:flex;gap:16px;align-items:center}
footer{padding:24px 32px;color:#6e7682;font-size:12px;text-align:center;border-top:1px solid #1f2329;margin-top:48px}
</style>
</head>
<body>
<header>
  <div>
    <h1>qa/ — Cortex AI Automation</h1>
    <div class="meta">Test Management Dashboard</div>
  </div>
  <div class="meta">Generated: ${generatedAt}</div>
</header>
<main>

<section>
  <h2>Key Metrics</h2>
  <div class="kpis">
    <div class="kpi"><span class="kpi-label">Total TC</span><span class="kpi-value">${totalTcs}</span><span class="kpi-sub">${Object.keys(suites).length} suite</span></div>
    <div class="kpi ${automationPct >= 70 ? "good" : automationPct >= 40 ? "warn" : "bad"}"><span class="kpi-label">Automation</span><span class="kpi-value">${automationPct}%</span><span class="kpi-sub">${automatedCount} of ${totalTcs} automated</span></div>
    <div class="kpi"><span class="kpi-label">P0 Critical</span><span class="kpi-value">${priorityCounts.P0}</span><span class="kpi-sub">P1: ${priorityCounts.P1}, P2: ${priorityCounts.P2}, P3: ${priorityCounts.P3}</span></div>
    <div class="kpi"><span class="kpi-label">Test Runs</span><span class="kpi-value">${runs.length}</span><span class="kpi-sub">last: ${sortedRuns[0]?.data.started?.slice(0, 10) || "—"}</span></div>
    <div class="kpi ${lastStatusCounts.fail > 0 ? "bad" : "good"}"><span class="kpi-label">Last Result — Pass</span><span class="kpi-value">${lastStatusCounts.pass}</span><span class="kpi-sub">fail: ${lastStatusCounts.fail}, blocked: ${lastStatusCounts.blocked}, never run: ${lastStatusCounts.never}</span></div>
    <div class="kpi"><span class="kpi-label">Requirements</span><span class="kpi-value">${reqs.length}</span><span class="kpi-sub">${plans.length} test plans</span></div>
  </div>
</section>

<section>
  <h2>Coverage Matrix (suite × priority)</h2>
  <table>
    <thead><tr><th>Suite</th><th class="num">P0</th><th class="num">P1</th><th class="num">P2</th><th class="num">P3</th><th class="num">Total</th><th class="num">Auto</th><th>Coverage</th></tr></thead>
    <tbody>
      ${Object.keys(suites).sort().map((s) => {
        const m = suites[s];
        const pct = m.total > 0 ? Math.round((m.automated / m.total) * 100) : 0;
        return `<tr>
          <td>${s}</td>
          <td class="num">${m.P0 || 0}</td>
          <td class="num">${m.P1 || 0}</td>
          <td class="num">${m.P2 || 0}</td>
          <td class="num">${m.P3 || 0}</td>
          <td class="num"><strong>${m.total}</strong></td>
          <td class="num">${m.automated}</td>
          <td><div class="bar-container"><div class="bar-fill" style="width:${pct}%"></div></div><span class="meta" style="font-size:11px;margin-left:4px">${pct}%</span></td>
        </tr>`;
      }).join("\n")}
    </tbody>
  </table>
</section>

<section>
  <h2>Recent Runs</h2>
  ${recentRuns.length === 0 ? '<div class="empty">No runs recorded yet. Try <code>npm run run-record</code> or <code>npm run import-results</code>.</div>' :
    recentRuns.map((r) => {
      const s = r.data.summary;
      const total = s?.total || 1;
      const passPct = ((s?.passed || 0) / total) * 100;
      const failPct = ((s?.failed || 0) / total) * 100;
      const blockedPct = ((s?.blocked || 0) / total) * 100;
      const skippedPct = ((s?.skipped || 0) / total) * 100;
      return `<div class="run-row">
        <div>
          <strong>${r.data.id}</strong>
          <div class="meta">plan: ${r.data.plan} · ${r.data.environment?.branch || "?"}@${r.data.environment?.commit || "?"} · ${r.data.environment?.browser || ""} ${r.data.environment?.env || ""}</div>
        </div>
        <div class="run-meta">
          <span class="meta">${s?.passed || 0}/${s?.total || 0}</span>
          <div class="run-bar" title="pass:${s?.passed} fail:${s?.failed} blocked:${s?.blocked} skipped:${s?.skipped}">
            <div style="width:${passPct}%;background:#3fb950"></div>
            <div style="width:${failPct}%;background:#f85149"></div>
            <div style="width:${blockedPct}%;background:#d29922"></div>
            <div style="width:${skippedPct}%;background:#6e7682"></div>
          </div>
          <span class="meta">${r.data.started?.slice(0, 16).replace("T", " ") || ""}</span>
        </div>
      </div>`;
    }).join("\n")}
</section>

<section>
  <h2>All Test Cases (${totalTcs})</h2>
  <div class="controls">
    <input type="text" id="filter" placeholder="Filter by ID, title, suite, tag...">
    <select id="prio-filter"><option value="">All priorities</option><option>P0</option><option>P1</option><option>P2</option><option>P3</option></select>
    <select id="auto-filter"><option value="">All automation</option><option value="automated">Automated</option><option value="not-automated">Not automated</option><option value="in-progress">In progress</option><option value="out-of-scope">Out of scope</option></select>
    <select id="last-filter"><option value="">All last status</option><option value="pass">Pass</option><option value="fail">Fail</option><option value="blocked">Blocked</option><option value="skipped">Skipped</option><option value="">Never run</option></select>
  </div>
  <table id="tc-table">
    <thead><tr><th>ID</th><th>Title</th><th>Suite</th><th>Prio</th><th>Type</th><th>Automation</th><th>Last Run</th><th>Last Status</th><th class="num">Open Defects</th></tr></thead>
    <tbody>
      ${tcRows.map((t) => `<tr data-prio="${t.priority}" data-auto="${t.auto}" data-last="${t.lastStatus}" data-search="${(t.id + " " + t.title + " " + t.suite).toLowerCase()}">
        <td><code>${t.id}</code></td>
        <td>${escapeHtml(t.title)}</td>
        <td>${t.suite}</td>
        <td><span class="badge b-${t.priority}">${t.priority}</span></td>
        <td>${t.type}</td>
        <td><span class="badge a-${t.auto}">${t.auto}</span></td>
        <td><code style="font-size:11px">${t.lastRun}</code></td>
        <td>${t.lastStatus ? `<span class="badge s-${t.lastStatus}">${t.lastStatus}</span>` : "—"}</td>
        <td class="num">${t.openDefects || ""}</td>
      </tr>`).join("\n")}
    </tbody>
  </table>
</section>

</main>
<footer>
  qa/ Dashboard — produced by <code>tools/dashboard.mjs</code> · open-source workflow, no external trackers · ${generatedAt}
</footer>
<script>
const filter = document.getElementById("filter");
const prio = document.getElementById("prio-filter");
const auto = document.getElementById("auto-filter");
const last = document.getElementById("last-filter");
const rows = Array.from(document.querySelectorAll("#tc-table tbody tr"));
function apply() {
  const q = filter.value.toLowerCase();
  const p = prio.value, a = auto.value, l = last.value;
  for (const r of rows) {
    const matchQ = !q || r.dataset.search.includes(q);
    const matchP = !p || r.dataset.prio === p;
    const matchA = !a || r.dataset.auto === a;
    const matchL = l === "" ? true : r.dataset.last === l;
    r.style.display = matchQ && matchP && matchA && matchL ? "" : "none";
  }
}
[filter, prio, auto, last].forEach((el) => el.addEventListener("input", apply));
</script>
</body>
</html>`;

await mkdir(path.dirname(outPath), { recursive: true });
await writeFile(outPath, html, "utf8");
console.log(`✓ ${path.relative(process.cwd(), outPath)}`);
console.log(`  ${totalTcs} TC, ${runs.length} runs, ${reqs.length} requirements, ${plans.length} plans`);

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
