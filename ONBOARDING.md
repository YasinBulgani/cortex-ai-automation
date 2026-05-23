# Cortex Automation — Onboarding

**Hedef:** Yeni gelen bir QA testçi veya developer'ın 30 dakika içinde sistemi ayağa kaldırıp ilk testini koşturması.

Bu rehber adım adım, her adımın **beklenen çıktısı** ve **yaygın hata + çözümü** ile birlikte.

---

## 1. Önkoşullar (15 dk)

Aşağıdaki yazılımları kurulu olmalı. Sürüm kontrolü için her satırı çalıştır:

```bash
java --version        # JDK 17+
node --version        # 20+
python3 --version     # 3.10+
mvn --version         # 3.9+ (veya repo'daki ./mvnw kullanılır)
ollama --version      # 0.5+
```

Eksikse macOS'ta Homebrew ile:
```bash
brew install openjdk@17 node@20 python@3.12 maven ollama
```

**Ollama modelini indir** (~10 GB, internet hızına bağlı 5-15 dk):
```bash
ollama pull qwen2.5:14b
```

> ⚠ Sistem RAM'i ≥16 GB olmalı. qwen2.5:14b çalışırken ~9 GB tüketir. RAM düşükse `qwen2.5:7b` veya `llama3.1:8b` kullan.

**Beklenen çıktı:**
```
$ ollama list
NAME             SIZE
qwen2.5:14b      9.0 GB
```

---

## 2. Repo Kurulumu (3 dk)

```bash
cd ~/Desktop
git clone <REPO_URL> Cortex_Ai_Automation
cd Cortex_Ai_Automation
```

**Bağımlılıkları yükle:**
```bash
make cortex-install      # Playwright Chromium indirir (~150 MB)
cd apps/web && npm install && cd ../..   # Next.js bağımlılıkları
pip3 install -r requirements.txt 2>/dev/null || pip3 install flask gunicorn  # Flask için
```

> ⚠ Hata: `mvn: command not found` → Repo içinde `./mvnw` (Maven wrapper) var, `make cortex-install` onu kullanır. Sadece sistem `mvn` lazım olursa `brew install maven`.

---

## 3. Servisleri Başlat (2 dk)

Sistem **4 ayrı servise** ihtiyaç duyar. Hepsini tek komutla:

```bash
make cortex-up
```

Bu komut şunları başlatır:
- **Ollama** (background, port 11434) — AI Polish için
- **Flask API** (background, port 5001) — Dashboard backend
- **Next.js Dashboard** (background, port 3000) — Web UI
- **Java Recorder JVM** ihtiyaç oldukça Dashboard tarafından spawn edilir

**Beklenen çıktı:**
```
✓ Ollama 11434
✓ Flask 5001
✓ Next.js 3000
Dashboard: http://localhost:3000/products/intelligence
```

> ⚠ Port çakışması: Mevcut bir servis varsa `make cortex-down` ile kapat, sonra `cortex-up` çalıştır.

**Durum kontrolü** (her zaman çalıştırabilirsin):
```bash
make cortex-status
```

---

## 4. İlk Kaydını Al (5 dk)

1. Tarayıcıda aç: **http://localhost:3000/products/intelligence**
2. **"+ Yeni Cortex Senaryosu"** butonuna bas
3. Modal'da:
   - **Hedef URL:** `https://cortex-test.bgtsai.com/login`
   - **Feature dosya adı:** `ilk_test` (opsiyonel ama tavsiye edilir)
   - **Kayıt motoru:** **🤖 Playwright Codegen** seç (daha sağlam)
4. **🎬 Recorder'ı Başlat**'a bas — 20-40 saniye Maven derleme + Playwright Chromium spawn
5. Yeni açılan Chromium'da senaryonu gez (login, sayfada gezin, formları doldur)
6. İşin bittiğinde **⏹ Durdur ve Kaydet** (dashboard'da)

**Beklenen sonuç:**
- Modal'da "Kayıt tamamlandı" mesajı
- Üretilen dosya: `frameworks/cortex-java/src/test/resources/recordings/ilk_test.feature`
- Locator dosya: `recordings/locators/ilk_test.json`

> ⚠ "0 aksiyon yakalandı" → Yanlış pencerede çalışıyorsun. `[REC]` başlıklı ve üstte yeşil bar olan Chromium pencerede işlem yapmalısın. Normal Chrome'unda yaptıkların kayıt OLMAZ.

---

## 5. Kaydını Çalıştır (1 dk)

```bash
make cortex-feature FEATURE=src/test/resources/recordings/ilk_test.feature
```

Veya doğrudan:
```bash
cd frameworks/cortex-java
./scripts/cortex feature src/test/resources/recordings/ilk_test.feature
```

**Beklenen çıktı:**
```
1 Scenarios (1 passed)
N Steps (N passed)
Total time:  6.9 s
```

> ⚠ "Locator missing: xxx" → Recorder kayıtta site selector'ı stabil değil. Kayıt tekrar al veya locator JSON'unu manuel düzelt.

---

## 6. AI Polish (Opsiyonel)

Üretilen `.feature` insan-okunabilir hale gelmesi için Ollama'ya yollanabilir:

1. Dashboard'da modal'ı aç (idle state)
2. **"🪄 AI Polish Son Kayıt"** butonuna bas
3. 30-70 saniye bekle (Ollama qwen2.5:14b düşünüyor)
4. Diff modal açılır: sol eski, sağ AI temizlenmiş
5. **✓ Kabul Et & Kaydet** — `.feature` üzerine yazılır

Polish şunları yapar:
- "Scenario: Recorded - 22.05.2026" → "Scenario: BGTS Login Akışı"
- Her step üstüne Türkçe açıklayıcı yorum
- Senaryo sonuna doğrulama önerisi: `# ÖNERİ: Then I see "..."`

---

## 7. Servisleri Durdur

```bash
make cortex-down
```

Bu komut:
- Tüm orphan Java JVM'leri öldürür
- Flask, Next.js, Ollama'yı durdurur
- Tarayıcı pencerelerini kapatır

---

## 8. Sık Karşılaşılan Sorunlar

### "make cortex-up" çalışıyor ama dashboard açılmıyor
```bash
make cortex-status   # Her servisin durumunu gör
```
Eksik servisi tek tek başlat:
```bash
# Ollama
nohup ollama serve > /tmp/ollama.log 2>&1 &

# Flask
cd frameworks/cortex-java && nohup python3 python_server/flask_api.py > /tmp/flask.log 2>&1 &

# Next.js
cd apps/web && npm run dev
```

### Recorder JVM'ler birikiyor
```bash
pkill -9 -f "exec:java"        # Tümünü öldür
pkill -9 -f "playwright-java"  # Playwright helper'ları da
```

### Test fail: "TimeoutError: waiting for locator(...)"
Site SPA hidrasyonu yavaş. Timeout'u artır:
```bash
./scripts/cortex feature <path> -Dplaywright.timeout.ms=60000
```

### AI Polish "Ollama'ya bağlanılamıyor"
```bash
curl http://127.0.0.1:11434/api/tags   # Çalışıyor mu?
ollama serve                            # Yeniden başlat
```

### Dashboard'da "Senaryoyu Doğrula" hata veriyor
Bilinen bir hata (E09 — `/replay` endpoint broken). Şimdilik **bu butonu kullanma**, doğrudan `cortex feature` ile çalıştır.

---

## 9. Sıradaki Adımlar

1. **Mevcut senaryolar:** `frameworks/cortex-java/src/test/resources/recordings/` — diğer testleri incele
2. **Step kütüphanesi:** `frameworks/cortex-java/src/test/java/playwright/stepdefs/` — kullanılabilecek tüm Gherkin step phrase'leri
3. **Locator referansı:** `src/test/resources/shared/locators/common.json` — ortak locator'lar
4. **Eksiklikler:** `~/Desktop/eksiklikler/cortex-2026-05-22/README.md` — bilinen iyileştirme alanları

---

## 10. Yardım

- **Hızlı referans:** `./scripts/cortex` (argümansız çalıştırılınca komut listesi)
- **Detaylı:** `make help` → tüm Makefile target'ları
- **Geliştirici:** `frameworks/cortex-java/src/main/java/recorder/README.md`
