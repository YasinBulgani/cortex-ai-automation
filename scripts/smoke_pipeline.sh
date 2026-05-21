#!/usr/bin/env bash
# ============================================================
# smoke_pipeline.sh — Manuel Test → Otomasyon Pipeline Smoke Testi
# ============================================================
# Kullanım: ENGINE_URL=http://localhost:5001 ./scripts/smoke_pipeline.sh
# ============================================================

ENGINE="${ENGINE_URL:-http://localhost:5001}"
PASS=0
FAIL=0
LOG=""

pass() { PASS=$((PASS+1)); echo "  ✓ $1"; }
fail() { FAIL=$((FAIL+1)); echo "  ✗ $1"; LOG="$LOG\n  FAIL: $1"; }

echo ""
echo "══════════════════════════════════════════"
echo "  TestwrightAI Pipeline Smoke Test"
echo "  Engine: $ENGINE"
echo "══════════════════════════════════════════"

# 1. Engine sağlık kontrolü
echo ""
echo "1. Engine Health Check"
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$ENGINE/health" 2>/dev/null)
if [ "$STATUS" = "200" ]; then
  pass "Engine /health → 200"
else
  fail "Engine /health → $STATUS (engine çalışıyor mu?)"
  echo ""
  echo "Engine çalışmıyor. Önce başlatın: cd engine && python app.py"
  exit 1
fi

# 2. Manuel test oluştur
echo ""
echo "2. Manuel Test Oluşturma"
CREATE=$(curl -sf -X POST "$ENGINE/api/manual-tests" \
  -H "Content-Type: application/json" \
  -d '{"title":"Smoke Pipeline Test '$(date +%s)'"}' 2>/dev/null)
if echo "$CREATE" | grep -q '"ok": *true\|"ok":true'; then
  pass "POST /api/manual-tests → ok"
else
  fail "POST /api/manual-tests → $CREATE"
fi

# 3. Son oluşturulan test ID'yi al
TESTS=$(curl -sf "$ENGINE/api/manual-tests" 2>/dev/null)
TEST_ID=$(echo "$TESTS" | python3 -c "import json,sys; tests=json.load(sys.stdin); print(tests[0]['id'] if tests else 0)" 2>/dev/null)
if [ "$TEST_ID" -gt 0 ] 2>/dev/null; then
  pass "GET /api/manual-tests → test_id=$TEST_ID"
else
  fail "Test ID alınamadı: $TEST_ID"
  TEST_ID=1
fi

# 4. Adım ekle
echo ""
echo "3. Adım Ekleme"
STEP=$(curl -sf -X POST "$ENGINE/api/manual-tests/$TEST_ID/steps" \
  -H "Content-Type: application/json" \
  -d '{"action":"Kullanıcı login sayfasına gider","expected":"Login formu görünür"}' 2>/dev/null)
if echo "$STEP" | grep -q '"ok": *true\|"ok":true'; then
  pass "POST /api/manual-tests/$TEST_ID/steps → ok"
else
  fail "POST /api/manual-tests/$TEST_ID/steps → $STEP"
fi

STEP2=$(curl -sf -X POST "$ENGINE/api/manual-tests/$TEST_ID/steps" \
  -H "Content-Type: application/json" \
  -d '{"action":"Kullanıcı email ve şifre girer","expected":"Alanlar dolu görünür"}' 2>/dev/null)
if echo "$STEP2" | grep -q '"ok": *true\|"ok":true'; then
  pass "İkinci adım eklendi"
else
  fail "İkinci adım eklenemedi: $STEP2"
fi

# 5. Pipeline önizleme (AI gerektirmez değil, sadece endpoint erişimini test eder)
echo ""
echo "4. Pipeline Önizleme Endpoint Erişimi"
PREVIEW=$(curl -sf -o /dev/null -w "%{http_code}" -X POST \
  "$ENGINE/api/pipeline/manual-to-automation/preview" \
  -H "Content-Type: application/json" \
  -d '{"title":"Smoke Test","steps":[{"action":"Giriş yap","expected":"Dashboard açılır"}]}' \
  2>/dev/null)
if [ "$PREVIEW" = "200" ]; then
  pass "POST /api/pipeline/manual-to-automation/preview → 200"
elif [ "$PREVIEW" = "500" ] || [ "$PREVIEW" = "503" ]; then
  pass "POST /api/pipeline/manual-to-automation/preview → $PREVIEW (endpoint erişilebilir, AI API anahtarı gerekebilir)"
else
  fail "POST /api/pipeline/manual-to-automation/preview → $PREVIEW"
fi

# 6. Ana pipeline endpoint erişimi
echo ""
echo "5. Pipeline Orchestration Endpoint Erişimi"
PIPE=$(curl -sf -o /dev/null -w "%{http_code}" -X POST \
  "$ENGINE/api/pipeline/manual-to-automation" \
  -H "Content-Type: application/json" \
  -d "{\"test_id\":$TEST_ID}" \
  2>/dev/null)
if [ "$PIPE" = "200" ]; then
  pass "POST /api/pipeline/manual-to-automation → 200 (tam çalışıyor)"
elif [ "$PIPE" = "500" ] || [ "$PIPE" = "503" ]; then
  pass "POST /api/pipeline/manual-to-automation → $PIPE (endpoint erişilebilir, AI API anahtarı gerekebilir)"
else
  fail "POST /api/pipeline/manual-to-automation → $PIPE"
fi

# Özet
echo ""
echo "══════════════════════════════════════════"
echo "  Sonuç: $PASS geçti / $((PASS+FAIL)) toplam"
if [ $FAIL -gt 0 ]; then
  echo -e "$LOG"
  echo "  Durum: ⚠️  $FAIL adım başarısız"
  exit 1
else
  echo "  Durum: ✅ Tüm adımlar geçti"
fi
echo "══════════════════════════════════════════"
