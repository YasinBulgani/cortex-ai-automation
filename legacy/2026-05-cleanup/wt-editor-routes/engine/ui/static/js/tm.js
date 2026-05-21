/* ══════════════════════════════════════════════════════════════════════════
   tm.js — Test Yönetimi (Test Management) Modülü
   Projeler → Modüller → Test Case'ler → Run'lar → Bug'lar → Raporlar
══════════════════════════════════════════════════════════════════════════ */

/* ── State ──────────────────────────────────────────────────────────────── */
const TM = {
  activeProjectId: null,
  activeModuleId: null,
  activeRunId: null,
  projects: [],
  modules: [],
  cases: [],
  runs: [],
  bugs: [],
  aiFile: null,
  aiCases: [],
  chartPassFail: null,
  chartCoverage: null,
};

/* ── Yardımcı ────────────────────────────────────────────────────────────── */
function tmToast(msg, type = 'info') {
  if (typeof toast === 'function') { toast(msg, type); return; }
  const el = document.createElement('div');
  el.style.cssText = `position:fixed;bottom:20px;right:20px;z-index:9999;
    background:var(--bg3);border:1px solid var(--border);border-radius:8px;
    padding:10px 16px;font-size:12px;color:var(--text1)`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

function tmFmt(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('tr-TR');
}

/* ── Init ────────────────────────────────────────────────────────────────── */
async function tmInit() {
  await tmLoadProjects();
  tmSwitchTab('cases', document.getElementById('tmt-cases'));
}

/* ── Sekme Geçişi ────────────────────────────────────────────────────────── */
function tmSwitchTab(tab, btn) {
  document.querySelectorAll('.tm-tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tm-tab-panel').forEach(p => p.classList.remove('active'));
  if (btn) btn.classList.add('active');
  const panel = document.getElementById('tm-panel-' + tab);
  if (panel) panel.classList.add('active');

  if (tab === 'runs' && TM.activeProjectId) tmLoadRuns();
  if (tab === 'bugs' && TM.activeProjectId) tmLoadBugs();
  if (tab === 'report' && TM.activeProjectId) tmLoadReport();
  if (tab === 'ai') tmSyncAiModules();
}

/* ══════════════════════════════════════════════════════════════════════════
   PROJELER
══════════════════════════════════════════════════════════════════════════ */

async function tmLoadProjects() {
  const res = await fetch('/api/tm/projects');
  TM.projects = await res.json();
  tmRenderProjectTree();
}

function tmRenderProjectTree() {
  const el = document.getElementById('tm-project-tree');
  if (!TM.projects.length) {
    el.innerHTML = '<div class="tm-empty">Henüz proje yok.<br>+ Proje butonuna tıklayın.</div>';
    return;
  }
  el.innerHTML = TM.projects.map(p => `
    <div class="tm-tree-project ${TM.activeProjectId === p.id ? 'active' : ''}"
         onclick="tmSelectProject(${p.id})">
      📁 ${p.name}
    </div>
  `).join('');
}

async function tmSelectProject(id) {
  TM.activeProjectId = id;
  TM.activeModuleId = null;
  tmRenderProjectTree();
  await tmLoadModules();
  await tmLoadSprints();
  tmLoadCases();

  const activeTab = document.querySelector('.tm-tab.active');
  if (activeTab) {
    const tab = activeTab.id.replace('tmt-', '');
    if (tab === 'runs') tmLoadRuns();
    if (tab === 'bugs') tmLoadBugs();
    if (tab === 'report') tmLoadReport();
  }
}

function tmOpenProjectModal(editId = null) {
  const p = editId ? TM.projects.find(x => x.id === editId) : null;
  tmShowModal('Proje ' + (editId ? 'Düzenle' : 'Oluştur'), `
    <div class="form-group mb-16">
      <label>Proje Adı *</label>
      <input type="text" id="tm-m-pname" class="select-styled w-full" placeholder="örn. E-Ticaret" value="${p ? p.name : ''}">
    </div>
    <div class="form-group">
      <label>Açıklama</label>
      <textarea id="tm-m-pdesc" class="select-styled w-full" rows="3" placeholder="Proje hakkında kısa açıklama">${p ? (p.description || '') : ''}</textarea>
    </div>
  `, async () => {
    const name = document.getElementById('tm-m-pname').value.trim();
    if (!name) { tmToast('Proje adı gerekli', 'error'); return false; }
    const desc = document.getElementById('tm-m-pdesc').value;
    if (editId) {
      await fetch(`/api/tm/projects/${editId}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({name, description: desc}) });
    } else {
      await fetch('/api/tm/projects', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({name, description: desc}) });
    }
    await tmLoadProjects();
    tmToast('Proje kaydedildi', 'success');
  });
}

/* ══════════════════════════════════════════════════════════════════════════
   MODÜLLER
══════════════════════════════════════════════════════════════════════════ */

async function tmLoadModules() {
  if (!TM.activeProjectId) return;
  const res = await fetch(`/api/tm/projects/${TM.activeProjectId}/modules`);
  TM.modules = await res.json();
  tmRenderModuleSelect();
  tmSyncAiModules();
}

function tmRenderModuleSelect() {
  const sel = document.getElementById('tm-module-select');
  sel.innerHTML = '<option value="">Modül seçin...</option>' +
    TM.modules.map(m => `<option value="${m.id}" ${m.id === TM.activeModuleId ? 'selected' : ''}>${m.name}</option>`).join('');

  const addBtn = document.getElementById('tm-add-case-btn');
  if (addBtn) addBtn.disabled = !TM.activeModuleId;
}

function tmLoadCases() {
  TM.activeModuleId = parseInt(document.getElementById('tm-module-select').value) || null;
  const addBtn = document.getElementById('tm-add-case-btn');
  if (addBtn) addBtn.disabled = !TM.activeModuleId;
  if (!TM.activeModuleId) {
    document.getElementById('tm-cases-list').innerHTML = '<div class="tm-empty">Modül seçin.</div>';
    return;
  }
  tmFetchCases();
}

async function tmFetchCases() {
  if (!TM.activeModuleId) return;
  const res = await fetch(`/api/tm/modules/${TM.activeModuleId}/testcases`);
  TM.cases = await res.json();
  tmRenderCases();
}

function tmRenderCases() {
  const el = document.getElementById('tm-cases-list');
  if (!TM.cases.length) {
    el.innerHTML = '<div class="tm-empty">Bu modülde henüz test case yok.</div>';
    return;
  }
  el.innerHTML = TM.cases.map(c => `
    <div class="tm-case-card">
      <div class="tm-case-header">
        <div class="tm-case-title">${c.title}</div>
        <div class="tm-case-meta">
          <span class="tm-badge tm-badge-${c.priority.toLowerCase()}">${c.priority}</span>
          ${c.tags ? `<span style="font-size:10px;color:var(--text3)">${c.tags}</span>` : ''}
          <button class="btn btn-ghost btn-xs" onclick="tmOpenCaseModal(${c.id})" title="Düzenle">✏️</button>
          <button class="btn btn-danger btn-xs" onclick="tmDeleteCase(${c.id})" title="Sil">🗑</button>
        </div>
      </div>
      ${c.description ? `<div style="font-size:11px;color:var(--text3);margin-bottom:6px">${c.description}</div>` : ''}
      <div class="tm-case-steps">${c.steps.length} adım${c.preconditions ? ' · Ön koşul var' : ''}</div>
    </div>
  `).join('');
}

function tmOpenModuleModal(editId = null) {
  if (!TM.activeProjectId) { tmToast('Önce proje seçin', 'error'); return; }
  const m = editId ? TM.modules.find(x => x.id === editId) : null;
  tmShowModal('Modül ' + (editId ? 'Düzenle' : 'Oluştur'), `
    <div class="form-group mb-16">
      <label>Modül Adı *</label>
      <input type="text" id="tm-m-mname" class="select-styled w-full" placeholder="örn. Login, Ödeme" value="${m ? m.name : ''}">
    </div>
    <div class="form-group">
      <label>Açıklama</label>
      <input type="text" id="tm-m-mdesc" class="select-styled w-full" placeholder="..." value="${m ? (m.description || '') : ''}">
    </div>
  `, async () => {
    const name = document.getElementById('tm-m-mname').value.trim();
    if (!name) { tmToast('Modül adı gerekli', 'error'); return false; }
    const desc = document.getElementById('tm-m-mdesc').value;
    if (editId) {
      await fetch(`/api/tm/modules/${editId}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({name, description: desc}) });
    } else {
      await fetch(`/api/tm/projects/${TM.activeProjectId}/modules`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({name, description: desc}) });
    }
    await tmLoadModules();
    tmToast('Modül kaydedildi', 'success');
  });
}

/* ══════════════════════════════════════════════════════════════════════════
   TEST CASE'LER
══════════════════════════════════════════════════════════════════════════ */

function tmOpenCaseModal(editId = null) {
  if (!TM.activeModuleId) { tmToast('Önce modül seçin', 'error'); return; }
  const c = editId ? TM.cases.find(x => x.id === editId) : null;
  const stepsHtml = (c ? c.steps : []).map((s, i) => tmStepRow(i, s.action, s.expected)).join('');

  tmShowModal('Test Case ' + (editId ? 'Düzenle' : 'Ekle'), `
    <div class="form-group mb-12">
      <label>Başlık *</label>
      <input type="text" id="tc-title" class="select-styled w-full" placeholder="Test case başlığı" value="${c ? c.title : ''}">
    </div>
    <div style="display:flex;gap:12px;margin-bottom:12px">
      <div class="form-group" style="flex:1">
        <label>Öncelik</label>
        <select id="tc-priority" class="select-styled w-full">
          ${['P1','P2','P3'].map(p => `<option ${c && c.priority===p ? 'selected' : ''}>${p}</option>`).join('')}
        </select>
      </div>
      <div class="form-group" style="flex:2">
        <label>Etiketler</label>
        <input type="text" id="tc-tags" class="select-styled w-full" placeholder="smoke, login, ..." value="${c ? (c.tags || '') : ''}">
      </div>
    </div>
    <div class="form-group mb-12">
      <label>Açıklama</label>
      <input type="text" id="tc-desc" class="select-styled w-full" placeholder="..." value="${c ? (c.description || '') : ''}">
    </div>
    <div class="form-group mb-12">
      <label>Ön Koşul</label>
      <input type="text" id="tc-pre" class="select-styled w-full" placeholder="Kullanıcı giriş yapmış olmalı" value="${c ? (c.preconditions || '') : ''}">
    </div>
    <div style="margin-bottom:8px;font-size:12px;font-weight:600;color:var(--text2)">Adımlar</div>
    <div id="tc-steps-list">${stepsHtml}</div>
    <button class="btn btn-ghost btn-sm" style="margin-top:8px" onclick="tcAddStep()">+ Adım Ekle</button>
  `, async () => {
    const title = document.getElementById('tc-title').value.trim();
    if (!title) { tmToast('Başlık gerekli', 'error'); return false; }
    const steps = [];
    document.querySelectorAll('.tc-step-row').forEach(row => {
      const action = row.querySelector('.tc-step-action').value.trim();
      const expected = row.querySelector('.tc-step-expected').value.trim();
      if (action && expected) steps.push({action, expected});
    });
    const payload = {
      title,
      description: document.getElementById('tc-desc').value,
      preconditions: document.getElementById('tc-pre').value,
      priority: document.getElementById('tc-priority').value,
      tags: document.getElementById('tc-tags').value,
      steps
    };
    if (editId) {
      await fetch(`/api/tm/testcases/${editId}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    } else {
      await fetch(`/api/tm/modules/${TM.activeModuleId}/testcases`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    }
    await tmFetchCases();
    tmToast('Test case kaydedildi', 'success');
  }, '640px');
}

function tmStepRow(i, action = '', expected = '') {
  return `<div class="tc-step-row" style="display:flex;gap:8px;margin-bottom:6px;align-items:center">
    <span style="font-size:11px;color:var(--text3);min-width:20px">${i+1}.</span>
    <input type="text" class="tc-step-action select-styled" style="flex:1" placeholder="Aksiyon" value="${action}">
    <input type="text" class="tc-step-expected select-styled" style="flex:1" placeholder="Beklenen Sonuç" value="${expected}">
    <button class="btn btn-danger btn-xs" onclick="this.closest('.tc-step-row').remove()">✕</button>
  </div>`;
}

function tcAddStep() {
  const list = document.getElementById('tc-steps-list');
  const count = list.querySelectorAll('.tc-step-row').length;
  list.insertAdjacentHTML('beforeend', tmStepRow(count));
}

async function tmDeleteCase(id) {
  if (!confirm('Test case silinsin mi?')) return;
  await fetch(`/api/tm/testcases/${id}`, { method: 'DELETE' });
  await tmFetchCases();
  tmToast('Silindi', 'success');
}

/* ══════════════════════════════════════════════════════════════════════════
   SPRINT'LER
══════════════════════════════════════════════════════════════════════════ */

async function tmLoadSprints() {
  if (!TM.activeProjectId) return;
  const res = await fetch(`/api/tm/projects/${TM.activeProjectId}/sprints`);
  const sprints = await res.json();
  const sel = document.getElementById('tm-sprint-select');
  sel.innerHTML = '<option value="">Sprint seçin (opsiyonel)</option>' +
    sprints.map(s => `<option value="${s.id}">${s.name}${s.release_version ? ' · ' + s.release_version : ''}</option>`).join('');
}

function tmOpenSprintModal() {
  if (!TM.activeProjectId) { tmToast('Önce proje seçin', 'error'); return; }
  tmShowModal('Sprint Oluştur', `
    <div class="form-group mb-12">
      <label>Sprint Adı *</label>
      <input type="text" id="sp-name" class="select-styled w-full" placeholder="Sprint 1">
    </div>
    <div class="form-group mb-12">
      <label>Release Versiyonu</label>
      <input type="text" id="sp-release" class="select-styled w-full" placeholder="v1.2.0">
    </div>
    <div style="display:flex;gap:12px">
      <div class="form-group" style="flex:1">
        <label>Başlangıç</label>
        <input type="date" id="sp-start" class="select-styled w-full">
      </div>
      <div class="form-group" style="flex:1">
        <label>Bitiş</label>
        <input type="date" id="sp-end" class="select-styled w-full">
      </div>
    </div>
  `, async () => {
    const name = document.getElementById('sp-name').value.trim();
    if (!name) { tmToast('Sprint adı gerekli', 'error'); return false; }
    await fetch(`/api/tm/projects/${TM.activeProjectId}/sprints`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        name,
        release_version: document.getElementById('sp-release').value,
        start_date: document.getElementById('sp-start').value || null,
        end_date: document.getElementById('sp-end').value || null,
      })
    });
    await tmLoadSprints();
    tmToast('Sprint oluşturuldu', 'success');
  });
}

/* ══════════════════════════════════════════════════════════════════════════
   TEST RUN'LAR
══════════════════════════════════════════════════════════════════════════ */

async function tmLoadRuns() {
  if (!TM.activeProjectId) return;
  const res = await fetch(`/api/tm/projects/${TM.activeProjectId}/runs`);
  TM.runs = await res.json();
  tmRenderRuns();
}

function tmRenderRuns() {
  const el = document.getElementById('tm-runs-list');
  if (!TM.runs.length) {
    el.innerHTML = '<div class="tm-empty">Henüz test run yok.</div>';
    return;
  }
  el.innerHTML = TM.runs.map(r => {
    const stats = r.stats || {};
    const pass = stats['Pass'] || 0;
    const fail = stats['Fail'] || 0;
    const notrun = stats['Not Run'] || 0;
    return `
    <div class="tm-run-card">
      <div>
        <div class="tm-run-title">${r.name}</div>
        <div class="tm-run-meta">${r.sprint_name ? '🏃 ' + r.sprint_name + ' · ' : ''}${tmFmt(r.created_at)} · ${r.status}</div>
      </div>
      <div style="display:flex;gap:12px;align-items:center">
        <div class="tm-run-stats">
          <span class="tm-stat-pass">✓${pass}</span>
          <span class="tm-stat-fail">✗${fail}</span>
          <span class="tm-stat-notrun">—${notrun}</span>
        </div>
        <button class="btn btn-primary btn-sm" onclick="tmOpenRunExec(${r.id})">▶ Çalıştır</button>
        ${r.status !== 'Closed' ? `<button class="btn btn-ghost btn-sm" onclick="tmCloseRun(${r.id})">Kapat</button>` : ''}
      </div>
    </div>`;
  }).join('');
}

function tmOpenRunModal() {
  if (!TM.activeProjectId) { tmToast('Önce proje seçin', 'error'); return; }
  const sprintSel = document.getElementById('tm-sprint-select');
  tmShowModal('Yeni Test Run', `
    <div class="form-group mb-12">
      <label>Run Adı *</label>
      <input type="text" id="run-name" class="select-styled w-full" placeholder="Sprint 1 - Smoke Run">
    </div>
    <div class="form-group">
      <label>Sprint (opsiyonel)</label>
      <select id="run-sprint" class="select-styled w-full">
        ${sprintSel.innerHTML}
      </select>
    </div>
  `, async () => {
    const name = document.getElementById('run-name').value.trim();
    if (!name) { tmToast('Run adı gerekli', 'error'); return false; }
    const res = await fetch(`/api/tm/projects/${TM.activeProjectId}/runs`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ name, sprint_id: document.getElementById('run-sprint').value || null })
    });
    const data = await res.json();
    await tmLoadRuns();
    tmToast('Test run oluşturuldu', 'success');
    tmOpenRunExec(data.id);
  });
}

async function tmOpenRunExec(runId) {
  TM.activeRunId = runId;
  const res = await fetch(`/api/tm/runs/${runId}/results`);
  const results = await res.json();

  tmShowModal('Test Run Çalıştır', `
    <div style="max-height:60vh;overflow-y:auto">
      ${results.map(r => `
        <div style="border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
            <div>
              <div style="font-size:13px;font-weight:600">${r.title}</div>
              <div style="font-size:11px;color:var(--text3)">${r.module_name} · ${r.priority}</div>
            </div>
            <select class="select-styled run-result-status" data-rid="${r.id}" style="width:120px">
              ${['Not Run','Pass','Fail','Blocked'].map(s => `<option ${r.status===s?'selected':''}>${s}</option>`).join('')}
            </select>
          </div>
          <textarea class="select-styled w-full run-result-notes" data-rid="${r.id}" rows="1"
            placeholder="Not (opsiyonel)" style="margin-top:4px;font-size:11px">${r.notes || ''}</textarea>
          ${r.status === 'Fail' ? `<button class="btn btn-danger btn-xs" style="margin-top:6px" onclick="tmOpenBugFromResult(${r.id}, '${r.title.replace(/'/g,"\\'")}')">🐛 Bug Aç</button>` : ''}
        </div>
      `).join('')}
    </div>
  `, async () => {
    const updates = [];
    document.querySelectorAll('.run-result-status').forEach(sel => {
      const rid = sel.dataset.rid;
      const notes = document.querySelector(`.run-result-notes[data-rid="${rid}"]`).value;
      updates.push(fetch(`/api/tm/results/${rid}`, {
        method: 'PUT',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ status: sel.value, notes })
      }));
    });
    await Promise.all(updates);
    await tmLoadRuns();
    tmToast('Sonuçlar kaydedildi', 'success');
  }, '640px', 'Kaydet');
}

async function tmCloseRun(runId) {
  await fetch(`/api/tm/runs/${runId}/close`, { method: 'POST' });
  await tmLoadRuns();
  tmToast('Run kapatıldı', 'success');
}

/* ══════════════════════════════════════════════════════════════════════════
   BUG'LAR
══════════════════════════════════════════════════════════════════════════ */

async function tmLoadBugs() {
  if (!TM.activeProjectId) return;
  const res = await fetch(`/api/tm/projects/${TM.activeProjectId}/bugs`);
  TM.bugs = await res.json();
  tmRenderBugs();
}

function tmRenderBugs() {
  const el = document.getElementById('tm-bugs-list');
  if (!TM.bugs.length) {
    el.innerHTML = '<div class="tm-empty">Henüz bug yok.</div>';
    return;
  }
  el.innerHTML = TM.bugs.map(b => `
    <div class="tm-bug-card sev-${b.severity.toLowerCase()}">
      <div>
        <div style="font-size:13px;font-weight:600">${b.title}</div>
        <div style="font-size:11px;color:var(--text3);margin-top:3px">
          ${b.severity} · ${b.status} · ${tmFmt(b.created_at)}
          ${b.jira_key ? ` · <a href="#" style="color:var(--accent)">${b.jira_key}</a>` : ''}
        </div>
      </div>
      <div style="display:flex;gap:6px;align-items:center">
        ${!b.jira_key ? `<button class="btn btn-ghost btn-xs" onclick="tmPushBugToJira(${b.id})">Jira'ya At</button>` : ''}
        <button class="btn btn-danger btn-xs" onclick="tmDeleteBug(${b.id})">🗑</button>
      </div>
    </div>
  `).join('');
}

function tmOpenBugModal(resultId = null, caseTitle = '') {
  tmShowModal('Bug Ekle', `
    <div class="form-group mb-12">
      <label>Başlık *</label>
      <input type="text" id="bug-title" class="select-styled w-full" value="${caseTitle ? caseTitle + ' - Hata' : ''}">
    </div>
    <div class="form-group mb-12">
      <label>Açıklama</label>
      <textarea id="bug-desc" class="select-styled w-full" rows="3" placeholder="Hata detayı..."></textarea>
    </div>
    <div class="form-group">
      <label>Önem</label>
      <select id="bug-sev" class="select-styled w-full">
        <option>Critical</option><option selected>High</option><option>Medium</option><option>Low</option>
      </select>
    </div>
  `, async () => {
    const title = document.getElementById('bug-title').value.trim();
    if (!title) { tmToast('Başlık gerekli', 'error'); return false; }
    await fetch('/api/tm/bugs', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        title,
        description: document.getElementById('bug-desc').value,
        severity: document.getElementById('bug-sev').value,
        result_id: resultId || null
      })
    });
    await tmLoadBugs();
    tmToast('Bug eklendi', 'success');
  });
}

function tmOpenBugFromResult(resultId, caseTitle) {
  tmOpenBugModal(resultId, caseTitle);
}

async function tmDeleteBug(id) {
  if (!confirm('Bug silinsin mi?')) return;
  await fetch(`/api/tm/bugs/${id}`, { method: 'DELETE' });
  await tmLoadBugs();
}

async function tmPushBugToJira(bugId) {
  const res = await fetch(`/api/jira/bugs/${bugId}/push`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: '{}' });
  const data = await res.json();
  if (data.ok) {
    tmToast(`Jira'ya aktarıldı: ${data.jira_key}`, 'success');
    await tmLoadBugs();
  } else {
    tmToast('Jira hatası: ' + data.error, 'error');
  }
}

/* ══════════════════════════════════════════════════════════════════════════
   AI CASE ÜRETİMİ
══════════════════════════════════════════════════════════════════════════ */

function tmSyncAiModules() {
  const sel = document.getElementById('tm-ai-module-select');
  if (!sel) return;
  sel.innerHTML = '<option value="">Modül seçin...</option>' +
    TM.modules.map(m => `<option value="${m.id}">${m.name}</option>`).join('');
}

function tmAiDrop(e) {
  e.preventDefault();
  document.getElementById('tm-ai-dropzone').classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) tmAiSetFile(file);
}

function tmAiFileSelected(input) {
  if (input.files[0]) tmAiSetFile(input.files[0]);
}

function tmAiSetFile(file) {
  TM.aiFile = file;
  const info = document.getElementById('tm-ai-file-info');
  info.style.display = 'block';
  info.textContent = `📄 ${file.name} (${(file.size/1024).toFixed(1)} KB)`;
  const btn = document.getElementById('tm-ai-extract-btn');
  if (btn) btn.disabled = false;
}

async function tmAiExtract() {
  if (!TM.aiFile) { tmToast('Önce dosya seçin', 'error'); return; }
  const moduleId = document.getElementById('tm-ai-module-select').value;
  if (!moduleId) { tmToast('Hedef modül seçin', 'error'); return; }

  const btn = document.getElementById('tm-ai-extract-btn');
  btn.textContent = '⏳ Analiz ediliyor...';
  btn.disabled = true;

  const fd = new FormData();
  fd.append('file', TM.aiFile);
  fd.append('module_id', moduleId);

  try {
    const res = await fetch('/api/ai/extract-testcases', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    TM.aiCases = data.cases || [];
    tmRenderAiPreview();
  } catch(e) {
    tmToast('Hata: ' + e.message, 'error');
  } finally {
    btn.textContent = '✨ Case\'leri Çıkar';
    btn.disabled = false;
  }
}

function tmRenderAiPreview() {
  const preview = document.getElementById('tm-ai-preview');
  const list = document.getElementById('tm-ai-preview-list');
  if (!TM.aiCases.length) {
    tmToast('Case çıkarılamadı', 'error');
    return;
  }
  preview.style.display = 'block';
  list.innerHTML = TM.aiCases.map((c, i) => `
    <div class="tm-ai-case-item">
      <input type="checkbox" id="ai-case-${i}" checked>
      <div class="tm-ai-case-body">
        <div class="tm-ai-case-title">
          <label for="ai-case-${i}" style="cursor:pointer">${c.title}</label>
          <span class="tm-badge tm-badge-${(c.priority||'P2').toLowerCase()}" style="margin-left:6px">${c.priority || 'P2'}</span>
        </div>
        <div class="tm-ai-case-steps">
          ${(c.steps || []).map((s, si) => `${si+1}. ${s.action} → ${s.expected}`).join('<br>')}
        </div>
      </div>
    </div>
  `).join('');
}

function tmAiSelectAll() {
  document.querySelectorAll('#tm-ai-preview-list input[type=checkbox]').forEach(cb => cb.checked = true);
}

async function tmAiSaveSelected() {
  const moduleId = document.getElementById('tm-ai-module-select').value;
  if (!moduleId) { tmToast('Modül seçin', 'error'); return; }
  const selected = [];
  document.querySelectorAll('#tm-ai-preview-list input[type=checkbox]').forEach((cb, i) => {
    if (cb.checked) selected.push(TM.aiCases[i]);
  });
  if (!selected.length) { tmToast('En az bir case seçin', 'error'); return; }
  const res = await fetch(`/api/tm/modules/${moduleId}/testcases/bulk`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ cases: selected })
  });
  const data = await res.json();
  tmToast(`${data.created} test case kaydedildi`, 'success');
  document.getElementById('tm-ai-preview').style.display = 'none';
  TM.aiCases = [];
  if (parseInt(moduleId) === TM.activeModuleId) tmFetchCases();
}

/* ══════════════════════════════════════════════════════════════════════════
   RAPORLAMA
══════════════════════════════════════════════════════════════════════════ */

async function tmLoadReport() {
  if (!TM.activeProjectId) return;
  const res = await fetch(`/api/tm/projects/${TM.activeProjectId}/report`);
  const data = await res.json();

  // Stat kartları
  const statsEl = document.getElementById('tm-report-stats');
  const stats = data.result_stats || {};
  const pass = stats['Pass'] || 0;
  const fail = stats['Fail'] || 0;
  const total = data.total_cases || 0;
  statsEl.innerHTML = [
    {v: total, l: 'Toplam Case'},
    {v: data.total_runs || 0, l: 'Test Run'},
    {v: pass, l: 'Geçti'},
    {v: fail, l: 'Başarısız'},
    {v: data.bug_count || 0, l: 'Bug'},
  ].map(s => `
    <div class="tm-stat-card">
      <div class="tm-sc-value">${s.v}</div>
      <div class="tm-sc-label">${s.l}</div>
    </div>
  `).join('');

  // Pass/Fail chart
  const pfCtx = document.getElementById('tm-chart-passfail');
  if (pfCtx) {
    if (TM.chartPassFail) TM.chartPassFail.destroy();
    TM.chartPassFail = new Chart(pfCtx, {
      type: 'doughnut',
      data: {
        labels: Object.keys(stats),
        datasets: [{ data: Object.values(stats), backgroundColor: ['#3fb950','#f85149','#ffa600','#388bfd','#8b949e'] }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: '#c9d1d9', font: { size: 11 } } } } }
    });
  }

  // Module coverage chart
  const covCtx = document.getElementById('tm-chart-coverage');
  if (covCtx && data.module_coverage) {
    if (TM.chartCoverage) TM.chartCoverage.destroy();
    TM.chartCoverage = new Chart(covCtx, {
      type: 'bar',
      data: {
        labels: data.module_coverage.map(m => m.name),
        datasets: [{ label: 'Case Sayısı', data: data.module_coverage.map(m => m.case_count), backgroundColor: '#388bfd' }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { ticks: { color: '#8b949e' } }, x: { ticks: { color: '#8b949e' } } }
      }
    });
  }
}

async function tmExportExcel() {
  if (!TM.activeProjectId) return;
  const res = await fetch(`/api/tm/projects/${TM.activeProjectId}/report/excel`);
  if (!res.ok) { tmToast('Excel export hazır değil', 'error'); return; }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = 'test_report.xlsx'; a.click();
}

async function tmExportPDF() {
  tmToast('PDF export yakında eklenecek', 'info');
}

/* ══════════════════════════════════════════════════════════════════════════
   MODAL YARDIMCISI
══════════════════════════════════════════════════════════════════════════ */

function tmShowModal(title, bodyHtml, onConfirm, width = '520px', confirmLabel = 'Kaydet') {
  const existing = document.getElementById('tm-modal-overlay');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.id = 'tm-modal-overlay';
  overlay.style.cssText = `position:fixed;inset:0;background:rgba(0,0,0,.7);backdrop-filter:blur(4px);
    display:flex;align-items:center;justify-content:center;z-index:2000`;

  overlay.innerHTML = `
    <div style="background:var(--bg2);border:1px solid var(--border);border-radius:16px;width:${width};
      max-width:95vw;max-height:90vh;display:flex;flex-direction:column;box-shadow:0 20px 50px rgba(0,0,0,.5)">
      <div style="padding:16px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:14px;font-weight:600;color:var(--text1)">${title}</span>
        <button onclick="document.getElementById('tm-modal-overlay').remove()" style="background:none;border:none;color:var(--text3);font-size:18px;cursor:pointer">✕</button>
      </div>
      <div id="tm-modal-body" style="padding:20px;overflow-y:auto;flex:1">${bodyHtml}</div>
      <div style="padding:14px 20px;border-top:1px solid var(--border);display:flex;justify-content:flex-end;gap:8px">
        <button class="btn btn-ghost" onclick="document.getElementById('tm-modal-overlay').remove()">Vazgeç</button>
        <button class="btn btn-primary" id="tm-modal-confirm">${confirmLabel}</button>
      </div>
    </div>`;

  document.body.appendChild(overlay);

  document.getElementById('tm-modal-confirm').onclick = async () => {
    const result = await onConfirm();
    if (result !== false) overlay.remove();
  };

  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
}
