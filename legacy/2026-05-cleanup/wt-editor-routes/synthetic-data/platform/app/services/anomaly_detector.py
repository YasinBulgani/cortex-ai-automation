"""
Anomali Tespit Modülü - Bankacılık Verisi İçin

Bu modül, sentetik bankacılık verilerinde 9 farklı anomali türünü tespit eden
kapsamlı bir anomali dedektörü sağlar. İstatistiksel, kural tabanlı ve
bütünlük denetimi yöntemlerini birleştirir.

Desteklenen Anomali Türleri:
    Z_SCORE           : İstatistiksel aykırı değer (z-skoru > eşik)
    IQR               : Çeyrekler arası aralık tabanlı aykırı değer
    NEGATIVE_BALANCE  : Negatif hesap bakiyesi kuralı ihlali
    DATE_INCONSISTENCY: Gelecekteki tarihler veya tutarsız tarih aralıkları
    FK_INTEGRITY      : Yabancı anahtar bütünlüğü ihlali
    VALUE_RANGE       : İş kuralı değer aralığı ihlali
    NULL_RATIO        : Kabul edilemez yüksek null/NaN oranı
    DUPLICATE         : Tekrarlanan satır veya kritik alan tespiti
    DISTRIBUTION      : Gerçek/sentetik dağılım kayması

Bankacılığa Özgü Kurallar:
    - Hesap bakiyesi >= 0 (bireysel hesaplar için)
    - İşlem tutarı: -1,000,000 ile 10,000,000 TL arasında
    - Tarihler gelecekte olamaz
    - IBAN formatı: TR + 24 rakam
    - Faiz oranı: 0-100 arasında
    - Kredi skoru: 300-900 arasında

Kullanım:
    >>> detector = AnomalyDetector()
    >>> anomalies = detector.detect_all(dataframe, schema)
    >>> report = detector.generate_report(anomalies)
    >>> print(report['ozet']['toplam_anomali'])
"""

import numpy as np
import pandas as pd
import logging
import json
import re
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from enum import Enum
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sabitler: Bankacılığa özgü değer aralıkları
# ---------------------------------------------------------------------------

# İşlem miktarı sınırları (TL)
TRANSACTION_MIN_AMOUNT = -1_000_000.0
TRANSACTION_MAX_AMOUNT = 10_000_000.0

# Hesap bakiyesi sınırları
ACCOUNT_BALANCE_MIN = 0.0
ACCOUNT_BALANCE_MAX = 1_000_000_000.0  # 1 Milyar TL

# Faiz oranı sınırları (%)
INTEREST_RATE_MIN = 0.0
INTEREST_RATE_MAX = 100.0

# Kredi skoru sınırları
CREDIT_SCORE_MIN = 300
CREDIT_SCORE_MAX = 900

# Yaş sınırları
AGE_MIN = 18
AGE_MAX = 120

# TC Kimlik numarası uzunluğu
TC_ID_LENGTH = 11

# IBAN deseni (Türk IBAN: TR + 24 rakam)
IBAN_PATTERN = re.compile(r'^TR\d{24}$')

# İzin verilen null oranı eşiği
NULL_RATIO_THRESHOLD = 0.10  # %10

# Z-skor eşiği
Z_SCORE_THRESHOLD = 3.0

# IQR çarpanı
IQR_MULTIPLIER = 1.5

# Kritik sütun adı kalıpları (bankacılık)
BALANCE_COLUMNS = ['balance', 'bakiye', 'hesap_bakiyesi', 'account_balance',
                   'musteri_bakiyesi', 'borc', 'alacak']
AMOUNT_COLUMNS = ['amount', 'tutar', 'islem_tutari', 'transaction_amount',
                  'odeme_tutari', 'fatura_tutari', 'borc_tutari']
DATE_COLUMNS = ['date', 'tarih', 'islem_tarihi', 'transaction_date',
                'kayit_tarihi', 'olusturma_tarihi', 'guncelleme_tarihi',
                'vade_tarihi', 'dogum_tarihi']
RATE_COLUMNS = ['rate', 'faiz_orani', 'interest_rate', 'oran', 'yuzde']
CREDIT_SCORE_COLUMNS = ['credit_score', 'kredi_skoru', 'skor', 'score']
IBAN_COLUMNS = ['iban', 'hesap_no', 'account_number']
ID_COLUMNS = ['id', 'customer_id', 'musteri_id', 'transaction_id',
              'account_id', 'hesap_id', 'islem_id']


# ===========================================================================
# Enum Tanımlamaları
# ===========================================================================

class AnomalyType(Enum):
    """
    Desteklenen anomali türlerini listeler.

    Değerler:
        Z_SCORE           : İstatistiksel z-skor tabanlı aykırı değer
        IQR               : Çeyrekler arası aralık tabanlı aykırı değer
        NEGATIVE_BALANCE  : Negatif bakiye ihlali
        DATE_INCONSISTENCY: Tarih tutarsızlığı (gelecek, yanlış format vb.)
        FK_INTEGRITY      : Yabancı anahtar bütünlüğü ihlali
        VALUE_RANGE       : Değer aralığı ihlali
        NULL_RATIO        : Null oranı eşiği ihlali
        DUPLICATE         : Tekrarlanan kayıt
        DISTRIBUTION      : Dağılım sapması
    """

    Z_SCORE = "z_score"
    IQR = "iqr"
    NEGATIVE_BALANCE = "negative_balance"
    DATE_INCONSISTENCY = "date_inconsistency"
    FK_INTEGRITY = "fk_integrity"
    VALUE_RANGE = "value_range"
    NULL_RATIO = "null_ratio"
    DUPLICATE = "duplicate"
    DISTRIBUTION = "distribution"


class AnomalySeverity(Enum):
    """
    Anomali şiddet seviyeleri.

    Değerler:
        CRITICAL: Acil müdahale gerektiren kritik sorun
        HIGH    : Yüksek öncelikli sorun
        MEDIUM  : Orta öncelikli sorun
        LOW     : Düşük öncelikli bilgi amaçlı sorun
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ===========================================================================
# Veri Sınıfları
# ===========================================================================

@dataclass
class Anomaly:
    """
    Tek bir anomali tespitini temsil eder.

    Alanlar:
        type          : Anomali türü (AnomalyType enum değeri)
        severity      : Şiddet seviyesi (AnomalySeverity enum değeri)
        column        : Anomalinin tespit edildiği sütun adı
        description   : Anomalinin Türkçe açıklaması
        confidence    : Güven skoru [0.0, 1.0]
        row_indices   : Anomali içeren satır indeksleri listesi
        value         : Anomalik değer (veya temsili değer)
        expected_range: Beklenen değer aralığı demeti (min, max) veya None
    """

    type: AnomalyType
    severity: AnomalySeverity
    column: str
    description: str
    confidence: float
    row_indices: List[int]
    value: Any
    expected_range: Optional[tuple]

    def to_dict(self) -> Dict[str, Any]:
        """Anomaliyi JSON serileştirilebilir sözlüğe çevirir."""
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "column": self.column,
            "description": self.description,
            "confidence": round(float(self.confidence), 4),
            "row_count": len(self.row_indices),
            "row_indices_sample": self.row_indices[:20],  # İlk 20 indeks
            "value": self._serialize_value(self.value),
            "expected_range": list(self.expected_range) if self.expected_range else None,
        }

    @staticmethod
    def _serialize_value(val: Any) -> Any:
        """Değeri JSON serileştirilebilir forma çevirir."""
        if isinstance(val, (np.integer, np.int64, np.int32)):
            return int(val)
        elif isinstance(val, (np.floating, np.float64, np.float32)):
            return float(val)
        elif isinstance(val, np.ndarray):
            return val.tolist()
        elif isinstance(val, (datetime, date)):
            return val.isoformat()
        elif isinstance(val, pd.Timestamp):
            return val.isoformat()
        return val

    def is_critical(self) -> bool:
        """Anomali kritik mi?"""
        return self.severity == AnomalySeverity.CRITICAL

    def affects_many_rows(self, threshold: int = 10) -> bool:
        """Anomali belirtilen eşikten fazla satırı etkiliyor mu?"""
        return len(self.row_indices) >= threshold


# ===========================================================================
# AnomalyDetector
# ===========================================================================

class AnomalyDetector:
    """
    Bankacılık verisi için kapsamlı anomali dedektörü.

    9 farklı anomali türünü istatistiksel, kural tabanlı ve bütünlük
    kontrolleriyle tespit eder. Toplu işlem (batch) desteği de sunar.

    Parametreler:
        z_score_threshold : Z-skor eşiği (varsayılan 3.0)
        iqr_multiplier    : IQR çarpanı (varsayılan 1.5)
        null_threshold    : Null oranı uyarı eşiği (varsayılan 0.10)
        strict_mode       : Sıkı mod - daha katı kural uygulaması

    Örnek:
        >>> detector = AnomalyDetector(z_score_threshold=3.0)
        >>> schema = {"sutunlar": {"bakiye": {"tur": "float", "min": 0}}}
        >>> anomalies = detector.detect_all(df, schema)
        >>> report = detector.generate_report(anomalies)
    """

    def __init__(
        self,
        z_score_threshold: float = Z_SCORE_THRESHOLD,
        iqr_multiplier: float = IQR_MULTIPLIER,
        null_threshold: float = NULL_RATIO_THRESHOLD,
        strict_mode: bool = False,
    ):
        """
        AnomalyDetector'ı başlatır.

        Parametreler:
            z_score_threshold: Aykırı değer için z-skor eşiği
            iqr_multiplier   : IQR tabanlı eşik için çarpan
            null_threshold   : Kabul edilebilir maksimum null oranı
            strict_mode      : True ise daha katı bankacılık kuralları uygulanır
        """
        self.z_score_threshold = z_score_threshold
        self.iqr_multiplier = iqr_multiplier
        self.null_threshold = null_threshold
        self.strict_mode = strict_mode
        self._eps = 1e-8

        logger.info(
            f"AnomalyDetector başlatıldı: "
            f"z_threshold={z_score_threshold}, iqr={iqr_multiplier}, "
            f"null_thr={null_threshold}, strict={strict_mode}"
        )

    # ------------------------------------------------------------------
    # Ana Tespit Metodu
    # ------------------------------------------------------------------

    def detect_all(
        self,
        data: pd.DataFrame,
        schema: Optional[Dict[str, Any]] = None,
    ) -> List[Anomaly]:
        """
        Tüm anomali türlerini tek seferde tespit eder.

        İstatistiksel, iş kuralı ve bütünlük kontrollerini sırayla çalıştırır
        ve tüm anomalileri birleştirerek döner.

        Parametreler:
            data  : Kontrol edilecek DataFrame
            schema: İsteğe bağlı şema sözlüğü (sütun tipi ve kural tanımları)

        Döner:
            Tüm tespit edilen Anomaly nesnelerinin listesi

        Kaldırır:
            ValueError: data bir DataFrame değilse
        """
        if not isinstance(data, pd.DataFrame):
            raise ValueError("data bir pandas DataFrame olmalıdır.")

        if schema is None:
            schema = {}

        logger.info(
            f"Anomali tespiti başlıyor: {len(data)} satır, "
            f"{len(data.columns)} sütun"
        )

        all_anomalies: List[Anomaly] = []

        # 1. İstatistiksel anomaliler
        try:
            stat_anomalies = self.detect_statistical(data)
            all_anomalies.extend(stat_anomalies)
            logger.debug(f"İstatistiksel anomali: {len(stat_anomalies)} adet")
        except Exception as e:
            logger.warning(f"İstatistiksel tespit hatası: {e}")

        # 2. İş kuralı anomalileri
        try:
            biz_anomalies = self.detect_business_rule(data, schema)
            all_anomalies.extend(biz_anomalies)
            logger.debug(f"İş kuralı anomalisi: {len(biz_anomalies)} adet")
        except Exception as e:
            logger.warning(f"İş kuralı tespiti hatası: {e}")

        # 3. Bütünlük anomalileri
        try:
            int_anomalies = self.detect_integrity(data, schema)
            all_anomalies.extend(int_anomalies)
            logger.debug(f"Bütünlük anomalisi: {len(int_anomalies)} adet")
        except Exception as e:
            logger.warning(f"Bütünlük tespiti hatası: {e}")

        # Şiddet sırasına göre sırala (CRITICAL önce)
        severity_order = {
            AnomalySeverity.CRITICAL: 0,
            AnomalySeverity.HIGH: 1,
            AnomalySeverity.MEDIUM: 2,
            AnomalySeverity.LOW: 3,
        }
        all_anomalies.sort(key=lambda a: (severity_order.get(a.severity, 4), -a.confidence))

        logger.info(f"Toplam {len(all_anomalies)} anomali tespit edildi.")
        return all_anomalies

    # ------------------------------------------------------------------
    # 1. İstatistiksel Anomali Tespiti
    # ------------------------------------------------------------------

    def detect_statistical(
        self,
        data: pd.DataFrame,
    ) -> List[Anomaly]:
        """
        Z-skor ve IQR tabanlı istatistiksel anomali tespiti.

        Sayısal sütunlara z-skor ve IQR yöntemlerini uygular.
        Her sütun için ayrı anomali nesneleri oluşturur.

        Parametreler:
            data: Kontrol edilecek DataFrame

        Döner:
            Z_SCORE ve IQR tipinde Anomaly nesnelerinin listesi
        """
        anomalies: List[Anomaly] = []

        for col in data.columns:
            if not pd.api.types.is_numeric_dtype(data[col]):
                continue

            vals = data[col].dropna().values.astype(float)
            if len(vals) < 5:
                continue  # Yetersiz veri

            valid_indices = data[col].dropna().index.tolist()

            # Z-SKOR anomali tespiti
            z_anomalies = self._detect_z_score(data, col, valid_indices, vals)
            anomalies.extend(z_anomalies)

            # IQR anomali tespiti
            iqr_anomalies = self._detect_iqr(data, col, valid_indices, vals)
            anomalies.extend(iqr_anomalies)

        return anomalies

    def _detect_z_score(
        self,
        data: pd.DataFrame,
        col: str,
        valid_indices: List[int],
        vals: np.ndarray,
    ) -> List[Anomaly]:
        """
        Tek bir sütun için z-skor anomali tespiti.

        Parametreler:
            data         : DataFrame
            col          : Sütun adı
            valid_indices: NaN olmayan satır indeksleri
            vals         : NaN temizlenmiş sayısal değerler

        Döner:
            Z_SCORE tipinde Anomaly listesi (0 veya 1 eleman)
        """
        mean = np.mean(vals)
        std = np.std(vals)

        if std < self._eps:
            return []  # Sabit sütun

        z_scores = np.abs((vals - mean) / std)
        outlier_mask = z_scores > self.z_score_threshold

        if not np.any(outlier_mask):
            return []

        # Anomalik satır indeksleri
        anomaly_rows = [valid_indices[i] for i in np.where(outlier_mask)[0]]
        max_z = float(np.max(z_scores[outlier_mask]))

        # Şiddet belirleme
        if max_z > 5.0:
            severity = AnomalySeverity.HIGH
            confidence = 0.95
        elif max_z > 4.0:
            severity = AnomalySeverity.MEDIUM
            confidence = 0.85
        else:
            severity = AnomalySeverity.LOW
            confidence = 0.70

        outlier_vals = vals[outlier_mask]
        representative_val = float(outlier_vals[np.argmax(z_scores[outlier_mask])])

        return [Anomaly(
            type=AnomalyType.Z_SCORE,
            severity=severity,
            column=col,
            description=(
                f"'{col}' sütununda {len(anomaly_rows)} aykırı değer tespit edildi. "
                f"Maksimum z-skor: {max_z:.2f} (eşik: {self.z_score_threshold}). "
                f"Ortalama: {mean:.4f}, Std: {std:.4f}"
            ),
            confidence=confidence,
            row_indices=anomaly_rows,
            value=representative_val,
            expected_range=(float(mean - self.z_score_threshold * std),
                            float(mean + self.z_score_threshold * std)),
        )]

    def _detect_iqr(
        self,
        data: pd.DataFrame,
        col: str,
        valid_indices: List[int],
        vals: np.ndarray,
    ) -> List[Anomaly]:
        """
        Tek bir sütun için IQR tabanlı anomali tespiti.

        Parametreler:
            data         : DataFrame
            col          : Sütun adı
            valid_indices: NaN olmayan satır indeksleri
            vals         : NaN temizlenmiş sayısal değerler

        Döner:
            IQR tipinde Anomaly listesi (0 veya 1 eleman)
        """
        q1 = float(np.percentile(vals, 25))
        q3 = float(np.percentile(vals, 75))
        iqr = q3 - q1

        if iqr < self._eps:
            return []  # Sabit veya çok az değişken sütun

        lower_fence = q1 - self.iqr_multiplier * iqr
        upper_fence = q3 + self.iqr_multiplier * iqr

        outlier_mask = (vals < lower_fence) | (vals > upper_fence)

        if not np.any(outlier_mask):
            return []

        anomaly_rows = [valid_indices[i] for i in np.where(outlier_mask)[0]]
        outlier_vals = vals[outlier_mask]
        representative_val = float(outlier_vals[np.argmax(np.abs(outlier_vals))])

        n_outliers = len(anomaly_rows)
        outlier_ratio = n_outliers / len(vals)

        # Şiddet: orana göre
        if outlier_ratio > 0.10:
            severity = AnomalySeverity.HIGH
            confidence = 0.90
        elif outlier_ratio > 0.05:
            severity = AnomalySeverity.MEDIUM
            confidence = 0.80
        else:
            severity = AnomalySeverity.LOW
            confidence = 0.65

        return [Anomaly(
            type=AnomalyType.IQR,
            severity=severity,
            column=col,
            description=(
                f"'{col}' sütununda IQR tabanlı {n_outliers} aykırı değer tespit edildi "
                f"(%{outlier_ratio * 100:.1f} oran). "
                f"Beklenen aralık: [{lower_fence:.4f}, {upper_fence:.4f}]"
            ),
            confidence=confidence,
            row_indices=anomaly_rows,
            value=representative_val,
            expected_range=(lower_fence, upper_fence),
        )]

    # ------------------------------------------------------------------
    # 2. İş Kuralı Anomali Tespiti
    # ------------------------------------------------------------------

    def detect_business_rule(
        self,
        data: pd.DataFrame,
        schema: Optional[Dict[str, Any]] = None,
    ) -> List[Anomaly]:
        """
        Bankacılığa özgü iş kuralı ihlallerini tespit eder.

        Kontrol edilen kurallar:
            - Negatif bakiye (hesap bakiyesi >= 0)
            - Değer aralığı ihlali (işlem tutarı, faiz oranı, kredi skoru vb.)
            - Null/NaN oranı eşiği ihlali

        Parametreler:
            data  : Kontrol edilecek DataFrame
            schema: İsteğe bağlı sütun kural tanımları sözlüğü

        Döner:
            NEGATIVE_BALANCE, VALUE_RANGE ve NULL_RATIO tipinde Anomaly listesi
        """
        if schema is None:
            schema = {}

        anomalies: List[Anomaly] = []

        # Negatif bakiye kontrolü
        anomalies.extend(self._detect_negative_balance(data))

        # Değer aralığı kontrolleri
        anomalies.extend(self._detect_value_range(data, schema))

        # Null oranı kontrolü
        anomalies.extend(self._detect_null_ratio(data, schema))

        return anomalies

    def _detect_negative_balance(self, data: pd.DataFrame) -> List[Anomaly]:
        """
        Hesap bakiyesi sütunlarında negatif değerleri tespit eder.

        Bankacılık kuralı: Standart hesap bakiyeleri >= 0 olmalıdır.
        (Kredi hesapları hariç - şema ile işaretlenebilir)

        Parametreler:
            data: Kontrol edilecek DataFrame

        Döner:
            NEGATIVE_BALANCE tipinde Anomaly listesi
        """
        anomalies: List[Anomaly] = []

        # Bakiye sütunlarını bul (isme göre eşleştirme)
        for col in data.columns:
            col_lower = col.lower()
            is_balance_col = any(bc in col_lower for bc in BALANCE_COLUMNS)

            if not is_balance_col:
                continue
            if not pd.api.types.is_numeric_dtype(data[col]):
                continue

            vals = data[col].values.astype(float)
            neg_mask = vals < 0
            # NaN'ları dahil etme
            nan_mask = np.isnan(vals)
            neg_mask = neg_mask & ~nan_mask

            if not np.any(neg_mask):
                continue

            neg_rows = list(np.where(neg_mask)[0])
            neg_vals = vals[neg_mask]
            min_val = float(np.min(neg_vals))
            count = len(neg_rows)

            # Şiddet: count'a ve minimum değere göre
            if min_val < -100_000:
                severity = AnomalySeverity.CRITICAL
                confidence = 0.99
            elif min_val < -1_000 or count > 10:
                severity = AnomalySeverity.HIGH
                confidence = 0.95
            else:
                severity = AnomalySeverity.MEDIUM
                confidence = 0.85

            anomalies.append(Anomaly(
                type=AnomalyType.NEGATIVE_BALANCE,
                severity=severity,
                column=col,
                description=(
                    f"'{col}' sütununda {count} adet negatif bakiye tespit edildi. "
                    f"Minimum değer: {min_val:,.2f}. "
                    f"Bankacılık kuralı: hesap bakiyesi >= 0 olmalıdır."
                ),
                confidence=confidence,
                row_indices=neg_rows,
                value=min_val,
                expected_range=(ACCOUNT_BALANCE_MIN, ACCOUNT_BALANCE_MAX),
            ))

        return anomalies

    def _detect_value_range(
        self,
        data: pd.DataFrame,
        schema: Dict[str, Any],
    ) -> List[Anomaly]:
        """
        Değer aralığı ihlallerini tespit eder.

        Bankacılıkta bilinen sütunlar için belirlenmiş aralıkları kontrol eder.
        Şema tanımında özel aralıklar da desteklenir.

        Parametreler:
            data  : Kontrol edilecek DataFrame
            schema: Sütun kural tanımları

        Döner:
            VALUE_RANGE tipinde Anomaly listesi
        """
        anomalies: List[Anomaly] = []

        # Bilinen bankacılık sütun aralıkları
        known_ranges: Dict[str, Tuple[float, float]] = {}
        for col in data.columns:
            col_lower = col.lower()
            if any(ac in col_lower for ac in AMOUNT_COLUMNS):
                known_ranges[col] = (TRANSACTION_MIN_AMOUNT, TRANSACTION_MAX_AMOUNT)
            elif any(rc in col_lower for rc in RATE_COLUMNS):
                known_ranges[col] = (INTEREST_RATE_MIN, INTEREST_RATE_MAX)
            elif any(cc in col_lower for cc in CREDIT_SCORE_COLUMNS):
                known_ranges[col] = (float(CREDIT_SCORE_MIN), float(CREDIT_SCORE_MAX))
            elif 'yas' in col_lower or 'age' in col_lower:
                known_ranges[col] = (float(AGE_MIN), float(AGE_MAX))

        # Şemadan gelen özel aralıklar
        schema_cols = schema.get('sutunlar', schema.get('columns', {}))
        for col, col_def in schema_cols.items():
            if isinstance(col_def, dict):
                min_val = col_def.get('min', col_def.get('minimum'))
                max_val = col_def.get('max', col_def.get('maksimum'))
                if min_val is not None or max_val is not None:
                    known_ranges[col] = (
                        float(min_val) if min_val is not None else float('-inf'),
                        float(max_val) if max_val is not None else float('inf'),
                    )

        # Aralık kontrolü
        for col, (range_min, range_max) in known_ranges.items():
            if col not in data.columns:
                continue
            if not pd.api.types.is_numeric_dtype(data[col]):
                continue

            vals = data[col].values.astype(float)
            nan_mask = np.isnan(vals)
            valid_vals = vals[~nan_mask]
            valid_idx = np.where(~nan_mask)[0]

            if len(valid_vals) == 0:
                continue

            out_mask = (valid_vals < range_min) | (valid_vals > range_max)
            if not np.any(out_mask):
                continue

            out_rows = list(valid_idx[out_mask])
            out_vals = valid_vals[out_mask]
            worst_val = float(out_vals[np.argmax(
                np.maximum(range_min - out_vals, out_vals - range_max)
            )])
            count = len(out_rows)
            ratio = count / max(len(valid_vals), 1)

            if ratio > 0.10 or abs(worst_val) > abs(range_max) * 2:
                severity = AnomalySeverity.CRITICAL
                confidence = 0.97
            elif ratio > 0.05:
                severity = AnomalySeverity.HIGH
                confidence = 0.90
            else:
                severity = AnomalySeverity.MEDIUM
                confidence = 0.80

            anomalies.append(Anomaly(
                type=AnomalyType.VALUE_RANGE,
                severity=severity,
                column=col,
                description=(
                    f"'{col}' sütununda {count} değer beklenen aralığın dışında "
                    f"([{range_min:g}, {range_max:g}]). "
                    f"En aykırı değer: {worst_val:g} (%{ratio * 100:.1f} oran)"
                ),
                confidence=confidence,
                row_indices=out_rows,
                value=worst_val,
                expected_range=(range_min, range_max),
            ))

        return anomalies

    def _detect_null_ratio(
        self,
        data: pd.DataFrame,
        schema: Dict[str, Any],
    ) -> List[Anomaly]:
        """
        Sütun başına null/NaN oranını kontrol eder.

        Kabul edilebilir oranı aşan sütunlar için anomali kaydeder.
        Şemada 'zorunlu' olarak işaretlenen sütunlar için eşik 0'dır.

        Parametreler:
            data  : Kontrol edilecek DataFrame
            schema: Sütun kural tanımları

        Döner:
            NULL_RATIO tipinde Anomaly listesi
        """
        anomalies: List[Anomaly] = []

        # Zorunlu sütunları şemadan al
        schema_cols = schema.get('sutunlar', schema.get('columns', {}))
        required_cols = set()
        for col, col_def in schema_cols.items():
            if isinstance(col_def, dict):
                if col_def.get('zorunlu', col_def.get('required', False)):
                    required_cols.add(col)

        for col in data.columns:
            null_count = int(data[col].isna().sum())
            total = len(data)
            null_ratio = null_count / max(total, 1)

            is_required = col in required_cols
            threshold = 0.0 if is_required else self.null_threshold

            if null_ratio <= threshold:
                continue

            null_rows = list(data.index[data[col].isna()])

            if is_required and null_ratio > 0:
                severity = AnomalySeverity.CRITICAL
                confidence = 0.99
            elif null_ratio > 0.50:
                severity = AnomalySeverity.HIGH
                confidence = 0.95
            elif null_ratio > 0.20:
                severity = AnomalySeverity.MEDIUM
                confidence = 0.85
            else:
                severity = AnomalySeverity.LOW
                confidence = 0.70

            anomalies.append(Anomaly(
                type=AnomalyType.NULL_RATIO,
                severity=severity,
                column=col,
                description=(
                    f"'{col}' sütununda null oranı çok yüksek: "
                    f"%{null_ratio * 100:.1f} ({null_count}/{total}). "
                    f"{'Zorunlu sütun - hiç null olmamalı.' if is_required else f'Eşik: %{threshold * 100:.0f}'}"
                ),
                confidence=confidence,
                row_indices=null_rows[:100],  # İlk 100 satır
                value=null_ratio,
                expected_range=(0.0, threshold),
            ))

        return anomalies

    # ------------------------------------------------------------------
    # 3. Bütünlük Anomali Tespiti
    # ------------------------------------------------------------------

    def detect_integrity(
        self,
        data: pd.DataFrame,
        schema: Optional[Dict[str, Any]] = None,
    ) -> List[Anomaly]:
        """
        Veri bütünlüğü ihlallerini tespit eder.

        Kontrol edilen bütünlük kuralları:
            - Tarih tutarsızlıkları (gelecek tarihler, yanlış format)
            - Yabancı anahtar bütünlüğü
            - Tekrarlanan satırlar / IBAN ihlalleri

        Parametreler:
            data  : Kontrol edilecek DataFrame
            schema: İsteğe bağlı şema tanımı

        Döner:
            DATE_INCONSISTENCY, FK_INTEGRITY ve DUPLICATE tipinde Anomaly listesi
        """
        if schema is None:
            schema = {}

        anomalies: List[Anomaly] = []

        # Tarih tutarsızlıkları
        anomalies.extend(self._detect_date_inconsistency(data))

        # Yabancı anahtar bütünlüğü
        anomalies.extend(self._detect_fk_integrity(data, schema))

        # Tekrarlanan satırlar ve IBAN format kontrolü
        anomalies.extend(self._detect_duplicates(data))

        return anomalies

    def _detect_date_inconsistency(self, data: pd.DataFrame) -> List[Anomaly]:
        """
        Tarih sütunlarında tutarsızlıkları tespit eder.

        Kontroller:
            - Gelecekteki tarihler (işlem tarihleri)
            - Aşırı eski tarihler (1900 öncesi)
            - Tarih sırası tutarsızlığı (bitiş < başlangıç)
            - Geçersiz tarih formatı

        Parametreler:
            data: Kontrol edilecek DataFrame

        Döner:
            DATE_INCONSISTENCY tipinde Anomaly listesi
        """
        anomalies: List[Anomaly] = []
        now = pd.Timestamp.now()
        min_valid_date = pd.Timestamp('1900-01-01')

        for col in data.columns:
            col_lower = col.lower()
            is_date_col = (
                any(dc in col_lower for dc in DATE_COLUMNS) or
                pd.api.types.is_datetime64_any_dtype(data[col])
            )

            if not is_date_col:
                # Obje tipindeyse tarih olmaya çalış
                if data[col].dtype == object:
                    try:
                        parsed = pd.to_datetime(data[col], errors='coerce')
                        if parsed.notna().sum() > len(data) * 0.5:
                            data = data.copy()
                            data[col] = parsed
                        else:
                            continue
                    except Exception:
                        continue
                else:
                    continue

            # Datetime dönüşümü
            try:
                date_series = pd.to_datetime(data[col], errors='coerce')
            except Exception:
                continue

            valid_mask = date_series.notna()
            if valid_mask.sum() == 0:
                continue

            valid_dates = date_series[valid_mask]
            valid_idx = list(valid_dates.index)

            # 1. Gelecekteki tarihler (vade tarihi hariç)
            is_maturity = 'vade' in col_lower or 'maturity' in col_lower or 'bitis' in col_lower
            if not is_maturity:
                future_mask = valid_dates > now
                if future_mask.any():
                    future_rows = [valid_idx[i] for i, m in enumerate(future_mask) if m]
                    latest = valid_dates[future_mask].max()

                    anomalies.append(Anomaly(
                        type=AnomalyType.DATE_INCONSISTENCY,
                        severity=AnomalySeverity.HIGH,
                        column=col,
                        description=(
                            f"'{col}' sütununda {len(future_rows)} gelecek tarih tespit edildi. "
                            f"En ileri tarih: {latest.date().isoformat()}. "
                            f"İşlem tarihleri geçmişte veya bugün olmalıdır."
                        ),
                        confidence=0.95,
                        row_indices=future_rows,
                        value=latest.isoformat() if hasattr(latest, 'isoformat') else str(latest),
                        expected_range=(str(min_valid_date.date()), str(now.date())),
                    ))

            # 2. Aşırı eski tarihler
            old_mask = valid_dates < min_valid_date
            if old_mask.any():
                old_rows = [valid_idx[i] for i, m in enumerate(old_mask) if m]
                oldest = valid_dates[old_mask].min()

                anomalies.append(Anomaly(
                    type=AnomalyType.DATE_INCONSISTENCY,
                    severity=AnomalySeverity.MEDIUM,
                    column=col,
                    description=(
                        f"'{col}' sütununda {len(old_rows)} aşırı eski tarih tespit edildi. "
                        f"En eski tarih: {oldest.date().isoformat() if hasattr(oldest, 'date') else oldest}. "
                        f"1900 öncesi tarihlere şüpheyle yaklaşılmalıdır."
                    ),
                    confidence=0.85,
                    row_indices=old_rows,
                    value=oldest.isoformat() if hasattr(oldest, 'isoformat') else str(oldest),
                    expected_range=("1900-01-01", str(now.date())),
                ))

        # 3. Tarih çiftleri tutarsızlığı (başlangıç > bitiş)
        start_end_pairs = self._find_date_pairs(data)
        for start_col, end_col in start_end_pairs:
            try:
                starts = pd.to_datetime(data[start_col], errors='coerce')
                ends = pd.to_datetime(data[end_col], errors='coerce')
                valid = starts.notna() & ends.notna()
                inconsistent = valid & (starts > ends)
                if inconsistent.any():
                    incon_rows = list(data.index[inconsistent])
                    anomalies.append(Anomaly(
                        type=AnomalyType.DATE_INCONSISTENCY,
                        severity=AnomalySeverity.HIGH,
                        column=f"{start_col} -> {end_col}",
                        description=(
                            f"{len(incon_rows)} satırda başlangıç tarihi ({start_col}) "
                            f"bitiş tarihinden ({end_col}) sonra geliyor."
                        ),
                        confidence=0.99,
                        row_indices=incon_rows,
                        value=f"{start_col} > {end_col}",
                        expected_range=None,
                    ))
            except Exception:
                pass

        return anomalies

    @staticmethod
    def _find_date_pairs(data: pd.DataFrame) -> List[Tuple[str, str]]:
        """
        DataFrame'deki olası başlangıç-bitiş tarih çiftlerini bulur.

        Parametreler:
            data: DataFrame

        Döner:
            (başlangıç_sütunu, bitiş_sütunu) çiftleri listesi
        """
        pairs = []
        cols = list(data.columns)

        # Yaygın çift kalıpları
        start_keywords = ['baslangic', 'start', 'acilis', 'giris', 'from']
        end_keywords = ['bitis', 'end', 'kapanis', 'cikis', 'to', 'vade']

        for col1 in cols:
            c1 = col1.lower()
            if any(sk in c1 for sk in start_keywords):
                for col2 in cols:
                    c2 = col2.lower()
                    if any(ek in c2 for ek in end_keywords):
                        pairs.append((col1, col2))

        return pairs

    def _detect_fk_integrity(
        self,
        data: pd.DataFrame,
        schema: Dict[str, Any],
    ) -> List[Anomaly]:
        """
        Yabancı anahtar ve referans bütünlüğü ihlallerini tespit eder.

        Şemada tanımlanmış FK ilişkileri kontrol edilir.
        IBAN, TC kimlik formatları da burada doğrulanır.

        Parametreler:
            data  : Kontrol edilecek DataFrame
            schema: FK ilişkileri içeren şema tanımı

        Döner:
            FK_INTEGRITY tipinde Anomaly listesi
        """
        anomalies: List[Anomaly] = []

        # 1. Şemadan FK ilişkileri
        fk_relations = schema.get('yabanci_anahtarlar', schema.get('foreign_keys', {}))
        for fk_col, ref_info in fk_relations.items():
            if fk_col not in data.columns:
                continue

            if isinstance(ref_info, dict):
                ref_col = ref_info.get('referans_sutun', ref_info.get('reference_column'))
                ref_values = ref_info.get('degerler', ref_info.get('values', []))
            elif isinstance(ref_info, list):
                ref_col = None
                ref_values = ref_info
            else:
                continue

            fk_vals = data[fk_col].dropna()

            if ref_col and ref_col in data.columns:
                # Aynı DataFrame içinde FK kontrolü
                valid_vals = set(data[ref_col].dropna().unique())
            elif ref_values:
                valid_vals = set(ref_values)
            else:
                continue

            invalid_mask = ~fk_vals.isin(valid_vals)
            if not invalid_mask.any():
                continue

            invalid_rows = list(fk_vals.index[invalid_mask])
            sample_invalid = list(fk_vals[invalid_mask].unique()[:5])

            anomalies.append(Anomaly(
                type=AnomalyType.FK_INTEGRITY,
                severity=AnomalySeverity.CRITICAL,
                column=fk_col,
                description=(
                    f"'{fk_col}' sütununda {len(invalid_rows)} yabancı anahtar ihlali. "
                    f"Geçersiz değerler: {sample_invalid}. "
                    f"Referans: {'sütun ' + ref_col if ref_col else 'izin verilen değerler listesi'}"
                ),
                confidence=0.99,
                row_indices=invalid_rows,
                value=sample_invalid[0] if sample_invalid else None,
                expected_range=None,
            ))

        # 2. IBAN format kontrolü
        for col in data.columns:
            col_lower = col.lower()
            if any(ic in col_lower for ic in IBAN_COLUMNS):
                if data[col].dtype != object:
                    continue
                iban_vals = data[col].dropna().astype(str)
                invalid_iban_mask = ~iban_vals.str.match(IBAN_PATTERN)
                if invalid_iban_mask.any():
                    invalid_rows = list(iban_vals.index[invalid_iban_mask])
                    sample = list(iban_vals[invalid_iban_mask].head(3))

                    anomalies.append(Anomaly(
                        type=AnomalyType.FK_INTEGRITY,
                        severity=AnomalySeverity.HIGH,
                        column=col,
                        description=(
                            f"'{col}' sütununda {len(invalid_rows)} geçersiz IBAN formatı. "
                            f"Beklenen format: TR + 24 rakam (toplam 26 karakter). "
                            f"Örnek geçersiz: {sample}"
                        ),
                        confidence=0.95,
                        row_indices=invalid_rows,
                        value=sample[0] if sample else None,
                        expected_range=None,
                    ))

        # 3. TC Kimlik No format kontrolü
        for col in data.columns:
            col_lower = col.lower()
            if 'tc' in col_lower and ('kimlik' in col_lower or 'id' in col_lower or 'no' in col_lower):
                if data[col].dtype not in [object, str]:
                    continue
                tc_vals = data[col].dropna().astype(str)
                # TC kimlik: 11 basamak, ilk basamak 0 olamaz
                invalid_tc_mask = ~tc_vals.str.match(r'^[1-9]\d{10}$')
                if invalid_tc_mask.any():
                    invalid_rows = list(tc_vals.index[invalid_tc_mask])
                    anomalies.append(Anomaly(
                        type=AnomalyType.FK_INTEGRITY,
                        severity=AnomalySeverity.HIGH,
                        column=col,
                        description=(
                            f"'{col}' sütununda {len(invalid_rows)} geçersiz TC Kimlik No formatı. "
                            f"Beklenen: 11 basamak, ilk basamak 1-9."
                        ),
                        confidence=0.90,
                        row_indices=invalid_rows,
                        value=len(invalid_rows),
                        expected_range=None,
                    ))

        return anomalies

    def _detect_duplicates(self, data: pd.DataFrame) -> List[Anomaly]:
        """
        Tekrarlanan satırları ve kritik alan değerlerini tespit eder.

        Parametreler:
            data: Kontrol edilecek DataFrame

        Döner:
            DUPLICATE tipinde Anomaly listesi
        """
        anomalies: List[Anomaly] = []

        # 1. Tam satır tekrarları
        dup_mask = data.duplicated(keep='first')
        if dup_mask.any():
            dup_rows = list(data.index[dup_mask])
            dup_count = len(dup_rows)
            dup_ratio = dup_count / max(len(data), 1)

            severity = AnomalySeverity.HIGH if dup_ratio > 0.05 else AnomalySeverity.MEDIUM
            anomalies.append(Anomaly(
                type=AnomalyType.DUPLICATE,
                severity=severity,
                column="[tüm_satırlar]",
                description=(
                    f"{dup_count} adet tam kopya satır tespit edildi "
                    f"(%{dup_ratio * 100:.2f} oran). "
                    f"Sentetik veri üretiminde tekrar güdülemesi hatası."
                ),
                confidence=1.0,
                row_indices=dup_rows,
                value=dup_count,
                expected_range=(0, 0),
            ))

        # 2. Benzersiz olması gereken ID sütunlarında tekrar
        for col in data.columns:
            col_lower = col.lower()
            is_id_col = any(ic == col_lower or col_lower.endswith('_' + ic) or col_lower.startswith(ic + '_')
                           for ic in ['id', 'kimlik', 'no', 'number', 'numara'])

            if not is_id_col:
                continue

            non_null = data[col].dropna()
            if len(non_null) == 0:
                continue

            dup_id_mask = non_null.duplicated(keep='first')
            if not dup_id_mask.any():
                continue

            dup_id_rows = list(non_null.index[dup_id_mask])
            dup_vals = non_null[dup_id_mask].unique()[:5]

            anomalies.append(Anomaly(
                type=AnomalyType.DUPLICATE,
                severity=AnomalySeverity.CRITICAL,
                column=col,
                description=(
                    f"'{col}' benzersiz kimlik sütununda {len(dup_id_rows)} tekrar tespit edildi. "
                    f"Örnek tekrarlı değerler: {list(dup_vals)}. "
                    f"ID sütunları benzersiz olmalıdır."
                ),
                confidence=1.0,
                row_indices=dup_id_rows,
                value=str(dup_vals[0]) if len(dup_vals) > 0 else None,
                expected_range=None,
            ))

        return anomalies

    # ------------------------------------------------------------------
    # 4. Dağılım Anomali Tespiti
    # ------------------------------------------------------------------

    def detect_distribution(
        self,
        real_data: pd.DataFrame,
        synthetic_data: pd.DataFrame,
        threshold: float = 0.05,
    ) -> List[Anomaly]:
        """
        Gerçek ve sentetik veri arasındaki dağılım farklarını tespit eder.

        Her sayısal sütun için KS-tabanlı bir karşılaştırma yapar.
        Anlamlı dağılım kayması olan sütunlar için anomali kaydeder.

        Parametreler:
            real_data     : Gerçek veri DataFrame'i
            synthetic_data: Sentetik veri DataFrame'i
            threshold     : Anlamlılık eşiği (p < threshold = anomali)

        Döner:
            DISTRIBUTION tipinde Anomaly listesi
        """
        anomalies: List[Anomaly] = []

        common_cols = [
            c for c in real_data.columns
            if c in synthetic_data.columns and pd.api.types.is_numeric_dtype(real_data[c])
        ]

        for col in common_cols:
            real_vals = real_data[col].dropna().values.astype(float)
            syn_vals = synthetic_data[col].dropna().values.astype(float)

            if len(real_vals) < 5 or len(syn_vals) < 5:
                continue

            # KS istatistiği hesapla
            ks_stat, p_value = self._ks_two_sample(real_vals, syn_vals)

            # Ortalama ve std farkları
            mean_diff = abs(np.mean(real_vals) - np.mean(syn_vals))
            std_diff = abs(np.std(real_vals) - np.std(syn_vals))

            if p_value >= threshold:
                continue  # Dağılımlar benzer

            # Şiddet: KS istatistiğine göre
            if ks_stat > 0.5:
                severity = AnomalySeverity.CRITICAL
                confidence = 0.97
            elif ks_stat > 0.3:
                severity = AnomalySeverity.HIGH
                confidence = 0.90
            elif ks_stat > 0.15:
                severity = AnomalySeverity.MEDIUM
                confidence = 0.80
            else:
                severity = AnomalySeverity.LOW
                confidence = 0.70

            # Etkilenen satır indeksleri yaklaşımı: üst/alt %10'luk sapma gösterenler
            syn_mean = np.mean(syn_vals)
            real_mean = np.mean(real_vals)
            deviation = syn_vals - real_mean
            threshold_dev = 2.0 * np.std(real_vals)
            affected_mask = np.abs(deviation) > threshold_dev
            affected_rows = list(synthetic_data[col].dropna().index[affected_mask])

            anomalies.append(Anomaly(
                type=AnomalyType.DISTRIBUTION,
                severity=severity,
                column=col,
                description=(
                    f"'{col}' sütununda dağılım kayması tespit edildi. "
                    f"KS istatistiği: {ks_stat:.4f}, p-değeri: {p_value:.4f}. "
                    f"Gerçek ortalama: {real_mean:.4f}, "
                    f"Sentetik ortalama: {syn_mean:.4f}, "
                    f"Fark: {mean_diff:.4f}"
                ),
                confidence=confidence,
                row_indices=affected_rows[:100],
                value=float(ks_stat),
                expected_range=(float(np.min(real_vals)), float(np.max(real_vals))),
            ))

        return anomalies

    @staticmethod
    def _ks_two_sample(
        x: np.ndarray,
        y: np.ndarray,
    ) -> Tuple[float, float]:
        """
        İki örnek arasında saf NumPy KS testi.

        Parametreler:
            x: Birinci örnek
            y: İkinci örnek

        Döner:
            (ks_istatistigi, p_degeri) demeti
        """
        all_vals = np.sort(np.concatenate([x, y]))
        n1, n2 = len(x), len(y)

        ecdf1 = np.searchsorted(np.sort(x), all_vals, side='right') / n1
        ecdf2 = np.searchsorted(np.sort(y), all_vals, side='right') / n2

        ks_stat = float(np.max(np.abs(ecdf1 - ecdf2)))

        # Asimptotik p-değeri
        n = float(n1 * n2) / (n1 + n2)
        z = ks_stat * np.sqrt(n)

        if z < 0.27:
            p_value = 1.0
        else:
            # Serisi: 2 * sum_{k=1}^{inf} (-1)^{k-1} * exp(-2k^2 * z^2)
            p_value = float(
                2.0 * sum(
                    ((-1) ** (k - 1)) * np.exp(-2 * k ** 2 * z ** 2)
                    for k in range(1, 20)
                )
            )

        return ks_stat, float(np.clip(p_value, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Rapor Üretimi
    # ------------------------------------------------------------------

    def generate_report(self, anomalies: List[Anomaly]) -> Dict[str, Any]:
        """
        Anomali listesinden kapsamlı bir rapor oluşturur.

        Rapor şunları içerir:
            - Özet istatistikler (toplam, şiddet dağılımı, tür dağılımı)
            - Her anomalinin detayları
            - En kritik sorunlar
            - Öneriler

        Parametreler:
            anomalies: Anomaly nesnelerinin listesi

        Döner:
            JSON serileştirilebilir rapor sözlüğü
        """
        if not anomalies:
            return {
                "rapor_tarihi": datetime.now().isoformat(),
                "ozet": {
                    "toplam_anomali": 0,
                    "durum": "Anomali tespit edilmedi",
                },
                "anomaliler": [],
                "oneriler": ["Veri kalitesi kabul edilebilir düzeyde görünüyor."],
            }

        # Şiddet dağılımı
        severity_count: Dict[str, int] = defaultdict(int)
        for a in anomalies:
            severity_count[a.severity.value] += 1

        # Tür dağılımı
        type_count: Dict[str, int] = defaultdict(int)
        for a in anomalies:
            type_count[a.type.value] += 1

        # Etkilenen toplam benzersiz satır
        all_affected_rows: set = set()
        for a in anomalies:
            all_affected_rows.update(a.row_indices)

        # En kritik anomaliler
        critical_anomalies = [a for a in anomalies if a.severity == AnomalySeverity.CRITICAL]
        high_anomalies = [a for a in anomalies if a.severity == AnomalySeverity.HIGH]

        # Öneriler
        recommendations = self._generate_recommendations(anomalies, severity_count, type_count)

        # Anomali detayları
        anomaly_details = [a.to_dict() for a in anomalies]

        # Genel kalite puanı (0-100)
        quality_score = self._calculate_quality_score(anomalies, severity_count)

        return {
            "rapor_tarihi": datetime.now().isoformat(),
            "ozet": {
                "toplam_anomali": len(anomalies),
                "etkilenen_satir_sayisi": len(all_affected_rows),
                "kalite_puani": round(quality_score, 2),
                "durum": self._get_status(quality_score),
                "siddet_dagilimi": dict(severity_count),
                "tur_dagilimi": dict(type_count),
                "kritik_anomali_sayisi": len(critical_anomalies),
                "yuksek_anomali_sayisi": len(high_anomalies),
            },
            "kritik_anomaliler": [a.to_dict() for a in critical_anomalies[:10]],
            "anomaliler": anomaly_details,
            "oneriler": recommendations,
        }

    @staticmethod
    def _calculate_quality_score(
        anomalies: List[Anomaly],
        severity_count: Dict[str, int],
    ) -> float:
        """
        Anomali listesinden genel kalite puanı (0-100) hesaplar.

        Parametreler:
            anomalies     : Anomali listesi
            severity_count: Şiddet bazında anomali sayıları

        Döner:
            Kalite puanı [0.0, 100.0]
        """
        if not anomalies:
            return 100.0

        # Ağırlıklı puan düşümü
        weight_map = {
            "critical": 15.0,
            "high": 8.0,
            "medium": 3.0,
            "low": 1.0,
        }

        penalty = 0.0
        for sev, count in severity_count.items():
            weight = weight_map.get(sev, 1.0)
            # Logaritmik ceza: ilk birkaç anomali daha çok etkiler
            penalty += weight * np.log1p(count)

        score = max(0.0, 100.0 - penalty)
        return float(score)

    @staticmethod
    def _get_status(quality_score: float) -> str:
        """Kalite puanından durum etiketi üretir."""
        if quality_score >= 90:
            return "Mükemmel"
        elif quality_score >= 75:
            return "İyi"
        elif quality_score >= 50:
            return "Orta"
        elif quality_score >= 25:
            return "Zayıf"
        else:
            return "Kritik"

    @staticmethod
    def _generate_recommendations(
        anomalies: List[Anomaly],
        severity_count: Dict[str, int],
        type_count: Dict[str, int],
    ) -> List[str]:
        """
        Anomali türlerine ve şiddetine göre öneriler oluşturur.

        Parametreler:
            anomalies     : Anomali listesi
            severity_count: Şiddet bazında sayılar
            type_count    : Tür bazında sayılar

        Döner:
            Türkçe öneri metinleri listesi
        """
        recommendations: List[str] = []

        critical = severity_count.get('critical', 0)
        high = severity_count.get('high', 0)

        if critical > 0:
            recommendations.append(
                f"KRİTİK: {critical} kritik anomali tespit edildi. "
                f"Veri yayınlanmadan önce acil müdahale gereklidir."
            )

        if type_count.get('negative_balance', 0) > 0:
            recommendations.append(
                "Negatif bakiye değerleri bulunuyor. Bankacılık kurallarına göre "
                "standart hesap bakiyeleri sıfırın altına düşmemelidir. "
                "Veri üretim kısıtlarını güncelleyin."
            )

        if type_count.get('duplicate', 0) > 0:
            recommendations.append(
                "Tekrarlanan kayıtlar tespit edildi. Sentetik veri üreticisinin "
                "benzersizlik kısıtlamasını etkinleştirin veya artırın."
            )

        if type_count.get('date_inconsistency', 0) > 0:
            recommendations.append(
                "Tarih tutarsızlıkları mevcut. Gelecek tarih kısıtlamasını ve "
                "tarih aralığı doğrulamasını veri üretim kurallarına ekleyin."
            )

        if type_count.get('null_ratio', 0) > 0:
            recommendations.append(
                "Yüksek null oranları bulunuyor. Zorunlu sütunlar için null "
                "üretimini devre dışı bırakın ve eksik veri stratejisini gözden geçirin."
            )

        if type_count.get('fk_integrity', 0) > 0:
            recommendations.append(
                "Yabancı anahtar veya format ihlalleri tespit edildi. "
                "IBAN, TC kimlik ve referans değerleri için format doğrulama "
                "kuralları ekleyin."
            )

        if type_count.get('distribution', 0) > 0:
            recommendations.append(
                "Dağılım kaymaları tespit edildi. GAN modelini daha fazla epokla "
                "yeniden eğitin veya daha büyük gerçek veri kümesi kullanın."
            )

        if type_count.get('value_range', 0) > 0:
            recommendations.append(
                "Değer aralığı ihlalleri var. Veri üreticisine min/max kısıtları "
                "ekleyin. İşlem tutarı, faiz oranı ve kredi skoru aralıklarını doğrulayın."
            )

        if not recommendations:
            recommendations.append(
                "Tespit edilen anomaliler düşük şiddette. "
                "Düzenli izlemeye devam edin ve sonraki üretimde kontrol edin."
            )

        return recommendations

    # ------------------------------------------------------------------
    # Toplu İşlem (Batch) Desteği
    # ------------------------------------------------------------------

    def batch_detect(
        self,
        datasets: List[pd.DataFrame],
        schema: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Birden fazla veri kümesinde toplu anomali tespiti yapar.

        Her veri kümesi için ayrı bir rapor oluşturur ve döner.
        Bellek verimliliği için her veri kümesi bağımsız işlenir.

        Parametreler:
            datasets: DataFrame listesi
            schema  : İsteğe bağlı şema tanımı (tüm veri kümelerine uygulanır)

        Döner:
            Her veri kümesi için rapor sözlüğü içeren liste

        Örnek:
            >>> reports = detector.batch_detect([df1, df2, df3], schema)
            >>> for i, report in enumerate(reports):
            ...     print(f"Veri Kümesi {i+1}: {report['ozet']['kalite_puani']}")
        """
        if schema is None:
            schema = {}

        results: List[Dict[str, Any]] = []

        for idx, dataset in enumerate(datasets):
            logger.info(
                f"Batch tespit: {idx + 1}/{len(datasets)} veri kümesi işleniyor "
                f"({len(dataset)} satır)"
            )

            try:
                anomalies = self.detect_all(dataset, schema)
                report = self.generate_report(anomalies)
                report['veri_kumesi_no'] = idx
                report['satir_sayisi'] = len(dataset)
                report['sutun_sayisi'] = len(dataset.columns)
                results.append(report)
            except Exception as e:
                logger.error(f"Veri kümesi {idx + 1} işlenirken hata: {e}")
                results.append({
                    'veri_kumesi_no': idx,
                    'hata': str(e),
                    'ozet': {
                        'durum': 'İşleme Hatası',
                        'kalite_puani': 0.0,
                    },
                    'anomaliler': [],
                    'oneriler': [f"Veri kümesi işlenirken hata oluştu: {e}"],
                })

        # Batch özeti
        logger.info(
            f"Batch tespit tamamlandı: {len(datasets)} veri kümesi işlendi. "
            f"Ortalama kalite: {np.mean([r.get('ozet', {}).get('kalite_puani', 0) for r in results]):.2f}"
        )

        return results

    # ------------------------------------------------------------------
    # Yardımcı Metotlar
    # ------------------------------------------------------------------

    def get_summary_stats(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        DataFrame için temel istatistikleri hesaplar.

        Parametreler:
            data: İstatistikleri hesaplanacak DataFrame

        Döner:
            Sütun başına temel istatistikler sözlüğü
        """
        stats = {}
        for col in data.columns:
            col_stats: Dict[str, Any] = {
                "dtype": str(data[col].dtype),
                "null_count": int(data[col].isna().sum()),
                "null_ratio": float(data[col].isna().mean()),
                "unique_count": int(data[col].nunique()),
            }

            if pd.api.types.is_numeric_dtype(data[col]):
                vals = data[col].dropna().values.astype(float)
                if len(vals) > 0:
                    col_stats.update({
                        "mean": float(np.mean(vals)),
                        "std": float(np.std(vals)),
                        "min": float(np.min(vals)),
                        "max": float(np.max(vals)),
                        "q25": float(np.percentile(vals, 25)),
                        "median": float(np.median(vals)),
                        "q75": float(np.percentile(vals, 75)),
                    })

            stats[col] = col_stats

        return stats

    def compare_schemas(
        self,
        real_data: pd.DataFrame,
        synthetic_data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Gerçek ve sentetik veri şemalarını karşılaştırır.

        Parametreler:
            real_data     : Gerçek veri
            synthetic_data: Sentetik veri

        Döner:
            Şema uyumsuzlukları sözlüğü
        """
        issues = []

        real_cols = set(real_data.columns)
        syn_cols = set(synthetic_data.columns)

        # Eksik sütunlar
        missing_in_syn = real_cols - syn_cols
        extra_in_syn = syn_cols - real_cols

        if missing_in_syn:
            issues.append({
                "tur": "eksik_sutun",
                "sutunlar": list(missing_in_syn),
                "aciklama": f"Sentetik veride eksik sütunlar: {missing_in_syn}"
            })

        if extra_in_syn:
            issues.append({
                "tur": "fazla_sutun",
                "sutunlar": list(extra_in_syn),
                "aciklama": f"Sentetik veride fazladan sütunlar: {extra_in_syn}"
            })

        # Tür uyumsuzlukları
        for col in real_cols & syn_cols:
            real_type = real_data[col].dtype
            syn_type = synthetic_data[col].dtype
            if str(real_type) != str(syn_type):
                # Sayısal uyumluluk kontrolü
                both_numeric = (
                    pd.api.types.is_numeric_dtype(real_type) and
                    pd.api.types.is_numeric_dtype(syn_type)
                )
                if not both_numeric:
                    issues.append({
                        "tur": "tur_uyumsuzlugu",
                        "sutun": col,
                        "gercek_tur": str(real_type),
                        "sentetik_tur": str(syn_type),
                        "aciklama": (
                            f"'{col}': gerçek={real_type}, sentetik={syn_type}"
                        )
                    })

        return {
            "toplam_sorun": len(issues),
            "sorunlar": issues,
            "gercek_sutun_sayisi": len(real_cols),
            "sentetik_sutun_sayisi": len(syn_cols),
            "ortak_sutun_sayisi": len(real_cols & syn_cols),
        }

    def __repr__(self) -> str:
        return (
            f"AnomalyDetector("
            f"z_threshold={self.z_score_threshold}, "
            f"iqr={self.iqr_multiplier}, "
            f"null_thr={self.null_threshold}, "
            f"strict={self.strict_mode})"
        )


# ===========================================================================
# Modül Düzeyinde Yardımcı Fonksiyonlar
# ===========================================================================

def quick_anomaly_check(
    data: pd.DataFrame,
    schema: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tek satırlık hızlı anomali kontrolü.

    Parametreler:
        data  : Kontrol edilecek DataFrame
        schema: İsteğe bağlı şema tanımı

    Döner:
        Anomali raporu sözlüğü
    """
    detector = AnomalyDetector()
    anomalies = detector.detect_all(data, schema or {})
    return detector.generate_report(anomalies)


def get_anomaly_summary(anomalies: List[Anomaly]) -> str:
    """
    Anomali listesinden kısa Türkçe özet metin üretir.

    Parametreler:
        anomalies: Anomaly nesneleri listesi

    Döner:
        Kısa özet metin
    """
    if not anomalies:
        return "Anomali tespit edilmedi. Veri kalitesi iyi görünüyor."

    critical = sum(1 for a in anomalies if a.severity == AnomalySeverity.CRITICAL)
    high = sum(1 for a in anomalies if a.severity == AnomalySeverity.HIGH)
    medium = sum(1 for a in anomalies if a.severity == AnomalySeverity.MEDIUM)
    low = sum(1 for a in anomalies if a.severity == AnomalySeverity.LOW)

    lines = [
        f"Toplam {len(anomalies)} anomali tespit edildi:",
        f"  Kritik : {critical}",
        f"  Yüksek : {high}",
        f"  Orta   : {medium}",
        f"  Düşük  : {low}",
    ]

    if critical > 0:
        lines.append("UYARI: Acil müdahale gerektiren kritik sorunlar mevcut!")

    return "\n".join(lines)


def filter_anomalies(
    anomalies: List[Anomaly],
    min_severity: AnomalySeverity = AnomalySeverity.MEDIUM,
    anomaly_types: Optional[List[AnomalyType]] = None,
    min_confidence: float = 0.0,
) -> List[Anomaly]:
    """
    Anomali listesini filtreler.

    Parametreler:
        anomalies    : Filtrelenecek anomali listesi
        min_severity : Minimum şiddet seviyesi
        anomaly_types: Dahil edilecek anomali türleri (None = hepsi)
        min_confidence: Minimum güven skoru

    Döner:
        Filtrelenmiş Anomaly listesi
    """
    severity_order = {
        AnomalySeverity.LOW: 0,
        AnomalySeverity.MEDIUM: 1,
        AnomalySeverity.HIGH: 2,
        AnomalySeverity.CRITICAL: 3,
    }
    min_sev_val = severity_order.get(min_severity, 0)

    filtered = [
        a for a in anomalies
        if (
            severity_order.get(a.severity, 0) >= min_sev_val and
            a.confidence >= min_confidence and
            (anomaly_types is None or a.type in anomaly_types)
        )
    ]

    return filtered


def anomalies_to_json(anomalies: List[Anomaly], indent: int = 2) -> str:
    """
    Anomali listesini JSON dizgisine dönüştürür.

    Parametreler:
        anomalies: Anomaly nesneleri listesi
        indent   : JSON girintisi

    Döner:
        JSON biçimli dizgi
    """
    return json.dumps(
        [a.to_dict() for a in anomalies],
        indent=indent,
        ensure_ascii=False,
        default=str,
    )
