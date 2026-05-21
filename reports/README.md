# BGTS Test Raporları

Bu dizin BGTS test koşularının raporlarını ve şablonlarını barındırır.

## Dizin Yapısı

```
reports/
├── README.md                # Bu dosya
├── templates/
│   ├── html_report.html     # Tailwind dark-theme HTML rapor şablonu
│   └── email_report.html    # E-posta uyumlu HTML rapor şablonu
├── bgts_rapor_*.html        # Üretilen HTML raporlar
├── bgts_rapor_*.json        # Üretilen JSON raporlar
├── bgts_rapor_*.csv         # CSV dışa aktarımlar
└── bgts-*-results.json      # CI pipeline sonuç dosyaları
```

## Yerel Rapor Üretme

### 1. Smoke Testleri Çalıştırma ve Rapor Alma

```bash
cd engine
python bgts_runner.py --smoke --report
```

### 2. Regresyon Testleri (Paralel + Retry)

```bash
cd engine
python bgts_runner.py --regression --parallel 4 --retry 2 --report
```

### 3. Belirli Feature Çalıştırma

```bash
cd engine
python bgts_runner.py --feature login --report
```

### 4. Shell Script ile Kolay Kullanım

```bash
# Smoke testleri
./engine/scripts/run_bgts_tests.sh --smoke

# Tam regresyon
./engine/scripts/run_bgts_tests.sh --regression --parallel

# Tarayıcı görünür modda
./engine/scripts/run_bgts_tests.sh --smoke --headed
```

### 5. JSON Çıktı Alma

```bash
cd engine
python bgts_runner.py --all --json-output ../reports/sonuc.json
```

## Allure Raporları

### Ön Koşul

Allure CLI kurulu olmalıdır:

```bash
# macOS
brew install allure

# Linux
sudo apt-get install -y allure

# veya npm ile
npm install -g allure-commandline
```

### Rapor Üretme

```bash
cd engine

# Testleri çalıştır (Allure sonuçları otomatik toplanır)
python bgts_runner.py --smoke

# HTML rapor üret
allure generate allure-results -o allure-report --clean

# Raporu tarayıcıda aç
allure open allure-report

# Veya canlı sunucu başlat
allure serve allure-results
```

### Allure Rapor İçeriği

- **Overview**: Genel başarı/başarısızlık özeti ve trend grafikleri
- **Suites**: Test sınıflarına göre gruplandırılmış sonuçlar
- **Graphs**: Süre dağılımı, durum dağılımı, trend
- **Timeline**: Testlerin zaman çizelgesi
- **Behaviors**: BDD feature/scenario bazında sonuçlar
- **Packages**: Modül bazında kapsam

## CI/CD Rapor Artifact'leri

### GitHub Actions

Her CI koşusunda aşağıdaki artifact'ler üretilir:

| Artifact | İçerik | Saklama Süresi |
|----------|--------|---------------|
| `bgts-smoke-allure` | Smoke Allure sonuçları | 14 gün |
| `bgts-smoke-reports` | Smoke HTML/JSON raporlar | 14 gün |
| `bgts-smoke-screenshots` | Başarısız test ekran görüntüleri | 7 gün |
| `bgts-api-allure` | API test Allure sonuçları | 14 gün |
| `bgts-regression-allure` | Regresyon Allure sonuçları | 30 gün |
| `bgts-regression-reports` | Regresyon HTML/JSON raporlar | 30 gün |
| `bgts-scheduled-*` | Zamanlanmış koşu raporları | 30 gün |

### Artifact İndirme

```bash
# GitHub CLI ile
gh run download <RUN_ID> -n bgts-regression-reports
```

## Bildirim Yapılandırması

### Slack Webhook

1. [Slack API](https://api.slack.com/messaging/webhooks) üzerinden Incoming Webhook oluşturun
2. GitHub repo Settings > Secrets > Actions'a ekleyin:
   - Anahtar: `WEBHOOK_SLACK_URL`
   - Değer: `https://hooks.slack.com/services/T.../B.../...`

### Microsoft Teams Webhook

1. Teams kanalında Incoming Webhook connector ekleyin
2. GitHub repo Settings > Secrets > Actions'a ekleyin:
   - Anahtar: `WEBHOOK_TEAMS_URL`
   - Değer: `https://outlook.office.com/webhook/...`

### Yerel Bildirim

```bash
# Ortam değişkeni olarak ayarlayın
export WEBHOOK_SLACK_URL="https://hooks.slack.com/services/..."

# Testleri çalıştırın — başarısızlıkta otomatik bildirim gider
cd engine
python bgts_runner.py --regression
```

## Rapor Formatları

### HTML Raporu
- Tailwind CSS dark theme
- Türkçe etiketler
- Özet kartları (toplam, başarılı, başarısız, atlanan, süre)
- SVG pasta grafik (başarı/başarısızlık dağılımı)
- Genişletilebilir hata detayları tablosu
- Ortam bilgisi kenar çubuğu
- Duruma göre filtreleme

### JSON Raporu
- Makine tarafından okunabilir
- Ortam bilgisi, test sayıları, süre, hata detayları
- CI/CD entegrasyonu ve trend analizi için uygun

### CSV Raporu
- UTF-8 BOM (Excel uyumluluğu)
- Metrik/değer çiftleri + hata listesi
- Paydaşlarla paylaşım için hazır

### E-posta Raporu
- Satır içi CSS (dış bağımlılık yok)
- Tüm e-posta istemcilerinde düzgün görüntülenir
- Özet tablosu, başarı çubuğu, kritik hatalar listesi
