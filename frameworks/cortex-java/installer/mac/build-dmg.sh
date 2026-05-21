#!/usr/bin/env bash
# ============================================================
#  Cortex Otomasyon — Mac DMG Builder
# ============================================================
#  Bu script "Cortex Otomasyon Setup.dmg" üretir.
#  Son kullanıcı DMG'yi açar → "Cortex Setup.command" tıklar.
#
#  Usage:
#    ./installer/mac/build-dmg.sh [version]
# ============================================================

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VERSION="${1:-1.0.0}"

OUT_DIR="$REPO_ROOT/installer/out"
STAGING="$OUT_DIR/dmg-staging"
DMG_NAME="Cortex-Otomasyon-Setup-${VERSION}-macOS"
DMG_PATH="$OUT_DIR/$DMG_NAME.dmg"

RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; BLUE=$'\033[0;34m'; NC=$'\033[0m'
log() { printf "%s[BUILD]%s %s\n" "$BLUE" "$NC" "$1"; }
ok()  { printf "%s[OK]%s    %s\n" "$GREEN" "$NC" "$1"; }
err() { printf "%s[FAIL]%s  %s\n" "$RED" "$NC" "$1"; }

log "Cortex Otomasyon DMG Builder v${VERSION}"
log "Repo:       $REPO_ROOT"
log "Çıktı:      $DMG_PATH"
echo

# Clean previous
rm -rf "$STAGING" "$DMG_PATH"
mkdir -p "$STAGING" "$OUT_DIR"

# ── 1. Copy source files into DMG staging ────────────────────
log "Kaynak dosyalar kopyalanıyor..."
mkdir -p "$STAGING/source"
rsync -a \
    --exclude='.git/' --exclude='target/' --exclude='.idea/' \
    --exclude='.venv/' --exclude='node_modules/' \
    --exclude='logs/*.log*' --exclude='__pycache__/' \
    --exclude='installer/out/' --exclude='dist/' \
    "$REPO_ROOT/" "$STAGING/source/"

# ── 2. Copy installer script to DMG root ─────────────────────
log "Setup .command'i DMG köküne kopyalanıyor..."
cp "$SCRIPT_DIR/Cortex Setup.command" "$STAGING/"
chmod +x "$STAGING/Cortex Setup.command"

# Also ship install.sh next to it (the .command auto-finds it)
cp "$SCRIPT_DIR/install.sh" "$STAGING/install.sh"
chmod +x "$STAGING/install.sh"

# ── 3. README.md inside DMG ──────────────────────────────────
cat > "$STAGING/OKU-BENI.txt" <<README
==========================================================
  CORTEX OTOMASYON — Mac Kurulum
==========================================================

KURULUM:
  1. "Cortex Setup.command" dosyasına ÇİFT TIKLAYIN.
  2. Terminal otomatik açılır, kurulum başlar.
  3. İlk kullanımda sudo şifresi istenebilir (Java kurulumu için).
  4. Kurulum tamamlandığında "Cortex Otomasyon.app" başlatılır.

İLK ÇALIŞTIRMADA "İZİN VERİLEMEDİ" UYARISI ALIRSANIZ:
  • System Settings → Privacy & Security → "Open Anyway" tıklayın
  • Veya Terminal'den: xattr -d com.apple.quarantine "Cortex Setup.command"

DEPENDENCIES (otomatik kurulur):
  • Java 17+   (Adoptium Temurin / Homebrew)
  • Python 3.10+ (genelde önceden var)
  • Maven      (proje içindeki ./mvnw kullanılır)
  • Playwright Chromium (mvn ile)

HEDEF DİZİN:
  ~/Applications/Cortex Otomasyon/

UYGULAMA:
  /Applications/Cortex Otomasyon.app

DEINSTALL:
  rm -rf "~/Applications/Cortex Otomasyon"
  rm -rf "/Applications/Cortex Otomasyon.app"

DESTEK:
  https://cortex-test.bgtsai.com/
  Sürüm: ${VERSION}
==========================================================
README

# ── 4. Create symlink to /Applications for drag-install UX ───
ln -s /Applications "$STAGING/Applications"

# ── 5. Build the DMG ─────────────────────────────────────────
log "DMG oluşturuluyor (sıkıştırma ~30sn sürebilir)..."

hdiutil create \
    -volname "Cortex Otomasyon ${VERSION}" \
    -srcfolder "$STAGING" \
    -ov \
    -format UDZO \
    -fs HFS+ \
    "$DMG_PATH"

# Cleanup
rm -rf "$STAGING"

SIZE=$(du -h "$DMG_PATH" | cut -f1)
ok "Tamamlandı: $DMG_PATH  ($SIZE)"
echo
log "Test için: open \"$DMG_PATH\""
log "Dağıtım:    $DMG_NAME.dmg"
