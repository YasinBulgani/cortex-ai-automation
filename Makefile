# ═══════════════════════════════════════════════════════════════════════════════
# TestwrightAI — Unified Test Runner
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: help setup setup-venv seed test-smoke test-regression test-full test-service \
        test-backend test-engine test-e2e report clean docker-up docker-down \
        test-paribu test-nexusqa test-nexusqa-domain run-aday-analizi run-aday-degerlendirme \
        gateway-install gateway-dev gateway-test gateway-up gateway-down \
        nexusqa-dev nexusqa-up nexusqa-up-ui nexusqa-down nexusqa-status nexusqa-smoke \
        ollama-status ollama-warm \
        prod-up prod-down prod-logs prod-status prod-deploy validate-env ssl-self-signed \
        test-mobile test-load \
        dsl-ai-warm dsl-ai-rebuild dsl-ai-info dsl-editor-config dsl-proposals \
        sec-audit eval tia

SHELL := /bin/bash
VENV   := .venv
PYTHON := $(VENV)/bin/python3
PIP    := $(VENV)/bin/pip
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
	@echo "║  CORTEX OTOMASYON (Java)                                ║"
	@echo "║    make cortex-help          Cortex komutlari          ║"
	@echo "║    make cortex-smoke         Cortex smoke              ║"
	@echo "║    make cortex-record        Recorder                  ║"
	@echo "║                                                         ║"
	@echo "║  ARAÇLAR                                                ║"
	@echo "║    make report               HTML raporu aç            ║"
	@echo "║    make clean                Raporları temizle         ║"
	@echo "║    make docker-down          Altyapıyı durdur          ║"
	@echo "║    make nexusqa-up-ui        Tüm stack + Open WebUI    ║"
	@echo "║    make nexusqa-smoke        Uçtan uca canlı smoke     ║"
	@echo "║    make run-aday-analizi     Aday analizi çalıştır     ║"
	@echo "║    make run-aday-degerlendirme Mülakat aracı çalıştır  ║"
	@echo "║                                                         ║"
	@echo "╚═══════════════════════════════════════════════════════════╝"
	@echo ""

# ─── Kurulum ──────────────────────────────────────────────────────────────────
$(VENV):
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip setuptools wheel

setup: $(VENV)
	npm ci
	cd apps/web && npm ci
	$(PIP) install -r backend/requirements.txt -r backend/requirements-dev.txt
	$(PIP) install -r engine/requirements.txt
	npm run playwright:install

setup-venv:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r backend/requirements.txt -r backend/requirements-dev.txt
	.venv/bin/pip install -r engine/requirements.txt
	@echo "✓ Virtual environment ready. Run: source .venv/bin/activate"

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

## Demo ortamı — 10 dakikalık "ilk deneme" akışı (UX-F1-102)
## Postgres + Redis + Backend + Engine + Web ayağa kalkar, seed + demo proje.
## URL: http://localhost:3000/login (admin@example.com / admin123)
.PHONY: demo demo-up demo-seed demo-status demo-down
demo: demo-up demo-seed demo-status

demo-up:
	@echo "▶ Demo servisleri başlatılıyor (demo override profili aktif)..."
	@docker compose -f docker-compose.yml -f docker-compose.demo.yml up -d \
		postgres redis backend web engine
	@echo "▶ Backend readiness bekleniyor (max 60s)..."
	@for i in $$(seq 1 30); do \
		if curl -s http://localhost:8000/health >/dev/null 2>&1; then \
			echo "✓ Backend hazır."; break; \
		fi; \
		sleep 2; \
	done
	@if ! curl -s http://localhost:8000/health >/dev/null 2>&1; then \
		echo "⚠ Backend 60s'de yanıt vermedi — 'docker compose logs backend' ile kontrol edin."; \
		exit 1; \
	fi

demo-seed:
	@echo "▶ Seed + demo verisi yükleniyor..."
	@docker compose exec -T backend python scripts/seed.py 2>/dev/null || \
		cd backend && PYTHONPATH=. $(PYTHON) scripts/seed.py
	@docker compose exec -T backend python scripts/seed_demo.py 2>/dev/null || \
		cd backend && PYTHONPATH=. $(PYTHON) scripts/seed_demo.py
	@echo "✓ Seed tamamlandı."

demo-status:
	@echo ""
	@echo "╔═══════════════════════════════════════════════════════════╗"
	@echo "║  🎉 BGTS / TestwrightAI Demo hazır                         ║"
	@echo "╠═══════════════════════════════════════════════════════════╣"
	@echo "║                                                           ║"
	@echo "║  Web arayüzü:  http://localhost:3000                      ║"
	@echo "║  Backend API:  http://localhost:8000/docs                 ║"
	@echo "║  Engine:       http://localhost:5001/health               ║"
	@echo "║                                                           ║"
	@echo "║  Demo giriş:   admin@example.com / admin123               ║"
	@echo "║                                                           ║"
	@echo "║  İlk test üretmek için:                                   ║"
	@echo "║    → http://localhost:3000/bgtest-wizard                  ║"
	@echo "║                                                           ║"
	@echo "║  Port durumu:  make ports-check                           ║"
	@echo "║  Logları gör:  docker compose logs -f backend             ║"
	@echo "║  Kapatmak:     make demo-down                             ║"
	@echo "║                                                           ║"
	@echo "║  Kılavuz:      docs/user-guide/01-quickstart.md           ║"
	@echo "╚═══════════════════════════════════════════════════════════╝"

demo-down:
	@echo "▶ Demo servisleri kapatılıyor..."
	@docker compose stop postgres redis backend web engine
	@echo "✓ Demo kapatıldı (veriler korundu — tekrar 'make demo' ile kaldığın yerden)."

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

# ─── Cortex Otomasyon (frameworks/cortex-java) ───────────────────────────────
.PHONY: cortex-help cortex-smoke cortex-regression cortex-parallel cortex-debug \
        cortex-record cortex-lint cortex-dashboard cortex-install cortex-rerun cortex-clean

CORTEX_DIR := frameworks/cortex-java

cortex-help:
	@echo ""
	@echo "  CORTEX OTOMASYON (frameworks/cortex-java/)"
	@echo "    make cortex-install    Playwright browser'larini indir (ilk seferde)"
	@echo "    make cortex-smoke      @smoke tagli senaryolar"
	@echo "    make cortex-regression Full Cortex regression"
	@echo "    make cortex-parallel   4 thread paralel regression"
	@echo "    make cortex-debug      trace + video + slow-mo"
	@echo "    make cortex-rerun      Onceki failed senaryolari tekrar dene"
	@echo "    make cortex-record     IntelliJ-driven recorder"
	@echo "    make cortex-lint       LocatorLinter"
	@echo "    make cortex-dashboard  Flask dashboard (http://localhost:5001)"
	@echo "    make cortex-clean      target/ temizle"
	@echo ""

cortex-install:
	cd $(CORTEX_DIR) && ./scripts/cortex install

cortex-smoke:
	cd $(CORTEX_DIR) && ./scripts/cortex smoke

cortex-regression:
	cd $(CORTEX_DIR) && ./scripts/cortex regression

cortex-parallel:
	cd $(CORTEX_DIR) && ./scripts/cortex parallel 4

cortex-debug:
	@test -n "$(FEATURE)" || { echo "FEATURE=path/to/file.feature zorunlu"; exit 1; }
	cd $(CORTEX_DIR) && ./scripts/cortex debug $(FEATURE)

cortex-record:
	cd $(CORTEX_DIR) && ./scripts/cortex record $(URL)

cortex-lint:
	cd $(CORTEX_DIR) && ./scripts/cortex lint

cortex-dashboard:
	cd $(CORTEX_DIR) && ./scripts/cortex dashboard

cortex-rerun:
	cd $(CORTEX_DIR) && ./scripts/cortex rerun

cortex-clean:
	cd $(CORTEX_DIR) && ./scripts/cortex clean

# ─── Cortex Servis Orkestrasyonu (Onboarding) ────────────────────────────────
# Bu target'lar Cortex Automation'ın çalışması için gerekli 4 servisi yönetir:
# Ollama (11434) + Flask (5001) + Next.js Dashboard (3000) + Java JVM (on-demand)

cortex-up: ## Tüm Cortex servislerini başlat (Ollama + Flask + Dashboard)
	@echo "→ Ollama başlatılıyor..."
	@if ! curl -s -m 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then \
		nohup ollama serve > /tmp/cortex-ollama.log 2>&1 & \
		echo "  Ollama spawn edildi (log: /tmp/cortex-ollama.log)"; \
		sleep 3; \
	else \
		echo "  ✓ Ollama zaten çalışıyor"; \
	fi
	@echo "→ Flask API başlatılıyor..."
	@if ! curl -s -m 1 http://127.0.0.1:5001/ >/dev/null 2>&1; then \
		cd $(CORTEX_DIR) && nohup python3 python_server/flask_api.py > /tmp/cortex-flask.log 2>&1 & \
		echo "  Flask spawn edildi (log: /tmp/cortex-flask.log)"; \
		sleep 3; \
	else \
		echo "  ✓ Flask zaten çalışıyor"; \
	fi
	@echo "→ Next.js Dashboard başlatılıyor..."
	@if ! curl -s -m 1 http://127.0.0.1:3000/ >/dev/null 2>&1; then \
		cd apps/web && nohup npm run dev > /tmp/cortex-nextjs.log 2>&1 & \
		echo "  Next.js spawn edildi (log: /tmp/cortex-nextjs.log)"; \
		echo "  ~30sn ilk derleme süresi var..."; \
	else \
		echo "  ✓ Next.js zaten çalışıyor"; \
	fi
	@echo ""
	@echo "Dashboard: http://localhost:3000/products/intelligence"
	@echo "Durum kontrolü: make cortex-status"

cortex-down: ## Tüm Cortex servislerini durdur (JVM + Flask + Next.js + Ollama)
	@echo "→ Cortex servisleri durduruluyor..."
	-@pkill -9 -f "exec:java" 2>/dev/null && echo "  ✓ Java JVM'ler kapatıldı" || echo "  - JVM yok"
	-@pkill -9 -f "playwright-java" 2>/dev/null && echo "  ✓ Playwright helper'ları kapatıldı" || true
	-@pkill -f "python_server/flask_api.py" 2>/dev/null && echo "  ✓ Flask kapatıldı" || echo "  - Flask yok"
	-@pkill -f "next dev" 2>/dev/null && echo "  ✓ Next.js kapatıldı" || echo "  - Next.js yok"
	@echo "  (Ollama: kapatmıyorum, başka uygulamalar kullanıyor olabilir)"
	@echo "  Ollama'yı kapatmak için: pkill -f 'ollama serve'"

cortex-status: ## Tüm Cortex servislerinin durumunu göster
	@echo "Cortex Servis Durumu:"
	@printf "  Flask   :5001   "
	@if curl -s -m 1 http://127.0.0.1:5001/ >/dev/null 2>&1; then echo "✓ çalışıyor"; else echo "✗ kapalı"; fi
	@printf "  Next.js :3000   "
	@if curl -s -m 1 http://127.0.0.1:3000/ >/dev/null 2>&1; then echo "✓ çalışıyor"; else echo "✗ kapalı"; fi
	@printf "  Ollama  :11434  "
	@if curl -s -m 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then echo "✓ çalışıyor (AI polish aktif)"; else echo "○ kapalı (opsiyonel — AI polish devre dışı)"; fi
	@printf "  Java JVM        "
	@n=$$(ps -ax | grep "exec:java" | grep -v grep | wc -l | tr -d ' '); \
	if [ "$$n" -gt 0 ]; then echo "● $$n aktif recorder JVM (cortex-down ile öldür)"; else echo "○ idle (recorder kullanılmıyor)"; fi
	@printf "  Recorder server  "
	@if curl -s -m 1 http://127.0.0.1:7700/status >/dev/null 2>&1; then echo "✓ :7700 dinliyor"; else echo "○ aktif değil"; fi

cortex-feature: ## Tek bir .feature dosyasını çalıştır (FEATURE=path/to/file zorunlu)
	@test -n "$(FEATURE)" || { echo "Kullanım: make cortex-feature FEATURE=src/test/resources/recordings/foo.feature"; exit 1; }
	cd $(CORTEX_DIR) && ./scripts/cortex feature $(FEATURE)

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
	cd ai-gateway && $(PIP) install -r requirements.txt
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

## Nexus QA canlı smoke: health + login + proje + autopilot
nexusqa-smoke:
	@set -e; \
	echo "🧪 Nexus QA smoke başlıyor..."; \
	curl -fsS http://localhost:8000/health >/dev/null; \
	curl -fsS http://localhost:8080/ai/health >/dev/null; \
	curl -fsS http://localhost:5001/health >/dev/null; \
	echo "✅ Health endpoint'leri hazır"; \
	TOKEN=$$(curl -fsS -X POST http://localhost:8000/api/v1/auth/login \
		-H "Content-Type: application/json" \
		-d '{"email":"test@test.com","password":"test"}' \
		| python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'); \
	PROJECT_ID=$$(curl -fsS http://localhost:8000/api/v1/tspm/projects \
		-H "Authorization: Bearer $$TOKEN" \
		| python3 -c 'import json,sys; data=json.load(sys.stdin); print(data[0]["id"] if data else "")'); \
	if [ -z "$$PROJECT_ID" ]; then \
		echo "❌ Smoke: erişilebilir proje bulunamadı"; \
		exit 1; \
	fi; \
	curl -fsS "http://localhost:8000/api/v1/ai/autopilot/status?project_id=$$PROJECT_ID" \
		-H "Authorization: Bearer $$TOKEN" >/dev/null; \
	RUN_ID=$$(curl -fsS -X POST http://localhost:8000/api/v1/ai/autopilot/run \
		-H "Authorization: Bearer $$TOKEN" \
		-H "Content-Type: application/json" \
		-d "{\"project_id\":\"$$PROJECT_ID\",\"mode\":\"observe\",\"apply_safe_actions\":false,\"trigger\":\"smoke\"}" \
		| python3 -c 'import json,sys; print(json.load(sys.stdin).get("id",""))'); \
	if [ -z "$$RUN_ID" ]; then \
		echo "❌ Smoke: autopilot run id alınamadı"; \
		exit 1; \
	fi; \
	RUN_OK=$$(curl -fsS "http://localhost:8000/api/v1/ai/autopilot/runs?project_id=$$PROJECT_ID&limit=20" \
		-H "Authorization: Bearer $$TOKEN" \
		| RUN_ID="$$RUN_ID" python3 -c 'import json,os,sys; rid=os.environ["RUN_ID"]; runs=json.load(sys.stdin).get("runs",[]); ok=any(r.get("id")==rid and r.get("mode")=="observe" and r.get("trigger")=="smoke" and r.get("status") in {"completed","partial"} for r in runs); print("yes" if ok else "no")'); \
	if [ "$$RUN_OK" != "yes" ]; then \
		echo "❌ Smoke: autopilot run doğrulaması başarısız (run_id=$$RUN_ID)"; \
		exit 1; \
	fi; \
	echo "✅ Smoke tamam: project=$$PROJECT_ID run_id=$$RUN_ID (autopilot observe doğrulandı)"

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

## Production ENV değişkenlerini doğrula (deployment öncesi)
validate-env:
	@bash scripts/validate-prod-env.sh $(ENV_FILE)

## Yeni image'ı sıfır downtime ile deploy et (rolling update)
prod-deploy: validate-env
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

# ─── Eval Harness (D1·E1.1) ──────────────────────────────────────────────────
# AI/DSL çıktı kalitesi için golden set tabanlı regresyon.
# Fixture suite'ler deterministik koşar; canlı LLM trendi için EVAL_RUN_LLM=1.

.PHONY: eval eval-suite eval-strict eval-unit eval-live-gateway

## Tüm eval suite'lerini koş (reports/evals/<ts>/ altına JSON+HTML yazar)
eval:
	@cd backend && ../.venv/bin/python -m app.domains.evals.cli

## Tek suite: make eval-suite SUITE=dsl_retrieval
eval-suite:
	@if [ -z "$(SUITE)" ]; then echo "SUITE=<name> gerekli"; exit 2; fi
	@cd backend && ../.venv/bin/python -m app.domains.evals.cli --suite $(SUITE)

## CI modu: skip'i de fail say (adapter hazır değilse exit 1)
eval-strict:
	@cd backend && ../.venv/bin/python -m app.domains.evals.cli --strict-skip

## Eval harness için unit testler (scorers + runner + loader)
eval-unit:
	@cd backend && ../.venv/bin/python -m pytest tests/eval/ -q

## Canlı AI Gateway eval — gerçek LLM çağrısı yapar (gateway + key hazır olmalı)
eval-live-gateway:
	@cd backend && set -a; [ -f .env ] && source .env; set +a; EVAL_RUN_LLM=1 $(PYTHON) -m app.domains.evals.cli \
		--suites-dir app/domains/evals/live_suites \
		--suite ai_gateway_live \
		--strict-skip \
		--json ../reports/evals/ai-gateway-live-summary.json

# ─── Test Impact Analysis (D2·E2.3) ─────────────────────────────────────────

.PHONY: tia tia-json

## PR diff → etkilenen test listesi (stdout) — BASE/HEAD override edilebilir
tia:
	@cd backend && ../.venv/bin/python -m scripts.tia --base $${BASE:-origin/main} --head $${HEAD:-HEAD}

tia-json:
	@cd backend && ../.venv/bin/python -m scripts.tia --base $${BASE:-origin/main} --head $${HEAD:-HEAD} --json

# ─── Privacy / Compliance (D3·E3.1, E3.6) ────────────────────────────────────

.PHONY: compliance-coverage compliance-evidence privacy-test

## Kontrol matrisi + unmapped rapor — unmapped varsa exit 1
compliance-coverage:
	@cd backend && ../.venv/bin/python -m app.domains.compliance.cli --coverage --fail-on-gap

## Evidence pack JSON → reports/compliance/pack.json
compliance-evidence:
	@mkdir -p reports/compliance
	@cd backend && ../.venv/bin/python -m app.domains.compliance.cli --export ../reports/compliance/pack.json

## Privacy scanner birim testleri (bankacılık P0 gate)
privacy-test:
	@cd backend && ../.venv/bin/python -m pytest tests/unit/test_privacy_scanner.py -q

# ─── Migration asistanı (D4·E4.4) ────────────────────────────────────────────

.PHONY: migrate

## make migrate SOURCE=selenium-java FILE=path/to/Steps.java [OUT=out.ts]
## make migrate SOURCE=katalon DIR=src/katalon/
migrate:
	@cd backend && ../.venv/bin/python -m scripts.migrate \
		--source $(SOURCE) \
		$(if $(FILE),--file $(FILE)) \
		$(if $(DIR),--dir $(DIR)) \
		$(if $(OUT),--out $(OUT))

# ─── Security (D3·E3.4) — local runs ─────────────────────────────────────────

.PHONY: sec-scan sec-audit

## gitleaks + pip-audit local — CI dışında da çalıştırılabilir (araçlar kurulu olmalı)
sec-scan:
	@echo "→ gitleaks protect --staged..."
	@command -v gitleaks >/dev/null 2>&1 && gitleaks protect --staged --redact --config .gitleaks.toml || echo "(gitleaks kurulu değil, CI'da zorunlu)"

sec-audit:
	@echo "→ pip-audit (backend/requirements.txt)..."
	@../.venv/bin/pip-audit --requirement backend/requirements.txt 2>&1 | tail -20 || echo "(pip-audit kurulu değil: pip install pip-audit)"

# ─── Full test (tüm yeni unit'ler) ───────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# Backbone quality gates
# ──────────────────────────────────────────────────────────────────────────────

.PHONY: prompt-lock prompt-check migration-roundtrip contracts-generate contracts-check backbone-check

## Update prompt_center/manifest.lock.json hashes
prompt-lock:
	$(PYTHON) prompt_center/lock.py

## CI: verify prompt lock file is up to date (fails if stale)
prompt-check:
	$(PYTHON) prompt_center/lock.py --check

## Regenerate packages/contracts/src/openapi.d.ts from live FastAPI spec
contracts-generate:
	cd backend && TESTING=true $(PYTHON) -c "import json; from app.main import app; open('../openapi.json','w').write(json.dumps(app.openapi(), indent=2))"
	npm run -w @neurex/contracts generate:file

## CI: check contracts/openapi.d.ts is not stale (fails if drift detected)
contracts-check: contracts-generate
	@echo "Checking for drift in packages/contracts/src/openapi.d.ts..."
	git diff --exit-code packages/contracts/src/openapi.d.ts || \
		(echo "ERROR: openapi.d.ts is stale. Run: make contracts-generate && git add" && exit 1)

## Run alembic up → down → up roundtrip (requires local Postgres)
migration-roundtrip:
	cd backend && PYTHONPATH=. $(PYTHON) -m alembic upgrade head
	cd backend && PYTHONPATH=. $(PYTHON) -m alembic downgrade base
	cd backend && PYTHONPATH=. $(PYTHON) -m alembic upgrade head
	@echo "Migration roundtrip OK"

## Run all backbone quality gates locally
backbone-check: prompt-check contracts-check
	@echo "All backbone checks passed"

.PHONY: test-all-new

## Bu sprint eklenen tüm yeni unit testleri tek komutla koş
test-all-new:
	@cd backend && ../.venv/bin/python -m pytest \
		tests/unit/test_feature_flags.py \
		tests/unit/test_pricing.py \
		tests/unit/test_budget.py \
		tests/unit/test_usage_service.py \
		tests/unit/test_prompts.py \
		tests/unit/test_healing_locator.py \
		tests/unit/test_healing_patch.py \
		tests/unit/test_healing_orchestrator.py \
		tests/unit/test_healing_router.py \
		tests/unit/test_flaky_service.py \
		tests/unit/test_tia.py \
		tests/unit/test_privacy_scanner.py \
		tests/unit/test_prompt_shield.py \
		tests/unit/test_audit_chain.py \
		tests/unit/test_rbac_policy.py \
		tests/unit/test_compliance_mapping.py \
		tests/unit/test_roi_service.py \
		tests/unit/test_visual_compare.py \
		tests/unit/test_a11y_service.py \
		tests/unit/test_pr_bot.py \
		tests/unit/test_marketplace_templates.py \
		tests/unit/test_telemetry.py \
		tests/unit/test_migration_assistant.py \
		tests/eval/ \
		-q
