"""
Column Classifier — semantik kolon sınıflandırma + PII tespit.

Platform-v4'ten port edildi (Faz 3.B). Sınıflandırma → Faker provider eşlemesi
ile gerçekçi üretim için hazırlık.
"""
from __future__ import annotations

import re


# ─── Faker provider eşlemesi ─────────────────────────────────────────────────
FAKER_MAPPING: dict[str, dict] = {
    "tc_kimlik":    {"provider": "random_number", "args": {"digits": 11, "fix_len": True}},
    "iban":         {"provider": "iban", "locale": "tr_TR"},
    "email":        {"provider": "email"},
    "phone":        {"provider": "phone_number", "locale": "tr_TR"},
    "name":         {"provider": "first_name", "locale": "tr_TR"},
    "surname":      {"provider": "last_name", "locale": "tr_TR"},
    "full_name":    {"provider": "name", "locale": "tr_TR"},
    "address":      {"provider": "address", "locale": "tr_TR"},
    "city":         {"provider": "city", "locale": "tr_TR"},
    "country":      {"provider": "country", "locale": "tr_TR"},
    "date_of_birth":{"provider": "date_of_birth", "args": {"minimum_age": 18, "maximum_age": 90}},
    "date":         {"provider": "date"},
    "amount":       {"provider": "pyfloat", "args": {"positive": True, "min_value": 1, "max_value": 100000}},
    "currency":     {"provider": "currency_code"},
    "account_no":   {"provider": "bban"},
    "credit_score": {"provider": "random_int", "args": {"min": 0, "max": 1900}},
    "status":       {"provider": "random_element", "args": {"elements": ["Active", "Inactive", "Pending"]}},
    "id":           {"provider": "random_int", "args": {"min": 1, "max": 999999}},
    "gender":       {"provider": "random_element", "args": {"elements": ["Male", "Female", "Other"]}},
    "company":      {"provider": "company", "locale": "tr_TR"},
}

# ─── Sınıflandırma kuralları ─────────────────────────────────────────────────
# (classification, name_patterns, value_patterns, dtype_hint)
CLASSIFICATION_RULES: list[tuple[str, list[str], list[str], str]] = [
    ("tc_kimlik",   [r"tc", r"kimlik", r"tckn", r"identity"],                        [r"^\d{11}$"],                        "numeric"),
    ("iban",        [r"iban"],                                                        [r"^TR\d{24}$"],                      "string"),
    ("email",       [r"e[\-_]?mail", r"eposta"],                                     [r"@.*\.\w+$"],                       "string"),
    ("phone",       [r"phone", r"tel", r"gsm", r"mobile", r"cep"],                  [r"^\+?\d{10,13}$", r"^05\d{9}$"],   "string"),
    ("name",        [r"first[\-_]?name", r"ad[iı]?$", r"isim"],                     [],                                   "string"),
    ("surname",     [r"last[\-_]?name", r"soyad", r"surname"],                      [],                                   "string"),
    ("full_name",   [r"full[\-_]?name", r"ad[\-_]?soyad", r"customer[\-_]?name", r"musteri[\-_]?ad"], [],                 "string"),
    ("address",     [r"address", r"adres", r"sokak", r"cadde"],                      [],                                   "string"),
    ("city",        [r"city", r"sehir", r"il$", r"province"],                        [],                                   "string"),
    ("country",     [r"country", r"ulke"],                                            [],                                   "string"),
    ("date_of_birth",[r"birth", r"dogum", r"dob"],                                   [],                                   "datetime"),
    ("date",        [r"date", r"tarih", r"created", r"updated", r"timestamp"],       [],                                   "datetime"),
    ("amount",      [r"amount", r"tutar", r"bakiye", r"balance", r"price", r"fiyat", r"ucret"], [],                       "numeric"),
    ("currency",    [r"currency", r"para[\-_]?birimi", r"doviz"],                    [],                                   "string"),
    ("account_no",  [r"account[\-_]?no", r"hesap[\-_]?no", r"account[\-_]?number"], [],                                   "string"),
    ("credit_score",[r"credit[\-_]?score", r"kredi[\-_]?skor"],                     [],                                   "numeric"),
    ("status",      [r"status", r"durum", r"state"],                                 [],                                   "string"),
    ("id",          [r"^id$", r"[\-_]id$", r"[\-_]no$", r"number$"],                [],                                   "numeric"),
    ("gender",      [r"gender", r"cinsiyet", r"sex"],                                [],                                   "string"),
    ("company",     [r"company", r"firma", r"sirket", r"enterprise"],                [],                                   "string"),
]

# ─── PII kategorileri ────────────────────────────────────────────────────────
PII_CATEGORIES: frozenset[str] = frozenset({
    "tc_kimlik", "iban", "email", "phone", "name", "surname", "full_name",
    "address", "date_of_birth", "account_no",
})

# ─── Semantik açıklamalar ────────────────────────────────────────────────────
SEMANTIC_DESCRIPTIONS: dict[str, str] = {
    "tc_kimlik":    "Türkiye Cumhuriyeti vatandaşlık numarası (11 haneli).",
    "iban":         "Uluslararası Banka Hesap Numarası (TR formatında).",
    "email":        "Kullanıcının elektronik posta adresi.",
    "phone":        "Kullanıcının cep telefonu veya sabit hat numarası.",
    "name":         "Kişinin adı.",
    "surname":      "Kişinin soyadı.",
    "full_name":    "Kişinin ad ve soyad birleşimi.",
    "address":      "Ev veya iş yeri açık adres bilgisi.",
    "city":         "Şehir / İl bilgisi.",
    "country":      "Ülke bilgisi.",
    "date_of_birth":"Kişinin doğum tarihi (yaş hesaplamaları için kritik).",
    "date":         "İşlem veya kayıt oluşturma tarihi.",
    "amount":       "Parasal işlem tutarı veya bakiye.",
    "currency":     "Para birimi (TRY, USD, EUR vb.).",
    "account_no":   "Banka hesap numarası (internal use).",
    "credit_score": "Kişinin kredi risk puanı (0-1900 arası).",
    "status":       "Kaydın aktiflik/pasiflik durumu.",
    "id":           "Benzersiz kayıt numarası (Primary Key).",
    "gender":       "Kişinin cinsiyet bilgisi.",
    "company":      "Kurumsal firma veya iş yeri adı.",
}


class ColumnClassifier:
    """Kolon adı, örnek değerler ve istatistikleri inceleyerek sınıflandırma yapar."""

    def classify(self, column_info: dict) -> dict:
        """
        Tek kolon için zenginleştirilmiş info döner:
            - classification
            - pii (bool)
            - pii_confidence (float 0-1)
            - faker_config (dict | None)
            - description (str)
        """
        col_name = column_info["name"].lower()
        dtype = column_info.get("dtype", "")
        samples = column_info.get("sample_values", [])
        existing_class = column_info.get("classification", "unknown")

        # Analyzer zaten enum işaretlediyse saygı göster
        if existing_class == "enum":
            return {
                **column_info,
                "pii": False,
                "pii_confidence": 0.0,
                "faker_config": None,
                "description": "Önceden tanımlı veya düşük varyasyonlu liste (Kategori).",
            }

        best_match: str | None = None
        best_confidence = 0.0

        for classification, name_patterns, value_patterns, dtype_hint in CLASSIFICATION_RULES:
            confidence = 0.0

            for pattern in name_patterns:
                if re.search(pattern, col_name, re.IGNORECASE):
                    confidence += 0.6
                    break

            for pattern in value_patterns:
                matches = sum(1 for s in samples if re.search(pattern, str(s)))
                if matches > 0:
                    confidence += 0.3 * (matches / max(len(samples), 1))

            if dtype_hint == "numeric" and ("int" in dtype or "float" in dtype):
                confidence += 0.1
            elif dtype_hint == "string" and ("object" in dtype or "str" in dtype):
                confidence += 0.1
            elif dtype_hint == "datetime" and "datetime" in dtype:
                confidence += 0.1

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = classification

        if best_match and best_confidence >= 0.3:
            column_info["classification"] = best_match
            column_info["pii"] = best_match in PII_CATEGORIES
            column_info["pii_confidence"] = round(min(best_confidence, 1.0), 2)
            column_info["faker_config"] = FAKER_MAPPING.get(best_match)
            column_info["description"] = SEMANTIC_DESCRIPTIONS.get(best_match, "Bilinmeyen kolon.")
        else:
            if existing_class == "id":
                column_info["faker_config"] = FAKER_MAPPING.get("id")
                column_info["description"] = SEMANTIC_DESCRIPTIONS.get("id")
            else:
                column_info["classification"] = existing_class
                column_info["faker_config"] = None
                column_info["description"] = "Genel veri alanı (Analiz edilemedi)."

        return column_info

    def classify_schema(self, schema: dict) -> dict:
        """Şemadaki tüm kolonları sınıflandır ve PII özeti çıkar."""
        classified = [self.classify(col) for col in schema.get("columns", [])]
        schema["columns"] = classified

        pii_fields = [c["name"] for c in classified if c.get("pii")]
        schema["pii_summary"] = {
            "total_columns": len(classified),
            "pii_columns": len(pii_fields),
            "pii_fields": pii_fields,
        }
        return schema
