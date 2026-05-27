// Cortex Recorder popup — talks to background service worker only.

const els = {
  dot:             document.getElementById('dot'),
  status:          document.getElementById('status'),
  idleSection:     document.getElementById('idle-section'),
  runningSection:  document.getElementById('running-section'),
  passwordSection: document.getElementById('password-section'),
  savedSection:    document.getElementById('saved-section'),
  featureName:     document.getElementById('feature-name'),
  tags:            document.getElementById('tags'),
  startBtn:        document.getElementById('start'),
  undoBtn:         document.getElementById('undo'),
  stopBtn:         document.getElementById('stop'),
  newBtn:          document.getElementById('new-recording'),
  count:           document.getElementById('count'),
  elapsed:         document.getElementById('elapsed'),
  savedFile:       document.getElementById('saved-file'),
  portInfo:        document.getElementById('port-info'),
  // Password alias confirm UI
  pwAlias:         document.getElementById('pw-alias'),
  pwConfirmBtn:    document.getElementById('pw-confirm'),
  pwSkipBtn:       document.getElementById('pw-skip'),
};

function showSection(name) {
  els.idleSection.hidden     = name !== 'idle';
  els.runningSection.hidden  = name !== 'running';
  els.passwordSection.hidden = name !== 'password';
  els.savedSection.hidden    = name !== 'saved';
}

function setStatus(text, color) {
  els.status.textContent = text;
  els.status.style.color = color || '';
}

function send(type, extra) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage(Object.assign({ type }, extra || {}), (resp) => {
        if (chrome.runtime.lastError) {
          resolve({ ok: false, error: chrome.runtime.lastError.message });
        } else {
          resolve(resp);
        }
      });
    } catch (e) {
      resolve({ ok: false, error: String(e) });
    }
  });
}

let elapsedTimer = null;
let startedAt = 0;

function fmtElapsed(ms) {
  const s = Math.floor(ms / 1000);
  const mm = String(Math.floor(s / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  return mm + ':' + ss;
}

function startElapsed() {
  stopElapsed();
  elapsedTimer = setInterval(() => {
    els.elapsed.textContent = fmtElapsed(Date.now() - startedAt);
  }, 1000);
}
function stopElapsed() {
  if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
}

async function refresh() {
  const state = await send('getState');
  if (!state || !('recording' in state)) {
    setStatus('arka plan yanit vermiyor', '#f59e0b');
    els.dot.className = 'dot error';
    return;
  }
  els.portInfo.textContent = state.port ? ('port :' + state.port) : 'port aranıyor';

  if (state.recording && state.pendingPassword) {
    // Password field detected — show alias confirmation UI.
    showSection('password');
    els.dot.className = 'dot recording';
    setStatus('sifre alani yakalandı · alias girin', '#d946ef');
    // Pre-fill alias with background suggestion but only if field is empty or matches prev suggestion.
    if (!els.pwAlias.value || els.pwAlias.dataset.lastSuggestion === els.pwAlias.value) {
      els.pwAlias.value = state.pendingPassword.alias || '';
      els.pwAlias.dataset.lastSuggestion = els.pwAlias.value;
    }
    // Focus alias input automatically.
    setTimeout(() => els.pwAlias.focus(), 80);
  } else if (state.recording) {
    showSection('running');
    els.dot.className = 'dot recording';
    setStatus('port :' + state.port + ' · canli', '#94a3b8');
    els.count.textContent = String(state.actionCount || 0);
    startedAt = state.startedAt || Date.now();
    startElapsed();
  } else if (state.savedFile) {
    showSection('saved');
    els.dot.className = 'dot saved';
    setStatus('kayit tamamlandi', '#34d399');
    els.savedFile.textContent = state.savedFile;
    stopElapsed();
  } else {
    showSection('idle');
    els.dot.className = 'dot';
    setStatus(state.port ? ('hazir · port :' + state.port) : 'java server aranıyor', '#94a3b8');
    stopElapsed();
  }
}

els.startBtn.addEventListener('click', async () => {
  els.startBtn.disabled = true;
  els.startBtn.textContent = 'başlatılıyor...';
  const opts = {
    featureName: els.featureName.value.trim() || undefined,
    tags: els.tags.value.trim().split(/\s+/).filter(Boolean),
  };
  const r = await send('start', { options: opts });
  if (r && r.ok) {
    await refresh();
  } else {
    setStatus((r && r.error) || 'başlatma başarısız', '#ef4444');
    els.dot.className = 'dot error';
    els.startBtn.disabled = false;
    els.startBtn.textContent = '▶ Kaydı Başlat';
  }
});

els.undoBtn.addEventListener('click', async () => {
  els.undoBtn.disabled = true;
  const r = await send('undo');
  if (r && typeof r.count === 'number') els.count.textContent = String(r.count);
  els.undoBtn.disabled = false;
});

els.stopBtn.addEventListener('click', async () => {
  els.stopBtn.disabled = true;
  els.stopBtn.textContent = 'kaydediliyor...';
  stopElapsed();
  const r = await send('stop');
  if (r && r.ok) {
    await refresh();
  } else {
    setStatus((r && r.error) || 'durdurma başarısız', '#ef4444');
    els.dot.className = 'dot error';
    els.stopBtn.disabled = false;
    els.stopBtn.textContent = '⏹ Durdur ve Kaydet';
  }
});

els.newBtn.addEventListener('click', async () => {
  await send('reset');
  els.featureName.value = '';
  els.tags.value = '';
  await refresh();
});

// ── Password alias confirm / skip ────────────────────────────────────────────

els.pwConfirmBtn.addEventListener('click', async () => {
  const alias = els.pwAlias.value.trim();
  if (!alias) {
    els.pwAlias.focus();
    els.pwAlias.style.borderColor = '#ef4444';
    setTimeout(() => { els.pwAlias.style.borderColor = ''; }, 1500);
    return;
  }
  els.pwConfirmBtn.disabled = true;
  els.pwConfirmBtn.textContent = 'kaydediliyor…';
  const r = await send('confirmPassword', { alias });
  els.pwAlias.value = '';
  els.pwAlias.dataset.lastSuggestion = '';
  els.pwConfirmBtn.disabled = false;
  els.pwConfirmBtn.textContent = '✓ Kaydet';
  if (r && typeof r.count === 'number') els.count.textContent = String(r.count);
  await refresh();
});

els.pwSkipBtn.addEventListener('click', async () => {
  els.pwSkipBtn.disabled = true;
  await send('skipPassword');
  els.pwAlias.value = '';
  els.pwAlias.dataset.lastSuggestion = '';
  els.pwSkipBtn.disabled = false;
  await refresh();
});

// Allow Enter key to confirm alias input.
els.pwAlias.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') els.pwConfirmBtn.click();
  if (e.key === 'Escape') els.pwSkipBtn.click();
});

refresh();
setInterval(refresh, 1200);
