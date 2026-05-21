# Contributing

## Dil politikası (zorunlu)

| Katman | Dil |
|---|---|
| Java/Python kod (yorumlar, log, exception text) | **İngilizce** |
| Step phrase'leri, locator key'ler, tag'ler, dosya adları | **İngilizce** |
| Test verisi (UI input/expected string'leri) | **Türkçe** (Cortex UI ile eşleş) |
| README, CHANGELOG, docs/, recorder.properties yorumları | **Türkçe** (takım için) |
| Commit mesajları | **İngilizce** (Conventional Commits) |
| Scenario açıklamaları (Gherkin başlık) | **Türkçe** (`Geçerli kullanıcı girişi`) |
| Exception mesajı `throw new ...("...")` | **İngilizce** (grep + Sentry uyumlu) |

**Neden:** Türkçe karakter (`ı, ş, ğ`) Java identifier'da yasak, encoding sorunlu. ASCII-Türkçe (`cikis`) iki dünyanın en kötüsü (ne grep edilebilir ne okunabilir). Kod tabanı tek dilde tutulduğunda IDE, AI tooling, contributor onboarding hızlanır.

**Yeni dosya eklerken kontrol et:**
- `.java` / `.py` içinde yorumlar EN
- Log mesajları EN (`log.info("Browser launched")` değil `log.info("Tarayici acildi")`)
- Exception text EN
- Feature dosya **adı** EN (`login.feature`, `login-validation.feature`)
- Scenario **başlığı** TR olabilir (`Scenario: Geçerli kullanıcı girisi`)
- Locator **key**'i EN camelCase (`loginButton`, `userNameInput`)
- Locator **value**'su domain'e göre (`//button[normalize-space()='Giriş Yap']` — Türkçe UI ile eşleş)

## Branch stratejisi

```
main             korumalı, sadece review'lu PR merge
 │
 ├── develop     entegrasyon branch (bir sonraki sürüm)
 │
 ├── feature/<isim>     yeni özellik
 ├── fix/<isim>         bug fix
 └── chore/<isim>       refactor/temizlik
```

## Commit mesajı

Convention: [Conventional Commits](https://www.conventionalcommits.org/).

```
feat(playwright): add parallel runner with 4 thread default
fix(driver): remove clearDriverCache that slows every test
chore(deps): bump selenium-devtools to v131
docs(readme): add cortex env setup section
```

Tip prefix'leri: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`, `build`.

## Yeni feature/test eklerken

1. Branch aç: `git checkout -b feature/cortex-yeni-akis`
2. Feature dosyası: `src/test/resources/cortex/<isim>.feature`
3. Locator JSON: `src/main/resources/locators/cortex_<isim>.json`
4. Step phrase ekleyeceksen **hem** Selenium hem Playwright tarafına ekle:
   - `src/test/java/stepdefs/<X>Steps.java`
   - `src/test/java/playwright/stepdefs/PwExtraSteps.java`
5. Lokal koşum:
   ```bash
   mvn test -Dcucumber.features=src/test/resources/cortex/<isim>.feature
   mvn -Pplaywright test -Dcucumber.features=src/test/resources/cortex/<isim>.feature
   ```
6. PR aç (CI yeşil olmalı).

## Locator naming kuralları

| Tip | Örnek |
|---|---|
| Input field | `userNameInput`, `emailInput`, `passwordInput` |
| Button | `loginButton`, `submitButton`, `cancelButton` |
| Link | `forgotPasswordLink`, `signupLink` |
| Container | `loginContainer`, `errorContainer` |
| Error/Alert | `loginErrorMessage`, `validationAlert` |
| Modal | `confirmModal`, `infoModal` |

camelCase, Türkçe karakter yok (recorder bunu otomatik yapıyor).

## Recorder ile yeni feature kaydı

```cmd
IntelliJ Run > Recorder
   → Chromium açılır
   → cortex'i gez, sağ-alt toolbar
   → "Durdur ve Kaydet"
   → src/test/resources/recordings/recorded_*.feature
```

Sonra dosyayı `recordings/`'ten resmi klasöre taşı, locator JSON adını feature adı ile aynı yap, gerekirse step phrase'leri inceleyip rename et.

## Code style

- Java: Maven `pom.xml` `maven.compiler.source=17`, IntelliJ default formatter
- Python: PEP 8, `black --line-length 100`
- Yorumlar mümkün olduğunca İngilizce (Türkçe karakter encoding sorunlarını önler)

## Güvenlik

- `password.properties`, `.env`, `*.key` **asla** commit edilmez (`.gitignore`)
- Yeni hassas alan eklerken `${ENV:VAR}` placeholder ile config'e koy
- AES anahtarı rotasyonu için [scripts/scrub-git-history.sh](scripts/scrub-git-history.sh)
