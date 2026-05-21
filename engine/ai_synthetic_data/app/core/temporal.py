"""
Temporal Pattern Analyzer — Zaman serisi pattern koruma.

Islem tarihlerindeki haftalik/aylik donguleri tespit eder
ve sentetik tarihlerde ayni pattern'i korur.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TemporalAnalyzer:
    """Zaman serisi pattern analizi ve sentetik tarih uretimi."""

    def analyze_temporal_patterns(self, dates: pd.Series) -> dict:
        """Tarih serisindeki zamansal pattern'lari tespit et."""
        dt = pd.to_datetime(dates, errors="coerce").dropna()
        if len(dt) < 10:
            return {"pattern_detected": False}

        weekday_dist = dt.dt.weekday.value_counts(normalize=True).sort_index()
        weekday_names = ["Pazartesi", "Sali", "Carsamba", "Persembe",
                         "Cuma", "Cumartesi", "Pazar"]
        weekday_profile = {
            weekday_names[i]: round(float(weekday_dist.get(i, 0)), 4)
            for i in range(7)
        }

        monthly_dist = dt.dt.month.value_counts(normalize=True).sort_index()
        monthly_profile = {
            str(m): round(float(monthly_dist.get(m, 0)), 4)
            for m in range(1, 13)
        }

        hour_dist = dt.dt.hour.value_counts(normalize=True).sort_index()
        hourly_profile = {
            str(h): round(float(hour_dist.get(h, 0)), 4)
            for h in range(24)
        }

        day_of_month_dist = dt.dt.day.value_counts(normalize=True).sort_index()
        is_month_start_heavy = sum(day_of_month_dist.get(d, 0) for d in range(1, 6)) > 0.25
        is_month_end_heavy = sum(day_of_month_dist.get(d, 0) for d in range(25, 32)) > 0.25

        weekday_ratio = sum(weekday_dist.get(d, 0) for d in range(5))

        return {
            "pattern_detected": True,
            "weekday_profile": weekday_profile,
            "monthly_profile": monthly_profile,
            "hourly_profile": hourly_profile,
            "weekday_ratio": round(float(weekday_ratio), 4),
            "is_month_start_heavy": is_month_start_heavy,
            "is_month_end_heavy": is_month_end_heavy,
            "date_range": {
                "min": dt.min().isoformat(),
                "max": dt.max().isoformat(),
                "span_days": (dt.max() - dt.min()).days,
            },
            "total_records": len(dt),
        }

    def generate_dates_with_pattern(
        self, n: int, pattern: dict,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[str]:
        """Tespit edilen pattern'a uygun sentetik tarihler uret."""
        if not pattern.get("pattern_detected"):
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = end_date - timedelta(days=365)
            days = (end_date - start_date).days
            return [(start_date + timedelta(days=np.random.randint(0, days + 1))).isoformat()
                    for _ in range(n)]

        if end_date is None:
            end_date = date.today()
        if start_date is None:
            span = pattern.get("date_range", {}).get("span_days", 365)
            start_date = end_date - timedelta(days=span)

        weekday_profile = pattern.get("weekday_profile", {})
        weekday_weights = [weekday_profile.get(d, 1 / 7) for d in
                           ["Pazartesi", "Sali", "Carsamba", "Persembe",
                            "Cuma", "Cumartesi", "Pazar"]]
        total_w = sum(weekday_weights)
        weekday_weights = [w / total_w for w in weekday_weights]

        days_range = (end_date - start_date).days
        if days_range <= 0:
            days_range = 365

        all_days: list[tuple[date, int]] = []
        for d in range(days_range + 1):
            day = start_date + timedelta(days=d)
            all_days.append((day, day.weekday()))

        day_weights = [weekday_weights[wd] for _, wd in all_days]
        total_dw = sum(day_weights)
        day_probs = [w / total_dw for w in day_weights]

        indices = np.random.choice(len(all_days), size=n, p=day_probs)
        results = [all_days[i][0].isoformat() for i in indices]
        return sorted(results)

    def generate_timestamps_with_pattern(
        self, n: int, pattern: dict,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[str]:
        """Pattern'a uygun tarih + saat ureten versiyon."""
        dates = self.generate_dates_with_pattern(n, pattern, start_date, end_date)

        hourly = pattern.get("hourly_profile", {})
        hours = list(range(24))
        hour_weights = [hourly.get(str(h), 1 / 24) for h in hours]
        total_h = sum(hour_weights)
        hour_probs = [w / total_h for w in hour_weights]

        results = []
        for d in dates:
            hour = np.random.choice(hours, p=hour_probs)
            minute = np.random.randint(0, 60)
            second = np.random.randint(0, 60)
            results.append(f"{d}T{hour:02d}:{minute:02d}:{second:02d}")

        return results
