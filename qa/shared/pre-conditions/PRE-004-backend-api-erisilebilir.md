---
id: PRE-004
title: "Backend API erişilebilir (http://127.0.0.1:8000)"
description: "Tüm API ve E2E TC'leri için backend servisinin ayakta olmasını garanti eder."
setup_steps:
  - "docker-compose up backend (veya `cd backend && uvicorn app.main:app`)"
  - "Health check: GET /health → 200"
  - "Ready check: GET /ready → 200 (DB bağlantısı dahil)"
teardown_steps: []
---

# PRE-004 — Backend API erişilebilir

## Amaç

API tabanlı TC'ler backend servisine HTTP istek yapar. Bu önkoşul servisin ayakta olduğunu doğrular.

## Setup

```bash
docker-compose up -d backend
curl -fsS http://127.0.0.1:8000/health || (echo "Backend down" && exit 1)
curl -fsS http://127.0.0.1:8000/ready || (echo "DB not ready" && exit 1)
```

## Bunu kullanan TC'ler

`API`, `AUTH`, `PRJ`, `SCN`, `EXC`, `APR`, `RUN`, `SYN`, `INF` domain'lerinin **tümü**.
