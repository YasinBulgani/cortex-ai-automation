"""
Kredi/Banka kartı üretim modülü.
Luhn algoritması ile geçerli kart numarası üretir.
Troy (9792), Visa (4), Mastercard (51-55) prefix desteği.
"""
import random
from typing import Literal

CardType = Literal['troy', 'troy_debit', 'visa', 'visa_debit', 'mastercard']

CARD_PREFIXES = {
    'troy':        ['9792'],
    'troy_debit':  ['9792'],
    'visa':        ['4539', '4556', '4916', '4532', '4929'],
    'visa_debit':  ['4485', '4716'],
    'mastercard':  ['5100', '5200', '5300', '5400', '5500', '5101', '5201'],
}


def luhn_check(number: str) -> bool:
    """Luhn algoritması ile kart numarasını doğrular."""
    digits = [int(d) for d in number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for d in even_digits:
        total += sum(divmod(d * 2, 10))
    return total % 10 == 0


def generate_card_number(card_type: CardType = 'troy', seed: int = None) -> str:
    """Luhn geçerli kart numarası üretir."""
    if seed is not None:
        random.seed(seed)
    prefixes = CARD_PREFIXES.get(card_type, CARD_PREFIXES['troy'])
    prefix = random.choice(prefixes)
    target_length = 16
    partial = prefix + ''.join([str(random.randint(0, 9)) for _ in range(target_length - len(prefix) - 1)])
    for check in range(10):
        candidate = partial + str(check)
        if luhn_check(candidate):
            return candidate
    return partial + '0'


def generate_card_expiry(min_years: int = 1, max_years: int = 5) -> str:
    """Kart son kullanma tarihi üretir: MM/YY formatında."""
    import datetime
    now = datetime.datetime.now()
    years_ahead = random.randint(min_years, max_years)
    exp_year = now.year + years_ahead
    exp_month = random.randint(1, 12)
    return f"{exp_month:02d}/{str(exp_year)[2:]}"


def generate_cvv(card_type: CardType = 'troy') -> str:
    """CVV/CVC üretir. Tüm haneler aynı olamaz."""
    length = 4 if card_type == 'amex' else 3
    while True:
        cvv = ''.join([str(random.randint(0, 9)) for _ in range(length)])
        if len(set(cvv)) > 1 and cvv not in ('000', '0000'):
            return cvv


def mask_card_number(card: str) -> str:
    """Kart numarasını maskeler: 4539 **** **** 1234"""
    return card[:4] + ' **** **** ' + card[-4:]
