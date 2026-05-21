"""
Differential Privacy module for TestwrightAI synthetic data protection.

Implements epsilon-differential privacy mechanisms, k-anonymity, l-diversity
checks, re-identification risk assessment, and KVKK compliance reporting
for Turkish banking test data.
"""

import hashlib
import math
import random
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PII DETECTION PATTERNS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_PII_PATTERNS: Dict[str, List[str]] = {
    "tckn": ["tckn", "tc_kimlik", "tc_no", "kimlik_no", "tcno"],
    "ad": ["ad", "first_name", "isim", "adi"],
    "soyad": ["soyad", "last_name", "soyadi", "surname"],
    "telefon": ["telefon", "phone", "tel", "gsm", "cep"],
    "email": ["email", "e_posta", "eposta", "mail"],
    "iban": ["iban"],
    "adres": ["adres", "address", "addr"],
    "dogum": ["dogum", "dogum_tarihi", "birth", "birthdate", "dob"],
}


def detect_pii_columns(data: List[Dict[str, Any]]) -> List[str]:
    """Auto-detect PII columns by name patterns."""
    if not data:
        return []
    columns = list(data[0].keys())
    detected: List[str] = []
    for col in columns:
        col_lower = col.lower()
        for _pii_type, patterns in _PII_PATTERNS.items():
            if any(p in col_lower for p in patterns):
                detected.append(col)
                break
    return detected


def suggest_privacy_config(
    data: List[Dict[str, Any]], epsilon: float = 1.0
) -> Dict[str, Dict[str, Any]]:
    """Auto-generate column_config based on detected column types."""
    if not data:
        return {}

    config: Dict[str, Dict[str, Any]] = {}
    sample = data[0]

    for col, value in sample.items():
        col_lower = col.lower()

        # Check PII patterns
        if any(p in col_lower for p in _PII_PATTERNS.get("tckn", [])):
            config[col] = {
                "type": "pii",
                "mechanism": "hash_and_mask",
                "reason": "Turkish ID number detected",
            }
        elif any(p in col_lower for p in _PII_PATTERNS.get("ad", []) + _PII_PATTERNS.get("soyad", [])):
            config[col] = {
                "type": "pii",
                "mechanism": "generalize",
                "reason": "Personal name detected",
            }
        elif any(p in col_lower for p in _PII_PATTERNS.get("telefon", [])):
            config[col] = {
                "type": "pii",
                "mechanism": "hash_and_mask",
                "reason": "Phone number detected",
            }
        elif any(p in col_lower for p in _PII_PATTERNS.get("email", [])):
            config[col] = {
                "type": "pii",
                "mechanism": "hash_and_mask",
                "reason": "Email address detected",
            }
        elif any(p in col_lower for p in _PII_PATTERNS.get("iban", [])):
            config[col] = {
                "type": "pii",
                "mechanism": "hash_and_mask",
                "reason": "IBAN detected",
            }
        elif any(p in col_lower for p in _PII_PATTERNS.get("adres", [])):
            config[col] = {
                "type": "pii",
                "mechanism": "generalize",
                "reason": "Address detected",
            }
        elif any(p in col_lower for p in _PII_PATTERNS.get("dogum", [])):
            config[col] = {
                "type": "quasi_identifier",
                "mechanism": "generalize",
                "granularity": "year",
                "reason": "Birth date detected (quasi-identifier)",
            }
        elif isinstance(value, (int, float)):
            # Numeric columns: estimate sensitivity from data range
            numeric_vals = [
                row[col] for row in data
                if col in row and isinstance(row[col], (int, float))
            ]
            if numeric_vals:
                sensitivity = max(numeric_vals) - min(numeric_vals)
                if sensitivity == 0:
                    sensitivity = 1.0
            else:
                sensitivity = 1.0
            config[col] = {
                "type": "numeric",
                "mechanism": "laplace",
                "sensitivity": sensitivity,
                "reason": "Numeric column — Laplace noise recommended",
            }
        elif isinstance(value, str):
            # Categorical string columns
            config[col] = {
                "type": "categorical",
                "mechanism": "randomized_response",
                "reason": "Categorical column — randomized response recommended",
            }

    return config


def validate_tckn(tckn: str) -> bool:
    """
    Validate Turkish ID number (TCKN) checksum.

    Algorithm:
    - 11 digits, first digit cannot be 0
    - d10 = ((d1+d3+d5+d7+d9)*7 - (d2+d4+d6+d8)) % 10
    - d11 = sum(d1..d10) % 10
    """
    if not tckn or len(tckn) != 11:
        return False
    if not tckn.isdigit():
        return False
    if tckn[0] == "0":
        return False

    digits = [int(c) for c in tckn]

    odd_sum = digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
    even_sum = digits[1] + digits[3] + digits[5] + digits[7]
    d10 = (odd_sum * 7 - even_sum) % 10
    if d10 != digits[9]:
        return False

    d11 = sum(digits[:10]) % 10
    if d11 != digits[10]:
        return False

    return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PRIVACY BUDGET MANAGER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PrivacyBudgetManager:
    """Tracks cumulative privacy budget across multiple queries."""

    def __init__(self, total_budget: float = 10.0):
        self.total_budget = total_budget
        self._spent = 0.0
        self._allocations: List[Dict[str, Any]] = []

    def allocate(self, amount: float) -> bool:
        """Reserve budget for a query. Returns True if budget is available."""
        if amount <= 0:
            raise ValueError("Allocation amount must be positive")
        if self._spent + amount > self.total_budget:
            return False
        self._allocations.append({"amount": amount, "status": "allocated"})
        return True

    def spend(self, amount: float) -> None:
        """Mark budget as spent."""
        if amount <= 0:
            raise ValueError("Spend amount must be positive")
        if self._spent + amount > self.total_budget:
            raise ValueError(
                "Cannot spend %.4f — only %.4f remaining"
                % (amount, self.remaining())
            )
        self._spent += amount
        self._allocations.append({"amount": amount, "status": "spent"})

    def remaining(self) -> float:
        """How much budget is left."""
        return max(0.0, self.total_budget - self._spent)

    def is_exhausted(self) -> bool:
        """True if no budget remains."""
        return self._spent >= self.total_budget

    def reset(self) -> None:
        """Reset budget (new session)."""
        self._spent = 0.0
        self._allocations.clear()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DIFFERENTIAL PRIVACY ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class DifferentialPrivacy:
    """
    Epsilon-differential privacy engine for synthetic data protection.

    Parameters
    ----------
    epsilon : float
        Privacy budget (lower = more private, typically 0.1-10).
    delta : float
        Probability of privacy breach.
    """

    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
        if epsilon <= 0:
            raise ValueError("Epsilon must be positive")
        if delta <= 0 or delta >= 1:
            raise ValueError("Delta must be in (0, 1)")
        self.epsilon = epsilon
        self.delta = delta
        self.budget_spent = 0.0
        self.queries: List[Dict[str, Any]] = []

    # ── Noise mechanisms ──────────────────────────────────────────────

    def add_laplace_noise(self, value: float, sensitivity: float) -> float:
        """
        Add calibrated Laplace noise.

        noise_scale = sensitivity / epsilon
        """
        noise_scale = sensitivity / self.epsilon
        if _HAS_NUMPY:
            noise = float(np.random.laplace(0, noise_scale))
        else:
            # Inverse CDF of Laplace distribution
            u = random.random() - 0.5
            noise = -noise_scale * _sign(u) * math.log(1 - 2 * abs(u))
        self.budget_spent += self.epsilon
        self.queries.append({
            "mechanism": "laplace",
            "sensitivity": sensitivity,
            "noise_scale": noise_scale,
            "epsilon_used": self.epsilon,
        })
        return value + noise

    def add_gaussian_noise(self, value: float, sensitivity: float) -> float:
        """
        Add Gaussian noise.

        sigma = sensitivity * sqrt(2 * ln(1.25/delta)) / epsilon
        """
        sigma = sensitivity * math.sqrt(2 * math.log(1.25 / self.delta)) / self.epsilon
        if _HAS_NUMPY:
            noise = float(np.random.normal(0, sigma))
        else:
            # Box-Muller transform
            u1 = random.random()
            u2 = random.random()
            noise = sigma * math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        self.budget_spent += self.epsilon
        self.queries.append({
            "mechanism": "gaussian",
            "sensitivity": sensitivity,
            "sigma": sigma,
            "epsilon_used": self.epsilon,
        })
        return value + noise

    # ── Dataset privatization ────────────────────────────────────────

    def privatize_dataset(
        self,
        data: List[Dict[str, Any]],
        column_config: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Apply differential privacy to a full dataset.

        column_config specifies per-column privacy strategy.
        """
        if not data:
            return {
                "privatized_data": [],
                "columns_processed": {},
                "budget_consumed": 0.0,
                "remaining_budget": 0.0,
            }

        budget_before = self.budget_spent
        privatized = [dict(row) for row in data]
        columns_processed: Dict[str, Dict[str, Any]] = {}

        for col, cfg in column_config.items():
            mechanism = cfg.get("mechanism", "laplace")
            col_type = cfg.get("type", "numeric")

            if mechanism == "laplace" and col_type == "numeric":
                sensitivity = cfg.get("sensitivity", 1.0)
                for row in privatized:
                    if col in row and isinstance(row[col], (int, float)):
                        row[col] = self.add_laplace_noise(float(row[col]), sensitivity)
                columns_processed[col] = {
                    "mechanism": "laplace",
                    "sensitivity": sensitivity,
                    "records_affected": sum(
                        1 for r in data if col in r and isinstance(r[col], (int, float))
                    ),
                }

            elif mechanism == "gaussian" and col_type == "numeric":
                sensitivity = cfg.get("sensitivity", 1.0)
                for row in privatized:
                    if col in row and isinstance(row[col], (int, float)):
                        row[col] = self.add_gaussian_noise(float(row[col]), sensitivity)
                columns_processed[col] = {
                    "mechanism": "gaussian",
                    "sensitivity": sensitivity,
                    "records_affected": sum(
                        1 for r in data if col in r and isinstance(r[col], (int, float))
                    ),
                }

            elif mechanism == "truncate" and col_type == "numeric":
                min_val = cfg.get("min", 0)
                max_val = cfg.get("max", 1e9)
                sensitivity = cfg.get("sensitivity", max_val - min_val)
                for row in privatized:
                    if col in row and isinstance(row[col], (int, float)):
                        clipped = max(min_val, min(max_val, float(row[col])))
                        row[col] = self.add_laplace_noise(clipped, sensitivity)
                columns_processed[col] = {
                    "mechanism": "truncate",
                    "min": min_val,
                    "max": max_val,
                    "records_affected": sum(
                        1 for r in data if col in r and isinstance(r[col], (int, float))
                    ),
                }

            elif mechanism == "randomized_response":
                p = 1.0 / (1.0 + math.exp(self.epsilon))
                unique_values = list(set(
                    row[col] for row in data if col in row and row[col] is not None
                ))
                if len(unique_values) > 1:
                    for row in privatized:
                        if col in row and row[col] is not None:
                            if random.random() < p:
                                # Flip to a random other value
                                alternatives = [v for v in unique_values if v != row[col]]
                                if alternatives:
                                    row[col] = random.choice(alternatives)
                columns_processed[col] = {
                    "mechanism": "randomized_response",
                    "flip_probability": p,
                    "unique_values": len(unique_values),
                    "records_affected": sum(
                        1 for r in data if col in r and r[col] is not None
                    ),
                }

            elif mechanism == "hash_and_mask":
                for row in privatized:
                    if col in row and row[col] is not None:
                        original = str(row[col])
                        hashed = hashlib.sha256(original.encode("utf-8")).hexdigest()[:16]
                        # Keep only last 2 chars visible
                        last2 = original[-2:] if len(original) >= 2 else original
                        row[col] = "****%s_%s" % (last2, hashed)
                columns_processed[col] = {
                    "mechanism": "hash_and_mask",
                    "records_affected": sum(
                        1 for r in data if col in r and r[col] is not None
                    ),
                }

            elif mechanism == "generalize":
                granularity = cfg.get("granularity", "category")
                for row in privatized:
                    if col in row and row[col] is not None:
                        row[col] = _generalize_value(row[col], granularity)
                columns_processed[col] = {
                    "mechanism": "generalize",
                    "granularity": granularity,
                    "records_affected": sum(
                        1 for r in data if col in r and r[col] is not None
                    ),
                }

            elif mechanism == "suppress_small_groups":
                min_group = cfg.get("min_group", 5)
                group_counts: Dict[Any, int] = Counter()
                for row in data:
                    if col in row:
                        group_counts[row[col]] += 1
                suppressed_count = 0
                privatized_filtered = []
                for row in privatized:
                    if col in row and group_counts.get(row[col], 0) < min_group:
                        suppressed_count += 1
                        continue
                    privatized_filtered.append(row)
                privatized = privatized_filtered
                columns_processed[col] = {
                    "mechanism": "suppress_small_groups",
                    "min_group": min_group,
                    "records_suppressed": suppressed_count,
                    "records_remaining": len(privatized),
                }

        budget_consumed = self.budget_spent - budget_before
        return {
            "privatized_data": privatized,
            "columns_processed": columns_processed,
            "budget_consumed": budget_consumed,
            "remaining_budget": max(0.0, 10.0 - self.budget_spent),
        }

    # ── Privacy checks ───────────────────────────────────────────────

    def k_anonymity_check(
        self,
        data: List[Dict[str, Any]],
        quasi_identifiers: List[str],
        k: int = 5,
    ) -> Dict[str, Any]:
        """
        Check if dataset satisfies k-anonymity.

        A dataset satisfies k-anonymity if every combination of
        quasi-identifier values appears at least k times.
        """
        if not data or not quasi_identifiers:
            return {
                "satisfies_k": True,
                "k_achieved": 0,
                "violating_groups": 0,
                "total_groups": 0,
            }

        group_counts: Dict[Tuple[Any, ...], int] = Counter()
        for row in data:
            key = tuple(row.get(qi) for qi in quasi_identifiers)
            group_counts[key] += 1

        total_groups = len(group_counts)
        min_count = min(group_counts.values()) if group_counts else 0
        violating = sum(1 for cnt in group_counts.values() if cnt < k)

        return {
            "satisfies_k": min_count >= k,
            "k_achieved": min_count,
            "violating_groups": violating,
            "total_groups": total_groups,
        }

    def l_diversity_check(
        self,
        data: List[Dict[str, Any]],
        quasi_identifiers: List[str],
        sensitive_attr: str,
        l: int = 3,
    ) -> Dict[str, Any]:
        """
        Check if dataset satisfies l-diversity.

        Each equivalence class (group of records sharing the same
        quasi-identifier values) must have at least l distinct values
        for the sensitive attribute.
        """
        if not data or not quasi_identifiers:
            return {
                "satisfies_l": True,
                "l_achieved": 0,
                "violations": 0,
            }

        groups: Dict[Tuple[Any, ...], set] = {}
        for row in data:
            key = tuple(row.get(qi) for qi in quasi_identifiers)
            if key not in groups:
                groups[key] = set()
            val = row.get(sensitive_attr)
            if val is not None:
                groups[key].add(val)

        if not groups:
            return {"satisfies_l": True, "l_achieved": 0, "violations": 0}

        min_diversity = min(len(vals) for vals in groups.values())
        violations = sum(1 for vals in groups.values() if len(vals) < l)

        return {
            "satisfies_l": min_diversity >= l,
            "l_achieved": min_diversity,
            "violations": violations,
        }

    def reidentification_risk(
        self,
        original: List[Dict[str, Any]],
        synthetic: List[Dict[str, Any]],
        quasi_identifiers: List[str],
    ) -> Dict[str, Any]:
        """
        Estimate re-identification risk.

        For each synthetic record, find closest match in original using
        quasi-identifiers and calculate match probability.
        """
        if not original or not synthetic or not quasi_identifiers:
            return {
                "overall_risk": 0.0,
                "max_risk": 0.0,
                "risky_records_pct": 0.0,
                "recommendation": "Insufficient data for risk assessment",
            }

        # Build original fingerprints
        orig_fingerprints: List[Dict[str, Any]] = []
        for row in original:
            fp = {qi: row.get(qi) for qi in quasi_identifiers}
            orig_fingerprints.append(fp)

        risks: List[float] = []
        for syn_row in synthetic:
            syn_fp = {qi: syn_row.get(qi) for qi in quasi_identifiers}
            best_match = 0.0
            for orig_fp in orig_fingerprints:
                match_score = _fingerprint_similarity(syn_fp, orig_fp, quasi_identifiers)
                if match_score > best_match:
                    best_match = match_score
            risks.append(best_match)

        overall_risk = sum(risks) / len(risks) if risks else 0.0
        max_risk = max(risks) if risks else 0.0
        risky_threshold = 0.8
        risky_count = sum(1 for r in risks if r >= risky_threshold)
        risky_pct = (risky_count / len(risks) * 100) if risks else 0.0

        if overall_risk < 0.2:
            recommendation = "Low risk — synthetic data provides strong privacy protection"
        elif overall_risk < 0.5:
            recommendation = "Moderate risk — consider increasing epsilon or adding more noise"
        elif overall_risk < 0.8:
            recommendation = "High risk — additional privacy mechanisms recommended"
        else:
            recommendation = "Critical risk — data should not be released without stronger anonymization"

        return {
            "overall_risk": round(overall_risk, 4),
            "max_risk": round(max_risk, 4),
            "risky_records_pct": round(risky_pct, 2),
            "recommendation": recommendation,
        }

    # ── KVKK compliance report ───────────────────────────────────────

    def privacy_report(
        self,
        data: List[Dict[str, Any]],
        original: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive KVKK compliance report.

        Checks PII detection, k-anonymity, l-diversity, and
        re-identification risk.
        """
        pii_detected = detect_pii_columns(data)

        # Determine which PII columns have been protected
        protected: List[str] = []
        if config:
            for col in pii_detected:
                if col in config:
                    protected.append(col)

        # Quasi-identifiers for anonymity checks
        quasi_ids = [
            col for col in (data[0].keys() if data else [])
            if any(
                p in col.lower()
                for p in ["dogum", "il", "yas", "cinsiyet", "meslek", "age", "gender", "city"]
            )
        ]

        # k-anonymity check
        k_result = self.k_anonymity_check(data, quasi_ids, k=5) if quasi_ids else {
            "satisfies_k": True, "k_achieved": 0, "violating_groups": 0, "total_groups": 0
        }

        # l-diversity check (look for a sensitive attribute)
        sensitive_candidates = [
            col for col in (data[0].keys() if data else [])
            if any(s in col.lower() for s in ["bakiye", "gelir", "maas", "balance", "income", "salary"])
        ]
        l_result = None
        if quasi_ids and sensitive_candidates:
            l_result_raw = self.l_diversity_check(data, quasi_ids, sensitive_candidates[0], l=3)
            l_result = {
                "l": l_result_raw["l_achieved"],
                "satisfied": l_result_raw["satisfies_l"],
            }

        # Re-identification risk
        reident_risk = None
        if original and quasi_ids:
            risk_result = self.reidentification_risk(original, data, quasi_ids)
            reident_risk = risk_result["overall_risk"]

        # KVKK compliance assessment
        kvkk_issues: List[str] = []
        recommendations: List[str] = []

        unprotected_pii = [col for col in pii_detected if col not in protected]
        if unprotected_pii:
            kvkk_issues.append(
                "Unprotected PII columns: %s" % ", ".join(unprotected_pii)
            )
            recommendations.append(
                "Apply hash_and_mask or generalize to: %s" % ", ".join(unprotected_pii)
            )

        if not k_result["satisfies_k"] and quasi_ids:
            kvkk_issues.append(
                "k-anonymity not satisfied (k=%d, need k>=5)" % k_result["k_achieved"]
            )
            recommendations.append("Apply suppress_small_groups to quasi-identifiers")

        if l_result and not l_result["satisfied"]:
            kvkk_issues.append(
                "l-diversity not satisfied (l=%d, need l>=3)" % l_result["l"]
            )
            recommendations.append("Add noise to sensitive attributes or generalize further")

        if reident_risk is not None and reident_risk > 0.5:
            kvkk_issues.append(
                "Re-identification risk too high: %.2f%%" % (reident_risk * 100)
            )
            recommendations.append("Lower epsilon or add additional noise to quasi-identifiers")

        if self.epsilon > 5.0:
            kvkk_issues.append(
                "Epsilon value (%.1f) is too high for sensitive banking data" % self.epsilon
            )
            recommendations.append("Use epsilon <= 1.0 for KVKK-compliant banking data")

        if not recommendations:
            recommendations.append("Current privacy settings meet KVKK requirements")

        kvkk_compliant = len(kvkk_issues) == 0

        return {
            "epsilon": self.epsilon,
            "delta": self.delta,
            "budget_spent": self.budget_spent,
            "k_anonymity": {
                "k": k_result["k_achieved"],
                "satisfied": k_result["satisfies_k"],
            },
            "l_diversity": l_result,
            "reidentification_risk": reident_risk,
            "pii_columns_detected": pii_detected,
            "pii_columns_protected": protected,
            "kvkk_compliant": kvkk_compliant,
            "kvkk_issues": kvkk_issues,
            "recommendations": recommendations,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PRIVATE HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _sign(x: float) -> float:
    """Return the sign of x."""
    if x > 0:
        return 1.0
    elif x < 0:
        return -1.0
    return 0.0


def _generalize_value(value: Any, granularity: str) -> Any:
    """Generalize a value based on granularity."""
    if value is None:
        return None

    s = str(value)

    if granularity == "year":
        # Extract year from date-like strings
        match = re.search(r"(\d{4})", s)
        if match:
            return match.group(1)
        return s

    if granularity == "month":
        # Extract year-month from date-like strings
        match = re.search(r"(\d{4}[-/]\d{2})", s)
        if match:
            return match.group(1)
        return s

    if granularity == "category":
        # For names, replace with first letter + asterisks
        if len(s) > 1:
            return s[0] + "*" * (len(s) - 1)
        return "*"

    if granularity == "range":
        # For numeric-looking strings, round to nearest 10
        try:
            num = float(s)
            base = int(num // 10) * 10
            return "%d-%d" % (base, base + 10)
        except (ValueError, TypeError):
            return s

    # Default: truncate to first 3 characters
    if len(s) > 3:
        return s[:3] + "***"
    return s


def _fingerprint_similarity(
    fp1: Dict[str, Any],
    fp2: Dict[str, Any],
    keys: List[str],
) -> float:
    """Calculate similarity between two fingerprints (0.0 to 1.0)."""
    if not keys:
        return 0.0

    matches = 0
    total = len(keys)

    for key in keys:
        v1 = fp1.get(key)
        v2 = fp2.get(key)

        if v1 is None or v2 is None:
            continue

        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            # Numeric similarity: inverse of relative distance
            max_val = max(abs(v1), abs(v2), 1.0)
            distance = abs(v1 - v2) / max_val
            matches += max(0.0, 1.0 - distance)
        elif str(v1) == str(v2):
            matches += 1.0

    return matches / total
