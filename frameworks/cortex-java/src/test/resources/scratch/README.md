# Scratch features

Bu klasör dev-amaçlı / one-shot feature dosyalarını içerir.
**TestRunner taramaz** — `@manual` tag'i ile filtrelenir.

## Dosyalar

| Dosya | Amaç |
|---|---|
| `setup-password.feature` | İlk kurulumda Cortex test-user + DB şifresini AES ile şifreleyip `password.properties`'e yaz |

## Kullanım

```bash
# 1. .env oluştur
./scripts/setup-env.sh

# 2. .env'i düzenle: CORTEX_USERNAME, CORTEX_PASSWORD, DB1_PASSWORD doldur
$EDITOR .env

# 3. Şifreli alias'ları kaydet (bir kez)
./mvnw test \
  -Dcucumber.features=src/test/resources/scratch/setup-password.feature \
  -Dcucumber.filter.tags="@setup"

# 4. password.properties oluştu mu kontrol et
ls src/main/resources/password.properties

# 5. Artık smoke run yapılabilir
./scripts/cortex smoke
```
