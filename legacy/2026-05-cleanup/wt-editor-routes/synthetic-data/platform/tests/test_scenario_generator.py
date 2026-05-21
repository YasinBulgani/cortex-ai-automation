"""
ScenarioGenerator birim testleri.

Senaryo bazlı sentetik veri üretimi, senaryo konfigürasyonları ve
karışık dağılım fonksiyonlarını test eder.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.services.scenario_generator import (
    SCENARIO_CONFIGS,
    ScenarioConfig,
    ScenarioGenerator,
    ScenarioResult,
    ScenarioType,
)


class TestScenarioTypeEnum:
    """ScenarioType enum testleri."""

    def test_all_12_scenarios_exist(self) -> None:
        """12 senaryo tipi tanımlı olmalı."""
        assert len(ScenarioType) == 12

    def test_expected_scenarios(self) -> None:
        """Beklenen senaryo tipleri mevcut olmalı."""
        expected = [
            "bireysel", "premium", "maas", "yuksek_bakiyeli",
            "kredi_karti_gecikmeli", "cok_islem", "dormant", "riskli",
            "ticari", "yeni_musteri", "emekli", "ogrenci",
        ]
        type_values = [t.value for t in ScenarioType]
        for e in expected:
            assert e in type_values, f"{e} ScenarioType'da bulunamadı"


class TestScenarioConfig:
    """ScenarioConfig testleri."""

    def test_all_scenarios_have_configs(self) -> None:
        """Her senaryo tipi için config tanımlı olmalı."""
        for scenario_type in ScenarioType:
            assert scenario_type in SCENARIO_CONFIGS, \
                f"{scenario_type.value} için config bulunamadı"

    def test_bireysel_config_values(self) -> None:
        """Bireysel senaryo config değerleri geçerli olmalı."""
        config = SCENARIO_CONFIGS[ScenarioType.BIREYSEL]
        assert config.min_bakiye >= 0
        assert config.max_bakiye > config.min_bakiye
        assert config.yas_min >= 18
        assert config.segment == "Bireysel"

    def test_premium_config_higher_balance(self) -> None:
        """Premium müşteri bakiyesi bireyseldan yüksek olmalı."""
        bireysel = SCENARIO_CONFIGS[ScenarioType.BIREYSEL]
        premium = SCENARIO_CONFIGS[ScenarioType.PREMIUM]
        assert premium.min_bakiye >= bireysel.min_bakiye

    def test_custom_config_creation(self) -> None:
        """Özel ScenarioConfig oluşturulabilmeli."""
        config = ScenarioConfig(
            name="Test Senaryosu",
            min_bakiye=1000.0,
            max_bakiye=50000.0,
            segment="Test",
        )
        assert config.name == "Test Senaryosu"
        assert config.min_bakiye == 1000.0


class TestScenarioGeneratorInit:
    """ScenarioGenerator başlatma testleri."""

    def test_create_instance(self, scenario_generator: ScenarioGenerator) -> None:
        """ScenarioGenerator örneği oluşturulabilmeli."""
        assert scenario_generator is not None


class TestGenerateScenario:
    """Senaryo bazlı üretim testleri."""

    def test_generate_bireysel_scenario(self, scenario_generator: ScenarioGenerator) -> None:
        """Bireysel senaryo ile veri üretilmeli."""
        result = scenario_generator.generate_scenario(
            ScenarioType.BIREYSEL, count=5
        )
        assert isinstance(result, ScenarioResult)
        assert result.scenario_type == ScenarioType.BIREYSEL
        assert result.customer_count == 5

    def test_generate_premium_scenario(self, scenario_generator: ScenarioGenerator) -> None:
        """Premium senaryo ile veri üretilmeli."""
        result = scenario_generator.generate_scenario(
            ScenarioType.PREMIUM, count=3
        )
        assert isinstance(result, ScenarioResult)
        assert result.scenario_type == ScenarioType.PREMIUM

    def test_scenario_result_has_dataframes(self, scenario_generator: ScenarioGenerator) -> None:
        """Senaryo sonucu müşteri, hesap ve işlem DataFrame'leri içermeli."""
        result = scenario_generator.generate_scenario(
            ScenarioType.BIREYSEL, count=3
        )
        assert result.customers is not None
        assert result.accounts is not None
        assert result.transactions is not None
        assert len(result.customers) == 3
        assert len(result.accounts) >= 3  # En az 1 hesap/müşteri
