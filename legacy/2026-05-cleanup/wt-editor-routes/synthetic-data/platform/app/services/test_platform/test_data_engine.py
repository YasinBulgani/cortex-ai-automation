"""
TestDataEngine — Test Verisi Üretimi (Statik / Dinamik / Mock)

Bankacılık domain'ine özgü test verileri üretir:
TCKN, IBAN, hesap numarası, tutar, kişi adı vb.
"""
from __future__ import annotations
import random
import string
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TestData:
    dataset_id: str
    name: str
    records: List[Dict[str, Any]]
    schema: Dict[str, str]
    record_count: int
    data_type: str  # static / dynamic / mock / boundary


class TestDataEngine:
    """
    Test senaryolarına uygun veri setleri üretir.
    Statik (sabit), dinamik (rastgele) ve mock veriler desteklenir.
    """

    _TURKISH_NAMES = [
        "Ahmet", "Mehmet", "Fatma", "Ayşe", "Ali", "Veli",
        "Zeynep", "Hasan", "Hüseyin", "Elif", "Emine", "Murat",
    ]
    _SURNAMES = [
        "Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Arslan",
        "Doğan", "Koç", "Kurt", "Aydın", "Öztürk", "Yıldız",
    ]
    _CITIES = ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana"]

    def generate_banking_dataset(
        self,
        count: int = 10,
        include_invalid: bool = True,
    ) -> TestData:
        """Bankacılık test verisi seti üretir."""
        records = []
        for i in range(count):
            is_invalid = include_invalid and i % 5 == 0  # %20 geçersiz veri
            records.append(self._banking_record(i, invalid=is_invalid))

        return TestData(
            dataset_id=str(uuid.uuid4())[:8],
            name="Bankacılık Test Verisi",
            records=records,
            schema={
                "tckn": "string(11)",
                "ad_soyad": "string",
                "hesap_no": "string(16)",
                "iban": "string(26)",
                "bakiye": "decimal",
                "sehir": "string",
                "is_valid": "boolean",
            },
            record_count=count,
            data_type="dynamic",
        )

    def generate_boundary_data(self, field: str, data_type: str = "numeric") -> TestData:
        """Sınır değer analizi için veri seti üretir."""
        boundaries = {
            "numeric": [0, -1, 1, 999_999_999, 1_000_000_000, -999_999_999],
            "string": ["", " ", "a" * 255, "a" * 256, "a" * 1000, "<script>"],
            "decimal": [0.0, 0.001, -0.001, 99_999_999.99, 100_000_000.00],
        }
        values = boundaries.get(data_type, boundaries["numeric"])
        records = [{"field": field, "value": v, "type": data_type} for v in values]

        return TestData(
            dataset_id=str(uuid.uuid4())[:8],
            name=f"Sınır Değer Verisi — {field}",
            records=records,
            schema={"field": "string", "value": "any", "type": "string"},
            record_count=len(records),
            data_type="boundary",
        )

    def generate_static_dataset(self, scenario: str) -> TestData:
        """Belirli senaryo için sabit test verisi seti döner."""
        scenarios = {
            "login": [
                {"username": "testuser@bank.com", "password": "Test1234!", "expected": "success"},
                {"username": "", "password": "Test1234!", "expected": "validation_error"},
                {"username": "testuser@bank.com", "password": "", "expected": "validation_error"},
                {"username": "wrong@bank.com", "password": "WrongPass", "expected": "auth_error"},
            ],
            "transfer": [
                {"amount": 100.0, "from_iban": self._gen_iban(), "to_iban": self._gen_iban(), "expected": "success"},
                {"amount": 0, "from_iban": self._gen_iban(), "to_iban": self._gen_iban(), "expected": "validation_error"},
                {"amount": -50, "from_iban": self._gen_iban(), "to_iban": self._gen_iban(), "expected": "validation_error"},
                {"amount": 9_999_999, "from_iban": self._gen_iban(), "to_iban": self._gen_iban(), "expected": "limit_exceeded"},
            ],
        }
        records = scenarios.get(scenario, [{"note": "Senaryo bulunamadı"}])
        return TestData(
            dataset_id=str(uuid.uuid4())[:8],
            name=f"Statik Test Verisi — {scenario}",
            records=records,
            schema={},
            record_count=len(records),
            data_type="static",
        )

    # ── Yardımcı üretecler ────────────────────────────────────────────

    def _banking_record(self, index: int, invalid: bool = False) -> Dict[str, Any]:
        tckn = self._gen_tckn() if not invalid else "00000000000"
        return {
            "tckn": tckn,
            "ad_soyad": f"{random.choice(self._TURKISH_NAMES)} {random.choice(self._SURNAMES)}",
            "hesap_no": "".join(random.choices(string.digits, k=16)),
            "iban": self._gen_iban(),
            "bakiye": round(random.uniform(-1000 if invalid else 0, 500_000), 2),
            "sehir": random.choice(self._CITIES),
            "is_valid": not invalid,
        }

    def _gen_tckn(self) -> str:
        digits = [random.randint(1, 9)] + [random.randint(0, 9) for _ in range(9)]
        odd_sum = sum(digits[i] for i in range(0, 9, 2))
        even_sum = sum(digits[i] for i in range(1, 8, 2))
        d10 = (odd_sum * 7 - even_sum) % 10
        d11 = sum(digits) % 10
        return "".join(map(str, digits)) + str(d10) + str(d11)

    def _gen_iban(self) -> str:
        bban = "".join(random.choices(string.digits, k=22))
        return f"TR{random.randint(10,99)}{bban}"

    # ── Public API (schema-based wrappers) ───────────────────────────────

    def generate_static_data(self, schema: dict) -> dict:
        """
        Schema tanımına göre sabit/öngörülebilir test verisi üret.

        Args:
            schema: Alan adı → tip string veya detay dict eşlemesi.
                    Örnek: {"username": "string", "amount": "decimal"}

        Returns:
            Alan adı → statik değer eşlemesi içeren dict.
        """
        if not schema:
            return {}

        result: dict[str, Any] = {}
        for field_name, field_spec in schema.items():
            field_type = (
                field_spec if isinstance(field_spec, str)
                else field_spec.get("type", "string")
            )
            result[field_name] = self._static_value_for_type(field_type, field_name)
        return result

    def generate_dynamic_data(self, schema: dict) -> dict:
        """
        Schema tanımına göre rastgele/dinamik test verisi üret.

        Args:
            schema: Alan adı → tip string veya detay dict eşlemesi.

        Returns:
            Alan adı → dinamik değer eşlemesi içeren dict.
        """
        if not schema:
            return {}

        result: dict[str, Any] = {}
        for field_name, field_spec in schema.items():
            field_type = (
                field_spec if isinstance(field_spec, str)
                else field_spec.get("type", "string")
            )
            result[field_name] = self._dynamic_value_for_type(field_type, field_name)
        return result

    def _static_value_for_type(self, field_type: str, field_name: str) -> Any:
        """Tip adına göre öngörülebilir statik değer döndür."""
        ft = field_type.lower()
        if ft in ("string", "str"):
            return f"test_{field_name}"
        if ft in ("integer", "int"):
            return 1
        if ft in ("decimal", "float", "number"):
            return 1.0
        if ft in ("boolean", "bool"):
            return True
        if ft == "email":
            return "test@example.com"
        if ft in ("date", "datetime"):
            return "2024-01-01"
        if ft == "uuid":
            return "00000000-0000-0000-0000-000000000001"
        if "string" in ft:
            return f"test_{field_name}"
        return f"static_{field_name}"

    def _dynamic_value_for_type(self, field_type: str, field_name: str) -> Any:
        """Tip adına göre rastgele dinamik değer üret."""
        ft = field_type.lower()
        if ft in ("string", "str"):
            return "".join(random.choices(string.ascii_lowercase, k=8))
        if ft in ("integer", "int"):
            return random.randint(1, 1000)
        if ft in ("decimal", "float", "number"):
            return round(random.uniform(1.0, 10000.0), 2)
        if ft in ("boolean", "bool"):
            return random.choice([True, False])
        if ft == "email":
            user = "".join(random.choices(string.ascii_lowercase, k=6))
            domain = "".join(random.choices(string.ascii_lowercase, k=4))
            return f"{user}@{domain}.com"
        if ft in ("date", "datetime"):
            day = random.randint(1, 28)
            month = random.randint(1, 12)
            return f"2024-{month:02d}-{day:02d}"
        if ft == "uuid":
            return str(uuid.uuid4())
        return "".join(random.choices(string.ascii_lowercase, k=8))
