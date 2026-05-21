"""
Advanced synthetic data generators for banking test data.

Supports:
- KDE (Kernel Density Estimation) based generation
- CTGAN (Conditional Tabular GAN) based generation (requires sdv)
- Banking-domain-specific data generation (customers, accounts, transactions)
- Data quality checking and privacy risk assessment

All external dependencies (scipy, sdv, ctgan) are optional — the code
degrades gracefully with histogram / random fallbacks.
"""

import hashlib
import logging
import math
import random
import string
import uuid
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

_logger = logging.getLogger(__name__)

# ── Optional dependency probing ─────────────────────────────────────────

_HAS_SCIPY = False
try:
    from scipy import stats as scipy_stats
    _HAS_SCIPY = True
except ImportError:
    _logger.info("scipy not installed — KDE will use histogram fallback")

_HAS_NUMPY = False
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _logger.info("numpy not installed — using pure-Python math fallback")

_HAS_SDV = False
try:
    from sdv.single_table import CTGANSynthesizer
    from sdv.metadata import SingleTableMetadata
    _HAS_SDV = True
except ImportError:
    _logger.info("sdv not installed — CTGAN will use KDE fallback")


# ═══════════════════════════════════════════════════════════════════════
# Utility helpers
# ═══════════════════════════════════════════════════════════════════════

def _is_numeric(value: Any) -> bool:
    """Check whether a value is numeric (int/float)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _column_type(values: List[Any]) -> str:
    """Infer column type from sample values: 'numeric' or 'categorical'."""
    non_none = [v for v in values if v is not None]
    if not non_none:
        return "categorical"
    numeric_count = sum(1 for v in non_none if _is_numeric(v))
    return "numeric" if numeric_count / len(non_none) > 0.7 else "categorical"


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stdev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (len(values) - 1))


def _pearson_corr(xs: List[float], ys: List[float]) -> float:
    """Pearson correlation between two lists of equal length."""
    n = min(len(xs), len(ys))
    if n < 3:
        return 0.0
    mx, my = _mean(xs[:n]), _mean(ys[:n])
    sx, sy = _stdev(xs[:n]), _stdev(ys[:n])
    if sx == 0 or sy == 0:
        return 0.0
    cov = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / (n - 1)
    return max(-1.0, min(1.0, cov / (sx * sy)))


# ═══════════════════════════════════════════════════════════════════════
# TCKN & IBAN generators
# ═══════════════════════════════════════════════════════════════════════

def generate_tckn() -> str:
    """Generate a valid Turkish Citizen ID (TCKN) with correct checksum."""
    # First digit cannot be 0
    digits = [random.randint(1, 9)]
    for _ in range(8):
        digits.append(random.randint(0, 9))

    # 10th digit: ((d1+d3+d5+d7+d9)*7 - (d2+d4+d6+d8)) mod 10
    odd_sum = sum(digits[i] for i in range(0, 9, 2))   # 1st,3rd,5th,7th,9th
    even_sum = sum(digits[i] for i in range(1, 8, 2))   # 2nd,4th,6th,8th
    d10 = (odd_sum * 7 - even_sum) % 10
    digits.append(d10)

    # 11th digit: sum(d1..d10) mod 10
    d11 = sum(digits) % 10
    digits.append(d11)

    return "".join(str(d) for d in digits)


def validate_tckn(tckn: str) -> bool:
    """Validate a TCKN string."""
    if not tckn or len(tckn) != 11 or not tckn.isdigit() or tckn[0] == "0":
        return False
    d = [int(c) for c in tckn]
    odd_sum = sum(d[i] for i in range(0, 9, 2))
    even_sum = sum(d[i] for i in range(1, 8, 2))
    if (odd_sum * 7 - even_sum) % 10 != d[9]:
        return False
    if sum(d[:10]) % 10 != d[10]:
        return False
    return True


def generate_iban(bank_code: Optional[str] = None) -> str:
    """Generate a valid-format Turkish IBAN: TR + 2check + 5bank + 16account."""
    if bank_code is None:
        # Common Turkish bank codes
        bank_codes = ["00010", "00046", "00062", "00064", "00067",
                      "00099", "00103", "00111", "00134", "00146"]
        bank_code = random.choice(bank_codes)
    bank_code = bank_code.zfill(5)
    account = "".join(str(random.randint(0, 9)) for _ in range(16))
    bban = bank_code + account  # 21 digits

    # ISO 7064 mod-97 check digit calculation
    # Move "TR00" to end, replace letters: T=29, R=27
    numeric_str = bban + "292700"
    remainder = int(numeric_str) % 97
    check = 98 - remainder
    return "TR" + str(check).zfill(2) + bban


# ═══════════════════════════════════════════════════════════════════════
# KDEGenerator
# ═══════════════════════════════════════════════════════════════════════

class KDEGenerator:
    """Kernel Density Estimation based generator that learns distributions
    from sample data."""

    def __init__(self) -> None:
        self.distributions: Dict[str, Any] = {}
        self.fitted = False
        self._column_order: List[str] = []
        self._column_types: Dict[str, str] = {}
        self._correlations: Dict[Tuple[str, str], float] = {}

    def fit(self, data: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> None:
        """Learn distributions from sample data."""
        if not data:
            raise ValueError("Cannot fit on empty data")

        all_cols = list(data[0].keys())
        cols = columns if columns else all_cols
        self._column_order = cols

        for col in cols:
            values = [row.get(col) for row in data if row.get(col) is not None]
            if not values:
                self._column_types[col] = "categorical"
                self.distributions[col] = {"type": "empty"}
                continue

            col_type = _column_type(values)
            self._column_types[col] = col_type

            if col_type == "numeric":
                num_values = [float(v) for v in values if _is_numeric(v)]
                if not num_values:
                    self.distributions[col] = {"type": "empty"}
                    continue

                dist_info: Dict[str, Any] = {
                    "type": "numeric",
                    "min": min(num_values),
                    "max": max(num_values),
                    "mean": _mean(num_values),
                    "std": _stdev(num_values),
                    "count": len(num_values),
                }

                if _HAS_SCIPY and _HAS_NUMPY and len(num_values) >= 5:
                    arr = np.array(num_values, dtype=float)
                    try:
                        kde = scipy_stats.gaussian_kde(arr)
                        dist_info["kde"] = kde
                        dist_info["method"] = "scipy_kde"
                    except Exception:
                        dist_info["method"] = "histogram"
                        dist_info["histogram"] = self._build_histogram(num_values)
                else:
                    dist_info["method"] = "histogram"
                    dist_info["histogram"] = self._build_histogram(num_values)

                self.distributions[col] = dist_info
            else:
                # Categorical — learn frequency distribution
                freq = Counter(values)
                total = sum(freq.values())
                probs = {k: v / total for k, v in freq.items()}
                self.distributions[col] = {
                    "type": "categorical",
                    "values": list(probs.keys()),
                    "probs": list(probs.values()),
                }

        # Compute pairwise correlations for numeric columns
        numeric_cols = [c for c in cols if self._column_types.get(c) == "numeric"]
        for i, c1 in enumerate(numeric_cols):
            for c2 in numeric_cols[i + 1:]:
                v1 = [float(row.get(c1, 0)) for row in data
                       if _is_numeric(row.get(c1)) and _is_numeric(row.get(c2))]
                v2 = [float(row.get(c2, 0)) for row in data
                       if _is_numeric(row.get(c1)) and _is_numeric(row.get(c2))]
                if len(v1) >= 3:
                    self._correlations[(c1, c2)] = _pearson_corr(v1, v2)

        self.fitted = True

    # ── histogram fallback ──────────────────────────────────────────────

    @staticmethod
    def _build_histogram(values: List[float], bins: int = 50) -> Dict[str, Any]:
        """Build a simple histogram for sampling."""
        lo, hi = min(values), max(values)
        if lo == hi:
            return {"edges": [lo, hi + 1], "weights": [1.0]}
        width = (hi - lo) / bins
        edges = [lo + i * width for i in range(bins + 1)]
        counts = [0] * bins
        for v in values:
            idx = min(int((v - lo) / width), bins - 1)
            counts[idx] += 1
        total = sum(counts) or 1
        weights = [c / total for c in counts]
        return {"edges": edges, "weights": weights}

    @staticmethod
    def _sample_histogram(hist: Dict[str, Any]) -> float:
        """Sample a single value from a histogram."""
        edges = hist["edges"]
        weights = hist["weights"]
        # Weighted random bin selection
        r = random.random()
        cumulative = 0.0
        idx = 0
        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                idx = i
                break
        lo = edges[idx]
        hi = edges[min(idx + 1, len(edges) - 1)]
        return random.uniform(lo, hi)

    # ── generate ────────────────────────────────────────────────────────

    def generate(self, count: int, seed: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate new synthetic records from learned distributions."""
        if not self.fitted:
            raise RuntimeError("Generator not fitted — call fit() first")

        if seed is not None:
            random.seed(seed)
            if _HAS_NUMPY:
                np.random.seed(seed)

        records: List[Dict[str, Any]] = []
        for _ in range(count):
            row: Dict[str, Any] = {}
            for col in self._column_order:
                dist = self.distributions.get(col)
                if dist is None or dist.get("type") == "empty":
                    row[col] = None
                    continue

                if dist["type"] == "numeric":
                    if dist.get("method") == "scipy_kde" and "kde" in dist:
                        val = float(dist["kde"].resample(1)[0][0])
                    elif "histogram" in dist:
                        val = self._sample_histogram(dist["histogram"])
                    else:
                        val = random.gauss(dist["mean"], max(dist["std"], 0.01))
                    # Clamp to observed range with 10% margin
                    margin = (dist["max"] - dist["min"]) * 0.1
                    val = max(dist["min"] - margin, min(val, dist["max"] + margin))
                    # Preserve int type if original was all ints
                    if dist["min"] == int(dist["min"]) and dist["max"] == int(dist["max"]):
                        row[col] = int(round(val))
                    else:
                        row[col] = round(val, 2)
                else:
                    # Categorical — weighted sampling
                    row[col] = random.choices(
                        dist["values"], weights=dist["probs"], k=1
                    )[0]
            records.append(row)

        return records

    # ── quality metrics ─────────────────────────────────────────────────

    def quality_metrics(
        self, original: List[Dict[str, Any]], synthetic: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare quality between original and synthetic data."""
        if not original or not synthetic:
            return {"column_stats": {}, "correlation_preservation": 0.0,
                    "distribution_similarity": {}}

        cols = list(original[0].keys())
        column_stats: Dict[str, Any] = {}
        distribution_similarity: Dict[str, float] = {}

        for col in cols:
            orig_vals = [row.get(col) for row in original if row.get(col) is not None]
            syn_vals = [row.get(col) for row in synthetic if row.get(col) is not None]

            if not orig_vals or not syn_vals:
                continue

            col_type = _column_type(orig_vals)
            if col_type == "numeric":
                orig_num = [float(v) for v in orig_vals if _is_numeric(v)]
                syn_num = [float(v) for v in syn_vals if _is_numeric(v)]
                if orig_num and syn_num:
                    orig_mean = _mean(orig_num)
                    syn_mean = _mean(syn_num)
                    orig_std = _stdev(orig_num)
                    syn_std = _stdev(syn_num)

                    column_stats[col] = {
                        "original_mean": round(orig_mean, 4),
                        "synthetic_mean": round(syn_mean, 4),
                        "original_std": round(orig_std, 4),
                        "synthetic_std": round(syn_std, 4),
                        "mean_diff_pct": round(
                            abs(orig_mean - syn_mean) / max(abs(orig_mean), 1e-9) * 100, 2
                        ),
                    }

                    # Distribution similarity via overlap of normalized ranges
                    if orig_std > 0 and syn_std > 0:
                        # Compare CDFs at quantile points
                        score = 1.0 - min(1.0, abs(orig_mean - syn_mean) / max(orig_std, syn_std))
                        distribution_similarity[col] = round(max(0.0, score), 4)
                    else:
                        distribution_similarity[col] = 1.0 if orig_mean == syn_mean else 0.0
            else:
                orig_freq = Counter(orig_vals)
                syn_freq = Counter(syn_vals)
                orig_total = sum(orig_freq.values()) or 1
                syn_total = sum(syn_freq.values()) or 1
                all_keys = set(orig_freq.keys()) | set(syn_freq.keys())

                column_stats[col] = {
                    "original_unique": len(set(orig_vals)),
                    "synthetic_unique": len(set(syn_vals)),
                    "category_overlap": len(set(orig_vals) & set(syn_vals)),
                }

                # Jensen-Shannon-like divergence approximation
                overlap = 0.0
                for k in all_keys:
                    p = orig_freq.get(k, 0) / orig_total
                    q = syn_freq.get(k, 0) / syn_total
                    overlap += min(p, q)
                distribution_similarity[col] = round(overlap, 4)

        # Correlation preservation
        corr_scores: List[float] = []
        numeric_cols = [c for c in cols if _column_type(
            [row.get(c) for row in original if row.get(c) is not None]
        ) == "numeric"]
        for i, c1 in enumerate(numeric_cols):
            for c2 in numeric_cols[i + 1:]:
                ov1 = [float(row.get(c1, 0)) for row in original
                       if _is_numeric(row.get(c1)) and _is_numeric(row.get(c2))]
                ov2 = [float(row.get(c2, 0)) for row in original
                       if _is_numeric(row.get(c1)) and _is_numeric(row.get(c2))]
                sv1 = [float(row.get(c1, 0)) for row in synthetic
                       if _is_numeric(row.get(c1)) and _is_numeric(row.get(c2))]
                sv2 = [float(row.get(c2, 0)) for row in synthetic
                       if _is_numeric(row.get(c1)) and _is_numeric(row.get(c2))]
                if len(ov1) >= 3 and len(sv1) >= 3:
                    orig_corr = _pearson_corr(ov1, ov2)
                    syn_corr = _pearson_corr(sv1, sv2)
                    corr_scores.append(1.0 - abs(orig_corr - syn_corr))

        correlation_preservation = round(_mean(corr_scores), 4) if corr_scores else 1.0

        return {
            "column_stats": column_stats,
            "correlation_preservation": correlation_preservation,
            "distribution_similarity": distribution_similarity,
        }


# ═══════════════════════════════════════════════════════════════════════
# CTGANGenerator
# ═══════════════════════════════════════════════════════════════════════

class CTGANGenerator:
    """Conditional Tabular GAN generator.
    Uses sdv library if available, otherwise falls back to KDEGenerator."""

    def __init__(self, epochs: int = 100) -> None:
        self.epochs = epochs
        self.model: Any = None
        self.fallback = not _HAS_SDV
        self._kde_fallback: Optional[KDEGenerator] = None
        self._metadata: Optional[Any] = None
        self._fitted = False

    def fit(self, data: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Train CTGAN model on data."""
        if not data:
            raise ValueError("Cannot fit on empty data")

        if _HAS_SDV and not self.fallback:
            try:
                import pandas as pd  # type: ignore
                df = pd.DataFrame(data)
                sdv_meta = SingleTableMetadata()
                sdv_meta.detect_from_dataframe(df)

                # Apply user-provided metadata overrides
                if metadata:
                    for col, col_meta in metadata.items():
                        if isinstance(col_meta, dict) and "sdtype" in col_meta:
                            sdv_meta.update_column(col, **col_meta)

                self.model = CTGANSynthesizer(
                    sdv_meta,
                    epochs=self.epochs,
                    verbose=False,
                )
                self.model.fit(df)
                self._metadata = sdv_meta
                self._fitted = True
                return
            except Exception as e:
                _logger.warning("CTGAN fit failed, falling back to KDE: %s", e)
                self.fallback = True

        # Fallback to KDE
        self._kde_fallback = KDEGenerator()
        self._kde_fallback.fit(data)
        self._fitted = True

    def generate(
        self, count: int, conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate synthetic records, optionally with conditions."""
        if not self._fitted:
            raise RuntimeError("Generator not fitted — call fit() first")

        if self.model is not None and not self.fallback:
            try:
                import pandas as pd  # type: ignore
                if conditions:
                    from sdv.sampling import Condition  # type: ignore
                    cond = Condition(conditions, num_rows=count)
                    df = self.model.sample_from_conditions([cond])
                else:
                    df = self.model.sample(count)
                return df.to_dict("records")
            except Exception as e:
                _logger.warning("CTGAN sample failed, using KDE fallback: %s", e)

        # KDE fallback (possibly with rejection sampling for conditions)
        if self._kde_fallback is None:
            raise RuntimeError("No model available")

        records = self._kde_fallback.generate(count * 3 if conditions else count)

        if conditions:
            records = self._apply_conditions(records, conditions, count)

        return records[:count]

    @staticmethod
    def _apply_conditions(
        records: List[Dict[str, Any]],
        conditions: Dict[str, Any],
        target_count: int,
    ) -> List[Dict[str, Any]]:
        """Filter / rejection-sample records to match conditions."""
        filtered: List[Dict[str, Any]] = []
        for rec in records:
            match = True
            for key, val in conditions.items():
                if key.startswith("min_"):
                    col = key[4:]
                    if col in rec and _is_numeric(rec[col]) and rec[col] < val:
                        match = False
                        break
                elif key.startswith("max_"):
                    col = key[4:]
                    if col in rec and _is_numeric(rec[col]) and rec[col] > val:
                        match = False
                        break
                else:
                    if rec.get(key) != val:
                        match = False
                        break
            if match:
                filtered.append(rec)
            if len(filtered) >= target_count:
                break
        return filtered

    def quality_report(
        self, original: List[Dict[str, Any]], synthetic: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate comprehensive quality metrics."""
        kde = KDEGenerator()
        return kde.quality_metrics(original, synthetic)


# ═══════════════════════════════════════════════════════════════════════
# BankingDataGenerator
# ═══════════════════════════════════════════════════════════════════════

# ── Turkish locale data ─────────────────────────────────────────────────

_ERKEK_ADLAR = [
    "Ahmet", "Mehmet", "Ali", "Mustafa", "Hasan", "Huseyin", "Ibrahim",
    "Ismail", "Osman", "Yusuf", "Murat", "Emre", "Burak", "Omer",
    "Serkan", "Kemal", "Ercan", "Tolga", "Cem", "Baris", "Onur",
    "Fatih", "Hakan", "Volkan", "Deniz", "Kaan", "Arda", "Berk",
]

_KADIN_ADLAR = [
    "Fatma", "Ayse", "Emine", "Hatice", "Zeynep", "Elif", "Merve",
    "Selin", "Derya", "Esra", "Sevgi", "Gulsen", "Ozlem", "Pinar",
    "Sibel", "Tugba", "Irem", "Ceren", "Basak", "Yasemin", "Damla",
    "Gamze", "Burcu", "Neslihan", "Hilal", "Cansu", "Ebru", "Asli",
]

_SOYADLAR = [
    "Yilmaz", "Kaya", "Demir", "Celik", "Sahin", "Yildiz", "Yildirim",
    "Ozturk", "Aydin", "Ozdemir", "Arslan", "Dogan", "Kilic", "Aslan",
    "Cetin", "Koc", "Kurt", "Ozkan", "Simsek", "Polat", "Korkmaz",
    "Erdogan", "Tas", "Cinar", "Gul", "Kaplan", "Aksoy", "Bulut",
    "Karaca", "Unal", "Basar", "Tekin", "Acar", "Aktas", "Erdem",
]

_ILLER = [
    "Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Adana",
    "Konya", "Gaziantep", "Mersin", "Kayseri", "Eskisehir", "Trabzon",
    "Samsun", "Denizli", "Malatya", "Diyarbakir", "Sakarya", "Manisa",
    "Mugla", "Balikesir", "Tekirdag", "Kocaeli", "Hatay", "Kahramanmaras",
]

_ILCELER: Dict[str, List[str]] = {
    "Istanbul": ["Kadikoy", "Besiktas", "Sisli", "Uskudar", "Bakirkoy",
                  "Fatih", "Beyoglu", "Sariyer", "Maltepe", "Atasehir"],
    "Ankara": ["Cankaya", "Kecioren", "Yenimahalle", "Mamak", "Etimesgut",
               "Sincan", "Altindag", "Polatli"],
    "Izmir": ["Konak", "Karsiyaka", "Bornova", "Buca", "Cigli",
              "Bayrakli", "Gaziemir", "Cesme"],
}
_DEFAULT_ILCELER = ["Merkez", "Yenisehir", "Altinova", "Cumhuriyet"]

_SOKAKLAR = [
    "Ataturk Cad.", "Cumhuriyet Mah.", "Istiklal Sok.", "Gazi Cad.",
    "Fatih Mah.", "Yeni Sok.", "Mevlana Cad.", "Hurriyet Mah.",
    "Barbaros Blv.", "Inonu Cad.", "Fevzi Cakmak Sok.", "Zafer Mah.",
]

_ISLEM_ACIKLAMALARI = {
    "havale": ["Kira odemesi", "Fatura odemesi", "Alis odeme", "Burs odemesi",
               "Kredi taksit", "Maas odemesi", "Tedarikci odemesi"],
    "eft": ["Sirket transferi", "Dis banka havale", "Yatirim hesabi",
            "Uluslararasi transfer", "Ithalat odemesi"],
    "virman": ["Hesaplar arasi", "Tasarruf hesabina", "Vadeli hesaba",
               "Kredi kartindan", "Yatirim hesabindan"],
    "atm_cekme": ["Nakit cekim", "Acil nakit", "Haftalik cekim"],
    "pos": ["Market alisi", "Restoran", "Akaryakit", "Online alis",
            "Giyim", "Elektronik", "Saglik", "Egitim"],
    "online": ["E-ticaret", "Abonelik", "Dijital hizmet", "Oyun icerigi",
               "Streaming", "Bulut depolama"],
}

_EMAIL_DOMAINS = [
    "gmail.com", "hotmail.com", "yahoo.com", "outlook.com",
    "yandex.com", "icloud.com", "protonmail.com",
]

_SEGMENTS = ["bireysel", "ticari", "kurumsal", "premium"]
_HESAP_TIPLERI = ["vadesiz", "vadeli", "kredi", "tasarruf"]
_PARA_BIRIMLERI = ["TRY", "USD", "EUR"]
_ISLEM_TIPLERI = ["havale", "eft", "virman", "atm_cekme", "pos", "online"]


class BankingDataGenerator:
    """High-level generator specialized for banking domain data."""

    def __init__(self, generator_type: str = "kde") -> None:
        if generator_type == "ctgan":
            self.generator: Any = CTGANGenerator()
        else:
            self.generator = KDEGenerator()
        self.generator_type = generator_type

    # ── Customers ───────────────────────────────────────────────────────

    def generate_customers(
        self,
        count: int,
        segment_distribution: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate customer records with valid TCKN, Turkish locale data."""
        if segment_distribution is None:
            segment_distribution = {
                "bireysel": 0.55,
                "ticari": 0.20,
                "kurumsal": 0.10,
                "premium": 0.15,
            }

        segments = list(segment_distribution.keys())
        weights = list(segment_distribution.values())

        customers: List[Dict[str, Any]] = []
        used_tckn: set = set()

        for i in range(count):
            # Unique TCKN
            tckn = generate_tckn()
            while tckn in used_tckn:
                tckn = generate_tckn()
            used_tckn.add(tckn)

            cinsiyet = random.choice(["E", "K"])
            if cinsiyet == "E":
                ad = random.choice(_ERKEK_ADLAR)
            else:
                ad = random.choice(_KADIN_ADLAR)
            soyad = random.choice(_SOYADLAR)

            # Age: 18-80
            birth_year = random.randint(datetime.now().year - 80, datetime.now().year - 18)
            birth_month = random.randint(1, 12)
            birth_day = random.randint(1, 28)
            dogum_tarihi = datetime(birth_year, birth_month, birth_day).strftime("%Y-%m-%d")

            segment = random.choices(segments, weights=weights, k=1)[0]
            il = random.choice(_ILLER)
            ilce_list = _ILCELER.get(il, _DEFAULT_ILCELER)
            ilce = random.choice(ilce_list)
            sokak = random.choice(_SOKAKLAR)
            adres = "{} No:{} {}/{}/{}".format(
                sokak, random.randint(1, 200), ilce, il, "Turkiye"
            )

            telefon = "+90 5{:02d} {:03d} {:02d} {:02d}".format(
                random.randint(0, 59),
                random.randint(0, 999),
                random.randint(0, 99),
                random.randint(0, 99),
            )

            email_ad = (ad + "." + soyad).lower().replace(" ", "")
            email_suffix = random.randint(1, 999)
            email = "{}{}@{}".format(email_ad, email_suffix, random.choice(_EMAIL_DOMAINS))

            # Registration date: within last 10 years
            reg_days_ago = random.randint(0, 3650)
            kayit_tarihi = (datetime.now() - timedelta(days=reg_days_ago)).strftime(
                "%Y-%m-%d"
            )

            musteri_no = "MUS{:08d}".format(i + 1)

            customers.append({
                "musteri_id": str(uuid.uuid4()),
                "musteri_no": musteri_no,
                "tckn": tckn,
                "ad": ad,
                "soyad": soyad,
                "dogum_tarihi": dogum_tarihi,
                "cinsiyet": cinsiyet,
                "segment": segment,
                "il": il,
                "ilce": ilce,
                "adres": adres,
                "telefon": telefon,
                "email": email,
                "kayit_tarihi": kayit_tarihi,
            })

        return customers

    # ── Accounts ────────────────────────────────────────────────────────

    def generate_accounts(
        self,
        customer_ids: List[str],
        accounts_per_customer: int = 2,
    ) -> List[Dict[str, Any]]:
        """Generate account records linked to customers (FK integrity)."""
        accounts: List[Dict[str, Any]] = []
        used_iban: set = set()

        for cid in customer_ids:
            n_accounts = max(
                1, accounts_per_customer + random.randint(-1, 1)
            )
            for _ in range(n_accounts):
                iban = generate_iban()
                while iban in used_iban:
                    iban = generate_iban()
                used_iban.add(iban)

                hesap_tipi = random.choice(_HESAP_TIPLERI)
                para_birimi = random.choices(
                    _PARA_BIRIMLERI, weights=[0.7, 0.15, 0.15], k=1
                )[0]

                # Balance depends on account type and currency
                if hesap_tipi == "kredi":
                    bakiye = -round(random.uniform(0, 500000), 2)
                elif hesap_tipi == "vadeli":
                    bakiye = round(random.uniform(1000, 5000000), 2)
                elif hesap_tipi == "tasarruf":
                    bakiye = round(random.uniform(100, 2000000), 2)
                else:  # vadesiz
                    bakiye = round(random.uniform(0, 1000000), 2)

                if para_birimi != "TRY":
                    bakiye = round(bakiye / 30.0, 2)  # rough TRY/FX ratio

                acilis_days_ago = random.randint(0, 3650)
                acilis_tarihi = (
                    datetime.now() - timedelta(days=acilis_days_ago)
                ).strftime("%Y-%m-%d")

                hesap_no = "".join(random.choices(string.digits, k=16))

                accounts.append({
                    "hesap_id": str(uuid.uuid4()),
                    "musteri_id": cid,
                    "hesap_no": hesap_no,
                    "iban": iban,
                    "hesap_tipi": hesap_tipi,
                    "para_birimi": para_birimi,
                    "bakiye": bakiye,
                    "acilis_tarihi": acilis_tarihi,
                })

        return accounts

    # ── Transactions ────────────────────────────────────────────────────

    def generate_transactions(
        self,
        account_ids: List[str],
        per_account: int = 10,
        days: int = 90,
    ) -> List[Dict[str, Any]]:
        """Generate transaction records with realistic distribution."""
        transactions: List[Dict[str, Any]] = []

        for acc_id in account_ids:
            n_tx = max(1, per_account + random.randint(-3, 3))
            for _ in range(n_tx):
                islem_tipi = random.choices(
                    _ISLEM_TIPLERI,
                    weights=[0.25, 0.15, 0.15, 0.15, 0.20, 0.10],
                    k=1,
                )[0]

                # Power-law distribution for amounts: many small, few large
                # Using Pareto-like: amount = base * (1 / U^alpha)
                u = random.random()
                if u < 0.001:
                    u = 0.001
                raw_amount = 50.0 * (1.0 / (u ** 0.6))
                # Clamp to realistic range
                tutar = round(min(raw_amount, 5000000.0), 2)

                # For ATM, amounts are typically round numbers
                if islem_tipi == "atm_cekme":
                    tutar = round(min(tutar, 10000.0) / 50) * 50
                    tutar = max(50.0, float(tutar))

                # Transaction date weighted toward recent
                days_ago = int((random.random() ** 2) * days)  # quadratic: recent-heavy
                tarih = (datetime.now() - timedelta(days=days_ago)).strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )

                aciklamalar = _ISLEM_ACIKLAMALARI.get(islem_tipi, ["Islem"])
                aciklama = random.choice(aciklamalar)

                transactions.append({
                    "islem_id": str(uuid.uuid4()),
                    "hesap_id": acc_id,
                    "islem_tipi": islem_tipi,
                    "tutar": tutar,
                    "tarih": tarih,
                    "aciklama": aciklama,
                })

        return transactions

    # ── Full Dataset ────────────────────────────────────────────────────

    def generate_full_dataset(
        self,
        customer_count: int = 100,
        accounts_per_customer: int = 2,
        transactions_per_account: int = 10,
        days: int = 90,
        segment_distribution: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Generate a complete linked dataset: customers -> accounts -> transactions."""
        customers = self.generate_customers(
            customer_count, segment_distribution=segment_distribution
        )
        customer_ids = [c["musteri_id"] for c in customers]

        accounts = self.generate_accounts(customer_ids, accounts_per_customer)
        account_ids = [a["hesap_id"] for a in accounts]

        transactions = self.generate_transactions(
            account_ids, per_account=transactions_per_account, days=days
        )

        # FK integrity check
        cid_set = set(customer_ids)
        aid_set = set(account_ids)
        fk_ok = (
            all(a["musteri_id"] in cid_set for a in accounts)
            and all(t["hesap_id"] in aid_set for t in transactions)
        )

        # Stats
        total_volume = sum(t["tutar"] for t in transactions)
        balances = [a["bakiye"] for a in accounts]
        avg_balance = _mean(balances) if balances else 0.0

        seg_counts: Dict[str, int] = Counter(c["segment"] for c in customers)
        acct_type_counts: Dict[str, int] = Counter(a["hesap_tipi"] for a in accounts)
        tx_type_counts: Dict[str, int] = Counter(t["islem_tipi"] for t in transactions)

        stats = {
            "customer_count": len(customers),
            "account_count": len(accounts),
            "transaction_count": len(transactions),
            "total_volume_try": round(total_volume, 2),
            "avg_balance": round(avg_balance, 2),
            "segments": dict(seg_counts),
            "account_types": dict(acct_type_counts),
            "transaction_types": dict(tx_type_counts),
        }

        return {
            "customers": customers,
            "accounts": accounts,
            "transactions": transactions,
            "fk_integrity": fk_ok,
            "stats": stats,
        }


# ═══════════════════════════════════════════════════════════════════════
# DataQualityChecker
# ═══════════════════════════════════════════════════════════════════════

class DataQualityChecker:
    """Quality and privacy checks for synthetic data."""

    @staticmethod
    def check_fk_integrity(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Verify all foreign keys are valid."""
        customers = dataset.get("customers", [])
        accounts = dataset.get("accounts", [])
        transactions = dataset.get("transactions", [])

        cid_set = set(c.get("musteri_id") for c in customers)
        aid_set = set(a.get("hesap_id") for a in accounts)

        orphan_accounts = [
            a["hesap_id"] for a in accounts if a.get("musteri_id") not in cid_set
        ]
        orphan_transactions = [
            t["islem_id"] for t in transactions if t.get("hesap_id") not in aid_set
        ]

        return {
            "valid": len(orphan_accounts) == 0 and len(orphan_transactions) == 0,
            "orphan_accounts": orphan_accounts,
            "orphan_transactions": orphan_transactions,
            "total_customers": len(customers),
            "total_accounts": len(accounts),
            "total_transactions": len(transactions),
        }

    @staticmethod
    def check_distributions(
        original: Dict[str, Any], synthetic: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare column distributions between original and synthetic datasets."""
        kde = KDEGenerator()
        results: Dict[str, Any] = {}
        for table_name in ["customers", "accounts", "transactions"]:
            orig_data = original.get(table_name, [])
            syn_data = synthetic.get(table_name, [])
            if orig_data and syn_data:
                results[table_name] = kde.quality_metrics(orig_data, syn_data)
        return results

    @staticmethod
    def privacy_risk_score(
        original: List[Dict[str, Any]], synthetic: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Estimate re-identification risk by checking for near-duplicates."""
        if not original or not synthetic:
            return {
                "risk_score": 0.0,
                "vulnerable_columns": [],
                "recommendation": "Insufficient data for analysis",
            }

        cols = list(original[0].keys())
        vulnerable: List[str] = []

        # Check each column for exact match overlap
        for col in cols:
            orig_vals = set(str(row.get(col, "")) for row in original)
            syn_vals = set(str(row.get(col, "")) for row in synthetic)
            overlap = orig_vals & syn_vals
            # Exclude common categorical values — only flag if high unique overlap
            unique_ratio = len(orig_vals) / max(len(original), 1)
            if unique_ratio > 0.5 and len(overlap) > 0:
                overlap_ratio = len(overlap) / max(len(orig_vals), 1)
                if overlap_ratio > 0.05:
                    vulnerable.append(col)

        # Record-level near-duplicate check (sample-based for performance)
        sample_size = min(200, len(synthetic))
        syn_sample = random.sample(synthetic, sample_size) if len(synthetic) > sample_size else synthetic

        near_dupes = 0
        for syn_row in syn_sample:
            syn_hash = _row_fingerprint(syn_row, cols)
            for orig_row in original[:500]:  # limit for perf
                orig_hash = _row_fingerprint(orig_row, cols)
                similarity = _hash_similarity(syn_hash, orig_hash, cols, syn_row, orig_row)
                if similarity > 0.8:
                    near_dupes += 1
                    break

        risk_score = min(1.0, near_dupes / max(sample_size, 1))

        if risk_score < 0.05:
            recommendation = "Low risk. Synthetic data appears sufficiently different from the original."
        elif risk_score < 0.20:
            recommendation = "Moderate risk. Consider adding more noise or differential privacy."
        else:
            recommendation = (
                "High risk. Significant overlap detected. Use differential privacy, "
                "increase sample diversity, or remove quasi-identifiers."
            )

        return {
            "risk_score": round(risk_score, 4),
            "vulnerable_columns": vulnerable,
            "recommendation": recommendation,
        }


def _row_fingerprint(row: Dict[str, Any], cols: List[str]) -> str:
    """Create a simple hash fingerprint of a row."""
    parts = [str(row.get(c, "")) for c in sorted(cols)]
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def _hash_similarity(
    h1: str, h2: str,
    cols: List[str],
    row1: Dict[str, Any],
    row2: Dict[str, Any],
) -> float:
    """Compare two rows for similarity (0-1)."""
    if h1 == h2:
        return 1.0
    matches = 0
    total = 0
    for col in cols:
        v1, v2 = row1.get(col), row2.get(col)
        if v1 is None and v2 is None:
            continue
        total += 1
        if v1 == v2:
            matches += 1
        elif _is_numeric(v1) and _is_numeric(v2):
            denom = max(abs(float(v1)), abs(float(v2)), 1e-9)
            if abs(float(v1) - float(v2)) / denom < 0.05:
                matches += 0.8
    return matches / max(total, 1)
