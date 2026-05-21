#!/usr/bin/env bash
# =============================================================
#  Git history'den hassas dosyalari kalici olarak siler.
#
#  TEHLIKELI: Bu komut tum branch ve tag'leri yeniden yazar.
#  Hareke gecmeden once:
#    1. Repo'nun bir backup'ini al (cp -r veya ayri remote'a push).
#    2. Takimi haberdar et — herkesin pull yapmasi gerekir.
#    3. Force-push'tan sonra eski clone'lar bozulur, yeniden klonlama lazim.
#
#  Calistirma:
#    chmod +x scripts/scrub-git-history.sh
#    scripts/scrub-git-history.sh
# =============================================================
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo "git-filter-repo yuklu degil."
  echo "  brew install git-filter-repo"
  echo "  veya: pip install git-filter-repo"
  exit 1
fi

read -p "Bu komut git history'yi yeniden yazacak. Devam? (yes/no) " ans
[ "$ans" = "yes" ] || { echo "Iptal."; exit 1; }

# Silinecek dosyalar
FILES=(
  src/main/resources/password.properties
  python_server/final_model.pkl
)

for f in "${FILES[@]}"; do
  echo "History'den siliniyor: $f"
  git filter-repo --invert-paths --path "$f" --force
done

echo ""
echo "==============================================="
echo "  Tamamlandi. Simdi force-push gerek:"
echo "    git push --force --all"
echo "    git push --force --tags"
echo ""
echo "  Takim uyelerine: lokal clone'larini silip"
echo "  yeniden git clone yapmali."
echo "==============================================="
