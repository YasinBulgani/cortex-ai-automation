# Windows'ta CortexSetup.exe Derleme — Adım Adım

Bu rehber, **Mac'te hazırlanan** Cortex_Ai_Automation projesinin Windows üstünde `.exe` installer'a derlenmesini anlatır.

---

## Ön koşullar (Windows PC'de)

| Araç | Gerekli mi | Nasıl kurulur |
|------|-----------|---------------|
| **Inno Setup 6+** | ✅ Zorunlu | `winget install JRSoftware.InnoSetup` veya <https://jrsoftware.org/isdl.php> |
| **PowerShell 5+** | ✅ Var (Windows 10+) | Otomatik |
| Java / Python / Node | ❌ İstemiyor | Bunlar `install-deps.ps1` tarafından **son kullanıcıda** kurulur |

---

## Adım 1 — Projeyi Windows PC'ye taşı

3 yöntemden biri:

### A. USB / Harici disk (en hızlı, ~12MB)
```bash
# Mac'te terminalden:
cp -r ~/Desktop/Cortex_Ai_Automation /Volumes/USB-NAME/
```

### B. OneDrive / Google Drive / Dropbox
- `~/Desktop/Cortex_Ai_Automation` klasörünü buluta yükle
- Windows'ta indir → çıkar

### C. Git (en temiz)
```bash
# Mac'te:
cd ~/Desktop/Cortex_Ai_Automation
git init
git add .
git commit -m "Initial"
git remote add origin <github-url>
git push -u origin main

# Windows'ta:
git clone <github-url>
```

---

## Adım 2 — Inno Setup 6 kur

```powershell
# winget ile (Windows 10 19h1+):
winget install JRSoftware.InnoSetup

# veya manuel: https://jrsoftware.org/isdl.php
# "innosetup-6.x.x.exe" indir, çift tıkla, ileri ileri kur
```

Kurulum sonrası test:
```cmd
where iscc
# Beklenen çıktı: C:\Program Files (x86)\Inno Setup 6\ISCC.exe
```

Eğer `where iscc` boş döndürürse PATH'e ekleyin:
- Başlat → "Environment Variables" yaz → "Edit System Environment Variables"
- PATH'e ekle: `C:\Program Files (x86)\Inno Setup 6`

---

## Adım 3 — .exe'yi derle

CMD veya PowerShell aç:

```cmd
cd C:\path\to\Cortex_Ai_Automation
installer\windows\build.bat 1.0.0
```

**Beklenen çıktı:**
```
============================================================
 Cortex AI Automation — Windows Installer v1.0.0
============================================================
[BUILD] Inno Setup derleniyor...
Inno Setup 6 Compiler version ...
Compiling: CortexSetup.iss
...
Successful compile (12.345 sec).
============================================================
 BASARILI
============================================================
 Cikti: ..\out\CortexSetup-1.0.0-Windows.exe
```

Dosya: `installer\out\CortexSetup-1.0.0-Windows.exe` (~5-10MB)

---

## Adım 4 — Test (kendi makinanda)

`CortexSetup-1.0.0-Windows.exe`'ye çift tıkla:

1. Inno Setup wizard (Türkçe + İngilizce dil seçimi)
2. Lisans → kabul
3. Hedef dizin: `C:\Program Files\Cortex_Ai_Automation\` (önerilen default)
4. Görev seçimi: ✓ Masaüstü kısayolu, ✓ Başlat menüsü
5. "Yükle" tıkla
6. **install-deps.ps1 otomatik çalışır** — Java/Python/Maven/Playwright kurar (3-5 dk)
7. Tamamlandığında → Dashboard tarayıcıda açılır

---

## Yaygın sorunlar

### "iscc not recognized"
- Inno Setup PATH'e ekli değil. Adım 2'deki PATH ayarını yap.
- Veya `build.bat`'i direkt full path ile çağır:
  ```cmd
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\windows\CortexSetup.iss
  ```

### "Source file not found: ..\..\framework\pom.xml"
- `build.bat`'i **proje kökünden** çalıştır:
  ```cmd
  cd C:\path\to\Cortex_Ai_Automation       # ← KÖK
  installer\windows\build.bat 1.0.0        # ← Bu yoldan
  ```

### "License file not found"
- `LICENSE.txt` proje kökünde olmalı. Kontrol et:
  ```cmd
  dir LICENSE.txt
  ```

### SmartScreen uyarısı (son kullanıcıda)
- "Bu uygulama korundu" → **Daha fazla bilgi** → **Yine de çalıştır**
- Production için code-signing sertifikası gerekir:
  ```cmd
  signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a installer\out\CortexSetup-1.0.0-Windows.exe
  ```

### Antivirüs karantinaya alıyor
- İmzasız `.exe` Windows Defender'ı tetikleyebilir
- Bir kerelik istisna ekle veya code-signing sertifikası al

---

## Bonus: Özel ikon eklemek

`cortex.ico` (256x256 multi-res .ico) bul/üret, `installer/windows/cortex.ico` olarak koy.

Sonra `CortexSetup.iss` içinde şu satırları **uncomment** et:
```ini
SetupIconFile=cortex.ico
UninstallDisplayIcon={app}\installer\windows\cortex.ico
```

Online .ico üretmek için: <https://www.icoconverter.com/>

---

## Kontrol listesi (özet)

- [ ] Cortex_Ai_Automation klasörü Windows PC'de
- [ ] Inno Setup 6+ kurulu (`where iscc` çalışıyor)
- [ ] `dir LICENSE.txt` (proje kökünde var)
- [ ] `dir framework\pom.xml` (var)
- [ ] `dir installer\windows\install-deps.ps1` (var)
- [ ] `installer\windows\build.bat 1.0.0` çalıştırıldı
- [ ] `installer\out\CortexSetup-1.0.0-Windows.exe` üretildi
- [ ] .exe çift tıklandığında Inno Setup sihirbazı açılıyor
- [ ] Sihirbaz tamamlandığında Java + Python + Flask hazır
