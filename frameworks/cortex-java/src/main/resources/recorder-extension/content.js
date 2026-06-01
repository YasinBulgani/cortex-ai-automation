// Cortex Recorder — content script.
// Runs in extension's isolated world on every page. Captures user events
// when background says recording is active. Sends actions to background
// via chrome.runtime.sendMessage. Background relays to Java HTTP server.
(function () {
  let recording = false;

  // Pull initial state from background.
  try {
    chrome.runtime.sendMessage({ type: 'getState' }, (resp) => {
      if (chrome.runtime.lastError) return;
      if (resp && resp.recording) {
        recording = true;
        console.log('[cortex-rec] resumed: recording is active');
        send({ type: 'navigate' });
      }
    });
  } catch (_) { /* extension reload */ }

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg && msg.type === 'recordingChanged') {
      recording = !!msg.active;
      console.log('[cortex-rec] recording state ->', recording);
      if (recording) send({ type: 'navigate' });
    }
  });

  function send(action) {
    if (!recording) return;
    action.timestamp = action.timestamp || Date.now();
    action.url = location.href;
    try {
      chrome.runtime.sendMessage({ type: 'action', action });
    } catch (e) {
      console.error('[cortex-rec] send failed', e);
    }
  }

  // ── Element describe ───────────────────────────────────────────────
  function describe(el) {
    if (!el || el.nodeType !== 1) return null;
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
      isPassword: (el.tagName === 'INPUT' && el.type === 'password'),
    };
  }

  function cssPathFor(el) {
    if (!(el instanceof Element)) return '';
    const path = [];
    let cur = el;
    while (cur && cur.nodeType === 1 && path.length < 5) {
      let part = cur.nodeName.toLowerCase();
      if (cur.id) { part += '#' + CSS.escape(cur.id); path.unshift(part); break; }
      const cls = (cur.className || '').toString().trim().split(/\s+/).filter(Boolean).slice(0, 2);
      if (cls.length) part += '.' + cls.map(c => CSS.escape(c)).join('.');
      const parent = cur.parentNode;
      if (parent && parent.children) {
        const same = Array.from(parent.children).filter(c => c.nodeName === cur.nodeName);
        if (same.length > 1) part += ':nth-of-type(' + (same.indexOf(cur) + 1) + ')';
      }
      path.unshift(part);
      cur = cur.parentElement;
    }
    return path.join(' > ');
  }

  function xpathFor(el) {
    if (!(el instanceof Element)) return '';
    if (el.id) return "//*[@id='" + el.id + "']";
    const parts = [];
    let cur = el;
    while (cur && cur.nodeType === 1 && parts.length < 6) {
      let idx = 1;
      let sib = cur.previousElementSibling;
      while (sib) { if (sib.nodeName === cur.nodeName) idx++; sib = sib.previousElementSibling; }
      parts.unshift(cur.nodeName.toLowerCase() + '[' + idx + ']');
      cur = cur.parentElement;
    }
    return '/' + parts.join('/');
  }

  // Skip events on extension UI itself (just in case the popup is open inside the page somehow).
  function shouldSkip(t) {
    if (!t || !t.closest) return false;
    return !!t.closest('[data-cortex-ext-toolbar]');
  }

  // ── Click capture (multi-event, capture phase) ─────────────────────
  let lastClick = { target: null, t: 0 };
  function clickHandler(e) {
    if (!recording) return;
    if (shouldSkip(e.target)) return;
    const now = Date.now();
    if (lastClick.target === e.target && (now - lastClick.t) < 80) return; // dedup
    lastClick.target = e.target; lastClick.t = now;
    send({ type: 'click', element: describe(e.target) });
  }
  ['click', 'mousedown', 'pointerdown'].forEach((ev) => {
    document.addEventListener(ev, clickHandler, { capture: true, passive: true });
  });

  // ── Input / change / submit ────────────────────────────────────────
  const inputTimers = new WeakMap();
  document.addEventListener('input', (e) => {
    if (!recording) return;
    const el = e.target;
    if (shouldSkip(el)) return;
    if (!('value' in el)) return;
    clearTimeout(inputTimers.get(el));
    const h = setTimeout(() => {
      if (el.type === 'password') {
        // Password fields: NEVER send the actual value.
        // Send a passwordCapture request so the popup can ask the user for an alias name.
        const suggestedAlias = el.name || el.id || el.getAttribute('autocomplete') || 'recordedPassword';
        try {
          chrome.runtime.sendMessage({
            type: 'passwordCapture',
            alias: suggestedAlias,
            element: describe(el),
            // actual value intentionally omitted
          });
        } catch (e2) {
          console.error('[cortex-rec] passwordCapture send failed', e2);
        }
      } else {
        send({ type: 'fill', element: describe(el), text: el.value });
      }
    }, 500); // debounce
    inputTimers.set(el, h);
  }, { capture: true, passive: true });

  document.addEventListener('change', (e) => {
    if (!recording) return;
    const el = e.target;
    if (shouldSkip(el)) return;
    if (el.tagName === 'SELECT') {
      send({ type: 'change', element: describe(el), text: el.value });
    } else if (el.type === 'checkbox' || el.type === 'radio') {
      send({ type: 'click', element: describe(el) });
    }
  }, { capture: true, passive: true });

  document.addEventListener('submit', (e) => {
    if (!recording) return;
    if (shouldSkip(e.target)) return;
    const active = document.activeElement;
    if (active && active.value !== undefined) {
      send({ type: 'press', key: 'Enter', element: describe(active) });
    } else {
      send({ type: 'comment', text: 'form submitted' });
    }
  }, { capture: true, passive: true });

  document.addEventListener('keydown', (e) => {
    if (!recording) return;
    if (shouldSkip(e.target)) return;
    if (e.key === 'Enter' || e.key === 'Escape' || e.key === 'Tab') {
      send({ type: 'press', key: e.key, element: describe(e.target) });
    }
  }, { capture: true });

  // ── URL change detection (poll — we can't hook history from isolated world) ──
  let lastUrl = location.href;
  function fireNavigate() {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      if (recording) send({ type: 'navigate' });
    }
  }
  setInterval(fireNavigate, 500);
  window.addEventListener('popstate', fireNavigate);
  window.addEventListener('hashchange', fireNavigate);

  console.log('[cortex-rec] content script ready on', location.href);
})();
