# Environment Setup

İlk kez çalıştırıyorsan bu adımları takip et.

## 1. `.env` dosyası

```bash
cp .env.example .env
```

Aç ve doldur:

```bash
# AES anahtari (TAM 16 KARAKTER) - sifreli parolalari acmak icin
CORTEX_AES_KEY=changeMeInProd16

# Cortex test kullanicisi
CORTEX_USERNAME=test_user@example.com
CORTEX_PASSWORD=cortex_password_burada

# DB
DB1_HOST=10.10.0.49
DB1_PORT=1433
DB1_NAME=HCM_Test_Final
DB1_USERNAME=hcmnonprod
DB1_PASSWORD=DB_PAROLASI

# Dashboard
DASHBOARD_PORT=5001
DASHBOARD_HOST=0.0.0.0
```

## 2. Sifreli parolalar (encrypted)

`enter encrypted password alias` step'i çalışsın diye lokal `password.properties` üret:

```bash
mvn test -Dcucumber.features=src/test/resources/scratch/password.feature \
  -Dcucumber.filter.tags="not @skip"
```

Veya manuel olarak feature yaz:

```gherkin
Feature: Setup encrypted passwords

  Scenario: Cortex kullanici sifresini sakla
    * I encrypt password "${ENV:CORTEX_PASSWORD}" and save as alias "cortexUser" with overwrite
    * I encrypt password "${ENV:DB1_PASSWORD}" and save as alias "db1" with overwrite
```

Çalıştır:
```bash
mvn test -Dcucumber.features=path/to/setup.feature
```

Sonuç `src/main/resources/password.properties` dosyasına yazılır (git'e gitmez).

## 3. Feature dosyasında env kullanımı

Write/type step'leri otomatik resolve eder:

```gherkin
When I write "${ENV:CORTEX_USERNAME}" into "userNameInput"
When I write "${ENV:CORTEX_USERNAME:fallback_user}" into "userNameInput"
```

## 4. Çözüm sırası

Her config değeri şu sıra ile çözülür:

```
1. -Dkey=value          (komut satırı veya IntelliJ VM options)
2. OS environment       (UPPER_SNAKE_CASE: cortex.url → CORTEX_URL)
3. .env dosyası         (proje kökü)
4. config.properties    (varsayılan)
```

## 5. CI ortamında

GitHub Actions secret olarak ekle:

```
Repository → Settings → Secrets → Actions:
  CORTEX_AES_KEY
  CORTEX_USERNAME
  CORTEX_PASSWORD
  DB1_PASSWORD
```

Workflow `secrets.CORTEX_AES_KEY` formatında env'e geçirir (bkz. [.github/workflows/ci.yml](../.github/workflows/ci.yml)).
