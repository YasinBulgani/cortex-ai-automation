const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('twai', {
  onPhase: (cb) => ipcRenderer.on('phase', (_e, data) => cb(data)),
  onServiceWaiting: (cb) => ipcRenderer.on('service:waiting', (_e, data) => cb(data)),
  onServiceReady: (cb) => ipcRenderer.on('service:ready', (_e, data) => cb(data)),
  onComposeLog: (cb) => ipcRenderer.on('compose:log', (_e, data) => cb(data)),
  onError: (cb) => ipcRenderer.on('error', (_e, data) => cb(data)),
  quit: () => ipcRenderer.invoke('app:quit'),
  retry: () => ipcRenderer.invoke('app:retry'),
  openDocker: () => ipcRenderer.invoke('app:open-docker'),
});
