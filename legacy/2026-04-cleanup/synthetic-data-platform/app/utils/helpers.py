"""
Yardımcı fonksiyonlar — Bankacılık domainine özel doğrulama ve araçlar.

TCKN doğrulama, IBAN doğrulama, telefon normalizasyon, email validasyon,
pattern eşleştirme ve kolon ismi normalleştirme gibi sık kullanılan
fonksiyonları içerir.
"""

import re
import unicodedata
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════════════
# TCKN (T.C. Kimlik Numarası) Doğrulama
# ═══════════════════════════════════════════════════════════════════════


def validate_tckn(value: str) -> bool:
    """
    T.C. Kimlik Numarasını algoritmik olarak doğrular.

    Kurallar:
    - Tam 11 haneli olmalı
    - İlk hane 0 olamaz
    - 10. hane: ((d1+d3+d5+d7+d9)*7 - (d2+d4+d6+d8)) % 10
    - 11. hane: (d1+d2+...+d10) % 10

    Args:
        value: Doğrulanacak TCKN string'i

    Returns:
        Geçerli ise True, değilse False
    """
    # Temizle — boşluk ve tire kaldır
    value = value.strip().replace(" ", "").replace("-", "")

    # Uzunluk ve sayısal kontrol
    if len(value) != 11 or not value.isdigit():
        return False

    # İlk hane 0 olamaz
    if value[0] == "0":
        return False

    digits = [int(d) for d in value]

    # 10. hane kontrolü
    odd_sum = digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
    even_sum = digits[1] + digits[3] + digits[5] + digits[7]
    check_10 = (odd_sum * 7 - even_sum) % 10
    if check_10 != digits[9]:
        return False

    # 11. hane kontrolü
    total = sum(digits[:10])
    check_11 = total % 10
    if check_11 != digits[10]:
        return False

    return True


def is_tckn_pattern(value: str) -> bool:
    """
    Bir değerin TCKN formatına uygun olup olmadığını kontrol eder.
    Tam algoritmik doğrulama yapmaz, sadece format kontrolü yapar.
    """
    value = str(value).strip().replace(" ", "").replace("-", "")
    return bool(re.match(r"^[1-9]\d{10}$", value))


# ═══════════════════════════════════════════════════════════════════════
# IBAN Doğrulama
# ═══════════════════════════════════════════════════════════════════════


def validate_iban(value: str) -> bool:
    """
    IBAN numarasını doğrular (ISO 13616 standardı).

    Türkiye IBAN formatı: TR + 2 kontrol hanesi + 5 banka kodu + 1 ayrılmış + 16 hesap no
    Toplam: 26 karakter

    Args:
        value: Doğrulanacak IBAN string'i

    Returns:
        Geçerli ise True, değilse False
    """
    # Temizle — boşluk, tire kaldır ve büyük harfe çevir
    value = value.strip().replace(" ", "").replace("-", "").upper()

    # Türk IBAN'ı kontrolü (TR ile başlar, 26 karakter)
    if value.startswith("TR"):
        if len(value) != 26:
            return False
    elif len(value) < 15 or len(value) > 34:
        return False

    # Alfanümerik kontrol
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]+$", value):
        return False

    # Mod-97 doğrulama (ISO 7064)
    rearranged = value[4:] + value[:4]
    numeric_str = ""
    for char in rearranged:
        if char.isdigit():
            numeric_str += char
        else:
            numeric_str += str(ord(char) - ord("A") + 10)

    return int(numeric_str) % 97 == 1


def is_iban_pattern(value: str) -> bool:
    """Bir değerin Türk IBAN formatına uygun olup olmadığını kontrol eder."""
    value = str(value).strip().replace(" ", "").replace("-", "").upper()
    return bool(re.match(r"^TR\d{24}$", value))


# ═══════════════════════════════════════════════════════════════════════
# Telefon Numarası Doğrulama ve Normalizasyon
# ═══════════════════════════════════════════════════════════════════════


# Türk telefon numarası pattern'ları
PHONE_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\+90\s?\d{3}\s?\d{3}\s?\d{2}\s?\d{2}$"),       # +90 5XX XXX XX XX
    re.compile(r"^0\d{3}\s?\d{3}\s?\d{2}\s?\d{2}$"),              # 05XX XXX XX XX
    re.compile(r"^\(5\d{2}\)\s?\d{3}\s?\d{2}\s?\d{2}$"),          # (5XX) XXX XX XX
    re.compile(r"^5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}$"),              # 5XX XXX XX XX
    re.compile(r"^\+90\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}$"),  # +90 (5XX) XXX-XX-XX
    re.compile(r"^0\d{10}$"),                                      # 05XXXXXXXXX (11 hane)
]


def is_phone_pattern(value: str) -> bool:
    """Bir değerin Türk telefon numarası formatına uyup uymadığını kontrol eder."""
    value = str(value).strip()
    return any(p.match(value) for p in PHONE_PATTERNS)


def normalize_phone(value: str) -> Optional[str]:
    """
    Türk telefon numarasını +90XXXXXXXXXX formatına normalleştirir.

    Desteklenen giriş formatları:
    - +90 532 123 45 67
    - 05321234567
    - (532) 123 45 67
    - 532 123 45 67
    - +90 (532) 123-45-67

    Args:
        value: Ham telefon numarası string'i

    Returns:
        Normalleştirilmiş telefon numarası (+90XXXXXXXXXX) veya None
    """
    if value is None:
        return None

    # Tüm non-digit karakterleri temizle (+ hariç önce kontrol et)
    raw = str(value).strip()
    has_plus90 = raw.startswith("+90")

    # Sadece rakamları al
    digits = re.sub(r"\D", "", raw)

    # Farklı uzunluklara göre normalleştir
    if has_plus90 and len(digits) == 12 and digits.startswith("90"):
        # +905321234567 → +905321234567
        return f"+{digits}"
    elif len(digits) == 12 and digits.startswith("90"):
        # 905321234567
        return f"+{digits}"
    elif len(digits) == 11 and digits.startswith("0"):
        # 05321234567
        return f"+90{digits[1:]}"
    elif len(digits) == 10 and digits.startswith("5"):
        # 5321234567
        return f"+90{digits}"
    else:
        return None


# ═══════════════════════════════════════════════════════════════════════
# Email Doğrulama
# ═══════════════════════════════════════════════════════════════════════

EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


def is_email_pattern(value: str) -> bool:
    """Bir değerin email formatına uyup uymadığını kontrol eder."""
    return bool(EMAIL_PATTERN.match(str(value).strip()))


def validate_email(value: str) -> bool:
    """
    Email adresini doğrular.

    Basit regex kontrolünün ötesinde ek doğrulamalar yapar:
    - Format kontrolü (regex)
    - Domain uzunluk kontrolü
    - Yaygın geçersiz domain'leri reddetme

    Args:
        value: Doğrulanacak email adresi

    Returns:
        Geçerli ise True, değilse False
    """
    value = str(value).strip().lower()

    # Temel format kontrolü
    if not EMAIL_PATTERN.match(value):
        return False

    # @ işaretinden böl
    local_part, domain = value.rsplit("@", 1)

    # Local part uzunluk kontrolü (RFC 5321)
    if len(local_part) > 64:
        return False

    # Domain uzunluk kontrolü
    if len(domain) > 253:
        return False

    # Domain en az bir nokta içermeli
    if "." not in domain:
        return False

    # TLD en az 2 karakter olmalı
    tld = domain.rsplit(".", 1)[-1]
    if len(tld) < 2:
        return False

    return True


# ═══════════════════════════════════════════════════════════════════════
# URL Doğrulama
# ═══════════════════════════════════════════════════════════════════════

URL_PATTERN = re.compile(
    r"^https?://[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*"
    r"(:\d+)?(/[^\s]*)?$"
)


def is_url_pattern(value: str) -> bool:
    """Bir değerin URL formatına uyup uymadığını kontrol eder."""
    return bool(URL_PATTERN.match(str(value).strip()))


# ═══════════════════════════════════════════════════════════════════════
# Tarih Formatı Tespiti
# ═══════════════════════════════════════════════════════════════════════

DATE_PATTERNS: dict[str, re.Pattern] = {
    "dd.mm.yyyy": re.compile(r"^\d{2}\.\d{2}\.\d{4}$"),
    "yyyy-mm-dd": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "dd/mm/yyyy": re.compile(r"^\d{2}/\d{2}/\d{4}$"),
    "mm/dd/yyyy": re.compile(r"^\d{2}/\d{2}/\d{4}$"),
    "dd-mm-yyyy": re.compile(r"^\d{2}-\d{2}-\d{4}$"),
    "yyyy/mm/dd": re.compile(r"^\d{4}/\d{2}/\d{2}$"),
    "dd.mm.yyyy HH:MM": re.compile(r"^\d{2}\.\d{2}\.\d{4}\s\d{2}:\d{2}$"),
    "yyyy-mm-dd HH:MM:SS": re.compile(r"^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$"),
    "dd/mm/yyyy HH:MM:SS": re.compile(r"^\d{2}/\d{2}/\d{4}\s\d{2}:\d{2}:\d{2}$"),
    "ISO 8601": re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"),
}


def detect_date_format(value: str) -> Optional[str]:
    """
    Bir string değerin tarih formatını tespit eder.

    Returns:
        Tespit edilen format string'i veya None
    """
    value = str(value).strip()
    for fmt_name, pattern in DATE_PATTERNS.items():
        if pattern.match(value):
            return fmt_name
    return None


def is_date_pattern(value: str) -> bool:
    """Bir değerin herhangi bir tarih formatına uyup uymadığını kontrol eder."""
    return detect_date_format(value) is not None


# ═══════════════════════════════════════════════════════════════════════
# Para Birimi Tespiti
# ═══════════════════════════════════════════════════════════════════════

CURRENCY_PATTERNS: dict[str, re.Pattern] = {
    "TRY": re.compile(r"^[\d.,]+\s*(TL|₺|TRY)$|^(TL|₺|TRY)\s*[\d.,]+$", re.IGNORECASE),
    "USD": re.compile(r"^[\d.,]+\s*(\$|USD)$|^(\$|USD)\s*[\d.,]+$", re.IGNORECASE),
    "EUR": re.compile(r"^[\d.,]+\s*(€|EUR)$|^(€|EUR)\s*[\d.,]+$", re.IGNORECASE),
}


def detect_currency(value: str) -> Optional[str]:
    """Bir string değerdeki para birimini tespit eder."""
    value = str(value).strip()
    for currency, pattern in CURRENCY_PATTERNS.items():
        if pattern.match(value):
            return currency
    return None


# ═══════════════════════════════════════════════════════════════════════
# Hesap ve Müşteri Numarası Pattern'ları
# ═══════════════════════════════════════════════════════════════════════

# Banka hesap numarası: genellikle 10-16 haneli sayısal
ACCOUNT_NUMBER_PATTERN = re.compile(r"^\d{10,16}$")

# Müşteri numarası: genellikle 6-12 haneli sayısal veya alfanümerik prefix ile
CUSTOMER_NUMBER_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\d{6,12}$"),                              # Sadece rakam
    re.compile(r"^(MUS|CUS|MTR|BRC)\d{6,10}$", re.IGNORECASE),  # Prefix'li
]


def is_account_number_pattern(value: str) -> bool:
    """Bir değerin banka hesap numarası formatına uyup uymadığını kontrol eder."""
    return bool(ACCOUNT_NUMBER_PATTERN.match(str(value).strip()))


def is_customer_number_pattern(value: str) -> bool:
    """Bir değerin müşteri numarası formatına uyup uymadığını kontrol eder."""
    value = str(value).strip()
    return any(p.match(value) for p in CUSTOMER_NUMBER_PATTERNS)


# ═══════════════════════════════════════════════════════════════════════
# Kredi Kartı Numarası Tespiti
# ═══════════════════════════════════════════════════════════════════════

CREDIT_CARD_PATTERN = re.compile(r"^\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}$")


def is_credit_card_pattern(value: str) -> bool:
    """
    Bir değerin kredi kartı numarası formatına uyup uymadığını kontrol eder.
    Luhn algoritması ile doğrulama yapmaz, sadece format kontrolü.
    """
    return bool(CREDIT_CARD_PATTERN.match(str(value).strip()))


def validate_luhn(value: str) -> bool:
    """
    Luhn algoritması ile kredi kartı / kart numarası doğrulaması yapar.

    Args:
        value: Doğrulanacak kart numarası

    Returns:
        Geçerli ise True, değilse False
    """
    digits_only = re.sub(r"\D", "", str(value).strip())
    if not digits_only or len(digits_only) < 13 or len(digits_only) > 19:
        return False

    total = 0
    reverse_digits = digits_only[::-1]
    for i, d in enumerate(reverse_digits):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


# ═══════════════════════════════════════════════════════════════════════
# Kolon İsmi Normalleştirme
# ═══════════════════════════════════════════════════════════════════════


def normalize_column_name(name: str) -> str:
    """
    Kolon ismini normalleştirir.

    Yapılan işlemler:
    - Baş/son boşluk temizleme
    - Türkçe karakterleri ASCII'ye çevirme
    - Küçük harfe çevirme
    - Boşluk ve özel karakterleri alt çizgiye çevirme
    - Ardışık alt çizgileri teke düşürme
    - Baştaki/sondaki alt çizgileri kaldırma

    Args:
        name: Ham kolon ismi

    Returns:
        Normalleştirilmiş kolon ismi
    """
    # Boşlukları temizle
    name = name.strip()

    # Türkçe karakter dönüşümü
    tr_map = str.maketrans({
        "ç": "c", "Ç": "C",
        "ğ": "g", "Ğ": "G",
        "ı": "i", "İ": "I",
        "ö": "o", "Ö": "O",
        "ş": "s", "Ş": "S",
        "ü": "u", "Ü": "U",
    })
    name = name.translate(tr_map)

    # Unicode normalleştirme ve ASCII'ye çevirme
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")

    # Küçük harfe çevir
    name = name.lower()

    # Boşluk ve özel karakterleri alt çizgiye çevir
    name = re.sub(r"[^a-z0-9_]", "_", name)

    # Ardışık alt çizgileri teke düşür
    name = re.sub(r"_+", "_", name)

    # Baş/son alt çizgileri kaldır
    name = name.strip("_")

    return name


# ═══════════════════════════════════════════════════════════════════════
# JSON Düzleştirme (Flatten)
# ═══════════════════════════════════════════════════════════════════════


def flatten_json(
    nested: dict,
    parent_key: str = "",
    separator: str = "_",
) -> dict:
    """
    İç içe (nested) JSON yapısını düz (flat) bir dict'e dönüştürür.

    Örnek:
        {"adres": {"il": "İstanbul", "ilce": "Kadıköy"}}
        →
        {"adres_il": "İstanbul", "adres_ilce": "Kadıköy"}

    Args:
        nested: Düzleştirilecek iç içe dict
        parent_key: Üst anahtar (rekürsif kullanım için)
        separator: Anahtar birleştirici karakter

    Returns:
        Düzleştirilmiş dict
    """
    items: list[tuple[str, object]] = []
    for key, value in nested.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        if isinstance(value, dict):
            items.extend(flatten_json(value, new_key, separator).items())
        elif isinstance(value, list):
            # Liste ise ilk elemanı kontrol et
            if value and isinstance(value[0], dict):
                # Dict listesi — her birini düzleştir (sadece ilk elemanın yapısını kullan)
                items.extend(flatten_json(value[0], new_key, separator).items())
            else:
                items.append((new_key, value))
        else:
            items.append((new_key, value))
    return dict(items)


# ═══════════════════════════════════════════════════════════════════════
# Dosya Boyutu Formatlama
# ═══════════════════════════════════════════════════════════════════════


def format_file_size(size_bytes: int) -> str:
    """
    Bayt cinsinden dosya boyutunu okunabilir formata çevirir.

    Args:
        size_bytes: Dosya boyutu (bayt)

    Returns:
        Okunabilir format (ör. "14.5 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"


# ═══════════════════════════════════════════════════════════════════════
# Güvenli Tip Dönüşümleri
# ═══════════════════════════════════════════════════════════════════════


def safe_float(value: Any) -> Optional[float]:
    """
    Değeri güvenli bir şekilde float'a çevirir.
    Başarısız olursa None döner, exception fırlatmaz.
    """
    if value is None:
        return None
    try:
        # Türk sayı formatı: 1.234,56 → 1234.56
        s = str(value).strip()
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except (ValueError, TypeError):
        return None


def safe_int(value: Any) -> Optional[int]:
    """
    Değeri güvenli bir şekilde int'e çevirir.
    Başarısız olursa None döner, exception fırlatmaz.
    """
    if value is None:
        return None
    try:
        f = safe_float(value)
        if f is not None:
            return int(f)
        return None
    except (ValueError, TypeError, OverflowError):
        return None
