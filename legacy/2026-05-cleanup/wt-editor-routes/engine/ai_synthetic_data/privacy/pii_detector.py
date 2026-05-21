"""
PII (Kişisel Tanımlanabilir Bilgi) tespit modülü.

DataFrame veya metin içindeki hassas bilgileri tespit eder.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

PII_RULES: list[tuple[str, str, str]] = [
    ("tc_kimlik", r"\b\d{11}\b", "TC Kimlik Numarası"),
    ("iban", r"\b[Tt][Rr]\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b", "IBAN"),
    ("email", r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "E-posta"),
    ("telefon", r"\b05\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b", "Telefon"),
    ("kredi_karti", r"\b(?:4\d{3}|5[1-5]\d{2}|6011|3[47]\d{2})[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "Kredi Kartı"),
]


@dataclass
class PIIDetection:
    column: str
    pii_type: str
    description: str
    sample_count: int
    total_rows: int
    detection_rate: float


class PIIDetector:
    """DataFrame veya sözlük listesinde PII tespit eder."""

    def __init__(self, rules: list[tuple[str, str, str]] | None = None):
        self.rules = rules or PII_RULES

    def scan_records(self, records: list[dict], sample_size: int = 100) -> list[PIIDetection]:
        """Kayıt listesindeki her alanı PII açısından tarar."""
        if not records:
            return []

        sample = records[:sample_size]
        columns = list(sample[0].keys())
        detections: list[PIIDetection] = []

        for col in columns:
            values = [str(r[col]) for r in sample if col in r and r[col] is not None]
            for pii_name, pattern, desc in self.rules:
                matches = sum(1 for v in values if re.search(pattern, v))
                if matches > 0:
                    detections.append(PIIDetection(
                        column=col,
                        pii_type=pii_name,
                        description=desc,
                        sample_count=matches,
                        total_rows=len(sample),
                        detection_rate=round(matches / max(len(sample), 1), 3),
                    ))
        return detections

    def scan_text(self, text: str) -> list[tuple[str, str, str]]:
        """Metin içindeki PII'leri tespit eder. (pii_type, match, description) döndürür."""
        findings: list[tuple[str, str, str]] = []
        for pii_name, pattern, desc in self.rules:
            for m in re.finditer(pattern, text):
                findings.append((pii_name, m.group(), desc))
        return findings
