/**
 * PM2 Ecosystem Config — NeurexQA
 *
 * Kullanım:
 *   pm2 start ecosystem.config.js      # tüm servisleri başlat
 *   pm2 restart ecosystem.config.js    # yeniden başlat
 *   pm2 stop ecosystem.config.js       # durdur
 *   pm2 delete ecosystem.config.js     # PM2'den kaldır
 *   pm2 startup && pm2 save            # Mac açılışına ekle
 *   pm2 monit                          # canlı dashboard
 */

const path = require("path");
const ROOT = __dirname;

module.exports = {
  apps: [
    // ── Backend (FastAPI / uvicorn) ──────────────────────────────────────────
    {
      name: "neurex-backend",
      script: path.join(ROOT, ".venv/bin/python"),
      args: "-m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      cwd: path.join(ROOT, "backend"),
      interpreter: "none",          // script zaten python binary

      // Yeniden başlatma politikası
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,          // 3 sn bekle, crash loop önle
      min_uptime: "10s",            // 10 sn'den kısa yaşarsa hata say

      // Log
      out_file: "/tmp/neurex-backend.log",
      error_file: "/tmp/neurex-backend-error.log",
      merge_logs: true,
      time: true,

      // Ortam — .env dosyasından okunur; burası sadece zorunlu overrides
      env_file: path.join(ROOT, ".env"),   // .env değerlerini PM2'ye yükle
      env: {
        NODE_ENV: "development",
        APP_ENV: "development",
        PYTHONPATH: path.join(ROOT, "backend"),
      },

      // Watch (dev'de False, değişiklik izleme gerekirse true yap)
      watch: false,
    },

    // ── Engine (Flask) ───────────────────────────────────────────────────────
    {
      name: "neurex-engine",
      script: "app.py",
      cwd: path.join(ROOT, "engine"),
      interpreter: path.join(ROOT, ".venv/bin/python"),

      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      min_uptime: "10s",

      out_file: "/tmp/neurex-engine.log",
      error_file: "/tmp/neurex-engine-error.log",
      merge_logs: true,
      time: true,

      env_file: path.join(ROOT, ".env"),  // ENGINE_INTERNAL_KEY ve diğer ortak değerleri yükle
      env: {
        NODE_ENV: "development",
        APP_ENV: "development",
        PYTHONPATH: path.join(ROOT, "engine"),
        ENGINE_PORT: "5001",
        FLASK_ENV: "development",
        PYTHONUNBUFFERED: "1",
      },

      watch: false,
    },

    // ── AI Gateway (FastAPI — port 8080) ────────────────────────────────────
    {
      name: "neurex-gateway",
      script: path.join(ROOT, ".venv/bin/python"),
      args: "-m uvicorn main:app --host 127.0.0.1 --port 8080",
      cwd: path.join(ROOT, "ai-gateway"),
      interpreter: "none",

      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      min_uptime: "10s",

      out_file: "/tmp/neurex-gateway.log",
      error_file: "/tmp/neurex-gateway-error.log",
      merge_logs: true,
      time: true,

      env: {
        NODE_ENV: "development",
        APP_ENV: "development",
        PYTHONPATH: path.join(ROOT, "ai-gateway"),
        // Gateway kendi klasöründe .env arar — değerleri doğrudan geçiyoruz
        INTERNAL_KEY: "278b969f4ea53eb0fcd415bcee1a57603cecd111f3ad3783064bd51576fb9d50",
        OLLAMA_BASE_URL: "http://localhost:11434/v1",
        OLLAMA_API_KEY: "ollama",
        OLLAMA_MODEL_ANALYST: "qwen2.5:14b",
        OLLAMA_MODEL_FAST: "llama3.1:8b",
        OLLAMA_MODEL_CODER: "qwen2.5-coder:7b",
        AI_PROVIDER: "ollama",
        AI_LOCAL_ONLY: "true",
        OLLAMA_ENABLED: "true",
        REDIS_URL: "redis://localhost:6379/1",
      },

      watch: false,
    },

    // NOT: neurex-watchdog PM2 tarafından DEĞİL LaunchAgent tarafından yönetilir.
    // ~/Library/LaunchAgents/com.neurexqa.watchdog.plist kurulumu: neurex install
    // PM2 zaten backend + engine'i restart ediyor; watchdog sadece
    // Playwright zombie temizliği ve macOS bildirimi için çalışır.
  ],
};
