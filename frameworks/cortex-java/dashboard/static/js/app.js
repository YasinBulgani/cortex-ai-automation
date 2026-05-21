// =====================================================
//  Cortex Otomasyon Dashboard - frontend
// =====================================================

const API = (path, opts = {}) =>
  fetch(path, { headers: { 'Content-Type': 'application/json' }, ...opts })
    .then(async (r) => {
      const txt = await r.text();
      try { return JSON.parse(txt); } catch { return txt; }
    });

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const VIEW_TITLES = {
  overview:    ['Genel Bakis',          'cortex-test.bgtsai.com'],
  runner:      ['Test Kosumu',          'Maven Cucumber test pipeline'],
  results:     ['Sonuclar',             'En son cucumber.json verisi'],
  screenshots: ['Ekran Goruntuleri',    'Senaryo + adim bazinda gorseller'],
  ai:          ['AI Hata Analizi',      'Hata mesajini siniflandir, oneri al'],
  config:      ['Konfigurasyon',        'Aktif config.properties'],
};

let pieChart = null;
let barChart = null;
let currentRunId = null;
let currentSource = null;

// ---------- Init ----------

document.addEventListener('DOMContentLoaded', () => {
  bindNav();
  bindActions();
  refreshAll();
  setInterval(refreshHealth, 8000);
});

function bindNav() {
  $$('.nav-btn').forEach((btn) => {
    btn.addEventListener('click', () => switchView(btn.dataset.view));
  });
}

function switchView(view) {
  $$('.nav-btn').forEach((b) => b.classList.toggle('active', b.dataset.view === view));
  $$('.view').forEach((v) => v.classList.toggle('active', v.dataset.view === view));
  const [title, sub] = VIEW_TITLES[view] || ['', ''];
  $('#view-title').textContent = title;
  $('#view-subtitle').textContent = sub;
  if (view === 'screenshots') loadScreenshots();
  if (view === 'config') loadConfig();
  if (view === 'results') loadResults();
}

function bindActions() {
  $('#refresh-btn').addEventListener('click', refreshAll);
  $('#run-btn').addEventListener('click', startRun);
  $('#stop-btn').addEventListener('click', stopRun);
  $('#ai-submit').addEventListener('click', submitAi);
  const cleanupBtn = $('#cleanup-browsers-btn');
  if (cleanupBtn) cleanupBtn.addEventListener('click', cleanupBrowsers);
}

// Kill orphan Playwright Chromium processes from previous interrupted runs.
async function cleanupBrowsers() {
  const btn = $('#cleanup-browsers-btn');
  if (!btn) return;
  const origText = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Temizleniyor…';
  try {
    const r = await fetch('/api/cortex/recorder/cleanup', { method: 'POST' });
    const j = await r.json();
    if (j.ok) {
      const n = j.killed || 0;
      btn.textContent = n > 0 ? `✓ ${n} tarayici kapatildi` : '✓ Acik tarayici yoktu';
      btn.classList.add('ok-flash');
    } else {
      btn.textContent = '✗ ' + (j.error || 'Hata');
      btn.classList.add('err-flash');
    }
  } catch (e) {
    btn.textContent = '✗ Baglanti hatasi';
    btn.classList.add('err-flash');
  } finally {
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = origText;
      btn.classList.remove('ok-flash', 'err-flash');
    }, 4000);
  }
}

// ---------- Health ----------

async function refreshHealth() {
  try {
    const h = await API('/api/health');
    const pill = $('#health-pill');
    pill.textContent = h.ok ? `online · ${h.active_runs} kosum` : 'offline';
    pill.classList.toggle('ok', h.ok);
    pill.classList.toggle('err', !h.ok);
    $('#version-tag').textContent = `v${h.version || '—'}`;
  } catch {
    const pill = $('#health-pill');
    pill.textContent = 'offline';
    pill.classList.remove('ok');
    pill.classList.add('err');
  }
}

async function refreshAll() {
  refreshHealth();
  await Promise.all([loadFeatures(), loadResults(), loadRuns()]);
}

// ---------- Features ----------

async function loadFeatures() {
  try {
    const feats = await API('/api/features');
    const sel = $('#feature-select');
    sel.innerHTML = '<option value="">— Tumu —</option>';
    feats.forEach((f) => {
      const opt = document.createElement('option');
      opt.value = f.relative;
      opt.textContent = `${f.folder}/${f.name}`;
      sel.appendChild(opt);
    });
  } catch (e) {
    console.error('Features load failed', e);
  }
}

// ---------- Results / charts ----------

async function loadResults() {
  try {
    const data = await API('/api/results');
    if (!data.available) {
      $('#results-tree').textContent = data.reason || 'Sonuc yok.';
      updateKpis({ total: 0, passed: 0, failed: 0, skipped: 0, pass_rate: 0, duration_seconds: 0 });
      drawCharts({ total: 0, passed: 0, failed: 0, skipped: 0 }, []);
      return;
    }
    updateKpis(data.summary);
    drawCharts(data.summary, data.features);
    renderResultsTree(data.features);
  } catch (e) {
    console.error('Results load failed', e);
  }
}

function updateKpis(s) {
  $('#kpi-total').textContent = s.total;
  $('#kpi-passed').textContent = s.passed;
  $('#kpi-failed').textContent = s.failed;
  $('#kpi-skipped').textContent = s.skipped;
  $('#kpi-rate').textContent = `${s.pass_rate || 0}%`;
  $('#kpi-duration').textContent = formatDuration(s.duration_seconds || 0);
}

function formatDuration(secs) {
  if (secs < 60) return `${secs.toFixed(1)}s`;
  const m = Math.floor(secs / 60);
  const s = Math.round(secs % 60);
  return `${m}m ${s}s`;
}

function drawCharts(summary, features) {
  const ctxPie = $('#chart-pie');
  const ctxBar = $('#chart-bar');
  if (!ctxPie || !ctxBar) return;

  const baseOpts = {
    responsive: true,
    plugins: {
      legend: { labels: { color: '#8b95b7', font: { size: 11 } } },
    },
  };

  if (pieChart) pieChart.destroy();
  pieChart = new Chart(ctxPie, {
    type: 'doughnut',
    data: {
      labels: ['Basarili', 'Basarisiz', 'Atlanan'],
      datasets: [{
        data: [summary.passed, summary.failed, summary.skipped],
        backgroundColor: ['#2ecc71', '#ff4f70', '#f39c12'],
        borderColor: '#0b0f1a',
        borderWidth: 2,
      }],
    },
    options: { ...baseOpts, cutout: '60%' },
  });

  const labels = features.map((f) => f.name || f.uri || '?').slice(0, 12);
  const pass = features.map((f) => f.scenarios.filter((s) => s.status === 'passed').length).slice(0, 12);
  const fail = features.map((f) => f.scenarios.filter((s) => s.status === 'failed').length).slice(0, 12);
  const skip = features.map((f) => f.scenarios.filter((s) => s.status === 'skipped').length).slice(0, 12);

  if (barChart) barChart.destroy();
  barChart = new Chart(ctxBar, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Basarili',  data: pass, backgroundColor: '#2ecc71' },
        { label: 'Basarisiz', data: fail, backgroundColor: '#ff4f70' },
        { label: 'Atlanan',   data: skip, backgroundColor: '#f39c12' },
      ],
    },
    options: {
      ...baseOpts,
      scales: {
        x: { stacked: true, ticks: { color: '#8b95b7', font: { size: 10 } } },
        y: { stacked: true, ticks: { color: '#8b95b7', font: { size: 10 } } },
      },
    },
  });
}

function renderResultsTree(features) {
  const root = $('#results-tree');
  if (!features.length) { root.textContent = 'Henuz sonuc yok.'; return; }
  root.innerHTML = '';
  features.forEach((feat) => {
    const block = document.createElement('div');
    block.className = 'feature-block';

    const passed = feat.scenarios.filter((s) => s.status === 'passed').length;
    const failed = feat.scenarios.filter((s) => s.status === 'failed').length;
    const skipped = feat.scenarios.filter((s) => s.status === 'skipped').length;

    block.innerHTML = `
      <div class="feature-header">
        <span>${escapeHtml(feat.name || feat.uri)}</span>
        <span class="muted">${passed}P / ${failed}F / ${skipped}S</span>
      </div>
    `;

    feat.scenarios.forEach((sc) => {
      const row = document.createElement('div');
      row.className = 'scenario-row';
      const tagStr = (sc.tags || []).join(' ');
      row.innerHTML = `
        <span>${escapeHtml(sc.name)} <span class="muted">${escapeHtml(tagStr)} · ${sc.duration_ms || 0}ms</span></span>
        <span class="status ${sc.status}">${sc.status}</span>
      `;
      block.appendChild(row);
      if (sc.status === 'failed' && sc.failed_step) {
        const det = document.createElement('div');
        det.className = 'fail-detail';
        det.textContent = `${sc.failed_step.name}\n${sc.failed_step.error}`;
        block.appendChild(det);
      }
    });

    root.appendChild(block);
  });
}

// ---------- Runs ----------

async function loadRuns() {
  try {
    const runs = await API('/api/runs');
    const lr = $('#last-run');
    if (!runs.length) { lr.textContent = 'Henuz kosum yok.'; return; }
    const r = runs[0];
    lr.innerHTML = `
      <div><strong>ID:</strong> <code>${r.id}</code></div>
      <div><strong>Durum:</strong> <span class="status ${r.exit_code === 0 ? 'passed' : (r.status === 'running' ? 'skipped' : 'failed')}">${r.status}</span></div>
      <div><strong>Baslangic:</strong> ${r.started_at || '-'}</div>
      <div><strong>Bitis:</strong> ${r.finished_at || '-'}</div>
      <div><strong>Feature:</strong> ${escapeHtml(r.feature || '— tumu —')}</div>
      <div><strong>Tag:</strong> ${escapeHtml(r.tag || '—')}</div>
    `;
  } catch (e) {
    console.error('runs', e);
  }
}

async function startRun() {
  const feature = $('#feature-select').value || null;
  const tag = $('#tag-input').value.trim() || null;
  $('#log-out').textContent = '';
  $('#run-state').textContent = 'baslatiliyor';

  try {
    const res = await API('/api/run', {
      method: 'POST',
      body: JSON.stringify({ feature, tag }),
    });
    if (res.error) {
      $('#run-state').textContent = 'hata';
      appendLog(`ERROR: ${res.error}`, 'line-err');
      return;
    }
    currentRunId = res.run_id;
    $('#run-id').textContent = `run #${currentRunId}`;
    $('#run-btn').disabled = true;
    $('#stop-btn').disabled = false;
    openLogStream(currentRunId);
  } catch (e) {
    $('#run-state').textContent = 'hata';
    appendLog(`ERROR: ${e.message}`, 'line-err');
  }
}

function openLogStream(runId) {
  if (currentSource) currentSource.close();
  currentSource = new EventSource(`/api/run/${runId}/stream`);
  currentSource.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data);
      if (data.event === 'end') {
        $('#run-state').textContent = data.status;
        $('#run-btn').disabled = false;
        $('#stop-btn').disabled = true;
        currentSource.close();
        loadResults();
        loadRuns();
        return;
      }
      if (data.line !== undefined) {
        appendLog(data.line, lineClass(data.line));
        $('#run-state').textContent = 'calisiyor';
      }
    } catch {}
  };
  currentSource.onerror = () => {
    appendLog('Stream baglantisi koptu.', 'line-warn');
  };
}

function appendLog(line, cls = '') {
  const out = $('#log-out');
  const span = document.createElement('span');
  if (cls) span.className = cls;
  span.textContent = line + '\n';
  out.appendChild(span);
  out.scrollTop = out.scrollHeight;
}

function lineClass(line) {
  const l = (line || '').toLowerCase();
  if (l.includes('error') || l.includes('failed') || l.includes('exception')) return 'line-err';
  if (l.includes('warn')) return 'line-warn';
  if (l.includes('build success') || l.includes('passed') || l.includes('ok')) return 'line-ok';
  return '';
}

async function stopRun() {
  if (!currentRunId) return;
  await API(`/api/run/${currentRunId}/stop`, { method: 'POST' });
}

// ---------- Screenshots ----------

async function loadScreenshots() {
  const grid = $('#shots-grid');
  grid.textContent = 'Yukleniyor...';
  try {
    const shots = await API('/api/screenshots');
    if (!shots.length) { grid.textContent = 'Henuz ekran goruntusu yok.'; return; }
    grid.innerHTML = '';
    shots.forEach((s) => {
      const div = document.createElement('div');
      div.className = 'shot';
      div.innerHTML = `
        <img loading="lazy" src="${s.url}" alt="${escapeHtml(s.name)}" />
        <div class="caption">
          <div>${escapeHtml(s.folder)}/${escapeHtml(s.name)}</div>
          <div class="muted">${s.size_kb} KB</div>
        </div>
      `;
      div.addEventListener('click', () => openModal(s.url));
      grid.appendChild(div);
    });
  } catch (e) {
    grid.textContent = 'Yuklenemedi.';
  }
}

function openModal(src) {
  let modal = $('#shot-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'shot-modal';
    modal.className = 'modal';
    modal.innerHTML = '<img />';
    modal.addEventListener('click', () => modal.classList.remove('show'));
    document.body.appendChild(modal);
  }
  modal.querySelector('img').src = src;
  modal.classList.add('show');
}

// ---------- AI ----------

async function submitAi() {
  const error = $('#ai-error').value.trim();
  if (!error) return;
  const payload = {
    error_message: error,
    scenario: $('#ai-scenario').value,
    step: $('#ai-step').value,
  };
  const res = await API('/api/classify_error', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  const box = $('#ai-result');
  box.classList.add('show');
  box.innerHTML = `
    <span class="label">Tahmin edilen kategori</span>
    <h4>${escapeHtml(res.predicted_label || 'unknown')}</h4>
    <span class="label">Oneri</span>
    <p>${escapeHtml(res.suggestion || '—')}</p>
  `;
}

// ---------- Config ----------

async function loadConfig() {
  const tbody = $('#config-table tbody');
  tbody.innerHTML = '<tr><td colspan="2">Yukleniyor...</td></tr>';
  try {
    const cfg = await API('/api/config');
    const rows = Object.entries(cfg);
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="2">Config bos.</td></tr>';
      return;
    }
    tbody.innerHTML = '';
    rows.forEach(([k, v]) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="key">${escapeHtml(k)}</td><td>${escapeHtml(v)}</td>`;
      tbody.appendChild(tr);
    });
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="2">Yuklenemedi.</td></tr>';
  }
}

// ---------- Utils ----------

function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}


/* ════════════════════════════════════════════════════════════════════════
   IDE  —  file tree + tabs + CodeMirror editor
   ════════════════════════════════════════════════════════════════════════ */

(function initIDE() {
  const treeContainer = document.getElementById('tree-container');
  const tabBar        = document.getElementById('editor-tabs');
  const empty         = document.getElementById('editor-empty');
  const textarea      = document.getElementById('editor-textarea');
  const statusPath    = document.getElementById('status-path');
  const statusLang    = document.getElementById('status-lang');
  const statusPos     = document.getElementById('status-pos');
  const statusDirty   = document.getElementById('status-dirty');
  const saveBtn       = document.getElementById('editor-save');
  const refreshBtn    = document.getElementById('tree-refresh');
  const newBtn        = document.getElementById('tree-new');

  if (!treeContainer) return; // section not on page

  /** state: tabs = [{path, lang, original, current, cm?}], activeIdx */
  const state = { tabs: [], activeIdx: -1, tree: [], collapsed: new Set() };
  let editor = null;

  const langMap = {
    gherkin: 'gherkin',
    json: { name: 'javascript', json: true },
    java: 'text/x-java',
    xml: 'application/xml',
    yaml: 'yaml',
    markdown: 'markdown',
    properties: 'properties',
    bash: 'shell',
    bat: 'shell',
    sql: 'text/x-sql',
    html: 'htmlmixed',
    css: 'css',
    javascript: 'javascript',
    typescript: { name: 'javascript', typescript: true },
    python: 'python',
    text: null,
  };

  /* ── Tree ──────────────────────────────────────────────────────────── */

  async function loadTree() {
    treeContainer.textContent = 'Yukleniyor...';
    try {
      const r = await fetch('/api/cortex/files/tree');
      state.tree = await r.json();
      renderTree();
    } catch (e) {
      treeContainer.innerHTML = `<div style="color:#ff5078;padding:8px">Hata: ${e}</div>`;
    }
  }

  function renderTree() {
    treeContainer.innerHTML = '';
    state.tree.forEach((root) => treeContainer.appendChild(renderNode(root, 0)));
  }

  function renderNode(node, depth) {
    const wrapper = document.createElement('div');
    if (node.type === 'dir') {
      const isCollapsed = state.collapsed.has(node.path) && depth > 0;
      wrapper.className = 'tree-node-wrap ' + (isCollapsed ? 'tree-collapsed' : '');
      const row = document.createElement('div');
      row.className = 'tree-node dir';
      row.dataset.path = node.path;
      row.innerHTML = `
        <span class="tree-icon">${isCollapsed ? '▶' : '▼'}</span>
        <span class="tree-label">📁 ${escapeHtml(node.name)}</span>
      `;
      row.addEventListener('click', (e) => {
        e.stopPropagation();
        if (isCollapsed) state.collapsed.delete(node.path);
        else state.collapsed.add(node.path);
        renderTree();
      });
      wrapper.appendChild(row);
      const children = document.createElement('div');
      children.className = 'tree-children';
      (node.children || []).forEach((c) => children.appendChild(renderNode(c, depth + 1)));
      wrapper.appendChild(children);
    } else {
      const row = document.createElement('div');
      row.className = 'tree-node file';
      row.dataset.path = node.path;
      row.innerHTML = `
        <span class="tree-icon">${iconFor(node.name)}</span>
        <span class="tree-label">${escapeHtml(node.name)}</span>
      `;
      if (!node.editable) {
        row.style.opacity = '0.45';
        row.title = 'Non-editable';
      }
      row.addEventListener('click', () => openFile(node.path));
      const activeTab = state.tabs[state.activeIdx];
      if (activeTab && activeTab.path === node.path) row.classList.add('active');
      wrapper.appendChild(row);
    }
    return wrapper;
  }

  function iconFor(name) {
    const ext = (name.split('.').pop() || '').toLowerCase();
    return {
      feature: '🥒', json: '🔑', java: '☕', xml: '📰',
      yml: '⚙️', yaml: '⚙️', md: '📘', properties: '⚙️',
      sh: '💻', bat: '💻', sql: '🗄', html: '🌐', css: '🎨',
      js: '📜', ts: '📜', py: '🐍', txt: '📄',
    }[ext] || '📄';
  }

  /* ── Editor ───────────────────────────────────────────────────────── */

  function ensureEditor() {
    if (editor) return editor;
    editor = CodeMirror.fromTextArea(textarea, {
      lineNumbers: true,
      theme: 'dracula',
      autoCloseBrackets: true,
      matchBrackets: true,
      indentUnit: 2,
      tabSize: 2,
      lineWrapping: false,
      extraKeys: {
        'Cmd-S':   () => saveActive(),
        'Ctrl-S':  () => saveActive(),
        'Cmd-W':   () => closeTab(state.activeIdx),
        'Ctrl-W':  () => closeTab(state.activeIdx),
      },
    });
    editor.on('change', () => {
      const t = state.tabs[state.activeIdx];
      if (!t) return;
      t.current = editor.getValue();
      const dirty = t.current !== t.original;
      t.dirty = dirty;
      statusDirty.textContent = dirty ? '● kaydedilmedi' : '';
      saveBtn.disabled = !dirty;
      renderTabs();
    });
    editor.on('cursorActivity', () => {
      const c = editor.getCursor();
      statusPos.textContent = `${c.line + 1}:${c.ch + 1}`;
    });
    return editor;
  }

  /* ── Open / Close / Save ──────────────────────────────────────────── */

  async function openFile(path) {
    // Already open?
    const existingIdx = state.tabs.findIndex((t) => t.path === path);
    if (existingIdx >= 0) {
      activateTab(existingIdx);
      return;
    }
    try {
      const r = await fetch('/api/cortex/files/read?path=' + encodeURIComponent(path));
      if (!r.ok) {
        const err = await r.json().catch(() => ({ error: r.statusText }));
        alert('Acilamadi: ' + (err.error || r.statusText));
        return;
      }
      const j = await r.json();
      state.tabs.push({
        path,
        lang: j.language,
        original: j.content,
        current: j.content,
        dirty: false,
      });
      activateTab(state.tabs.length - 1);
    } catch (e) {
      alert('Hata: ' + e);
    }
  }

  function activateTab(idx) {
    state.activeIdx = idx;
    const t = state.tabs[idx];
    if (!t) {
      empty.style.display = 'grid';
      saveBtn.disabled = true;
      statusPath.textContent = '—';
      statusLang.textContent = '—';
      statusDirty.textContent = '';
      renderTabs();
      renderTree();
      return;
    }
    empty.style.display = 'none';
    ensureEditor();
    editor.setOption('mode', langMap[t.lang] || null);
    editor.setValue(t.current);
    editor.refresh();
    editor.focus();
    statusPath.textContent = t.path;
    statusLang.textContent = t.lang;
    statusDirty.textContent = t.dirty ? '● kaydedilmedi' : '';
    saveBtn.disabled = !t.dirty;
    renderTabs();
    renderTree();
  }

  function closeTab(idx) {
    const t = state.tabs[idx];
    if (!t) return;
    if (t.dirty && !confirm(`${t.path} kaydedilmedi. Yine de kapatilsin mi?`)) return;
    state.tabs.splice(idx, 1);
    if (state.tabs.length === 0) activateTab(-1);
    else activateTab(Math.min(idx, state.tabs.length - 1));
  }

  async function saveActive() {
    const t = state.tabs[state.activeIdx];
    if (!t || !t.dirty) return;
    try {
      const r = await fetch('/api/cortex/files/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: t.path, content: t.current }),
      });
      const j = await r.json();
      if (!r.ok || !j.ok) {
        alert('Kaydedilemedi: ' + (j.error || r.statusText));
        return;
      }
      t.original = t.current;
      t.dirty = false;
      statusDirty.textContent = '✓ kaydedildi';
      setTimeout(() => { if (statusDirty.textContent === '✓ kaydedildi') statusDirty.textContent = ''; }, 1500);
      saveBtn.disabled = true;
      renderTabs();
    } catch (e) {
      alert('Hata: ' + e);
    }
  }

  /* ── Tabs ─────────────────────────────────────────────────────────── */

  function renderTabs() {
    tabBar.innerHTML = '';
    state.tabs.forEach((t, i) => {
      const el = document.createElement('div');
      el.className = 'ide-tab' + (i === state.activeIdx ? ' active' : '') + (t.dirty ? ' dirty' : '');
      el.innerHTML = `
        <span class="tree-icon">${iconFor(t.path)}</span>
        <span>${escapeHtml(t.path.split('/').pop())}</span>
        <span class="close-x" title="Kapat">✕</span>
      `;
      el.addEventListener('click', (e) => {
        if (e.target.classList.contains('close-x')) { closeTab(i); return; }
        activateTab(i);
      });
      tabBar.appendChild(el);
    });
  }

  /* ── New file dialog ──────────────────────────────────────────────── */

  newBtn?.addEventListener('click', async () => {
    const path = prompt(
      'Yeni dosya yolu (root/path/file.feature):\n\n' +
      'Ornek:\n' +
      '  projects/cortex/features/my-test.feature\n' +
      '  recordings/my-recording.feature\n' +
      '  shared/locators/common-extra.json'
    );
    if (!path) return;
    try {
      const r = await fetch('/api/cortex/files/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, kind: 'file' }),
      });
      const j = await r.json();
      if (!j.ok) { alert('Olusturulamadi: ' + j.error); return; }
      await loadTree();
      openFile(path);
    } catch (e) {
      alert('Hata: ' + e);
    }
  });

  refreshBtn?.addEventListener('click', loadTree);
  saveBtn?.addEventListener('click', saveActive);

  /* ── Lifecycle: load on first show ────────────────────────────────── */

  // Initial load when the IDE tab is opened
  document.querySelectorAll('.nav-btn').forEach((b) => {
    if (b.dataset.view === 'ide') {
      b.addEventListener('click', () => {
        if (state.tree.length === 0) loadTree();
        // Refresh CodeMirror layout
        setTimeout(() => editor && editor.refresh(), 50);
      });
    }
  });
})();
