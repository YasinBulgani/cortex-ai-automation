// Pipeline Conductor Dashboard — live state management

(() => {
  'use strict';

  // ═══ State ═══
  let currentState = null;
  let selectedItem = null;
  let sseConnection = null;

  const STAGE_LABEL_MAP = {
    analyzer: 'A', validator: 'V', proposer: 'P',
    approver: 'AP', product_validator: 'PV',
    designer: 'DS', architect: 'AR',
    frontend: 'FE', backend: 'BE', data_engineer: 'DA', devops: 'DV',
    code_reviewer: 'CR', integrator: 'IN',
    qa: 'QA', security_reviewer: 'SE', a11y_auditor: 'A11', performance_tester: 'PF',
    promoter: 'PR', release_manager: 'RM', observer: 'OB', retrospective: 'RT',
  };

  // ═══ DOM helpers ═══
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));
  const el = (tag, attrs = {}, ...children) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'className') e.className = v;
      else if (k === 'onclick') e.addEventListener('click', v);
      else if (v !== undefined && v !== null) e.setAttribute(k, v);
    }
    for (const child of children.flat()) {
      if (typeof child === 'string') e.appendChild(document.createTextNode(child));
      else if (child instanceof Node) e.appendChild(child);
    }
    return e;
  };

  // ═══ Init ═══
  function init() {
    if (window.mermaid) {
      mermaid.initialize({ startOnLoad: true, theme: 'dark', flowchart: { htmlLabels: true } });
    }

    // HF status
    fetchHFStatus();

    // Initial state load
    fetchState();
    fetchMetrics();

    // SSE
    connectSSE();

    // Poll run status
    setInterval(fetchRunStatus, 4000);
    setInterval(fetchMetrics, 15000);

    // Button handlers
    $('#btn-start').addEventListener('click', onStart);
    $('#btn-stop').addEventListener('click', onStop);
    $('#btn-refresh').addEventListener('click', () => { fetchState(); fetchMetrics(); });
    $('#btn-clear-log').addEventListener('click', () => { $('#log-stream').innerHTML = ''; });
  }

  // ═══ API ═══
  async function fetchJSON(url, opts = {}) {
    const res = await fetch(url, opts);
    if (!res.ok) throw new Error(`${url} → ${res.status}`);
    return res.json();
  }

  async function fetchState() {
    try {
      currentState = await fetchJSON('/api/state');
      renderState(currentState);
    } catch (e) {
      console.error(e);
    }
  }

  async function fetchMetrics() {
    try {
      const metrics = await fetchJSON('/api/metrics');
      renderMetrics(metrics);
      renderHeatmap(metrics);
    } catch (e) {
      console.error('metrics', e);
    }
  }

  async function fetchHFStatus() {
    try {
      const s = await fetchJSON('/api/llm/status?quick=true');
      const dot = $('#hf-dot'), label = $('#hf-label');
      dot.className = 'chip-dot';
      if (s.provider === 'ollama') {
        if (s.reachable) {
          dot.classList.add('green');
          label.textContent = `Ollama: ${shortModel(s.default_model)}`;
        } else {
          dot.classList.add('red');
          label.textContent = 'Ollama: kapalı';
        }
      } else {
        if (s.token_set) {
          dot.classList.add('green');
          label.textContent = `HF: ${shortModel(s.default_model)}`;
        } else {
          dot.classList.add('yellow');
          label.textContent = 'HF: token yok';
        }
      }
      label.title = `Provider: ${s.provider} | Default: ${s.default_model}`;
    } catch (e) {
      $('#hf-dot').classList.add('red');
      $('#hf-label').textContent = 'LLM: err';
    }
  }

  async function fetchRunStatus() {
    try {
      const s = await fetchJSON('/api/run/status');
      const dot = $('#run-dot'), label = $('#run-label');
      if (s.running) {
        dot.classList.add('blue');
        label.textContent = `Running (pid=${s.pid}, ${s.mode})`;
        $('#btn-start').disabled = true;
        $('#btn-stop').disabled = false;
      } else {
        dot.className = 'chip-dot';
        label.textContent = 'Idle';
        $('#btn-start').disabled = false;
        $('#btn-stop').disabled = true;
      }
    } catch (e) { /* */ }
  }

  function connectSSE() {
    if (sseConnection) sseConnection.close();
    sseConnection = new EventSource('/api/events');

    sseConnection.onopen = () => {
      $('#sse-dot').className = 'chip-dot green';
      $('#sse-label').textContent = 'Live';
    };
    sseConnection.onerror = () => {
      $('#sse-dot').className = 'chip-dot red';
      $('#sse-label').textContent = 'Kopuk';
      setTimeout(connectSSE, 3000);
    };
    sseConnection.addEventListener('state', (ev) => {
      try {
        currentState = JSON.parse(ev.data);
        renderState(currentState);
        appendLog('state', 'state.json güncel');
      } catch (e) { console.error(e); }
    });
    sseConnection.addEventListener('agent', (ev) => {
      try {
        const evt = JSON.parse(ev.data);
        appendLog(evt.type, formatAgentEvent(evt), evt);
      } catch (e) { console.error(e); }
    });
  }

  // ═══ Render ═══
  function renderState(state) {
    const items = state.items || [];

    // KPIs
    $('#kpi-total .kpi-val').textContent = items.length;
    $('#kpi-inprog .kpi-val').textContent = items.filter(i => i.status === 'in_progress').length;
    $('#kpi-waiting .kpi-val').textContent = items.filter(i => i.status === 'waiting' || i.status === 'feedback_loop').length;
    $('#kpi-done .kpi-val').textContent = items.filter(i => i.status === 'done').length;
    $('#kpi-human .kpi-val').textContent = items.filter(i => i.needs_human).length;

    // Table
    const tbody = $('#items-tbody');
    tbody.innerHTML = '';

    if (items.length === 0) {
      tbody.appendChild(el('tr', {}, el('td', { colspan: 5, className: 'muted' },
        'No items — stage.sh init ile başlat veya dep-watchdog koştur')));
    } else {
      // Sort: needs_human first, then active, then waiting, then done
      const sorted = [...items].sort((a, b) => {
        if (a.needs_human !== b.needs_human) return b.needs_human ? 1 : -1;
        const ord = { in_progress: 0, waiting: 1, feedback_loop: 2, blocked: 3, done: 4, rejected: 5 };
        return (ord[a.status] ?? 9) - (ord[b.status] ?? 9);
      });
      for (const item of sorted) {
        const tr = el('tr', {
          className: item.id === selectedItem ? 'selected' : '',
          onclick: () => selectItem(item.id),
        },
          el('td', {}, el('span', { className: `item-id type-${item.type}` }, item.id)),
          el('td', { title: item.title }, truncate(item.title, 32)),
          el('td', {}, el('span', { className: 'stage-pill' }, item.current_stage || '—')),
          el('td', {}, el('span', { className: `status-badge status-${item.status}` }, item.status)),
          el('td', {}, renderScope(item.scope || {})),
        );
        tbody.appendChild(tr);
      }
    }

    // Re-render detail if selected
    if (selectedItem) {
      const it = items.find(i => i.id === selectedItem);
      if (it) renderItemDetail(it);
    }

    // Update graph based on selected item
    renderGraph();

    $('#last-update').textContent = 'Güncel: ' + new Date().toLocaleTimeString();
  }

  function renderScope(scope) {
    const flags = ['fe', 'be', 'data', 'infra', 'perf_sensitive'];
    const wrap = el('span', { className: 'scope-flags' });
    for (const f of flags) {
      if (scope[f] === true) {
        wrap.appendChild(el('span', { className: 'scope-flag on', title: `${f}=true` }, f.slice(0, 2)));
      }
    }
    return wrap;
  }

  function selectItem(id) {
    selectedItem = id;
    $$('.items-table tr').forEach(r => r.classList.remove('selected'));
    const item = (currentState?.items || []).find(i => i.id === id);
    if (item) {
      renderItemDetail(item);
      renderGraph();
      $('#selected-item-label').textContent = `${item.id} — ${item.title}`;
      $$('.items-table tr').forEach(r => {
        if (r.textContent.startsWith(id)) r.classList.add('selected');
      });
    }
  }

  function renderItemDetail(item) {
    const wrap = $('#item-detail');
    wrap.className = 'detail-content';
    wrap.innerHTML = '';

    wrap.appendChild(el('div', { className: 'detail-row' },
      el('strong', {}, 'Title: '),
      document.createTextNode(item.title)
    ));
    wrap.appendChild(el('div', { className: 'detail-row' },
      el('strong', {}, 'Type / Priority: '),
      document.createTextNode(`${item.type} · ${item.priority || 'medium'}`)
    ));
    if (item.needs_human) {
      wrap.appendChild(el('div', { className: 'detail-row', style: 'color:var(--yellow)' },
        '⚠ Needs human intervention'));
    }
    if (item.feedback_loops?.length) {
      wrap.appendChild(el('div', { className: 'detail-row' },
        el('strong', {}, `Feedback loops (${item.feedback_loops.length}): `),
        document.createTextNode(item.feedback_loops.map(fb => `${fb.from_stage}→${fb.to_stage}`).join(', '))
      ));
    }

    wrap.appendChild(el('div', { className: 'detail-row' }, el('strong', {}, 'Stages:')));
    for (const [stage, sdata] of Object.entries(item.stages || {})) {
      const row = el('div', { className: 'detail-stage' },
        el('span', { className: 'detail-stage-name' }, stage),
        el('span', {},
          el('span', { className: `status-badge status-${sdata.status}` }, sdata.status),
          sdata.branch ? ` · ${sdata.branch}` : '',
          sdata.artifact ? ` · ${sdata.artifact}` : '',
          sdata.approval?.decision ? ` · ${sdata.approval.decision} (${(sdata.approval.confidence ?? 0).toFixed(2)})` : '',
        ),
      );
      wrap.appendChild(row);
    }
  }

  function renderGraph() {
    // Style node classes based on selected item (if any)
    const svg = document.querySelector('#pipeline-graph svg');
    if (!svg) return;

    svg.querySelectorAll('[class*="node-"]').forEach(n => {
      n.classList.remove('node-done', 'node-waiting', 'node-inprogress', 'node-skipped', 'node-rejected');
    });

    const item = selectedItem
      ? (currentState?.items || []).find(i => i.id === selectedItem)
      : null;
    if (!item) return;

    const nodeIdMap = {
      analyzer: 'A', validator: 'V', proposer: 'P',
      approver: 'AP', product_validator: 'PV',
      designer: 'DS', architect: 'AR',
      frontend: 'FE', backend: 'BE', data_engineer: 'DA', devops: 'DV',
      code_reviewer: 'CR', integrator: 'IN',
      qa: 'QA', security_reviewer: 'SE', a11y_auditor: 'A11', performance_tester: 'PF',
      promoter: 'PR', release_manager: 'RM', observer: 'OB', retrospective: 'RT',
    };

    for (const [stage, sdata] of Object.entries(item.stages || {})) {
      const nodeId = nodeIdMap[stage];
      if (!nodeId) continue;
      const statusClass = {
        done: 'node-done',
        waiting: 'node-waiting',
        in_progress: 'node-inprogress',
        skipped: 'node-skipped',
        rejected: 'node-rejected',
      }[sdata.status];
      if (!statusClass) continue;
      // Mermaid uses flowchart-{id}-{n} pattern
      const nodeSelectors = [
        `.node[id*="flowchart-${nodeId}-"]`,
        `.node#flowchart-${nodeId}-`,
        `.node[id$="${nodeId}-0"]`,
      ];
      const nodes = svg.querySelectorAll(`g.node`);
      for (const n of nodes) {
        if (n.id && n.id.includes(`-${nodeId}-`)) {
          n.classList.add(statusClass);
        }
      }
    }
  }

  // ═══ Metrics ═══
  function renderMetrics(m) {
    const w = $('#metrics-summary');
    w.innerHTML = '';
    const tbl = el('table', { className: 'metrics-table' });

    const add = (k, v) => tbl.appendChild(el('tr', {}, el('td', {}, k), el('td', {}, String(v))));

    add('Total items', m.total_items ?? 0);
    add('Done (7d)', m.throughput?.last_week ?? 0);
    add('Done (28d)', m.throughput?.last_month ?? 0);
    if (m.cycle_time_stats) {
      add('Cycle median', fmtMin(m.cycle_time_stats.median_min));
      add('Cycle p90', fmtMin(m.cycle_time_stats.p90_min));
    }
    add('Loop-backs', m.loop_back_total ?? 0);
    add('Needs human', (m.needs_human || []).length);
    add('Stuck', (m.stuck_items || []).length);

    w.appendChild(tbl);

    // Bottleneck
    if (m.stage_stats && Object.keys(m.stage_stats).length) {
      const top = Object.entries(m.stage_stats)
        .sort((a, b) => b[1].avg_min - a[1].avg_min)
        .slice(0, 3);
      const bnTbl = el('table', { className: 'metrics-table', style: 'margin-top:10px' });
      bnTbl.appendChild(el('tr', {}, el('td', { colspan: 2, style: 'color:var(--yellow)' }, 'Top bottleneck stages')));
      for (const [stage, stats] of top) {
        bnTbl.appendChild(el('tr', {}, el('td', {}, stage), el('td', {}, fmtMin(stats.avg_min))));
      }
      w.appendChild(bnTbl);
    }
  }

  function renderHeatmap(m) {
    const w = $('#heatmap');
    w.innerHTML = '';
    const ALL_STAGES = [
      'analyzer', 'validator', 'proposer', 'approver', 'product_validator',
      'designer', 'architect',
      'frontend', 'backend', 'data_engineer', 'devops',
      'code_reviewer', 'integrator',
      'qa', 'security_reviewer', 'a11y_auditor', 'performance_tester',
      'promoter', 'release_manager', 'observer', 'retrospective',
    ];
    const waiting = m.stage_waiting_now || {};
    for (const s of ALL_STAGES) {
      const count = waiting[s] || 0;
      const heatClass = count === 0 ? 'heat-0' : count === 1 ? 'heat-1' : count <= 3 ? 'heat-2' : 'heat-3';
      const cell = el('div', { className: `heat-cell ${heatClass}`, title: `${s}: ${count} waiting` },
        el('div', { className: 'heat-count' }, String(count)),
        el('div', { className: 'heat-label' }, s.replace(/_/g, ' ')),
      );
      w.appendChild(cell);
    }
  }

  // ═══ Logs ═══
  function appendLog(type, text, meta = null) {
    const stream = $('#log-stream');
    const ts = new Date().toLocaleTimeString();
    const line = el('div', { className: `log-line ${type}` },
      el('span', { className: 'log-ts' }, ts),
      document.createTextNode(text),
    );
    stream.appendChild(line);
    stream.scrollTop = stream.scrollHeight;
    // Trim old lines
    while (stream.children.length > 300) stream.removeChild(stream.firstChild);
  }

  function formatAgentEvent(evt) {
    const t = evt.type;
    if (t === 'agent_started') return `▶ ${evt.item_id} · ${evt.role} başladı`;
    if (t === 'agent_succeeded') {
      let s = `✓ ${evt.item_id} · ${evt.role} done`;
      if (evt.model) s += ` (${shortModel(evt.model)}`;
      if (evt.latency_s) s += ` ${evt.latency_s.toFixed(1)}s)`;
      else if (evt.model) s += ')';
      if (evt.decision) s += ` decision=${evt.decision}`;
      return s;
    }
    if (t === 'agent_failed') return `✗ ${evt.item_id} · ${evt.role} FAILED: ${evt.error || 'unknown'}`;
    if (t === 'run_started') return `━━━ Run started (mode=${evt.mode}, concurrent=${evt.max_concurrent})`;
    if (t === 'round_started') return `── Round ${evt.round} — ${evt.waiting_count} waiting`;
    if (t === 'round_completed') return `── Round ${evt.round} done`;
    if (t === 'run_completed') return `━━━ Run completed in ${(evt.duration_s || 0).toFixed(0)}s (ok=${evt.agents_succeeded}, fail=${evt.agents_failed})`;
    return `${t}: ${JSON.stringify(evt)}`;
  }

  // ═══ Control actions ═══
  async function onStart() {
    const body = {
      mode: $('#run-mode').value,
      max_concurrent: parseInt($('#run-concurrent').value, 10),
      filter_role: $('#run-filter-role').value.trim() || null,
    };
    if (body.mode === 'watch') body.idle_exit_after_s = 300;
    try {
      const r = await fetchJSON('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      appendLog('run-started', `Started ${body.mode} (pid=${r.pid})`);
      fetchRunStatus();
    } catch (e) {
      appendLog('agent_failed', `Start error: ${e.message}`);
    }
  }

  async function onStop() {
    try {
      const r = await fetchJSON('/api/run/stop', { method: 'POST' });
      appendLog('agent_failed', `Stopped pid=${r.pid}`);
      fetchRunStatus();
    } catch (e) {
      appendLog('agent_failed', `Stop error: ${e.message}`);
    }
  }

  // ═══ Utils ═══
  const truncate = (s, n) => (s || '').length > n ? (s.slice(0, n - 1) + '…') : (s || '');
  const shortModel = (m) => (m || '').split('/').pop();
  const fmtMin = (m) => {
    if (m == null) return '—';
    if (m < 60) return `${m.toFixed(0)}m`;
    if (m < 1440) return `${(m/60).toFixed(1)}h`;
    return `${(m/1440).toFixed(1)}d`;
  };

  // Boot
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
