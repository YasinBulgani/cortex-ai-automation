#!/usr/bin/env bash
# ============================================================
#  Cortex Otomasyon — Master Build Script (Mac side)
#
#  Bu script Mac üzerinde çalışır:
#    - DMG'yi yerel olarak derler (hdiutil)
#    - Windows .exe için instruction yazdırır (Inno Setup Windows-only)
#
#  Kullanım:
#    ./installer/build-all.sh [VERSION]
# ============================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="${1:-1.0.0}"

GREEN=$'\033[0;32m'; BLUE=$'\033[0;34m'; YELLOW=$'\033[1;33m'; NC=$'\033[0m'
ok()    { printf "%s[OK]%s    %s\n" "$GREEN" "$NC" "$1"; }
log()   { printf "%s[BUILD]%s %s\n" "$BLUE" "$NC" "$1"; }
warn()  { printf "%s[WARN]%s  %s\n" "$YELLOW" "$NC" "$1"; }

log "Cortex Otomasyon v${VERSION} — Master Build"
log "Repo: $REPO_ROOT"
echo

# Make all scripts executable
chmod +x "$SCRIPT_DIR/mac/install.sh"          2>/dev/null || true
chmod +x "$SCRIPT_DIR/mac/Cortex Setup.command" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/mac/build-dmg.sh"        2>/dev/null || true

# ── Mac DMG ──────────────────────────────────────────────────
log "Mac DMG derleniyor..."
bash "$SCRIPT_DIR/mac/build-dmg.sh" "$VERSION"
ok "Mac DMG hazır."

# ── Windows EXE (Mac üstünde derlenemez — Inno Setup Windows-only) ──
echo
warn "Windows .exe Mac üzerinde DERLENEMEZ (Inno Setup Windows-only)."
echo
echo "Windows .exe için bir Windows makinasında şu adımları izleyin:"
echo "  1. Inno Setup 6+ kur:  https://jrsoftware.org/isdl.php"
echo "                          veya: winget install JRSoftware.InnoSetup"
echo
echo "  2. Bu repo'yu Windows'a kopyalayın (Git, OneDrive, Network share)"
echo
echo "  3. Repo kökünde:"
echo "       installer\\windows\\build.bat $VERSION"
echo
echo "  4. Çıktı:  installer\\out\\CortexSetup-$VERSION-Windows.exe"
echo
echo "Cross-platform CI için: .github/workflows/build-installers.yml kullanılabilir."

echo
log "Tüm derleme tamamlandı."
log "Çıktılar:    $REPO_ROOT/installer/out/"
ls -lh "$REPO_ROOT/installer/out/" 2>/dev/null || true
