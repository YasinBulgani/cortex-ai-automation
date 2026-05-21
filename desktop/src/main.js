/**
 * TestwrightAI Desktop — Electron Main Process
 *
 * Sorumluluklar:
 *   1. Splash penceresini aç, kullanıcıya servis başlatma ilerlemesini göster
 *   2. docker compose up ile tüm backend servislerini ayağa kaldır
 *   3. Frontend (Next.js) health-check — hazır olunca ana pencereyi aç
 *   4. Uygulama kapanırken docker compose down çalıştır (temiz çıkış)
 */

const { app, BrowserWindow, Menu, shell, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');

const isDev = process.env.NODE_ENV === 'development';
const FRONTEND_URL = process.env.TWAI_FRONTEND_URL || 'http://localhost:3000';
const BACKEND_HEALTH = 'http://localhost:8000/health';
const ENGINE_HEALTH = 'http://localhost:5001/health';

function log(...args) {
  const ts = new Date().toISOString().slice(11, 23);
  console.log(`[twai ${ts}]`, ...args);
}

const START_TIMEOUT_MS = 5 * 60 * 1000;
const POLL_INTERVAL_MS = 2000;

let splashWindow = null;
let mainWindow = null;
let composeStopped = false;
let composeStarted = false;
let composeCmd = null;

function resolveProjectRoot() {
  // Dev modda: ../ (repo kökü). Prod modda: electron-builder extraResources ile
  // docker-compose.yml resources/compose/ altına kopyalanır.
  if (isDev) {
    return path.resolve(__dirname, '..', '..');
  }
  return path.join(process.resourcesPath, 'compose');
}

function resolveComposeFile() {
  return path.join(resolveProjectRoot(), 'docker-compose.yml');
}

function sendStatus(channel, payload) {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.webContents.send(channel, payload);
  }
}

function pingHttp(url, timeoutMs = 1500) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      res.resume();
      resolve(res.statusCode && res.statusCode < 500);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitUntilReady(url, label) {
  const deadline = Date.now() + START_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const ok = await pingHttp(url);
    if (ok) {
      sendStatus('service:ready', { name: label });
      return true;
    }
    sendStatus('service:waiting', { name: label });
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
  return false;
}

function tryRun(cmd, args) {
  return new Promise((resolve) => {
    const proc = spawn(cmd, args, { stdio: 'ignore' });
    proc.on('close', (code) => resolve(code === 0));
    proc.on('error', () => resolve(false));
  });
}

async function detectComposeCmd() {
  if (composeCmd) return composeCmd;
  if (await tryRun('docker', ['compose', 'version'])) {
    composeCmd = { bin: 'docker', prefix: ['compose'] };
  } else if (await tryRun('docker-compose', ['version'])) {
    composeCmd = { bin: 'docker-compose', prefix: [] };
  } else {
    composeCmd = null;
  }
  return composeCmd;
}

function runDockerCompose(args, { stream = false } = {}) {
  return new Promise(async (resolve, reject) => {
    const composeFile = resolveComposeFile();
    if (!fs.existsSync(composeFile)) {
      return reject(new Error(`docker-compose.yml bulunamadı: ${composeFile}`));
    }

    const cmd = await detectComposeCmd();
    if (!cmd) {
      return reject(new Error('Docker Compose bulunamadı (ne `docker compose` ne de `docker-compose`).'));
    }

    const fullArgs = [...cmd.prefix, '-f', composeFile, ...args];
    const proc = spawn(cmd.bin, fullArgs, {
      cwd: resolveProjectRoot(),
      env: { ...process.env },
    });

    let stderr = '';
    proc.stdout.on('data', (chunk) => {
      if (stream) sendStatus('compose:log', { line: chunk.toString() });
    });
    proc.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
      if (stream) sendStatus('compose:log', { line: chunk.toString() });
    });

    proc.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${cmd.bin} ${fullArgs.join(' ')} exit=${code}\n${stderr}`));
    });

    proc.on('error', reject);
  });
}

async function checkDockerAvailable() {
  const cliOk = await tryRun('docker', ['--version']);
  if (!cliOk) return { ok: false, reason: 'CLI yok' };
  const daemonOk = await tryRun('docker', ['info']);
  if (!daemonOk) return { ok: false, reason: 'daemon kapalı' };
  const compose = await detectComposeCmd();
  if (!compose) return { ok: false, reason: 'compose yok' };
  return { ok: true };
}

function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 560,
    height: 420,
    resizable: false,
    frame: false,
    transparent: false,
    backgroundColor: '#0b1020',
    center: true,
    alwaysOnTop: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  splashWindow.loadFile(path.join(__dirname, 'splash.html'));
  splashWindow.on('closed', () => {
    splashWindow = null;
  });
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    backgroundColor: '#0b1020',
    title: 'TestwrightAI',
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  log('mainWindow.loadURL →', FRONTEND_URL);
  mainWindow.loadURL(FRONTEND_URL);

  mainWindow.webContents.on('did-fail-load', (_e, code, desc, url) => {
    log('mainWindow did-fail-load:', code, desc, url);
  });
  mainWindow.webContents.on('did-finish-load', () => {
    log('mainWindow did-finish-load');
  });

  mainWindow.once('ready-to-show', () => {
    log('mainWindow ready-to-show → showing');
    mainWindow.show();
    if (splashWindow && !splashWindow.isDestroyed()) splashWindow.close();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function buildMenu() {
  const template = [
    {
      label: 'TestwrightAI',
      submenu: [
        { role: 'about', label: 'Hakkında' },
        { type: 'separator' },
        {
          label: 'Servis Durumunu Aç (API Docs)',
          click: () => shell.openExternal('http://localhost:8000/docs'),
        },
        {
          label: 'Engine Health',
          click: () => shell.openExternal('http://localhost:5001/health'),
        },
        { type: 'separator' },
        { role: 'services', label: 'Hizmetler' },
        { type: 'separator' },
        { role: 'hide', label: 'Gizle' },
        { role: 'hideOthers', label: 'Diğerlerini Gizle' },
        { role: 'unhide', label: 'Hepsini Göster' },
        { type: 'separator' },
        { role: 'quit', label: 'TestwrightAI\'dan Çık' },
      ],
    },
    {
      label: 'Düzen',
      submenu: [
        { role: 'undo', label: 'Geri Al' },
        { role: 'redo', label: 'Yinele' },
        { type: 'separator' },
        { role: 'cut', label: 'Kes' },
        { role: 'copy', label: 'Kopyala' },
        { role: 'paste', label: 'Yapıştır' },
        { role: 'selectAll', label: 'Tümünü Seç' },
      ],
    },
    {
      label: 'Görünüm',
      submenu: [
        { role: 'reload', label: 'Yeniden Yükle' },
        { role: 'forceReload', label: 'Zorla Yeniden Yükle' },
        { role: 'toggleDevTools', label: 'Geliştirici Araçları' },
        { type: 'separator' },
        { role: 'resetZoom', label: 'Yakınlaştırmayı Sıfırla' },
        { role: 'zoomIn', label: 'Yakınlaştır' },
        { role: 'zoomOut', label: 'Uzaklaştır' },
        { type: 'separator' },
        { role: 'togglefullscreen', label: 'Tam Ekran' },
      ],
    },
    {
      label: 'Pencere',
      submenu: [
        { role: 'minimize', label: 'Küçült' },
        { role: 'zoom', label: 'Büyüt' },
        { role: 'close', label: 'Kapat' },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

async function startup() {
  createSplashWindow();
  buildMenu();

  splashWindow.webContents.once('did-finish-load', async () => {
    log('splash did-finish-load');
    try {
      log('phase: docker-check');
      sendStatus('phase', { step: 'docker-check', label: 'Docker kontrol ediliyor' });
      const dockerCheck = await checkDockerAvailable();
      log('docker-check result:', dockerCheck);
      if (!dockerCheck.ok) {
        const hint = {
          'CLI yok': 'Docker CLI bulunamadı. Docker Desktop yükleyin.',
          'daemon kapalı': 'Docker daemon çalışmıyor. Docker Desktop uygulamasını açın.',
          'compose yok': '`docker compose` plugin\'i yok. Docker Desktop güncelleyin.',
        }[dockerCheck.reason] || 'Docker kontrolü başarısız';
        sendStatus('error', {
          title: 'Docker hazır değil',
          detail: `${hint}\n\nhttps://www.docker.com/products/docker-desktop`,
        });
        return;
      }

      log('phase: compose-up');
      sendStatus('phase', { step: 'compose-up', label: 'Servisler başlatılıyor (docker compose up)' });
      await runDockerCompose(['up', '-d'], { stream: true });
      composeStarted = true;
      log('compose-up: done');

      log('phase: wait-backend');
      sendStatus('phase', { step: 'wait-backend', label: 'Backend sağlık kontrolü (:8000)' });
      const backendReady = await waitUntilReady(BACKEND_HEALTH, 'backend');
      log('backend ready:', backendReady);
      if (!backendReady) throw new Error('Backend zamanında ayağa kalkmadı');

      log('phase: wait-engine');
      sendStatus('phase', { step: 'wait-engine', label: 'Engine sağlık kontrolü (:5001)' });
      const engineReady = await waitUntilReady(ENGINE_HEALTH, 'engine');
      log('engine ready:', engineReady);
      if (!engineReady) throw new Error('Engine zamanında ayağa kalkmadı');

      log('phase: wait-frontend');
      sendStatus('phase', { step: 'wait-frontend', label: 'Frontend yükleniyor (:3000)' });
      const frontendReady = await waitUntilReady(FRONTEND_URL, 'frontend');
      log('frontend ready:', frontendReady);
      if (!frontendReady) throw new Error('Frontend zamanında ayağa kalkmadı');

      log('phase: done — creating main window');
      sendStatus('phase', { step: 'done', label: 'Hazır — arayüz açılıyor' });
      createMainWindow();
      log('createMainWindow() returned');
    } catch (err) {
      log('STARTUP ERROR:', err.message || String(err));
      sendStatus('error', {
        title: 'Başlatma hatası',
        detail: err.message || String(err),
      });
    }
  });
}

async function shutdown() {
  if (composeStopped) return;
  composeStopped = true;
  if (!composeStarted) return;
  try {
    await runDockerCompose(['down']);
  } catch (err) {
    console.error('compose down failed:', err);
  }
}

ipcMain.handle('app:quit', () => {
  app.quit();
});

ipcMain.handle('app:retry', async () => {
  await shutdown();
  composeStopped = false;
  app.relaunch();
  app.exit(0);
});

ipcMain.handle('app:open-docker', () => {
  shell.openExternal('https://www.docker.com/products/docker-desktop');
});

app.whenReady().then(startup);

app.on('window-all-closed', async () => {
  await shutdown();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', async (event) => {
  if (!composeStopped) {
    event.preventDefault();
    await shutdown();
    app.exit(0);
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) startup();
});
