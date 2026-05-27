# Semgrep Secrets Runbook

Son güncelleme: 2026-05-24

Bu runbook, Cortex_Ai_Automation projesinde Semgrep SAST taramasının nasıl çalıştığını, gerekli CI secret'larının nasıl tanımlandığını ve tarama bulgularının nasıl yorumlanıp yönetildiğini belgelemektedir.

---

## 1. Semgrep Nedir ve Neden Kullanıyoruz?

Semgrep, kaynak kodunu soyut sözdizim ağacı (AST) üzerinde kural tabanlı örüntü eşleştirmeyle analiz eden açık kaynaklı bir statik analiz (SAST) aracıdır. Regex tabanlı araçlardan farklı olarak kod yapısını anlar ve false positive oranını düşürür.

Cortex_Ai_Automation'da Semgrep şu amaçlarla kullanılır:

- **OWASP Top 10 zafiyetlerini** branch merge öncesinde otomatik olarak tespit etmek
- **Hardcoded secret ve kimlik bilgilerini** (`p/secrets` kural seti) kod tabanına girmeden yakalamak
- **Python ve TypeScript/JavaScript** kodundaki güvensiz desenleri (SQL injection, path traversal, eval kullanımı vb.) işaretlemek
- Bulgular SARIF formatında GitHub Security sekmesine beslenerek merkezi güvenlik görünürlüğü sağlamak

Semgrep, `security.yml` workflow'unda CI gate olarak çalışır. `continue-on-error` kaldırılmıştır; kritik bulgu tespit edildiğinde pipeline fail olur.

---

## 2. GitHub Secrets

### Gerekli ve Opsiyonel Secret'lar

| Secret Adı | Zorunluluk | Açıklama |
|---|---|---|
| `SEMGREP_APP_TOKEN` | Opsiyonel (önerilen) | Semgrep Cloud Dashboard entegrasyonu için |
| `GITHUB_TOKEN` | Otomatik | GitHub Actions tarafından otomatik sağlanır, ek kurulum gerekmez |
| `SLACK_WEBHOOK_URL` | Opsiyonel | `scripts/ci/notify.sh` üzerinden Slack bildirimleri için |

Jenkins credential'ları bu belgede yer almaz; bkz. `docs/jenkins-setup.md`.

### `SEMGREP_APP_TOKEN` Nasıl Alınır?

1. [semgrep.app](https://semgrep.app) adresine gidin ve GitHub hesabınızla oturum açın.
2. Sol menüden **Settings → Tokens** seçin.
3. **Create new token** butonuna tıklayın.
4. Token adı olarak `cortex-ai-automation-ci` gibi tanımlayıcı bir isim girin.
5. Oluşturulan token değerini kopyalayın.

### Token'ı GitHub'a Tanımlama

1. Repoda **Settings → Secrets and variables → Actions** sayfasını açın.
2. **New repository secret** butonuna tıklayın.
3. Name: `SEMGREP_APP_TOKEN`
4. Secret: Kopyalanan token değerini yapıştırın.
5. **Add secret** ile kaydedin.

Token tanımlanmamışsa Semgrep, OSS yerel modda çalışmaya devam eder. Cloud dashboard'a sonuç gönderilmez, CI taraması normal şekilde gerçekleşir.

### `SLACK_WEBHOOK_URL` Nasıl Alınır?

1. Slack workspace yöneticisinden **Incoming Webhooks** app'ini etkinleştirmesini isteyin.
2. Hedef kanalı seçin ve webhook URL'ini kopyalayın.
3. GitHub'a `SLACK_WEBHOOK_URL` adıyla yukarıdaki adımlarla aynı şekilde ekleyin.

Tanımlanmamışsa `notify.sh` sessizce atlar, pipeline hata vermez.

---

## 3. Semgrep'i Lokal Çalıştırma

### Kurulum

```bash
pip install semgrep
```

Mevcut semgrep versiyonunu doğrulamak için:

```bash
semgrep --version
```

### Tam Tarama (CI ile Eşdeğer)

```bash
semgrep \
  --config p/owasp-top-ten \
  --config p/javascript \
  --config p/typescript \
  --config p/python \
  --config p/secrets \
  .
```

### SARIF Çıktısı Üretme

```bash
semgrep \
  --config p/owasp-top-ten \
  --config p/javascript \
  --config p/typescript \
  --config p/python \
  --config p/secrets \
  --sarif \
  --output semgrep.sarif \
  .
```

### Yalnızca Belirli Bir Dizini Tarama

```bash
semgrep --config p/python backend/
semgrep --config p/typescript apps/web/
```

### Yalnızca Belirli Bir Kural Setini Tarama

```bash
# Sadece secret taraması
semgrep --config p/secrets .

# Sadece OWASP Top 10
semgrep --config p/owasp-top-ten .
```

### Değişen Dosyaları Tarama (PR Simülasyonu)

```bash
git diff --name-only origin/main | xargs semgrep --config p/secrets --config p/python
```

---

## 4. Semgrep Bulgularını Yorumlama

### Çıktı Formatı

Semgrep terminale şu formatta çıktı verir:

```
backend/api/auth.py
   severity: ERROR   rule: python.flask.security.audit.hardcoded-secret
   21┆  SECRET_KEY = "hardcoded-value"
   ...
   Details: A hardcoded secret was found.
```

### Önem Seviyeleri

| Seviye | Anlam | Varsayılan Davranış |
|---|---|---|
| `ERROR` | Kritik güvenlik bulgusu | CI'ı fail eder |
| `WARNING` | Dikkat gerektiren sorun | Loglanır, CI'ı bloklamaz |
| `INFO` | Bilgilendirme niteliğinde | Loglanır, eylem gerektirmez |

### Kural Setleri ve Kapsamları

| Kural Seti | Dil/Alan | Neleri Yakalar |
|---|---|---|
| `p/owasp-top-ten` | Tüm diller | Injection, broken auth, XSS, IDOR vb. |
| `p/python` | Python | eval, pickle, subprocess güvensiz kullanım, SQL injection |
| `p/typescript` | TypeScript / JavaScript | Prototip kirliliği, eval, DOM-based XSS |
| `p/javascript` | JavaScript | Node.js güvensiz API'leri, açık bağlantı noktaları |
| `p/secrets` | Tüm diller | API key, token, parola, private key hardcode |

### Örnek Gerçek Bulgular

```
# Hardcoded secret — p/secrets tarafından yakalanır
DB_PASSWORD = "admin123"

# SQL Injection — p/python tarafından yakalanır
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# eval kullanımı — p/python tarafından yakalanır
eval(request.get_json()["expression"])
```

---

## 5. False Positive Bastırma

Semgrep'in hatalı pozitif olarak işaretlediği bir bulgu gerçekten güvenli ise satır içi `# nosemgrep` açıklamasıyla bastırılabilir.

### Tek Satır Bastırma

```python
# Güvenli: bu değer test fixture'ı, production sırrı değil
TEST_TOKEN = "dummy-token-for-unit-tests"  # nosemgrep: python.secrets.hardcoded-token
```

### Kural ID Olmadan Genel Bastırma (Önerilmez)

```python
value = eval(expr)  # nosemgrep
```

Kural ID belirtilmeden kullanım o satırda tüm Semgrep kurallarını devre dışı bırakır. Kötüye kullanımı önlemek için her zaman kural ID ile kullanın.

### Bir Dosya veya Dizini Yok Sayma

`.semgrepignore` dosyası oluşturun (`.gitignore` sözdizimiyle):

```
# .semgrepignore
tests/fixtures/
scripts/seed_data/
docs/
*.test.ts
```

### Bastırma Kararlarını Kaydetme

Her `# nosemgrep` açıklaması PR açıklamasında veya ilgili ticket'ta şu bilgilerle belgelenmeli:

- Bastırılan kural ID
- Neden false positive olduğunun gerekçesi
- Onaylayan kişi ve tarih

---

## 6. SARIF Çıktısı ve GitHub Security Sekmesi

### SARIF Nedir?

SARIF (Static Analysis Results Interchange Format), statik analiz araçlarının bulgularını standart JSON formatında ifade ettiği bir şemadır. GitHub Code Scanning, SARIF dosyalarını okuyarak bulguları **Security → Code Scanning** sekmesinde görüntüler.

### Workflow'da SARIF Akışı

`security.yml` içindeki Semgrep job'u iki adımda çalışır:

```yaml
- name: Run Semgrep
  uses: semgrep/semgrep-action@v1
  with:
    config: >-
      p/python
      p/typescript
      p/owasp-top-ten
      p/secrets
    auditOn: push
    generateSarif: "1"
  env:
    SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_APP_TOKEN }}

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: semgrep.sarif
  continue-on-error: true
```

`generateSarif: "1"` parametresi `semgrep.sarif` dosyasını üretir. `upload-sarif` adımı `if: always()` ile çalışır — tarama fail etse bile SARIF yüklenir.

SARIF yükleme başarısız olsa bile (`continue-on-error: true`) tarama sonucu yetkilidir; CI durumu değişmez.

### GitHub Security Sekmesini Kullanma

1. Repo'da **Security → Code Scanning** sayfasını açın.
2. Her bulgu için detaylar, etkilenen dosya, satır numarası ve kural açıklaması görüntülenir.
3. Bulguyu inceledikten sonra **Dismiss alert** ile kapatabilir ve gerekçe belirtebilirsiniz.
4. Kapatma kararları audit trail'e kaydedilir.

### Semgrep Cloud Dashboard

`SEMGREP_APP_TOKEN` tanımlandıysa bulgular ayrıca [semgrep.app](https://semgrep.app) üzerinde de görüntülenebilir. Dashboard'da:

- Trend analizi (hangi kural ne kadar sıklıkla tetikleniyor)
- Geçmişe yönelik karşılaştırma
- Ekip genelinde yönetim arayüzü

---

## 7. Semgrep CI'ı Blokladığında Eskalasyon

### Hızlı Triage Adımları

1. GitHub Actions logunda fail eden Semgrep adımına tıklayın.
2. Bulgunun önem seviyesini (`ERROR` / `WARNING`) ve kural ID'sini not edin.
3. İşaretlenen kodu kural dokümantasyonuyla karşılaştırın:
   ```bash
   semgrep --config <rule-id> --verbose <dosya>
   ```

### Seçenek A — Gerçek Güvenlik Bulgusu

Bulgu gerçek bir açıksa düzeltme yapılmalıdır. Düzeltme tamamlanmadan PR merge edilmemelidir.

```
Sorumlu: geliştirici
Süre: aynı sprint içinde
Eskalasyon: QA lead ve güvenlik sorumlusuna bildirin
```

### Seçenek B — False Positive

1. Kural dokümantasyonunu ve bağlamı inceleyin.
2. False positive olduğuna emin olun.
3. Satır başına `# nosemgrep: <rule-id>` ekleyin.
4. PR açıklamasına gerekçeyi yazın.
5. En az bir takım üyesinin onayından sonra merge edin.

### Seçenek C — Acil Hotfix (Geçici Bypass)

Kritik bir production hotfix'i Semgrep'e takılıyorsa ve gerçek güvenlik riski yoksa:

1. `security.yml` içindeki Semgrep job'una geçici olarak `continue-on-error: true` ekleyin.
2. Bu değişikliği ayrı bir commit ile kaydedin; commit mesajı `temp: semgrep bypass for hotfix <ticket-id>` formatında olmalıdır.
3. Hotfix merge edildikten sonra `continue-on-error` kaldırılmalı ve false positive düzeltilmelidir.
4. Bypass süresi en fazla **24 saat** olmalıdır.

```
Bypass kararını: güvenlik sorumlusu veya tech lead onaylamalıdır
Ticket açın: açık bulguyu takip etmek için
```

### Seçenek D — Semgrep Altyapı Hatası

Semgrep'in kendi altyapısından (ağ hatası, action versiyonu) kaynaklanan hata:

```bash
# Semgrep action versiyonunu pin'lenmiş SHA ile sabitleyin
uses: semgrep/semgrep-action@<SHA>
```

Geçici çözüm olarak lokal tarama çalıştırıp çıktıyı artefakt olarak yükleyin:

```bash
semgrep --config p/owasp-top-ten --config p/secrets --sarif --output semgrep.sarif .
```

---

## 8. CI Secret'larının Özeti

| Secret | Kaynak | Zorunluluk | Etki Alanı |
|---|---|---|---|
| `SEMGREP_APP_TOKEN` | semgrep.app → Settings → Tokens | Opsiyonel | Semgrep Cloud Dashboard'a sonuç gönderimi |
| `GITHUB_TOKEN` | GitHub Actions otomatik | Otomatik | PR yorum, SARIF yükleme, gitleaks |
| `SLACK_WEBHOOK_URL` | Slack workspace admin | Opsiyonel | `notify.sh` Slack bildirimleri |

Jenkins credential'ları için bkz. `docs/jenkins-setup.md`.

---

## 9. Sık Karşılaşılan Hatalar

### `Error: SEMGREP_APP_TOKEN is not set`

Bu bir hata değildir. Semgrep OSS modda çalışmaya devam eder. Cloud dashboard entegrasyonu için token eklenebilir.

### `semgrep.sarif not found`

`generateSarif: "1"` parametresini doğrulayın. SARIF upload adımı `if: always()` ile çalışmalıdır, aksi hâlde tarama fail ettiğinde dosya oluşturulmaz.

### `permissions: security-events: write` eksik

SARIF upload için `security-events: write` izni gereklidir. `security.yml` dosyasında job seviyesinde tanımlı olduğunu doğrulayın:

```yaml
permissions:
  security-events: write
```

### Çok Fazla False Positive

Kural setini daraltın ve `.semgrepignore` ile test dizinlerini hariç tutun. Tüm kural setlerini aynı anda kullanmak ilk kurulumda gürültü yaratabilir; kural setlerini aşamalı olarak ekleyin.

---

## İlgili Belgeler

- `docs/jenkins-setup.md` — Jenkins pipeline ve credential kurulumu
- `docs/runtime-hardening-checklist.md` — Production güvenlik kontrol listesi
- `.github/workflows/security.yml` — Tam güvenlik workflow tanımı
- [semgrep.app/docs](https://semgrep.dev/docs/) — Resmi Semgrep dokümantasyonu
- [github.com/semgrep/semgrep-rules](https://github.com/semgrep/semgrep-rules) — Açık kural deposu
