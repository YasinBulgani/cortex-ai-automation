---
id: PRE-007
title: "Engine + worker çalışıyor (test execution backend)"
description: "Test koşusu başlatan TC'ler (RUN, EXC, ENG) engine servisine + worker queue'ya ihtiyaç duyar."
setup_steps:
  - "docker-compose up engine worker (Flask + RQ)"
  - "Engine health: GET http://127.0.0.1:5001/health → 200"
  - "Redis erişilebilir (worker queue)"
  - "Playwright Chromium yüklü"
teardown_steps:
  - "Test koşumu sonrası worker queue temizlenir (opsiyonel)"
---

# PRE-007 — Engine + worker çalışıyor

## Amaç

Asenkron test koşumları engine (Flask) + worker (RQ) gerektirir. Synchronous TC'lerde bu önkoşul atlanır.

## Bağımlılık

- PRE-004 (backend API — engine backend ile konuşur)
