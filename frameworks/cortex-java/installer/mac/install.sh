#!/usr/bin/env bash
# ============================================================
#  Cortex Otomasyon — macOS installer
# ============================================================
#  Bu script otomatik olarak:
#   1. Java 17+ kontrolü (yoksa Adoptium veya Homebrew ile kurar)
#   2. Python 3.10+ kontrolü
#   3. Playwright Chromium indirir (mvn üzerinden)
#   4. Python venv kurar + requirements.txt yükler
#   5. /Applications/Cortex Otomasyon.app oluşturur
#   6. Dashboard'u başlatır + tarayıcıyı açar
# ============================================================

set -e
set -o pipefail

# ── Colors / logging ──────────────────────────────────────────
RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; BLUE=$'\033[0;34m'; NC=$'\033[0m'

log()    { printf "%s[INFO]%s  %s\n"  "$BLUE"   "$NC" "$1"; }
ok()     { printf "%s[OK]%s    %s\n"  "$GREEN"  "$NC" "$1"; }
warn()   { printf "%s[WARN]%s  %s\n"  "$YELLOW" "$NC" "$1"; }
err()    { printf "%s[FAIL]%s  %s\n"  "$RED"    "$NC" "$1"; }
header() { printf "\n%s═══════ %s ═══════%s\n" "$BLUE" "$1" "$NC"; }

# ── Dialog helper (uses osascript for GUI) ────────────────────
gui_dialog() {
    local title="$1" msg="$2" type="${3:-informational}"
    osascript -e "display dialog \"$msg\" with title \"$title\" buttons {\"OK\"} default button \"OK\" with icon $type" >/dev/null 2>&1 || true
}

gui_confirm() {
    local title="$1" msg="$2"
    local r=$(osascript -e "display dialog \"$msg\" with title \"$title\" buttons {\"İptal\", \"Devam Et\"} default button \"Devam Et\"" 2>/dev/null | grep -o "button returned:.*" | cut -d: -f2 || echo "")
    [[ "$r" == " Devam Et" ]]
}

gui_progress() {
    local msg="$1"
    osascript <<EOF 2>/dev/null &
display notification "$msg" with title "Cortex Setup" sound name "Glass"
EOF
}

# ── Project root detection ────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# When run from /Applications/Cortex Setup.app, SCRIPT_DIR is inside the bundle
# When run from the repo, it's /path/to/otomasyon_atolyesi/installer/mac
if [[ -f "$SCRIPT_DIR/../../pom.xml" ]]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
elif [[ -f "$SCRIPT_DIR/../Resources/source/pom.xml" ]]; then
    # Running from .app bundle
    REPO_ROOT="$SCRIPT_DIR/../Resources/source"
else
    # Maybe running from a downloaded archive — find by walking up
    REPO_ROOT="$SCRIPT_DIR"
    while [[ "$REPO_ROOT" != "/" && ! -f "$REPO_ROOT/pom.xml" ]]; do
        REPO_ROOT="$(dirname "$REPO_ROOT")"
    done
fi

if [[ ! -f "$REPO_ROOT/pom.xml" ]]; then
    err "Proje kökü bulunamadı. pom.xml yok."
    gui_dialog "Cortex Setup — Hata" "Kurulum dosyalarında pom.xml bulunamadı. Lütfen orijinal kurulum paketini kullandığınızdan emin olun." "stop"
    exit 1
fi

# ── Install destination ───────────────────────────────────────
INSTALL_DIR="${CORTEX_INSTALL_DIR:-$HOME/Applications/Cortex Otomasyon}"
APP_BUNDLE="/Applications/Cortex Otomasyon.app"

header "Cortex Otomasyon — macOS Kurulum"
log "Kaynak: $REPO_ROOT"
log "Hedef:  $INSTALL_DIR"
echo

# ── 1. Java check ─────────────────────────────────────────────
check_java() {
    if ! command -v java >/dev/null 2>&1; then
        return 1
    fi
    local v=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}' | cut -d. -f1)
    [[ -n "$v" && "$v" -ge 17 ]]
}

install_java() {
    warn "Java 17+ bulunamadı. Kuruluyor..."

    # Try Homebrew first
    if command -v brew >/dev/null 2>&1; then
        log "Homebrew ile openjdk@17 kuruluyor..."
        if brew install openjdk@17; then
            # Link for system Java to find it
            local jdk_path="/opt/homebrew/opt/openjdk@17"
            [[ -d "$jdk_path" ]] || jdk_path="/usr/local/opt/openjdk@17"
            if [[ -d "$jdk_path" ]]; then
                # Symlink (may need sudo, optional — JAVA_HOME export is enough)
                sudo ln -sfn "$jdk_path/libexec/openjdk.jdk" /Library/Java/JavaVirtualMachines/openjdk-17.jdk 2>/dev/null || true
                export JAVA_HOME="$jdk_path"
                export PATH="$JAVA_HOME/bin:$PATH"
            fi
            ok "OpenJDK 17 kuruldu."
            return 0
        fi
    fi

    # Fallback: download Adoptium Temurin .pkg installer
    warn "Homebrew yok ya da başarısız oldu. Adoptium Temurin 17 indiriliyor..."
    local arch=$(uname -m)
    local pkg_url
    if [[ "$arch" == "arm64" ]]; then
        pkg_url="https://api.adoptium.net/v3/installer/latest/17/ga/mac/aarch64/jdk/hotspot/normal/eclipse?project=jdk"
    else
        pkg_url="https://api.adoptium.net/v3/installer/latest/17/ga/mac/x64/jdk/hotspot/normal/eclipse?project=jdk"
    fi

    local tmp_pkg="/tmp/Cortex-OpenJDK17.pkg"
    log "İndiriliyor: $pkg_url"
    if ! curl -L -o "$tmp_pkg" "$pkg_url"; then
        err "JDK indirilemedi. İnternet bağlantısını kontrol edin."
        gui_dialog "Cortex Setup — Hata" "Java JDK indirilemedi. Lütfen internet bağlantınızı kontrol edin veya manuel olarak https://adoptium.net adresinden kurun." "stop"
        exit 1
    fi

    log "JDK kuruluyor (sudo şifresi istenebilir)..."
    if sudo installer -pkg "$tmp_pkg" -target /; then
        rm -f "$tmp_pkg"
        # Refresh PATH so java is findable
        if [[ -d "/Library/Java/JavaVirtualMachines" ]]; then
            local jdk=$(ls /Library/Java/JavaVirtualMachines | grep -i "temurin\|openjdk" | head -1)
            if [[ -n "$jdk" ]]; then
                export JAVA_HOME="/Library/Java/JavaVirtualMachines/$jdk/Contents/Home"
                export PATH="$JAVA_HOME/bin:$PATH"
            fi
        fi
        ok "Java JDK 17 kuruldu."
        return 0
    else
        err "JDK kurulumu başarısız."
        return 1
    fi
}

header "1/6 · Java 17 kontrolü"
if check_java; then
    ok "Java 17+ mevcut: $(java -version 2>&1 | head -1)"
else
    if ! install_java; then
        err "Java kurulumu başarısız. Lütfen https://adoptium.net adresinden manuel kurun."
        exit 1
    fi
fi

# ── 2. Python check ───────────────────────────────────────────
check_python() {
    if ! command -v python3 >/dev/null 2>&1; then return 1; fi
    local v=$(python3 -c 'import sys; print(sys.version_info.major*100 + sys.version_info.minor)' 2>/dev/null)
    [[ -n "$v" && "$v" -ge 310 ]]
}

install_python() {
    warn "Python 3.10+ bulunamadı."
    if command -v brew >/dev/null 2>&1; then
        log "Homebrew ile python@3.11 kuruluyor..."
        brew install python@3.11 && ok "Python 3.11 kuruldu." && return 0
    fi
    err "Lütfen Python 3.10+ kurun: https://www.python.org/downloads/"
    return 1
}

header "2/6 · Python 3.10+ kontrolü"
if check_python; then
    ok "Python mevcut: $(python3 --version)"
else
    install_python || exit 1
fi

# ── 3. Copy project files ─────────────────────────────────────
header "3/6 · Proje dosyaları kopyalanıyor"
mkdir -p "$INSTALL_DIR"

# Use rsync to avoid copying junk
log "Kopyalama: $REPO_ROOT → $INSTALL_DIR"
rsync -a --delete \
    --exclude='.git/' --exclude='target/' --exclude='.idea/' \
    --exclude='.venv/' --exclude='node_modules/' \
    --exclude='logs/*.log*' --exclude='__pycache__/' \
    --exclude='installer/' \
    "$REPO_ROOT/" "$INSTALL_DIR/"

# Always include README and LICENSE
cp -f "$REPO_ROOT/README.md" "$INSTALL_DIR/" 2>/dev/null || true
cp -f "$REPO_ROOT/LICENSE.txt" "$INSTALL_DIR/" 2>/dev/null || true

ok "Proje kopyalandı."

# ── 4. Maven dependencies + Playwright ────────────────────────
header "4/6 · Maven bağımlılıkları indiriliyor (ilk seferinde ~3-5 dk)"
cd "$INSTALL_DIR"

# Use bundled mvnw if available (zero-install Maven)
MVN_CMD="./mvnw"
if [[ ! -x "$MVN_CMD" ]]; then
    chmod +x ./mvnw 2>/dev/null || true
fi
if [[ ! -x "$MVN_CMD" ]]; then
    if command -v mvn >/dev/null 2>&1; then
        MVN_CMD="mvn"
    else
        err "Maven (mvn) ve Maven Wrapper (mvnw) bulunamadı."
        exit 1
    fi
fi

log "Bağımlılıklar çözümleniyor..."
if ! "$MVN_CMD" -q -DskipTests dependency:resolve; then
    warn "Maven bağımlılık çözümleme başarısız. Devam ediliyor (ilk koşumda çözülecek)."
fi

log "Playwright Chromium indiriliyor..."
if ! "$MVN_CMD" -q exec:java -Dexec.mainClass="com.microsoft.playwright.CLI" -Dexec.args="install chromium" 2>/dev/null; then
    warn "Playwright kurulumu otomatik yapılamadı. İlk recorder kullanımında otomatik kurulacak."
fi
ok "Java tarafı hazır."

# ── 5. Python venv + deps ─────────────────────────────────────
header "5/6 · Python venv + bağımlılıklar"
cd "$INSTALL_DIR"

PY="python3"
log "Sanal ortam: $INSTALL_DIR/.venv"
$PY -m venv .venv

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r python_server/requirements.txt

if [[ -f "python_server/train_model.py" && ! -f "python_server/final_model.pkl" ]]; then
    log "ML modeli eğitiliyor..."
    cd python_server && python train_model.py && cd ..
fi
deactivate
ok "Python ortamı hazır."

# ── 6. Create .app bundle for one-click launch ────────────────
header "6/6 · Uygulama paketi oluşturuluyor"

# Remove old .app if exists
[[ -d "$APP_BUNDLE" ]] && rm -rf "$APP_BUNDLE"

# Create .app bundle structure
mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"

cat > "$APP_BUNDLE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>             <string>Cortex Otomasyon</string>
    <key>CFBundleDisplayName</key>      <string>Cortex Otomasyon</string>
    <key>CFBundleIdentifier</key>       <string>com.bilgeadam.cortex.dashboard</string>
    <key>CFBundleVersion</key>          <string>1.0.0</string>
    <key>CFBundleShortVersionString</key><string>1.0.0</string>
    <key>CFBundlePackageType</key>      <string>APPL</string>
    <key>CFBundleExecutable</key>       <string>cortex-launcher</string>
    <key>LSMinimumSystemVersion</key>   <string>11.0</string>
    <key>NSHighResolutionCapable</key>  <true/>
    <key>LSUIElement</key>              <false/>
</dict>
</plist>
PLIST

cat > "$APP_BUNDLE/Contents/MacOS/cortex-launcher" <<LAUNCHER
#!/usr/bin/env bash
# Cortex Otomasyon launcher — opens dashboard in default browser
set -e

INSTALL_DIR="$INSTALL_DIR"
cd "\$INSTALL_DIR"

# Start dashboard (Flask) in background
source .venv/bin/activate

# Open Terminal window for logs
osascript -e "tell app \"Terminal\" to do script \"cd '\$INSTALL_DIR' && source .venv/bin/activate && cd python_server && python flask_api.py\"" >/dev/null 2>&1

# Wait for Flask to be ready
for i in {1..30}; do
    if curl -s -o /dev/null http://127.0.0.1:5001/api/health; then
        break
    fi
    sleep 1
done

# Open browser
open "http://127.0.0.1:5001"
LAUNCHER

chmod +x "$APP_BUNDLE/Contents/MacOS/cortex-launcher"

ok "Uygulama paketi oluşturuldu: $APP_BUNDLE"

# ── Final summary ─────────────────────────────────────────────
header "Kurulum Tamamlandı ✓"
echo
ok "Cortex Otomasyon yüklendi: $INSTALL_DIR"
ok "Uygulama: /Applications/Cortex Otomasyon.app"
echo
log "Şimdi başlatmak için:"
echo "  • Finder → Applications → Cortex Otomasyon (çift tıkla)"
echo "  • Veya: open '$APP_BUNDLE'"
echo
log "Manuel başlatma:"
echo "  cd '$INSTALL_DIR' && source .venv/bin/activate && cd python_server && python flask_api.py"
echo

gui_progress "Cortex Otomasyon hazır ✓"

# Auto-launch?
if [[ "${1:-}" != "--no-launch" ]]; then
    log "Cortex Otomasyon 3 saniye sonra başlatılıyor..."
    sleep 3
    open "$APP_BUNDLE"
fi

exit 0
