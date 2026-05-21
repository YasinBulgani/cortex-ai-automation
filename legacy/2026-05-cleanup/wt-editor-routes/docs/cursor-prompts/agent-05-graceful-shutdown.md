# Agent 5: Graceful Shutdown & Lifecycle Tamamlama

## Cursor'a yapistir:

```
Sen bir backend muhendisisin. BGTS bankacilik test otomasyon platformunun
graceful shutdown mekanizmasini tamamlayacaksin.

## KURALLAR
- Python 3.9 uyumlu
- Tum dosyalar ast.parse gecmeli
- Shutdown sirasinda hic bir exception kullaniciya yansimamali
- Her kaynak kapatma islemi timeout ile sarili olmali

## MEVCUT DURUM

### backend/app/main.py — lifespan fonksiyonu
Mevcut lifespan (satir ~155-175 civari) su sekilde:

```python
@asynccontextmanager
async def lifespan(app):
    # startup
    start_scheduler()
    try:
        _start_banking_scheduler()
    except Exception:
        pass
    try:
        from app.domains.ai.file_watcher import start_file_watcher
        start_file_watcher()
    except Exception:
        pass

    yield

    # shutdown
    try:
        from app.domains.ai.file_watcher import stop_file_watcher
        stop_file_watcher()
    except Exception:
        pass
    shutdown_scheduler()
```

### SORUNLAR
1. Banking scheduler start ediliyor ama STOP edilmiyor
2. Playwright browser sessions kapatilmiyor (bellekte browser process'leri kalir)
3. Redis connection pool kapatilmiyor
4. Async LLM client'lar kapatilmiyor
5. Shutdown siralama onemli: once consumer'lar, sonra producer'lar, sonra connection pool'lar

## YAPILACAKLAR

### Adim 1: main.py lifespan fonksiyonunu guncelle

Mevcut shutdown blogunu su sekilde genislet:

```python
    yield

    # ── Graceful Shutdown ────────────────────────────────────────────
    _logger.info("BGTS Backend kapatiliyor...")

    # 1. Playwright browser sessions kapat (acik browser process'leri durdur)
    try:
        from app.domains.playwright_mcp.browser_manager import get_browser_manager
        bm = get_browser_manager()
        await asyncio.wait_for(bm.shutdown(), timeout=5.0)
        _logger.info("Playwright sessions kapatildi")
    except Exception:
        _logger.debug("Playwright shutdown atlandi", exc_info=True)

    # 2. File watcher durdur
    try:
        from app.domains.ai.file_watcher import stop_file_watcher
        stop_file_watcher()
    except Exception:
        _logger.debug("File watcher shutdown atlandi", exc_info=True)

    # 3. Banking scheduler durdur
    try:
        from app.domains.tspm.banking_scheduler import stop_banking_scheduler
        stop_banking_scheduler()
        _logger.info("Banking scheduler durduruldu")
    except ImportError:
        pass
    except Exception:
        _logger.debug("Banking scheduler shutdown atlandi", exc_info=True)

    # 4. Ana scheduler durdur
    try:
        shutdown_scheduler()
    except Exception:
        _logger.debug("Scheduler shutdown atlandi", exc_info=True)

    # 5. Async LLM client'lari kapat
    try:
        from app.domains.ai.service import _async_openai_client, _async_anthropic_client
        if _async_openai_client is not None:
            await _async_openai_client.close()
        if _async_anthropic_client is not None:
            await _async_anthropic_client.close()
    except Exception:
        _logger.debug("LLM client shutdown atlandi", exc_info=True)

    _logger.info("BGTS Backend kapatildi")
```

### Adim 2: asyncio import'u ekle (yoksa)
main.py'in basina `import asyncio` ekle (zaten varsa dokunma)

### Adim 3: Banking scheduler stop fonksiyonu

`backend/app/domains/tspm/` altinda banking scheduler'i bul:
```bash
grep -rn "banking_scheduler\|BankingScheduler\|start_banking" backend/app/domains/tspm/
grep -rn "_start_banking_scheduler" backend/app/main.py
```

Bu fonksiyonun tanimlandigi dosyayi bul. Oraya `stop_banking_scheduler()` fonksiyonu ekle:
```python
def stop_banking_scheduler():
    """Banking scheduler'i durdurur."""
    global _scheduler  # veya ne isimle tanimlanmissa
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _logger.info("Banking scheduler durduruldu")
```

Eger banking scheduler APScheduler kullaniyorsa `.shutdown(wait=False)` yeterli.
Eger threading.Timer kullaniyorsa `.cancel()` cagir.

### Adim 4: browser_manager.py shutdown kontrol

`backend/app/domains/playwright_mcp/browser_manager.py` dosyasindaki `shutdown()` metodunu kontrol et.
- Zaten `async def shutdown()` var mi? Varsa dokunma.
- Yoksa ekle:
```python
async def shutdown(self):
    """Tum acik browser session'larini kapat."""
    for session_id in list(self._sessions.keys()):
        try:
            await self.close_session(session_id)
        except Exception:
            pass
```

## DOGRULAMA
```bash
python3 -c "import ast; ast.parse(open('backend/app/main.py').read()); print('OK')"
```
```
