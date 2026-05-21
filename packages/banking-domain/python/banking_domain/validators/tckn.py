"""
TCKN (TC Kimlik No) — MERNIS algoritması.

11 haneli. Kurallar:
  1. İlk hane sıfır olamaz
  2. Tüm haneler rakam
  3. 10. hane: ((d1+d3+d5+d7+d9) * 7 - (d2+d4+d6+d8)) mod 10
  4. 11. hane: (d1+d2+...+d10) mod 10
"""
from __future__ import annotations

import random


TCKN_LENGTH = 11


def validate_tckn(tckn: str | None) -> bool:
    """MERNIS algoritmasıyla TCKN doğrula."""
    if not tckn or not isinstance(tckn, str):
        return False
    s = tckn.strip()
    if len(s) != TCKN_LENGTH or not s.isdigit():
        return False
    digits = [int(c) for c in s]
    # İlk hane 0 olamaz
    if digits[0] == 0:
        return False

    # Kural 1: 10. kontrol
    odd_sum = digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
    even_sum = digits[1] + digits[3] + digits[5] + digits[7]
    d10 = (odd_sum * 7 - even_sum) % 10
    if d10 != digits[9]:
        return False

    # Kural 2: 11. kontrol
    d11 = sum(digits[:10]) % 10
    if d11 != digits[10]:
        return False

    return True


def generate_tckn() -> str:
    """Geçerli TCKN üret."""
    while True:
        first = random.randint(1, 9)
        rest = [random.randint(0, 9) for _ in range(8)]
        d1_9 = [first] + rest

        odd_sum = d1_9[0] + d1_9[2] + d1_9[4] + d1_9[6] + d1_9[8]
        even_sum = d1_9[1] + d1_9[3] + d1_9[5] + d1_9[7]
        d10 = (odd_sum * 7 - even_sum) % 10

        d11 = (sum(d1_9) + d10) % 10

        tckn = "".join(str(d) for d in d1_9) + str(d10) + str(d11)
        if validate_tckn(tckn):
            return tckn


def mask_tckn(tckn: str, visible_start: int = 3, visible_end: int = 2) -> str:
    """
    TCKN'yi maskele (KVKK için).
    Default: "12345678901" → "123******01"
    """
    if not tckn or len(tckn) != TCKN_LENGTH:
        return tckn or ""
    hidden_len = TCKN_LENGTH - visible_start - visible_end
    return tckn[:visible_start] + "*" * hidden_len + tckn[-visible_end:]
