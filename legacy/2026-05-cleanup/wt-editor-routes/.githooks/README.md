# Git Hooks — Pipeline Disiplini

Bu klasör pipeline conductor'un git disiplinini destekleyen hook'ları içerir.

## Kurulum

```bash
git config core.hooksPath .githooks
chmod +x .githooks/*
```

Her developer makinesinde bir kez yapılır. Tracking: `.git/config`'e yazılır, repo paylaşımlı değildir.

## Hook'lar

### `pre-commit`
- **Ne yapar:** Pipeline branch'ine commit ederken branch çakışması tespit ederse uyarı verir (non-blocking)
- **Atla:** `SKIP_PIPELINE_HOOK=1 git commit ...`
- **Strict mode:** `STRICT_CONFLICTS=1 git commit ...` → çakışma varsa commit'i engeller

### `pre-push`
- **Ne yapar:**
  1. `main` veya `test`'e doğrudan push'u engeller (PR şart)
  2. Pipeline branch'inde commit mesajlarında `[pipeline: <role> <id>]` etiketi eksikse uyarır
  3. Conflict check koşar (warn)
- **Atla:** `SKIP_PIPELINE_HOOK=1 git push ...`

## Test

```bash
# Hook'ların aktif olduğunu doğrula
git config --get core.hooksPath
# Çıktı: .githooks

# Conflict check'i manuel koş
./scripts/pipeline/check-conflicts.sh

# Strict mode test
./scripts/pipeline/check-conflicts.sh --strict

# JSON çıktı (CI için)
./scripts/pipeline/check-conflicts.sh --json | jq
```

## CI entegrasyonu

Conflict check aynı zamanda `.github/workflows/pipeline-orchestrator.yml` içinde PR üzerinde de çalışır (saatlik scheduled check için `.github/workflows/pipeline-conflict-scan.yml` ayrı).

## Uninstall

```bash
git config --unset core.hooksPath
```
