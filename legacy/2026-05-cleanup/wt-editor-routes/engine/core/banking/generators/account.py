"""
TR IBAN, Hesap No, SWIFT/BIC üretim modülü.
ISO 13616 MOD-97-10 checksum.
"""
import random
from typing import Optional, Dict

TR_BANK_CODES: Dict[str, str] = {
    '00010': 'Ziraat Bankası',
    '00012': 'Halkbank',
    '00015': 'Yapı Kredi',
    '00046': 'Akbank',
    '00047': 'Vakıfbank',
    '00062': 'Garanti BBVA',
    '00064': 'İş Bankası',
    '00059': 'Şekerbank',
    '00111': 'Finansbank (QNB)',
    '00134': 'Denizbank',
    '00203': 'Alternatifbank',
    '00302': 'TEB',
    '00309': 'ING Bank',
    '00400': 'HSBC',
}

TR_SWIFT_CODES: Dict[str, str] = {
    '00010': 'TCZBTR2A',
    '00012': 'TRHBTR2A',
    '00015': 'YAPITRISFXX',
    '00046': 'AKBKTRIS',
    '00047': 'TVBATR2A',
    '00062': 'TGBATRIS',
    '00064': 'ISBKTRIS',
    '00059': 'SEKETR2A',
    '00111': 'FNNBTR2X',
    '00134': 'DENITRIS',
    '00302': 'TEBUTRIS',
    '00309': 'INGBTR2X',
    '00400': 'HSBCTRIS',
}


def generate_tr_iban(bank_code: Optional[str] = None, seed: int = None) -> str:
    """ISO 13616 MOD-97-10 ile geçerli TR IBAN üretir."""
    if seed is not None:
        random.seed(seed)
    if bank_code is None:
        bank_code = random.choice(list(TR_BANK_CODES.keys()))
    rezerv = '0'
    account_no = ''.join([str(random.randint(0, 9)) for _ in range(16)])
    bban = bank_code + rezerv + account_no  # 22 hane
    # MOD-97-10 checksum
    check_str = bban + 'TR00'
    numeric = ''
    for c in check_str:
        if c.isalpha():
            numeric += str(ord(c) - 55)
        else:
            numeric += c
    check_digit = 98 - (int(numeric) % 97)
    return f"TR{check_digit:02d}{bban}"


def validate_tr_iban(iban: str) -> bool:
    """TR IBAN doğrular."""
    if not isinstance(iban, str) or len(iban) != 26:
        return False
    if not iban.startswith('TR'):
        return False
    rearranged = iban[4:] + iban[:4]
    numeric = ''
    for c in rearranged:
        if c.isalpha():
            numeric += str(ord(c) - 55)
        else:
            numeric += c
    return int(numeric) % 97 == 1


def generate_account_number(seed: int = None) -> str:
    """16 haneli hesap numarası üretir."""
    if seed is not None:
        random.seed(seed)
    return ''.join([str(random.randint(0, 9)) for _ in range(16)])


def generate_swift(bank_code: Optional[str] = None, branch: bool = False) -> str:
    """Türk banka SWIFT/BIC kodu üretir."""
    if bank_code and bank_code in TR_SWIFT_CODES:
        swift8 = TR_SWIFT_CODES[bank_code]
    else:
        swift8 = random.choice(list(TR_SWIFT_CODES.values()))
    # 8 haneli base kodu normalize et
    if len(swift8) > 8:
        swift8 = swift8[:8]
    if branch:
        suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=3))
        return swift8 + suffix
    return swift8 + 'XXX'


def get_bank_list() -> list:
    """Türk banka kodu ve adı listesi döndürür."""
    return [
        {'code': k, 'name': v, 'swift': TR_SWIFT_CODES.get(k, 'N/A')}
        for k, v in TR_BANK_CODES.items()
    ]
