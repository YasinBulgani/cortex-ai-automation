# ═══════════════════════════════════════════════════════════════════════════════
# TestwrightAI — Unified Test Runner
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: help setup seed test-smoke test-regression test-full test-service \
        test-backend test-engine test-e2e report clean docker-up docker-down \
        test-paribu test-nexusqa test-nexusqa-domain run-aday-analizi run-aday-degerlendirme \
        gateway-install gateway-dev gateway-test gateway-up gateway-down \
        nexusqa-dev nexusqa-up nexusqa-up-ui nexusqa-down nexusqa-status \
        ollama-status ollama-warm \
        prod-up prod-down prod-logs prod-status prod-deploy ssl-self-signed \
        test-mobile test-load \
        dsl-ai-warm dsl-ai-rebuild dsl-ai-info dsl-editor-config dsl-proposals

SHELL := /bin/bash
PYTHON := python3
PIP := pip3
COMPOSE := $(shell if docker compose version >/dev/null 2>&1; then printf 'docker compose'; elif command -v docker-compose >/dev/null 2>&1; then printf 'docker-compose'; else printf 'docker compose'; fi)
COMPOSE_BASE := $(COMPOSE) -f docker-compose.yml
COMPOSE_AI := $(COMPOSE) -f docker-compose.yml -f docker-compose.ai.yml

# ─── Pipeline (25 rollü agent orkestrasyonu) ────────────────────────────────
# Komutlar: make pipeline-help
-include Makefile.pipeline

# ─── Yardım ──────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "╔═══════════════════════════════════════════════════════════╗"
	@echo "║       TestwrightAI — Test Komutları                     ║"
	@echo "╠═══════════════════════════════════════════════════════════╣"
	@echo "║                                                         ║"
	@echo "║  KURULUM                                                ║"
	@echo "║    make setup         Tüm bağımlılıkları kur           ║"
	@echo "║    make seed          Temel verileri yükle              ║"
	@echo "║    make docker-up     Altyapıyı başlat                  ║"
	@echo "║    make ollama-warm   Ollama modellerini ısıt          ║"
	@echo "║    make ollama-status Ollama yüklü modelleri göster    ║"
	@echo "║                                                         ║"
	@echo "║  TEST SETLERİ                                           ║"
	@echo "║    make test-smoke       Smoke (hızlı doğrulama)       ║"
	@echo "║    make test-regression  Regression (tam doğrulama)    ║"
	@echo "║    make test-full        Full (tüm testler)            ║"
	@echo "║    make test-service     Service (yalnızca API)        ║"
	@echo "║                                                         ║"
	@echo "║  KATMAN TESTLERİ                                        ║"
	@echo "║    make test-backend     Backend pytest                 ║"
	@echo "║    make test-engine      Engine pytest                  ║"
	@echo "║    make test-e2e         E2E Playwright                 ║"
	@echo "║                                                         ║"
	@echo "║  FRAMEWORK TESTLERİ                                     ║"
	@echo "║    make test-paribu          Paribu @paribu etiketli   ║"
	@echo "║    make test-nexusqa        NexusQA tüm testler      ║"
	@echo "║    make test-nexusqa-domain DOMAIN=girit domain testi ║"
	@echo "║                                                         ║"
	@echo "║  ARAÇLAR                                                ║"
	@echo "║    make report               HTML raporu aç            ║"
	@echo "║    make clean                Raporları temizle         ║"
	@echo "║    make docker-down          Altyapıyı durdur          ║"
	@echo "║    make nexusqa-up-ui        Tüm stack + Open WebUI    ║"
	@echo "║    make run-aday-analizi     Aday analizi çalıştır     ║"
	@echo "║    make run-aday-degerlendirme Mülakat aracı çalıştır  ║"
	@echo "║                                                         ║"
	@echo "╚═══════════════════════════════════════════════════════════╝"
	@echo ""

# ─── Kurulum ──────────────────────────────────────────────────────────────────
setup:
	npm ci
	cd apps/web && npm ci
	cd backend && $(PIP) install -r requirements.txt -r requirements-dev.txt
	cd engine && $(PIP) install -r requirements.txt
	npm run playwright:install

seed:
	cd backend && PYTHONPATH=. $(PYTHON) scripts/seed.py

seed-demo:
	cd backend && PYTHONPATH=. $(PYTHON) scripts/seed_demo.py

# ─── Altyapı ─────────────────────────────────────────────────────────────────
docker-up:
	$(COMPOSE_BASE) up -d postgres redis

docker-down:
	$(COMPOSE_AI) down --remove-orphans

docker-full:
	TWAI_ENABLE_AI_STACK=true ./start-all.sh

# ─── Smoke: Hızlı geri bildirim (~2dk) ───────────────────────────────────────
test-smoke: test-backend-smoke test-engine-smoke test-e2e-smoke
	@echo "✅ Smoke suite tamamlandı"

test-backend-smoke:
	cd backend && $(PYTHON) -m pytest -m smoke -v --tb=short

test-engine-smoke:
	cd engine && $(PYTHON) -m pytest tests/unit/ -m "not ai" -v --tb=short

test-e2e-smoke:
	npm run test:e2e:smoke

# ─── Service: Yalnızca API (~3dk) ────────────────────────────────────────────
test-service: test-backend-service test-e2e-service
	@echo "✅ Service suite tamamlandı"

test-backend-service:
	cd backend && $(PYTHON) -m pytest -m "service or regression" -v

test-e2e-service:
	npm run test:e2e:service

# ─── Regression: Mevcut özellik doğrulama (~10dk) ────────────────────────────
test-regression: test-backend test-engine test-e2e-regression
	@echo "✅ Regression suite tamamlandı"

test-e2e-regression:
	npm run test:e2e:regression

# ─── Full: Tüm testler (~20dk) ───────────────────────────────────────────────
test-full: test-backend-full test-engine-full test-e2e-full
	@echo "✅ Full suite tamamlandı"

test-backend-full:
	cd backend && $(PYTHON) -m pytest --cov=app --cov-report=term-missing --cov-report=html:../reports/backend-coverage -v

test-engine-full:
	cd engine && $(PYTHON) -m pytest tests/ -m "not ai" -v --tb=short

test-e2e-full:
	npm run test:e2e:full

# ─── Katman kısayolları ──────────────────────────────────────────────────────
test-backend:
	cd backend && $(PYTHON) -m pytest -v --tb=short

test-contract:
	cd backend && $(PYTHON) -m pytest tests/contract/test_openapi_contract.py -v --tb=short

test-engine:
	cd engine && $(PYTHON) -m pytest tests/unit/ -m "not ai" -v --tb=short

test-e2e:
	npm run test:e2e

# ─── Raporlama ───────────────────────────────────────────────────────────────
report:
	npm run report:open

clean:
	rm -rf reports/
	rm -rf e2e/.auth/
	rm -rf backend/reports/
	rm -rf engine/reports/
	@echo "🧹 Tüm raporlar temizlendi"

# ─── Framework Testleri ──────────────────────────────────────────────────────
test-paribu:
	cd frameworks/playwright-cucumber-ts && npx cucumber-js --tags @paribu

test-nexusqa:
	cd frameworks/selenium-cucumber-java && mvn test

test-nexusqa-domain:
	cd frameworks/selenium-cucumber-java && mvn test -Ddomains=$(DOMAIN)
# Kullanım: make test-nexusqa-domain DOMAIN=girit

# ─── Araçlar ─────────────────────────────────────────────────────────────────
run-aday-analizi:
	cd tools/aday-analizi && $(PYTHON) main.py

run-aday-degerlendirme:
	cd tools/aday-degerlendirme && mvn exec:java -Dexec.mainClass="Main"

# ═══════════════════════════════════════════════════════════════════════════════
# NEXUS QA — AI Gateway (Faz 0)
# ═══════════════════════════════════════════════════════════════════════════════

## AI Gateway kurulumu (bağımlılıkları yükle)
gateway-install:
	@echo "📦 AI Gateway bağımlılıkları kuruluyor..."
	cd ai-gateway && $(PIP) install -r requirements.txt --break-system-packages
	@echo "✅ AI Gateway kurulumu tamamlandı"
	@echo ""
	@echo "⚙️  API key'leri için:"
	@echo "   cp ai-gateway/.env.example ai-gateway/.env"
	@echo "   # Groq: https://console.groq.com (ücretsiz)"
	@echo "   # Gemini: https://aistudio.google.com/app/apikey (ücretsiz)"

## AI Gateway geliştirme modu (hot-reload, port 8080)
gateway-dev:
	@echo "🚀 AI Gateway başlatılıyor (geliştirme modu)..."
	cd ai-gateway && uvicorn main:app --host 0.0.0.0 --port 8080 --reload

## AI Gateway testleri
gateway-test:
	@echo "🧪 AI Gateway testleri çalıştırılıyor..."
	cd ai-gateway && $(PYTHON) -m pytest tests/ -v --tb=short
	@echo "✅ AI Gateway testleri tamamlandı"

## AI Gateway Docker'da başlat
gateway-up:
	@echo "🐳 AI Gateway Docker'da başlatılıyor..."
	$(COMPOSE_AI) up -d ai-gateway
	@echo "✅ AI Gateway çalışıyor → http://localhost:8080"
	@echo "   Docs: http://localhost:8080/docs"
	@echo "   Health: http://localhost:8080/ai/health"

## AI Gateway Docker'da durdur
gateway-down:
	$(COMPOSE_AI) stop ai-gateway
	$(COMPOSE_AI) rm -f ai-gateway

# ─── Nexus QA — Tüm Servisler ──────────────────────────────────────────────

## Nexus QA geliştirme ortamını başlat (altyapı + AI gateway)
nexusqa-dev:
	@echo "🚀 Nexus QA geliştirme ortamı başlatılıyor..."
	$(COMPOSE_BASE) up -d postgres redis
	@echo "   PostgreSQL: localhost:5432"
	@echo "   Redis: localhost:6379"
	@echo ""
	@echo "   AI Gateway başlatmak için: make gateway-dev"
	@echo "   Backend başlatmak için: cd backend && uvicorn app.main:app --port 8000 --reload"
	@echo "   Frontend başlatmak için: cd apps/web && npm run dev"

## Tüm Nexus QA servislerini Docker'da başlat
nexusqa-up:
	@echo "🐳 Nexus QA tüm servisler başlatılıyor..."
	TWAI_ENABLE_AI_STACK=true ./start-all.sh
	@echo ""
	@echo "✅ Servisler çalışıyor:"
	@echo "   PostgreSQL:  localhost:5432"
	@echo "   Redis:       localhost:6379"
	@echo "   Backend:     http://localhost:8000"
	@echo "   Engine:      http://localhost:5001"
	@echo "   AI Gateway:  http://localhost:8080  ← YENİ"
	@echo "   AI Health:   http://localhost:8080/ai/health"
	@echo "   AI Docs:     http://localhost:8080/docs"

nexusqa-up-ui:
	@echo "🐳 Nexus QA tüm servisler + Open WebUI başlatılıyor..."
	TWAI_ENABLE_AI_STACK=true TWAI_ENABLE_OPEN_WEBUI=true ./start-all.sh --ai-ui
	@echo "   Open WebUI:  http://localhost:3001"

## Tüm Nexus QA servislerini durdur
nexusqa-down:
	$(COMPOSE_AI) down --remove-orphans
	@echo "🛑 Tüm servisler durduruldu"

## Servis durumlarını göster
nexusqa-status:
	@echo "📊 Nexus QA Servis Durumu:"
	@$(COMPOSE_AI) --profile ui ps 2>/dev/null || echo "Docker Compose çalışmıyor"
	@echo ""
	@echo "🔍 AI Gateway health check:"
	@curl -s http://localhost:8080/ai/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "   AI Gateway çalışmıyor (make gateway-dev)"

ollama-status:
	@bash ./scripts/ollama-warm.sh --status

ollama-warm:
	@bash ./scripts/ollama-warm.sh

# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCTION
# ═══════════════════════════════════════════════════════════════════════════════

COMPOSE_PROD := $(COMPOSE) -f docker-compose.prod.yml

## Production stack'i başlat (.env dosyası şart)
prod-up:
	@if [ ! -f .env ]; then \
		echo "❌ .env dosyası bulunamadı!"; \
		echo "   cp .env.example .env  →  sonra CHANGEME değerlerini doldurun"; \
		exit 1; \
	fi
	@echo "🚀 Production stack başlatılıyor..."
	$(COMPOSE_PROD) up -d
	@echo ""
	@echo "✅ Production servisleri çalışıyor:"
	@echo "   HTTPS:     https://bgtest.dev"
	@echo "   Grafana:   https://bgtest.dev/grafana"
	@echo "   Prometheus: http://localhost:9090 (iç ağ)"
	@$(COMPOSE_PROD) ps

## Production stack'i durdur
prod-down:
	$(COMPOSE_PROD) down
	@echo "🛑 Production stack durduruldu"

## Production log'larını takip et
prod-logs:
	$(COMPOSE_PROD) logs -f --tail=100

## Production servis durumları
prod-status:
	@echo "📊 Production Servis Durumu:"
	@$(COMPOSE_PROD) ps
	@echo ""
	@echo "🔍 Health check'ler:"
	@curl -sk https://localhost/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "   Backend: UNREACHABLE"
	@curl -sk http://localhost:9090/-/healthy 2>/dev/null && echo "   Prometheus: OK" || echo "   Prometheus: UNREACHABLE"

## Yeni image'ı sıfır downtime ile deploy et (rolling update)
prod-deploy:
	@echo "🔄 Rolling deploy başlatılıyor (IMAGE_TAG=$(IMAGE_TAG:-latest))..."
	$(COMPOSE_PROD) pull
	$(COMPOSE_PROD) up -d --no-deps --scale backend=2 backend
	sleep 10
	$(COMPOSE_PROD) up -d --no-deps web engine worker ai-gateway
	@echo "✅ Deploy tamamlandı"

## Self-signed SSL sertifikası oluştur (staging/test)
ssl-self-signed:
	@mkdir -p infra/ssl
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout infra/ssl/key.pem \
		-out infra/ssl/cert.pem \
		-subj "/C=TR/ST=Istanbul/L=Istanbul/O=TestwrightAI/CN=localhost"
	@echo "✅ Self-signed SSL sertifikası oluşturuldu: infra/ssl/"

## Visium Farm mobil E2E testlerini çalıştır
test-mobile:
	npx playwright test --project=regression e2e/mobile.spec.ts --reporter=list

## BDD testlerini çalıştır (Cucumber + Playwright)
test-bdd:
	npm run test:bdd

## BDD smoke testleri
test-bdd-smoke:
	npm run test:bdd:smoke

## BDD regression testleri
test-bdd-regression:
	npm run test:bdd:regression

## Cross-browser testleri (Chromium + Firefox + WebKit)
test-cross-browser:
	PLAYWRIGHT_BROWSERS_PATH=.pw-browsers npx playwright install chromium firefox webkit
	npm run test:e2e:cross-browser

## k6 yük testini çalıştır
test-load:
	@if command -v k6 >/dev/null 2>&1; then \
		k6 run tests/load/api-load.js; \
	else \
		echo "❌ k6 kurulu değil: https://k6.io/docs/getting-started/installation/"; \
	fi

# ═══════════════════════════════════════════════════════════════════════════════
# DSL AI Embedding Index + Editör
# ═══════════════════════════════════════════════════════════════════════════════
# bge-m3 embedding modelini Ollama'ya çek ve ısıt. Sonra backend
# /dsl/index/rebuild ile alias corpus'unu vektörleştirip AI aramayı açar.
# Editör uç noktalarını ve bekleyen önerileri inceleyen yardımcılar da var.

OLLAMA_EMBED_MODEL ?= bge-m3
API_BASE ?= http://127.0.0.1:8000
DSL_AI_TOKEN ?=

## bge-m3 gibi embedding modellerini Ollama'ya çek ve ısıt
dsl-ai-warm:
	@command -v ollama >/dev/null 2>&1 || { echo "ollama bulunamadı"; exit 1; }
	@echo "[dsl-ai] $(OLLAMA_EMBED_MODEL) pull ediliyor..."
	@ollama pull $(OLLAMA_EMBED_MODEL)
	@TWAI_OLLAMA_WARM_MODELS=$(OLLAMA_EMBED_MODEL) bash ./scripts/ollama-warm.sh

## DSL embedding indeksini backend üzerinden zorla yeniden oluştur
##   make dsl-ai-rebuild DSL_AI_TOKEN=<access_token>
dsl-ai-rebuild:
	@if [ -z "$(DSL_AI_TOKEN)" ]; then \
		echo "DSL_AI_TOKEN boş — önce admin access token al."; exit 1; \
	fi
	@curl -fsS -X POST "$(API_BASE)/api/v1/dsl/index/rebuild?force=true" \
		-H "Authorization: Bearer $(DSL_AI_TOKEN)" | python3 -m json.tool

## DSL embedding indeksinin mevcut durumunu göster
dsl-ai-info:
	@if [ -z "$(DSL_AI_TOKEN)" ]; then \
		echo "DSL_AI_TOKEN boş — önce admin access token al."; exit 1; \
	fi
	@curl -fsS "$(API_BASE)/api/v1/dsl/index/info" \
		-H "Authorization: Bearer $(DSL_AI_TOKEN)" | python3 -m json.tool

## DSL editör config — git_enabled, git_mode, provider durumunu yazdır
dsl-editor-config:
	@if [ -z "$(DSL_AI_TOKEN)" ]; then \
		echo "DSL_AI_TOKEN boş — önce admin access token al."; exit 1; \
	fi
	@curl -fsS "$(API_BASE)/api/v1/dsl/editor/config" \
		-H "Authorization: Bearer $(DSL_AI_TOKEN)" | python3 -m json.tool

## Bekleyen DSL düzenleme önerilerini listele
dsl-proposals:
	@if [ -z "$(DSL_AI_TOKEN)" ]; then \
		echo "DSL_AI_TOKEN boş — önce admin access token al."; exit 1; \
	fi
	@curl -fsS "$(API_BASE)/api/v1/dsl/proposals?status=pending&limit=50" \
		-H "Authorization: Bearer $(DSL_AI_TOKEN)" | python3 -m json.tool
