"""
TC Kimlik No ve VKN üretim/doğrulama modülü.
BDDK/KVKK uyumlu: Algoritmik üretim, gerçek kimlik değil.
Referans: https://tc-no.com/python-ile-tc-kimlik-no-olusturma/
"""
import random
from typing import List


def generate_tc_kimlik(seed: int = None) -> str:
    """Mod-10 algoritması ile geçerli TC Kimlik No üretir."""
    if seed is not None:
        random.seed(seed)
    digits = [random.randint(1, 9)] + [random.randint(0, 9) for _ in range(8)]
    odd_sum = sum(digits[i] for i in range(0, 9, 2))
    even_sum = sum(digits[i] for i in range(1, 8, 2))
    d10 = (odd_sum * 7 - even_sum) % 10
    digits.append(d10)
    d11 = sum(digits) % 10
    digits.append(d11)
    return ''.join(map(str, digits))


def validate_tc_kimlik(tc: str) -> bool:
    """TC Kimlik No doğrular. True: geçerli, False: geçersiz."""
    if not isinstance(tc, str) or len(tc) != 11 or not tc.isdigit() or tc[0] == '0':
        return False
    d = [int(c) for c in tc]
    odd_sum = sum(d[i] for i in range(0, 9, 2))
    even_sum = sum(d[i] for i in range(1, 8, 2))
    check10 = (odd_sum * 7 - even_sum) % 10
    check11 = sum(d[:10]) % 10
    return check10 == d[9] and check11 == d[10]


def generate_tc_kimlik_batch(count: int, seed: int = None) -> List[str]:
    """N adet geçerli TC Kimlik No üretir (benzersiz)."""
    if seed is not None:
        random.seed(seed)
    results = set()
    while len(results) < count:
        tc = generate_tc_kimlik()
        if validate_tc_kimlik(tc):
            results.add(tc)
    return list(results)


def generate_vkn(seed: int = None) -> str:
    """10 haneli algoritmik geçerli VKN üretir."""
    if seed is not None:
        random.seed(seed)
    while True:
        base = [random.randint(1 if i == 0 else 0, 9) for i in range(9)]
        r = []
        for i in range(9):
            x = (base[i] + (9 - i)) % 10
            if x == 9:
                r.append(9)
            else:
                r.append((x * (2 ** (9 - i))) % 9)
        total = sum(r)
        control = (10 - (total % 10)) % 10
        vkn = ''.join(map(str, base)) + str(control)
        if validate_vkn(vkn):
            return vkn


def validate_vkn(vkn: str) -> bool:
    """VKN doğrular."""
    if not isinstance(vkn, str) or len(vkn) != 10 or not vkn.isdigit():
        return False
    d = list(vkn)
    r = []
    for i in range(9):
        x = (int(d[i]) + (9 - i)) % 10
        if x == 9:
            r.append(9)
        else:
            r.append((x * (2 ** (9 - i))) % 9)
    total = sum(r)
    computed = (10 - (total % 10)) % 10
    return computed == int(d[9])
