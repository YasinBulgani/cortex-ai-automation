# Agent 1: AI Router Error Handling Cleanup

## Cursor'a yapistir:

```
Sen bir senior backend muhendisisin. BGTS bankacilik test otomasyon platformunda
backend/app/domains/ai/router.py dosyasindaki error handling'i standardize edeceksin.

## PROJE BILGILERI
- Proje koku: bu repo'nun root'u
- Python 3.9 uyumlu kod yaz (Optional[str] kullan, str | None DEGIL — ama dosyada zaten from __future__ import annotations var, o yuzden tip annotasyonlari icin sorun yok)
- Dosya degisiklikten sonra ast.parse gecmeli
- Mevcut endpoint logic'e DOKUNMA, sadece error handling degistir

## MEVCUT DURUM
Dosya: backend/app/domains/ai/router.py (1342 satir)
- Dosyada zaten `from fastapi import ... status` ve `import logging` ve `_logger = logging.getLogger(__name__)` var
- 16 adet raw HTTPException(500, ...) kullaniliyor
- Bazi except bloklarinda logging yok
- Hata mesajlari tutarsiz (bazen "hatası" bazen "hatasi")

## YAPILACAKLAR

### Adim 1: Dosyanin basina (import blogundan sonra, router tanimından once) error helper ekle:

```python
# ── Structured Error Response ────────────────────────────────────────────
def _ai_error(code: str, message: str, exc: Exception) -> HTTPException:
    """AI endpoint'leri icin standart hata response'u olusturur."""
    _logger.exception("AI endpoint hatasi [%s]: %s", code, message)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"error": code, "message": message, "detail": str(exc)[:300]},
    )
```

### Adim 2: 16 adet raw HTTPException(500, ...) satirini degistir

HER BIRINI bul ve degistir. Asagidaki mapping'i kullan:

| Satir | Eski kod | Yeni kod |
|-------|----------|----------|
| 664 | `raise HTTPException(500, f"AI assertion analizi hatası: {str(e)}")` | `raise _ai_error("AI_ASSERT", "AI assertion analizi hatasi", e)` |
| 773 | `raise HTTPException(500, f"Batch ingest hatasi: {e}")` | `raise _ai_error("AI_INGEST", "Batch ingest hatasi", e)` |
| 811 | `raise HTTPException(500, f"Arama hatasi: {e}")` | `raise _ai_error("AI_SEARCH", "Bilgi deposu arama hatasi", e)` |
| 834 | `raise HTTPException(500, f"Temizleme hatasi: {e}")` | `raise _ai_error("AI_CLEANUP", "Bilgi deposu temizleme hatasi", e)` |
| 889 | `raise HTTPException(500, f"Router stats hatasi: {e}")` | `raise _ai_error("AI_STATS", "Router istatistik hatasi", e)` |
| 931 | `raise HTTPException(500, f"Few-shot stats hatasi: {e}")` | `raise _ai_error("AI_FEWSHOT", "Few-shot istatistik hatasi", e)` |
| 1085 | `raise HTTPException(500, f"QA plan hatasi: {str(e)[:300]}")` | `raise _ai_error("AI_QA_PLAN", "QA plan olusturma hatasi", e)` |
| 1115 | `raise HTTPException(500, f"QA execute hatasi: {str(e)[:300]}")` | `raise _ai_error("AI_QA_EXEC", "QA calistirma hatasi", e)` |
| 1143 | `raise HTTPException(500, f"QA verify hatasi: {str(e)[:300]}")` | `raise _ai_error("AI_QA_VERIFY", "QA dogrulama hatasi", e)` |
| 1168 | `raise HTTPException(500, f"QA full-cycle hatasi: {str(e)[:300]}")` | `raise _ai_error("AI_QA_CYCLE", "QA tam dongu hatasi", e)` |
| 1193 | `raise HTTPException(500, f"QA explore hatasi: {str(e)[:300]}")` | `raise _ai_error("AI_QA_EXPLORE", "QA kesfetme hatasi", e)` |
| 1214 | `raise HTTPException(500, f"QA status hatasi: {str(e)[:300]}")` | `raise _ai_error("AI_QA_STATUS", "QA durum sorgulama hatasi", e)` |
| 1253 | `raise HTTPException(500, f"NL test uretim hatasi: {str(e)[:300]}")` | `raise _ai_error("AI_NL_GEN", "Dogal dil test uretim hatasi", e)` |
| 1284 | `raise HTTPException(500, f"NL batch uretim hatasi: {str(e)[:300]}")` | `raise _ai_error("AI_NL_BATCH", "Toplu test uretim hatasi", e)` |
| 1315 | `raise HTTPException(500, f"NL suggest hatasi: {str(e)[:300]}")` | `raise _ai_error("AI_NL_SUGGEST", "Test onerisi hatasi", e)` |
| 1342 | `raise HTTPException(500, f"Kod dogrulama hatasi: {str(e)[:300]}")` | `raise _ai_error("AI_CODE_VAL", "Kod dogrulama hatasi", e)` |

### Adim 3: Logging olmayan except bloklarina logger ekle

Su satirlardaki except bloklari icerisinde logging YOK — sadece pass veya return var:
- Satir 125: `except Exception:` → icerisine `_logger.debug("...", exc_info=True)` ekle
- Satir 185: `except Exception:` → ayni
- Satir 216: `except Exception:` → ayni
- Satir 258: `except Exception:` → ayni

Bu bloklarda raise yapilmiyor (fire-and-forget), o yuzden sadece debug level log yeterli.

### Adim 4: Dogrulama
Degisiklik sonrasi calistir:
```bash
python3 -c "import ast; ast.parse(open('backend/app/domains/ai/router.py').read()); print('OK')"
```

## ONEMLI
- Endpoint logic'e, request/response schemaya, import'lara DOKUNMA
- Sadece except bloklari ve raise HTTPException(500, ...) satirlarini degistir
- _ai_error helper'i dosyanin basina (router = APIRouter(...) satirindan ONCE) ekle
```
