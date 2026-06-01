# Test Koşumu Rehberi

## Hızlı Başlangıç

### Backend unit testleri
```bash
cd backend
pytest tests/unit/ -v --tb=short -m "not slow"
```

### Backend integration testleri
```bash
pytest tests/integration/ -v --tb=short
```

### Engine unit testleri
```bash
cd engine
pytest tests/unit/ -v --tb=short
```

### Frontend testleri
```bash
cd apps/web
npm test -- --watchAll=false
```

## Marker Sistemi

| Marker | Açıklama | Koşum |
|---|---|---|
| `unit` | Hızlı, izole testler | Her PR'da |
| `integration` | Backend+DB testleri | Her PR'da |
| `smoke` | Kritik yol testleri | Deploy öncesi |
| `slow` | >5 saniye testler | Nightly |
| `security` | Güvenlik testleri | Her PR'da |
| `asyncio` | Async testler | Her PR'da |

## Import guard pattern

Her test dosyasında:
```python
try:
    from app.domains.X.service import Y
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False
pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")
```

## Test yazma kuralları

1. **Service testleri**: HTTP-agnostic — `ValueError`/`KeyError` test et, `HTTPException` değil
2. **Engine testleri**: Minimal Flask app — sadece test edilen blueprint'i kaydet
3. **Integration testleri**: `TestClient(app, raise_server_exceptions=False)` kullan
4. **Async testleri**: `@pytest.mark.asyncio` + `AsyncMock`

## CI koşumu sırası

1. Lint (ruff, mypy, eslint)
2. Unit testler
3. Integration testler
4. Security scan (semgrep, bandit, safety)
5. Build check (docker build --no-cache)
