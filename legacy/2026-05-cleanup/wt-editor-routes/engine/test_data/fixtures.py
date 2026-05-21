"""
engine/test_data/fixtures.py — Test veri yardımcıları

JSON fixture dosyalarını yükler ve algoritmik olarak geçerli
Türk bankacılık test verileri üretir (TCKN, IBAN, telefon vb.).
"""

from __future__ import annotations

import json
import random
import string
from pathlib import Path
from typing import Any, Optional

_DATA_DIR = Path(__file__).resolve().parent

# ── Sabit listeler ────────────────────────────────────────────────────────────

_TURKISH_FIRST_NAMES_MALE = [
    "Ahmet", "Mehmet", "Mustafa", "Ali", "Hüseyin", "Hasan", "İbrahim",
    "Ömer", "Yusuf", "Murat", "Emre", "Burak", "Fatih", "Kerem", "Serkan",
    "Oğuz", "Barış", "Cem", "Deniz", "Eren",
]

_TURKISH_FIRST_NAMES_FEMALE = [
    "Fatma", "Ayşe", "Emine", "Hatice", "Zeynep", "Elif", "Merve",
    "Büşra", "Özge", "Şeyma", "Selin", "Defne", "İrem", "Gül", "Ceren",
    "Burcu", "Dilek", "Nihan", "Pınar", "Yasemin",
]

_TURKISH_LAST_NAMES = [
    "Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Yıldırım",
    "Öztürk", "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan",
    "Çetin", "Kara", "Koç", "Kurt", "Özkan", "Şimşek", "Polat", "Korkmaz",
    "Erdoğan", "Acar", "Güneş", "Aktaş", "Taş", "Bulut", "Kaplan", "Ünal",
]

_BANK_CODES = [
    "00010", "00012", "00015", "00046", "00062",
    "00064", "00067", "00099", "00111", "00134",
]

_PHONE_PREFIXES = [
    "530", "531", "532", "533", "534", "535", "536", "537", "538", "539",
    "540", "541", "542", "543", "544", "545", "546", "547", "548", "549",
    "550", "551", "552", "553", "554", "555", "556", "557", "558", "559",
]

# ── JSON yükleme ─────────────────────────────────────────────────────────────


def load_test_data(filename: str) -> Any:
    """test_data/ dizininden bir JSON dosyası yükler ve Python nesnesine çevirir."""
    filepath = _DATA_DIR / filename
    with open(filepath, encoding="utf-8") as fh:
        return json.load(fh)


# ── Kolay erişim fonksiyonları ────────────────────────────────────────────────


def get_admin_user() -> dict:
    """Admin kullanıcı verisini döndürür."""
    data = load_test_data("users.json")
    for user in data["users"]:
        if user["role"] == "admin":
            return user
    raise ValueError("Admin kullanıcı bulunamadı")


def get_user_by_role(role: str) -> dict:
    """Belirtilen role sahip ilk kullanıcıyı döndürür."""
    data = load_test_data("users.json")
    for user in data["users"]:
        if user["role"] == role:
            return user
    raise ValueError(f"'{role}' rolüne sahip kullanıcı bulunamadı")


def get_test_projects() -> list[dict]:
    """Tüm test projelerini döndürür."""
    return load_test_data("projects.json")["projects"]


def get_test_scenarios() -> list[dict]:
    """Tüm test senaryolarını döndürür."""
    return load_test_data("scenarios.json")["scenarios"]


def get_scenarios_by_project(project_id: str) -> list[dict]:
    """Belirli bir projeye ait senaryoları döndürür."""
    return [s for s in get_test_scenarios() if s["project_id"] == project_id]


def get_api_payload(name: str) -> dict:
    """İsme göre API payload verisini döndürür."""
    data = load_test_data("api_payloads.json")
    payload = data["payloads"].get(name)
    if payload is None:
        available = ", ".join(data["payloads"].keys())
        raise ValueError(f"'{name}' payload bulunamadı. Mevcut: {available}")
    return payload


def get_environment(env_name: str) -> dict:
    """Ortam konfigürasyonunu döndürür (dev / staging / production)."""
    data = load_test_data("environments.json")
    env = data["environments"].get(env_name)
    if env is None:
        available = ", ".join(data["environments"].keys())
        raise ValueError(f"'{env_name}' ortamı bulunamadı. Mevcut: {available}")
    return env


def get_locators(page_name: str) -> dict:
    """Sayfa adına göre UI element seçicilerini döndürür."""
    data = load_test_data("locator_test_data.json")
    page = data["pages"].get(page_name)
    if page is None:
        available = ", ".join(data["pages"].keys())
        raise ValueError(f"'{page_name}' sayfası bulunamadı. Mevcut: {available}")
    return page


# ── Rastgele Türk bankacılık verisi üreticileri ──────────────────────────────


def random_turkish_name() -> str:
    """Rastgele bir Türk ad-soyad çifti döndürür (ör. 'Elif Kaya')."""
    first_names = _TURKISH_FIRST_NAMES_MALE + _TURKISH_FIRST_NAMES_FEMALE
    return f"{random.choice(first_names)} {random.choice(_TURKISH_LAST_NAMES)}"


def random_turkish_first_name(*, gender: Optional[str] = None) -> str:
    """Rastgele Türk adı döndürür. gender='M' veya 'F' ile cinsiyete göre."""
    if gender and gender.upper() == "M":
        return random.choice(_TURKISH_FIRST_NAMES_MALE)
    if gender and gender.upper() in ("F", "K"):
        return random.choice(_TURKISH_FIRST_NAMES_FEMALE)
    return random.choice(_TURKISH_FIRST_NAMES_MALE + _TURKISH_FIRST_NAMES_FEMALE)


def random_turkish_last_name() -> str:
    """Rastgele Türk soyadı döndürür."""
    return random.choice(_TURKISH_LAST_NAMES)


def random_tckn() -> str:
    """
    Algoritmik olarak geçerli 11 haneli TC Kimlik Numarası üretir.

    Kurallar:
      - İlk hane 0 olamaz.
      - 10. hane: ((d1+d3+d5+d7+d9)*7 - (d2+d4+d6+d8)) mod 10
      - 11. hane: (d1+d2+d3+d4+d5+d6+d7+d8+d9+d10) mod 10
    """
    digits = [random.randint(1, 9)]  # d1: 1-9
    for _ in range(8):
        digits.append(random.randint(0, 9))  # d2..d9

    odds_sum = digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
    evens_sum = digits[1] + digits[3] + digits[5] + digits[7]
    d10 = (odds_sum * 7 - evens_sum) % 10
    digits.append(d10)

    d11 = sum(digits) % 10
    digits.append(d11)

    return "".join(str(d) for d in digits)


def validate_tckn(tckn: str) -> bool:
    """Verilen TCKN'nin algoritmik olarak geçerli olup olmadığını kontrol eder."""
    if not tckn or len(tckn) != 11 or not tckn.isdigit() or tckn[0] == "0":
        return False
    d = [int(c) for c in tckn]
    check10 = (sum(d[i] for i in range(0, 9, 2)) * 7 - sum(d[i] for i in range(1, 8, 2))) % 10
    if check10 != d[9]:
        return False
    check11 = sum(d[:10]) % 10
    return check11 == d[10]


def random_iban(bank_code: Optional[str] = None) -> str:
    """
    Geçerli kontrol basamaklı TR IBAN üretir.

    Format: TR + 2 kontrol hanesi + 5 banka kodu + 1 rezerv (0) + 16 hesap no
    Toplam: 26 karakter

    Kontrol basamağı ISO 13616 (mod-97) algoritmasına göre hesaplanır.
    """
    if bank_code is None:
        bank_code = random.choice(_BANK_CODES)

    reserve = "0"
    account_no = "".join(str(random.randint(0, 9)) for _ in range(16))
    bban = bank_code + reserve + account_no  # 22 haneli

    # ISO 13616: BBAN + ülke kodu (T=29, R=17) + kontrol yeri tutucu "00"
    numeric_str = bban + "291700"
    check = 98 - (int(numeric_str) % 97)
    check_digits = f"{check:02d}"

    return f"TR{check_digits}{bban}"


def validate_iban(iban: str) -> bool:
    """TR IBAN'ının mod-97 kontrolünü doğrular."""
    if not iban or len(iban) != 26 or not iban.startswith("TR"):
        return False
    rearranged = iban[4:] + "2917" + iban[2:4]
    try:
        return int(rearranged) % 97 == 1
    except ValueError:
        return False


def random_phone() -> str:
    """+90 5XX XXX XX XX formatında Türk cep telefonu numarası üretir."""
    prefix = random.choice(_PHONE_PREFIXES)
    rest = "".join(str(random.randint(0, 9)) for _ in range(7))
    return f"+90 {prefix} {rest[:3]} {rest[3:5]} {rest[5:7]}"


def random_email(first_name: Optional[str] = None, last_name: Optional[str] = None) -> str:
    """Türkçe uyumlu e-posta adresi üretir."""
    _tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    if first_name is None:
        first_name = random_turkish_first_name()
    if last_name is None:
        last_name = random_turkish_last_name()
    local = f"{first_name.lower()}.{last_name.lower()}".translate(_tr_map)
    domain = random.choice(["gmail.com", "hotmail.com", "outlook.com", "yahoo.com"])
    return f"{local}@{domain}"


def random_currency_amount(
    min_val: float = 1.0,
    max_val: float = 100000.0,
) -> str:
    """Rastgele TL tutarı üretir (ör. '12345.67')."""
    amount = round(random.uniform(min_val, max_val), 2)
    return f"{amount:.2f}"


def random_account_number() -> str:
    """16 haneli rastgele hesap numarası üretir."""
    return "".join(str(random.randint(0, 9)) for _ in range(16))


def random_customer_id() -> str:
    """CIF formatında müşteri numarası üretir (ör. 'CIF-0012345678')."""
    num = random.randint(1, 9999999999)
    return f"CIF-{num:010d}"
