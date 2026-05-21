#!/usr/bin/env python3
"""Türkçe karakter normalizasyonu — ASCII → diakritik.

UI kodunda bulunan yaygın ASCII Türkçe yazımları (ör. "baglanti" → "bağlantı")
sözlük bazlı olarak düzeltir. Yanlış eşleşmeyi azaltmak için yalnızca JSX/TSX
string literal'leri ve JSX text içeriği hedeflenir; kod tanımlayıcıları,
import path'leri, CSS class'ları ve testID'ler korunur.

Kullanım:
    python scripts/tr_normalize.py --dry-run
    python scripts/tr_normalize.py --apply
    python scripts/tr_normalize.py --check-only    # CI için — bulgu varsa exit 1

Kapsam:
    - apps/web/**/*.tsx
    - apps/web/**/*.ts (yalnızca string literal'ler)

Çıktı:
    Etkilenen dosya, satır no, eski ve yeni metin (terminal renkleriyle).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ── Eşleme sözlüğü ──────────────────────────────────────────────────────────
# NOT: Sadece küçük harf eşlemeleri tanımlanır; büyük/küçük harf karma
# varyantları runtime'da üretilir. Kök + sonek yaklaşımı genelde yeterli.
# Yanlış eşleşme riskini azaltmak için yalnızca kelime sınırı ile eşleşiriz.

# Yalnızca gerçek bir dönüşüm yapan eşlemeler. Türkçe karakter içermeyen
# kelimeler (ör. "tasarla", "durum") listeye konulmaz.
#
# Listeye yeni giriş eklerken:
#   * Uzun biçim önce gelmeli (ör. "koleksiyonlari" → "koleksiyonları" )
#     çünkü kısa biçim olan "kosu" onu maskelemeyecektir — tam-kelime
#     eşleşmesi uygulanır.
#   * Sadece ASCII Türkçe varyantı "farklı" ise ekleyin; yoksa gereksiz
#     normalizer turu oluşturur.
_REPLACEMENTS: list[tuple[str, str]] = [
    # Çok kelimeli ifadeler (öncelikli — tam kelime bu bileşik metni kapar)
    ("istege bagli", "isteğe bağlı"),
    ("hata mesaji", "hata mesajı"),
    ("sifremi unuttum", "şifremi unuttum"),
    ("son kullanici", "son kullanıcı"),

    # Uzun compound kelimeler (önce — kısa kök gelip yutmasın)
    ("koleksiyonlari", "koleksiyonları"),
    ("baglantisi", "bağlantısı"),
    ("kullanicilar", "kullanıcılar"),
    ("kullanici", "kullanıcı"),
    ("baglantili", "bağlantılı"),
    ("baglantida", "bağlantıda"),

    # Eylem/durum kökleri
    ("baglanti", "bağlantı"),
    ("baglan", "bağlan"),
    ("baslatildi", "başlatıldı"),
    ("baslatil", "başlatıl"),
    ("baslatiyor", "başlatıyor"),
    ("baslati", "başlatı"),
    ("baslat", "başlat"),
    ("baslang", "başlang"),
    ("basari", "başarı"),
    ("basarisiz", "başarısız"),
    ("basarili", "başarılı"),
    ("calistir", "çalıştır"),
    ("calisma", "çalışma"),
    ("calisan", "çalışan"),
    ("calis", "çalış"),
    ("cozumle", "çözümle"),
    ("cozum", "çözüm"),
    ("cozumleniyor", "çözümleniyor"),
    ("degisik", "değişik"),
    ("degisen", "değişen"),
    ("degisik", "değişik"),
    ("degistir", "değiştir"),
    ("degis", "değiş"),
    ("duzenle", "düzenle"),
    ("gecer", "geçer"),
    ("gecersiz", "geçersiz"),
    ("gercek", "gerçek"),
    ("gecmis", "geçmiş"),
    ("gonder", "gönder"),
    ("gorev", "görev"),
    ("gorevler", "görevler"),
    ("gozle", "gözle"),
    ("gozlemle", "gözlemle"),
    ("goruntule", "görüntüle"),
    ("goruntu", "görüntü"),
    ("hazirla", "hazırla"),
    ("hazirlan", "hazırlan"),
    ("hazir", "hazır"),
    ("ice", "içe"),
    ("icin", "için"),
    ("iceri", "içeri"),
    ("ilerleme", "ilerleme"),
    ("kaldir", "kaldır"),
    ("kaldiril", "kaldırıl"),
    ("kapali", "kapalı"),
    ("kesif", "keşif"),
    ("kesfet", "keşfet"),
    ("kirik", "kırık"),
    ("kosul", "koşul"),
    ("kosulmadi", "koşulmadı"),
    ("kosu", "koşu"),
    ("olcut", "ölçüt"),
    ("olcu", "ölçü"),
    ("olustur", "oluştur"),
    ("olusan", "oluşan"),
    ("olus", "oluş"),
    ("oneri", "öneri"),
    ("oner", "öner"),
    ("ozet", "özet"),
    ("ozellik", "özellik"),
    ("secili", "seçili"),
    ("sifre", "şifre"),
    ("sifir", "sıfır"),
    ("simdi", "şimdi"),
    ("test ediliyor", "test ediliyor"),
    ("tumunu", "tümünü"),
    ("tum", "tüm"),
    ("uret", "üret"),
    ("uretim", "üretim"),
    ("yukle", "yükle"),
    ("yuklen", "yüklen"),
    ("yaparak", "yaparak"),
    ("yonet", "yönet"),

    # Tekil kelimeler
    ("adim", "adım"),
    ("acik", "açık"),
    ("dokuman", "doküman"),
    ("giris", "giriş"),
    ("guncel", "güncel"),
    ("isaretli", "işaretli"),
    ("kisisel", "kişisel"),
    ("mesaji", "mesajı"),
    ("sonuc", "sonuç"),
    ("suresi", "süresi"),
    ("sirasinda", "sırasında"),
    ("sirasi", "sırası"),
    ("tasarimi", "tasarımı"),
    ("tasarim", "tasarım"),
    ("turu", "türü"),
    ("varsayilan", "varsayılan"),
    ("yanit", "yanıt"),
]

# Büyük/küçük harf varyantlarını otomatik üret (ilk harf büyük, tümü büyük)
def _case_variants(pair: tuple[str, str]) -> list[tuple[str, str]]:
    asc, tr = pair
    seen: set[str] = set()
    variants: list[tuple[str, str]] = []

    def _add(a: str, t: str) -> None:
        if a != t and a not in seen:
            seen.add(a)
            variants.append((a, t))

    _add(asc, tr)
    if asc and asc[0].isalpha():
        # Baş harf büyük
        _add(asc[0].upper() + asc[1:], tr[0].upper() + tr[1:])
        # Türkçe "I" özel: baştaki "I" çoğu zaman "İ" olmalı
        if asc[0].lower() == "i":
            _add("İ" + asc[1:], tr[0].upper() + tr[1:])
    return variants


ALL_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = []
# Tam kelime eşleşmesi — hem öncesinde hem sonrasında ASCII/Türkçe/underscore/
# rakam olmamalı. Böylece `oner` ifadesi `onerror` identifier'ının içinden
# kapılmaz; bu kural önceki regresyonun (`es.önerror`) tekrarını engeller.
_WORD_CHAR = r"[A-Za-z0-9_ıİğĞüÜşŞöÖçÇ]"
for base_pair in _REPLACEMENTS:
    for asc, tr in _case_variants(base_pair):
        pattern = re.compile(
            rf"(?<!{_WORD_CHAR}){re.escape(asc)}(?!{_WORD_CHAR})",
        )
        ALL_REPLACEMENTS.append((pattern, tr))


# ── Yalnızca JSX text ve string literal'leri dönüştür ───────────────────────
# Basitleştirilmiş strateji: satırlarda `data-testid=`, `className=`, import,
# require, url içeren bölümleri atla; diğer satırlardaki düz metni normalize et.
_SKIP_PATTERNS = [
    re.compile(r"\bdata-testid\s*="),
    re.compile(r"\bclassName\s*="),
    re.compile(r"\bclass\s*="),
    re.compile(r"\bimport\s+"),
    re.compile(r"\bfrom\s+[\"']"),
    re.compile(r"\brequire\s*\("),
    re.compile(r"https?://"),
    re.compile(r"\.(png|jpg|jpeg|svg|webp|gif|ico)\b"),
    # Storage key sabitleri (localStorage.setItem("twai_session"))
    re.compile(r"\blocalStorage\."),
    re.compile(r"\bsessionStorage\."),
    re.compile(r"\bdocument\.cookie"),
]


def _should_skip_line(line: str) -> bool:
    return any(pat.search(line) for pat in _SKIP_PATTERNS)


def normalize_line(line: str) -> tuple[str, list[tuple[str, str]]]:
    """Satırı normalize eder ve değişim listesi döner."""
    if _should_skip_line(line):
        return line, []

    changes: list[tuple[str, str]] = []
    new_line = line
    for pattern, tr in ALL_REPLACEMENTS:
        matches = list(pattern.finditer(new_line))
        if not matches:
            continue
        for m in matches:
            changes.append((m.group(0), tr))
        new_line = pattern.sub(tr, new_line)
    return new_line, changes


# ── Dosya işleme ────────────────────────────────────────────────────────────
def walk_targets(root: Path) -> list[Path]:
    # .ts/.tsx frontend; .py backend — her iki tarafta da aynı kurallar.
    patterns = ["**/*.tsx", "**/*.ts", "**/*.py"]
    excludes = {
        "node_modules",
        ".next",
        ".turbo",
        "dist",
        "build",
        "out",
        "__pycache__",
        ".venv",
        "venv",
        "alembic/versions",  # migration dosyaları — text değil
    }

    result: list[Path] = []
    for pat in patterns:
        for path in root.glob(pat):
            if any(part in excludes for part in path.parts):
                continue
            result.append(path)
    return sorted(set(result))


def process_file(path: Path, apply: bool) -> tuple[int, list[str]]:
    """Dosyayı işler. Döner: (değişim sayısı, rapor satırları)."""
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return 0, []

    out_lines: list[str] = []
    report: list[str] = []
    total_changes = 0

    for idx, line in enumerate(original.splitlines(keepends=True), 1):
        new_line, changes = normalize_line(line)
        out_lines.append(new_line)
        if changes:
            total_changes += len(changes)
            for old, new in changes:
                report.append(f"  {path}:{idx}  {old!r} → {new!r}")

    if apply and total_changes:
        path.write_text("".join(out_lines), encoding="utf-8")

    return total_changes, report


def main() -> int:
    parser = argparse.ArgumentParser(description="TR karakter normalize.")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--dry-run", action="store_true", help="Değişimleri listele, yazma.")
    grp.add_argument("--apply", action="store_true", help="Değişimleri dosyalara yaz.")
    grp.add_argument(
        "--check-only",
        action="store_true",
        help="Değişim gerektirecek bir şey varsa exit 1 (CI gate).",
    )
    parser.add_argument(
        "--root",
        default="apps/web",
        help="Hedef kök dizin (default: apps/web).",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"HATA: {root} bulunamadı", file=sys.stderr)
        return 2

    targets = walk_targets(root)
    total = 0
    all_reports: list[str] = []
    for path in targets:
        count, report = process_file(path, apply=args.apply)
        if count:
            total += count
            all_reports.extend(report)

    if all_reports:
        print("\n".join(all_reports[:200]))
        if len(all_reports) > 200:
            print(f"… +{len(all_reports) - 200} daha")

    print(f"\nToplam: {total} değişim, {len({r.split()[0] for r in all_reports})} dosya")

    if args.check_only and total > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
