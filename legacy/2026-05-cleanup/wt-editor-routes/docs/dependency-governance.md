# Dependency ve Sürüm Yönetişimi

Bu doküman, BGTS monorepo'da runtime sürümlerini, bağımlılık güncelleme döngüsünü ve release'e giriş kurallarını tek bir standartta toplar.

## 1) Tek kaynak standart

Operasyonel doğruluk için aşağıdaki kaynaklar birlikte referans alınır:

- `README.md` — geliştirici odaklı kurulum ve günlük komutlar
- `DEPLOYMENT_OPS_GUIDE.md` — staging/production dağıtım ve rollback akışı
- `docs/runtime-hardening-checklist.md` — production benzeri ortam kontratları
- Bu doküman — dependency/sürüm yönetimi politikası

Çelişki görülürse öncelik sırası: `DEPLOYMENT_OPS_GUIDE.md` > `docs/runtime-hardening-checklist.md` > `README.md`.

## 2) Runtime sözleşmeleri

| Katman | Standart |
|-------|----------|
| Python runtime (backend) | `3.12` (Docker/CI parity) |
| Node.js runtime (web) | `20.x` |
| PostgreSQL | `16` |
| Redis | `7` |

Notlar:

- Runtime major sürümleri CI ve deployment akışında birlikte güncellenir.
- Runtime değişikliği tek bir dosyada bırakılmaz; Dockerfile, workflow ve compose dosyaları birlikte revize edilir.

## 3) Bağımlılık güncelleme kuralları

### 3.1 JavaScript (`apps/web`)

- Kilit dosya (`apps/web/package-lock.json`) zorunludur.
- Yeni paket ekleme/çıkarma yalnızca `npm install <paket>` veya `npm uninstall <paket>` ile yapılır.
- Elle `package-lock.json` düzenlenmez.

### 3.2 Python (`backend`, `engine`, `ai-gateway`)

- Doğrudan bağımlılıklar ilgili `requirements*.txt` dosyalarında tutulur.
- Güvenlik veya üretim etkili yükseltmelerde smoke/integration testleri koşulmadan merge yapılmaz.
- Production etkili paketlerde major sürüm atlaması için kısa risk notu PR açıklamasına eklenir.

### 3.3 Container taban imajları

- Base image yükseltmeleri (`python`, `node`, `postgres`, `redis`) release penceresinde planlanır.
- Runtime parity kontrolü için CI `runtime-contracts` işinin yeşil olması zorunludur.

## 4) Güncelleme kadansı

- Otomatik güncelleme PR'ları haftalık açılır (Dependabot).
- Manuel toplu güncelleme penceresi: sprint başına en az 1 kez.
- Kritik güvenlik bildirimi (CVSS yüksek) durumunda normal pencere beklenmeden hotfix süreci uygulanır.

## 5) Merge öncesi minimum kontrol listesi

Bağımlılık/runtime içeren bir PR için:

1. Etkilenen servis(ler) için testler geçti (`pytest` / `npm test` / E2E gerekli ise).
2. `runtime-contracts` ve ana CI işleri başarılı.
3. Değişiklik, `README.md` veya `DEPLOYMENT_OPS_GUIDE.md` üzerinde gerekli notlarla dokümante edildi.
4. Gerekliyse rollback notu PR açıklamasına eklendi.

## 6) Anti-pattern listesi

- `latest` etiketi ile production deploy
- Lock dosyasını güncellemeden `package.json` bağımlılığı değiştirmek
- Sadece lokal ortamda test edip runtime major yükseltmesi merge etmek
- Security advisory içeren paketi "sonraki sprint" gerekçesiyle plansız bırakmak
