"""
Şema Analiz Servisi — Kapsamlı SchemaAnalyzer Modülü.

Yüklenen dosyaları (CSV, Excel, JSON) okuyup her kolon için veri tipi tespiti,
istatistiksel profil çıkarma, pattern tanıma ve dağılım analizi yapar.
Bankacılık domainine özel pattern'lar (TCKN, IBAN, telefon, hesap no vb.)
otomatik olarak tespit edilir.

Desteklenen dosya formatları:
  - CSV  (encoding tespiti ile — chardet)
  - XLSX / XLS (openpyxl)
  - JSON (nested yapı düzleştirme destekli)
"""

from __future__ import annotations

import io
import json
import logging
import math
import os
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from app.config import settings
from app.utils.helpers import (
    detect_currency,
    detect_date_format,
    flatten_json,
    format_file_size,
    is_account_number_pattern,
    is_credit_card_pattern,
    is_customer_number_pattern,
    is_email_pattern,
    is_iban_pattern,
    is_phone_pattern,
    is_tckn_pattern,
    is_url_pattern,
    normalize_column_name,
    safe_float,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Sonuç Dataclass'ları
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ColumnAnalysis:
    """
    Tek bir kolon için analiz sonucu.

    SchemaAnalyzer tarafından üretilir, ColumnProfile ORM modeline
    dönüştürülebilir yapıdadır.
    """

    # Temel bilgiler
    name: str
    original_name: str  # Normalleştirme öncesi orijinal isim
    data_type: str  # string, integer, float, decimal, date, datetime, boolean
    semantic_type: Optional[str] = None  # email, iban, tckn, phone, url, currency, account_no, customer_no, credit_card

    # Null ve benzersizlik istatistikleri
    total_count: int = 0
    null_count: int = 0
    null_ratio: float = 0.0
    distinct_count: int = 0
    distinct_ratio: float = 0.0

    # Sayısal istatistikler
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    std_value: Optional[float] = None

    # String istatistikleri
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    avg_length: Optional[float] = None

    # Pattern bilgisi
    pattern: Optional[str] = None  # Tespit edilen regex deseni
    detected_patterns: dict[str, float] = field(default_factory=dict)  # pattern → oran

    # Örnek ve yaygın değerler
    sample_values: list[Any] = field(default_factory=list)  # 5 adet örnek
    most_common_values: list[dict[str, Any]] = field(default_factory=list)  # Top 10 {value, count, ratio}

    # Dağılım bilgileri
    distribution: Optional[dict[str, Any]] = None  # histogram veya frekans

    # PII tespiti
    is_pii: bool = False
    pii_level: str = "none"  # none, low, medium, high, critical

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict'e dönüştürür."""
        result = asdict(self)
        # NaN ve Inf değerleri None'a çevir (JSON uyumluluk)
        return _sanitize_for_json(result)

    def to_column_profile_dict(self) -> dict[str, Any]:
        """
        ColumnProfile ORM modeline uyumlu dict döndürür.
        DB'ye kaydetme işlemi için kullanılır.
        """
        return {
            "name": self.name,
            "data_type": self.data_type,
            "semantic_type": self.semantic_type,
            "is_pii": self.is_pii,
            "pii_level": self.pii_level,
            "null_ratio": self.null_ratio,
            "distinct_ratio": self.distinct_ratio,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "mean_value": self.mean_value,
            "pattern": self.pattern,
            "sample_values": {"values": self.sample_values},
            "statistics": _sanitize_for_json({
                "total_count": self.total_count,
                "null_count": self.null_count,
                "distinct_count": self.distinct_count,
                "median": self.median_value,
                "std": self.std_value,
                "min_length": self.min_length,
                "max_length": self.max_length,
                "avg_length": self.avg_length,
                "most_common": self.most_common_values,
                "distribution": self.distribution,
                "detected_patterns": self.detected_patterns,
            }),
        }


@dataclass
class AnalysisResult:
    """
    Dosya analiz sonucunun tamamı.

    Tüm kolon analizlerini, dosya meta bilgilerini ve özet istatistikleri içerir.
    """

    # Dosya meta bilgileri
    file_name: str
    file_type: str  # csv, xlsx, json
    file_size: int  # byte
    file_size_human: str  # ör. "14.5 MB"
    row_count: int
    column_count: int

    # Kolon analizleri
    columns: list[ColumnAnalysis] = field(default_factory=list)

    # Özet istatistikler
    pii_columns: list[str] = field(default_factory=list)
    date_columns: list[str] = field(default_factory=list)
    numeric_columns: list[str] = field(default_factory=list)
    categorical_columns: list[str] = field(default_factory=list)

    # Analiz meta bilgileri
    analysis_duration_ms: float = 0.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict'e dönüştürür."""
        return _sanitize_for_json(asdict(self))

    def get_column(self, name: str) -> Optional[ColumnAnalysis]:
        """İsme göre kolon analizi döndürür."""
        for col in self.columns:
            if col.name == name or col.original_name == name:
                return col
        return None


# ═══════════════════════════════════════════════════════════════════════
# SchemaAnalyzer Ana Sınıfı
# ═══════════════════════════════════════════════════════════════════════


class SchemaAnalyzer:
    """
    Veritabanı şemasını analiz eden ana sınıf.

    Dosya okuma, kolon analizi, pattern tespiti ve dağılım analizi
    işlemlerini koordine eder. ColumnProfile ORM modeli ile uyumlu
    sonuçlar üretir.

    Kullanım:
        analyzer = SchemaAnalyzer()
        result = analyzer.analyze_file("/path/to/data.csv")
        # veya
        result = analyzer.analyze_dataframe(df, "data.csv")

    Attributes:
        max_file_size: Maksimum dosya boyutu (byte)
        max_rows: Analiz için maksimum satır sayısı (örnekleme yapılır)
        sample_size: Pattern tespiti için örneklem boyutu
        chunk_size: Büyük dosyalar için chunk okuma boyutu
    """

    def __init__(
        self,
        max_file_size: Optional[int] = None,
        max_rows: int = 100_000,
        sample_size: int = 1_000,
        chunk_size: int = 10_000,
    ) -> None:
        """
        SchemaAnalyzer başlatıcı.

        Args:
            max_file_size: Maksimum dosya boyutu (byte). None ise config'den alınır.
            max_rows: Analiz için maksimum satır sayısı
            sample_size: Pattern tespiti örneklem boyutu
            chunk_size: Büyük CSV dosyaları için chunk boyutu
        """
        self.max_file_size = max_file_size or settings.MAX_UPLOAD_SIZE
        self.max_rows = max_rows
        self.sample_size = sample_size
        self.chunk_size = chunk_size

        # Pattern tespit fonksiyonları — (fonksiyon, semantik_tip, pii_seviyesi) üçlüleri
        self._pattern_detectors: list[tuple[callable, str, str]] = [
            (is_tckn_pattern, "tckn", "critical"),
            (is_iban_pattern, "iban", "high"),
            (is_credit_card_pattern, "credit_card", "critical"),
            (is_email_pattern, "email", "medium"),
            (is_phone_pattern, "phone", "medium"),
            (is_url_pattern, "url", "low"),
            (is_account_number_pattern, "account_number", "high"),
            (is_customer_number_pattern, "customer_number", "medium"),
        ]

    # ─── Ana Analiz Metotları ──────────────────────────────────────

    def analyze_file(self, file_path: str) -> AnalysisResult:
        """
        Dosyayı okuyup tam analiz yapar.

        Dosya tipine göre uygun okuyucu seçilir (CSV, Excel, JSON).
        Büyük dosyalar chunk'lar halinde okunur.

        Args:
            file_path: Analiz edilecek dosya yolu

        Returns:
            AnalysisResult — tüm kolon analizlerini içeren sonuç

        Raises:
            FileNotFoundError: Dosya bulunamazsa
            ValueError: Desteklenmeyen format veya boyut aşımı
            RuntimeError: Dosya okunamadığında
        """
        start_time = datetime.now()
        path = Path(file_path)

        # ── Dosya varlık kontrolü ──
        if not path.exists():
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

        # ── Boyut kontrolü ──
        file_size = path.stat().st_size
        if file_size > self.max_file_size:
            raise ValueError(
                f"Dosya boyutu ({format_file_size(file_size)}) izin verilen "
                f"maksimumu ({format_file_size(self.max_file_size)}) aşıyor."
            )

        if file_size == 0:
            raise ValueError("Dosya boş (0 byte).")

        # ── Uzantı tespiti ──
        suffix = path.suffix.lower()
        file_type_map = {
            ".csv": "csv",
            ".xlsx": "xlsx",
            ".xls": "xls",
            ".json": "json",
            ".tsv": "csv",  # TSV de CSV okuyucu ile okunur
        }

        file_type = file_type_map.get(suffix)
        if not file_type:
            raise ValueError(
                f"Desteklenmeyen dosya formatı: '{suffix}'. "
                f"Desteklenen: {', '.join(file_type_map.keys())}"
            )

        # ── Dosya okuma ──
        logger.info("Dosya okunuyor: %s (%s)", path.name, format_file_size(file_size))

        try:
            if file_type == "csv":
                df = self._read_csv(file_path, separator="\t" if suffix == ".tsv" else None)
            elif file_type in ("xlsx", "xls"):
                df = self._read_excel(file_path)
            elif file_type == "json":
                df = self._read_json(file_path)
            else:
                raise ValueError(f"Bilinmeyen dosya tipi: {file_type}")
        except (ValueError, FileNotFoundError):
            raise
        except Exception as exc:
            raise RuntimeError(f"Dosya okunurken hata oluştu: {exc}") from exc

        # ── Satır sayısı kontrolü ve örnekleme ──
        warnings: list[str] = []
        total_rows = len(df)
        if total_rows > self.max_rows:
            warnings.append(
                f"Dosya {total_rows:,} satır içeriyor. Analiz için {self.max_rows:,} "
                f"satırlık rastgele örneklem kullanılıyor."
            )
            df = df.sample(n=self.max_rows, random_state=42).reset_index(drop=True)

        # ── Analiz yap ──
        result = self.analyze_dataframe(df, path.name)
        result.file_type = file_type
        result.file_size = file_size
        result.file_size_human = format_file_size(file_size)
        result.row_count = total_rows  # Orijinal satır sayısı
        result.warnings.extend(warnings)

        # Süre hesapla
        duration = (datetime.now() - start_time).total_seconds() * 1000
        result.analysis_duration_ms = round(duration, 2)

        logger.info(
            "Analiz tamamlandı: %s — %d kolon, %d satır, %.0f ms",
            path.name, result.column_count, total_rows, duration,
        )

        return result

    def analyze_dataframe(
        self,
        df: pd.DataFrame,
        source_name: str = "dataframe",
    ) -> AnalysisResult:
        """
        Pandas DataFrame üzerinde tam analiz yapar.

        Args:
            df: Analiz edilecek DataFrame
            source_name: Kaynak adı (loglama ve sonuç için)

        Returns:
            AnalysisResult — tüm kolon analizlerini içeren sonuç
        """
        start_time = datetime.now()

        columns: list[ColumnAnalysis] = []
        pii_cols: list[str] = []
        date_cols: list[str] = []
        numeric_cols: list[str] = []
        categorical_cols: list[str] = []

        for col_name in df.columns:
            try:
                analysis = self._analyze_column(df[col_name], str(col_name))
                columns.append(analysis)

                # Kategorize et
                if analysis.is_pii:
                    pii_cols.append(analysis.name)
                if analysis.data_type in ("date", "datetime"):
                    date_cols.append(analysis.name)
                if analysis.data_type in ("integer", "float", "decimal"):
                    numeric_cols.append(analysis.name)
                if analysis.data_type == "string" and analysis.distinct_ratio < 0.3:
                    categorical_cols.append(analysis.name)

            except Exception as exc:
                logger.warning("Kolon analiz hatası '%s': %s", col_name, exc)
                # Hatalı kolon için minimal bilgi oluştur
                columns.append(ColumnAnalysis(
                    name=normalize_column_name(str(col_name)),
                    original_name=str(col_name),
                    data_type="unknown",
                    total_count=len(df),
                ))

        duration = (datetime.now() - start_time).total_seconds() * 1000

        return AnalysisResult(
            file_name=source_name,
            file_type="dataframe",
            file_size=0,
            file_size_human="N/A",
            row_count=len(df),
            column_count=len(df.columns),
            columns=columns,
            pii_columns=pii_cols,
            date_columns=date_cols,
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            analysis_duration_ms=round(duration, 2),
        )

    # ─── Dosya Okuma Metotları ─────────────────────────────────────

    def _read_csv(
        self,
        file_path: str,
        separator: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        CSV dosyasını okur. Encoding tespiti chardet ile yapılır.
        Büyük dosyalar chunk'lar halinde okunur.

        Args:
            file_path: CSV dosya yolu
            separator: Ayırıcı karakter (None ise otomatik tespit)

        Returns:
            Pandas DataFrame
        """
        # ── Encoding tespiti ──
        encoding = self._detect_encoding(file_path)
        logger.info("CSV encoding tespit edildi: %s", encoding)

        # ── Ayırıcı tespiti ──
        if separator is None:
            separator = self._detect_csv_separator(file_path, encoding)

        # ── Dosya boyutuna göre okuma stratejisi ──
        file_size = os.path.getsize(file_path)

        try:
            if file_size > 100 * 1024 * 1024:  # 100 MB üzeri → chunk okuma
                logger.info("Büyük CSV dosyası — chunk okuma modu (%s)", format_file_size(file_size))
                chunks: list[pd.DataFrame] = []
                rows_read = 0
                for chunk in pd.read_csv(
                    file_path,
                    encoding=encoding,
                    sep=separator,
                    chunksize=self.chunk_size,
                    on_bad_lines="warn",
                    low_memory=True,
                ):
                    chunks.append(chunk)
                    rows_read += len(chunk)
                    if rows_read >= self.max_rows:
                        break
                df = pd.concat(chunks, ignore_index=True)
            else:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    sep=separator,
                    on_bad_lines="warn",
                    low_memory=False,
                )
        except UnicodeDecodeError:
            # Encoding fallback zinciri
            for fallback in ["utf-8", "latin-1", "iso-8859-9", "cp1254", "ascii"]:
                try:
                    logger.warning("Encoding fallback: %s", fallback)
                    df = pd.read_csv(
                        file_path,
                        encoding=fallback,
                        sep=separator,
                        on_bad_lines="warn",
                    )
                    break
                except (UnicodeDecodeError, Exception):
                    continue
            else:
                raise RuntimeError(
                    f"CSV dosyası hiçbir encoding ile okunamadı: {file_path}"
                )

        if df.empty:
            raise ValueError("CSV dosyası boş veya geçersiz.")

        return df

    def _read_excel(self, file_path: str) -> pd.DataFrame:
        """
        Excel dosyasını (.xlsx / .xls) okur.

        İlk sheet okunur. Birden fazla sheet varsa uyarı loglanır.

        Args:
            file_path: Excel dosya yolu

        Returns:
            Pandas DataFrame
        """
        try:
            # Sheet isimlerini kontrol et
            xl = pd.ExcelFile(file_path, engine="openpyxl")
            sheet_names = xl.sheet_names

            if len(sheet_names) > 1:
                logger.info(
                    "Excel dosyasında %d sheet var. İlk sheet okunuyor: '%s'",
                    len(sheet_names), sheet_names[0],
                )

            df = pd.read_excel(
                file_path,
                sheet_name=0,
                engine="openpyxl",
            )

            if df.empty:
                raise ValueError("Excel dosyası boş.")

            return df

        except ImportError:
            raise RuntimeError(
                "Excel dosyası okumak için 'openpyxl' paketi gerekli. "
                "pip install openpyxl"
            )
        except Exception as exc:
            raise RuntimeError(f"Excel dosyası okunamadı: {exc}") from exc

    def _read_json(self, file_path: str) -> pd.DataFrame:
        """
        JSON dosyasını okur. Nested yapıları düzleştirir.

        Desteklenen formatlar:
        - JSON Array: [{...}, {...}, ...]
        - JSON Lines (JSONL): her satır bir JSON objesi
        - Nested JSON: otomatik düzleştirme

        Args:
            file_path: JSON dosya yolu

        Returns:
            Pandas DataFrame
        """
        encoding = self._detect_encoding(file_path)

        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read().strip()

            if not content:
                raise ValueError("JSON dosyası boş.")

            # JSON parse
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # JSONL formatını dene — her satır bir JSON objesi
                lines = content.splitlines()
                data = []
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning("JSONL satır %d parse edilemedi, atlanıyor.", i + 1)

            if not data:
                raise ValueError("JSON dosyasından veri okunamadı.")

            # Liste değilse listeye çevir
            if isinstance(data, dict):
                # Tek obje — veya içinde bir liste alanı var mı kontrol et
                for key, value in data.items():
                    if isinstance(value, list) and value and isinstance(value[0], dict):
                        data = value
                        break
                else:
                    data = [data]

            if not isinstance(data, list):
                raise ValueError("JSON verisi liste formatında olmalıdır.")

            # Nested yapıları düzleştir
            flat_data = []
            for record in data:
                if isinstance(record, dict):
                    flat_data.append(flatten_json(record))
                else:
                    flat_data.append({"value": record})

            df = pd.DataFrame(flat_data)

            if df.empty:
                raise ValueError("JSON verisi boş DataFrame oluşturdu.")

            return df

        except (ValueError, RuntimeError):
            raise
        except Exception as exc:
            raise RuntimeError(f"JSON dosyası okunamadı: {exc}") from exc

    # ─── Yardımcı Okuma Metotları ──────────────────────────────────

    def _detect_encoding(self, file_path: str) -> str:
        """
        Dosyanın karakter kodlamasını tespit eder.

        chardet kütüphanesi kullanılır. Bulunamazsa fallback değerler denenir.

        Args:
            file_path: Dosya yolu

        Returns:
            Encoding string'i (ör. "utf-8", "iso-8859-9")
        """
        try:
            import chardet
        except ImportError:
            logger.warning("chardet yüklü değil, utf-8 varsayılıyor.")
            return "utf-8"

        # İlk 100 KB'ı oku (performans için tamamını okumaya gerek yok)
        with open(file_path, "rb") as f:
            raw_data = f.read(min(100 * 1024, os.path.getsize(file_path)))

        result = chardet.detect(raw_data)
        encoding = result.get("encoding", "utf-8") or "utf-8"
        confidence = result.get("confidence", 0)

        # Düşük güven skorunda Türkçe encoding'leri dene
        if confidence < 0.7:
            logger.info(
                "Encoding güven skoru düşük (%.2f). Türkçe fallback denenecek.",
                confidence,
            )
            # Türkçe içerik için yaygın encoding'ler
            for test_enc in ["utf-8", "iso-8859-9", "cp1254"]:
                try:
                    with open(file_path, "r", encoding=test_enc) as f:
                        f.read(1024)
                    return test_enc
                except (UnicodeDecodeError, Exception):
                    continue

        return encoding

    def _detect_csv_separator(self, file_path: str, encoding: str) -> str:
        """
        CSV dosyasının ayırıcı karakterini tespit eder.

        İlk birkaç satırı okuyarak en yaygın ayırıcıyı belirler.

        Args:
            file_path: CSV dosya yolu
            encoding: Dosya encoding'i

        Returns:
            Ayırıcı karakter (ör. ",", ";", "\\t", "|")
        """
        candidates = [",", ";", "\t", "|"]

        try:
            with open(file_path, "r", encoding=encoding) as f:
                # İlk 5 satırı oku
                lines = []
                for _ in range(5):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line)

            if not lines:
                return ","

            # Her ayırıcı için tutarlılık skoru hesapla
            best_sep = ","
            best_score = -1

            for sep in candidates:
                counts = [line.count(sep) for line in lines]
                if all(c > 0 for c in counts):
                    # Tutarlılık: tüm satırlarda aynı sayıda ayırıcı varsa iyi
                    avg_count = sum(counts) / len(counts)
                    variance = sum((c - avg_count) ** 2 for c in counts) / len(counts)
                    score = avg_count / (1 + variance)  # Yüksek ortalama, düşük varyans
                    if score > best_score:
                        best_score = score
                        best_sep = sep

            return best_sep

        except Exception:
            return ","

    # ─── Kolon Analizi ─────────────────────────────────────────────

    def _analyze_column(self, series: pd.Series, original_name: str) -> ColumnAnalysis:
        """
        Tek bir kolon (Series) için kapsamlı analiz yapar.

        Adımlar:
        1. Temel istatistikler (null, distinct)
        2. Veri tipi tespiti
        3. Tip'e özel istatistikler
        4. Pattern tespiti (bankacılık domain)
        5. Dağılım analizi
        6. PII tespiti

        Args:
            series: Analiz edilecek pandas Series
            original_name: Kolonun orijinal adı

        Returns:
            ColumnAnalysis dataclass
        """
        normalized_name = normalize_column_name(original_name)
        total = len(series)
        null_count = int(series.isna().sum())
        non_null = series.dropna()
        non_null_count = len(non_null)

        # Temel istatistikler
        distinct_count = int(non_null.nunique()) if non_null_count > 0 else 0
        null_ratio = round(null_count / total, 4) if total > 0 else 0.0
        distinct_ratio = round(distinct_count / non_null_count, 4) if non_null_count > 0 else 0.0

        # Veri tipi tespiti
        data_type = self._detect_data_type(non_null)

        # Analiz objesi oluştur
        analysis = ColumnAnalysis(
            name=normalized_name,
            original_name=original_name,
            data_type=data_type,
            total_count=total,
            null_count=null_count,
            null_ratio=null_ratio,
            distinct_count=distinct_count,
            distinct_ratio=distinct_ratio,
        )

        if non_null_count == 0:
            return analysis

        # Tip'e özel istatistikler
        if data_type in ("integer", "float", "decimal"):
            self._compute_numeric_stats(analysis, non_null)
        elif data_type in ("date", "datetime"):
            self._compute_date_stats(analysis, non_null)
        elif data_type == "string":
            self._compute_string_stats(analysis, non_null)
        elif data_type == "boolean":
            self._compute_boolean_stats(analysis, non_null)

        # Pattern tespiti (string ve karışık tipler için)
        if data_type in ("string", "integer") or distinct_ratio < 1.0:
            self._detect_patterns(analysis, non_null)

        # Örnek değerler (5 adet)
        sample_n = min(5, non_null_count)
        analysis.sample_values = [
            _to_serializable(v) for v in non_null.sample(n=sample_n, random_state=42).tolist()
        ]

        # En yaygın değerler (top 10)
        analysis.most_common_values = self._compute_most_common(non_null, top_n=10)

        # Dağılım analizi
        analysis.distribution = self._compute_distribution(analysis, non_null)

        # PII tespiti
        self._detect_pii(analysis)

        return analysis

    # ─── Veri Tipi Tespiti ─────────────────────────────────────────

    def _detect_data_type(self, series: pd.Series) -> str:
        """
        Kolon veri tipini tespit eder.

        Tespit sırası:
        1. Boolean (True/False, 0/1, Evet/Hayır)
        2. Integer (tam sayı)
        3. Float / Decimal (ondalıklı sayı)
        4. Date / Datetime (tarih)
        5. String (varsayılan)

        Args:
            series: Null değerler çıkarılmış Series

        Returns:
            Veri tipi string'i
        """
        if len(series) == 0:
            return "string"

        # ── Boolean kontrolü ──
        if self._is_boolean(series):
            return "boolean"

        # ── Pandas dtype kontrolü ──
        dtype = series.dtype

        if pd.api.types.is_integer_dtype(dtype):
            return "integer"
        if pd.api.types.is_float_dtype(dtype):
            # Tüm değerler tam sayı mı kontrol et
            if series.dropna().apply(lambda x: float(x).is_integer()).all():
                return "integer"
            return "float"

        # ── String tabanlı tip tespiti ──
        str_series = series.astype(str).str.strip()

        # Örneklem al (performans için)
        sample = str_series.head(min(self.sample_size, len(str_series)))

        # Tarih kontrolü
        date_ratio = sample.apply(lambda v: detect_date_format(v) is not None).mean()
        if date_ratio > 0.8:
            # Datetime mi date mi?
            datetime_patterns = ["yyyy-mm-dd HH:MM:SS", "dd/mm/yyyy HH:MM:SS",
                                 "dd.mm.yyyy HH:MM", "ISO 8601"]
            has_time = sample.apply(
                lambda v: detect_date_format(v) in datetime_patterns
            ).mean()
            return "datetime" if has_time > 0.5 else "date"

        # Sayısal kontrol (string olarak saklanan sayılar)
        numeric_ratio = sample.apply(lambda v: safe_float(v) is not None).mean()
        if numeric_ratio > 0.8:
            # Integer mi float mi?
            int_ratio = sample.apply(
                lambda v: safe_float(v) is not None and float(safe_float(v)).is_integer()
            ).mean()
            if int_ratio > 0.9:
                return "integer"
            # Decimal kontrolü (2 ondalık basamak — para birimi muhtemel)
            decimal_ratio = sample.apply(self._is_decimal_value).mean()
            if decimal_ratio > 0.5:
                return "decimal"
            return "float"

        return "string"

    def _is_boolean(self, series: pd.Series) -> bool:
        """Boolean kolon tespiti."""
        if pd.api.types.is_bool_dtype(series.dtype):
            return True

        unique_vals = set(series.dropna().astype(str).str.strip().str.lower().unique())

        boolean_sets = [
            {"true", "false"},
            {"0", "1"},
            {"evet", "hayır"},
            {"evet", "hayir"},
            {"yes", "no"},
            {"e", "h"},
            {"y", "n"},
            {"aktif", "pasif"},
            {"var", "yok"},
        ]

        return any(unique_vals.issubset(bs) and len(unique_vals) <= len(bs) for bs in boolean_sets)

    @staticmethod
    def _is_decimal_value(value: str) -> bool:
        """Değerin tam 2 ondalık basamaklı olup olmadığını kontrol eder (para birimi)."""
        try:
            v = str(value).strip()
            if "." in v:
                _, decimal_part = v.rsplit(".", 1)
                return len(decimal_part) == 2
            if "," in v:
                _, decimal_part = v.rsplit(",", 1)
                return len(decimal_part) == 2
        except (ValueError, AttributeError):
            pass
        return False

    # ─── Tip'e Özel İstatistikler ──────────────────────────────────

    def _compute_numeric_stats(self, analysis: ColumnAnalysis, series: pd.Series) -> None:
        """Sayısal kolon istatistikleri."""
        try:
            # String'den sayıya çevirme denemesi
            numeric = pd.to_numeric(series, errors="coerce").dropna()

            if len(numeric) == 0:
                # Manuel çevirme (Türk formatı: 1.234,56)
                numeric = series.apply(safe_float).dropna()
                numeric = pd.to_numeric(numeric, errors="coerce").dropna()

            if len(numeric) == 0:
                return

            analysis.min_value = str(numeric.min())
            analysis.max_value = str(numeric.max())
            analysis.mean_value = _safe_number(float(numeric.mean()))
            analysis.median_value = _safe_number(float(numeric.median()))
            analysis.std_value = _safe_number(float(numeric.std()))

        except Exception as exc:
            logger.debug("Sayısal istatistik hatası (%s): %s", analysis.name, exc)

    def _compute_string_stats(self, analysis: ColumnAnalysis, series: pd.Series) -> None:
        """String kolon istatistikleri."""
        try:
            str_series = series.astype(str)
            lengths = str_series.str.len()

            analysis.min_length = int(lengths.min())
            analysis.max_length = int(lengths.max())
            analysis.avg_length = round(float(lengths.mean()), 2)
            analysis.min_value = str(str_series.min())
            analysis.max_value = str(str_series.max())

        except Exception as exc:
            logger.debug("String istatistik hatası (%s): %s", analysis.name, exc)

    def _compute_date_stats(self, analysis: ColumnAnalysis, series: pd.Series) -> None:
        """Tarih kolon istatistikleri."""
        try:
            dates = pd.to_datetime(series, errors="coerce", dayfirst=True, format="mixed").dropna()
            if len(dates) == 0:
                return

            analysis.min_value = str(dates.min())
            analysis.max_value = str(dates.max())

            # Tarih aralığı
            date_range = (dates.max() - dates.min()).days
            analysis.distribution = {
                "type": "date_range",
                "range_days": int(date_range),
                "earliest": str(dates.min()),
                "latest": str(dates.max()),
            }

        except Exception as exc:
            logger.debug("Tarih istatistik hatası (%s): %s", analysis.name, exc)

    def _compute_boolean_stats(self, analysis: ColumnAnalysis, series: pd.Series) -> None:
        """Boolean kolon istatistikleri."""
        try:
            str_vals = series.astype(str).str.strip().str.lower()
            value_counts = str_vals.value_counts(normalize=True)

            analysis.distribution = {
                "type": "boolean",
                "frequencies": {
                    str(k): round(float(v), 4) for k, v in value_counts.items()
                },
            }
        except Exception as exc:
            logger.debug("Boolean istatistik hatası (%s): %s", analysis.name, exc)

    # ─── Pattern Tespiti ───────────────────────────────────────────

    def _detect_patterns(self, analysis: ColumnAnalysis, series: pd.Series) -> None:
        """
        Kolon değerlerinde bankacılık domain pattern'larını tespit eder.

        Tespit edilen pattern'lar:
        - TCKN (11 hane, algoritmik)
        - IBAN (TR + 24 hane)
        - Kredi kartı (16 hane, Luhn)
        - Email
        - Telefon (+90, 05xx)
        - URL
        - Hesap numarası
        - Müşteri numarası
        - Tarih formatları
        - Para birimi (TRY, USD, EUR)

        Args:
            analysis: Güncellenecek ColumnAnalysis objesi
            series: Analiz edilecek Series (null'lar çıkarılmış)
        """
        # Örneklem al
        sample_size = min(self.sample_size, len(series))
        sample = series.sample(n=sample_size, random_state=42).astype(str).str.strip()

        detected: dict[str, float] = {}
        best_pattern: Optional[str] = None
        best_ratio: float = 0.0
        best_pii: str = "none"

        # ── Bankacılık domain pattern'ları ──
        for detector_fn, semantic_type, pii_level in self._pattern_detectors:
            try:
                matches = sample.apply(detector_fn)
                ratio = float(matches.mean())
                if ratio > 0.3:  # En az %30 eşleşme
                    detected[semantic_type] = round(ratio, 4)
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_pattern = semantic_type
                        best_pii = pii_level
            except Exception:
                continue

        # ── Tarih pattern tespiti ──
        date_matches = sample.apply(lambda v: detect_date_format(v) is not None)
        date_ratio = float(date_matches.mean())
        if date_ratio > 0.3:
            detected["date"] = round(date_ratio, 4)
            # En yaygın tarih formatını bul
            formats = sample.apply(detect_date_format).dropna()
            if len(formats) > 0:
                most_common_fmt = formats.mode().iloc[0]
                detected[f"date_format:{most_common_fmt}"] = round(date_ratio, 4)

        # ── Para birimi pattern tespiti ──
        currency_matches = sample.apply(lambda v: detect_currency(v) is not None)
        currency_ratio = float(currency_matches.mean())
        if currency_ratio > 0.3:
            currencies = sample.apply(detect_currency).dropna()
            if len(currencies) > 0:
                most_common_curr = currencies.mode().iloc[0]
                detected[f"currency:{most_common_curr}"] = round(currency_ratio, 4)
                if best_ratio < currency_ratio:
                    best_pattern = f"currency:{most_common_curr}"
                    best_ratio = currency_ratio

        # Sonuçları kaydet
        analysis.detected_patterns = detected
        if best_pattern and best_ratio > 0.5:
            # Yüksek güvenle tespit edilen pattern
            semantic = best_pattern.split(":")[0] if ":" in best_pattern else best_pattern
            analysis.semantic_type = semantic
            analysis.pattern = self._get_regex_for_pattern(semantic)

            if best_pii != "none":
                analysis.is_pii = True
                analysis.pii_level = best_pii

    def _get_regex_for_pattern(self, semantic_type: str) -> Optional[str]:
        """Semantik tip için regex pattern döndürür."""
        patterns = {
            "tckn": r"^[1-9]\d{10}$",
            "iban": r"^TR\d{24}$",
            "credit_card": r"^\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}$",
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "phone": r"^(\+90|0)?\s?\(?\d{3}\)?\s?\d{3}[\s-]?\d{2}[\s-]?\d{2}$",
            "url": r"^https?://[^\s]+$",
            "account_number": r"^\d{10,16}$",
            "customer_number": r"^(MUS|CUS|MTR|BRC)?\d{6,12}$",
            "date": r"^\d{2}[./-]\d{2}[./-]\d{4}$",
            "currency": r"^[\d.,]+\s*(TL|₺|TRY|\$|USD|€|EUR)$",
        }
        return patterns.get(semantic_type)

    # ─── PII Tespiti ───────────────────────────────────────────────

    def _detect_pii(self, analysis: ColumnAnalysis) -> None:
        """
        Kolon için PII (Kişisel Tanımlayıcı Bilgi) seviyesini tespit eder.

        Semantik tip bazlı tespit + kolon adı bazlı sezgisel tespit.
        """
        # Semantik tip zaten PII belirlemiş olabilir
        if analysis.is_pii:
            return

        # Kolon adı bazlı sezgisel tespit
        name_lower = analysis.name.lower()

        # Kritik PII (kolon adına göre)
        critical_keywords = [
            "tckn", "tc_kimlik", "kimlik_no", "vergi_no",
            "kredi_kart", "credit_card", "kart_no",
        ]
        if any(kw in name_lower for kw in critical_keywords):
            analysis.is_pii = True
            analysis.pii_level = "critical"
            return

        # Yüksek PII
        high_keywords = [
            "iban", "hesap_no", "account", "banka_hesap",
            "pasaport", "passport", "ehliyet", "sgk",
        ]
        if any(kw in name_lower for kw in high_keywords):
            analysis.is_pii = True
            analysis.pii_level = "high"
            return

        # Orta PII
        medium_keywords = [
            "email", "e_posta", "eposta", "telefon", "phone", "tel_no",
            "cep", "gsm", "musteri_no", "customer", "dogum", "birth",
            "ad_soyad", "isim", "soyisim", "name",
        ]
        if any(kw in name_lower for kw in medium_keywords):
            analysis.is_pii = True
            analysis.pii_level = "medium"
            return

        # Düşük PII
        low_keywords = [
            "adres", "address", "sehir", "city", "ilce", "posta_kodu",
            "zip", "cinsiyet", "gender", "meslek", "occupation",
        ]
        if any(kw in name_lower for kw in low_keywords):
            analysis.is_pii = True
            analysis.pii_level = "low"
            return

    # ─── Dağılım Analizi ───────────────────────────────────────────

    def _compute_distribution(
        self, analysis: ColumnAnalysis, series: pd.Series
    ) -> Optional[dict[str, Any]]:
        """
        Kolon dağılım analizini yapar.

        - Sayısal: histogram (10 bin)
        - Kategorik: frekans dağılımı
        - Tarih: zaman aralığı ve yoğunluk

        Args:
            analysis: Kolon analiz sonucu
            series: Analiz edilecek Series

        Returns:
            Dağılım bilgisi dict veya None
        """
        # Tarih kolonları zaten date_stats'ta ele alındı
        if analysis.data_type in ("date", "datetime") and analysis.distribution:
            return analysis.distribution

        # ── Sayısal histogram ──
        if analysis.data_type in ("integer", "float", "decimal"):
            return self._compute_numeric_distribution(series)

        # ── Kategorik frekans ──
        if analysis.data_type == "string" or analysis.data_type == "boolean":
            return self._compute_categorical_distribution(series)

        return None

    def _compute_numeric_distribution(self, series: pd.Series) -> Optional[dict[str, Any]]:
        """Sayısal kolon için histogram dağılımı."""
        try:
            numeric = pd.to_numeric(series, errors="coerce").dropna()
            if len(numeric) < 2:
                return None

            # Histogram hesapla (10 bin)
            counts, bin_edges = np.histogram(numeric, bins=10)

            histogram = []
            for i in range(len(counts)):
                histogram.append({
                    "bin_start": round(float(bin_edges[i]), 4),
                    "bin_end": round(float(bin_edges[i + 1]), 4),
                    "count": int(counts[i]),
                    "ratio": round(int(counts[i]) / len(numeric), 4),
                })

            # Çeyrek değerler
            quartiles = {
                "q1": _safe_number(float(numeric.quantile(0.25))),
                "q2": _safe_number(float(numeric.quantile(0.50))),
                "q3": _safe_number(float(numeric.quantile(0.75))),
                "iqr": _safe_number(float(numeric.quantile(0.75) - numeric.quantile(0.25))),
            }

            # Çarpıklık ve basıklık
            skewness = _safe_number(float(numeric.skew()))
            kurtosis = _safe_number(float(numeric.kurtosis()))

            return {
                "type": "numeric_histogram",
                "histogram": histogram,
                "quartiles": quartiles,
                "skewness": skewness,
                "kurtosis": kurtosis,
            }

        except Exception as exc:
            logger.debug("Histogram hesaplama hatası: %s", exc)
            return None

    def _compute_categorical_distribution(self, series: pd.Series) -> Optional[dict[str, Any]]:
        """Kategorik kolon için frekans dağılımı."""
        try:
            value_counts = series.astype(str).value_counts()
            total = len(series)

            # En fazla 50 kategori göster
            top_n = min(50, len(value_counts))
            top_values = value_counts.head(top_n)

            frequencies = []
            for val, count in top_values.items():
                frequencies.append({
                    "value": str(val),
                    "count": int(count),
                    "ratio": round(int(count) / total, 4),
                })

            return {
                "type": "categorical_frequency",
                "total_categories": int(len(value_counts)),
                "frequencies": frequencies,
            }

        except Exception as exc:
            logger.debug("Frekans hesaplama hatası: %s", exc)
            return None

    # ─── En Yaygın Değerler ────────────────────────────────────────

    @staticmethod
    def _compute_most_common(series: pd.Series, top_n: int = 10) -> list[dict[str, Any]]:
        """Kolondaki en yaygın değerleri döndürür."""
        try:
            value_counts = series.value_counts()
            total = len(series)
            result = []

            for val, count in value_counts.head(top_n).items():
                result.append({
                    "value": _to_serializable(val),
                    "count": int(count),
                    "ratio": round(int(count) / total, 4),
                })

            return result
        except Exception:
            return []

    # ─── Veritabanı Kaydetme ───────────────────────────────────────

    def save_to_db(
        self,
        result: AnalysisResult,
        dataset_id: int,
        db_session: Any,
    ) -> list[Any]:
        """
        Analiz sonucunu veritabanına ColumnProfile kayıtları olarak kaydeder.

        Args:
            result: SchemaAnalyzer'dan dönen AnalysisResult
            dataset_id: İlişkilendirilecek Dataset ID
            db_session: SQLAlchemy Session nesnesi

        Returns:
            Oluşturulan ColumnProfile ORM nesnelerinin listesi
        """
        from app.models.dataset import ColumnProfile

        profiles = []
        for col in result.columns:
            profile_data = col.to_column_profile_dict()
            profile_data["dataset_id"] = dataset_id

            profile = ColumnProfile(**profile_data)
            db_session.add(profile)
            profiles.append(profile)

        try:
            db_session.flush()
            logger.info(
                "Veritabanına %d kolon profili kaydedildi (dataset_id=%d).",
                len(profiles), dataset_id,
            )
        except Exception as exc:
            logger.error("Kolon profilleri kaydedilirken hata: %s", exc)
            db_session.rollback()
            raise

        return profiles


# ═══════════════════════════════════════════════════════════════════════
# Yardımcı Fonksiyonlar (Modül düzeyinde)
# ═══════════════════════════════════════════════════════════════════════


def _safe_number(value: float) -> Optional[float]:
    """NaN ve Inf değerleri None'a çevirir."""
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return round(value, 6)


def _to_serializable(value: Any) -> Any:
    """Değeri JSON serializable hale getirir."""
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, pd.Timedelta):
        return str(value)
    return value


def _sanitize_for_json(obj: Any) -> Any:
    """
    Dict/list yapısındaki NaN, Inf, numpy tiplerini JSON uyumlu hale getirir.
    Rekürsif olarak tüm iç içe yapıları temizler.
    """
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, (datetime, pd.Timestamp)):
        return obj.isoformat()
    return obj
