"""
Senaryo Bazli Sentetik Veri Uretici — ScenarioGenerator Modulu.

Hazir bankacilik senaryolariyla toplu veri uretimi saglar.
12 ontanimli senaryo (bireysel, premium, maas, riskli, ticari vb.)
ve ozel senaryo destegi ile karisik veri setleri olusturur.

Kullanim:
    generator = ScenarioGenerator()
    result = generator.generate_scenario(ScenarioType.BIREYSEL, count=500)
    generator.export_csv(result, output_dir="output/")

    # Karisik dagilim
    dist = {ScenarioType.BIREYSEL: 0.4, ScenarioType.PREMIUM: 0.2, ...}
    mixed = generator.generate_mixed_dataset(dist, total_count=10000)
"""

from __future__ import annotations

import csv
import io
import json
import logging
import math
import os
import random
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd

from app.config import settings
from app.services.synthetic_generator import (
    GenerationProgress,
    GenerationResult,
    SyntheticDataGenerator,
)

logger = logging.getLogger(__name__)


# =====================================================================
# Senaryo Tipi Tanimlari
# =====================================================================


class ScenarioType(str, Enum):
    """
    Desteklenen bankacilik senaryolari.

    Her senaryo, belirli musteri profili, hesap yapisi ve islem
    davranisini tanimlar. Gercek bankacilik segmentasyonuna dayalidir.
    """

    BIREYSEL = "bireysel"                       # Standart bireysel musteri
    PREMIUM = "premium"                         # Premium / VIP musteri
    MAAS = "maas"                               # Maas musterisi
    YUKSEK_BAKIYELI = "yuksek_bakiyeli"         # Yuksek bakiye segmenti
    KREDI_KARTI_GECIKMELI = "kredi_karti_gecikmeli"  # Kredi karti gecikmeli
    COK_ISLEM = "cok_islem"                     # Yogun islem yapan musteri
    DORMANT = "dormant"                         # Hareketsiz / uykudaki hesap
    RISKLI = "riskli"                           # Yuksek riskli musteri
    TICARI = "ticari"                           # Ticari / kurumsal musteri
    YENI_MUSTERI = "yeni_musteri"               # Yeni musteri (son 6 ay)
    EMEKLI = "emekli"                           # Emekli musteri profili
    OGRENCI = "ogrenci"                         # Ogrenci musteri profili


# =====================================================================
# Senaryo Konfigurasyon Dataclass'i
# =====================================================================


@dataclass
class ScenarioConfig:
    """
    Tek bir senaryonun tam konfigurasyonu.

    Musteri profili, hesap yapisi, islem davranisi ve ozel kurallari
    tek bir yapida toplar. generate_custom_scenario() ile kullanilabilir.

    Attributes:
        name: Senaryo adi (Turkce)
        description: Senaryo aciklamasi
        min_bakiye: Minimum hesap bakiyesi (TRY)
        max_bakiye: Maksimum hesap bakiyesi (TRY)
        kredi_skoru_min: Minimum kredi notu (0-1900)
        kredi_skoru_max: Maksimum kredi notu (0-1900)
        segment: Musteri segmenti
        musteri_tipi: Musteri tipi (Bireysel / Ticari)
        hesap_sayisi_min: Musteri basina minimum hesap sayisi
        hesap_sayisi_max: Musteri basina maksimum hesap sayisi
        islem_sayisi_min: Hesap basina minimum islem sayisi
        islem_sayisi_max: Hesap basina maksimum islem sayisi
        islem_tutar_min: Islem tutari minimum (TRY)
        islem_tutar_max: Islem tutari maksimum (TRY)
        yas_min: Minimum yas
        yas_max: Maksimum yas
        ozel_kurallar: Senaryoya ozel ek kurallar dict'i
    """

    name: str = "Ozel Senaryo"
    description: str = ""
    min_bakiye: float = 0.0
    max_bakiye: float = 100_000.0
    kredi_skoru_min: int = 300
    kredi_skoru_max: int = 1900
    segment: str = "Bireysel"
    musteri_tipi: str = "Bireysel"
    hesap_sayisi_min: int = 1
    hesap_sayisi_max: int = 3
    islem_sayisi_min: int = 1
    islem_sayisi_max: int = 20
    islem_tutar_min: float = 10.0
    islem_tutar_max: float = 10_000.0
    yas_min: int = 18
    yas_max: int = 80
    ozel_kurallar: dict[str, Any] = field(default_factory=dict)


# =====================================================================
# Ontanimli Senaryo Konfigurasyonlari (12 senaryo)
# =====================================================================


SCENARIO_CONFIGS: dict[ScenarioType, ScenarioConfig] = {
    ScenarioType.BIREYSEL: ScenarioConfig(
        name="Bireysel Musteri",
        description="Standart bireysel bankacilik musterisi. Ortalama gelir, "
                    "duzenli maas girisi, gunluk harcamalar.",
        min_bakiye=500.0,
        max_bakiye=50_000.0,
        kredi_skoru_min=500,
        kredi_skoru_max=1500,
        segment="Bireysel",
        musteri_tipi="Bireysel",
        hesap_sayisi_min=1,
        hesap_sayisi_max=3,
        islem_sayisi_min=5,
        islem_sayisi_max=30,
        islem_tutar_min=20.0,
        islem_tutar_max=5_000.0,
        yas_min=22,
        yas_max=65,
        ozel_kurallar={
            "hesap_tipleri": ["Vadesiz", "Tasarruf"],
            "islem_tipleri": ["Havale", "EFT", "Kart", "ATM"],
            "kanallar": ["Mobil", "Internet", "ATM", "Sube"],
        },
    ),

    ScenarioType.PREMIUM: ScenarioConfig(
        name="Premium / VIP Musteri",
        description="Yuksek gelirli premium segment musterisi. Yuksek bakiye, "
                    "yatirim hesaplari, ozel bankacilik hizmetleri.",
        min_bakiye=100_000.0,
        max_bakiye=5_000_000.0,
        kredi_skoru_min=1200,
        kredi_skoru_max=1900,
        segment="Platinum",
        musteri_tipi="Bireysel",
        hesap_sayisi_min=3,
        hesap_sayisi_max=8,
        islem_sayisi_min=10,
        islem_sayisi_max=50,
        islem_tutar_min=500.0,
        islem_tutar_max=500_000.0,
        yas_min=30,
        yas_max=70,
        ozel_kurallar={
            "hesap_tipleri": ["Vadesiz", "Vadeli", "Yatirim", "Tasarruf"],
            "islem_tipleri": ["Havale", "EFT", "SWIFT", "Yatirim", "Kart"],
            "kanallar": ["Mobil", "Internet", "Ozel Bankacilik"],
            "para_birimleri": ["TRY", "USD", "EUR"],
        },
    ),

    ScenarioType.MAAS: ScenarioConfig(
        name="Maas Musterisi",
        description="Maas odemesi alan calisan musteri. Duzenli gelir, "
                    "aylik maas girisi, fatura odemeleri.",
        min_bakiye=1_000.0,
        max_bakiye=30_000.0,
        kredi_skoru_min=600,
        kredi_skoru_max=1400,
        segment="Bireysel",
        musteri_tipi="Bireysel",
        hesap_sayisi_min=1,
        hesap_sayisi_max=2,
        islem_sayisi_min=10,
        islem_sayisi_max=40,
        islem_tutar_min=50.0,
        islem_tutar_max=15_000.0,
        yas_min=25,
        yas_max=60,
        ozel_kurallar={
            "hesap_tipleri": ["Vadesiz"],
            "islem_tipleri": ["Maas", "Havale", "EFT", "Fatura", "Kart", "ATM"],
            "kanallar": ["Mobil", "Internet", "ATM"],
            "aylik_maas": True,
        },
    ),

    ScenarioType.YUKSEK_BAKIYELI: ScenarioConfig(
        name="Yuksek Bakiyeli Musteri",
        description="Cok yuksek bakiyeli tasarruf/yatirim odakli musteri. "
                    "Buyuk mevduat, dusuk islem sikligi.",
        min_bakiye=500_000.0,
        max_bakiye=50_000_000.0,
        kredi_skoru_min=1400,
        kredi_skoru_max=1900,
        segment="VIP",
        musteri_tipi="Bireysel",
        hesap_sayisi_min=2,
        hesap_sayisi_max=6,
        islem_sayisi_min=3,
        islem_sayisi_max=15,
        islem_tutar_min=5_000.0,
        islem_tutar_max=2_000_000.0,
        yas_min=35,
        yas_max=75,
        ozel_kurallar={
            "hesap_tipleri": ["Vadeli", "Yatirim", "Vadesiz"],
            "islem_tipleri": ["Havale", "EFT", "SWIFT", "Yatirim"],
            "kanallar": ["Ozel Bankacilik", "Mobil", "Internet"],
            "para_birimleri": ["TRY", "USD", "EUR", "GBP"],
        },
    ),

    ScenarioType.KREDI_KARTI_GECIKMELI: ScenarioConfig(
        name="Kredi Karti Gecikmeli",
        description="Kredi karti odemelerinde gecikme yasayan musteri. "
                    "Dusuk kredi notu, yuksek kart borcu.",
        min_bakiye=0.0,
        max_bakiye=5_000.0,
        kredi_skoru_min=200,
        kredi_skoru_max=600,
        segment="Bireysel",
        musteri_tipi="Bireysel",
        hesap_sayisi_min=1,
        hesap_sayisi_max=2,
        islem_sayisi_min=15,
        islem_sayisi_max=60,
        islem_tutar_min=10.0,
        islem_tutar_max=3_000.0,
        yas_min=20,
        yas_max=55,
        ozel_kurallar={
            "hesap_tipleri": ["Vadesiz", "Kredi"],
            "islem_tipleri": ["Kart", "Gecikme Faizi", "Taksit", "ATM"],
            "kanallar": ["Mobil", "ATM", "POS"],
            "gecikme_gunu_min": 5,
            "gecikme_gunu_max": 90,
        },
    ),

    ScenarioType.COK_ISLEM: ScenarioConfig(
        name="Cok Islem Yapan Musteri",
        description="Gunluk cok sayida islem yapan aktif musteri. "
                    "E-ticaret, POS, mobil bankacilik yogun kullanim.",
        min_bakiye=2_000.0,
        max_bakiye=80_000.0,
        kredi_skoru_min=700,
        kredi_skoru_max=1600,
        segment="Bireysel",
        musteri_tipi="Bireysel",
        hesap_sayisi_min=2,
        hesap_sayisi_max=5,
        islem_sayisi_min=50,
        islem_sayisi_max=200,
        islem_tutar_min=5.0,
        islem_tutar_max=8_000.0,
        yas_min=20,
        yas_max=45,
        ozel_kurallar={
            "hesap_tipleri": ["Vadesiz", "Tasarruf"],
            "islem_tipleri": ["Kart", "Havale", "EFT", "ATM", "QR", "Temassiz"],
            "kanallar": ["Mobil", "Internet", "POS", "ATM"],
        },
    ),

    ScenarioType.DORMANT: ScenarioConfig(
        name="Hareketsiz Hesap (Dormant)",
        description="Uzun suredir islem yapilmayan uykudaki hesap. "
                    "Cok dusuk bakiye, yilda 1-2 islem.",
        min_bakiye=0.0,
        max_bakiye=500.0,
        kredi_skoru_min=300,
        kredi_skoru_max=800,
        segment="Bireysel",
        musteri_tipi="Bireysel",
        hesap_sayisi_min=1,
        hesap_sayisi_max=1,
        islem_sayisi_min=0,
        islem_sayisi_max=2,
        islem_tutar_min=0.0,
        islem_tutar_max=100.0,
        yas_min=25,
        yas_max=80,
        ozel_kurallar={
            "hesap_tipleri": ["Vadesiz"],
            "islem_tipleri": ["Masraf", "Faiz"],
            "kanallar": ["Sistem"],
            "hesap_durumu": "Pasif",
        },
    ),

    ScenarioType.RISKLI: ScenarioConfig(
        name="Yuksek Riskli Musteri",
        description="Kredi riski yuksek, odemelerde duzensizlik gosteren musteri. "
                    "Dusuk kredi notu, negatif bakiye olasiligi.",
        min_bakiye=-10_000.0,
        max_bakiye=5_000.0,
        kredi_skoru_min=100,
        kredi_skoru_max=400,
        segment="Bireysel",
        musteri_tipi="Bireysel",
        hesap_sayisi_min=1,
        hesap_sayisi_max=2,
        islem_sayisi_min=5,
        islem_sayisi_max=25,
        islem_tutar_min=10.0,
        islem_tutar_max=2_000.0,
        yas_min=20,
        yas_max=60,
        ozel_kurallar={
            "hesap_tipleri": ["Vadesiz", "Kredi"],
            "islem_tipleri": ["ATM", "Kart", "Gecikme Faizi", "Icra"],
            "kanallar": ["ATM", "Sube"],
            "risk_skoru_yuksek": True,
        },
    ),

    ScenarioType.TICARI: ScenarioConfig(
        name="Ticari / Kurumsal Musteri",
        description="Sirket hesabi olan ticari musteri. Yuksek hacimli "
                    "havale/EFT, coklu hesap, doviz islemleri.",
        min_bakiye=50_000.0,
        max_bakiye=10_000_000.0,
        kredi_skoru_min=800,
        kredi_skoru_max=1900,
        segment="Ticari",
        musteri_tipi="Ticari",
        hesap_sayisi_min=3,
        hesap_sayisi_max=10,
        islem_sayisi_min=20,
        islem_sayisi_max=100,
        islem_tutar_min=1_000.0,
        islem_tutar_max=5_000_000.0,
        yas_min=25,
        yas_max=70,
        ozel_kurallar={
            "hesap_tipleri": ["Cari", "Vadesiz", "Vadeli", "Yatirim"],
            "islem_tipleri": ["Havale", "EFT", "SWIFT", "Vergi", "SGK", "Maas"],
            "kanallar": ["Internet", "Sube", "API"],
            "para_birimleri": ["TRY", "USD", "EUR"],
            "vergi_no_gerekli": True,
        },
    ),

    ScenarioType.YENI_MUSTERI: ScenarioConfig(
        name="Yeni Musteri",
        description="Son 6 ayda hesap acmis yeni musteri. Dusuk bakiye, "
                    "az islem, kesif asamasinda.",
        min_bakiye=100.0,
        max_bakiye=10_000.0,
        kredi_skoru_min=400,
        kredi_skoru_max=1000,
        segment="Bireysel",
        musteri_tipi="Bireysel",
        hesap_sayisi_min=1,
        hesap_sayisi_max=1,
        islem_sayisi_min=1,
        islem_sayisi_max=10,
        islem_tutar_min=20.0,
        islem_tutar_max=3_000.0,
        yas_min=18,
        yas_max=45,
        ozel_kurallar={
            "hesap_tipleri": ["Vadesiz"],
            "islem_tipleri": ["Havale", "Kart", "ATM"],
            "kanallar": ["Mobil", "ATM"],
            "kayit_son_6_ay": True,
        },
    ),

    ScenarioType.EMEKLI: ScenarioConfig(
        name="Emekli Musteri",
        description="Emekli maasi alan yasli musteri. Duzenli maas girisi, "
                    "dusuk islem sikligi, tasarruf odakli.",
        min_bakiye=5_000.0,
        max_bakiye=200_000.0,
        kredi_skoru_min=700,
        kredi_skoru_max=1500,
        segment="Bireysel",
        musteri_tipi="Bireysel",
        hesap_sayisi_min=1,
        hesap_sayisi_max=3,
        islem_sayisi_min=5,
        islem_sayisi_max=15,
        islem_tutar_min=50.0,
        islem_tutar_max=10_000.0,
        yas_min=55,
        yas_max=85,
        ozel_kurallar={
            "hesap_tipleri": ["Vadesiz", "Vadeli", "Tasarruf"],
            "islem_tipleri": ["Emekli Maas", "Fatura", "Havale", "ATM"],
            "kanallar": ["Sube", "ATM", "Mobil"],
            "emekli_maas": True,
        },
    ),

    ScenarioType.OGRENCI: ScenarioConfig(
        name="Ogrenci Musteri",
        description="Universite ogrencisi musteri. Dusuk bakiye, burs/harclik "
                    "girisi, kucuk tutarli sik islem.",
        min_bakiye=0.0,
        max_bakiye=5_000.0,
        kredi_skoru_min=300,
        kredi_skoru_max=700,
        segment="Bireysel",
        musteri_tipi="Bireysel",
        hesap_sayisi_min=1,
        hesap_sayisi_max=1,
        islem_sayisi_min=10,
        islem_sayisi_max=40,
        islem_tutar_min=5.0,
        islem_tutar_max=1_000.0,
        yas_min=18,
        yas_max=26,
        ozel_kurallar={
            "hesap_tipleri": ["Vadesiz"],
            "islem_tipleri": ["Kart", "ATM", "Havale", "QR"],
            "kanallar": ["Mobil", "ATM"],
            "ogrenci_hesap": True,
        },
    ),
}


# =====================================================================
# Senaryo Uretim Sonuc Dataclass'i
# =====================================================================


@dataclass
class ScenarioResult:
    """
    Senaryo bazli uretim sonucu.

    Attributes:
        scenario_type: Kullanilan senaryo tipi
        config: Uygulanan konfigurasyon
        customers: Musteri DataFrame'i
        accounts: Hesap DataFrame'i
        transactions: Islem DataFrame'i
        metadata: Uretim meta bilgisi (sure, sayilar, parametreler)
    """

    scenario_type: Optional[str] = None
    config: Optional[ScenarioConfig] = None
    customers: Optional[pd.DataFrame] = None
    accounts: Optional[pd.DataFrame] = None
    transactions: Optional[pd.DataFrame] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def customer_count(self) -> int:
        """Uretilen musteri sayisi."""
        return len(self.customers) if self.customers is not None else 0

    @property
    def account_count(self) -> int:
        """Uretilen hesap sayisi."""
        return len(self.accounts) if self.accounts is not None else 0

    @property
    def transaction_count(self) -> int:
        """Uretilen islem sayisi."""
        return len(self.transactions) if self.transactions is not None else 0

    def summary(self) -> dict[str, Any]:
        """Uretim ozetini dondurur."""
        return {
            "senaryo": self.scenario_type,
            "musteri_sayisi": self.customer_count,
            "hesap_sayisi": self.account_count,
            "islem_sayisi": self.transaction_count,
            "metadata": self.metadata,
        }

    def to_dict(self) -> dict[str, Any]:
        """Tum sonucu dict olarak dondurur (DataFrame'ler records formatinda)."""
        return {
            "scenario_type": self.scenario_type,
            "config": asdict(self.config) if self.config else None,
            "customers": (
                self.customers.to_dict("records")
                if self.customers is not None else []
            ),
            "accounts": (
                self.accounts.to_dict("records")
                if self.accounts is not None else []
            ),
            "transactions": (
                self.transactions.to_dict("records")
                if self.transactions is not None else []
            ),
            "metadata": self.metadata,
        }


# =====================================================================
# Ana Sinif — ScenarioGenerator
# =====================================================================


class ScenarioGenerator:
    """
    Senaryo bazli sentetik bankacilik verisi uretici.

    SyntheticDataGenerator'i sarmalayarak senaryo konfigurasyonlarina
    gore tutarli musteri + hesap + islem veri setleri olusturur.

    Kullanim:
        gen = ScenarioGenerator(seed=42)

        # Tek senaryo
        result = gen.generate_scenario(ScenarioType.BIREYSEL, count=500)

        # Karisik dagilim
        dist = {
            ScenarioType.BIREYSEL: 0.40,
            ScenarioType.PREMIUM: 0.15,
            ScenarioType.MAAS: 0.20,
            ScenarioType.OGRENCI: 0.10,
            ScenarioType.EMEKLI: 0.15,
        }
        mixed = gen.generate_mixed_dataset(dist, total_count=5000)

        # CSV export
        gen.export_csv(result, output_dir="output/bireysel/")
    """

    def __init__(
        self,
        seed: Optional[int] = None,
        locale: str = "tr_TR",
    ) -> None:
        """
        ScenarioGenerator baslatici.

        Args:
            seed: Tekrarlanabilirlik icin rastgele tohum degeri
            locale: Faker locale (varsayilan: tr_TR)
        """
        self._seed = seed
        self._locale = locale
        self._generator = SyntheticDataGenerator(seed=seed, locale=locale)
        self._rng = random.Random(seed)
        self._np_rng = np.random.RandomState(seed)

        logger.info(
            "ScenarioGenerator baslatildi (seed=%s, locale=%s)",
            seed, locale,
        )

    # -- Tek Senaryo Uretimi ------------------------------------------

    def generate_scenario(
        self,
        scenario_type: ScenarioType,
        count: int = 1000,
        progress_callback: Optional[Callable[[GenerationProgress], None]] = None,
    ) -> ScenarioResult:
        """
        Belirli bir senaryo tipine gore veri seti uretir.

        Args:
            scenario_type: Senaryo tipi (ScenarioType enum)
            count: Uretilecek musteri sayisi
            progress_callback: Ilerleme bildirimi callback'i

        Returns:
            ScenarioResult — musteri, hesap ve islem DataFrame'leri

        Raises:
            ValueError: Gecersiz senaryo tipi veya count <= 0
        """
        if count <= 0:
            raise ValueError(f"Musteri sayisi pozitif olmali, verilen: {count}")

        if scenario_type not in SCENARIO_CONFIGS:
            raise ValueError(
                f"Bilinmeyen senaryo tipi: {scenario_type}. "
                f"Gecerli tipler: {[s.value for s in ScenarioType]}"
            )

        config = SCENARIO_CONFIGS[scenario_type]
        logger.info(
            "Senaryo uretimi basliyor: %s (%d musteri)",
            config.name, count,
        )

        return self._generate_from_config(
            config=config,
            count=count,
            scenario_type_name=scenario_type.value,
            progress_callback=progress_callback,
        )

    # -- Ozel Senaryo Uretimi -----------------------------------------

    def generate_custom_scenario(
        self,
        config: ScenarioConfig,
        count: int = 1000,
        progress_callback: Optional[Callable[[GenerationProgress], None]] = None,
    ) -> ScenarioResult:
        """
        Ozel konfigurasyon ile senaryo uretir.

        Args:
            config: Ozel ScenarioConfig nesnesi
            count: Uretilecek musteri sayisi
            progress_callback: Ilerleme bildirimi callback'i

        Returns:
            ScenarioResult — ozel senaryoya gore uretilmis veri seti
        """
        if count <= 0:
            raise ValueError(f"Musteri sayisi pozitif olmali, verilen: {count}")

        logger.info(
            "Ozel senaryo uretimi: %s (%d musteri)", config.name, count,
        )

        return self._generate_from_config(
            config=config,
            count=count,
            scenario_type_name="custom",
            progress_callback=progress_callback,
        )

    # -- Karisik Dagilim Uretimi --------------------------------------

    def generate_mixed_dataset(
        self,
        distribution: dict[ScenarioType, float],
        total_count: int = 10_000,
        progress_callback: Optional[Callable[[GenerationProgress], None]] = None,
    ) -> ScenarioResult:
        """
        Birden fazla senaryoyu belirli bir dagilimla karistirarak uretir.

        Args:
            distribution: {ScenarioType: oran} sozlugu (toplami ~1.0 olmali)
            total_count: Toplam musteri sayisi
            progress_callback: Ilerleme bildirimi callback'i

        Returns:
            ScenarioResult — tum senaryolardan birlestirilmis veri seti

        Raises:
            ValueError: Dagilim toplami 0 veya negatif oran varsa
        """
        if total_count <= 0:
            raise ValueError(f"Toplam musteri sayisi pozitif olmali: {total_count}")

        # Oranlari normalize et
        total_weight = sum(distribution.values())
        if total_weight <= 0:
            raise ValueError("Dagilim agirliklari toplami pozitif olmali")

        normalized: dict[ScenarioType, float] = {
            st: w / total_weight for st, w in distribution.items()
        }

        # Her senaryo icin musteri sayisini hesapla
        scenario_counts: dict[ScenarioType, int] = {}
        allocated = 0
        sorted_scenarios = sorted(
            normalized.items(), key=lambda x: x[1], reverse=True,
        )

        for i, (scenario_type, ratio) in enumerate(sorted_scenarios):
            if i == len(sorted_scenarios) - 1:
                # Son senaryo: kalan sayiyi al (yuvarlama farkini telafi)
                scenario_counts[scenario_type] = total_count - allocated
            else:
                cnt = max(1, round(total_count * ratio))
                scenario_counts[scenario_type] = cnt
                allocated += cnt

        logger.info(
            "Karisik veri seti uretimi: toplam=%d, dagilim=%s",
            total_count,
            {st.value: cnt for st, cnt in scenario_counts.items()},
        )

        # Her senaryoyu ayri uret
        all_customers: list[pd.DataFrame] = []
        all_accounts: list[pd.DataFrame] = []
        all_transactions: list[pd.DataFrame] = []
        metadata_parts: list[dict[str, Any]] = []

        for scenario_type, cnt in scenario_counts.items():
            if cnt <= 0:
                continue

            result = self.generate_scenario(
                scenario_type=scenario_type,
                count=cnt,
                progress_callback=progress_callback,
            )

            if result.customers is not None:
                # Senaryo etiketi ekle
                result.customers["senaryo"] = scenario_type.value
                all_customers.append(result.customers)

            if result.accounts is not None:
                result.accounts["senaryo"] = scenario_type.value
                all_accounts.append(result.accounts)

            if result.transactions is not None:
                result.transactions["senaryo"] = scenario_type.value
                all_transactions.append(result.transactions)

            metadata_parts.append({
                "senaryo": scenario_type.value,
                "musteri_sayisi": result.customer_count,
                "hesap_sayisi": result.account_count,
                "islem_sayisi": result.transaction_count,
            })

        # DataFrame'leri birlestir
        combined = ScenarioResult(
            scenario_type="mixed",
            config=None,
            customers=(
                pd.concat(all_customers, ignore_index=True)
                if all_customers else pd.DataFrame()
            ),
            accounts=(
                pd.concat(all_accounts, ignore_index=True)
                if all_accounts else pd.DataFrame()
            ),
            transactions=(
                pd.concat(all_transactions, ignore_index=True)
                if all_transactions else pd.DataFrame()
            ),
            metadata={
                "distribution": {st.value: r for st, r in normalized.items()},
                "scenario_details": metadata_parts,
                "total_count": total_count,
            },
        )

        logger.info(
            "Karisik veri seti tamamlandi: %d musteri, %d hesap, %d islem",
            combined.customer_count,
            combined.account_count,
            combined.transaction_count,
        )

        return combined

    # -- Ic Uretim Motoru ---------------------------------------------

    def _generate_from_config(
        self,
        config: ScenarioConfig,
        count: int,
        scenario_type_name: str,
        progress_callback: Optional[Callable[[GenerationProgress], None]] = None,
    ) -> ScenarioResult:
        """
        ScenarioConfig'e gore musteri + hesap + islem uretir.

        Ic metod — generate_scenario() ve generate_custom_scenario()
        tarafindan cagrilir.
        """
        import time
        start_time = time.time()

        ozel = config.ozel_kurallar
        hesap_tipleri = ozel.get("hesap_tipleri", ["Vadesiz", "Tasarruf"])
        islem_tipleri = ozel.get(
            "islem_tipleri", ["Havale", "EFT", "Kart", "ATM"],
        )
        kanallar = ozel.get("kanallar", ["Mobil", "Internet", "ATM", "Sube"])
        para_birimleri = ozel.get("para_birimleri", ["TRY"])

        # -- 1. Musteri Uretimi ----------------------------------------
        customers_data: list[dict[str, Any]] = []
        progress = GenerationProgress(
            table_name="customers",
            total_rows=count,
            total_chunks=1,
            status="running",
        )

        for i in range(count):
            yas = self._rng.randint(config.yas_min, config.yas_max)
            dogum_yili = date.today().year - yas
            dogum_ayi = self._rng.randint(1, 12)
            dogum_gunu = self._rng.randint(1, 28)
            dogum_tarihi = date(dogum_yili, dogum_ayi, dogum_gunu)

            kredi_notu = self._rng.randint(
                config.kredi_skoru_min, config.kredi_skoru_max,
            )

            # Kayit tarihi — yeni musteri senaryosu icin son 6 ay
            if ozel.get("kayit_son_6_ay"):
                kayit_gun_once = self._rng.randint(1, 180)
            else:
                kayit_gun_once = self._rng.randint(30, 3650)
            kayit_tarihi = date.today() - timedelta(days=kayit_gun_once)

            first_name = self._generator._gen_first_name()
            last_name = self._generator._gen_last_name()

            customer = {
                "musteri_no": f"MUS{100000 + i:08d}",
                "tckn": self._generator._gen_tckn(),
                "ad": first_name,
                "soyad": last_name,
                "dogum_tarihi": dogum_tarihi.isoformat(),
                "yas": yas,
                "cinsiyet": self._rng.choice(["E", "K"]),
                "telefon": self._generator._gen_phone(),
                "email": self._generator._gen_email(),
                "adres": self._generator._gen_address(),
                "sehir": self._generator._pick_weighted_city()["name"],
                "ilce": self._rng.choice(
                    self._generator._pick_weighted_city()["districts"]
                ),
                "segment": config.segment,
                "musteri_tipi": config.musteri_tipi,
                "kredi_notu": kredi_notu,
                "kayit_tarihi": kayit_tarihi.isoformat(),
            }
            customers_data.append(customer)

            if (i + 1) % 500 == 0:
                progress.generated_rows = i + 1
                if progress_callback:
                    progress_callback(progress)

        customers_df = pd.DataFrame(customers_data)
        progress.generated_rows = count
        progress.status = "completed"
        if progress_callback:
            progress_callback(progress)

        # -- 2. Hesap Uretimi ------------------------------------------
        accounts_data: list[dict[str, Any]] = []
        account_idx = 0

        for _, customer in customers_df.iterrows():
            num_accounts = self._rng.randint(
                config.hesap_sayisi_min, config.hesap_sayisi_max,
            )

            for _ in range(num_accounts):
                bakiye = self._np_rng.uniform(
                    config.min_bakiye, config.max_bakiye,
                )
                # Lognormal dagilim uygula (gercekci bakiye dagilimi)
                if config.min_bakiye >= 0:
                    log_mean = math.log(
                        max(1, (config.min_bakiye + config.max_bakiye) / 4)
                    )
                    log_std = 0.8
                    bakiye = float(
                        np.clip(
                            self._np_rng.lognormal(log_mean, log_std),
                            config.min_bakiye,
                            config.max_bakiye,
                        )
                    )

                hesap_tipi = self._rng.choice(hesap_tipleri)
                para_birimi = self._rng.choice(para_birimleri)

                # Hesap durumu — dormant senaryosunda Pasif
                if ozel.get("hesap_durumu") == "Pasif":
                    hesap_durumu = "Pasif"
                else:
                    hesap_durumu = self._rng.choices(
                        ["Aktif", "Pasif", "Kapali", "Donmus"],
                        weights=[0.80, 0.10, 0.05, 0.05],
                    )[0]

                # Faiz orani — hesap tipine gore
                if hesap_tipi == "Vadeli":
                    faiz_orani = round(self._np_rng.uniform(15.0, 55.0), 2)
                elif hesap_tipi == "Tasarruf":
                    faiz_orani = round(self._np_rng.uniform(5.0, 30.0), 2)
                else:
                    faiz_orani = 0.0

                account = {
                    "hesap_no": f"HSP{200000 + account_idx:010d}",
                    "musteri_no": customer["musteri_no"],
                    "iban": self._generator._gen_iban(),
                    "hesap_tipi": hesap_tipi,
                    "hesap_durumu": hesap_durumu,
                    "bakiye": round(bakiye, 2),
                    "para_birimi": para_birimi,
                    "faiz_orani": faiz_orani,
                    "sube_kodu": self._generator._gen_branch_code(),
                    "acilis_tarihi": customer["kayit_tarihi"],
                }
                accounts_data.append(account)
                account_idx += 1

        accounts_df = pd.DataFrame(accounts_data)

        # -- 3. Islem Uretimi ------------------------------------------
        transactions_data: list[dict[str, Any]] = []
        txn_idx = 0

        for _, account in accounts_df.iterrows():
            num_txns = self._rng.randint(
                config.islem_sayisi_min, config.islem_sayisi_max,
            )

            for _ in range(num_txns):
                # Islem tutari — lognormal dagilim
                if config.islem_tutar_max > 0:
                    log_mean = math.log(
                        max(
                            1,
                            (config.islem_tutar_min + config.islem_tutar_max) / 4,
                        )
                    )
                    tutar = float(
                        np.clip(
                            self._np_rng.lognormal(log_mean, 0.7),
                            config.islem_tutar_min,
                            config.islem_tutar_max,
                        )
                    )
                else:
                    tutar = 0.0

                # Islem tarihi — son 1 yil icinde rastgele
                gun_once = self._rng.randint(0, 365)
                islem_tarihi = date.today() - timedelta(days=gun_once)

                islem_tipi = self._rng.choice(islem_tipleri)
                kanal = self._rng.choice(kanallar)

                # Yon: gelen/giden
                yon = self._rng.choices(
                    ["Giden", "Gelen"],
                    weights=[0.60, 0.40],
                )[0]

                transaction = {
                    "islem_no": f"TXN{300000 + txn_idx:012d}",
                    "hesap_no": account["hesap_no"],
                    "musteri_no": account["musteri_no"],
                    "islem_tarihi": islem_tarihi.isoformat(),
                    "islem_tipi": islem_tipi,
                    "tutar": round(tutar, 2),
                    "para_birimi": account["para_birimi"],
                    "yon": yon,
                    "kanal": kanal,
                    "aciklama": self._generate_description(islem_tipi, tutar),
                    "referans_no": uuid.uuid4().hex[:12].upper(),
                }
                transactions_data.append(transaction)
                txn_idx += 1

        transactions_df = pd.DataFrame(transactions_data)

        elapsed = time.time() - start_time

        result = ScenarioResult(
            scenario_type=scenario_type_name,
            config=config,
            customers=customers_df,
            accounts=accounts_df,
            transactions=transactions_df,
            metadata={
                "sure_saniye": round(elapsed, 2),
                "musteri_sayisi": len(customers_df),
                "hesap_sayisi": len(accounts_df),
                "islem_sayisi": len(transactions_df),
                "senaryo_adi": config.name,
                "seed": self._seed,
            },
        )

        logger.info(
            "Senaryo uretimi tamamlandi: %s — %d musteri, %d hesap, %d islem (%.2f sn)",
            config.name,
            result.customer_count,
            result.account_count,
            result.transaction_count,
            elapsed,
        )

        return result

    # -- Islem Aciklama Uretici ---------------------------------------

    def _generate_description(self, islem_tipi: str, tutar: float) -> str:
        """Islem tipine gore Turkce aciklama uretir."""
        templates: dict[str, list[str]] = {
            "Havale": [
                f"{tutar:,.2f} TL havale gonderimi",
                "Bireysel havale islemi",
                "Hesaplar arasi transfer",
            ],
            "EFT": [
                f"{tutar:,.2f} TL EFT gonderimi",
                "Banka disi EFT transferi",
                "EFT — farkli banka hesabina",
            ],
            "SWIFT": [
                "Uluslararasi para transferi",
                "SWIFT transfer islemi",
                f"Doviz transferi — {tutar:,.2f}",
            ],
            "Kart": [
                "Kart ile alisveris",
                "POS harcamasi",
                "Online alisveris odemesi",
            ],
            "ATM": [
                "ATM nakit cekimi",
                "ATM para yatirma",
                "ATM bakiye sorgulama",
            ],
            "Fatura": [
                "Elektrik faturasi odemesi",
                "Dogalgaz faturasi odemesi",
                "Su faturasi odemesi",
                "Telefon faturasi odemesi",
                "Internet faturasi odemesi",
            ],
            "Maas": [
                "Aylik maas odemesi",
                "Maas girisi",
            ],
            "Emekli Maas": [
                "Emekli maas odemesi",
                "SGK emekli ayligi",
            ],
            "Vergi": [
                "KDV odemesi",
                "Gelir vergisi odemesi",
                "Kurumlar vergisi",
            ],
            "Yatirim": [
                "Hisse senedi alim",
                "Yatirim fonu alimi",
                "Altin alis islemi",
            ],
            "Taksit": [
                "Kredi karti taksit odemesi",
                "Bireysel kredi taksiti",
            ],
            "Gecikme Faizi": [
                "Gecikme faizi tahakkuku",
                "Kredi karti gecikme cezasi",
            ],
            "Icra": [
                "Icra kesintisi",
                "Haciz islemi",
            ],
            "SGK": [
                "SGK prim odemesi",
                "Sosyal guvenlik kesintisi",
            ],
            "Masraf": [
                "Hesap isletim ucreti",
                "Yillik kart aidati",
            ],
            "Faiz": [
                "Mevduat faiz geliri",
                "Vadeli hesap faiz odemesi",
            ],
            "QR": [
                "QR kod ile odeme",
                "QR para transferi",
            ],
            "Temassiz": [
                "Temassiz kart odemesi",
                "Contactless islem",
            ],
        }

        choices = templates.get(islem_tipi, [f"{islem_tipi} islemi"])
        return self._rng.choice(choices)

    # -- CSV Export ---------------------------------------------------

    def export_csv(
        self,
        result: ScenarioResult,
        output_dir: str = "output",
        prefix: str = "",
        encoding: str = "utf-8-sig",
    ) -> dict[str, str]:
        """
        ScenarioResult'i CSV dosyalarina yazar.

        Args:
            result: Uretim sonucu
            output_dir: Cikti klasoru
            prefix: Dosya adi on eki (opsiyonel)
            encoding: Dosya kodlamasi (varsayilan: utf-8-sig — Excel uyumlu)

        Returns:
            {tablo_adi: dosya_yolu} sozlugu
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_prefix = f"{prefix}_" if prefix else ""
        scenario_name = result.scenario_type or "custom"
        paths: dict[str, str] = {}

        for table_name, df in [
            ("customers", result.customers),
            ("accounts", result.accounts),
            ("transactions", result.transactions),
        ]:
            if df is not None and not df.empty:
                filename = f"{file_prefix}{scenario_name}_{table_name}.csv"
                filepath = output_path / filename
                df.to_csv(filepath, index=False, encoding=encoding)
                paths[table_name] = str(filepath)
                logger.info("CSV yazildi: %s (%d satir)", filepath, len(df))

        return paths

    # -- JSON Export --------------------------------------------------

    def export_json(
        self,
        result: ScenarioResult,
        output_dir: str = "output",
        prefix: str = "",
    ) -> dict[str, str]:
        """
        ScenarioResult'i JSON dosyalarina yazar.

        Args:
            result: Uretim sonucu
            output_dir: Cikti klasoru
            prefix: Dosya adi on eki

        Returns:
            {tablo_adi: dosya_yolu} sozlugu
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_prefix = f"{prefix}_" if prefix else ""
        scenario_name = result.scenario_type or "custom"
        paths: dict[str, str] = {}

        for table_name, df in [
            ("customers", result.customers),
            ("accounts", result.accounts),
            ("transactions", result.transactions),
        ]:
            if df is not None and not df.empty:
                filename = f"{file_prefix}{scenario_name}_{table_name}.json"
                filepath = output_path / filename

                records = df.to_dict("records")
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "scenario": scenario_name,
                            "table": table_name,
                            "count": len(records),
                            "data": records,
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                        default=str,
                    )
                paths[table_name] = str(filepath)
                logger.info("JSON yazildi: %s (%d kayit)", filepath, len(df))

        return paths

    # -- Mevcut Senaryolari Listele -----------------------------------

    @staticmethod
    def list_scenarios() -> list[dict[str, Any]]:
        """
        Tum tanimli senaryolari listeler.

        Returns:
            Senaryo listesi — her biri ad, aciklama ve parametre araliklarini icerir.
        """
        scenarios: list[dict[str, Any]] = []
        for st in ScenarioType:
            cfg = SCENARIO_CONFIGS[st]
            scenarios.append({
                "type": st.value,
                "name": cfg.name,
                "description": cfg.description,
                "bakiye_araligi": (
                    f"{cfg.min_bakiye:,.0f} - {cfg.max_bakiye:,.0f} TRY"
                ),
                "kredi_skoru_araligi": (
                    f"{cfg.kredi_skoru_min} - {cfg.kredi_skoru_max}"
                ),
                "segment": cfg.segment,
                "musteri_tipi": cfg.musteri_tipi,
                "hesap_sayisi": (
                    f"{cfg.hesap_sayisi_min} - {cfg.hesap_sayisi_max}"
                ),
                "islem_sayisi": (
                    f"{cfg.islem_sayisi_min} - {cfg.islem_sayisi_max}"
                ),
                "yas_araligi": f"{cfg.yas_min} - {cfg.yas_max}",
            })
        return scenarios

    # -- Senaryo Adindan Tip Bulma ------------------------------------

    @staticmethod
    def find_scenario_by_keyword(keyword: str) -> Optional[ScenarioType]:
        """
        Anahtar kelimeye gore senaryo tipini bulur.

        Args:
            keyword: Arama metni (Turkce veya Ingilizce)

        Returns:
            Eslesen ScenarioType veya None
        """
        keyword_lower = keyword.lower().strip()

        # Dogrudan enum degeri eslesmesi
        for st in ScenarioType:
            if st.value == keyword_lower:
                return st

        # Anahtar kelime eslestirme tablosu
        keyword_map: dict[str, ScenarioType] = {
            "bireysel": ScenarioType.BIREYSEL,
            "standart": ScenarioType.BIREYSEL,
            "normal": ScenarioType.BIREYSEL,
            "premium": ScenarioType.PREMIUM,
            "vip": ScenarioType.PREMIUM,
            "platinum": ScenarioType.PREMIUM,
            "maas": ScenarioType.MAAS,
            "salary": ScenarioType.MAAS,
            "calisan": ScenarioType.MAAS,
            "yuksek bakiye": ScenarioType.YUKSEK_BAKIYELI,
            "zengin": ScenarioType.YUKSEK_BAKIYELI,
            "high balance": ScenarioType.YUKSEK_BAKIYELI,
            "gecikmeli": ScenarioType.KREDI_KARTI_GECIKMELI,
            "gecikme": ScenarioType.KREDI_KARTI_GECIKMELI,
            "kredi karti": ScenarioType.KREDI_KARTI_GECIKMELI,
            "overdue": ScenarioType.KREDI_KARTI_GECIKMELI,
            "cok islem": ScenarioType.COK_ISLEM,
            "aktif": ScenarioType.COK_ISLEM,
            "yogun": ScenarioType.COK_ISLEM,
            "high volume": ScenarioType.COK_ISLEM,
            "dormant": ScenarioType.DORMANT,
            "hareketsiz": ScenarioType.DORMANT,
            "uykuda": ScenarioType.DORMANT,
            "pasif": ScenarioType.DORMANT,
            "inactive": ScenarioType.DORMANT,
            "riskli": ScenarioType.RISKLI,
            "risk": ScenarioType.RISKLI,
            "yuksek risk": ScenarioType.RISKLI,
            "high risk": ScenarioType.RISKLI,
            "ticari": ScenarioType.TICARI,
            "kurumsal": ScenarioType.TICARI,
            "sirket": ScenarioType.TICARI,
            "corporate": ScenarioType.TICARI,
            "commercial": ScenarioType.TICARI,
            "yeni": ScenarioType.YENI_MUSTERI,
            "yeni musteri": ScenarioType.YENI_MUSTERI,
            "new customer": ScenarioType.YENI_MUSTERI,
            "emekli": ScenarioType.EMEKLI,
            "retired": ScenarioType.EMEKLI,
            "pensioner": ScenarioType.EMEKLI,
            "ogrenci": ScenarioType.OGRENCI,
            "student": ScenarioType.OGRENCI,
            "universite": ScenarioType.OGRENCI,
        }

        # Tam esleme
        if keyword_lower in keyword_map:
            return keyword_map[keyword_lower]

        # Alt-string esleme
        for key, scenario_type in keyword_map.items():
            if key in keyword_lower or keyword_lower in key:
                return scenario_type

        return None

    # -- Senaryo Ozeti ------------------------------------------------

    @staticmethod
    def get_scenario_summary(scenario_type: ScenarioType) -> dict[str, Any]:
        """
        Belirli bir senaryonun detayli ozetini dondurur.

        Args:
            scenario_type: ScenarioType enum degeri

        Returns:
            Senaryo detaylari dict'i
        """
        cfg = SCENARIO_CONFIGS[scenario_type]
        return {
            "type": scenario_type.value,
            "name": cfg.name,
            "description": cfg.description,
            "parametreler": {
                "bakiye": {"min": cfg.min_bakiye, "max": cfg.max_bakiye},
                "kredi_skoru": {
                    "min": cfg.kredi_skoru_min,
                    "max": cfg.kredi_skoru_max,
                },
                "segment": cfg.segment,
                "musteri_tipi": cfg.musteri_tipi,
                "hesap_sayisi": {
                    "min": cfg.hesap_sayisi_min,
                    "max": cfg.hesap_sayisi_max,
                },
                "islem_sayisi": {
                    "min": cfg.islem_sayisi_min,
                    "max": cfg.islem_sayisi_max,
                },
                "islem_tutari": {
                    "min": cfg.islem_tutar_min,
                    "max": cfg.islem_tutar_max,
                },
                "yas": {"min": cfg.yas_min, "max": cfg.yas_max},
            },
            "ozel_kurallar": cfg.ozel_kurallar,
        }
