"""
Veri maskeleme modülü.

Gerçek verideki hassas bilgileri maskeleyerek güvenli hale getirir.
"""
from __future__ import annotations

import hashlib
import random
import re

from .pii_detector import PII_RULES


class DataMasker:
    """Kayıtlardaki hassas bilgileri maskeler."""

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self._cache: dict[str, str] = {}

    def mask_records(self, records: list[dict], columns_to_mask: list[str] | None = None) -> list[dict]:
        """Kayıt listesindeki hassas alanları maskeler."""
        masked: list[dict] = []
        for record in records:
            new_record = dict(record)
            for col, value in record.items():
                if columns_to_mask and col not in columns_to_mask:
                    continue
                if isinstance(value, str):
                    new_record[col] = self._mask_value(value)
            masked.append(new_record)
        return masked

    def mask_text(self, text: str) -> str:
        """Metin içindeki PII'leri maskeler."""
        for _, pattern, _ in PII_RULES:
            text = re.sub(pattern, lambda m: self._mask_match(m.group()), text)
        return text

    def _mask_value(self, value: str) -> str:
        for _, pattern, _ in PII_RULES:
            value = re.sub(pattern, lambda m: self._mask_match(m.group()), value)
        return value

    def _mask_match(self, original: str) -> str:
        if original in self._cache:
            return self._cache[original]

        if re.match(r"^\d{11}$", original):
            masked = self._random_digits(11)
        elif re.match(r"^[Tt][Rr]\d", original):
            masked = "TR" + self._random_digits(24)
        elif "@" in original:
            masked = f"masked_{self._deterministic_hash(original)[:8]}@example.com"
        elif re.match(r"^05\d", original.replace("-", "").replace(" ", "")):
            masked = "05" + self._random_digits(9)
        else:
            masked = self._random_digits(len(re.sub(r"\D", "", original)))

        self._cache[original] = masked
        return masked

    def _random_digits(self, length: int) -> str:
        return "".join(str(self._rng.randint(0, 9)) for _ in range(length))

    @staticmethod
    def _deterministic_hash(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()
