#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# TestwrightAI — DB / User Rename Deploy Script
#
# Bu script, rebranding Faz 4 kapsamında PostgreSQL'de şu değişiklikleri yapar:
#   - user:  bgts_user → twai_user
#   - pass:  bgts_pass → twai_pass (varsayılan; --password ile değiştirilebilir)
#   - db:    bgts_db   → twai_db
#
# ALEMBIC İLE YAPILMADI ÇÜNKÜ:
# PostgreSQL'de `ALTER DATABASE` komutu, bağlı olunan DB'nin kendisine
# uygulanamaz. Migration runner'ın `bgts_db`'ye bağlı olması gerekirdi
# ama rename için başka bir DB'ye (örn. `postgres`) bağlı olmak lazım.
# Bu yüzden bu bir deploy-time script olarak sunuluyor.
#
# KULLANIM:
#
#   1) Önce ortamı durdur:
#      docker compose down
#
#   2) Postgres'i YALNIZ başlat (diğer servisler DB'ye bağlı değilken rename olur):
#      docker compose up -d postgres
#
#   3) Scripti çalıştır:
#      ./scripts/rebrand-db.sh
#
#   4) .env dosyanda DATABASE_URL'i güncelle (twai_user:twai_pass@host:5432/twai_db)
#
#   5) Tüm servisleri tekrar başlat:
#      docker compose up -d
#
# GERİ ALMAK İÇİN (rollback):
#   ./scripts/rebrand-db.sh --rollback
#
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ─── Varsayılan Değerler ──────────────────────────────────────────────────────
PGHOST="${PGHOST:-127.0.0.1}"
PGPORT="${PGPORT:-5432}"
PGSUPERUSER="${PGSUPERUSER:-postgres}"
PGSUPERPASS="${PGSUPERPASS:-}"          # boşsa peer auth dener

OLD_USER="bgts_user"
OLD_DB="bgts_db"
NEW_USER="twai_user"
NEW_DB="twai_db"
NEW_PASSWORD="twai_pass"

ROLLBACK=0

# ─── CLI Argümanları ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --rollback)    ROLLBACK=1; shift ;;
    --password)    NEW_PASSWORD="$2"; shift 2 ;;
    --host)        PGHOST="$2"; shift 2 ;;
    --port)        PGPORT="$2"; shift 2 ;;
    --superuser)   PGSUPERUSER="$2"; shift 2 ;;
    -h|--help)
      sed -n '1,45p' "$0"
      exit 0
      ;;
    *) echo "Bilinmeyen argüman: $1" >&2; exit 2 ;;
  esac
done

# ─── Rollback Modu ────────────────────────────────────────────────────────────
if [[ "$ROLLBACK" -eq 1 ]]; then
  OLD_USER="twai_user"
  OLD_DB="twai_db"
  NEW_USER="bgts_user"
  NEW_DB="bgts_db"
  NEW_PASSWORD="bgts_pass"
  echo "🔁 ROLLBACK MODU — $OLD_USER/$OLD_DB geri dönüş: $NEW_USER/$NEW_DB"
fi

echo "📦 TestwrightAI DB Rebrand"
echo "   Host: $PGHOST:$PGPORT (superuser: $PGSUPERUSER)"
echo "   User: $OLD_USER → $NEW_USER"
echo "   DB:   $OLD_DB → $NEW_DB"
echo

# ─── PSQL Helper ──────────────────────────────────────────────────────────────
export PGPASSWORD="$PGSUPERPASS"
PSQL=(psql -h "$PGHOST" -p "$PGPORT" -U "$PGSUPERUSER" -v ON_ERROR_STOP=1)

run_sql() {
  "${PSQL[@]}" -d postgres -c "$1"
}

# ─── Ön Kontrol ───────────────────────────────────────────────────────────────
echo "🔍 Mevcut durumu kontrol ediliyor..."
"${PSQL[@]}" -d postgres -t -c "SELECT datname FROM pg_database WHERE datname IN ('$OLD_DB', '$NEW_DB');" \
  || { echo "❌ Postgres'e bağlanılamadı. Çalışıyor mu? (docker compose up -d postgres)"; exit 1; }

EXISTS_OLD=$("${PSQL[@]}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$OLD_DB'" || echo "")
EXISTS_NEW=$("${PSQL[@]}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$NEW_DB'" || echo "")

if [[ -z "$EXISTS_OLD" && -n "$EXISTS_NEW" ]]; then
  echo "✅ DB zaten rename edilmiş görünüyor. Bir şey yapılmadı."
  exit 0
fi
if [[ -z "$EXISTS_OLD" ]]; then
  echo "⚠️  $OLD_DB bulunamadı. Eğer ilk kurulum ise docker-compose volume'u sıfır olabilir."
  echo "   Bu durumda rename'e gerek yok, container yeni DB'yi zaten $NEW_DB ismiyle yaratacak."
  exit 0
fi

# ─── 1) Aktif bağlantıları kapat ──────────────────────────────────────────────
echo "🔌 $OLD_DB üzerindeki aktif bağlantılar kapatılıyor..."
run_sql "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE datname = '$OLD_DB' AND pid <> pg_backend_pid();
" >/dev/null

# ─── 2) DB'yi rename et ───────────────────────────────────────────────────────
echo "📝 DATABASE rename: $OLD_DB → $NEW_DB"
run_sql "ALTER DATABASE \"$OLD_DB\" RENAME TO \"$NEW_DB\";"

# ─── 3) Kullanıcıyı rename et ve şifresini güncelle ───────────────────────────
EXISTS_OLD_USER=$("${PSQL[@]}" -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname = '$OLD_USER'" || echo "")
if [[ -n "$EXISTS_OLD_USER" ]]; then
  echo "👤 ROLE rename: $OLD_USER → $NEW_USER"
  run_sql "ALTER ROLE \"$OLD_USER\" RENAME TO \"$NEW_USER\";"
  run_sql "ALTER ROLE \"$NEW_USER\" WITH PASSWORD '$NEW_PASSWORD';"
else
  echo "ℹ️  $OLD_USER rolü bulunamadı. $NEW_USER yaratılıyor..."
  run_sql "CREATE ROLE \"$NEW_USER\" WITH LOGIN PASSWORD '$NEW_PASSWORD';"
  run_sql "GRANT ALL PRIVILEGES ON DATABASE \"$NEW_DB\" TO \"$NEW_USER\";"
fi

# ─── 4) Doğrulama ─────────────────────────────────────────────────────────────
echo
echo "✅ Rebrand tamamlandı."
echo "   Yeni DB  : $NEW_DB"
echo "   Yeni User: $NEW_USER"
echo
echo "📌 Şimdi yapılması gerekenler:"
echo "   1. .env dosyanda DATABASE_URL'i güncelle:"
echo "      DATABASE_URL=postgresql+psycopg2://$NEW_USER:$NEW_PASSWORD@$PGHOST:$PGPORT/$NEW_DB"
echo "   2. docker compose up -d   (tüm servisleri tekrar başlat)"
echo "   3. Smoke test:  curl http://localhost:8000/health"
