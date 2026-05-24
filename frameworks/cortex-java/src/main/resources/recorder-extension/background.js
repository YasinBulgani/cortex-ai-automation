// Cortex Recorder — background service worker (MV3).
// Holds state + relays HTTP traffic to the local Java server.

const PORT_CANDIDATES = [7700, 7701, 7702, 7703, 7704, 7705];

const state = {
  recording: false,
  port: null,
  featureName: null,
  tags: [],
  startedAt: 0,
  actionCount: 0,
  lastError: null,
  savedFile: null,
  // Pending password capture waiting for popup confirmation.
  // IMPORTANT: actual password value is NEVER stored here — only alias suggestion.
  pendingPassword: null, // null | { alias: string, element: object, capturedAt: number }
};

async function tryFetch(port, path, opts) {
  try {
    const r = await fetch(`http://127.0.0.1:${port}${path}`, opts);
    if (!r.ok) return null;
    return await r.json();
  } catch (_) { return null; }
}

async function resolvePort() {
  if (state.port) {
    const data = await tryFetch(state.port, '/status');
    if (data) return state.port;
  }
  for (const p of PORT_CANDIDATES) {
    const data = await tryFetch(p, '/status');
    if (data) {
      state.port = p;
      return p;
    }
  }
  state.port = null;
  return null;
}

async function pollStatus() {
  if (!state.recording) return;
  const port = await resolvePort();
  if (!port) {
    state.lastError = 'Java server not reachable';
    return;
  }
  const data = await tryFetch(port, '/status');
  if (data && typeof data.actions === 'number') {
    state.actionCount = data.actions;
  }
}

setInterval(pollStatus, 1500);

async function notifyContentScripts(active) {
  try {
    const tabs = await chrome.tabs.query({});
    for (const t of tabs) {
      if (!t.id) continue;
      try { await chrome.tabs.sendMessage(t.id, { type: 'recordingChanged', active }); }
      catch (_) { /* tab without content script */ }
    }
  } catch (e) {
    console.warn('[cortex-rec-bg] notify failed', e);
  }
}

async function startRecording({ featureName, tags } = {}) {
  const port = await resolvePort();
  if (!port) {
    return { ok: false, error: 'Java server bulunamadi (port 7700-7705). Once: ./mvnw -Precorder-server compile exec:java' };
  }
  state.recording = true;
  state.featureName = featureName || null;
  state.tags = tags || [];
  state.startedAt = Date.now();
  state.actionCount = 0;
  state.savedFile = null;
  state.lastError = null;
  await notifyContentScripts(true);
  return { ok: true, port };
}

async function stopRecording() {
  const port = await resolvePort();
  if (!port) return { ok: false, error: 'Java server bulunamadi' };
  state.recording = false;
  await notifyContentScripts(false);
  const data = await tryFetch(port, '/stop', { method: 'POST' });
  if (!data) {
    state.lastError = '/stop call failed';
    return { ok: false, error: state.lastError };
  }
  state.savedFile = data.featureFile || data.file || data.path || `port ${port}: kayit kaydedildi`;
  return { ok: true, ...data };
}

function resetState() {
  state.recording = false;
  state.featureName = null;
  state.tags = [];
  state.startedAt = 0;
  state.actionCount = 0;
  state.lastError = null;
  state.savedFile = null;
  state.pendingPassword = null;
}

// Open the popup so the user sees the password confirmation UI.
async function openPopup() {
  try {
    await chrome.action.openPopup();
  } catch (_) {
    // openPopup is not available in all contexts (e.g. non-user-gesture).
    // Badge the icon instead to draw attention.
    chrome.action.setBadgeText({ text: '🔑' });
    chrome.action.setBadgeBackgroundColor({ color: '#d946ef' });
  }
}

function clearPasswordBadge() {
  chrome.action.setBadgeText({ text: '' });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    try {
      if (!msg || !msg.type) { sendResponse({ ok: false }); return; }

      switch (msg.type) {
        case 'getState': {
          // Refresh port detection opportunistically.
          if (!state.port) await resolvePort();
          sendResponse({ ...state });
          return;
        }
        case 'start': {
          const r = await startRecording(msg.options || {});
          sendResponse(r);
          return;
        }
        case 'stop': {
          const r = await stopRecording();
          sendResponse(r);
          return;
        }
        case 'reset': {
          resetState();
          sendResponse({ ok: true });
          return;
        }
        case 'action': {
          const port = await resolvePort();
          if (!port) { sendResponse({ ok: false }); return; }
          const r = await tryFetch(port, '/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(msg.action),
          });
          if (r && typeof r.count === 'number') state.actionCount = r.count;
          sendResponse({ ok: !!r, count: state.actionCount });
          return;
        }
        case 'undo': {
          const port = await resolvePort();
          if (!port) { sendResponse({ ok: false }); return; }
          const r = await tryFetch(port, '/undo', { method: 'POST' });
          if (r && typeof r.count === 'number') state.actionCount = r.count;
          sendResponse({ ok: !!r, count: state.actionCount });
          return;
        }
        // ── Password mask flow ───────────────────────────────────────────
        case 'passwordCapture': {
          // Content script detected a password field fill; store alias suggestion.
          // Actual password value is NEVER relayed — only the alias name flows through.
          if (!state.recording) { sendResponse({ ok: false }); return; }
          state.pendingPassword = {
            alias: msg.alias || 'recordedPassword',
            element: msg.element || {},
            capturedAt: Date.now(),
          };
          await openPopup();
          sendResponse({ ok: true });
          return;
        }
        case 'confirmPassword': {
          // Popup user confirmed alias name → send masked fill action to Java server.
          if (!state.pendingPassword) { sendResponse({ ok: false, error: 'no pending capture' }); return; }
          const confirmedAlias = (msg.alias || state.pendingPassword.alias).trim();
          const port = await resolvePort();
          if (!port) { sendResponse({ ok: false, error: 'Java server bulunamadi' }); return; }
          const r = await tryFetch(port, '/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              type: 'fill',
              element: state.pendingPassword.element,
              text: null,                 // actual value intentionally null
              passwordAlias: confirmedAlias,
              masked: true,
              timestamp: state.pendingPassword.capturedAt,
              url: state.pendingPassword.element.url || '',
            }),
          });
          if (r && typeof r.count === 'number') state.actionCount = r.count;
          state.pendingPassword = null;
          clearPasswordBadge();
          sendResponse({ ok: !!r, count: state.actionCount });
          return;
        }
        case 'skipPassword': {
          // User chose to skip recording this password field entirely.
          state.pendingPassword = null;
          clearPasswordBadge();
          sendResponse({ ok: true });
          return;
        }
        default:
          sendResponse({ ok: false, error: 'unknown msg type: ' + msg.type });
      }
    } catch (e) {
      console.error('[cortex-rec-bg] handler error', e);
      sendResponse({ ok: false, error: String(e) });
    }
  })();
  return true; // async response
});

console.log('[cortex-rec-bg] service worker booted');
