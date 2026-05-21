# Birebir Tekrarlar — İlk Dalga

Tarih: 2026-04-10

## 1. Birebir Kopya Dizinler

### `backend/banking-data` ve `synthetic-data/banking`

- Durum: birebir aynı içerik
- Kanıt:
  - `diff -rq backend/banking-data synthetic-data/banking` boş döndü
  - `app/main.py` birebir aynı
  - `frontend/package.json` birebir aynı
- Boyut:
  - `backend/banking-data`: `335M`
  - `synthetic-data/banking`: `335M`
- Öneri:
  - Tek bir kanonik kaynak bırak
  - Diğerini arşivle veya sil

### `backend/synthetic-data-v4` ve `synthetic-data/platform-v4`

- Durum: aynı kaynak ağacı
- Kanıt:
  - `diff -rq` çıktısında sadece bunlar farklı:
    - `backend/synthetic-data-v4/synthetic_data.log`
    - `backend/synthetic-data-v4/venv_v4`
- Boyut:
  - `backend/synthetic-data-v4`: `9.1M`
  - `synthetic-data/platform-v4`: `304K`
- Öneri:
  - Kanonik kaynak olarak `synthetic-data/platform-v4` bırakmak daha temiz görünüyor
  - `backend/synthetic-data-v4` içindeki local log/venv temizlenebilir veya tamamen kaldırılabilir

## 2. Birebir Kopya Dosyalar

### `engine/scripts/scaffold_project.py` ve `engine/scripts/legacy/scaffold_project.py`

- Durum: birebir aynı dosya
- Kanıt:
  - `cmp -s` başarılı
  - SHA1:
    - `87f0495ec28470d51ee11e189a4ddcdb2999192d`
    - `87f0495ec28470d51ee11e189a4ddcdb2999192d`
- Öneri:
  - `legacy/` altındaki kopya kaldırılabilir

## 3. Fiilen Boş / Kaynak Kodu Olmayan Klasörler

### `ai-test-pipeline`

- Durum: gerçek kaynak yok
- İçerik:
  - `ai-test-pipeline/app/__pycache__/config.cpython-310.pyc`
  - `ai-test-pipeline/app/__pycache__/main.cpython-310.pyc`
- Boyut: `120K`
- Öneri:
  - Güçlü silme adayı

### `test-automation-workspace`

- Durum: boş
- İçerik:
  - `test-automation-workspace/.DS_Store`
- Boyut: `8.0K`
- Öneri:
  - Güçlü silme adayı

## 4. Başlama Sırası

En güvenli ilk dalga:

1. `test-automation-workspace`
2. `ai-test-pipeline`
3. `engine/scripts/legacy/scaffold_project.py`
4. `backend/synthetic-data-v4` veya `synthetic-data/platform-v4` içinden kanonik olmayan taraf
5. `backend/banking-data` veya `synthetic-data/banking` içinden kanonik olmayan taraf

## 5. Not

Son iki madde yüksek disk kazancı sağlar ama hangisinin kalacağına karar verilmeden silinmemeli.

