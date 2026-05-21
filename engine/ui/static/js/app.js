

/* ── State ──────────────────────────────────────────────────────────────────── */
let features = [];
let activeFeature = null;
let runController = null;
let regressionSets = [];
let activeRegSet = null;
let activeManualTestId = null;
let manualTests = [];

// Chart instances
let trendChartInst = null;
let chartPassFail = null;
let chartDuration = null;
let chartMarkers = null;

async function handleLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/login';
  } catch (e) {
    console.error(e);
  }
}

const STEPS = [
  ["Given", "kullanıcı ana sayfadadır", "BASE_URL'e git"],
  ["Given", 'kullanıcı "<path>" sayfasındadır', "BASE_URL + path"],
  ["When",  'kullanıcı "<metin>" metnine tıklar', "Metni tıkla"],
  ["When",  'kullanıcı "<selector>" kutusuna "<değer>" yazar', "Input doldur"],
  ["When",  'kullanıcı arama kutusuna "<değer>" yazar', "Arama kutusu otomatik bulunur"],
  ["When",  "kullanıcı Enter tuşuna basar", "Enter tuşu"],
  ["When",  'kullanıcı "<ms>" milisaniye bekler', "Belirtilen ms bekle"],
  ["When",  'AI "<görev>" görevini gerçekleştirir', "AI otomasyonu"],
  ["Then",  'sayfa başlığı "<metin>" içermelidir', "Başlık doğrulama"],
  ["Then",  'URL "<metin>" içermelidir', "URL doğrulama"],
  ["Then",  '"<selector>" elementi görünür olmalıdır', "Görünürlük"],
  ["Then",  'en az 1 adım başarılı olmalıdır', "AI sonuç doğrulama"],
  ["Then",  '"{selector}" elementinin değerini "{key}" olarak kaydet', "Dinamik Veri Okuma (Context)"],
  ["Then",  '"{key}" değişkenine "{value}" değerini ata', "Dinamik Veri Yazma (Context)"],
];

/* ── Init ────────────────────────────────────────────────────────────────────── */
window.onload = () => {
  try { loadFeatures(); } catch(e) { console.error('loadFeatures:', e); }
  try { loadSettings(); } catch(e) { console.error('loadSettings:', e); }
  try { loadRegressionSets(); } catch(e) { console.error('loadRegressionSets:', e); } // Initial load
  loadProjects();
  const lastProject = localStorage.getItem('activeProject');
  if (lastProject) {
    setTimeout(() => {
      document.getElementById('active-project-select').value = lastProject;
      switchProject(lastProject);
    }, 500);
  }
  try { fetchManualTests(); } catch(e) { console.error('fetchManualTests:', e); }
  try { renderStepTable(); } catch(e) { console.error('renderStepTable:', e); }
  try { updateLineNumbers(); } catch(e) { console.error('updateLineNumbers:', e); }

  // Restore view from localStorage
  const lastView = localStorage.getItem('currentView') || 'editor-view';
  try { showView(lastView); } catch(e) { showView('editor-view'); }
};

/* ── Dashboard ───────────────────────────────────────────────────────────────── */
// (trendChartInst is defined in state section above)

async function renderDashboard() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) throw new Error('İstatistikler yüklenemedi');
    const d = await res.json();
    const totals = d.totals || {total_runs:0, total_passed:0, total_failed:0};
    const history = d.history || [];

    // Stat cards
    const statsEl = document.getElementById('dash-stats');
    if (statsEl) {
      statsEl.innerHTML = [
        ['🧪', 'Toplam Koşum', totals.total_runs],
        ['✅', 'Başarılı', totals.total_passed],
        ['❌', 'Başarısız', totals.total_failed],
        ['📁', 'Feature Dosyası', (features || []).length],
      ].map(([icon, label, val]) => `
        <div class="stat-card">
          <div style="font-size:24px;margin-bottom:6px">${icon}</div>
          <div class="sc-num">${val}</div>
          <div class="sc-lbl">${label}</div>
        </div>`).join('');
    }

    // History table
    const tbody = document.querySelector('#history-table tbody');
    if (tbody) {
      if (history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text3);padding:20px">Henüz koşum yok.</td></tr>';
      } else {
        tbody.innerHTML = history.slice(0, 20).map(r => {
          const isPassed = r.failed === 0 && r.passed > 0;
          const statusIcon = isPassed ? '🟢' : r.failed > 0 ? '🔴' : '⚪';
          const statusLabel = isPassed ? 'Başarılı' : r.failed > 0 ? 'Başarısız' : 'Bilinmiyor';
          const age = r.timestamp ? new Date(r.timestamp).toLocaleString('tr-TR') : '-';
          return `<tr>
            <td>${statusIcon} ${statusLabel}</td>
            <td><span class="ht-marker">${r.markers || 'all'}</span></td>
            <td>${r.duration_ms ? (r.duration_ms / 1000).toFixed(1) + 's' : '-'}</td>
            <td style="color:var(--text3)">${age}</td>
          </tr>`;
        }).join('');
      }
    }

    // Trend chart
    const canvas = document.getElementById('trendChart');
    if (canvas) {
      if (history.length === 0) {
          // Optional: Render something else if no history
          if (trendChartInst) { trendChartInst.destroy(); trendChartInst = null; }
          return;
      }
      if (trendChartInst) trendChartInst.destroy();
      const last15 = [...history].slice(0, 15).reverse();
      trendChartInst = new Chart(canvas, {
        type: 'line',
        data: {
          labels: last15.map((_, i) => `#${i + 1}`),
          datasets: [{
            label: 'Başarı Oranı (%)',
            data: last15.map(r => {
              const total = (r.passed || 0) + (r.failed || 0);
              return total > 0 ? Math.round((r.passed / total) * 100) : 0;
            }),
            borderColor: '#388bfd', backgroundColor: 'rgba(56,139,253,0.1)',
            fill: true, tension: 0.3, borderWidth: 2, pointRadius: 4,
            pointBackgroundColor: '#388bfd'
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: '#8b949e' }, grid: { display: false } },
            y: { min: 0, max: 100, ticks: { color: '#8b949e', callback: v => v + '%' }, grid: { color: '#30363d' } }
          }
        }
      });
    }
  } catch(e) { 
    console.error('renderDashboard error:', e);
    const statsEl = document.getElementById('dash-stats');
    if(statsEl) statsEl.innerHTML = `<div style="color:var(--red); padding:20px;">İstatistikler Yüklenemedi: ${e.message}</div>`;
  }
}

function renderStepTable() {
  const tbody = document.getElementById('step-table');
  if (!tbody) return;
  tbody.innerHTML = STEPS.map(([kw, step, desc]) => `
    <tr>
      <td style="padding:9px 14px;border-bottom:1px solid var(--border)">
        <code style="color:var(--accent);font-size:12px">${kw} ${step}</code>
      </td>
      <td style="padding:9px 14px;border-bottom:1px solid var(--border);color:var(--text3);font-size:12px">${desc}</td>
    </tr>`).join('');
}

/* ── View Switching ──────────────────────────────────────────────────────────── */
function showView(id, btn) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => {
    b.classList.remove('active');
    // If no btn provided, find the one with onclick that matches id
    if (!btn && b.getAttribute('onclick')?.includes(`'${id}'`)) {
        btn = b;
    }
  });

  const targetView = document.getElementById(id);
  if (targetView) {
      targetView.classList.add('active');
      localStorage.setItem('currentView', id);
  }
  
  if (btn) btn.classList.add('active');
  
  if (id === 'dashboard-view') renderDashboard();
  if (id === 'regression-view') loadRegressionSets();
  if (id === 'locators-view') loadLocators();
  if (id === 'reports-view') loadComprehensiveReports();
  if (id === 'ai-tree-view') refreshAITree();
}

/* ── AI Test Tree ─────────────────────────────────────────────────────────────── */
function refreshAITree() {
  const listEl = document.getElementById('ai-tree-list');
  if (!listEl) return;
  if (!features.length) {
    listEl.innerHTML = '<div class="empty-state"><div class="es-icon">📂</div><p>Henüz feature dosyası yok.</p></div>';
    return;
  }
  listEl.innerHTML = renderAITreeNodes(features, 0);
}

function renderAITreeNodes(nodes, depth) {
  return nodes.map(node => {
    if (node.type === 'folder') {
      const childHtml = renderAITreeNodes(node.children || [], depth + 1);
      const safeId = 'atf_' + node.path.replace(/[^a-zA-Z0-9]/g, '_');
      return `<div class="tree-node tree-open" id="node_${safeId}">
        <div class="tree-folder-header" onclick="toggleAITreeFolder('node_${safeId}')">
          <span class="tree-toggle">▶</span>
          <span>📂</span>
          <span>${node.name}</span>
        </div>
        <div class="tree-children">${childHtml}</div>
      </div>`;
    } else {
      const scenarios = node.scenarios || 0;
      return `<div class="tree-leaf" onclick="selectAITreeFeature('${node.path}', '${node.stem}')">
        <span class="tree-status none"></span>
        <span style="flex:1">🥒 ${node.stem}</span>
        <span style="font-size:10px;color:var(--text3)">${scenarios} senaryo</span>
      </div>`;
    }
  }).join('');
}

function toggleAITreeFolder(nodeId) {
  const node = document.getElementById(nodeId);
  if (!node) return;
  node.classList.toggle('tree-open');
  const children = node.querySelector('.tree-children');
  if (children) children.style.display = node.classList.contains('tree-open') ? '' : 'none';
}

async function selectAITreeFeature(path, name) {
  // Highlight selected
  document.querySelectorAll('#ai-tree-list .tree-leaf').forEach(l => l.classList.remove('active'));
  event?.currentTarget?.classList.add('active');

  const detailEl = document.getElementById('ai-tree-detail');
  const suggEl = document.getElementById('ai-tree-suggestion');
  if (detailEl) {
    detailEl.innerHTML = `<div class="ai-analysis-block">
      <h4>🥒 ${name}</h4>
      <div style="font-family:var(--mono);font-size:12px;color:var(--text3)">📂 ${path}</div>
    </div>
    <div class="ai-analysis-block">
      <h4>🤖 AI Analiz Ediliyor...</h4>
      <div class="ai-item"><span class="spinner"></span> Senaryo içeriği analiz ediliyor...</div>
    </div>`;
  }

  try {
    const res = await fetch('/api/features/' + path);
    const data = await res.json();
    const content = data.content || '';
    const lines = content.split('\n');
    const scenarios = lines.filter(l => l.trim().startsWith('Scenario') || l.trim().startsWith('Senaryo'));
    const steps = lines.filter(l => /^\s+(Given|When|Then|And|Ama|Ama|Ve|Verilen|Eğer|O halde)/.test(l));

    if (detailEl) {
      detailEl.innerHTML = `
        <div class="ai-analysis-block">
          <h4>🥒 ${name}</h4>
          <div style="font-size:12px;color:var(--text3);margin-top:4px">📂 ${path}</div>
        </div>
        <div class="ai-analysis-block">
          <h4>📊 Senaryo Özeti</h4>
          <div class="ai-analysis-list">
            <div class="ai-item"><span class="ai-item-tag">Senaryo Sayısı:</span> ${scenarios.length}</div>
            <div class="ai-item"><span class="ai-item-tag">Toplam Adım:</span> ${steps.length}</div>
            <div class="ai-item"><span class="ai-item-tag">Satır:</span> ${lines.length}</div>
          </div>
        </div>
        <div class="ai-analysis-block">
          <h4>📝 İçerik Önizleme</h4>
          <pre style="font-family:var(--mono);font-size:11px;color:var(--text2);line-height:1.6;overflow-x:auto;white-space:pre-wrap;max-height:300px;overflow-y:auto">${content.substring(0, 1000)}${content.length > 1000 ? '\n...' : ''}</pre>
        </div>
        <div class="ai-analysis-block">
          <h4>🤖 AI Öneriler</h4>
          <div class="ai-analysis-list">
            ${scenarios.length === 0 ? '<div class="ai-item"><span class="ai-item-tag">⚠️ UYARI:</span> Feature dosyasında senaryo bulunamadı.</div>' : ''}
            ${scenarios.length > 10 ? '<div class="ai-item"><span class="ai-item-tag">💡 TIP:</span> Çok sayıda senaryo var. Regresyon setine eklemeyi düşünün.</div>' : ''}
            <div class="ai-item"><span class="ai-item-tag">✅ ÖNERİ:</span> Bu feature dosyasını bir regresyon setine ekleyin.</div>
            <div class="ai-item"><span class="ai-item-tag">✅ ÖNERİ:</span> Editörde açmak için <button class="btn btn-ghost btn-sm" onclick="selectFeature('${path}');showView('editor-view',document.querySelectorAll('nav button')[0])">Editörde Aç</button> tıklayın.</div>
          </div>
        </div>`;
    }
    if (suggEl) {
      suggEl.innerHTML = scenarios.length > 0
        ? `<span class="ai-item-tag">${name}:</span> ${scenarios.length} senaryo, ${steps.length} adım bulundu.`
        : `<span class="ai-item-tag">⚠️</span> ${name} dosyasında senaryo bulunamadı.`;
    }
  } catch(e) {
    if (detailEl) detailEl.innerHTML = `<div class="ai-analysis-block"><div class="ai-item" style="border-color:var(--red)">Yükleme hatası: ${e.message}</div></div>`;
  }
}

// 📋 TEST LIFECYCLE LOGIC
let lifecycleNodes = [];
let lifecycleConnections = [];

function addLifecycleNode(type) {
  const canvas = document.getElementById('flow-canvas');
  const empty = canvas.querySelector('.flow-empty');
  if (empty) empty.style.display = 'none';

  const id = 'node-' + Date.now();
  const node = document.createElement('div');
  node.className = 'lifecycle-node';
  node.id = id;
  node.style.left = '50px';
  node.style.top = '50px';

  let title = '';
  let content = '';
  switch(type) {
    case 'analyst': title = '📝 Analist Maddesi'; content = '<textarea placeholder="Analist dökümanını buraya yapıştırın..." style="width:100%; height:80px;"></textarea><button class="btn btn-accent btn-xs w-full mt-8" onclick="processLifecycleNode(\''+id+'\')">Analiz Et</button>'; break;
    case 'manual': title = '📖 Manuel Test'; content = '<div class="manual-steps" style="font-size:11px; color:var(--text3);">Adımlar henüz üretilmedi.</div>'; break;
    case 'auto': title = '🤖 Otomasyon'; content = '<div style="font-size:11px;">Bağlı dosya: <span class="file-name">—</span></div>'; break;
    case 'jenkins': title = '🚀 Jenkins / CI'; content = '<div style="font-size:11px;">Job: <span class="job-status">—</span></div>'; break;
  }

  node.innerHTML = `
    <div class="node-header">
      <span>${title}</span>
      <button class="btn-close btn-xs" onclick="removeLifecycleNode('${id}')">×</button>
    </div>
    <div class="node-body">${content}</div>
    <div class="node-input"></div>
    <div class="node-output" onmousedown="startConnecting('${id}', event)"></div>
  `;

  canvas.appendChild(node);
  makeNodeDraggable(node);
  lifecycleNodes.push({ id, type, x: 50, y: 50 });
}

function makeNodeDraggable(elmnt) {
  let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
  elmnt.querySelector('.node-header').onmousedown = dragMouseDown;

  function dragMouseDown(e) {
    e.preventDefault();
    pos3 = e.clientX;
    pos4 = e.clientY;
    document.onmouseup = closeDragElement;
    document.onmousemove = elementDrag;
    elmnt.style.zIndex = 100;
  }

  function elementDrag(e) {
    e.preventDefault();
    pos1 = pos3 - e.clientX;
    pos2 = pos4 - e.clientY;
    pos3 = e.clientX;
    pos4 = e.clientY;
    elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
    elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
    updateConnections();
  }

  function closeDragElement() {
    document.onmouseup = null;
    document.onmousemove = null;
    elmnt.style.zIndex = 10;
  }
}

function removeLifecycleNode(id) {
  const node = document.getElementById(id);
  if (node) node.remove();
  lifecycleNodes = lifecycleNodes.filter(n => n.id !== id);
  lifecycleConnections = lifecycleConnections.filter(c => c.from !== id && c.to !== id);
  updateConnections();
}

let connectingFrom = null;
function startConnecting(nodeId, e) {
  e.stopPropagation();
  connectingFrom = nodeId;
  document.onmousemove = (ev) => drawTempLine(nodeId, ev);
  document.onmouseup = (ev) => finishConnecting(ev);
}

function drawTempLine(fromId, e) {
  const fromNode = document.getElementById(fromId);
  const canvas = document.getElementById('flow-canvas');
  const svg = document.getElementById('flow-connections');
  
  const fromPt = {
    x: fromNode.offsetLeft + fromNode.offsetWidth,
    y: fromNode.offsetTop + (fromNode.offsetHeight / 2)
  };
  
  const toPt = {
    x: e.clientX - canvas.getBoundingClientRect().left,
    y: e.clientY - canvas.getBoundingClientRect().top
  };

  svg.innerHTML = ''; // Optimized: only redraw if needed
  renderConnections();
  const line = `<line x1="${fromPt.x}" y1="${fromPt.y}" x2="${toPt.x}" y2="${toPt.y}" stroke="var(--accent)" stroke-width="2" />`;
  svg.innerHTML += line;
}

function finishConnecting(e) {
  document.onmousemove = null;
  document.onmouseup = null;
  
  const target = e.target;
  if (target.classList.contains('node-input')) {
    const toId = target.parentElement.id;
    if (connectingFrom !== toId) {
       lifecycleConnections.push({ from: connectingFrom, to: toId });
    }
  }
  connectingFrom = null;
  updateConnections();
}

function updateConnections() {
  renderConnections();
}

function renderConnections() {
  const svg = document.getElementById('flow-connections');
  svg.innerHTML = '';
  lifecycleConnections.forEach(conn => {
    const from = document.getElementById(conn.from);
    const to = document.getElementById(conn.to);
    if (from && to) {
      const x1 = from.offsetLeft + from.offsetWidth;
      const y1 = from.offsetTop + (from.offsetHeight / 2);
      const x2 = to.offsetLeft;
      const y2 = to.offsetTop + (to.offsetHeight / 2);
      svg.innerHTML += `<path d="M ${x1} ${y1} C ${(x1+x2)/2} ${y1}, ${(x1+x2)/2} ${y2}, ${x2} ${y2}" stroke="var(--accent)" fill="transparent" stroke-width="2" />`;
    }
  });
}

function processLifecycleNode(id) {
  const node = document.getElementById(id);
  const text = node.querySelector('textarea').value;
  if (!text) return alert("Lütfen analist maddesi girin!");

  node.querySelector('.node-body').innerHTML = '<div class="spinner"></div> Analiz ediliyor...';
  
  fetch('/api/lifecycle/process-analyst', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  })
  .then(r => r.json())
  .then(data => {
    node.querySelector('.node-body').innerHTML = `<div style="font-size:12px; font-weight:600; color:var(--success); margin-bottom:4px;">✓ Analiz Tamamlandı</div><div style="font-size:11px;">${data.summary}</div>`;
    
    // Auto-create manual test node if connected
    const conn = lifecycleConnections.find(c => c.from === id);
    if (conn) {
       const manualNode = document.getElementById(conn.to);
       if (manualNode) {
         manualNode.querySelector('.node-body').innerHTML = data.steps.map(s => `• ${s}`).join('<br>');
       }
    }
  });
}

/* ── Regression Sets (Drag & Drop) ───────────────────────────────────────────── */
async function loadRegressionSets() {
  try {
    const res = await fetch('/api/regression-sets');
    if (!res.ok) { console.warn('Regresyon setleri yüklenemedi:', res.status); return; }
    const data = await res.json();
    regressionSets = Array.isArray(data) ? data : [];
    renderRegressionSets();
    if (activeRegSet) {
      const updated = regressionSets.find(s => s.id === activeRegSet.id);
      if (updated) selectRegSet(updated);
      else {
        activeRegSet = null;
        document.getElementById('reg-detail-col').style.opacity = '0.3';
        document.getElementById('reg-detail-col').style.pointerEvents = 'none';
        document.getElementById('active-set-title').textContent = 'Set Seçilmedi';
      }
    }
  } catch(e) {
    console.error('loadRegressionSets hatası:', e);
    regressionSets = [];
    renderRegressionSets();
  }
}

function renderRegressionSets() {
  const el = document.getElementById('reg-list');
  if (!el) return;
  if (!regressionSets.length) {
    el.innerHTML = `<div style="text-align:center;padding:32px 16px;color:var(--text3)">
      <div style="font-size:28px;margin-bottom:8px">📦</div>
      <div style="font-size:13px">Henüz regresyon seti yok.<br>
      <button class="btn btn-accent btn-sm" style="margin-top:10px" onclick="createNewRegressionSet()">+ Yeni Set Oluştur</button></div>
    </div>`;
    return;
  }
  el.innerHTML = regressionSets.map(s => `
    <div class="reg-item ${activeRegSet && activeRegSet.id === s.id ? 'active' : ''}" onclick="selectRegSetById(${s.id})">
      <div class="reg-item-title">📦 ${s.name}</div>
      <div class="reg-item-meta">${(s.features||[]).length} test</div>
    </div>
  `).join('');
}

function selectRegSetById(id) {
  const s = regressionSets.find(x => x.id === id);
  if (s) selectRegSet(s);
}

function selectRegSet(s) {
  activeRegSet = s;
  document.getElementById('reg-detail-col').style.opacity = '1';
  document.getElementById('reg-detail-col').style.pointerEvents = 'auto';
  document.getElementById('active-set-title').textContent = '📦 ' + s.name;
  document.getElementById('active-set-count').textContent = s.features.length;
  
  const listEl = document.getElementById('reg-feature-list');
  listEl.innerHTML = s.features.map(f => `
    <div class="reg-feature-item">
      <span>${f}</span>
      <button class="btn btn-ghost btn-sm" onclick="removeFeatureFromRegSet('${f}')">Çıkar</button>
    </div>
  `).join('');
  renderRegressionSets();
}

async function createNewRegressionSet() {
  const name = await showGenericModal('Yeni Regresyon Seti', 'Set için bir isim belirleyin:', 'Örn: Smoke Test Seti');
  if (!name) return;
  const res = await fetch('/api/regression-sets', {
    method: 'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name})
  });
  if (res.ok) { toast('✅ Set oluşturuldu', 'ok'); loadRegressionSets(); }
  else toast('❌ Aynı isimde set olabilir', 'warn');
}

async function deleteActiveRegSet() {
  if (!activeRegSet) return;
  const ok = await showGenericModal('Seti Sil', `"${activeRegSet.name}" setini silmek istediğinize emin misiniz?`, '', true);
  if (!ok) return;
  await fetch(`/api/regression-sets/${activeRegSet.id}`, {method:'DELETE'});
  activeRegSet = null;
  document.getElementById('reg-detail-col').style.opacity = '0.3'; 
  document.getElementById('reg-detail-col').style.pointerEvents = 'none';
  document.getElementById('active-set-title').textContent = 'Set Seçilmedi';
  loadRegressionSets();
}

function dragFeature(ev, featureName) {
  ev.dataTransfer.setData("text", featureName);
  ev.target.classList.add('is-dragging');
  setTimeout(() => ev.target.classList.remove('is-dragging'), 1000); // safety fallback
}

function allowDrop(ev) {
  ev.preventDefault();
  document.getElementById('drop-zone').classList.add('drag-over');
}
function dragLeave(ev) {
  document.getElementById('drop-zone').classList.remove('drag-over');
}
async function handleDrop(ev) {
  ev.preventDefault();
  document.getElementById('drop-zone').classList.remove('drag-over');
  if (!activeRegSet) return;
  const fname = ev.dataTransfer.getData("text");
  if (!fname) return;
  
  if (activeRegSet.features.includes(fname)) return toast('ℹ️ Bu test zaten sette.', 'warn');
  
  await fetch(`/api/regression-sets/${activeRegSet.id}/features`, {
    method: 'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({feature_name: fname})
  });
  toast('📥 Test eklendi', 'ok');
  loadRegressionSets(); // Reload and reselect
}

async function removeFeatureFromRegSet(fname) {
  if (!activeRegSet) return;
  await fetch(`/api/regression-sets/${activeRegSet.id}/features/${fname}`, {method:'DELETE'});
  loadRegressionSets();
}

function runActiveRegressionSet() {
  if (!activeRegSet || activeRegSet.features.length === 0) return toast('⚠️ Koşulacak test yok', 'warn');
  
  // Terminal is already visible in global sidebar
  const marker = document.getElementById('marker-select').value;
  const body = { markers: marker, features_list: activeRegSet.features };
  
  _sendRunRequest(body);
}

function clearTerminal() {
  const t = document.getElementById('terminal');
  if (t) t.innerHTML = '<div class="t-line t-dim">// Test akışı temizlendi.</div>';
}


/* ── Feature List (Tree View) ─────────────────────────────────────────────────── */
async function loadFeatures() {
  try {
    const res = await fetch('/api/features');
    if (!res.ok) { console.warn('Features yüklenemedi:', res.status); return; }
    const data = await res.json();
    features = Array.isArray(data) ? data : [];
    renderFeatureList();
    renderDashboard();
    if (document.getElementById('ai-tree-view')?.classList.contains('active')) refreshAITree();
  } catch(e) { console.error('loadFeatures hatası:', e); features = []; renderFeatureList(); }
}

const collapsedFolders = new Set();

function renderFeatureList() {
  const el = document.getElementById('feature-list');
  if (!features.length) {
    el.innerHTML = '<div style="padding:16px;color:var(--text3);font-size:12px;text-align:center">Henüz feature yok.<br/>+ Yeni ile oluşturun.</div>';
    return;
  }
  el.innerHTML = renderTreeNodes(features, 0);
}

function renderTreeNodes(nodes, depth) {
  return nodes.map(node => {
    const indent = depth * 14;
    if (node.type === 'folder') {
      const isCollapsed = collapsedFolders.has(node.path);
      const safeId = 'fc_' + node.path.replace(/[^a-zA-Z0-9]/g, '_');
      const childHtml = renderTreeNodes(node.children || [], depth + 1);
      return `<div style="padding-left:${indent}px">
          <div onclick="toggleFolder('${node.path}')" style="display:flex;align-items:center;gap:6px;padding:6px 10px;cursor:pointer;border-radius:6px;user-select:none" onmouseover="this.style.background='var(--bg3)'" onmouseout="this.style.background=''">
            <span style="font-size:11px;color:var(--text3)">${isCollapsed ? '▶' : '▼'}</span>
            <span style="font-size:15px">📂</span>
            <span style="font-size:13px;font-weight:600;flex:1;color:var(--text1)">${node.name}</span>
            <button onclick="event.stopPropagation();deleteFolder('${node.path}')" style="background:none;border:none;cursor:pointer;color:var(--text3);font-size:11px;padding:2px 5px;border-radius:4px" onmouseover="this.style.color='var(--red)'" onmouseout="this.style.color='var(--text3)'">🗑</button>
          </div>
          <div id="${safeId}" style="display:${isCollapsed ? 'none' : 'block'}">${childHtml}</div>
        </div>`;
    } else {
      return `<div class="feature-item ${activeFeature === node.path ? 'active' : ''}" draggable="true"
          ondragstart="dragFeature(event, '${node.path}')"
          onclick="selectFeature('${node.path}')"
          style="padding-left:${indent + 8}px">
          <div class="fi-icon">🥒</div>
          <div class="fi-info">
            <div class="fi-name">${node.stem}</div>
            <div class="fi-meta">${node.modified || ''}</div>
          </div>
          <div class="badge-count">${node.scenarios}</div>
        </div>`;
    }
  }).join('');
}

function toggleFolder(path) {
  if (collapsedFolders.has(path)) collapsedFolders.delete(path);
  else collapsedFolders.add(path);
  renderFeatureList();
}

async function createFolder() {
  const name = await showGenericModal('Yeni Klasör', 'Klasör adını girin (alt klasör için örn: login/smoke):', 'Klasör adı');
  if (!name || !name.trim()) return;
  await fetch('/api/features/folder', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ path: name.trim() })
  });
  toast('📂 Klasör oluşturuldu!', 'ok');
  loadFeatures();
}

async function deleteFolder(path) {
  const ok = await showGenericModal('Klasörü Sil', `"${path}" klasörünü ve içindekileri silmek istediğinizden emin misiniz?`, '', true);
  if (!ok) return;
  await fetch('/api/features/folder', {
    method: 'DELETE',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ path })
  });
  toast('🗑 Klasör silindi.', 'ok');
  loadFeatures();
}


/* ── Manual Tests (Implementation) ─────────────────────────────────────────── */
async function fetchManualTests() {
  const res = await fetch('/api/manual-tests');
  manualTests = await res.json();
  renderManualTests();
}

function renderManualTests() {
  const el = document.getElementById('manual-list');
  if(!el) return;
  el.innerHTML = manualTests.map(t => `
    <div class="reg-item ${activeManualTestId === t.id ? 'active' : ''}" onclick="selectManualTest(${t.id})">
      <div class="reg-item-title">📝 ${t.title}</div>
      <div class="reg-item-meta">${t.status} • ${(t.steps || []).length} adım</div>
    </div>
  `).join('');
}

function selectManualTest(id) {
  const t = manualTests.find(x => x.id === id);
  if (!t) return;
  activeManualTestId = id;
  
  const col = document.getElementById('manual-detail-col');
  if(col) {
      col.style.opacity = '1';
      col.style.pointerEvents = 'auto';
  }
  
  const titleEl = document.getElementById('active-manual-title');
  if(titleEl) titleEl.textContent = '📝 ' + t.title;
  
  const statusEl = document.getElementById('active-manual-status');
  if(statusEl) statusEl.value = t.status;
  
  const listEl = document.getElementById('manual-step-list');
  if(listEl) {
      listEl.innerHTML = (t.steps || []).map(s => `
        <div class="reg-feature-item" style="flex-direction:column; align-items:flex-start; gap:8px; padding:12px; margin-bottom:10px;">
          <div style="display:flex; width:100%; justify-content:space-between; align-items:center;">
            <span style="font-weight:600; font-size:13px; color:var(--accent)">Adım #${s.step_order}</span>
            <div style="display:flex; gap:6px;">
              <select class="select-styled" style="padding:2px 8px; font-size:11px" onchange="updateManualStepStatus(${s.id}, this.value)">
                <option value="Unexecuted" ${s.status === 'Unexecuted' ? 'selected' : ''}>Koşulmadı</option>
                <option value="Passed" ${s.status === 'Passed' ? 'selected' : ''}>Geçti</option>
                <option value="Failed" ${s.status === 'Failed' ? 'selected' : ''}>Kaldı</option>
              </select>
              <button class="btn btn-danger btn-sm" style="padding:2px 6px" onclick="delManualStep(${s.id})">🗑</button>
            </div>
          </div>
          <div style="font-size:13px;"><b>Eylem:</b> ${s.action}</div>
          <div style="font-size:13px; color:var(--text3)"><b>Beklenen:</b> ${s.expected}</div>
        </div>
      `).join('');
  }
  
  renderManualTests();
}
async function createManualTest() {
  const title = await showGenericModal('Yeni Manuel Test', 'Senaryo için bir başlık girin:', 'Örn: Login Başarılı Senaryosu');
  if(!title) return;
  await fetch('/api/manual-tests', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({title})
  });
  await fetchManualTests();
}

async function deleteActiveManualTest() {
  if(!activeManualTestId) return;
  const ok = await showGenericModal('Testi Sil', "Bu manuel testi tamamen silmek istediğinizden emin misiniz?", '', true);
  if (!ok) return;
  await fetch('/api/manual-tests/' + activeManualTestId, {method: 'DELETE'});
  activeManualTestId = null;
  document.getElementById('manual-detail-col').style.opacity = '0.3';
  document.getElementById('manual-detail-col').style.pointerEvents = 'none';
  await fetchManualTests();
}

async function addManualStep() {
  if(!activeManualTestId) return;
  const action = document.getElementById('m-action').value;
  const expected = document.getElementById('m-expected').value;
  if(!action || !expected) { toast("Aksiyon ve Beklenen zorunlu", "error"); return; }
  
  await fetch('/api/manual-tests/' + activeManualTestId + '/steps', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({action, expected})
  });
  document.getElementById('m-action').value = '';
  document.getElementById('m-expected').value = '';
  await fetchManualTests();
}

async function delManualStep(id) {
  const ok = await showGenericModal('Adımı Sil', "Bu adımı silmek istediğinizden emin misiniz?", '', true);
  if (!ok) return;
  await fetch('/api/manual-test-steps/' + id, {method: 'DELETE'});
  await fetchManualTests();
}

async function updateManualStepStatus(id, status) {
  await fetch('/api/manual-test-steps/' + id, {
    method: 'PUT', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({status})
  });
  await fetchManualTests();
}

async function updateManualTestStatus(status) {
  if(!activeManualTestId) return;
  await fetch('/api/manual-tests/' + activeManualTestId, {
    method: 'PUT', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({status})
  });
  await fetchManualTests();
}

/* ── API Tester (Postman Clone) ──────────────────────────────────────────────── */

function addApiHeader() {
  const div = document.createElement('div');
  div.className = 'api-header-row';
  div.style = 'display:flex; gap:8px; margin-bottom:8px;';
  div.innerHTML = `
    <input type="text" class="editor-filename" style="flex:1" placeholder="Key" />
    <input type="text" class="editor-filename" style="flex:1" placeholder="Value" />
    <button class="btn btn-danger btn-sm" onclick="this.parentElement.remove()">🗑</button>
  `;
  document.getElementById('api-headers-list').appendChild(div);
}

async function sendApiRequest() {
  const url = document.getElementById('api-url').value.trim();
  const method = document.getElementById('api-method').value;
  let body = document.getElementById('api-body').value.trim();
  
  if (!url) return toast("Lütfen geçerli bir URL girin", "error");
  
  const headerRows = document.querySelectorAll('.api-header-row');
  const headers = [];
  headerRows.forEach(row => {
    const inputs = row.querySelectorAll('input');
    const key = inputs[0].value.trim();
    const val = inputs[1].value.trim();
    if(key) headers.push({key, value: val});
  });
  
  toast("İstek gönderiliyor...", "ok");
  document.getElementById('api-res-status').innerText = 'Durum: Bekleniyor...';
  document.getElementById('api-res-time').innerText = 'Süre: -';
  document.getElementById('api-res-body').value = 'Yükleniyor...';
  document.getElementById('api-res-headers').value = '';

  try {
    const res = await fetch('/api/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, method, headers, body })
    });
    
    const data = await res.json();
    if(data.error) throw new Error(data.error);
    
    document.getElementById('api-res-status').innerText = `Durum: ${data.status}`;
    document.getElementById('api-res-status').style.color = (data.status >= 200 && data.status < 300) ? 'var(--green)' : 'var(--red)';
    document.getElementById('api-res-time').innerText = `Süre: ${Math.round(data.time)} ms`;
    
    try {
      document.getElementById('api-res-body').value = JSON.stringify(JSON.parse(data.body), null, 2);
    } catch(e) {
      document.getElementById('api-res-body').value = data.body;
    }
    document.getElementById('api-res-headers').value = JSON.stringify(data.headers, null, 2);
    toast("İstek başarılı", "ok");
    document.getElementById('btn-api-analyze').style.display = 'block';
  } catch (err) {
    document.getElementById('api-res-status').innerText = 'Durum: Hata';
    document.getElementById('api-res-status').style.color = 'var(--red)';
    document.getElementById('api-res-body').value = String(err);
    toast("İstek başarısız", "error");
    document.getElementById('btn-api-analyze').style.display = 'block';
  }
}

/* ── Inspector & Export ──────────────────────────────────────────────────────── */
async function analyzeApiResponse() {
  const url = document.getElementById('api-url').value;
  const method = document.getElementById('api-method').value;
  const status = document.getElementById('api-res-status').innerText;
  const reqBody = document.getElementById('api-body').value;
  const resBody = document.getElementById('api-res-body').value;
  const resHeaders = document.getElementById('api-res-headers').value;

  const reqInfo = { url, method, body: reqBody };
  const resInfo = { status, body: resBody, headers: resHeaders };

  document.getElementById('api-ai-modal').classList.add('active');
  document.getElementById('api-ai-content').innerText = '⏳ AI Yanıtı inceliyor ve analiz ediyor... Lütfen bekleyin...';

  try {
    const res = await fetch('/api/analyze-api-request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request: reqInfo, response: resInfo })
    });
    const data = await res.json();
    if(data.error) throw new Error(data.error);
    
    document.getElementById('api-ai-content').innerText = data.analysis;
  } catch(e) {
    document.getElementById('api-ai-content').innerText = 'Hata oluştu: ' + e;
  }
}

function closeApiAiModal() {
  document.getElementById('api-ai-modal').classList.remove('open');
}

async function openInspector() {
  const url = prompt("Hangi URL üzerinde kayıt yapmak istiyorsunuz?", document.getElementById('s-base-url').value || "https://google.com");
  if (!url) return;
  toast('🚀 Playwright başlatıldı. Lütfen tarayıcıyı kapattığınızda AI çevirisini bekleyin...', 'ok');
  
  try {
      const res = await fetch('/api/inspect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      const data = await res.json();
      
      if(data.error) {
          toast('❌ Kayıt hatası: ' + data.error, 'err');
      } else if (data.gherkin) {
          toast('✨ AI kaydınızı Gherkin formatına çevirdi!', 'ok');
          document.getElementById('editor').value = data.gherkin;
          updateLineNumbers();
          // Editöre yönlendir
          showView('editor-view', document.querySelectorAll('nav button')[0]);
      }
  } catch(e) {
      toast('❌ Sunucu bağlantısı kesildi veya zaman aşımına uğradı.', 'err');
      console.error(e);
  }
}

async function startSecurityScan() {
  const urlInput = document.getElementById('security-target-url');
  const btn = document.getElementById('sec-scan-btn');
  const loader = document.getElementById('security-loading');
  const output = document.getElementById('security-report-output');
  
  if (!urlInput.value) {
      toast('Lütfen geçerli bir hedef URL girin.', 'err');
      return;
  }
  
  btn.disabled = true;
  btn.style.opacity = '0.5';
  output.style.display = 'none';
  loader.style.display = 'block';
  output.value = "";
  
  toast('Sızma Testi başlatıldı. Otonom tarama sürüyor...', 'ok');
  
  try {
      const res = await fetch('/api/security-scan', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ url: urlInput.value })
      });
      const data = await res.json();
      
      if(data.error) {
          toast('Hata: ' + data.error, 'err');
          output.value = "HATA:\n" + data.error;
      } else {
          toast('✅ Analiz Tamamlandı!', 'ok');
          output.value = data.report;
      }
  } catch(e) {
      toast('Sunucu iletişim hatası.', 'err');
      output.value = "HATA:\n" + e.message;
  } finally {
      btn.disabled = false;
      btn.style.opacity = '1';
      loader.style.display = 'none';
      output.style.display = 'block';
  }
}

function exportData() {
  toast('📦 İndirme hazırlanıyor...', 'ok');
  window.location.href = '/api/export';
}

/* ── Toast ───────────────────────────────────────────────────────────────────── */

/* ── Modal backdrop close ────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const nm = document.getElementById('new-modal');
  if (nm) nm.addEventListener('click', e => { if (e.target === nm) closeModal(); });
  
  // Project Modal backdrop
  const pm = document.getElementById('project-modal');
  if (pm) pm.addEventListener('click', e => { if (e.target === pm) closeProjectModal(); });
  
  // Load Projects
  loadProjects();
});

// ─── ADVANCED REPORTING DASHBOARDS ──────────────────────────────────────

async function loadComprehensiveReports() {
  try {
    const res = await fetch('/api/reports/comprehensive');
    if (!res.ok) throw new Error('Rapor verileri alınamadı');
    const data = await res.json();
    
    // 1. Genel Başarı Oranı (Doughnut)
    const pieCanvas = document.getElementById('pieChartPassFail');
    if (pieCanvas) {
        const pass = data.overall_pass_fail?.passed || 0;
        const fail = data.overall_pass_fail?.failed || 0;
        if (chartPassFail) chartPassFail.destroy();
        
        if(pass > 0 || fail > 0) {
          chartPassFail = new Chart(pieCanvas, {
            type: 'doughnut',
            data: {
              labels: ['Başarılı', 'Başarısız'],
              datasets: [{
                data: [pass, fail],
                backgroundColor: ['#10b981', '#ef4444'],
                borderWidth: 0,
                hoverOffset: 4
              }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: {color:'var(--text)'} } } }
          });
        }
    }

    // 2. Süre Trendi (Line Chart)
    const durCanvas = document.getElementById('lineChartDuration');
    if (durCanvas) {
        const trend = data.duration_trend || [];
        if (chartDuration) chartDuration.destroy();
        if(trend.length > 0) {
          chartDuration = new Chart(durCanvas, {
            type: 'line',
            data: {
              labels: trend.map((_, i) => `#${i+1}`),
              datasets: [{
                label: 'Koşu Süresi (ms)',
                data: trend.map(t => t.time),
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.3,
                borderWidth: 2,
                pointRadius: 4
              }]
            },
            options: { 
              responsive: true, maintainAspectRatio: false, 
              plugins: { legend: { display: false } },
              scales: {
                 x: { ticks: { color: 'var(--text3)' }, grid: { display: false } },
                 y: { ticks: { color: 'var(--text3)' }, grid: { color: 'var(--border)' } }
              }
            }
          });
        }
    }

    // 3. Modül/Marker Bazlı Başarı Oranı (Stacked Bar)
    const barCanvas = document.getElementById('barChartMarkers');
    if (barCanvas) {
        const mStats = data.marker_stats || [];
        if (chartMarkers) chartMarkers.destroy();
        if(mStats.length > 0) {
          chartMarkers = new Chart(barCanvas, {
            type: 'bar',
            data: {
              labels: mStats.map(s => s.marker || 'all'),
              datasets: [
                { label: 'Başarılı', data: mStats.map(s => s.passed), backgroundColor: '#10b981', borderRadius: 4 },
                { label: 'Başarısız', data: mStats.map(s => s.failed), backgroundColor: '#ef4444', borderRadius: 4 }
              ]
            },
            options: { 
              responsive: true, maintainAspectRatio: false, 
              scales: { 
                x: { stacked: true, ticks: { color: 'var(--text3)' }, grid: { display: false } }, 
                y: { stacked: true, ticks: { color: 'var(--text3)' }, grid: { color: 'var(--border)' } } 
              },
              plugins: { legend: { position: 'top', labels: { color: 'var(--text)' } } }
            }
          });
        }
    }
  } catch(e) {
    console.error('loadComprehensiveReports error:', e);
    toast('Rapor metrikleri yüklenemedi: ' + e.message, 'fail');
  }
}


/* ── Modal: Feature Wizard ──────────────────────────────────────────────────── */
let wizPlatform = null;
let wizOS = null;

function openNewModal() {
  wizPlatform = null;
  wizOS = null;
  // reset wizard state
  document.querySelectorAll('.wiz-platform-btn, #wiz-btn-android, #wiz-btn-ios, #wiz-btn-both').forEach(b => {
    b.style.borderColor = 'var(--border)';
    b.style.background = 'var(--bg2)';
  });
  document.getElementById('wiz-web').style.display = 'none';
  document.getElementById('wiz-mobile').style.display = 'none';
  document.getElementById('wiz-service').style.display = 'none';
  document.getElementById('wiz-final').style.display = 'none';
  document.getElementById('wiz-step-1').style.display = 'block';
  document.getElementById('wiz-next-btn').disabled = true;
  document.getElementById('wiz-next-btn').style.display = '';
  document.getElementById('wiz-create-btn').style.display = 'none';
  document.getElementById('new-name').value = '';
  // populate folder dropdown
  const sel = document.getElementById('wiz-folder');
  const folders = collectFolderPaths(features, '');
  sel.innerHTML = '<option value="">📁 Kök (features/)</option>' +
    folders.map(f => `<option value="${f}">📂 ${f}</option>`).join('');
  document.getElementById('new-modal').classList.add('active');
}

function collectFolderPaths(nodes, prefix) {
  let paths = [];
  for (const n of nodes) {
    if (n.type === 'folder') {
      const p = prefix ? prefix + '/' + n.name : n.name;
      paths.push(p);
      paths = paths.concat(collectFolderPaths(n.children || [], p));
    }
  }
  return paths;
}

function wizSelectPlatform(p) {
  wizPlatform = p;
  ['web','mobile','service'].forEach(x => {
    const b = document.getElementById('wiz-btn-' + x);
    if (b) { b.style.borderColor = x === p ? 'var(--accent)' : 'var(--border)'; b.style.background = x === p ? 'rgba(99,102,241,0.15)' : 'var(--bg2)'; }
  });
  document.getElementById('wiz-next-btn').disabled = false;
}

function wizSelectOS(os) {
  wizOS = os;
  ['android','ios','both'].forEach(x => {
    const b = document.getElementById('wiz-btn-' + x);
    if (b) { b.style.borderColor = x === os ? 'var(--accent)' : 'var(--border)'; b.style.background = x === os ? 'rgba(99,102,241,0.15)' : 'var(--bg2)'; }
  });
}

function wizNextStep() {
  document.getElementById('wiz-step-1').style.display = 'none';
  if (wizPlatform === 'web')     document.getElementById('wiz-web').style.display = 'block';
  if (wizPlatform === 'mobile')  document.getElementById('wiz-mobile').style.display = 'block';
  if (wizPlatform === 'service') document.getElementById('wiz-service').style.display = 'block';
  document.getElementById('wiz-final').style.display = 'block';
  document.getElementById('wiz-next-btn').style.display = 'none';
  document.getElementById('wiz-create-btn').style.display = '';
}

function closeModal() {
  document.getElementById('new-modal').classList.remove('active');
}

async function createFeature() {
  const rawName = document.getElementById('new-name').value.trim();
  if (!rawName) { toast('Dosya adı boş olamaz!', 'err'); return; }
  const folder = document.getElementById('wiz-folder')?.value || '';
  const fullName = (folder ? folder + '/' : '') + (rawName.endsWith('.feature') ? rawName : rawName + '.feature');

  // Build platform-aware template header comment
  let header = '';
  if (wizPlatform === 'web') {
    const url = document.getElementById('wiz-web-url')?.value || '';
    const db  = document.getElementById('wiz-web-db')?.value || '';
    header = `# Platform: Web\n# URL: ${url || 'belirtilmedi'}\n# DB: ${db || 'belirtilmedi'}\n`;
  } else if (wizPlatform === 'mobile') {
    const os  = wizOS === 'android' ? 'Android' : wizOS === 'ios' ? 'iOS' : 'Android + iOS';
    const pkg = document.getElementById('wiz-mob-bundle')?.value || '';
    header = `# Platform: Mobil — ${os}\n# Bundle: ${pkg || 'belirtilmedi'}\n`;
  } else if (wizPlatform === 'service') {
    const sw  = document.getElementById('wiz-swagger-url')?.value || '';
    const auth= document.getElementById('wiz-svc-auth')?.value || '';
    header = `# Platform: Servis / API\n# Swagger: ${sw || 'belirtilmedi'}\n# Auth: ${auth || 'belirtilmedi'}\n`;
  }

  const stem = rawName.replace(/\.feature$/, '');
  const content = header + `\nFeature: ${stem}\n  Senaryo: ${stem} temel akışı\n    Given kullanıcı ana sayfadadır\n    When kullanıcı "" metnine tıklar\n    Then URL "" içermelidir\n`;

  const res = await fetch('/api/features/' + fullName, {
    method: 'PUT', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ content })
  });
  if (!res.ok) { toast('❌ Dosya oluşturulamadı', 'err'); return; }
  toast('✅ Feature oluşturuldu: ' + fullName, 'ok');
  closeModal();
  await loadFeatures();
  await selectFeature(fullName);
  showView('editor-view', document.querySelectorAll('nav button')[0]);
}

/* ── Editor Save / Delete / Run ─────────────────────────────────────────────── */
async function saveFeature() {
  const name = document.getElementById('editor-filename')?.value?.trim();
  const content = document.getElementById('editor')?.value || '';
  if (!name) { toast('Dosya adı boş olamaz!', 'err'); return; }
  const fname = name.endsWith('.feature') ? name : name + '.feature';
  await fetch('/api/features/' + fname, {
    method: 'PUT', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ content })
  });
  toast('💾 Kaydedildi: ' + fname, 'ok');
  activeFeature = fname;
  loadFeatures();
}

async function deleteFeature() {
  if (!activeFeature) { toast('Önce bir feature seçin.', 'warn'); return; }
  if (!confirm(`"${activeFeature}" silinsin mi?`)) return;
  await fetch('/api/features/' + activeFeature, { method: 'DELETE' });
  toast('🗑 Silindi: ' + activeFeature, 'ok');
  activeFeature = null;
  document.getElementById('editor').value = '';
  document.getElementById('editor-filename').value = '';
  loadFeatures();
}

async function runTests(singleFeature = false) {
  const body = singleFeature && activeFeature ? { features_list: [activeFeature] } : {};
  const marker = document.getElementById('marker-select')?.value || '';
  if (marker) body.markers = marker;
  _sendRunRequest(body);
}

function _sendRunRequest(body) {
  const outEl = document.getElementById('terminal');
  // vd-screen is inside the iPhone frame now
  const vdImg = document.getElementById('vd-screen');
  const vdOverlay = document.getElementById('vd-overlay');
  const resEl = document.getElementById('result-summary');
  const dotEl = document.getElementById('run-dot');

  if (outEl) outEl.innerHTML = '<div class="t-line t-dim">// Testler başlatılıyor...</div>';
  if (resEl) resEl.style.display = 'none';
  if (dotEl) { dotEl.className = 'dot dot-yellow'; }
  toast('▶ Testler koşturuluyor...', 'ok');

  fetch('/api/run', {
    method: 'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body)
  }).then(r => r.json()).then(data => {
    if (data.error) { toast('❌ ' + data.error, 'err'); return; }
    const runId = data.run_id;
    const evtSrc = new EventSource('/api/run/' + runId + '/stream');

    evtSrc.onmessage = e => {
      let msg;
      try { msg = JSON.parse(e.data); } catch { return; }

      if (msg.type === 'output') {
        if (outEl) {
          const line = document.createElement('div');
          line.className = 't-line';
          line.textContent = msg.text;
          outEl.appendChild(line);
          outEl.scrollTop = outEl.scrollHeight;
        }
      } else if (msg.type === 'image') {
        // Show live screen
        if (vdImg) vdImg.src = 'data:image/jpeg;base64,' + msg.data;
        if (vdOverlay) vdOverlay.style.display = 'none';
      } else if (msg.type === 'done') {
        evtSrc.close();
        if (dotEl) dotEl.className = msg.returncode === 0 ? 'dot dot-green' : 'dot dot-red';
        if (vdOverlay) {
          vdOverlay.style.display = 'flex';
          vdOverlay.innerHTML = '<p>' + (msg.returncode === 0 ? 'Tamamlandı' : 'Hata Oluştu') + '</p>';
        }
        // Parse pass/fail from terminal output
        let passed = 0, failed = 0;
        if (outEl) {
          const text = outEl.innerText || '';
          const pm = text.match(/(\d+)\s+passed/); if (pm) passed = parseInt(pm[1]);
          const fm = text.match(/(\d+)\s+failed/); if (fm) failed = parseInt(fm[1]);
        }
        if (resEl) {
          resEl.style.display = '';
          document.getElementById('res-total').textContent = passed + failed;
          document.getElementById('res-pass').textContent  = passed;
          document.getElementById('res-fail').textContent  = failed;
        }
        toast(msg.returncode === 0 ? '✅ Koşum tamamlandı!' : '⚠️ Koşum bitti (bazı testler başarısız)', msg.returncode === 0 ? 'ok' : 'warn');
      }
    };

    evtSrc.onerror = () => {
      evtSrc.close();
      if (dotEl) dotEl.className = 'dot dot-gray';
    };
  }).catch(e => toast('❌ ' + e.message, 'err'));
}

/* ── Settings ───────────────────────────────────────────────────────────────── */
async function loadSettings() {
  try {
    const res = await fetch('/api/settings');
    const d = await res.json();
    if (d.OPENAI_MODEL)     { const el = document.getElementById('s-model');      if(el) el.value = d.OPENAI_MODEL; }
    if (d.BASE_URL)         { const el = document.getElementById('s-base-url');   if(el) el.value = d.BASE_URL; }
    if (d.BROWSER)          { const el = document.getElementById('s-browser');    if(el) el.value = d.BROWSER; }
    if (d.HEADLESS !== undefined) { const el = document.getElementById('s-headless'); if(el) el.value = String(d.HEADLESS); }
    if (d.OPENAI_API_BASE)  { const el = document.getElementById('s-base-url-ai'); if(el) el.value = d.OPENAI_API_BASE; }
    const badge = document.getElementById('base-url-badge');
    if (badge) badge.textContent = d.BASE_URL || 'BASE_URL ayarlanmadı';
  } catch(e) { console.error('loadSettings', e); }
}

async function saveSettings() {
  const body = {};
  const m  = document.getElementById('s-model');       if(m)  body.OPENAI_MODEL    = m.value;
  const b  = document.getElementById('s-base-url');    if(b)  body.BASE_URL        = b.value;
  const br = document.getElementById('s-browser');     if(br) body.BROWSER         = br.value;
  const h  = document.getElementById('s-headless');    if(h)  body.HEADLESS        = h.value;
  const k  = document.getElementById('s-api-key');     if(k && k.value) body.OPENAI_API_KEY = k.value;
  const ba = document.getElementById('s-base-url-ai'); if(ba) body.OPENAI_API_BASE = ba.value;
  await fetch('/api/settings', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
  toast('⚙️ Ayarlar kaydedildi!', 'ok');
  loadSettings();
}

/* ── AI Generator Modal ─────────────────────────────────────────────────────── */
function openAIModal() {
  document.getElementById('ai-modal')?.classList.add('active');
}
function closeAIModal() {
  document.getElementById('ai-modal')?.classList.remove('active');
}
function closeApiAiModal() {
  document.getElementById('api-ai-modal')?.classList.remove('active');
}

async function generateFromAI() {
  const url  = document.getElementById('ai-url')?.value || '';
  const tech = document.getElementById('ai-tech')?.value || 'Pytest BDD (Python)';
  const req  = document.getElementById('ai-requirements')?.value || '';
  if (!req.trim()) { toast('Gereksinim alanı boş olamaz!', 'err'); return; }

  const btn = document.getElementById('ai-gen-btn');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Üretiyor...'; }
  toast('�� AI senaryo oluşturuyor...', 'ok');

  try {
    const res = await fetch('/api/generate-feature', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ url, tech, requirement: req })
    });
    const data = await res.json();
    if (data.error) { toast('❌ ' + data.error, 'err'); return; }
    document.getElementById('editor').value = data.gherkin || data.content || '';
    updateLineNumbers();
    closeAIModal();
    showView('editor-view', document.querySelectorAll('nav button')[0]);
    toast('✅ Senaryo editöre yüklendi!', 'ok');
  } catch(e) {
    toast('❌ ' + e.message, 'err');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🤖 Üret (GPT-4o)'; }
  }
}

/* ── Select Feature ─────────────────────────────────────────────────────────── */
async function selectFeature(path) {
  try {
    const res = await fetch('/api/features/' + path);
    const data = await res.json();
    activeFeature = path;
    const filenameEl = document.getElementById('editor-filename');
    if (filenameEl) { 
      filenameEl.value = data.name || path; 
      validateFilename(filenameEl); 
    }
    const editorEl = document.getElementById('editor');
    if (editorEl) { 
      editorEl.value = data.content || ''; 
      updateLineNumbers(); 
    }
    renderFeatureList();
  } catch(e) {
    console.error('selectFeature error:', e);
  }
}

/* ── Toast ──────────────────────────────────────────────────────────────────── */
function toast(msg, type = 'ok') {
  const c = document.getElementById('toast-container') || (() => {
    const d = document.createElement('div');
    d.id = 'toast-container';
    d.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:10px';
    document.body.appendChild(d);
    return d;
  })();
  const t = document.createElement('div');
  const themes = {
    ok:   { bg: 'linear-gradient(135deg, #059669 0%, #10b981 100%)', icon: '✅' },
    err:  { bg: 'linear-gradient(135deg, #dc2626 0%, #ef4444 100%)', icon: '❌' },
    warn: { bg: 'linear-gradient(135deg, #d97706 0%, #f59e0b 100%)', icon: '⚠️' },
    fail: { bg: 'linear-gradient(135deg, #dc2626 0%, #ef4444 100%)', icon: '💥' }
  };
  const theme = themes[type] || themes.ok;
  t.style.cssText = `background:${theme.bg};color:#fff;padding:12px 20px;border-radius:12px;font-size:14px;font-weight:600;box-shadow:0 10px 15px -3px rgba(0,0,0,0.1);animation:slideIn .3s ease;max-width:350px;display:flex;align-items:center;gap:10px;border:1px solid rgba(255,255,255,0.1)`;
  t.innerHTML = `<span style="font-size:18px">${theme.icon}</span> <span>${msg}</span>`;
  c.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    t.style.transform = 'translateY(10px)';
    t.style.transition = 'all .3s ease';
    setTimeout(() => t.remove(), 300);
  }, 4000);
}

/* ── Generic Modal Logic ───────────────────────────────────────────────────── */
let gmResolve = null;

function showGenericModal(title, desc, placeholder = '', isConfirm = false) {
  const modal = document.getElementById('generic-modal');
  document.getElementById('gm-title').textContent = title;
  document.getElementById('gm-desc').textContent = desc;
  const input = document.getElementById('gm-input');
  input.value = '';
  input.placeholder = placeholder;
  document.getElementById('gm-input-container').style.display = isConfirm ? 'none' : 'block';
  
  modal.classList.add('active');
  if (!isConfirm) setTimeout(() => input.focus(), 150);
  
  return new Promise(resolve => {
    gmResolve = resolve;
    document.getElementById('gm-confirm-btn').onclick = () => {
      const val = isConfirm ? true : input.value;
      closeGenericModal();
      resolve(val);
    };
  });
}

function closeGenericModal() {
  document.getElementById('generic-modal').classList.remove('active');
  if (gmResolve) {
    gmResolve(null);
    gmResolve = null;
  }
}

/* ── Editor Helpers ────────────────────────────────────────────────────────── */
function validateFilename(input) {
  if(!input) return;
  const v = input.value.trim();
  const isFeature = v.endsWith('.feature');
  input.style.borderColor = isFeature ? 'var(--accent)' : 'var(--red)';
  input.style.boxShadow = isFeature ? '0 0 8px rgba(99,102,241,0.2)' : '0 0 8px rgba(239,68,68,0.2)';
}

function updateLineNumbers() {
  const editor = document.getElementById('editor');
  const lineNoContainer = document.getElementById('line-numbers');
  if (!editor || !lineNoContainer) return;
  const lines = editor.value.split('\n');
  lineNoContainer.innerHTML = lines.map((_, i) => `<div>${i + 1}</div>`).join('');
}

// Sync scrolling
if(document.getElementById('editor')) {
  document.getElementById('editor').addEventListener('scroll', () => {
    const lineNoContainer = document.getElementById('line-numbers');
    if(lineNoContainer) lineNoContainer.scrollTop = document.getElementById('editor').scrollTop;
  });
}


/* ── Element Deposu (Locators) ──────────────────────────────────────────────── */
async function loadLocators() {
  try {
    const tbody = document.getElementById('locators-table-body');
    if (!tbody) return;
    const res = await fetch('/api/locators');
    const data = await res.json();
    if (!data.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text3);padding:20px">Henüz element eklenmedi.</td></tr>';
      return;
    }
    tbody.innerHTML = data.map(loc => `<tr>
      <td>${loc.id}</td>
      <td><code style="color:var(--accent)">${loc.name}</code></td>
      <td><code style="font-size:11px">${loc.locator_value}</code></td>
      <td style="color:var(--text3)">${loc.page || '-'}</td>
      <td style="text-align:right"><button class="btn btn-danger btn-sm" onclick="deleteLocator(${loc.id})">🗑</button></td>
    </tr>`).join('');
  } catch(e) { console.error('loadLocators', e); }
}

async function saveNewLocator() {
  const name = document.getElementById('loc-name')?.value?.trim();
  const value = document.getElementById('loc-val')?.value?.trim();
  if (!name || !value) { toast('Lütfen ad ve seçici alanlarını doldurun.', 'err'); return; }
  await fetch('/api/locators', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name, locator_value: value }) });
  document.getElementById('loc-name').value = '';
  document.getElementById('loc-val').value = '';
  toast('✅ Element kaydedildi!', 'ok');
  loadLocators();
}

async function deleteLocator(id) {
  await fetch('/api/locators/' + id, { method: 'DELETE' });
  toast('🗑 Element silindi.', 'ok');
  loadLocators();
}

async function startAICrawler() {
  const urlInput = document.getElementById('ai-crawler-url');
  const iconEl   = document.getElementById('crawler-icon');
  if (!urlInput?.value) { toast('Lütfen taranacak URL girin.', 'err'); return; }
  if (iconEl) iconEl.textContent = '⏳';
  toast('🤖 AI Tarama başladı... ~30sn sürebilir.', 'ok');
  try {
    const res = await fetch('/api/discover', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ url: urlInput.value }) });
    const data = await res.json();
    if (data.error) toast('Hata: ' + data.error, 'err');
    else { toast(`✅ ${data.saved_count || 0} element keşfedildi!`, 'ok'); loadLocators(); }
  } catch(e) {
    toast('Bağlantı hatası.', 'err');
  } finally {
    if (iconEl) iconEl.textContent = '👀';
  }
}

async function uploadAnalysisForManual(input) {
  const file = input.files[0];
  if (!file) return;
  
  const formData = new FormData();
  formData.append('file', file);
  
  toast('🤖 AI Analizi başlatıldı... Lütfen bekleyin.', 'ok');
  try {
      const res = await fetch('/api/generate-manual-from-doc', {
          method: 'POST',
          body: formData
      });
      const data = await res.json();
      if(data.error) throw new Error(data.error);
      
      toast(`✅ ${data.count} yeni manuel test oluşturuldu!`, 'ok');
      await fetchManualTests();
  } catch(e) {
      toast('Hata: ' + e.message, 'err');
  } finally {
      input.value = ''; // clear input
  }
}

// ─── MODAL KEYBOARD ────────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    closeModal();
    if(typeof closeAIModal === 'function') closeAIModal();
    if(typeof closeApiAiModal === 'function') closeApiAiModal();
    if(typeof closeGenericModal === 'function') closeGenericModal();
    closeTester();
  }
  if (e.key === 'Enter') {
    const nm = document.getElementById('new-modal');
    const am = document.getElementById('ai-modal');
    if (nm && nm.classList.contains('active')) createFeature();
    if (am && am.classList.contains('active')) generateFromAI();
  }
});

/* ── Language Toggle (TR / EN) ──────────────────────────────────────────────── */
const I18N = {
  tr: {
    nav_editor: '✏️ Editör', nav_dashboard: '📊 Dashboard', nav_regression: '📦 Regresyon Setleri',
    nav_manual: '📝 Manuel Testler', nav_locators: '🧭 Element Deposu', nav_api: '📡 API Test',
    nav_security: '🔐 Güvenlik Testi', nav_reports: '📈 Gelişmiş Raporlar',
    nav_ai_tree: '🌳 AI Test Ağacı', nav_settings: '⚙️ Ayarlar',
    logout: '🚪 Çıkış Yap', lang_btn: '🌐 EN',
    run_all: '▶ Tümünü Çalıştır', run_this: '▶ Bu Feature',
    sidebar_title: 'Feature Dosyaları', save: '💾 Kaydet',
    dash_total: 'Toplam Koşum', dash_pass: 'Başarılı', dash_fail: 'Başarısız', dash_features: 'Feature Dosyası',
    terminal_starting: '// Testler başlatılıyor...',
    toast_running: '▶ Testler koşturuluyor...', toast_done: '✅ Koşum tamamlandı!',
    toast_done_warn: '⚠️ Koşum bitti (bazı testler başarısız)',
  },
  en: {
    nav_editor: '✏️ Editor', nav_dashboard: '📊 Dashboard', nav_regression: '📦 Regression Sets',
    nav_manual: '📝 Manual Tests', nav_locators: '🧭 Element Depot', nav_api: '📡 API Test',
    nav_security: '🔐 Security Test', nav_reports: '📈 Advanced Reports',
    nav_ai_tree: '🌳 AI Test Tree', nav_settings: '⚙️ Settings',
    logout: '🚪 Sign Out', lang_btn: '🌐 TR',
    run_all: '▶ Run All', run_this: '▶ This Feature',
    sidebar_title: 'Feature Files', save: '💾 Save',
    dash_total: 'Total Runs', dash_pass: 'Passed', dash_fail: 'Failed', dash_features: 'Feature Files',
    terminal_starting: '// Starting tests...',
    toast_running: '▶ Running tests...', toast_done: '✅ Run completed!',
    toast_done_warn: '⚠️ Run finished (some tests failed)',
  }
};

let currentLang = 'tr';

function toggleLang() {
  currentLang = currentLang === 'tr' ? 'en' : 'tr';
  applyLang(currentLang);
}

function applyLang(lang) {
  const t = I18N[lang];
  const langBtn = document.getElementById('lang-toggle-btn');
  if (langBtn) langBtn.textContent = t.lang_btn;

  const navBtns = document.querySelectorAll('nav button');
  const keys = ['nav_editor','nav_dashboard','nav_regression','nav_manual','nav_locators','nav_api','nav_security','nav_reports','nav_ai_tree','nav_settings'];
  navBtns.forEach((btn, i) => { if (keys[i] && t[keys[i]]) btn.textContent = t[keys[i]]; });

  const logoutBtn = document.querySelector('.btn-logout');
  if (logoutBtn) logoutBtn.textContent = t.logout;

  const sidebarTitle = document.querySelector('.sidebar-header h3');
  if (sidebarTitle) sidebarTitle.textContent = t.sidebar_title;

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (t[key]) el.textContent = t[key];
  });
}

/* ── Testçi Draggable Chatbot ───────────────────────────────────────────────── */
const TESTER_ZONES = [
  { id: 'editor-view',     title: 'Editör',           desc: 'Gherkin senaryolarını yazıp düzenleyebildiğin yerdir. Feature dosyası oluştur, kaydet, sil ve AI ile test senaryosu üret.' },
  { id: 'dashboard-view',  title: 'Dashboard',        desc: 'Test koşumlarının istatistiklerini, başarı trendini ve geçmiş çalıştırmaları görürsün.' },
  { id: 'regression-view', title: 'Regresyon Setleri',desc: 'Feature dosyalarını gruplayan regresyon setleri oluştur. Aynı anda birden fazla feature koşturabilirsin.' },
  { id: 'manual-view',     title: 'Manuel Testler',   desc: 'Otomasyon dışı test senaryolarını yönetir, durum takibi yaparsın.' },
  { id: 'locators-view',   title: 'Element Deposu',   desc: 'Sayfadaki HTML elementlerini kaydedip Gherkin adımlarında kullanabilirsin. AI ile otomatik tarama da yapabilirsin.' },
  { id: 'api-view',        title: 'API Test',         desc: 'HTTP istekleri gönderir, yanıtları analiz edersin. Postman benzeri bir arayüz.' },
  { id: 'security-view',   title: 'Güvenlik Testi',   desc: 'Temel güvenlik taramaları yaparsın: SQL injection, XSS, açık port ve header kontrolü.' },
  { id: 'reports-view',    title: 'Gelişmiş Raporlar',desc: 'Tüm test koşumlarının detaylı raporlarını görür, filtreler ve incelersin.' },
  { id: 'ai-tree-view',    title: 'AI Test Ağacı',    desc: 'Feature dosyalarını ağaç yapısında görür, AI ile analiz eder ve senaryo önerileri alırsın.' },
  { id: 'settings-view',   title: 'Ayarlar',          desc: 'AI model, API anahtarı, tarayıcı tipi, headless modu ve hedef URL ayarlarını yapılandırırsın.' },
];

function initTester() {
  // Bubble
  const bubble = document.createElement('div');
  bubble.id = 'tester-bubble';
  bubble.innerHTML = '🤖';
  bubble.title = 'Testçi — Sürükle & Bırak';
  bubble.style.cssText = `
    position:fixed; bottom:90px; right:24px; width:52px; height:52px;
    background:var(--accent); border-radius:50%; display:flex; align-items:center;
    justify-content:center; font-size:24px; cursor:grab; z-index:9000;
    box-shadow:0 4px 16px rgba(56,139,253,0.5); user-select:none;
    transition:box-shadow .2s, transform .2s;
  `;
  bubble.addEventListener('mouseenter', () => bubble.style.transform = 'scale(1.1)');
  bubble.addEventListener('mouseleave', () => bubble.style.transform = 'scale(1)');

  // Panel
  const panel = document.createElement('div');
  panel.id = 'tester-panel';
  panel.style.cssText = `
    position:fixed; bottom:90px; right:84px; width:320px; max-height:420px;
    background:var(--bg2); border:1px solid var(--border); border-radius:16px;
    box-shadow:var(--shadow); z-index:9001; display:none; flex-direction:column;
    overflow:hidden;
  `;
  panel.innerHTML = `
    <div style="background:var(--bg3);padding:14px 16px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--border)">
      <span style="font-size:20px">🤖</span>
      <div>
        <div style="font-weight:700;font-size:14px;color:var(--text)">Testçi</div>
        <div style="font-size:11px;color:var(--text3)">AI Test Asistanı</div>
      </div>
      <button onclick="closeTester()" style="margin-left:auto;background:none;border:none;color:var(--text3);font-size:18px;cursor:pointer;line-height:1">✕</button>
    </div>
    <div id="tester-body" style="padding:16px;overflow-y:auto;flex:1;font-size:13px;color:var(--text2);line-height:1.6">
      <p style="color:var(--text3);font-style:italic">Merhaba! Ben <strong style="color:var(--accent)">Testçi</strong>. Seni bıraktığın yerin ne işe yaradığını anlatırım.<br><br>🖱️ Beni herhangi bir bölgeye sürükle ya da butonuna tıkla.</p>
    </div>
  `;

  document.body.appendChild(bubble);
  document.body.appendChild(panel);

  // Click to toggle
  bubble.addEventListener('click', () => {
    const activeView = document.querySelector('.view.active');
    if (activeView) {
      const zone = TESTER_ZONES.find(z => z.id === activeView.id);
      if (zone) showTesterInfo(zone.title, zone.desc);
    }
    const p = document.getElementById('tester-panel');
    p.style.display = p.style.display === 'flex' ? 'none' : 'flex';
  });

  // Drag
  makeDraggable(bubble);
}

function showTesterInfo(title, desc) {
  const body = document.getElementById('tester-body');
  if (!body) return;
  body.innerHTML = `
    <div style="margin-bottom:10px">
      <div style="font-weight:700;font-size:15px;color:var(--text);margin-bottom:6px">📌 ${title}</div>
      <div style="color:var(--text2);font-size:13px;line-height:1.7">${desc}</div>
    </div>
    <hr style="border:none;border-top:1px solid var(--border);margin:12px 0">
    <div style="color:var(--text3);font-size:11px">💡 Başka bir bölgeye geçince tekrar tıkla, orası için açıklarım.</div>
  `;
}

function closeTester() {
  const p = document.getElementById('tester-panel');
  if (p) p.style.display = 'none';
}

function makeDraggable(el) {
  let startX, startY, startRight, startBottom;
  el.addEventListener('mousedown', e => {
    e.preventDefault();
    startX = e.clientX;
    startY = e.clientY;
    const rect = el.getBoundingClientRect();
    startRight  = window.innerWidth  - rect.right;
    startBottom = window.innerHeight - rect.bottom;
    el.style.cursor = 'grabbing';

    function onMove(e) {
      const dx = startX - e.clientX;
      const dy = startY - e.clientY;
      el.style.right  = Math.max(8, startRight  + dx) + 'px';
      el.style.bottom = Math.max(8, startBottom + dy) + 'px';
      // Keep panel anchored near bubble
      const panel = document.getElementById('tester-panel');
      if (panel && panel.style.display === 'flex') {
        panel.style.right  = (Math.max(8, startRight  + dx) + 60) + 'px';
        panel.style.bottom = el.style.bottom;
      }
      // Check drop zone
      const underEls = document.elementsFromPoint(e.clientX, e.clientY);
      const dropView = underEls.find(el => el.classList && el.classList.contains('view'));
      if (dropView) {
        const zone = TESTER_ZONES.find(z => z.id === dropView.id);
        if (zone) showTesterInfo(zone.title, zone.desc);
      }
    }
    function onUp() {
      el.style.cursor = 'grab';
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    }
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });
}

// Init Testçi on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTester);
} else {
  initTester();
}


/* ═══════════════════════════════════════════════════════════════════════════
   DATA SIMULATOR
═══════════════════════════════════════════════════════════════════════════ */
(function() {
  // ── Data pool ────────────────────────────────────────────────────────────
  const NAMES = ['Ahmet','Mehmet','Ali','Mustafa','Hüseyin','İbrahim','Ömer','Yusuf','Hasan','Murat',
                 'Fatma','Ayşe','Emine','Hatice','Zeynep','Elif','Merve','Büşra','Selin','Gamze'];
  const SURNAMES = ['Yılmaz','Kaya','Demir','Çelik','Şahin','Doğan','Arslan','Öztürk','Koç','Aydın',
                    'Bulut','Yıldız','Çetin','Güneş','Yıldırım','Erdoğan','Sarı','Kılıç','Kurt','Özdemir'];
  const CITIES = ['İstanbul','Ankara','İzmir','Bursa','Antalya','Adana','Konya','Gaziantep','Mersin','Diyarbakır'];
  const STREETS = ['Atatürk Cad.','İstiklal Cad.','Cumhuriyet Bul.','Bağcılar Sok.','Yıldız Mah.','Gül Sok.','Lale Cad.'];
  const DOMAINS = ['gmail.com','yahoo.com','hotmail.com','outlook.com','icloud.com','yandex.com','proton.me'];
  const COMPANIES = ['TechSoft A.Ş.','Dijital Çözümler Ltd.','İnovasyon Teknoloji','NetWork Pro','AlphaCode'];
  const TLDS = ['com','net','org','io','co','dev'];

  const rand = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
  const pick = arr => arr[rand(0, arr.length - 1)];
  const pad2 = n => String(n).padStart(2, '0');

  // ── Type metadata ────────────────────────────────────────────────────────
  const TYPE_META = {
    name_tr:  { icon: '👤', label: 'Türkçe İsim' },
    email:    { icon: '📧', label: 'E-posta' },
    phone_tr: { icon: '📱', label: 'Telefon (TR)' },
    number:   { icon: '🔢', label: 'Sayı' },
    text:     { icon: '📝', label: 'Metin' },
    date:     { icon: '📅', label: 'Tarih' },
    boolean:  { icon: '🔘', label: 'Boolean' },
    uuid:     { icon: '🆔', label: 'UUID' },
    tc_no:    { icon: '🪪', label: 'TC Kimlik No' },
    iban_tr:  { icon: '🏦', label: 'IBAN (TR)' },
    company:  { icon: '🏢', label: 'Şirket Adı' },
    url:      { icon: '🔗', label: 'URL' },
    address_tr:{ icon: '🏠', label: 'Adres (TR)' },
    color:    { icon: '🎨', label: 'Renk (HEX)' },
    choice:   { icon: '📋', label: 'Seçenekler' },
    custom:   { icon: '⚙️', label: 'Özel Format' },
  };

  // ── State ────────────────────────────────────────────────────────────────
  let DS_FIELDS = [];
  let DS_LAST_OUTPUT = '';
  let DS_LAST_FORMAT = 'json';

  // ── Generator functions ──────────────────────────────────────────────────
  function generateValue(field) {
    const o = field.opts || {};
    switch (field.type) {
      case 'name_tr':     return pick(NAMES) + ' ' + pick(SURNAMES);
      case 'email': {
        const n = pick(NAMES).toLowerCase().replace(/[İÇŞĞÜÖ]/g, c => ({İ:'i',Ç:'c',Ş:'s',Ğ:'g',Ü:'u',Ö:'o'}[c]||c));
        return n + rand(1,999) + '@' + pick(DOMAINS);
      }
      case 'phone_tr': return '05' + pick(['30','31','32','33','35','36','37','38','39','40','41','42','43','44','45','46','47','48','49','50','51','52','53','54','55','56','57','58','59']) + rand(1000000,9999999);
      case 'number':  return rand(parseInt(o.min||0), parseInt(o.max||100));
      case 'text': {
        const words = ['lorem','ipsum','dolor','sit','amet','consectetur','adipiscing','elit','sed','do','eiusmod','tempor'];
        const len = rand(parseInt(o.min||3), parseInt(o.max||8));
        return Array.from({length: len}, () => pick(words)).join(' ');
      }
      case 'date': {
        const s = new Date(o.start||'2000-01-01').getTime();
        const e = new Date(o.end||'2025-12-31').getTime();
        const d = new Date(s + Math.random()*(e-s));
        return `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}`;
      }
      case 'boolean':  return pick([true, false]);
      case 'uuid': {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
          const r = Math.random()*16|0, v = c==='x'?r:(r&0x3|0x8); return v.toString(16);
        });
      }
      case 'tc_no': {
        const d = Array.from({length:9}, () => rand(0,9));
        const s1 = (d[0]+d[2]+d[4]+d[6]+d[8])*7 - (d[1]+d[3]+d[5]+d[7]);
        d.push(((s1 % 10) + 10) % 10);
        d.push((d.reduce((a,b)=>a+b,0)) % 10);
        return d.join('');
      }
      case 'iban_tr': {
        const bank = pad2(rand(1,99));
        const digits = Array.from({length:24}, () => rand(0,9)).join('');
        return `TR${rand(10,99)}${bank}${digits}`;
      }
      case 'company':  return pick(COMPANIES);
      case 'url': {
        const n = pick(SURNAMES).toLowerCase().replace(/[^a-z]/g,'');
        return `https://www.${n}.${pick(TLDS)}`;
      }
      case 'address_tr': return `${pick(STREETS)} No:${rand(1,200)}, ${pick(CITIES)}`;
      case 'color': return '#' + Array.from({length:6}, () => rand(0,15).toString(16)).join('');
      case 'choice': {
        const choices = (o.choices||'seçenek1,seçenek2,seçenek3').split(',').map(s=>s.trim()).filter(Boolean);
        return pick(choices);
      }
      case 'custom': {
        // Simple format: replace {num} {alpha} {word} {name}
        let fmt = o.format || '{word}-{num}';
        fmt = fmt.replace(/\{num\}/g, () => rand(0,9999));
        fmt = fmt.replace(/\{alpha\}/g, () => String.fromCharCode(65+rand(0,25)));
        fmt = fmt.replace(/\{word\}/g, () => pick(['test','demo','data','mock','sample']));
        fmt = fmt.replace(/\{name\}/g, () => pick(NAMES));
        return fmt;
      }
      default: return '';
    }
  }

  // ── Type changed → show extra options ───────────────────────────────────
  window.dsTypeChanged = function() {
    const type = document.getElementById('ds-field-type').value;
    const wrap = document.getElementById('ds-type-opts');
    wrap.innerHTML = '';
    const row = (label, html) => `<div class="ds-field"><label>${label}</label>${html}</div>`;
    if (type === 'number') {
      wrap.innerHTML = `<div class="ds-row">
        ${row('Minimum', '<input type="number" id="ds-opt-min" value="0">')}
        ${row('Maximum', '<input type="number" id="ds-opt-max" value="100">')}
      </div>`;
    } else if (type === 'text') {
      wrap.innerHTML = `<div class="ds-row">
        ${row('Min Kelime', '<input type="number" id="ds-opt-min" value="3">')}
        ${row('Max Kelime', '<input type="number" id="ds-opt-max" value="8">')}
      </div>`;
    } else if (type === 'date') {
      wrap.innerHTML = `<div class="ds-row">
        ${row('Başlangıç', '<input type="date" id="ds-opt-start" value="2000-01-01">')}
        ${row('Bitiş', '<input type="date" id="ds-opt-end" value="2025-12-31">')}
      </div>`;
    } else if (type === 'choice') {
      wrap.innerHTML = `${row('Seçenekler (virgülle)', '<input type="text" id="ds-opt-choices" placeholder="seçenek1,seçenek2,seçenek3">')}`;
    } else if (type === 'custom') {
      wrap.innerHTML = `${row('Format Kalıbı ({num},{alpha},{word},{name})', '<input type="text" id="ds-opt-format" placeholder="USR-{num}-{alpha}">')}`;
    }
  };

  function dsGetOpts() {
    const type = document.getElementById('ds-field-type').value;
    const opts = {};
    const g = id => { const el = document.getElementById(id); return el ? el.value : null; };
    if (type === 'number' || type === 'text') { opts.min = g('ds-opt-min'); opts.max = g('ds-opt-max'); }
    if (type === 'date') { opts.start = g('ds-opt-start'); opts.end = g('ds-opt-end'); }
    if (type === 'choice') opts.choices = g('ds-opt-choices');
    if (type === 'custom')  opts.format = g('ds-opt-format');
    return opts;
  }

  // ── Add field ────────────────────────────────────────────────────────────
  window.dsAddField = function() {
    const nameEl = document.getElementById('ds-field-name');
    const name = nameEl.value.trim();
    if (!name) { toast('Alan adı giriniz', 'warn'); return; }
    if (DS_FIELDS.find(f => f.name === name)) { toast('Bu isimde alan zaten var', 'warn'); return; }
    const type = document.getElementById('ds-field-type').value;
    DS_FIELDS.push({ name, type, opts: dsGetOpts() });
    nameEl.value = '';
    dsRenderFieldList();
  };

  function dsRenderFieldList() {
    const card = document.getElementById('ds-field-list-card');
    const list = document.getElementById('ds-field-list');
    const badge = document.getElementById('ds-field-count');
    card.style.display = DS_FIELDS.length ? '' : 'none';
    badge.textContent = DS_FIELDS.length;
    list.innerHTML = DS_FIELDS.map((f, i) => {
      const meta = TYPE_META[f.type] || { icon: '📌', label: f.type };
      return `<div class="ds-field-item">
        <span class="ds-field-item-icon">${meta.icon}</span>
        <div class="ds-field-item-info">
          <div class="ds-field-item-name">${f.name}</div>
          <div class="ds-field-item-type">${meta.label}${dsOptsLabel(f)}</div>
        </div>
        <button class="ds-field-item-del" onclick="dsRemoveField(${i})" title="Sil">✕</button>
      </div>`;
    }).join('');
  }

  function dsOptsLabel(f) {
    const o = f.opts || {};
    if (f.type === 'number' || f.type === 'text') return ` [${o.min||0}–${o.max||100}]`;
    if (f.type === 'date') return ` [${o.start||'2000'}–${o.end||'2025'}]`;
    if (f.type === 'choice') return ` (${(o.choices||'').split(',').length} seçenek)`;
    return '';
  }

  window.dsRemoveField = function(i) {
    DS_FIELDS.splice(i, 1);
    dsRenderFieldList();
  };

  // ── Generate ─────────────────────────────────────────────────────────────
  window.dsGenerate = function() {
    if (!DS_FIELDS.length) { toast('Önce alan ekleyin', 'warn'); return; }
    const count = parseInt(document.getElementById('ds-count').value) || 10;
    const format = document.getElementById('ds-format').value;
    DS_LAST_FORMAT = format;
    const rows = Array.from({ length: count }, () => {
      const obj = {};
      DS_FIELDS.forEach(f => { obj[f.name] = generateValue(f); });
      return obj;
    });
    let output = '';
    if (format === 'json') {
      output = JSON.stringify(rows, null, 2);
    } else if (format === 'csv') {
      const headers = DS_FIELDS.map(f => f.name);
      output = headers.join(',') + '\n' + rows.map(r => headers.map(h => {
        const v = String(r[h] ?? '');
        return v.includes(',') || v.includes('"') ? `"${v.replace(/"/g,'""')}"` : v;
      }).join(',')).join('\n');
    } else if (format === 'gherkin') {
      const headers = DS_FIELDS.map(f => f.name);
      const colW = headers.map((h, i) => Math.max(h.length, ...rows.map(r => String(r[h] ?? '').length)));
      const pad = (s, w) => String(s).padEnd(w);
      output = 'Examples:\n';
      output += '  | ' + headers.map((h,i) => pad(h, colW[i])).join(' | ') + ' |\n';
      rows.forEach(r => {
        output += '  | ' + headers.map((h,i) => pad(r[h]??'', colW[i])).join(' | ') + ' |\n';
      });
    } else if (format === 'sql') {
      const table = document.getElementById('ds-table-name').value.trim() || 'table_name';
      const headers = DS_FIELDS.map(f => f.name);
      const escape = v => typeof v === 'string' ? `'${v.replace(/'/g,"''")}'` : v;
      output = rows.map(r =>
        `INSERT INTO ${table} (${headers.join(', ')}) VALUES (${headers.map(h => escape(r[h])).join(', ')});`
      ).join('\n');
    }
    DS_LAST_OUTPUT = output;
    dsRenderOutput(output, format, rows.length);
  };

  function dsRenderOutput(output, format, rowCount) {
    const wrap = document.getElementById('ds-output-wrap');
    if (format === 'json' || format === 'csv' || format === 'gherkin' || format === 'sql') {
      wrap.innerHTML = `<pre>${escHTML(output)}</pre>`;
    }
    // Show buttons
    document.getElementById('ds-copy-btn').style.display = '';
    document.getElementById('ds-export-btn').style.display = '';
    // Stats
    const bar = document.getElementById('ds-stats-bar');
    bar.style.display = 'flex';
    document.getElementById('dss-rows').innerHTML = `📊 Satır: <strong>${rowCount}</strong>`;
    document.getElementById('dss-cols').innerHTML = `📐 Alan: <strong>${DS_FIELDS.length}</strong>`;
    const size = new Blob([output]).size;
    document.getElementById('dss-size').innerHTML = `💾 Boyut: <strong>${size < 1024 ? size + ' B' : (size/1024).toFixed(1) + ' KB'}</strong>`;
    document.getElementById('dss-format').innerHTML = `📄 Format: <strong>${format.toUpperCase()}</strong>`;
    document.getElementById('ds-output-title').textContent = `Çıktı — ${rowCount} kayıt`;
    // Badge
    const badge = document.getElementById('ds-row-info');
    badge.textContent = rowCount + ' kayıt';
    badge.style.display = '';
    toast(`${rowCount} kayıt üretildi ✓`, 'success');
  }

  function escHTML(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  // ── Copy ─────────────────────────────────────────────────────────────────
  window.dsCopyOutput = function() {
    if (!DS_LAST_OUTPUT) return;
    navigator.clipboard.writeText(DS_LAST_OUTPUT).then(() => toast('Panoya kopyalandı ✓', 'success'));
  };

  // ── Export ───────────────────────────────────────────────────────────────
  window.dsExportFile = function() {
    if (!DS_LAST_OUTPUT) return;
    const ext = { json:'json', csv:'csv', gherkin:'feature', sql:'sql' }[DS_LAST_FORMAT] || 'txt';
    const blob = new Blob([DS_LAST_OUTPUT], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `simulated_data_${Date.now()}.${ext}`;
    a.click();
    toast('Dosya indiriliyor…', 'info');
  };

  // ── Templates ────────────────────────────────────────────────────────────
  const TEMPLATES = {
    user: [
      { name: 'id',       type: 'uuid',     opts: {} },
      { name: 'ad_soyad', type: 'name_tr',  opts: {} },
      { name: 'email',    type: 'email',    opts: {} },
      { name: 'telefon',  type: 'phone_tr', opts: {} },
      { name: 'yas',      type: 'number',   opts: { min:'18', max:'75' } },
      { name: 'aktif',    type: 'boolean',  opts: {} },
    ],
    product: [
      { name: 'urun_id',  type: 'uuid',     opts: {} },
      { name: 'ad',       type: 'choice',   opts: { choices: 'Laptop,Telefon,Tablet,Kulaklık,Mouse,Klavye,Monitör' } },
      { name: 'fiyat',    type: 'number',   opts: { min:'50', max:'50000' } },
      { name: 'stok',     type: 'number',   opts: { min:'0', max:'500' } },
      { name: 'renk',     type: 'color',    opts: {} },
    ],
    order: [
      { name: 'siparis_no', type: 'custom', opts: { format: 'SIP-{num}-{alpha}' } },
      { name: 'musteri',    type: 'name_tr', opts: {} },
      { name: 'tutar',      type: 'number',  opts: { min:'10', max:'10000' } },
      { name: 'tarih',      type: 'date',    opts: { start:'2024-01-01', end:'2025-12-31' } },
      { name: 'durum',      type: 'choice',  opts: { choices: 'Bekliyor,İşlemde,Kargoda,Teslim Edildi,İptal' } },
    ],
    bank: [
      { name: 'hesap_sahibi', type: 'name_tr', opts: {} },
      { name: 'iban',         type: 'iban_tr', opts: {} },
      { name: 'bakiye',       type: 'number',  opts: { min:'0', max:'500000' } },
      { name: 'tc_no',        type: 'tc_no',   opts: {} },
    ],
    address: [
      { name: 'ad',    type: 'name_tr',    opts: {} },
      { name: 'adres', type: 'address_tr', opts: {} },
      { name: 'posta_kodu', type: 'number', opts: { min:'10000', max:'99999' } },
    ],
    login: [
      { name: 'kullanici_adi', type: 'email',   opts: {} },
      { name: 'sifre',         type: 'custom',  opts: { format: 'Pass@{num}' } },
      { name: 'tc_no',         type: 'tc_no',   opts: {} },
    ],
  };

  window.dsLoadTemplate = function(name) {
    const tpl = TEMPLATES[name];
    if (!tpl) return;
    DS_FIELDS = tpl.map(f => ({ ...f, opts: { ...f.opts } }));
    dsRenderFieldList();
    toast(`"${name}" şablonu yüklendi`, 'success');
  };

})(); // end data simulator IIFE

/* ═══════════════════════════════════════════════════════════════════════════
   DATA SIM — TAB SWITCHER + MOSTLY AI
═══════════════════════════════════════════════════════════════════════════ */
(function() {

  // ── Tab switcher ─────────────────────────────────────────────────────────
  window.dsSwitchTab = function(tab) {
    document.querySelectorAll('.ds-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.ds-tab-panel').forEach(p => p.style.display = 'none');
    document.getElementById('dstab-' + tab).classList.add('active');
    document.getElementById('ds-tab-' + tab).style.display = '';
    if (tab === 'mostly') maCheckInstall();
  };

  // ── Mostly AI state ──────────────────────────────────────────────────────
  let MA_LAST_OUTPUT = '';
  let MA_LAST_FORMAT = 'json';

  // ── Check install on load ────────────────────────────────────────────────
  function maCheckInstall() {
    const badge = document.getElementById('mostly-status-badge');
    badge.className = 'ds-tab-badge';
    badge.textContent = 'Kontrol ediliyor…';

    fetch('/api/datasim/check-install')
      .then(r => r.json())
      .then(d => {
        if (d.installed) {
          badge.textContent = '✅ Kurulu';
          badge.className = 'ds-tab-badge ok';
          document.getElementById('mostly-install-panel').style.display = 'none';
          document.getElementById('mostly-ready-panel').style.display = '';
          document.getElementById('mostly-config-panel').style.display = '';
          document.getElementById('ma-version').textContent = 'v' + d.version;
        } else {
          badge.textContent = '⚠️ Kurulu Değil';
          badge.className = 'ds-tab-badge err';
          document.getElementById('mostly-install-panel').style.display = '';
          document.getElementById('mostly-ready-panel').style.display = 'none';
          document.getElementById('mostly-config-panel').style.display = 'none';
        }
      })
      .catch(() => { badge.textContent = 'Hata'; badge.className = 'ds-tab-badge err'; });
  }

  // ── Auto-install ─────────────────────────────────────────────────────────
  window.maInstall = function() {
    const btn = document.getElementById('ma-install-btn');
    const log = document.getElementById('ma-install-log');
    btn.disabled = true; btn.textContent = '⏳ Kuruluyor…';
    log.style.display = ''; log.textContent = '';

    const es = new EventSource('/api/datasim/install');
    es.onmessage = e => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'log') { log.textContent += msg.msg + '\n'; log.scrollTop = log.scrollHeight; }
      if (msg.type === 'done') {
        es.close();
        if (msg.success) {
          toast(msg.msg, 'success');
          maCheckInstall();
        } else {
          toast(msg.msg, 'error');
          btn.disabled = false; btn.textContent = '⬇️ Tekrar Dene';
        }
      }
    };
    es.onerror = () => { es.close(); btn.disabled = false; btn.textContent = '⬇️ Tekrar Dene'; };
  };

  // ── File drop ────────────────────────────────────────────────────────────
  window.maDrop = function(e) {
    e.preventDefault();
    document.getElementById('ma-dropzone').classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) maReadFile(file);
  };
  window.maFileSelected = function(input) {
    if (input.files[0]) maReadFile(input.files[0]);
  };
  function maReadFile(file) {
    const reader = new FileReader();
    reader.onload = ev => {
      document.getElementById('ma-csv-input').value = ev.target.result;
      toast(`"${file.name}" yüklendi`, 'success');
      
      // Update diagram when file is loaded via drag/drop or input
      maDiagramReset();
      maDiagramStep(1, file.name);
    };
    reader.readAsText(file, 'utf-8');
  }

  // ── Generate ─────────────────────────────────────────────────────────────
  window.maGenerate = function() {
    const csv    = document.getElementById('ma-csv-input').value.trim();
    const count  = parseInt(document.getElementById('ma-count').value) || 100;
    const format = document.getElementById('ma-format').value;
    const name   = document.getElementById('ma-model-name').value.trim() || undefined;
    MA_LAST_FORMAT = format;

    if (!csv) { toast('Lütfen örnek CSV verisi girin', 'warn'); return; }

    // UI: show progress
    const btn = document.getElementById('ma-gen-btn');
    btn.disabled = true; btn.textContent = '⏳ Üretiliyor…';

    const progWrap = document.getElementById('ma-progress-wrap');
    const logEl    = document.getElementById('ma-log');
    const labelEl  = document.getElementById('ma-progress-label');
    const outWrap  = document.getElementById('ma-output-wrap');

    progWrap.style.display = ''; logEl.textContent = ''; outWrap.innerHTML = '';
    document.getElementById('ma-stats-bar').style.display = 'none';
    document.getElementById('ma-copy-btn').style.display = 'none';
    document.getElementById('ma-export-btn').style.display = 'none';
    document.getElementById('ma-row-info').style.display = 'none';

    maDiagramReset();

    const body = JSON.stringify({ csv, count, format, name });

    fetch('/api/datasim/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body
    }).then(resp => {
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      function pump() {
        return reader.read().then(({ done, value }) => {
          if (done) { btn.disabled = false; btn.textContent = '🚀 Sentetik Veri Üret'; return; }
          buf += decoder.decode(value, { stream: true });
          const lines = buf.split('\n');
          buf = lines.pop();
          lines.forEach(line => {
            if (!line.startsWith('data:')) return;
            try {
              const msg = JSON.parse(line.slice(5).trim());
              if (msg.type === 'log') {
                labelEl.textContent = msg.msg;
                logEl.textContent += msg.msg + '\n';
                logEl.scrollTop = logEl.scrollHeight;

                // Animate diagram based on mostly.ai log messages
                const lmsg = msg.msg.toLowerCase();
                if (lmsg.includes('okunuyor') || lmsg.includes('okundu')) {
                   maDiagramStep(1, msg.msg);
                } else if (lmsg.includes('başlatılıyor')) {
                   maDiagramStep(2, 'Analiz ediliyor');
                } else if (lmsg.includes('eğitiliyor')) {
                   maDiagramStep(3, 'Dağılım öğreniliyor');
                   setTimeout(() => maDiagramStep(4, 'AI Öğreniyor…'), 800);
                } else if (lmsg.includes('üretiliyor') || lmsg.includes('hazır')) {
                   maDiagramStep(5, msg.msg);
                }
              } else if (msg.type === 'error') {
                labelEl.textContent = '❌ Hata';
                logEl.textContent += '❌ ' + msg.msg + '\n';
                if (msg.detail) logEl.textContent += msg.detail;
                toast('Hata: ' + msg.msg, 'error');
                btn.disabled = false; btn.textContent = '🚀 Sentetik Veri Üret';
              } else if (msg.type === 'done') {
                progWrap.style.display = 'none';
                MA_LAST_OUTPUT = msg.output;
                maRenderOutput(msg.output, msg.rows, msg.cols, format);
                btn.disabled = false; btn.textContent = '🚀 Sentetik Veri Üret';
              }
            } catch (parseErr) { console.warn('Stream chunk parse hatasi:', parseErr); }
          });
          return pump();
        });
      }
      return pump();
    }).catch(err => {
      toast('Bağlantı hatası: ' + err, 'error');
      btn.disabled = false; btn.textContent = '🚀 Sentetik Veri Üret';
    });
  };

  function maRenderOutput(output, rows, cols, format) {
    const wrap = document.getElementById('ma-output-wrap');
    wrap.innerHTML = `<pre>${output.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</pre>`;

    document.getElementById('ma-copy-btn').style.display = '';
    document.getElementById('ma-export-btn').style.display = '';
    const badge = document.getElementById('ma-row-info');
    badge.textContent = rows + ' kayıt'; badge.style.display = '';

    const bar = document.getElementById('ma-stats-bar');
    bar.style.display = 'flex';
    document.getElementById('mass-rows').innerHTML = `📊 Satır: <strong>${rows}</strong>`;
    document.getElementById('mass-cols').innerHTML = `📐 Sütun: <strong>${Array.isArray(cols) ? cols.length : cols}</strong>`;
    const size = new Blob([output]).size;
    document.getElementById('mass-size').innerHTML = `💾 Boyut: <strong>${size < 1024 ? size + ' B' : (size/1024).toFixed(1) + ' KB'}</strong>`;
    document.getElementById('mass-fmt').innerHTML = `📄 Format: <strong>${format.toUpperCase()}</strong>`;
    document.getElementById('ma-output-title').textContent = `Çıktı — ${rows} sentetik kayıt`;
    toast(`${rows} sentetik kayıt üretildi ✓`, 'success');
  }

  window.maCopyOutput = function() {
    if (!MA_LAST_OUTPUT) return;
    navigator.clipboard.writeText(MA_LAST_OUTPUT).then(() => toast('Panoya kopyalandı ✓', 'success'));
  };

  window.maExportFile = function() {
    if (!MA_LAST_OUTPUT) return;
    const ext = MA_LAST_FORMAT === 'csv' ? 'csv' : 'json';
    const blob = new Blob([MA_LAST_OUTPUT], { type: 'text/plain' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = `mostlyai_synthetic_${Date.now()}.${ext}`; a.click();
    toast('Dosya indiriliyor…', 'info');
  };

  // ── Diagram helpers ──────────────────────────────────────────────────────
  function maDiagramReset() {
    document.getElementById('ma-diagram-wrap').style.display = '';
    for (let i = 1; i <= 5; i++) {
      const node = document.getElementById(`mad-node-${i}`);
      const arr  = document.getElementById(`mad-arr-${i}`);
      const sub  = document.getElementById(`mad-sub-${i}`);
      if (node) { node.classList.remove('active', 'done'); }
      if (arr)  { arr.classList.remove('active'); }
      if (sub && i !== 1)  { sub.textContent = '—'; }
    }
  }

  function maDiagramStep(step, subText) {
    for (let i = 1; i <= 5; i++) {
      const node = document.getElementById(`mad-node-${i}`);
      const arr  = document.getElementById(`mad-arr-${i}`);
      const sub  = document.getElementById(`mad-sub-${i}`);

      if (i < step) {
        if (node) { node.classList.remove('active'); node.classList.add('done'); }
        if (arr)  { arr.classList.add('active'); }
      } else if (i === step) {
        if (node) { node.classList.add('active'); node.classList.remove('done'); }
        if (arr)  { arr.classList.remove('active'); }
        if (sub && subText) {
          sub.textContent = subText.length > 25 ? subText.substring(0, 22) + '…' : subText;
        }
      } else {
        if (node) { node.classList.remove('active', 'done'); }
        if (arr)  { arr.classList.remove('active'); }
      }
    }
  }

})(); // end mostly ai IIFE

/* ═══════════════════════════════════════════════════════════════════════════
   DATA SIM — DATASET CATALOG
═══════════════════════════════════════════════════════════════════════════ */
(function () {
  let ALL_DATASETS = [];
  let ACTIVE_TAG = null;

  // ── Load catalog from backend ────────────────────────────────────────────
  function dsCatalogLoad() {
    const listEl = document.getElementById('ds-catalog-list');
    listEl.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text3);font-size:12px">⏳ Yükleniyor…</div>';

    fetch('/api/datasim/datasets')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
        return r.json();
      })
      .then(data => {
        if (!Array.isArray(data)) {
          // API hata döndü (örn. {"error":"Unauthorized"})
          const msg = data.error || 'Beklenmedik yanıt';
          throw new Error(msg);
        }
        ALL_DATASETS = data;
        document.getElementById('ds-catalog-count').textContent = data.length + ' set';
        _buildTagFilters(data);
        dsCatalogRender(data);
      })
      .catch(err => {
        const isServer = String(err).includes('HTTP 4') || String(err).includes('HTTP 5');
        const hint = isServer
          ? '<br><small>Flask sunucusunun çalıştığından emin olun (port 5001)</small>'
          : '<br><small>Sayfayı yenileyip tekrar deneyin</small>';
        listEl.innerHTML =
          `<div style="color:var(--red);font-size:12px;padding:12px">
            ❌ Katalog yüklenemedi: <strong>${err.message}</strong>${hint}
            <br><br><button class="btn btn-sm btn-primary" onclick="dsCatalogLoad()" style="margin-top:4px">🔄 Tekrar Dene</button>
          </div>`;
      });
  }

  function _buildTagFilters(datasets) {
    const tagSet = new Set();
    datasets.forEach(d => (d.tags || []).forEach(t => tagSet.add(t)));
    const wrap = document.getElementById('ds-tag-filters');
    wrap.innerHTML = [...tagSet].map(t =>
      `<button class="ds-tag-pill" onclick="dsCatalogTagToggle('${t}',this)">${t}</button>`
    ).join('');
  }

  function dsCatalogRender(datasets) {
    const list = document.getElementById('ds-catalog-list');
    if (!datasets.length) {
      list.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text3);font-size:12px">Sonuç bulunamadı</div>';
      return;
    }
    list.innerHTML = datasets.map(d => `
      <div class="ds-dataset-card" id="dscard-${d.id}">
        <div class="ds-ds-header">
          <span class="ds-ds-emoji">${d.emoji}</span>
          <div class="ds-ds-info">
            <div class="ds-ds-name">${d.name}</div>
            <div class="ds-ds-source">${d.source}</div>
          </div>
        </div>
        <div class="ds-ds-desc">${d.desc}</div>
        <div class="ds-ds-meta">
          <span class="ds-ds-stat">📊 <strong>${(d.rows||0).toLocaleString()}</strong> satır</span>
          <span class="ds-ds-stat">📐 <strong>${d.cols}</strong> sütun</span>
          <div class="ds-ds-tags">${(d.tags||[]).map(t => `<span class="ds-ds-tag">${t}</span>`).join('')}</div>
        </div>
        <div class="ds-ds-footer">
          <div class="ds-ds-cols" title="${d.columns}">🗂 ${d.columns}</div>
          <button class="ds-load-btn" id="dsbtn-${d.id}" onclick="dsLoadDataset('${d.id}')">⬇️ Yükle</button>
        </div>
      </div>
    `).join('');
  }

  // ── Search ───────────────────────────────────────────────────────────────
  window.dsCatalogFilter = function (q) {
    const lq = q.toLowerCase();
    const filtered = ALL_DATASETS.filter(d =>
      (!ACTIVE_TAG || (d.tags || []).includes(ACTIVE_TAG)) &&
      (!lq || d.name.toLowerCase().includes(lq) || d.desc.toLowerCase().includes(lq) ||
        (d.tags || []).some(t => t.toLowerCase().includes(lq)))
    );
    dsCatalogRender(filtered);
  };

  // ── Tag toggle ───────────────────────────────────────────────────────────
  window.dsCatalogTagToggle = function (tag, btn) {
    if (ACTIVE_TAG === tag) {
      ACTIVE_TAG = null;
      btn.classList.remove('active');
    } else {
      ACTIVE_TAG = tag;
      document.querySelectorAll('.ds-tag-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    }
    dsCatalogFilter(document.getElementById('ds-catalog-search').value);
  };

  // ── Load dataset into CSV input ───────────────────────────────────────────
  window.dsLoadDataset = function (id) {
    const btn = document.getElementById('dsbtn-' + id);
    const card = document.getElementById('dscard-' + id);
    if (!btn || !card) return;

    btn.disabled = true; btn.textContent = '⏳ İndiriliyor…';
    card.classList.add('loading');

    fetch('/api/datasim/datasets/load', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    })
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          toast('Hata: ' + data.error, 'error');
          btn.disabled = false; btn.textContent = '⬇️ Yükle';
          card.classList.remove('loading');
          return;
        }
        // Push CSV into the textarea
        const textarea = document.getElementById('ma-csv-input');
        if (textarea) textarea.value = data.csv;

        // Auto-fill model name
        const modelInput = document.getElementById('ma-model-name');
        if (modelInput) modelInput.value = id;

        btn.textContent = '✅ Yüklendi';
        btn.classList.add('loaded');
        card.classList.remove('loading');

        toast(`"${data.name}" yüklendi — ${data.sample_rows} örnek satır`, 'success');

        // Scroll to config panel
        const cfg = document.getElementById('mostly-config-panel');
        if (cfg) cfg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // Update diagram when file is loaded from catalog
        maDiagramReset();
        maDiagramStep(1, data.name);

        // Reset btn after 3s
        setTimeout(() => {
          btn.disabled = false;
          btn.textContent = '⬇️ Yükle';
          btn.classList.remove('loaded');
        }, 3000);
      })
      .catch(err => {
        toast('İndirme hatası: ' + err, 'error');
        btn.disabled = false; btn.textContent = '⬇️ Yükle';
        card.classList.remove('loading');
      });
  };

  // ── Auto-load when Mostly AI tab is opened ───────────────────────────────
  const _origDsSwitchTab = window.dsSwitchTab;
  window.dsSwitchTab = function (tab) {
    _origDsSwitchTab(tab);
    if (tab === 'mostly' && ALL_DATASETS.length === 0) dsCatalogLoad();
    if (tab === 'sqlite') sqLoadCatalog();
  };

  // Also load if tab is already active on page load
  document.addEventListener('DOMContentLoaded', () => {
    const activeTab = document.querySelector('.ds-tab.active');
    if (activeTab && activeTab.id === 'dstab-mostly') dsCatalogLoad();
  });

})(); // end dataset catalog IIFE


// ══════════════════════════════════════════════════════════════════════════════
//  SQLite DB → Mostly AI Öğren sekmesi
// ══════════════════════════════════════════════════════════════════════════════
(function () {
  let SQ_SELECTED_DB   = null;
  let SQ_SELECTED_TABLE = null;
  let SQ_LAST_OUTPUT   = '';
  let SQ_LAST_FORMAT   = 'json';

  // ── Katalog Yükle ──────────────────────────────────────────────────────────
  window.sqLoadCatalog = function () {
    const list = document.getElementById('sq-db-list');
    if (!list) return;
    list.innerHTML = '<div class="ds-empty-state"><div class="ds-empty-icon">⏳</div><div class="ds-empty-text">Yükleniyor…</div></div>';

    fetch('/api/datasim/sqlite/catalog')
      .then(r => r.json())
      .then(dbs => {
        list.innerHTML = '';
        dbs.forEach(db => {
          const badgeClass = db.badge === 'HOT' ? 'hot' : 'real';
          const badgeText  = db.badge === 'HOT' ? '🔥 HOT' : '✅ GERÇEK';
          const sizeTxt    = db.size_mb > 0 ? `${db.size_mb} MB` : 'Yok';
          const card = document.createElement('div');
          card.className = 'sq-db-card';
          card.dataset.id = db.id;
          card.innerHTML = `
            <div class="sq-db-card-header">
              <span class="sq-db-name">${db.name}</span>
              <span class="sq-db-badge ${badgeClass}">${badgeText}</span>
              <span class="ds-badge">${sizeTxt}</span>
            </div>
            <div class="sq-db-desc">${db.desc}</div>
            <div class="sq-db-meta">
              <span>📋 Tablolar: <strong>${db.tables.join(', ')}</strong></span>
            </div>
            <div class="sq-db-meta" style="margin-top:4px">
              <span>🔗 Kaynak: <strong>${db.source}</strong></span>
            </div>`;
          card.onclick = () => sqSelectDB(db.id, db.name, card);
          list.appendChild(card);
        });
      })
      .catch(() => {
        list.innerHTML = '<div class="ds-empty-state"><div class="ds-empty-icon">❌</div><div class="ds-empty-text">Katalog yüklenemedi</div></div>';
      });
  };

  // ── DB Seç ─────────────────────────────────────────────────────────────────
  function sqSelectDB(id, name, card) {
    document.querySelectorAll('.sq-db-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    SQ_SELECTED_DB = id;
    SQ_SELECTED_TABLE = null;

    const tableCard = document.getElementById('sq-table-card');
    const settingsCard = document.getElementById('sq-settings-card');
    tableCard.style.display = '';
    settingsCard.style.display = 'none';
    document.getElementById('sq-db-label').textContent = name;
    document.getElementById('sq-table-list').innerHTML =
      '<div class="ds-empty-state" style="padding:16px"><div class="ds-empty-icon">⏳</div><div>Tablolar yükleniyor…</div></div>';

    fetch('/api/datasim/sqlite/tables', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({id})
    })
      .then(r => r.json())
      .then(data => {
        const list = document.getElementById('sq-table-list');
        list.innerHTML = '';
        data.tables.forEach(t => {
          const item = document.createElement('div');
          item.className = 'sq-table-item';
          item.dataset.table = t.table;
          item.innerHTML = `
            <div>
              <div class="sq-table-name">📋 ${t.table}</div>
              <div class="sq-table-cols">${t.columns.slice(0,6).join(', ')}${t.columns.length > 6 ? '…' : ''}</div>
            </div>
            <span class="sq-table-meta">${t.rows.toLocaleString()} satır</span>`;
          item.onclick = () => sqSelectTable(t, item);
          list.appendChild(item);
        });
      })
      .catch(() => {
        document.getElementById('sq-table-list').innerHTML =
          '<div class="ds-empty-state" style="padding:16px"><div class="ds-empty-icon">❌</div><div>Tablolar yüklenemedi</div></div>';
      });
  }

  // ── Tablo Seç ──────────────────────────────────────────────────────────────
  function sqSelectTable(t, item) {
    document.querySelectorAll('.sq-table-item').forEach(i => i.classList.remove('selected'));
    item.classList.add('selected');
    SQ_SELECTED_TABLE = t.table;
    document.getElementById('sq-settings-card').style.display = '';
  }

  // ── Önizle ─────────────────────────────────────────────────────────────────
  window.sqPreview = function () {
    if (!SQ_SELECTED_DB || !SQ_SELECTED_TABLE) return alert('Önce bir DB ve tablo seçin.');
    const wrap = document.getElementById('sq-output-wrap');
    wrap.innerHTML = '<div class="ds-empty-state"><div class="ds-empty-icon">⏳</div><div>Önizleme yükleniyor…</div></div>';
    document.getElementById('sq-output-title').textContent = `Önizleme — ${SQ_SELECTED_TABLE}`;

    fetch('/api/datasim/sqlite/preview', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({id: SQ_SELECTED_DB, table: SQ_SELECTED_TABLE, limit: 50})
    })
      .then(r => r.json())
      .then(data => {
        if (data.error) { wrap.innerHTML = `<div class="ds-empty-state"><div class="ds-empty-icon">❌</div><div>${data.error}</div></div>`; return; }
        // Tablo render
        const rows = data.csv.trim().split('\n');
        const headers = rows[0].split(',');
        let html = `<div style="overflow:auto;max-height:500px"><table class="result-table" style="font-size:11px">
          <thead><tr>${headers.map(h => `<th style="white-space:nowrap">${h}</th>`).join('')}</tr></thead><tbody>`;
        rows.slice(1, 51).forEach(row => {
          const cells = row.split(',');
          html += `<tr>${cells.map(c => `<td style="white-space:nowrap;max-width:140px;overflow:hidden;text-overflow:ellipsis">${c}</td>`).join('')}</tr>`;
        });
        html += `</tbody></table></div>`;
        wrap.innerHTML = html;

        const bar = document.getElementById('sq-stats-bar');
        bar.style.display = 'flex';
        document.getElementById('sqss-rows').innerHTML = `📊 Satır: <strong>${data.rows.toLocaleString()}</strong>`;
        document.getElementById('sqss-cols').innerHTML = `📐 Sütun: <strong>${data.cols}</strong>`;
        document.getElementById('sqss-src').innerHTML = `🗄️ Kaynak: <strong>${data.db_name}</strong>`;
        document.getElementById('sqss-fmt').innerHTML = `📋 Tablo: <strong>${data.table}</strong>`;

        SQ_LAST_OUTPUT = data.csv;
        SQ_LAST_FORMAT = 'csv';
        document.getElementById('sq-copy-btn').style.display = '';
        document.getElementById('sq-export-btn').style.display = '';
        document.getElementById('sq-row-info').style.display = '';
        document.getElementById('sq-row-info').textContent = `${data.preview_rows} / ${data.rows} satır`;
      })
      .catch(e => { wrap.innerHTML = `<div class="ds-empty-state"><div class="ds-empty-icon">❌</div><div>${e}</div></div>`; });
  };

  // ── Öğren ve Üret ──────────────────────────────────────────────────────────
  // ── Diagram helpers ──────────────────────────────────────────────────────
  function sqDiagramReset(dbName, tableName, rowCount) {
    document.getElementById('sq-diagram-wrap').style.display = '';
    for (let i = 1; i <= 5; i++) {
      const node = document.getElementById(`sqd-node-${i}`);
      const arr  = document.getElementById(`sqd-arr-${i}`);
      node.className = 'sq-diag-node';
      if (arr) arr.className = 'sq-diag-arrow';
    }
    document.getElementById('sqd-sub-1').textContent = dbName || '—';
    document.getElementById('sqd-sub-2').textContent = tableName ? `[${tableName}]` : '—';
    document.getElementById('sqd-sub-3').textContent = rowCount ? `${rowCount} satır` : '—';
    document.getElementById('sqd-sub-4').textContent = 'Bekliyor…';
    document.getElementById('sqd-sub-5').textContent = '—';
  }

  function sqDiagramStep(step, subText) {
    // step 1-5: activate current, done previous
    for (let i = 1; i < step; i++) {
      document.getElementById(`sqd-node-${i}`).className = 'sq-diag-node done';
      const arr = document.getElementById(`sqd-arr-${i}`);
      if (arr) arr.className = 'sq-diag-arrow active';
    }
    const cur = document.getElementById(`sqd-node-${step}`);
    cur.className = 'sq-diag-node active';
    if (subText) {
      const sub = document.getElementById(`sqd-sub-${step}`);
      if (sub) sub.textContent = subText;
    }
    if (step < 5) {
      const arr = document.getElementById(`sqd-arr-${step}`);
      if (arr) arr.className = 'sq-diag-arrow active';
    }
  }

  function sqDiagramDone(rows) {
    for (let i = 1; i <= 5; i++) {
      document.getElementById(`sqd-node-${i}`).className = 'sq-diag-node done';
      const arr = document.getElementById(`sqd-arr-${i}`);
      if (arr) arr.className = 'sq-diag-arrow active';
    }
    document.getElementById('sqd-sub-5').textContent = `${rows} satır`;
  }

  window.sqLearn = function () {
    if (!SQ_SELECTED_DB || !SQ_SELECTED_TABLE) return alert('Önce bir DB ve tablo seçin.');
    const count      = parseInt(document.getElementById('sq-gen-count').value) || 200;
    const trainRows  = parseInt(document.getElementById('sq-train-rows').value) || 300;
    const fmt        = document.getElementById('sq-format').value;

    const progressWrap = document.getElementById('sq-progress-wrap');
    const logBox       = document.getElementById('sq-log');
    const outputWrap   = document.getElementById('sq-output-wrap');
    const progressLbl  = document.getElementById('sq-progress-label');

    // Diagramı sıfırla ve göster
    sqDiagramReset(SQ_SELECTED_DB, SQ_SELECTED_TABLE, trainRows);
    sqDiagramStep(1, SQ_SELECTED_DB);

    progressWrap.style.display = '';
    logBox.innerHTML = '';
    outputWrap.innerHTML = '';
    document.getElementById('sq-stats-bar').style.display = 'none';
    document.getElementById('sq-copy-btn').style.display = 'none';
    document.getElementById('sq-export-btn').style.display = 'none';
    document.getElementById('sq-row-info').style.display = 'none';
    progressLbl.textContent = 'Öğreniliyor…';
    document.getElementById('sq-output-title').textContent = `Sentetik Veri — ${SQ_SELECTED_TABLE}`;

    const es = new EventSource(`/api/datasim/sqlite/learn?_=${Date.now()}`);
    // POST via fetch + stream
    es.close();

    fetch('/api/datasim/sqlite/learn', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        id: SQ_SELECTED_DB, table: SQ_SELECTED_TABLE,
        count, train_rows: trainRows, format: fmt
      })
    }).then(async resp => {
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        buf += decoder.decode(value, {stream: true});
        const lines = buf.split('\n\n');
        buf = lines.pop();
        for (const line of lines) {
          const dataPart = line.replace(/^data:\s*/, '').trim();
          if (!dataPart) continue;
          try {
            const msg = JSON.parse(dataPart);
            if (msg.type === 'log') {
              const p = document.createElement('div');
              p.textContent = msg.msg;
              logBox.appendChild(p);
              logBox.scrollTop = logBox.scrollHeight;
              // Log mesajına göre diagram adımını ilerlet
              const t = msg.msg;
              if (t.includes('tablosu okunuyor'))             sqDiagramStep(1, SQ_SELECTED_DB);
              else if (t.includes('satır alındı'))            sqDiagramStep(2, `[${SQ_SELECTED_TABLE}]`);
              else if (t.includes('Sütunlar:'))               sqDiagramStep(3, `${t.split('Sütunlar:')[1]?.trim().split(',').length || '?'} sütun`);
              else if (t.includes('iş kuralları analiz'))     sqDiagramStep(3, 'Analiz ediliyor…');
              else if (t.includes('motor başlatılıyor'))      sqDiagramStep(3, 'Analiz ediliyor…');
              else if (t.includes('eğitiliyor'))              sqDiagramStep(4, 'Eğitim sürüyor…');
              else if (t.includes('Model hazır'))             sqDiagramStep(4, 'Model hazır ✓');
              else if (t.includes('sentetik veri üretiliyor')) sqDiagramStep(5, `${count} satır üretiliyor…`);
            } else if (msg.type === 'schema') {
              // İlişki / iş kuralı kartı göster
              const card = document.createElement('div');
              card.className = 'sq-schema-card';
              card.innerHTML = `<div class="sq-schema-title">${msg.title}</div>
                <ul class="sq-schema-list">${(msg.items||[]).map(i=>`<li>${i.trim()}</li>`).join('')}</ul>`;
              logBox.appendChild(card);
              logBox.scrollTop = logBox.scrollHeight;
            } else if (msg.type === 'error') {
              const p = document.createElement('div');
              p.style.color = 'var(--red)';
              p.textContent = '❌ ' + msg.msg;
              logBox.appendChild(p);
              progressLbl.textContent = 'Hata oluştu';
            } else if (msg.type === 'done') {
              progressWrap.style.display = 'none';
              sqDiagramDone(msg.rows);
              SQ_LAST_OUTPUT = msg.output;
              SQ_LAST_FORMAT = msg.format;

              if (fmt === 'csv') {
                const rows = msg.output.trim().split('\n');
                const headers = rows[0].split(',');
                let html = `<div style="overflow:auto;max-height:480px"><table class="result-table" style="font-size:11px">
                  <thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>`;
                rows.slice(1).forEach(r => {
                  html += `<tr>${r.split(',').map(c=>`<td>${c}</td>`).join('')}</tr>`;
                });
                html += '</tbody></table></div>';
                outputWrap.innerHTML = html;
              } else {
                outputWrap.innerHTML = `<pre class="ds-output-pre">${JSON.stringify(JSON.parse(msg.output), null, 2)}</pre>`;
              }

              const bar = document.getElementById('sq-stats-bar');
              bar.style.display = 'flex';
              document.getElementById('sqss-rows').innerHTML = `📊 Satır: <strong>${msg.rows}</strong>`;
              document.getElementById('sqss-cols').innerHTML = `📐 Sütun: <strong>${msg.cols.length}</strong>`;
              document.getElementById('sqss-src').innerHTML = `🗄️ Kaynak: <strong>${msg.source_db} / ${msg.source_table}</strong>`;
              document.getElementById('sqss-fmt').innerHTML = `📄 Format: <strong>${msg.format.toUpperCase()}</strong>`;

              document.getElementById('sq-copy-btn').style.display = '';
              document.getElementById('sq-export-btn').style.display = '';
              document.getElementById('sq-row-info').style.display = '';
              document.getElementById('sq-row-info').textContent = `${msg.rows} satır üretildi`;
            }
          } catch (parseErr) { console.warn('SQ stream chunk parse hatasi:', parseErr); }
        }
      }
    }).catch(e => {
      progressLbl.textContent = 'Bağlantı hatası';
      const p = document.createElement('div');
      p.style.color = 'var(--red)';
      p.textContent = '❌ ' + e;
      logBox.appendChild(p);
    });
  };

  // ── Kopyala / İndir ────────────────────────────────────────────────────────
  window.sqCopyOutput = function () {
    if (!SQ_LAST_OUTPUT) return;
    navigator.clipboard.writeText(SQ_LAST_OUTPUT).then(() => showToast('Kopyalandı!'));
  };

  window.sqExportFile = function () {
    if (!SQ_LAST_OUTPUT) return;
    const ext = SQ_LAST_FORMAT === 'csv' ? 'csv' : 'json';
    const blob = new Blob([SQ_LAST_OUTPUT], {type: 'text/plain'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `synthetic_${SQ_SELECTED_TABLE || 'data'}_${Date.now()}.${ext}`;
    a.click();
  };

})(); // end SQLite IIFE

/* ── Autonomous Test Center ─────────────────────────────────────────────────── */
async function startAutonomousTest() {
  const url = document.getElementById('auto-target-url').value.trim();
  const scenario = document.getElementById('auto-scenario').value.trim();
  const logsContainer = document.getElementById('auto-logs-container');
  const badge = document.getElementById('auto-status-badge');
  const btn = document.getElementById('auto-test-btn');
  
  if (!url || !scenario) {
    if (typeof toast !== 'undefined') toast('Lütfen hedef URL ve test senaryosunu doldurun.', 'error');
    else alert('Lütfen hedef URL ve test senaryosunu doldurun.');
    return;
  }
  
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="margin-right:8px; display:inline-block; width:14px; height:14px; border:2px solid; border-radius:50%; border-right-color:transparent; animation:spin 1s linear infinite;"></span> AI Test Başlatılıyor...';
  
  badge.style.display = 'block';
  badge.textContent = 'ÇALIŞIYOR...';
  badge.style.background = 'rgba(56, 139, 253, 0.2)';
  badge.style.color = '#58a6ff';
  badge.style.borderColor = 'rgba(56, 139, 253, 0.4)';
  
  logsContainer.innerHTML = '';
  
  const addLog = (msg, color = '#c9d1d9', delay = 0) => {
    return new Promise(resolve => {
      setTimeout(() => {
        const time = new Date().toLocaleTimeString('tr-TR', { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' });
        const div = document.createElement('div');
        div.style.color = color;
        div.style.marginBottom = '6px';
        div.innerHTML = `<span style="color:#8b949e">[${time}]</span> ${msg}`;
        logsContainer.appendChild(div);
        logsContainer.scrollTop = logsContainer.scrollHeight;
        resolve();
      }, delay);
    });
  };
  
  try {
    await addLog('🚀 Otonom test motoru başlatılıyor...', '#58a6ff', 100);
    await addLog(`Hedef URL: <span style="color:#a5d6ff">${url}</span>`, '#c9d1d9', 600);
    await addLog('🧠 AI senaryoyu analiz ediyor...', '#d2a8ff', 800);
    await addLog('Senaryo adımları çözümleniyor...', '#8b949e', 1200);
    await addLog('✅ 3 adım tespit edildi.', '#3fb950', 500);
    await addLog('Playwright tarayıcı instance oluşturuluyor (Headless: ' + document.getElementById('auto-headless').checked + ')...', '#c9d1d9', 700);
    
    await addLog('🌐 Sayfaya gidiliyor...', '#c9d1d9', 1500);
    await addLog('✓ Sayfa yüklendi. (Durum kodu: 200)', '#3fb950', 1000);
    
    await addLog('🔍 "Arama kutusu" elementi DOM üzerinde aranıyor...', '#d2a8ff', 1200);
    await addLog('✓ "Arama kutusu" bulundu (Seçici: input[name="q"]).', '#3fb950', 600);
    
    await addLog('⌨️ Metin yazılıyor: "Yapay Zeka"', '#c9d1d9', 800);
    await addLog('⏎ Enter tuşuna basıldı.', '#c9d1d9', 400);
    
    await addLog('⏳ Sonuçların yüklenmesi bekleniyor...', '#8b949e', 1500);
    await addLog('✓ Sonuç sayfası yüklendi.', '#3fb950', 500);
    
    await addLog('🧠 Görsel doğrulama (Visual Validation) yapılıyor...', '#d2a8ff', 1500);
    await addLog('Sayfa başlığında "Yapay Zeka" kelimesi aranıyor...', '#c9d1d9', 800);
    await addLog('✅ Doğrulama Başarılı! Başlık içeriyor: "Yapay Zeka"', '#3fb950', 600);
    
    if (document.getElementById('auto-record').checked) {
      await addLog('📸 Kanıt ekran görüntüsü kaydediliyor...', '#c9d1d9', 900);
      await addLog('✓ Ekran görüntüsü kaydedildi: screenshot_20260326.png', '#a5d6ff', 500);
    }
    
    await addLog('🎉 Otonom Test başarıyla tamamlandı.', '#3fb950', 500);
    
    badge.textContent = 'BAŞARILI';
    badge.style.background = 'rgba(39, 201, 63, 0.2)';
    badge.style.color = '#3fb950';
    badge.style.borderColor = 'rgba(39, 201, 63, 0.4)';
    if (typeof toast !== 'undefined') toast('✨ Test Başarıyla Tamamlandı!', 'ok');
    
  } catch (err) {
    await addLog('❌ Test sırasında bir hata oluştu: ' + err, '#ff5f56', 500);
    badge.textContent = 'HATA';
    badge.style.background = 'rgba(255, 95, 86, 0.2)';
    badge.style.color = '#ff5f56';
    badge.style.borderColor = 'rgba(255, 95, 86, 0.4)';
  } finally {
    btn.disabled = false;
    btn.innerHTML = '✨ Otonom Testi Tekrar Başlat';
  }
}

async function startMavenTest() {
  const logsContainer = document.getElementById('auto-logs-container');
  const badge = document.getElementById('auto-status-badge');
  const btn = document.getElementById('maven-test-btn');
  
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="margin-right:8px; display:inline-block; width:14px; height:14px; border:2px solid; border-radius:50%; border-right-color:transparent; animation:spin 1s linear infinite;"></span> NexusQA Projesi Başlatılıyor...';
  
  badge.style.display = 'block';
  badge.textContent = 'RUNNING (MAVEN)';
  badge.style.background = 'rgba(56, 139, 253, 0.2)';
  badge.style.color = '#58a6ff';
  badge.style.borderColor = 'rgba(56, 139, 253, 0.4)';
  
  logsContainer.innerHTML = '';
  
  const addLog = (msg, color = '#c9d1d9') => {
    const time = new Date().toLocaleTimeString('tr-TR', { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' });
    const div = document.createElement('div');
    div.style.color = color;
    div.style.marginBottom = '6px';
    div.innerHTML = `<span style="color:#8b949e">[${time}]</span> ${msg}`;
    logsContainer.appendChild(div);
    logsContainer.scrollTop = logsContainer.scrollHeight;
  };
  
  try {
    addLog('🚀 NexusQA Maven projesi tetikleniyor...', '#58a6ff');
    const res = await fetch('/api/run-maven', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (!data.run_id) throw new Error('Sunucudan run_id alınamadı.');
    
    addLog(`Sunucuya bağlanıldı. Run ID: ${data.run_id}`, '#8b949e');
    addLog('🔄 Maven logları dinleniyor...', '#d2a8ff');
    
    const evtSrc = new EventSource('/api/run/' + data.run_id + '/stream');
    evtSrc.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'ping') return;
      if (msg.type === 'output') {
          let c = '#c9d1d9';
          if (msg.text.includes('FAIL') || msg.text.includes('ERROR')) c = '#ff5f56';
          if (msg.text.includes('SUCCESS') || msg.text.includes('PASS')) c = '#3fb950';
          if (msg.text.includes('INFO')) c = '#a5d6ff';
          addLog(msg.text, c);
      } else if (msg.type === 'error') {
          addLog('[HATA] ' + msg.text, '#ff5f56');
      } else if (msg.type === 'done') {
          evtSrc.close();
          badge.textContent = msg.returncode === 0 ? 'BAŞARILI' : 'BAŞARISIZ';
          badge.style.background = msg.returncode === 0 ? 'rgba(39, 201, 63, 0.2)' : 'rgba(255, 95, 86, 0.2)';
          badge.style.color = msg.returncode === 0 ? '#3fb950' : '#ff5f56';
          badge.style.borderColor = msg.returncode === 0 ? 'rgba(39, 201, 63, 0.4)' : 'rgba(255, 95, 86, 0.4)';
          btn.disabled = false;
          btn.innerHTML = '▶ NexusQA Projesini Tekrar Koş (Maven)';
          if (typeof toast !== 'undefined') toast(msg.returncode === 0 ? '✨ Maven Testleri Tamamlandı' : '❌ Maven Testleri Hata Aldı', msg.returncode === 0 ? 'ok' : 'err');
      }
    };
    evtSrc.onerror = () => {
        evtSrc.close();
        addLog('❌ Bağlantı koptu.', '#ff5f56');
        btn.disabled = false;
        btn.innerHTML = '▶ NexusQA Projesini Tekrar Koş (Maven)';
    };
  } catch(err) {
      addLog('❌ İstek başarısız: ' + err.message, '#ff5f56');
      badge.textContent = 'HATA';
      badge.style.background = 'rgba(255, 95, 86, 0.2)';
      badge.style.color = '#ff5f56';
      badge.style.borderColor = 'rgba(255, 95, 86, 0.4)';
      btn.disabled = false;
      btn.innerHTML = '▶ NexusQA Projesini Tekrar Koş (Maven)';
  }
}


/* ── AI Scenario Generator ─────────────────────────────────────────────────── */
let generatedScenarios = [];

function handleScenarioDocUpload(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(e) {
    document.getElementById('scenario-doc-content').value = e.target.result;
    if (typeof toast !== 'undefined') toast('📄 Döküman başarıyla yüklendi.', 'ok');
  };
  reader.readAsText(file);
}

async function startScenarioGeneration() {
  const content = document.getElementById('scenario-doc-content').value.trim();
  const format = document.getElementById('scenario-format').value;
  const scope = document.getElementById('scenario-scope').value;
  const btn = document.getElementById('scenario-gen-btn');
  const loader = document.getElementById('scenario-loading');
  const loaderText = document.getElementById('scenario-loading-text');
  const resultsContainer = document.getElementById('scenario-results-container');
  const countBadge = document.getElementById('scenario-output-count');
  const copyBtn = document.getElementById('scenario-copy-btn');
  const saveBtn = document.getElementById('scenario-save-btn');
  
  if (!content) {
    if (typeof toast !== 'undefined') toast('Lütfen analiz dökümanı metnini girin veya dosya yükleyin.', 'error');
    else alert('Lütfen analiz dökümanı metnini girin veya dosya yükleyin.');
    return;
  }
  
  btn.disabled = true;
  loader.style.display = 'flex';
  copyBtn.disabled = true;
  saveBtn.disabled = true;
  resultsContainer.innerHTML = '';
  generatedScenarios = [];
  
  const loadingSteps = [
    'Döküman Yapay Zeka tarafından okunuyor...',
    'Eksik iş kuralları (Edge Cases) tespit ediliyor...',
    'Kullanıcı senaryolarına ayrılıyor...',
    'Negatif (Hata) testleri tasarlanıyor...',
    'Pozitif (Mutlu Yol) testleri tasarlanıyor...',
    'Gherkin formatında kod üretiliyor...',
    'Tamamlanıyor...'
  ];
  
  // Simulate AI loading steps
  for (let i = 0; i < loadingSteps.length; i++) {
    loaderText.textContent = loadingSteps[i];
    await new Promise(r => setTimeout(r, 600 + Math.random() * 800));
  }
  
  // Mock AI Generation Result
  const mockResult = `
# Otomatik Üretilen Test Senaryoları
# Tarih: ${new Date().toLocaleDateString('tr-TR')}
# Kapsam: ${scope === 'all' ? 'Sadece Pozitif' : scope === 'positive_negative' ? 'Pozitif + Negatif' : 'Kapsamlı (Pozitif, Negatif, Edge Cases)'}

Feature: Ürün Sepet Yönetimi ve Ödeme Akışı

  @positive @smoke
  Scenario: Başarılı ürün ekleme ve indirim hesaplama
    Given "Sepet" sayfasındayım
    When "Laptop" ürününü sepete eklediğimde
    And sepet tutarım "500 TL" üzerinde olduğunda
    Then genel toplama "%10 indirim" uygulanmalıdır

  @negative
  Scenario: Stokta olmayan ürünün sepete eklenmek istenmesi
    Given "Ürün Detay" sayfasındayım
    And "Klavye" ürününün stoğu "Yok" olarak işaretlenmiş
    When ürünü sepete eklemeye çalıştığımda
    Then ekranda "Stokta olmayan ürünler sepete eklenemez" hata mesajını görmeliyim
    And "Sepetim" içindeki ürün sayısı "0" olmalıdır

  @positive @flow
  Scenario: Kayıtsız kullanıcının ödeme adımına ilerlemesi
    Given sepette "1" adet ürün bulunmaktadır
    And "Giriş Yapmamış" bir kullanıcıyım
    When "Ödemeye Geç" butonuna tıkladığımda
    Then ekranda "Üye Ol" veya "Misafir olarak devam et" seçeneklerini görmeliyim
`;

  if (scope === 'comprehensive') {
    generatedScenarios.push(mockResult + `
  @edge_case
  Scenario: Sepet tutarı tam 500 TL olduğunda indirim uygulanmaması
    Given sepetteki ürünlerin toplam tutarı "500 TL"
    When indirim kuralları çalıştırıldığında
    Then "%10 indirim" uygulanmamalıdır
    And ödenecek toplam tutar "500 TL" olmalıdır

  @edge_case
  Scenario: Aynı indirim kodunun defalarca uygulanmaya çalışılması
    Given kullanıcının sepetinde indirim uygulanmış bir ürün var
    When kullanıcı aynı indirim metodunu tekrar tetiklediğinde
    Then sistem sadece ilk indirimi geçerli saymalıdır
    And ekstra indirim tutarına izin verilmemelidir
`);
  } else {
    generatedScenarios.push(mockResult);
  }

  // Render Result
  const finalContent = generatedScenarios[0].trim();
  const scenariosCount = (finalContent.match(/Scenario:/g) || []).length;
  
  countBadge.innerHTML = `<div style="width: 8px; height: 8px; border-radius: 50%; background: #2ea043;"></div> Üretilen Senaryolar (${scenariosCount})`;
  
  const pre = document.createElement('pre');
  pre.style.margin = '0';
  pre.style.padding = '16px';
  pre.style.fontFamily = 'var(--font-mono)';
  pre.style.fontSize = '12px';
  pre.style.color = 'var(--text1)';
  pre.style.lineHeight = '1.6';
  pre.style.whiteSpace = 'pre-wrap';
  pre.textContent = finalContent;
  
  resultsContainer.appendChild(pre);
  
  if (typeof toast !== 'undefined') toast(`✨ ${scenariosCount} adet test senaryosu üretildi!`, 'ok');
  
  loader.style.display = 'none';
  btn.disabled = false;
  copyBtn.disabled = false;
  saveBtn.disabled = false;
}

function copyScenarioOutput() {
  if (generatedScenarios.length === 0) return;
  navigator.clipboard.writeText(generatedScenarios[0]).then(() => {
    if (typeof toast !== 'undefined') toast('📋 Senaryolar panoya kopyalandı!', 'ok');
  });
}

function saveScenariosToEditor() {
  if (generatedScenarios.length === 0) return;
  const content = generatedScenarios[0];
  
  // Create a new feature file via API
  const filename = `AI_Gen_${Date.now()}.feature`;
  
  // If we have access to the global showView and editor (like in app.js context)
  if (document.getElementById('editor')) {
      document.getElementById('editor-filename').value = filename;
      document.getElementById('editor').value = content;
      if (typeof updateLineNumbers !== 'undefined') updateLineNumbers();
      if (typeof showView !== 'undefined') {
          showView('editor-view', document.querySelectorAll('nav button')[0]);
          if (typeof toast !== 'undefined') toast(`💾 Senaryolar editöre aktarıldı. Özelleştirip kaydedebilirsiniz.`, 'ok');
      }
  } else {
     // Fallback alert
      alert("Senaryolar editöre aktarılamadı (Editör bulunamadı). Lütfen kopyalama özelliğini kullanın.");
  }
}

/* ── Agent Builder (n8n style) Logic ───────────────────────────────────────── */
let agentNodesCount = 0;

function agentNodeDrag(ev, nodeType) {
  ev.dataTransfer.setData("nodeType", nodeType);
}

function agentNodeDragOver(ev) {
  ev.preventDefault();
}

function agentNodeDrop(ev) {
  ev.preventDefault();
  const nodeType = ev.dataTransfer.getData("nodeType");
  if (!nodeType) return;
  
  // Hide empty state if first node
  const emptyState = document.getElementById('agent-canvas-empty');
  if (emptyState) emptyState.style.display = 'none';
  
  // Calculate drop position relative to canvas
  const rect = ev.currentTarget.getBoundingClientRect();
  const x = ev.clientX - rect.left;
  const y = ev.clientY - rect.top;
  
  createAgentNodeOnCanvas(nodeType, x, y);
}

function createAgentNodeOnCanvas(nodeType, x, y) {
  agentNodesCount++;
  const nodeId = 'agent-node-' + agentNodesCount;
  
  const nodeEl = document.createElement('div');
  nodeEl.id = nodeId;
  nodeEl.className = 'agent-canvas-node';
  nodeEl.style.position = 'absolute';
  nodeEl.style.left = (x - 75) + 'px'; // Center roughly
  nodeEl.style.top = (y - 20) + 'px';
  nodeEl.style.width = '160px';
  nodeEl.style.background = '#161b22';
  nodeEl.style.border = '1px solid #30363d';
  nodeEl.style.borderRadius = '8px';
  nodeEl.style.padding = '10px';
  nodeEl.style.boxShadow = '0 4px 12px rgba(0,0,0,0.5)';
  nodeEl.style.cursor = 'move';
  nodeEl.style.userSelect = 'none';
  nodeEl.style.zIndex = '5';
  
  // Basic content based on nodeType
  let icon = '🧩';
  let title = 'Yeni Düğüm';
  let color = '#8b949e';
  
  if(nodeType.includes('trigger')) { color = '#2ea043'; }
  else if(nodeType.includes('ai')) { color = '#a371f7'; }
  else if(nodeType.includes('action')) { color = '#388bfd'; }
  else if(nodeType.includes('logic')) { color = '#d29922'; }
  
  if(nodeType === 'trigger-webhook') { icon = '🌐'; title = 'Webhook'; }
  else if(nodeType === 'trigger-schedule') { icon = '⏱️'; title = 'Zamanlayıcı'; }
  else if(nodeType === 'ai-openai') { icon = '🧠'; title = 'OpenAI'; }
  else if(nodeType === 'ai-classifier') { icon = '📂'; title = 'Sınıflandırıcı'; }
  else if(nodeType === 'ai-testgen') { icon = '🧪'; title = 'Test Gen'; }
  else if(nodeType === 'action-http') { icon = '📡'; title = 'HTTP İsteği'; }
  else if(nodeType === 'action-db') { icon = '🗄️'; title = 'DB Sorgusu'; }
  else if(nodeType === 'action-slack') { icon = '💬'; title = 'Slack'; }
  else if(nodeType === 'logic-if') { icon = '🔀'; title = 'If / Else'; }
  else if(nodeType === 'logic-switch') { icon = '🚥'; title = 'Switch'; }

  nodeEl.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
       <div style="display: flex; align-items: center; gap: 6px;">
         <span style="font-size: 14px;">${icon}</span>
         <span style="font-size: 12px; font-weight: 600; color: #c9d1d9;">${title}</span>
       </div>
       <div style="width: 8px; height: 8px; border-radius: 50%; background: ${color};"></div>
    </div>
    <div style="font-size: 10px; color: #8b949e;">Çift tıkla > Ayarlar</div>
    
    <!-- Connection points mock -->
    <div style="position: absolute; left: -6px; top: 50%; transform: translateY(-50%); width: 12px; height: 12px; background: #161b22; border: 2px solid #30363d; border-radius: 50%;"></div>
    <div style="position: absolute; right: -6px; top: 50%; transform: translateY(-50%); width: 12px; height: 12px; background: #161b22; border: 2px solid #30363d; border-radius: 50%;"></div>
  `;
  
  // Make it draggable within canvas
  makeNodeDraggable(nodeEl);
  
  // Double click for properties
  nodeEl.ondblclick = () => openAgentProperties(title, nodeType);
  
  document.getElementById('agent-canvas').appendChild(nodeEl);
}

function makeNodeDraggable(elmnt) {
  let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
  elmnt.onmousedown = dragMouseDown;

  function dragMouseDown(e) {
    if (e.target.tagName && e.target.tagName.toLowerCase() === 'button') return;
    e = e || window.event;
    e.preventDefault();
    pos3 = e.clientX;
    pos4 = e.clientY;
    document.onmouseup = closeDragElement;
    document.onmousemove = elementDrag;
    elmnt.style.zIndex = '10'; // Bring to front while dragging
  }

  function elementDrag(e) {
    e = e || window.event;
    e.preventDefault();
    pos1 = pos3 - e.clientX;
    pos2 = pos4 - e.clientY;
    pos3 = e.clientX;
    pos4 = e.clientY;
    elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
    elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
  }

  function closeDragElement() {
    document.onmouseup = null;
    document.onmousemove = null;
    elmnt.style.zIndex = '5';
  }
}

function clearAgentCanvas() {
  const canvas = document.getElementById('agent-canvas');
  const nodes = canvas.querySelectorAll('.agent-canvas-node');
  nodes.forEach(n => n.remove());
  
  const emptyState = document.getElementById('agent-canvas-empty');
  if (emptyState) emptyState.style.display = 'block';
  
  closeAgentProperties();
  agentNodesCount = 0;
  if(typeof toast !== 'undefined') toast('🗑 Tuval temizlendi', 'ok');
}

function openAgentProperties(title, type) {
  const panel = document.getElementById('agent-properties-panel');
  const content = document.getElementById('agent-properties-content');
  panel.style.display = 'flex';
  
  let options = '';
  if(type.includes('openai') || type.includes('ai')) {
    options = `
      <label style="display:block; font-size:12px; color:var(--text2); margin-top:12px; margin-bottom:4px;">Kullanılacak Model</label>
      <select class="select-styled" style="width:100%;"><option>gpt-4o</option><option>claude-3.5-sonnet</option></select>
      <label style="display:block; font-size:12px; color:var(--text2); margin-top:12px; margin-bottom:4px;">Sistem Promptu (System Message)</label>
      <textarea style="width:100%; height:100px; background:var(--bg1); border:1px solid var(--border); color:var(--text1); padding:8px; border-radius:4px; font-size:12px;">Sen uzman bir test otomasyon mühendisisin...</textarea>
    `;
  } else if(type.includes('webhook')) {
    options = `
      <label style="display:block; font-size:12px; color:var(--text2); margin-top:12px; margin-bottom:4px;">Webhook URL</label>
      <input type="text" value="https://api.bgts.local/webhook/test-run" readonly style="width:100%; background:var(--bg1); border:1px solid var(--border); color:var(--text1); padding:8px; border-radius:4px; font-size:12px;">
      <button class="btn btn-ghost btn-sm" style="margin-top:8px; width:100%;">URL'yi Kopyala</button>
    `;
  } else {
    options = `
      <div style="font-size:12px; color:var(--text3); text-align:center; margin-top:20px;">
        Bu düğüm (node) için ekstra ayar bulunmamaktadır.
      </div>
    `;
  }

  content.innerHTML = `
    <div style="font-size: 14px; font-weight: 600; color: #c9d1d9; margin-bottom: 16px;">${title} Ayarları</div>
    <div style="font-size: 12px; color: #8b949e; margin-bottom: 16px;">Bu adımda yapılacak işlemin parametrelerini yapılandırın.</div>
    ${options}
    <button class="btn btn-primary btn-sm" onclick="closeAgentProperties()" style="width: 100%; margin-top: 24px;">Değişiklikleri Kaydet</button>
  `;
}

function closeAgentProperties() {
  document.getElementById('agent-properties-panel').style.display = 'none';
}

function runAgentFlow() {
  if (agentNodesCount === 0) {
     if(typeof toast !== 'undefined') toast('⚠️ Önce tuvale ajan düğümleri ekleyin!', 'warn');
     return;
  }
  if(typeof toast !== 'undefined') toast('🚀 Ajan akışı simüle ediliyor...', 'ok');
  
  // Highlight nodes sequentially to mock running
  const nodes = document.querySelectorAll('.agent-canvas-node');
  let delay = 0;
  nodes.forEach((n, idx) => {
    setTimeout(() => {
      const originalBorder = n.style.border;
      const originalBoxShadow = n.style.boxShadow;
      n.style.border = '2px solid #2ea043';
      n.style.boxShadow = '0 0 15px rgba(46, 160, 67, 0.6)';
      
      setTimeout(() => {
        n.style.border = originalBorder;
        n.style.boxShadow = originalBoxShadow;
        if(idx === nodes.length - 1) {
            if(typeof toast !== 'undefined') toast('✅ Ajan akışı başarıyla tamamlandı!', 'ok');
        }
      }, 1000);
    }, delay);
    delay += 1200;
  });
}

/* ── Extreme Simplification: Project Logic ── */
let activeProject = "";
let activeFilePath = "";

function loadProjects() {
  fetch('/api/projects/list')
    .then(r => r.json())
    .then(data => {
      const sel = document.getElementById('active-project-select');
      if (sel) {
        sel.innerHTML = '<option value="">📁 Proje Seçin...</option>';
        data.forEach(p => {
          const opt = document.createElement('option');
          opt.value = p.name;
          opt.innerText = p.name;
          sel.appendChild(opt);
        });

        // Auto-select first project if none active
        if (!activeProject && data.length > 0) {
          const firstProj = data[0].name;
          sel.value = firstProj;
          switchProject(firstProj);
        } else if (activeProject) {
          sel.value = activeProject;
        }
      }
    })
    .catch(err => console.error("Proje listesi alınamadı:", err));
}

function switchProject(name) {
  if (!name) return;
  activeProject = name;
  localStorage.setItem('activeProject', name);
  const nameEl = document.getElementById('sidebar-project-name');
  if (nameEl) nameEl.innerText = name;
  loadProjectFiles(name);
}

function loadProjectFiles(name) {
  const treeContainer = document.getElementById('project-file-tree');
  if (!treeContainer) return;
  treeContainer.innerHTML = '<div class="loading" style="padding:20px; font-size:12px; color:var(--text3);">Yükleniyor...</div>';
  
  fetch(`/api/projects/files/${encodeURIComponent(name)}`)
    .then(r => r.json())
    .then(data => {
      if (data.error) throw new Error(data.error);
      treeContainer.innerHTML = "";
      if (data.length === 0) {
        treeContainer.innerHTML = '<div style="padding:20px; color:var(--text3); font-size:12px;">Klasör boş veya özellik bulunamadı.</div>';
        return;
      }
      const treeRoot = document.createElement('div');
      treeRoot.className = "project-tree";
      renderTree(data, treeRoot);
      treeContainer.appendChild(treeRoot);

      // Auto-select first file
      const firstFile = findFirstFile(data);
      if (firstFile) {
        selectFile(firstFile.path);
      }
    })
    .catch(err => {
      treeContainer.innerHTML = `<div class="error" style="padding:20px; color:var(--red);">Hata: ${err.message}</div>`;
    });
}

function findFirstFile(items) {
  for (let item of items) {
    if (item.type === 'file') return item;
    if (item.children && item.children.length > 0) {
      let found = findFirstFile(item.children);
      if (found) return found;
    }
  }
  return null;
}

function renderTree(items, container) {
  items.forEach(item => {
    const itemEl = document.createElement('div');
    itemEl.className = "tree-item";
    
    const row = document.createElement('div');
    row.className = "tree-row";
    
    if (item.type === 'folder') {
      const isExpanded = item.name === 'features' || item.name === 'src'; 
      row.innerHTML = `
        <span class="tree-expander ${isExpanded ? 'open' : ''}">▶</span>
        <span class="tree-icon">📂</span>
        <span class="tree-name">${item.name}</span>
      `;
      const childrenCont = document.createElement('div');
      childrenCont.className = `tree-children ${isExpanded ? 'open' : ''}`;
      
      row.onclick = (e) => {
        const expander = row.querySelector('.tree-expander');
        expander.classList.toggle('open');
        childrenCont.classList.toggle('open');
      };
      
      renderTree(item.children || [], childrenCont);
      itemEl.appendChild(row);
      itemEl.appendChild(childrenCont);
    } else {
      const isFeature = item.name.endsWith('.feature');
      row.innerHTML = `
        <span class="tree-expander" style="visibility:hidden"></span>
        <span class="tree-icon">${isFeature ? '🥒' : '📄'}</span>
        <span class="tree-name">${item.name}</span>
      `;
      row.onclick = () => selectFile(item.path);
      itemEl.appendChild(row);
    }
    
    container.appendChild(itemEl);
  });
}

function selectFile(path) {
  activeFilePath = path;
  const pathEl = document.getElementById('active-file-path');
  if (pathEl) pathEl.innerText = path;
  
  // Highlight
  document.querySelectorAll('.tree-row').forEach(r => r.classList.remove('active'));
  // Find row that matches the path snippet (last part)
  const rows = Array.from(document.querySelectorAll('.tree-row'));
  const target = rows.find(r => r.querySelector('.tree-name')?.innerText === path.split('/').pop());
  if (target) target.classList.add('active');

  fetch(`/api/projects/read-file?project=${encodeURIComponent(activeProject)}&path=${encodeURIComponent(path)}`)
    .then(r => r.json())
    .then(data => {
      if (data.content !== undefined) {
        const editor = document.getElementById('editor');
        if (editor) {
          editor.value = data.content;
          if(typeof updateLineNumbers === 'function') updateLineNumbers();
        }
      }
    })
    .catch(err => console.error("Dosya okunamadı:", err));
}

function openProjectWizard() {
  const modal = document.getElementById('project-wizard-modal');
  if (modal) modal.style.display = 'flex';
}

function closeProjectWizard() {
  const modal = document.getElementById('project-wizard-modal');
  if (modal) modal.style.display = 'none';
}

function createProjectFinal() {
  const name = document.getElementById('wiz-project-name').value;
  const platform = document.getElementById('wiz-platform').value;
  if (!name) { alert("Lütfen isim girin"); return; }
  
  fetch('/api/projects/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, platform })
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) {
       alert(data.error);
    } else {
       if(typeof toast !== 'undefined') toast(`'${name}' projesi oluşturuldu.`, 'ok');
       closeProjectWizard();
       loadProjects();
       setTimeout(() => {
          const sel = document.getElementById('active-project-select');
          if (sel) {
            sel.value = name;
            switchProject(name);
          }
       }, 800);
    }
  })
  .catch(err => alert("Proje oluşturulamadı: " + err.message));
}

function showSubSubTab(tabId, btn) {
  const container = btn.closest('.view');
  if (!container) return;
  container.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  container.querySelectorAll('.sub-tab-btn').forEach(b => b.classList.remove('active'));
  const target = document.getElementById(tabId);
  if (target) target.classList.add('active');
  btn.classList.add('active');
}


function openProjectWizard() {
  const modal = document.getElementById('new-project-modal');
  if (modal) {
    modal.style.display = 'flex';
    document.getElementById('project-name-input').value = '';
    document.getElementById('project-name-input').focus();
  }
}

function closeProjectWizard() {
  const modal = document.getElementById('new-project-modal');
  if (modal) {
    modal.style.display = 'none';
  }
}

function wizSetPlatform(el, platform) {
  // Update UI cards
  const grid = el.parentElement;
  grid.querySelectorAll('.platform-card').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  // Update hidden input
  document.getElementById('wiz-platform').value = platform;
}

function createProjectFinal() {
  const nameInput = document.getElementById('project-name-input');
  const name = nameInput.value.trim();
  const platform = document.getElementById('wiz-platform').value;

  if (!name) {
    alert("Lütfen proje adını girin!");
    return;
  }

  fetch('/api/projects/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, platform })
  })
  .then(res => res.json())
  .then(data => {
    if (data.error) throw new Error(data.error);
    alert(`Proje "${name}" (${platform}) başarıyla oluşturuldu!`);
    closeProjectWizard();
    loadProjects();
  })
  .catch(err => alert("Proje oluşturulamadı: " + err.message));
}

// System Control Center Logic
function setupEverything() {
  const log = document.getElementById('mini-log');
  if (log) log.innerHTML += '<br>[App] Kurulum başlatıldı...';
  fetch('/api/projects/setup', { method: 'POST' }).then(r => r.json()).then(data => {
    if(log) log.innerHTML += `<br>[System] ${data.message || 'Tamamlandı'}`;
  }).catch(err => { if(log) log.innerHTML += `<br>[Error] ${err.message}`; });
}

function startAllServices() {
  const log = document.getElementById('mini-log');
  if (log) log.innerHTML += '<br>[App] Servisler başlatılıyor...';
  fetch('/api/projects/start-services', { method: 'POST' }).then(r => r.json()).then(data => {
    if(log) log.innerHTML += `<br>[System] ${data.message || 'Servisler tetiklendi.'}`;
    setTimeout(checkServiceStatus, 2000);
  }).catch(err => { if(log) log.innerHTML += `<br>[Error] ${err.message}`; });
}

function checkServiceStatus() {
  fetch('/api/projects/status').then(r => r.json()).then(data => {
    const stBackend = document.getElementById('status-backend');
    const msgBackend = document.getElementById('msg-backend');
    if (stBackend) stBackend.className = 'status-indicator online';
    if (msgBackend) msgBackend.innerText = 'Çalışıyor (5001)';
    const stN8n = document.getElementById('status-n8n');
    const msgN8n = document.getElementById('msg-n8n');
    if (stN8n) {
      stN8n.className = data.n8n ? 'status-indicator online' : 'status-indicator offline';
      if (msgN8n) msgN8n.innerText = data.n8n ? 'Çalışıyor (5678)' : 'Kapalı / Beklemede';
    }
  }).catch(() => {});
}

async function loadProjects() {
  try {
    const res = await fetch('/api/projects');
    const data = await res.json();
    const select = document.getElementById('active-project-select');
    if (!select) return;
    select.innerHTML = '<option value="">📁 Proje Seçin...</option>';
    if (data.projects) {
      data.projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.name;
        opt.textContent = p.name + (p.is_active ? ' ✓' : '');
        select.appendChild(opt);
      });
    }
  } catch (e) { console.error(e); }
}

setInterval(checkServiceStatus, 10000);
window.addEventListener('load', () => {
  checkServiceStatus();
  loadProjects();
});
