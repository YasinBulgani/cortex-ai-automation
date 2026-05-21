# Agent 3: Config Hardening & Secrets Management

## Cursor'a yapistir:

```
Sen bir DevSecOps muhendisisin. BGTS bankacilik test otomasyon platformunun
konfigurasyonunu production-grade guvenlik seviyesine cikaracaksin.

## KURALLAR
- Python 3.9 uyumlu
- Mevcut development akisini BOZMA — local'de calismaya devam etmeli
- Production'da guvenlik kontrollerini ZORUNLU kil

## DOSYA 1: backend/app/config.py (mevcut ~120 satir)

### Mevcut Durum
- Satir 12: `_INSECURE_JWT_DEFAULT = "change-me-in-production-use-long-random-secret"`
- Satir 25-27: Hardcoded DB credentials: `postgresql+psycopg2://bgts_user:bgts_pass@127.0.0.1:5432/syndata_db`
- Satir 31: `jwt_secret: str = _INSECURE_JWT_DEFAULT`
- Satir 48-52: `openai_api_key: str = ""` ve `anthropic_api_key: str = ""`
- Satir 55: `ai_provider: str = "openai"`
- Satir 80-117: JWT validator ZATEN mevcut ve iyi yazilmis (debug modda uyari, production'da hata veriyor)

### Yapilacak Degisiklikler

1. **Yeni alan ekle** (Settings class'ina):
```python
    # ── Ortam ─────────────────────────────────────────────────────────
    environment: str = "development"  # development | staging | production
```

2. **AI provider-key uyum validator'u ekle** (mevcut _validate_jwt_secret'ten sonra):
```python
    @model_validator(mode="after")
    def _validate_ai_keys(self) -> "Settings":
        """AI provider secildiyse ilgili API key zorunlu."""
        if self.environment == "production":
            if self.ai_provider == "openai" and not self.openai_api_key:
                _logger.warning(
                    "UYARI: AI provider 'openai' secili ama OPENAI_API_KEY bos. "
                    "AI ozellikleri calismayacak."
                )
            elif self.ai_provider == "anthropic" and not self.anthropic_api_key:
                _logger.warning(
                    "UYARI: AI provider 'anthropic' secili ama ANTHROPIC_API_KEY bos. "
                    "AI ozellikleri calismayacak."
                )
        return self
```

3. **Database URL validator ekle** (production icin):
```python
    @model_validator(mode="after")
    def _validate_database_url(self) -> "Settings":
        """Production'da default DB credentials kullanilmasin."""
        if self.environment == "production":
            if "bgts_pass" in self.database_url or "bgts_user" in self.database_url:
                raise ValueError(
                    "KRITIK: Production'da varsayilan veritabani kimlik bilgileri kullanilamaz. "
                    "DATABASE_URL ortam degiskenini guncelleyin."
                )
        return self
```

## DOSYA 2: backend/.env.example (YENI DOSYA)

Olustur:
```env
# ═══════════════════════════════════════════════════════════════════════
# BGTS Nexus QA Platform — Ortam Degiskenleri
# ═══════════════════════════════════════════════════════════════════════
# Bu dosyayi .env olarak kopyalayin ve degerleri doldurun:
#   cp .env.example .env
#
# ONEMLI: .env dosyasi ASLA git'e commit edilmemelidir!
# ═══════════════════════════════════════════════════════════════════════

# ── Ortam ─────────────────────────────────────────────────────────────
# development | staging | production
ENVIRONMENT=development
DEBUG=true

# ── Veritabani (ZORUNLU) ──────────────────────────────────────────────
DATABASE_URL=postgresql+psycopg2://bgts_user:bgts_pass@127.0.0.1:5432/syndata_db
REDIS_URL=redis://127.0.0.1:6379/0

# ── Guvenlik (PRODUCTION'DA ZORUNLU) ──────────────────────────────────
# JWT secret en az 64 karakter olmali:
#   openssl rand -base64 64
JWT_SECRET=change-me-in-production-use-long-random-secret

# ── AI Provider ───────────────────────────────────────────────────────
# ollama (local) | openai | anthropic
AI_PROVIDER=ollama

# OpenAI (AI_PROVIDER=openai ise gerekli)
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# Anthropic (AI_PROVIDER=anthropic ise gerekli)
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Ollama (AI_PROVIDER=ollama ise)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL_ANALYST=qwen2.5:32b
OLLAMA_MODEL_FAST=mistral:latest
OLLAMA_MODEL_CODER=qwen2.5-coder:7b

# ── Otomasyon Motoru ──────────────────────────────────────────────────
ENGINE_BASE_URL=http://127.0.0.1:5001

# ── N8N Entegrasyonu ──────────────────────────────────────────────────
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=

# ── CORS ──────────────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# ── Rate Limiting ─────────────────────────────────────────────────────
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_REGISTER=3/minute
RATE_LIMIT_DEFAULT=60/minute

# ── Monitoring (opsiyonel) ────────────────────────────────────────────
SENTRY_DSN=
SENTRY_ENVIRONMENT=development
PROMETHEUS_ENABLED=false
```

## DOSYA 3: backend/.gitignore guncelle
`.env` satirinin ZATEN oldugunu kontrol et. Yoksa ekle:
```
.env
.env.local
.env.production
```

## DOGRULAMA
```bash
python3 -c "import ast; ast.parse(open('backend/app/config.py').read()); print('OK')"
```
```
