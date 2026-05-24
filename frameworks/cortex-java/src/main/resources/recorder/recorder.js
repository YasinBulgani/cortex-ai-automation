/* ===========================================================
 *  Cortex Recorder v3 - injected page script
 *  - CDP binding (window.__cortexSend) PRIMARY transport
 *  - HTTP fetch fallback
 *  - Multi-listener (window + document + documentElement)
 *    + multi-event (click + mousedown + pointerdown), capture+bubble
 *  - Visual probe (top of page, green strip) to prove inject worked
 *  - Verbose console log + debug overlay with TEST button
 *  ===========================================================
 */
(function () {
  // ── NULL-SAFE DOM HELPERS ────────────────────────────────────────────
  // Re-inject on SPA navigation can fire before document.documentElement /
  // body exist, or with a partially-torn-down tree. Sites like cortex-test
  // that use React Strict + heavy hydration hit this regularly.
  // Without these guards we get:
  //   - "Cannot read properties of null (reading 'setAttribute')"
  //   - "Failed to execute 'observe' on 'MutationObserver': parameter 1 is not of type 'Node'"
  // and the recorder stops capturing events even though the JVM is happy.
  function _docRoot() {
    return document.documentElement || document.body || null;
  }
  function _safeAppend(parent, child) {
    try {
      const p = parent || _docRoot();
      if (p && child) { p.appendChild(child); return true; }
    } catch (e) { console.warn('[cortex-rec] append failed', e); }
    return false;
  }
  function _safeObserve(cb, target, opts) {
    try {
      const t = target || _docRoot();
      if (!t || t.nodeType !== 1) {
        console.warn('[cortex-rec] observe target missing, will retry');
        return null;
      }
      const obs = new MutationObserver(cb);
      obs.observe(t, opts || { childList: true, subtree: true });
      return obs;
    } catch (e) {
      console.warn('[cortex-rec] observe failed', e);
      return null;
    }
  }
  // If the document is not yet usable, defer the entire IIFE body.
  if (!document.documentElement) {
    console.log('[cortex-rec] document not ready, waiting for DOMContentLoaded');
    document.addEventListener('DOMContentLoaded', () => {
      // Re-eval will be triggered by RecorderMain re-inject on next nav.
    }, { once: true });
    return;
  }

  // ── EARLY PROBE — React-proof (attaches to <html>, observed) ────────
  try {
    document.documentElement.setAttribute('data-cortex-recorder', 'v3');

    const PROBE_ID = 'cortex-rec-probe';
    const ensureProbe = () => {
      if (document.getElementById(PROBE_ID)) return;
      const probe = document.createElement('div');
      probe.id = PROBE_ID;
      probe.style.cssText = 'position:fixed!important;top:0!important;left:0!important;right:0!important;height:4px!important;background:linear-gradient(90deg,#00ff99,#00cc66,#00ff99)!important;background-size:200% 100%!important;z-index:2147483647!important;pointer-events:none!important;box-shadow:0 0 12px rgba(0,255,153,0.7)!important;animation:cortex-rec-pulse 2s linear infinite!important;';
      // Attach to <html> directly so React rebuilding <body> can't remove it
      _safeAppend(document.documentElement, probe);
    };
    ensureProbe();

    // Inline keyframes (also React-proof since style goes in <head>)
    if (!document.getElementById('cortex-rec-anim')) {
      const s = document.createElement('style');
      s.id = 'cortex-rec-anim';
      s.textContent = '@keyframes cortex-rec-pulse{0%{background-position:0% 0%}100%{background-position:200% 0%}}';
      (document.head || document.documentElement).appendChild(s);
    }

    // Re-attach probe if React/SPA removes it
    _safeObserve(() => ensureProbe(), document.documentElement, { childList: true, subtree: true });

    // Title marker so the user knows they're in the right Chromium window
    const setTitle = () => {
      if (!document.title.startsWith('[REC] ')) {
        try { document.title = '[REC] ' + document.title; } catch (_) {}
      }
    };
    setTitle();
    document.addEventListener('DOMContentLoaded', setTitle);
    // Also rewrite if SPA changes title
    _safeObserve(() => setTitle(), document.head || document.documentElement, { childList: true, subtree: true });

    // ── BIG "WRONG BROWSER" GUARD BANNER ──────────────────────────────
    // Auto-hides after 10 seconds OR when user clicks ✕.
    // Re-appears every time recorder is re-injected (framenavigated).
    const BANNER_ID = 'cortex-rec-bigbanner';
    const ensureBigBanner = () => {
      if (document.getElementById(BANNER_ID)) return;
      if (window.__cortexBannerDismissed) return;  // user closed it, respect that
      const b = document.createElement('div');
      b.id = BANNER_ID;
      b.style.cssText = [
        'position:fixed!important', 'top:50px!important', 'left:50%!important',
        'transform:translateX(-50%)!important', 'z-index:2147483646!important',
        'background:linear-gradient(135deg,#00ff99,#00cc66)!important', 'color:#000!important',
        'padding:18px 28px!important', 'border-radius:14px!important',
        'font:bold 16px/1.4 system-ui!important', 'box-shadow:0 12px 36px rgba(0,0,0,.45),0 0 0 4px rgba(0,255,153,.3)!important',
        'border:3px solid #fff!important', 'max-width:580px!important', 'text-align:center!important',
        'cursor:default!important', 'animation:cortex-banner-in .3s ease-out!important',
      ].join(';') + ';';
      b.innerHTML = '🎬 <u>BU PENCERE RECORDER\'A AİT</u> 🎬<br>' +
        '<span style="font-size:13px!important;font-weight:normal!important;display:block!important;margin-top:6px!important;">' +
        'Sadece bu pencerede yaptığın işlemler kayıt olur.<br>' +
        'Normal Chrome/Edge/Safari\'de yapacağın hiçbir şey yakalanmaz.' +
        '</span>' +
        '<button id="cortex-bigbanner-close" style="margin-top:10px!important;padding:6px 16px!important;background:#000!important;color:#0fa!important;border:none!important;border-radius:6px!important;font:bold 12px system-ui!important;cursor:pointer!important;">Anladım ✓</button>';
      document.documentElement.appendChild(b);
      const closeBtn = b.querySelector('#cortex-bigbanner-close');
      if (closeBtn) closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        window.__cortexBannerDismissed = true;
        b.remove();
      });
      // Auto-hide after 10s
      setTimeout(() => { if (b.parentNode) { window.__cortexBannerDismissed = true; b.remove(); } }, 10000);
    };
    ensureBigBanner();

    // CSS animation
    if (!document.getElementById('cortex-banner-anim')) {
      const s = document.createElement('style');
      s.id = 'cortex-banner-anim';
      s.textContent = '@keyframes cortex-banner-in{from{opacity:0;transform:translateX(-50%) translateY(-20px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}';
      (document.head || document.documentElement).appendChild(s);
    }
  } catch (e) { console.error('[cortex-rec] probe install failed', e); }

  console.log('[cortex-rec] v3 loading…', { url: location.href, hasBinding: typeof window.__cortexSend === 'function', topFrame: window === top });

  // Global error capture so we never silently lose script execution again.
  window.__cortexLastError = null;
  window.addEventListener('error', (ev) => {
    window.__cortexLastError = {
      msg: ev.message, src: ev.filename, line: ev.lineno, col: ev.colno,
      stack: ev.error?.stack, at: Date.now()
    };
    try { console.error('[cortex-rec] global error', window.__cortexLastError); } catch (_) {}
  }, true);
  window.addEventListener('unhandledrejection', (ev) => {
    window.__cortexLastError = { msg: 'unhandledrejection: ' + (ev.reason?.message || ev.reason), stack: ev.reason?.stack, at: Date.now() };
    try { console.error('[cortex-rec] unhandled rejection', window.__cortexLastError); } catch (_) {}
  });

  // Expose a diag function the user can call from DevTools console:
  // > __cortexDiag()
  window.__cortexDiag = function () {
    // Guarded: __dbg might still be in TDZ if script crashed before its decl
    let dbg = { tdz: true };
    try { dbg = __dbg; } catch (_) { /* TDZ — leave default */ }
    const info = {
      'recorderJs marker': document.documentElement.getAttribute('data-cortex-recorder'),
      'window.__cortexSend type': typeof window.__cortexSend,
      'window.__cortexRecorderActive': typeof window.__cortexRecorderActive,
      'probe element': !!document.getElementById('cortex-rec-probe'),
      'debug overlay':  !!document.getElementById('cortex-rec-debug'),
      'toolbar':        !!document.getElementById('cortex-rec-toolbar'),
      'clicks captured': dbg.clicks ?? '?',
      'inputs captured': dbg.inputs ?? '?',
      'changes captured': dbg.changes ?? '?',
      'submits captured': dbg.submits ?? '?',
      'sent OK':         dbg.sends ?? '?',
      'sent FAIL':       dbg.fails ?? '?',
      'heartbeat ticks': dbg.heartbeat ?? '?',
      'last error':      window.__cortexLastError?.msg || 'none',
      'url':            location.href,
      'top frame?':     window === top,
      'document.title': document.title,
    };
    console.table(info);
    if (window.__cortexLastError) console.error('LAST ERROR:', window.__cortexLastError);
    return info;
  };

  if (window.__cortexRecorderActive) {
    console.log('[cortex-rec] already active in this frame, exiting');
    return;
  }
  window.__cortexRecorderActive = true;

  const PORT = window.__CORTEX_RECORDER_PORT__ || 7700;
  const BASE = `http://127.0.0.1:${PORT}`;

  // --- inject styles ---
  try {
    const css = window.__CORTEX_RECORDER_CSS__ || '';
    const style = document.createElement('style');
    style.id = 'cortex-rec-style';
    style.textContent = css;
    (document.head || document.documentElement).appendChild(style);
  } catch (e) {}

  let state = {
    paused: false,
    assertMode: false,
    actionCount: 0,
    recentActions: [],   // R3: son 5 aksiyonun ozeti
  };

  // ── HOISTED early so re-injection (framenavigated) doesn't hit TDZ ──
  //    Previously these were declared lower in the file. When the script
  //    re-runs on a page that's already loaded, emitNavigateOnce() fires
  //    *immediately* (before lower-line `let` declarations execute) and
  //    threw ReferenceError on __nav / __dbg, killing toolbar/overlay/heartbeat.
  let __nav = false;
  let __dbg = { clicks: 0, sends: 0, fails: 0, inputs: 0, changes: 0, submits: 0, navs: 0, heartbeat: 0, lowlevel: 0, errors: 0 };
  let __hbCount = 0;
  let __failCount = 0;

  // ----------------------------------------------------------
  //  POST helper
  // ----------------------------------------------------------
  /**
   * Action transport — TRIPLE PATH for max reliability:
   *   1. Playwright exposeBinding (no PNA/CORS issues)        [preferred]
   *   2. console.log("__CORTEX_ACTION__" + json) backup       [bullet-proof]
   *   3. HTTP fetch fallback (bookmarklet mode outside JVM)   [last resort]
   *
   * The console-log channel always works because Playwright reads console
   * messages via CDP, regardless of page CSP/PNA/CORS state.
   */
  async function send(action) {
    if (state.paused && action.type !== 'navigate') return;
    if (!action.timestamp) action.timestamp = Date.now();
    action.url = location.href;

    // ── CHANNEL 2: console-based backup. ALWAYS emit — Java side reads
    //    these via page.onConsoleMessage. If binding works, action shows up
    //    twice in Java logs but RecorderServer.addAction dedups by timestamp.
    //    More importantly, if binding is broken on this domain, this channel
    //    still gets the action through.
    try { console.log('__CORTEX_ACTION__' + JSON.stringify(action)); } catch (_) {}

    try {
      let j = null;
      if (typeof window.__cortexSend === 'function') {
        // ── CHANNEL 1: CDP binding path (preferred — bypasses PNA) ──
        j = await window.__cortexSend(action);
      } else {
        // ── CHANNEL 3: HTTP fallback ──
        const resp = await fetch(`${BASE}/action`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(action),
          mode: 'cors', credentials: 'omit', cache: 'no-store',
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        j = await resp.json();
      }
      if (j && j.count != null) {
        state.actionCount = j.count;
        state.recentActions.unshift(describeActionShort(action));
        state.recentActions = state.recentActions.slice(0, 5);
        updateToolbar();
        __failCount = 0;
        // Remove the persistent error banner if it was up
        const err = document.getElementById('cortex-rec-err');
        if (err) err.remove();
      }
    } catch (e) {
      __failCount++;
      console.error('[cortex-rec] action send failed (channel 1/3 failed; console channel may still deliver):', e, action);
      if (__failCount <= 3) {
        toast(`CDP binding fail — console kanalı kullanılıyor`);
      } else if (__failCount === 4) {
        showPersistentError(
          'CDP binding (__cortexSend) yok. Console kanalı yedek olarak\n' +
          'çalışıyor olabilir (Java logs\'ta görürsün).\n' +
          'Yine de aksiyon gelmiyorsa Recorder JVM\'i yeniden başlat.'
        );
      }
    }
  }

  function showPersistentError(msg) {
    let el = document.getElementById('cortex-rec-err');
    if (!el) {
      el = document.createElement('div');
      el.id = 'cortex-rec-err';
      el.style.cssText = 'position:fixed!important;top:8px!important;right:8px!important;z-index:2147483647!important;background:#7f1d1d!important;color:#fff!important;padding:12px 16px!important;border-radius:8px!important;font:13px/1.4 system-ui!important;max-width:340px!important;box-shadow:0 10px 25px rgba(0,0,0,.5)!important;white-space:pre-line!important;border:1px solid #f87171!important;';
      document.documentElement.appendChild(el);
    }
    el.textContent = '⚠ ' + msg;
  }

  function describeActionShort(a) {
    if (a.type === 'click' && a.element?.text) return `click "${a.element.text.slice(0, 30)}"`;
    if (a.type === 'click' && a.element?.tag) return `click <${a.element.tag}>`;
    if (a.type === 'fill') return `fill "${(a.text || '').slice(0, 30)}"`;
    if (a.type === 'navigate') return `nav ${(a.url || '').slice(0, 40)}`;
    if (a.type === 'press') return `press ${a.key}`;
    if (a.type === 'wait') return `wait ${a.seconds}s`;
    if (a.type.startsWith('assert')) return a.type;
    return a.type;
  }

  // ----------------------------------------------------------
  //  Locator info builder (eleman -> ElementInfo)
  // ----------------------------------------------------------
  function describe(el) {
    if (!el || el.nodeType !== 1) return null;
    const attrs = {};
    for (const a of el.attributes || []) attrs[a.name] = a.value;
    return {
      tag: (el.tagName || '').toLowerCase(),
      id: el.id || null,
      name: el.getAttribute('name'),
      type: el.getAttribute('type'),
      value: 'value' in el ? (el.value || null) : null,
      placeholder: el.getAttribute('placeholder'),
      role: el.getAttribute('role'),
      ariaLabel: el.getAttribute('aria-label'),
      dataTestId: el.getAttribute('data-testid') || el.getAttribute('data-test-id') || el.getAttribute('data-test'),
      dataCy: el.getAttribute('data-cy'),
      dataQa: el.getAttribute('data-qa'),
      text: (el.innerText || el.textContent || '').trim().slice(0, 120),
      href: el.getAttribute('href'),
      cssPath: cssPathFor(el),
      xpath: xpathFor(el),
      attributes: attrs,
      isPassword: (el.tagName === 'INPUT' && (el.type === 'password')),
    };
  }

  function cssPathFor(el) {
    if (!(el instanceof Element)) return '';
    const path = [];
    let cur = el;
    while (cur && cur.nodeType === 1 && path.length < 5) {
      let part = cur.nodeName.toLowerCase();
      if (cur.id) { part += `#${CSS.escape(cur.id)}`; path.unshift(part); break; }
      const cls = (cur.className || '').toString().trim().split(/\s+/).filter(Boolean).slice(0, 2);
      if (cls.length) part += '.' + cls.map(c => CSS.escape(c)).join('.');
      const parent = cur.parentNode;
      if (parent && parent.children) {
        const same = Array.from(parent.children).filter(c => c.nodeName === cur.nodeName);
        if (same.length > 1) part += `:nth-of-type(${same.indexOf(cur) + 1})`;
      }
      path.unshift(part);
      cur = cur.parentElement;
    }
    return path.join(' > ');
  }

  function xpathFor(el) {
    if (!(el instanceof Element)) return '';
    if (el.id) return `//*[@id='${el.id}']`;
    const parts = [];
    let cur = el;
    while (cur && cur.nodeType === 1 && parts.length < 6) {
      let idx = 1;
      let sib = cur.previousElementSibling;
      while (sib) { if (sib.nodeName === cur.nodeName) idx++; sib = sib.previousElementSibling; }
      parts.unshift(`${cur.nodeName.toLowerCase()}[${idx}]`);
      cur = cur.parentElement;
    }
    return '/' + parts.join('/');
  }

  // ----------------------------------------------------------
  //  PAGE SCAN — enumerate all interactive elements + selectors
  // ----------------------------------------------------------
  function isVisible(el) {
    if (!el || !el.getBoundingClientRect) return false;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return false;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
    return true;
  }

  function scanPage() {
    const SELECTORS = [
      'a[href]',
      'button',
      'input:not([type=hidden])',
      'select',
      'textarea',
      '[role="button"]',
      '[role="link"]',
      '[role="textbox"]',
      '[role="checkbox"]',
      '[role="tab"]',
      '[role="menuitem"]',
      '[onclick]',
      '[tabindex]:not([tabindex="-1"])',
      'label',
      'summary',
    ];
    const seen = new Set();
    const list = [];
    let counter = 0;
    document.querySelectorAll(SELECTORS.join(',')).forEach((el) => {
      if (seen.has(el)) return;
      seen.add(el);
      if (!isVisible(el)) return;
      counter++;
      const info = describe(el);
      const label =
        info.dataTestId
          ? `[data-testid="${info.dataTestId}"]`
          : info.id
            ? `#${info.id}`
            : info.text
              ? `${info.tag} "${info.text.slice(0, 40)}"`
              : info.placeholder
                ? `${info.tag}[placeholder="${info.placeholder.slice(0, 30)}"]`
                : info.ariaLabel
                  ? `${info.tag}[aria-label="${info.ariaLabel.slice(0, 30)}"]`
                  : info.name
                    ? `${info.tag}[name="${info.name}"]`
                    : `<${info.tag}>`;
      list.push({
        index: counter,
        tag: info.tag,
        id: info.id,
        name: info.name,
        type: info.type,
        text: info.text,
        placeholder: info.placeholder,
        ariaLabel: info.ariaLabel,
        dataTestId: info.dataTestId,
        role: info.role,
        href: info.href,
        isPassword: info.isPassword,
        xpath: info.xpath,
        cssPath: info.cssPath,
        label, // human-readable
      });
    });
    return { url: location.href, title: document.title, count: list.length, scannedAt: Date.now(), elements: list };
  }
  // Expose for Java page.evaluate
  window.__cortexScan = scanPage;

  // Auto-scan + push to JVM
  let __lastScanAt = 0;
  function autoScanAndPush() {
    try {
      const now = Date.now();
      if (now - __lastScanAt < 800) return; // throttle
      __lastScanAt = now;
      const snap = scanPage();
      console.log('[cortex-rec] scan:', snap.count, 'interactive elements');
      if (typeof window.__cortexElements === 'function') {
        try { window.__cortexElements(snap); } catch (e) { console.error('push elements failed', e); }
      }
    } catch (e) {
      console.error('[cortex-rec] scanPage failed', e);
    }
  }

  // First scan after DOMContentLoaded + load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(autoScanAndPush, 300));
  } else {
    setTimeout(autoScanAndPush, 300);
  }
  window.addEventListener('load', () => setTimeout(autoScanAndPush, 500));

  // Re-scan when the DOM changes substantially (SPA route, modal open, etc.)
  let __scanTimer = null;
  _safeObserve(() => {
    clearTimeout(__scanTimer);
    __scanTimer = setTimeout(autoScanAndPush, 600);
  }, document.documentElement, { childList: true, subtree: true });

  // ----------------------------------------------------------
  //  Highlight feedback
  // ----------------------------------------------------------
  function flash(el, captured = true) {
    if (!el || el.nodeType !== 1) return;
    const cls = captured ? 'cortex-rec-captured-outline' : 'cortex-rec-hover-outline';
    el.classList.add(cls);
    setTimeout(() => el.classList.remove(cls), 500);
  }

  function toast(msg) {
    let t = document.getElementById('cortex-rec-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'cortex-rec-toast';
      document.documentElement.appendChild(t);
    }
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(t.__h);
    t.__h = setTimeout(() => t.classList.remove('show'), 1500);
  }

  // ----------------------------------------------------------
  //  Event listeners
  // ----------------------------------------------------------
  function shouldSkip(target) {
    if (!target || !target.closest) return true;
    if (target.closest('#cortex-rec-toolbar'))     return true;
    if (target.closest('#cortex-rec-debug'))       return true;
    if (target.closest('#cortex-rec-err'))         return true;
    if (target.closest('#cortex-pick-banner'))     return true;
    if (target.closest('#cortex-pick-outline'))    return true;
    if (target.closest('#cortex-pick-tip'))        return true;
    if (target.closest('#cortex-pick-locked'))     return true;
    if (target.closest('#cortex-action-chooser'))  return true;
    return false;
  }

  // ── CLICK CAPTURE (bulletproof) ─────────────────────────────────────
  // Some sites intercept events on window or document. We attach to all
  // three targets and to multiple event names; dedup by element+timestamp.
  const __recentClick = { target: null, t: 0 };
  function clickHandler(e) {
    if (typeof __dbg !== 'undefined') { __dbg.clicks++; updateDebugOverlay && updateDebugOverlay(); }
    console.log('[cortex-rec] event:', e.type, '@', e.eventPhase === 1 ? 'capture' : 'bubble',
                '·', e.target?.tagName, e.target);
    if (shouldSkip(e.target)) { console.log('[cortex-rec] skipped (own UI)'); return; }
    // Dedup: ignore multi-handler firings within 80ms for the same target
    const now = Date.now();
    if (__recentClick.target === e.target && (now - __recentClick.t) < 80) {
      console.log('[cortex-rec] dedup');
      return;
    }
    __recentClick.target = e.target; __recentClick.t = now;

    if (state.assertMode) {
      send({ type: 'assert_visible', element: describe(e.target) });
      flash(e.target);
      state.assertMode = false;
      document.documentElement.style.cursor = '';
      document.getElementById('cortex-rec-toolbar')?.classList.remove('assert-mode');
      toast('Assertion eklendi');
      return;
    }
    send({ type: 'click', element: describe(e.target) });
    flash(e.target);
  }

  function attachClickListeners() {
    const targets = [window, document, document.documentElement].filter(Boolean);
    // 'click' fires on left-button. 'mousedown' + 'pointerdown' are backups
    // in case the page calls stopPropagation on 'click'.
    const events = ['click', 'mousedown', 'pointerdown'];
    targets.forEach((t) => {
      events.forEach((ev) => {
        try {
          // capture phase first (runs before bubble + before site handlers)
          t.addEventListener(ev, clickHandler, { capture: true, passive: true });
          // bubble phase as last-resort backup
          t.addEventListener(ev, clickHandler, { capture: false, passive: true });
        } catch (e) { console.warn('[cortex-rec] listener attach failed', t, ev, e); }
      });
    });
    console.log('[cortex-rec]', targets.length, 'targets ×', events.length, '× 2 phases =', targets.length * events.length * 2, 'listeners attached');
  }
  attachClickListeners();
  // Some sites replace document.body or remove our listeners. Re-attach on load.
  window.addEventListener('load', attachClickListeners, { once: true });

  // ── INPUT / CHANGE / SUBMIT — multi-target, multi-event ─────────────
  // Sites can intercept clicks but rarely intercept input/change/submit
  // because that would break form usability. Attach to window+document.
  function attachFormListeners() {
    const targets = [window, document, document.documentElement].filter(Boolean);
    const events = ['input', 'change', 'submit'];
    targets.forEach(t => events.forEach(ev => {
      try {
        // capture + bubble for redundancy
        if (ev === 'input')      t.addEventListener(ev, inputHandler,   { capture: true, passive: true });
        else if (ev === 'change') t.addEventListener(ev, changeHandler, { capture: true, passive: true });
        else                      t.addEventListener(ev, submitHandler, { capture: true, passive: true });
      } catch (_) {}
    }));
    console.log('[cortex-rec] form event listeners attached (input/change/submit on', targets.length, 'targets)');
  }

  function inputHandler(e) {
    if (typeof __dbg !== 'undefined') { __dbg.inputs = (__dbg.inputs || 0) + 1; updateDebugOverlay && updateDebugOverlay(); }
    console.log('[cortex-rec] input event:', e.target?.tagName, '"' + (e.target?.value || '').slice(0, 20) + '..."');
    if (shouldSkip(e.target)) return;
    const el = e.target;
    if (!('value' in el)) return;
    clearTimeout(lastInput.get(el));
    const h = setTimeout(async () => {
      if (el.type === 'password' && !el.__cortexAliasAsked) {
        const alias = prompt(
          'Bu sifre alanini hangi alias ile saklayalim?\n(Iptal: "recordedPassword")',
          el.name || el.id || 'cortexUser'
        );
        el.__cortexAliasAsked = true;
        el.__cortexAlias = (alias && alias.trim()) || 'recordedPassword';
      }
      const action = { type: 'fill', element: describe(el), text: el.value };
      if (el.__cortexAlias) action.passwordAlias = el.__cortexAlias;
      send(action);
    }, 500); // debounce 500ms — fires after user stops typing
    lastInput.set(el, h);
  }

  function changeHandler(e) {
    if (typeof __dbg !== 'undefined') { __dbg.changes = (__dbg.changes || 0) + 1; }
    console.log('[cortex-rec] change event:', e.target?.tagName, e.target?.value);
    if (shouldSkip(e.target)) return;
    const el = e.target;
    if (el.tagName === 'SELECT') {
      send({ type: 'change', element: describe(el), text: el.value });
    } else if (el.type === 'checkbox' || el.type === 'radio') {
      send({ type: el.checked ? 'click' : 'click', element: describe(el) });
    }
  }

  function submitHandler(e) {
    if (typeof __dbg !== 'undefined') { __dbg.submits = (__dbg.submits || 0) + 1; }
    console.log('[cortex-rec] submit event:', e.target);
    if (shouldSkip(e.target)) return;
    // record form submission as a "press Enter on the active input"
    const active = document.activeElement;
    if (active && active.value !== undefined) {
      send({ type: 'press', key: 'Enter', element: describe(active) });
    } else {
      send({ type: 'comment', text: 'form submitted' });
    }
  }

  // Track url changes (SPA pushState/replaceState/popstate)
  function attachUrlChangeWatchers() {
    let __lastUrl = location.href;
    const fire = () => {
      if (location.href !== __lastUrl) {
        const from = __lastUrl;
        __lastUrl = location.href;
        console.log('[cortex-rec] url change:', from, '→', location.href);
        if (typeof __dbg !== 'undefined') __dbg.navs = (__dbg.navs || 0) + 1;
        send({ type: 'navigate' });
      }
    };
    ['pushState', 'replaceState'].forEach(m => {
      const orig = history[m];
      if (orig.__cortexHooked) return;
      history[m] = function () {
        const ret = orig.apply(this, arguments);
        setTimeout(fire, 50);
        return ret;
      };
      history[m].__cortexHooked = true;
    });
    window.addEventListener('popstate', fire);
    window.addEventListener('hashchange', fire);
    // Also poll URL every 500ms as ultimate fallback
    if (!window.__cortexUrlPoll) {
      window.__cortexUrlPoll = setInterval(fire, 500);
    }
  }
  // Per-element debounce map used by inputHandler
  const lastInput = new WeakMap();

  // Wire up the form listeners + URL watchers that were declared above.
  attachFormListeners();
  attachUrlChangeWatchers();

  // KEY ENTER/ESC/TAB — covers standalone keypresses that don't fire a submit.
  // submitHandler handles the form-submit case; this one handles bare Tab/Esc.
  document.addEventListener('keydown', (e) => {
    if (shouldSkip(e.target)) return;
    if (e.key === 'Enter' || e.key === 'Escape' || e.key === 'Tab') {
      send({ type: 'press', key: e.key, element: describe(e.target) });
    }
  }, true);

  // R1: iframe enjeksiyonu (yeni eklenen iframe'lere recorder.js gir)
  // Playwright Page.addInitScript zaten her frame'e enjekte ediyor; bu
  // mevcut sayfada sonradan eklenen iframe'leri kapsiyor.
  _safeObserve((mutations) => {
    for (const m of mutations) {
      for (const node of m.addedNodes) {
        if (node.tagName === 'IFRAME') {
          try {
            const doc = node.contentDocument;
            if (doc && !doc.__cortexRecorderAttached) {
              doc.__cortexRecorderAttached = true;
              console.log('[Cortex Recorder] iframe detected:', node.src);
            }
          } catch (e) { /* cross-origin */ }
        }
      }
    }
  }, document.documentElement, { childList: true, subtree: true });

  // Initial navigate aksiyonu
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => emitNavigateOnce());
  } else {
    // Defer to next tick so any later top-level statements finish executing
    setTimeout(emitNavigateOnce, 0);
  }
  function emitNavigateOnce() {
    if (__nav) return; __nav = true;
    try { send({ type: 'navigate' }); } catch (e) { console.error('[cortex-rec] navigate failed', e); }
    try { buildToolbar(); }           catch (e) { console.error('[cortex-rec] buildToolbar failed', e); }
    try { installDebugOverlay(); }    catch (e) { console.error('[cortex-rec] installDebugOverlay failed', e); }
  }

  // ----------------------------------------------------------
  //  DEBUG overlay — sol üst köşede sabit
  //  Binding var mı, kaç tıklama yakalandı, kaç başarılı send
  // ----------------------------------------------------------
  // (__dbg hoisted to top of IIFE — see TDZ comment up there)
  function installDebugOverlay() {
    if (document.getElementById('cortex-rec-debug')) {
      updateDebugOverlay();
      return;
    }
    const wrap = document.createElement('div');
    wrap.id = 'cortex-rec-debug';
    wrap.style.cssText = 'position:fixed!important;top:12px!important;left:12px!important;z-index:2147483647!important;background:rgba(0,0,0,0.92)!important;color:#0fa!important;padding:10px 14px!important;border-radius:10px!important;font:12px/1.45 "SF Mono",Menlo,monospace!important;border:2px solid #0fa!important;white-space:pre!important;box-shadow:0 8px 24px rgba(0,255,153,0.25)!important;min-width:260px!important;';

    const txt = document.createElement('div');
    txt.id = 'cortex-rec-debug-text';
    wrap.appendChild(txt);

    const testBtn = document.createElement('button');
    testBtn.textContent = '⚡ TEST send()';
    testBtn.style.cssText = 'margin-top:8px!important;width:100%!important;padding:6px 10px!important;background:#0fa!important;color:#000!important;border:none!important;border-radius:6px!important;font:bold 11px monospace!important;cursor:pointer!important;';
    testBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      console.log('[cortex-rec] TEST button clicked');
      const fake = { type: 'comment', text: '[TEST] debug overlay button — ' + new Date().toLocaleTimeString() };
      try { await send(fake); console.log('[cortex-rec] TEST send succeeded'); }
      catch (err) { console.error('[cortex-rec] TEST send failed:', err); }
    });
    wrap.appendChild(testBtn);

    // Attach to <html> instead of <body> so React's body replacement can't remove us
    document.documentElement.appendChild(wrap);
    updateDebugOverlay();

    // Watch for removal and re-attach
    if (!window.__cortexDbgObserver) {
      window.__cortexDbgObserver = _safeObserve(() => {
        if (!document.getElementById('cortex-rec-debug')) installDebugOverlay();
      }, document.documentElement, { childList: true, subtree: false });
    }
  }
  function updateDebugOverlay() {
    const wrap = document.getElementById('cortex-rec-debug');
    const txt  = document.getElementById('cortex-rec-debug-text');
    if (!wrap || !txt) return;
    const hasBinding = typeof window.__cortexSend === 'function';
    const transport  = hasBinding ? 'CDP binding ✓' : 'HTTP fallback';
    const color      = hasBinding ? '#0fa' : '#fc0';
    wrap.style.color = color;
    wrap.style.borderColor = color;
    txt.textContent =
      `🎬 CORTEX RECORDER v3 (hybrid)\n` +
      `transport : ${transport}\n` +
      `port      : ${PORT}\n` +
      `URL frame : ${location.host}\n` +
      `clicks    : ${__dbg.clicks || 0}\n` +
      `inputs    : ${__dbg.inputs || 0}    (auto-recorded)\n` +
      `changes   : ${__dbg.changes || 0}\n` +
      `submits   : ${__dbg.submits || 0}\n` +
      `navs      : ${__dbg.navs || 0}\n` +
      `sent      : ${__dbg.sends || 0}\n` +
      `failed    : ${__dbg.fails || 0}\n` +
      `heartbeat : ${__dbg.heartbeat || 0}\n` +
      `pause     : ${state.paused}`;
  }
  // Wrap send to increment send/fail counters (click counter is in the listener)
  const __origSend = send;
  send = async function (action) {
    updateDebugOverlay();
    try {
      const r = await __origSend(action);
      if (action && action.type !== 'navigate') { __dbg.sends++; updateDebugOverlay(); }
      return r;
    } catch (e) {
      __dbg.fails++;
      updateDebugOverlay();
      throw e;
    }
  };

  // ----------------------------------------------------------
  //  Toolbar (R3: live preview, R4: undo)
  // ----------------------------------------------------------
  function buildToolbar() {
    if (document.getElementById('cortex-rec-toolbar')) return;
    const bar = document.createElement('div');
    bar.id = 'cortex-rec-toolbar';
    bar.innerHTML = `
      <span class="dot"></span>
      <span class="lbl">REC</span>
      <span class="count">0</span>
      <span class="hybrid-hint" style="color:#0fa!important;font:11px system-ui!important;margin:0 8px!important;opacity:.85!important;" title="Yazılan değerler otomatik kayıt edilir. Butonlar/linkler için 'ELEMENT SEÇ' kullan.">
        ⌨ Yaz → otomatik · 👆 Tıkla → SEÇ
      </span>
      <button data-act="pick" class="pick-btn" style="background:#0fa!important;color:#000!important;font-weight:bold">🎯 ELEMENT SEÇ</button>
      <button data-act="pause">Duraklat</button>
      <button data-act="undo" title="Son aksiyonu sil">↶ Geri Al</button>
      <button data-act="assert" class="assert-btn">Dogrulama</button>
      <button data-act="wait">+ Bekleme</button>
      <button data-act="stop" class="danger">Durdur ve Kaydet</button>
      <div class="recent"></div>
    `;
    // Attach to <html> so React rebuilding <body> can't remove us
    (document.body || document.documentElement).appendChild(bar);

    bar.addEventListener('click', (e) => {
      const btn = e.target.closest('button');
      if (!btn) return;
      const act = btn.dataset.act;
      if (act === 'pick') {
        startPickMode();
        return;
      }
      if (act === 'pause') {
        state.paused = !state.paused;
        btn.textContent = state.paused ? 'Devam et' : 'Duraklat';
        bar.classList.toggle('paused', state.paused);
        toast(state.paused ? 'Duraklatildi' : 'Devam ediyor');
      } else if (act === 'undo') {
        const undoFn = typeof window.__cortexUndo === 'function'
          ? window.__cortexUndo()
          : fetch(`${BASE}/undo`, { method: 'POST' }).then(r => r.json());
        Promise.resolve(undoFn).then((j) => {
          if (j && j.ok) {
            state.actionCount = (j.count != null) ? j.count : Math.max(0, state.actionCount - 1);
            state.recentActions.shift();
            updateToolbar();
            toast('Son aksiyon silindi');
          }
        }).catch(() => toast('Geri alma basarisiz'));
      } else if (act === 'assert') {
        state.assertMode = !state.assertMode;
        bar.classList.toggle('assert-mode', state.assertMode);
        document.documentElement.style.cursor = state.assertMode ? 'crosshair' : '';
        toast(state.assertMode ? 'Dogrulama modu - tikla' : 'Dogrulama kapatildi');
      } else if (act === 'wait') {
        const secs = parseInt(prompt('Kac saniye bekle?', '2'), 10);
        if (!isNaN(secs) && secs > 0) {
          send({ type: 'wait', seconds: secs });
          toast(`+ ${secs}s bekleme`);
        }
      } else if (act === 'stop') {
        if (typeof window.__cortexStop === 'function') {
          try { window.__cortexStop(); } catch (_) {}
        } else {
          fetch(`${BASE}/stop`, { method: 'POST' }).catch(() => {});
        }
        toast('Kayit durduruluyor...');
        setTimeout(() => bar.remove(), 800);
      }
    });
    updateToolbar();
  }

  function updateToolbar() {
    const bar = document.getElementById('cortex-rec-toolbar');
    if (!bar) return;
    const c = bar.querySelector('.count');
    if (c) c.textContent = String(state.actionCount);
    const rec = bar.querySelector('.recent');
    if (rec) {
      if (state.recentActions.length === 0) {
        rec.textContent = '';
      } else {
        rec.innerHTML = state.recentActions.map(a => `<div class="recent-item">${escapeHtml(a)}</div>`).join('');
      }
    }
  }

  // ============================================================
  //  PICK MODE — manual element selection with action picker
  // ============================================================

  let __pickActive = false;
  let __pickHover  = null;

  function startPickMode() {
    if (__pickActive) return;
    __pickActive = true;
    document.documentElement.style.cursor = 'crosshair';
    installPickBanner();
    document.addEventListener('mouseover',  pickMouseOver, true);
    document.addEventListener('mouseout',   pickMouseOut,  true);
    document.addEventListener('click',      pickClick,     true);
    document.addEventListener('keydown',    pickKeyDown,   true);
    toast('SEÇİM MODU — bir elemana tıkla (ESC ile iptal)');
  }

  function stopPickMode() {
    __pickActive = false;
    document.documentElement.style.cursor = '';
    document.removeEventListener('mouseover',  pickMouseOver, true);
    document.removeEventListener('mouseout',   pickMouseOut,  true);
    document.removeEventListener('click',      pickClick,     true);
    document.removeEventListener('keydown',    pickKeyDown,   true);
    removePickBanner();
    removePickOutline();
    __pickHover = null;
  }

  function pickMouseOver(e) {
    const el = e.target;
    if (shouldSkip(el)) return;
    if (__pickHover === el) return;
    __pickHover = el;
    drawPickOutline(el);
  }

  function pickMouseOut() { /* outline kept until next over */ }

  function pickClick(e) {
    const el = e.target;
    if (shouldSkip(el)) return;
    // BLOCK the actual click so the site doesn't navigate / submit
    e.preventDefault();
    e.stopImmediatePropagation();
    e.stopPropagation();
    stopPickMode();
    openActionChooser(el);
  }

  function pickKeyDown(e) {
    if (e.key === 'Escape') {
      stopPickMode();
      toast('Iptal');
    }
  }

  function installPickBanner() {
    if (document.getElementById('cortex-pick-banner')) return;
    const b = document.createElement('div');
    b.id = 'cortex-pick-banner';
    b.style.cssText = 'position:fixed!important;top:8px!important;left:50%!important;transform:translateX(-50%)!important;z-index:2147483647!important;background:#fbbf24!important;color:#000!important;padding:8px 16px!important;border-radius:8px!important;font:bold 13px/1.3 system-ui!important;box-shadow:0 4px 16px rgba(0,0,0,.4)!important;pointer-events:none!important;border:2px solid #f59e0b!important;';
    b.textContent = '🎯 ELEMENT SEÇİM MODU — sayfaya tıkla · ESC ile iptal';
    document.documentElement.appendChild(b);
  }
  function removePickBanner() {
    document.getElementById('cortex-pick-banner')?.remove();
  }

  function drawPickOutline(el) {
    removePickOutline();
    const rect = el.getBoundingClientRect();
    const ov = document.createElement('div');
    ov.id = 'cortex-pick-outline';
    ov.style.cssText = `position:fixed!important;top:${rect.top}px!important;left:${rect.left}px!important;width:${rect.width}px!important;height:${rect.height}px!important;border:3px dashed #0fa!important;background:rgba(0,255,170,0.12)!important;z-index:2147483646!important;pointer-events:none!important;border-radius:4px!important;box-shadow:0 0 0 2px rgba(0,0,0,0.4),0 4px 16px rgba(0,255,170,0.4)!important;transition:all 0.05s ease!important;`;
    document.documentElement.appendChild(ov);

    // Tooltip
    const tip = document.createElement('div');
    tip.id = 'cortex-pick-tip';
    const sel = bestSelector(el);
    tip.textContent = sel;
    tip.style.cssText = `position:fixed!important;top:${rect.bottom + 6}px!important;left:${rect.left}px!important;max-width:400px!important;background:#0fa!important;color:#000!important;padding:4px 8px!important;font:11px/1.3 "SF Mono",monospace!important;border-radius:4px!important;z-index:2147483647!important;pointer-events:none!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;`;
    document.documentElement.appendChild(tip);
  }
  function removePickOutline() {
    document.getElementById('cortex-pick-outline')?.remove();
    document.getElementById('cortex-pick-tip')?.remove();
  }

  /** Best-effort short selector preview shown in the tooltip. */
  function bestSelector(el) {
    if (!el || el.nodeType !== 1) return '';
    if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
    if (el.id) return `#${el.id}`;
    if (el.getAttribute('name')) return `${el.tagName.toLowerCase()}[name="${el.getAttribute('name')}"]`;
    const text = (el.innerText || '').trim().slice(0, 30);
    if (text && (el.tagName === 'BUTTON' || el.tagName === 'A')) {
      return `${el.tagName.toLowerCase()} ("${text}")`;
    }
    if (el.placeholder) return `input[placeholder="${el.placeholder}"]`;
    const cls = (el.className || '').toString().split(/\s+/).filter(Boolean).slice(0, 2).join('.');
    return cls ? `${el.tagName.toLowerCase()}.${cls}` : el.tagName.toLowerCase();
  }

  /** Show inline modal: "What do you want to do with this element?" */
  function openActionChooser(el) {
    // Highlight the chosen element with a persistent green outline
    const rect = el.getBoundingClientRect();
    const lock = document.createElement('div');
    lock.id = 'cortex-pick-locked';
    lock.style.cssText = `position:fixed!important;top:${rect.top}px!important;left:${rect.left}px!important;width:${rect.width}px!important;height:${rect.height}px!important;border:3px solid #0fa!important;background:rgba(0,255,170,0.18)!important;z-index:2147483646!important;pointer-events:none!important;border-radius:4px!important;`;
    document.documentElement.appendChild(lock);

    const info = describe(el);
    const elemLabel = info.dataTestId || info.id || info.name || info.text?.slice(0, 30) || `<${info.tag}>`;

    const modal = document.createElement('div');
    modal.id = 'cortex-action-chooser';
    modal.style.cssText = 'position:fixed!important;top:50%!important;left:50%!important;transform:translate(-50%,-50%)!important;z-index:2147483647!important;background:#0a0f1c!important;border:2px solid #0fa!important;border-radius:14px!important;padding:20px!important;box-shadow:0 16px 48px rgba(0,0,0,.6)!important;min-width:360px!important;font:13px/1.4 system-ui!important;color:#fff!important;';
    modal.innerHTML = `
      <div style="font-size:11px!important;color:#0fa!important;font-weight:bold!important;letter-spacing:.05em!important;margin-bottom:4px!important;">YAKALANAN ELEMENT</div>
      <div style="background:rgba(0,255,170,0.1)!important;border-radius:8px!important;padding:10px!important;margin-bottom:14px!important;font-family:monospace!important;font-size:12px!important;word-break:break-all!important;">
        ${escapeHtml('<' + (info.tag || '?') + '>')}
        <strong style="color:#0fa!important;">${escapeHtml(elemLabel)}</strong>
      </div>
      <div style="font-size:11px!important;color:#888!important;text-transform:uppercase!important;letter-spacing:.05em!important;margin-bottom:8px!important;">NE YAPMAK İSTERSİN?</div>
      <div id="cortex-act-grid" style="display:grid!important;grid-template-columns:1fr 1fr!important;gap:8px!important;"></div>
      <button id="cortex-act-cancel" style="margin-top:10px!important;width:100%!important;padding:8px!important;background:transparent!important;color:#888!important;border:1px solid #333!important;border-radius:6px!important;cursor:pointer!important;font:inherit!important;">İptal</button>
    `;
    document.documentElement.appendChild(modal);

    const grid = modal.querySelector('#cortex-act-grid');
    const actions = [
      { type: 'click',          label: '👆 Tıkla',           text: null,    css: '#22d3ee' },
      { type: 'assert_visible', label: '👁 Gör (visible)',   text: null,    css: '#a78bfa' },
      { type: 'fill',           label: '✏️ Bu alana yaz',    text: 'ask',   css: '#fbbf24', requireInput: true },
      { type: 'assert_text',    label: '📝 Metin içerir',    text: 'ask',   css: '#f472b6' },
      { type: 'hover',          label: '🖱 Hover',           text: null,    css: '#34d399' },
      { type: 'scroll',         label: '⬇ Scroll to',        text: null,    css: '#60a5fa' },
    ];
    actions.forEach((a) => {
      const b = document.createElement('button');
      b.style.cssText = `padding:10px!important;background:rgba(255,255,255,0.05)!important;color:#fff!important;border:1px solid ${a.css}55!important;border-radius:8px!important;cursor:pointer!important;font:inherit!important;text-align:left!important;`;
      b.textContent = a.label;
      b.addEventListener('mouseover', () => b.style.background = `${a.css}22`);
      b.addEventListener('mouseout',  () => b.style.background = 'rgba(255,255,255,0.05)');
      b.addEventListener('click', async (e) => {
        e.stopPropagation();
        let payload = { type: a.type, element: info };
        if (a.text === 'ask') {
          const v = window.prompt(
            a.type === 'fill'        ? 'Bu alana ne yazilsin?' :
            a.type === 'assert_text' ? 'Hangi metin kontrol edilsin?' : 'Deger:'
          );
          if (v == null || v === '') { closeChooser(); return; }
          payload.text = v;
          if (a.requireInput && info.isPassword) {
            const alias = window.prompt('Sifre alani! Hangi alias ile saklansin?', 'cortexUser');
            if (alias) payload.passwordAlias = alias.trim();
          }
        }
        try { await send(payload); toast('+ ' + a.label); }
        catch (err) { console.error('send failed', err); toast('Hata: ' + err.message); }
        closeChooser();
      });
      grid.appendChild(b);
    });
    modal.querySelector('#cortex-act-cancel').addEventListener('click', closeChooser);
  }

  function closeChooser() {
    document.getElementById('cortex-action-chooser')?.remove();
    document.getElementById('cortex-pick-locked')?.remove();
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  console.log('[Cortex Recorder] aktif v3, port:', PORT);

  // ============================================================
  //  HEARTBEAT — re-apply UI every 400ms to defeat React hydration
  //  that wipes <body> / <html> attributes / our injected elements
  // ============================================================
  // (__hbCount hoisted to top of IIFE — see TDZ comment up there)
  function recorderHeartbeat() {
    try {
      __hbCount++;

      // 1) Re-apply marker (React hydration may strip unknown <html> attrs)
      const _de = document.documentElement;
      if (_de && _de.getAttribute('data-cortex-recorder') !== 'v3') {
        try { _de.setAttribute('data-cortex-recorder', 'v3'); } catch (_) {}
      }

      // 2) Probe (top green bar)
      if (_de && !document.getElementById('cortex-rec-probe')) {
        try { /* re-trigger probe via the closure */
          const probe = document.createElement('div');
          probe.id = 'cortex-rec-probe';
          probe.style.cssText = 'position:fixed!important;top:0!important;left:0!important;right:0!important;height:4px!important;background:linear-gradient(90deg,#00ff99,#00cc66,#00ff99)!important;background-size:200% 100%!important;z-index:2147483647!important;pointer-events:none!important;box-shadow:0 0 12px rgba(0,255,153,0.7)!important;';
          _safeAppend(_de, probe);
        } catch (_) {}
      }

      // 3) Debug overlay
      if (!document.getElementById('cortex-rec-debug')) {
        try { installDebugOverlay(); } catch (_) {}
      }

      // 4) Toolbar
      if (!document.getElementById('cortex-rec-toolbar')) {
        try { buildToolbar(); } catch (_) {}
      }

      // 5) Title prefix
      if (!document.title.startsWith('[REC] ')) {
        try { document.title = '[REC] ' + document.title.replace(/^\[REC\]\s*/, ''); } catch (_) {}
      }

      // 6) Re-attach window-level listeners (idempotent — addEventListener
      //    with the same handler+capture is deduped by the browser)
      try { attachClickListeners(); } catch (_) {}
      try { attachFormListeners(); } catch (_) {}
      try { attachUrlChangeWatchers(); } catch (_) {}

      // Surface heartbeat in the debug overlay
      try { __dbg.heartbeat = __hbCount; updateDebugOverlay && updateDebugOverlay(); } catch (_) {}
    } catch (e) {
      console.error('[cortex-rec] heartbeat error', e);
    }
  }
  // First beat immediately, then every 400ms
  recorderHeartbeat();
  setInterval(recorderHeartbeat, 400);

  // ============================================================
  //  Extra fail-safe: capture clicks at the very lowest level
  //  via Document.prototype hooks. This catches even sites that
  //  call stopPropagation on capture before our listener runs.
  // ============================================================
  (function installLowLevelClickHook() {
    try {
      const origDispatch = EventTarget.prototype.dispatchEvent;
      if (origDispatch.__cortexHooked) return;
      EventTarget.prototype.dispatchEvent = function (event) {
        try {
          if (event && (event.type === 'click' || event.type === 'mousedown') &&
              event.isTrusted && this && this.tagName) {
            console.log('[cortex-rec] LOWLEVEL', event.type, this.tagName, this);
            if (typeof __dbg !== 'undefined') {
              __dbg.lowlevel = (__dbg.lowlevel || 0) + 1;
            }
          }
        } catch (_) {}
        return origDispatch.apply(this, arguments);
      };
      EventTarget.prototype.dispatchEvent.__cortexHooked = true;
      console.log('[cortex-rec] low-level click hook installed');
    } catch (e) {
      console.warn('[cortex-rec] low-level hook failed', e);
    }
  })();
})();
