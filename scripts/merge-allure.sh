#!/usr/bin/env bash
# Unified Allure report — engine pytest + Playwright E2E sonuçlarını birleştirir.
#
# Amacı: Bugüne kadar engine tarafında pytest `--alluredir=engine/allure-results`
# yazıyor, Playwright E2E tarafı ise Allure'a hiç yazmıyordu. Playwright'a
# `allure-playwright` reporter'ı eklendikten sonra iki kaynak da aynı Allure
# raporunda görünsün diye bu birleştirici script eklendi.
#
# Çıktı:
#   reports/allure-merged-results/  →  tüm result dosyaları
#   reports/allure-report/           →  tek HTML rapor
#
# Ön koşul:
#   - `allure` CLI yüklü (npm i -g allure-commandline veya brew install allure)
#
# Kullanım:
#   scripts/merge-allure.sh
#   scripts/merge-allure.sh --open     # raporu bitince aç (lokal)
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE_RESULTS="$ROOT/engine/allure-results"
E2E_RESULTS="$ROOT/reports/allure-e2e-results"
MERGED="$ROOT/reports/allure-merged-results"
REPORT="$ROOT/reports/allure-report"

mkdir -p "$MERGED" "$ROOT/reports"
rm -rf "$MERGED"/*

copied=0
if [ -d "$ENGINE_RESULTS" ] && compgen -G "$ENGINE_RESULTS/*" >/dev/null; then
    cp -R "$ENGINE_RESULTS"/. "$MERGED"/
    copied=1
    echo "✔ engine/allure-results → merged"
fi
if [ -d "$E2E_RESULTS" ] && compgen -G "$E2E_RESULTS/*" >/dev/null; then
    cp -R "$E2E_RESULTS"/. "$MERGED"/
    copied=1
    echo "✔ reports/allure-e2e-results → merged"
fi

if [ "$copied" = "0" ]; then
    echo "⚠  Hiç Allure result bulunamadı. Önce testleri çalıştırın:" >&2
    echo "   - engine:  cd engine && pytest tests/ --alluredir=allure-results" >&2
    echo "   - e2e:     npx playwright test" >&2
    exit 1
fi

if ! command -v allure >/dev/null 2>&1; then
    echo "⚠  allure CLI kurulu değil. Kurulum:" >&2
    echo "   npm i -g allure-commandline       (veya)" >&2
    echo "   brew install allure" >&2
    exit 2
fi

rm -rf "$REPORT"
allure generate "$MERGED" -o "$REPORT" --clean
echo "✅ Birleşik Allure raporu: $REPORT/index.html"

if [ "${1:-}" = "--open" ]; then
    allure open "$REPORT"
fi
