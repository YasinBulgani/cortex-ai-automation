"""PII Detector and Data Masker unit tests."""

import pytest

from ai_synthetic_data.privacy.pii_detector import PIIDetector
from ai_synthetic_data.privacy.data_masker import DataMasker

class TestPIIDetector:
    @pytest.fixture
    def detector(self):
        return PIIDetector()

    def test_scan_text_tc(self, detector):
        findings = detector.scan_text("TC: 12345678901")
        assert any(f[0] == "tc_kimlik" for f in findings)

    def test_scan_text_iban(self, detector):
        findings = detector.scan_text("IBAN: TR330006100519786457841326")
        assert any(f[0] == "iban" for f in findings)

    def test_scan_text_iban_lowercase(self, detector):
        findings = detector.scan_text("iban: tr330006100519786457841326")
        assert any(f[0] == "iban" for f in findings)

    def test_scan_text_email(self, detector):
        findings = detector.scan_text("email: ali@banka.com")
        assert any(f[0] == "email" for f in findings)

    def test_scan_text_phone(self, detector):
        findings = detector.scan_text("tel: 0532 123 45 67")
        assert any(f[0] == "telefon" for f in findings)

    def test_scan_records(self, detector):
        records = [
            {"name": "Ali", "tc": "12345678901", "email": "ali@bank.com"},
            {"name": "Veli", "tc": "98765432109", "email": "veli@bank.com"},
        ]
        detections = detector.scan_records(records)
        assert len(detections) > 0
        pii_types = {d.pii_type for d in detections}
        assert "tc_kimlik" in pii_types

    def test_handles_numeric_values(self, detector):
        records = [{"amount": 0, "flag": False, "count": 12345678901}]
        detections = detector.scan_records(records)
        assert any(d.pii_type == "tc_kimlik" for d in detections)

    def test_skips_none_values(self, detector):
        records = [{"tc": None, "name": "Ali"}]
        detections = detector.scan_records(records)
        tc_detections = [d for d in detections if d.column == "tc"]
        assert tc_detections == []

    def test_empty_records(self, detector):
        assert detector.scan_records([]) == []

class TestDataMasker:
    @pytest.fixture
    def masker(self):
        return DataMasker(seed=42)

    def test_masks_tc(self, masker):
        records = [{"tc": "12345678901"}]
        masked = masker.mask_records(records)
        assert masked[0]["tc"] != "12345678901"
        assert len(masked[0]["tc"]) == 11

    def test_masks_email(self, masker):
        records = [{"email": "ali@bank.com"}]
        masked = masker.mask_records(records)
        assert "ali@bank.com" not in masked[0]["email"]
        assert "@example.com" in masked[0]["email"]

    def test_masks_text(self, masker):
        text = "TC: 12345678901, email: test@bank.com"
        masked = masker.mask_text(text)
        assert "12345678901" not in masked
        assert "test@bank.com" not in masked

    def test_deterministic(self, masker):
        r1 = masker.mask_records([{"tc": "12345678901"}])
        r2 = masker.mask_records([{"tc": "12345678901"}])
        assert r1[0]["tc"] == r2[0]["tc"]

    def test_iban_uppercase(self, masker):
        masked = masker.mask_text("TR330006100519786457841326")
        assert masked.startswith("TR")
        assert masked != "TR330006100519786457841326"

    def test_iban_lowercase(self, masker):
        masked = masker.mask_text("tr330006100519786457841326")
        assert masked.startswith("TR")

    def test_column_filter(self, masker):
        records = [{"tc": "12345678901", "name": "Ali"}]
        masked = masker.mask_records(records, columns_to_mask=["tc"])
        assert masked[0]["tc"] != "12345678901"
        assert masked[0]["name"] == "Ali"
