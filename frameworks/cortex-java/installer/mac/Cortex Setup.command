#!/usr/bin/env bash
# ===========================================================
#  Cortex Otomasyon - macOS Setup (double-click in Finder)
# ===========================================================
#  Bu dosyayı Finder'da çift tıklayarak kurulum başlatılır.
#  Terminal otomatik açılır, ilerlemeyi gösterir.
# ===========================================================

# Resolve script location (the directory this .command file lives in)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Run the installer
clear
cat <<'BANNER'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║       ░█▀▀░█▀█░█▀▄░▀█▀░█▀▀░█░█                              ║
║       ░█░░░█░█░█▀▄░░█░░█▀▀░▄▀▄                              ║
║       ░▀▀▀░▀▀▀░▀░▀░░▀░░▀▀▀░▀░▀                              ║
║                                                              ║
║       Cortex Otomasyon - macOS Setup                        ║
║       BilgeAdam Test Automation Platform                    ║
║                                                              ║
║       Kurulum şimdi başlıyor...                             ║
║       (sudo şifresi istenirse: Mac giriş şifrenizi girin)   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
BANNER
echo
sleep 2

if [[ -f "$DIR/install.sh" ]]; then
    bash "$DIR/install.sh"
elif [[ -f "$DIR/../installer/mac/install.sh" ]]; then
    bash "$DIR/../installer/mac/install.sh"
else
    echo "[FATAL] install.sh bulunamadı."
    echo "Bu .command dosyasını kurulum paketinin içinden çıkarmayın."
    read -p "Çıkmak için ENTER tuşuna basın..."
    exit 1
fi

EXIT_CODE=$?
echo
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✓ Kurulum başarıyla tamamlandı. Bu pencereyi kapatabilirsiniz."
else
    echo "✗ Kurulum sırasında hata oluştu (exit code: $EXIT_CODE)."
    echo "  Lütfen yukarıdaki mesajları kontrol edin."
fi
echo
read -p "Pencereyi kapatmak için ENTER tuşuna basın..."
exit $EXIT_CODE
