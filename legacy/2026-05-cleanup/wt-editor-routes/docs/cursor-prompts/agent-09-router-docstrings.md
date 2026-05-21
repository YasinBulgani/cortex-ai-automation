# Agent 9: Router Endpoint Docstring'ler

## Cursor'a yapistir:

```
Sen bir teknik yazar / backend muhendisisin. BGTS bankacilik test otomasyon
platformundaki tum router endpoint'lerine Turkce docstring ekleyeceksin.

## KURALLAR
- Docstring TURKCE olmali (proje dili Turkce)
- Kisa ve ozlu: 1-2 satir
- FastAPI docstring'leri otomatik olarak OpenAPI/Swagger UI'da gorunur
- Mevcut docstring varsa DOKUNMA
- Python 3.9 uyumlu
- Dosyalar ast.parse gecmeli

## FORMAT
```python
@router.get("/endpoint")
async def my_endpoint():
    """Kisa, ozlu Turkce aciklama."""
    ...
```

Eger endpoint karmasiksa 2 satir kullan:
```python
@router.post("/endpoint")
async def my_endpoint():
    """Yeni kayit olusturur.

    Belirtilen proje altinda yeni bir senaryo kaydeder ve ID doner.
    """
    ...
```

## DOCSTRING EKSIK ROUTER'LAR (ONCELIK SIRASI)

### 1. backend/app/domains/artifacts/router.py (28 satir, ~1 endpoint)
- Cok kisa dosya, tum endpoint'lere docstring ekle
- Ornek: "Artifact dosyasini yukler ve depolar."

### 2. backend/app/domains/catalog/router.py (150 satir, ~6 endpoint)
Router'i oku ve su sekilde docstring ekle:
- list_datasets → "Proje veri setlerini listeler."
- create_dataset → "Yeni veri seti olusturur."
- get_dataset → "Belirtilen veri seti detayini getirir."
- update_dataset → "Veri seti bilgilerini gunceller."
- delete_dataset → "Veri setini siler."
- (diger endpoint'ler varsa benzer sekilde)

### 3. backend/app/domains/jobs/router.py (130 satir, ~5 endpoint)
- list_jobs → "Arka plan islerini listeler."
- enqueue_job → "Yeni arka plan isi kuyruga ekler."
- get_job → "Is detayini ve durumunu getirir."
- cancel_job → "Calisma bekleyen isi iptal eder."
- retry_job → "Basarisiz isi yeniden kuyruga ekler."

### 4. backend/app/domains/rules/router.py (85 satir, ~3 endpoint)
- list_rule_sets → "Is kurali setlerini listeler."
- create_rule_set → "Yeni is kurali seti olusturur."
- get_rule_set → "Kural seti detayini getirir."

### 5. backend/app/domains/auth/router.py (409 satir, ~15 endpoint)
- Bu dosyada BAZI endpoint'lerin docstring'i var, bazilarin yok
- Sadece OLMAYANLARA ekle, mevcutlara DOKUNMA
- Ornekler:
  - login → "Kullanici girisi yapar ve JWT token doner." (varsa dokunma)
  - register → "Yeni kullanici kaydeder."
  - refresh_token → "Refresh token ile yeni access token alir."
  - change_password → "Kullanici parolasini degistirir."
  - forgot_password → "Parola sifirlama istegi olusturur."
  - reset_password → "Parola sifirlama tokenı ile yeni parola belirler."
  - me → "Oturumdaki kullanici bilgilerini getirir."
  - update_profile → "Kullanici profil bilgilerini gunceller."

### 6. backend/app/domains/audit/router.py (72 satir, ~1-2 endpoint)
- list_audit_logs → "Denetim izlerini (audit trail) listeler."
- get_audit_log → "Denetim izi detayini getirir."

### 7. backend/app/domains/notifications/router.py (100 satir, ~3 endpoint)
- list_prefs → "Bildirim tercihlerini getirir."
- update_prefs → "Bildirim tercihlerini gunceller."

### 8. backend/app/domains/automation/router.py (59 satir, ~2 endpoint)
- trigger_run → "Otomasyon motorunda test kosusunu baslatir."
- get_status → "Kosu durumunu sorgular."

### 9. backend/app/domains/tspm/router.py (5443 satir, ~148 endpoint) ⚠️ BUYUK
- Bu dosya COK BUYUK — her endpoint'e bakmak cok zaman alir
- STRATEJI: Dosyayi oku, `def ` ile baslayan satirlari bul, docstring OLMAYANLARI tespit et
- SADECE docstring olmayanlara ekle
- Endpoint isimleri genellikle kendini aciklar: create_project, list_scenarios, vb.
- Docstring ornekleri:
  - create_project → "Yeni proje olusturur."
  - list_projects → "Projeleri listeler."
  - get_project → "Proje detayini getirir."
  - update_project → "Proje bilgilerini gunceller."
  - delete_project → "Projeyi siler."
  - create_scenario → "Yeni test senaryosu olusturur."
  - import_scenarios → "Metin veya dosyadan senaryo aktarir."
  - get_dashboard → "Proje ozet istatistiklerini getirir."
  - get_traceability → "Gereksinim-senaryo izlenebilirlik matrisini getirir."
  - create_defect → "Yeni hata kaydi olusturur."
  - bulk_update_status → "Toplu senaryo durum guncellemesi yapar."

## ISLEM SIRASI
1. Her dosyayi sirayla oku
2. Docstring OLMAYAN endpoint'leri bul (fonksiyon tanimından hemen sonra docstring yoksa)
3. 1-2 satirlik Turkce docstring ekle
4. ast.parse ile dogrula
5. Sonraki dosyaya gec

## DOGRULAMA
```bash
python3 -c "
import ast, pathlib
routers = [
    'artifacts', 'catalog', 'jobs', 'rules', 'auth', 'audit',
    'notifications', 'automation', 'tspm'
]
for r in routers:
    path = f'backend/app/domains/{r}/router.py'
    try:
        ast.parse(pathlib.Path(path).read_text())
        print(f'✅ {path}')
    except SyntaxError as e:
        print(f'❌ {path}: {e}')
"
```
```
