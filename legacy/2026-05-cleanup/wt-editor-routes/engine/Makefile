.PHONY: smoke regression api all parallel report clean help

PYTHON ?= python3
PYTEST ?= $(PYTHON) -m pytest
RUNNER ?= $(PYTHON) bgts_runner.py

help: ## Kullanilabilir komutlari goster
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

smoke: ## Smoke testlerini calistir (~5 dk)
	$(RUNNER) --suite smoke --report

regression: ## Regresyon testlerini calistir (~30 dk)
	$(RUNNER) --suite regression --report

api: ## API testlerini calistir
	$(RUNNER) --suite api --report

all: ## Tum testleri calistir
	$(RUNNER) --suite all --report

parallel: ## Tum testleri paralel calistir (4 worker)
	$(RUNNER) --suite all --parallel 4 --report

report: ## Son test sonuclarindan Allure rapor olustur
	$(RUNNER) --report-only

lint: ## Python dosyalarini lint et
	$(PYTHON) -m ruff check steps/ tests/ pages/ core/ locators/ test_data/ --fix

typecheck: ## Tip kontrolu yap
	$(PYTHON) -m mypy steps/ tests/ pages/ --ignore-missing-imports

collect: ## Testleri topla (calistirmadan)
	$(PYTEST) --collect-only tests/e2e/ -q

clean: ## Test artifact'larini temizle
	rm -rf allure-results/ reports/output/ screenshots/ traces/ __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
