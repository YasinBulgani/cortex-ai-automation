# Agent 2: Diger Router'lar Error Handling Standardizasyonu

## Cursor'a yapistir:

```
Sen bir senior backend muhendisisin. BGTS bankacilik test otomasyon platformunda
birden fazla router dosyasindaki error handling'i standardize edeceksin.

## KURALLAR
- Python 3.9 uyumlu
- Her dosya degisiklik sonrasi ast.parse gecmeli
- Hata mesajlari TURKCE
- Endpoint logic'e dokunma, sadece error handling
- Her dosyada logger yoksa ekle

## HEDEF ERROR FORMAT
Tum router'larda ayni structured format:
```python
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail={"error": "<DOMAIN>_<KOD>", "message": "Turkce aciklama", "detail": str(e)[:300]}
)
```

## DOSYA DOSYA YAPILACAKLAR

### 1. backend/app/domains/agents/router.py (907 satir, 9 except, 22 raise)
- Dosyanin basinda `import logging` ve `_logger = logging.getLogger(__name__)` OLMAYABILIR — kontrol et, yoksa ekle
- Satir 274, 281, 291: bare `except Exception:` bloklari — logging YOK
  → Her birine `_logger.exception("Agent endpoint hatasi")` ekle
- Satir 395, 697, 748, 793, 830, 876: `except Exception as exc:` — bunlarda logging VAR MI kontrol et, yoksa ekle
- Raw status code varsa status.HTTP_XXX ile degistir

### 2. backend/app/domains/notifications/router.py (100 satir, 2 except, 1 raise)
- `import logging` ve logger ekle
- Satir 44 civari: bare `except Exception` — logging ekle
- Structured error format kullan

### 3. backend/app/domains/n8n/router.py (100 satir, 2 except, 1 raise)
- `import logging` ve logger ekle
- Satir 46 civari: `raise HTTPException(404, "...")` → `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "N8N_NOT_FOUND", "message": "..."})`
- Satir 51 civari: bare except → logging ekle

### 4. backend/app/domains/cicd/router.py (404 satir, 5 except, 4 raise)
- Logger ekle
- Raw 401 kullanimlari → `status.HTTP_401_UNAUTHORIZED` ile degistir
- Webhook signature hatalari icin structured response:
  ```python
  raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail={"error": "CICD_INVALID_SIGNATURE", "message": "Gecersiz webhook imzasi"}
  )
  ```

### 5. backend/app/domains/automation/router.py (59 satir, 0 except, 0 raise)
- Bu dosyada hic error handling YOK — proxy pass-through yapiyor
- httpx isteklerini try/except ile sar:
  ```python
  try:
      resp = httpx.request(...)
  except httpx.ConnectError:
      raise HTTPException(
          status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
          detail={"error": "AUTO_ENGINE_DOWN", "message": "Otomasyon motoru erisilemez"}
      )
  except Exception as e:
      _logger.exception("Otomasyon proxy hatasi")
      raise HTTPException(
          status_code=status.HTTP_502_BAD_GATEWAY,
          detail={"error": "AUTO_PROXY_ERROR", "message": "Motor iletisim hatasi", "detail": str(e)[:200]}
      )
  ```

### 6. backend/app/domains/playwright_mcp/router.py (337 satir, 2 except, 13 raise)
- Logger ZATEN var (import logging, logger = logging.getLogger)
- HTTPException raise'leri kontrol et — raw 500 varsa structured formata donustur
- Playwright-specific error code prefix: "PW_"

### 7. backend/app/domains/tspm/router.py (5443 satir, 45 except, 137 raise) ⚠️ BUYUK DOSYA
- Logger VARSA kontrol et (muhtemelen var)
- 45 except blogundan LOGGING OLMAYANLARI bul, logger.exception() ekle
- Raw status code kullanimlari → status.HTTP_XXX
- Bu dosya cok buyuk — SADECE except bloklarini degistir, baska hicbir seye dokunma
- Error code prefix: "TSPM_"

### 8. backend/app/domains/coverup/router.py (112 satir, 0 except, 0 raise)
- Error handling HIC yok — endpoint'ler coverup servisini cagiriyor
- Kritik endpoint'lere try/except ekle (upload, analyze, generate)
- Error code prefix: "COV_"

## HER DOSYA ICIN KONTROL LISTESI
1. ✅ Dosyayi oku
2. ✅ `import logging` var mi? Yoksa ekle
3. ✅ `from fastapi import status` var mi? Yoksa import'a ekle
4. ✅ `_logger = logging.getLogger(__name__)` var mi? Yoksa ekle
5. ✅ Her bare except'e logger.exception() ekle
6. ✅ Raw status code → status.HTTP_XXX
7. ✅ Hata detail'i structured format: {"error": "...", "message": "...", "detail": "..."}
8. ✅ ast.parse dogrulama

## DOGRULAMA (hepsini bitirdikten sonra)
```bash
python3 -c "
import ast, pathlib
for f in ['agents', 'notifications', 'n8n', 'cicd', 'automation', 'playwright_mcp', 'tspm', 'coverup']:
    path = f'backend/app/domains/{f}/router.py'
    try:
        ast.parse(pathlib.Path(path).read_text())
        print(f'✅ {path}')
    except SyntaxError as e:
        print(f'❌ {path}: {e}')
"
```
```
