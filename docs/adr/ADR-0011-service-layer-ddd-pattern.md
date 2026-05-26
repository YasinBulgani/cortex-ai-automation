# ADR-0011: Service Layer DDD Pattern — HTTP-Agnostic Services

**Tarih:** 2026-05-26  
**Durum:** Kabul Edildi  
**Karar Vericiler:** Yasin Bulgani, Neurex_QA Ekibi

## Bağlam

Backend domain service.py dosyaları, başlangıçta doğrudan `fastapi.HTTPException` 
fırlatıyordu. Bu, iş mantığını HTTP taşıma katmanına bağlıyor ve test edilebilirliği
düşürüyordu.

## Karar

Tüm `service.py` dosyaları **HTTP-agnostic** olmalıdır:
- `HTTPException` yerine `ValueError` (400 → kötü istek) 
- `HTTPException` yerine `KeyError` (404 → bulunamadı)
- `HTTPException` yerine `RuntimeError` (500 → iç hata)

Router katmanı bu hataları yakalar ve uygun HTTP yanıtına çevirir.

## Uygulama

Global exception handler'lar `backend/app/core/exception_handlers.py` içinde:
```python
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(status_code=400, content={"error": str(exc)})

@app.exception_handler(KeyError)
async def key_error_handler(request, exc):
    return JSONResponse(status_code=404, content={"error": str(exc)})
```

## Sonuçlar

- ✅ Service katmanı tam unit testlenebilir (FastAPI TestClient gerekmez)
- ✅ İş mantığı HTTP'den bağımsız (CLI, background task, başka domain çağrısı)
- ✅ Router'lar basitleşir — sadece HTTP haritalama
- ⚠️ Mevcut router'lar try/except güncellenmesini gerektirir

## Uyumluluk

`coverup/service.py` ve `test_management/service.py` Sprint 2026-05-26'da düzeltildi.
Yeni servis dosyaları bu pattern'e uymalıdır.
