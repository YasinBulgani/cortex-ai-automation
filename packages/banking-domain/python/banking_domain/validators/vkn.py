"""
VKN (Vergi Kimlik Numarası) — TR 10 haneli tüzel kişi no.

Algoritma (Gelir İdaresi):
  1. 10 dijit
  2. İlk 9 dijit için:
     - Her i (0-indexli) için p_i = (d_i + (9 - i)) mod 10
     - q_i = (p_i * 2^(9 - i)) mod 9 (eğer p_i != 0 ve sonuç 0 ise 9)
  3. Toplam = sum(q_i) mod 10
  4. Check dijit = (10 - toplam) mod 10
"""
from __future__ import annotations

import random


VKN_LENGTH = 10


def validate_vkn(vkn: str | None) -> bool:
    """10 dijit VKN doğrulama."""
    if not vkn or not isinstance(vkn, str):
        return False
    s = vkn.strip()
    if len(s) != VKN_LENGTH or not s.isdigit():
        return False
    digits = [int(c) for c in s]

    total = 0
    for i in range(9):
        tmp = (digits[i] + (9 - i)) % 10
        if tmp == 0:
            q = 0
        else:
            q = (tmp * (2 ** (9 - i))) % 9
            if q == 0:
                q = 9
        total += q

    check = (10 - (total % 10)) % 10
    return check == digits[9]


def generate_vkn() -> str:
    """Geçerli VKN üret."""
    while True:
        body = [random.randint(0, 9) for _ in range(9)]
        # İlk dijit 0 olmasın (realistik)
        if body[0] == 0:
            continue
        total = 0
        for i in range(9):
            tmp = (body[i] + (9 - i)) % 10
            if tmp == 0:
                q = 0
            else:
                q = (tmp * (2 ** (9 - i))) % 9
                if q == 0:
                    q = 9
            total += q
        check = (10 - (total % 10)) % 10
        candidate = "".join(str(d) for d in body) + str(check)
        if validate_vkn(candidate):
            return candidate
