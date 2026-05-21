# Cortex AI Automation — Installer Üretimi

Tek tıklamayla kurulum sağlayan, **bağımlılıkları otomatik kuran** Mac ve Windows installer'ları.

## Neyi yapar?

Son kullanıcının yapması gereken **TEK İŞ**: indir → çift tıkla → bekle.

Installer otomatik olarak:

| Adım | Mac | Windows |
|------|-----|---------|
| Java 17+ tespit | ✓ `java -version` | ✓ `java -version` |
| Java 17+ kurulum (yoksa) | Homebrew → Adoptium Temurin .pkg | winget → Adoptium Temurin MSI |
| Python 3.10+ tespit | ✓ `python3 --version` | ✓ `python --version` |
| Python 3.10+ kurulum (yoksa) | Homebrew → python@3.11 | winget → Python 3.11 / python.org |
| Maven | Proje içi `mvnw` wrapper | Proje içi `mvnw.cmd` wrapper |
| Java bağımlılıkları | `mvnw dependency:resolve` | `mvnw.cmd dependency:resolve` |
| Playwright Chromium | `mvn exec:java ... install chromium` | aynı |
| Python venv | `python3 -m venv .venv` + `pip install -r` | `python -m venv .venv` + `pip install -r` |
| ML modeli eğitim | `train_model.py` (yoksa) | aynı |
| Launcher | `/Applications/Cortex AI Automation.app` | `Cortex-Baslat.bat` + Masaüstü kısayolu |
| Dashboard başlat | Tarayıcıda http://localhost:5001 | aynı |

---

## Çıktılar

```
installer/out/
├── Cortex-Otomasyon-Setup-1.0.0-macOS.dmg     (~50 MB, Mac)
└── CortexSetup-1.0.0-Windows.exe              (~90 MB, Windows)
```

---

## Builder için: Derleme

### Mac üzerinde (Mac DMG için)

```bash
chmod +x installer/build-all.sh
./installer/build-all.sh 1.0.0
```

Çıktı: `installer/out/Cortex-Otomasyon-Setup-1.0.0-macOS.dmg`

### Windows üzerinde (Windows .exe için)

1. Inno Setup 6+ kur: <https://jrsoftware.org/isdl.php>
   - Veya: `winget install JRSoftware.InnoSetup`

2. Repo kökünde:
   ```cmd
   installer\windows\build.bat 1.0.0
   ```

Çıktı: `installer\out\CortexSetup-1.0.0-Windows.exe`

### CI üzerinden (her ikisi otomatik)

`git tag v1.0.0 && git push --tags` →
GitHub Actions hem Mac DMG hem Windows EXE üretir + Release'e ekler.

`.github/workflows/build-installers.yml` workflow'u:
- `macos-latest` runner'da DMG derler
- `windows-latest` runner'da Inno Setup + EXE derler
- Tag push'unda otomatik GitHub Release oluşturur

Manuel tetikleme:
- GitHub UI → Actions → "Build Installers" → "Run workflow"

---

## Son kullanıcı için: Kurulum

### Mac

1. `Cortex-Otomasyon-Setup-1.0.0-macOS.dmg` dosyasını indir
2. Çift tıkla → DMG mount olur
3. **`Cortex Setup.command`** dosyasına çift tıkla
4. Terminal açılır, kurulum başlar
5. Gerekirse sudo şifresi gir (Java kurulumu için)
6. ~5 dk sonra `/Applications/Cortex AI Automation.app` hazır
7. Dashboard tarayıcıda açılır

**İlk açılışta "izin verilemedi" uyarısı** alırsanız:
```bash
xattr -d com.apple.quarantine "/Volumes/Cortex AI Automation 1.0.0/Cortex Setup.command"
```
Veya: System Settings → Privacy & Security → "Open Anyway"

### Windows

1. `CortexSetup-1.0.0-Windows.exe` dosyasını indir
2. Çift tıkla → Inno Setup sihirbazı açılır
3. Standart sihirbaz adımları (lisans, dizin, görev seçimi)
4. Setup → bağımlılıkları kurar (3-5 dk)
5. Masaüstünde **Cortex AI Automation** kısayolu
6. Çift tıkla → dashboard açılır

**SmartScreen uyarısı** alırsanız:
- "Daha fazla bilgi" → "Yine de çalıştır"
- (Production için code-signing sertifikası ile imzalanması önerilir)

---

## Dosya yapısı

```
installer/
├── README.md                    # Bu dosya
├── build-all.sh                 # Master build (Mac üstünde)
│
├── mac/
│   ├── install.sh               # Ana Mac install logic
│   ├── Cortex Setup.command     # Finder'da çift-tıklanabilir wrapper
│   └── build-dmg.sh             # DMG üretici
│
├── windows/
│   ├── CortexSetup.iss          # Inno Setup script
│   ├── install-deps.ps1         # PowerShell dep installer
│   ├── build.bat                # Inno Setup derleyici
│   └── cortex.ico               # Installer/uygulama ikonu (opsiyonel)
│
├── shared/                      # Cross-platform yardımcılar (gelecekte)
│
└── out/                         # Derleme çıktıları
    ├── Cortex-Otomasyon-Setup-*.dmg
    └── CortexSetup-*-Windows.exe
```

---

## Gömülü JRE / Maven (opsiyonel ama önerilir)

İnternet yok ya da kısıtlı ortamlarda kurulum için, JRE'yi installer'a göm:

### Windows (Inno Setup)
1. <https://adoptium.net/temurin/releases/?os=windows&package=jre&arch=x64> sayfasından Windows x64 **portable JRE** zip'i indir
2. `installer/windows/runtime/jre/` altına aç
3. `CortexSetup.iss` içindeki şu satırı uncomment et:
   ```
   Source: "runtime\jre\*"; DestDir: "{app}\runtime\jre"; Flags: recursesubdirs createallsubdirs
   ```
4. `install-deps.ps1` içindeki `Test-Java17` fonksiyonu önce `$InstallDir\runtime\jre\bin\java.exe`'yi kontrol etsin (eklenti gerekli)

### Mac (DMG)
1. Mac portable JRE'yi indir (Temurin .tar.gz)
2. `installer/mac/runtime/jre/` altına aç
3. `install.sh` içinde `check_java` fonksiyonuna ek path kontrolü ekle

**Trade-off**: installer ~250 MB olur ama offline kurulum garantili.

---

## Code signing (production)

### Windows
```cmd
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a installer\out\CortexSetup-1.0.0-Windows.exe
```

### Mac
```bash
codesign --deep --force --verify --verbose --sign "Developer ID Application: Bilge Adam (TEAMID)" "installer/out/Cortex-Otomasyon-Setup-1.0.0-macOS.dmg"
```

Sonrasında **Apple notarize**:
```bash
xcrun notarytool submit installer/out/*.dmg --apple-id you@example.com --team-id TEAMID --wait
xcrun stapler staple installer/out/*.dmg
```

---

## Sorun giderme

| Sorun | Çözüm |
|-------|-------|
| **Mac**: "Cortex Setup.command çalıştırılamaz" | `chmod +x "Cortex Setup.command"` |
| **Mac**: Gatekeeper engelliyor | `xattr -d com.apple.quarantine *.command` |
| **Mac**: Java kurulamıyor (sudo gerekli) | Mac giriş şifrenizi girin; veya manuel: `brew install openjdk@17` |
| **Win**: SmartScreen "Bu uygulama korundu" | "Daha fazla bilgi" → "Yine de çalıştır" |
| **Win**: PowerShell "execution policy" hatası | Inno Setup script `-ExecutionPolicy Bypass` ile çağırıyor — Windows policy override |
| **Win**: winget yok (Windows 10 1809 öncesi) | Fallback olarak direct download çalışır |
| Dashboard açılmıyor (port 5001 dolu) | `lsof -i :5001` (Mac) / `netstat -ano \| findstr 5001` (Win) — kapatın |
| Playwright Chromium yok | İlk Recorder kullanımında otomatik iner; veya manuel: `cd <install> && ./mvnw exec:java -Dexec.mainClass=com.microsoft.playwright.CLI -Dexec.args="install chromium"` |

---

## Versiyon yönetimi

Versiyon `installer/build-all.sh 2.0.0` veya `installer\windows\build.bat 2.0.0` argümanı ile geçer.

Tek yerden değiştirmek için her iki dosyada `MyAppVersion` default'unu güncelleyin.

**Daha güzelini istiyorsanız**: `installer/version.txt` yaratıp her iki script'i bu dosyadan okuyun (TODO).
