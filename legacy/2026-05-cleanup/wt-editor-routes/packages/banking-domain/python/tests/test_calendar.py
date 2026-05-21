"""TR takvim — tatiller, iş günleri, maaş günleri."""

from __future__ import annotations

from datetime import date

from banking_domain import (
    is_holiday, is_weekend, is_business_day,
    next_business_day, previous_business_day,
    business_days_between, holidays_in_year, add_business_days,
    SalaryPattern, salary_day_for_month, is_salary_day,
    RESMI_TATILLER, DINI_BAYRAMLAR,
)


class TestHolidays:
    def test_official_holidays(self):
        # 1 Ocak Yılbaşı her yıl
        for year in (2025, 2026, 2027, 2028):
            assert is_holiday(date(year, 1, 1))

    def test_april_23(self):
        assert is_holiday(date(2026, 4, 23))

    def test_republic_day(self):
        # 29 Ekim Cumhuriyet Bayramı
        assert is_holiday(date(2026, 10, 29))

    def test_ramazan_2026(self):
        # 20-22 Mart 2026
        assert is_holiday(date(2026, 3, 20))
        assert is_holiday(date(2026, 3, 21))
        assert is_holiday(date(2026, 3, 22))
        # 23 Mart artık tatil değil
        assert not is_holiday(date(2026, 3, 23))

    def test_kurban_2026(self):
        # 26-29 Mayıs 2026 (4 gün)
        assert is_holiday(date(2026, 5, 26))
        assert is_holiday(date(2026, 5, 27))
        assert is_holiday(date(2026, 5, 28))
        assert is_holiday(date(2026, 5, 29))
        assert not is_holiday(date(2026, 5, 30))

    def test_not_holiday(self):
        # 2 Ocak 2026 (Cuma, normal iş günü)
        assert not is_holiday(date(2026, 1, 2))


class TestBusinessDays:
    def test_weekend(self):
        # 2026 içinde bir Cumartesi
        sat = date(2026, 1, 3)  # Cumartesi
        sun = date(2026, 1, 4)  # Pazar
        assert sat.weekday() == 5
        assert sun.weekday() == 6
        assert is_weekend(sat)
        assert is_weekend(sun)
        assert not is_business_day(sat)
        assert not is_business_day(sun)

    def test_weekday_non_holiday(self):
        # 2026-01-02 Cuma
        friday = date(2026, 1, 2)
        assert is_business_day(friday)

    def test_next_business_day_skip_weekend(self):
        friday = date(2026, 1, 2)  # Cuma
        next_ = next_business_day(friday)
        # Normal durumda Pazartesi — ama başka tatil yoksa
        assert next_.weekday() == 0  # Pazartesi

    def test_next_business_day_skip_holiday(self):
        # 29 Nisan 2026 (Çarşamba), 23 Nisan (Perşembe) tatil
        day_before = date(2026, 4, 22)  # Çarşamba
        nxt = next_business_day(day_before)
        # 23 Nisan tatil, 24 Cuma iş günü olmalı
        assert nxt == date(2026, 4, 24)

    def test_previous_business_day(self):
        monday = date(2026, 1, 5)  # Pazartesi
        prev = previous_business_day(monday)
        assert prev == date(2026, 1, 2)  # Cuma

    def test_business_days_between(self):
        # 2026-01-02 (Cuma) → 2026-01-09 (Cuma)
        # Araf: 2/1 (Cu), 5/1 (Pt), 6/1 (Sa), 7/1 (Ça), 8/1 (Pe)
        # end = 9/1 exclusive → 5 iş günü
        count = business_days_between(date(2026, 1, 2), date(2026, 1, 9))
        assert count == 5

    def test_add_business_days(self):
        # 2026-01-02 (Cuma) + 3 iş günü
        # Sonuç: Pt (5), Sa (6), Ça (7) → 7 Ocak
        result = add_business_days(date(2026, 1, 2), 3)
        assert result == date(2026, 1, 7)

    def test_add_negative_business_days(self):
        # 7 Ocak - 3 iş günü → 2 Ocak
        result = add_business_days(date(2026, 1, 7), -3)
        assert result == date(2026, 1, 2)


class TestHolidaysListing:
    def test_holidays_in_2026_sorted(self):
        holidays = holidays_in_year(2026)
        assert len(holidays) > 0
        # Sorted by date
        for i in range(len(holidays) - 1):
            assert holidays[i][0] <= holidays[i + 1][0]

    def test_specific_holiday_names(self):
        holidays_2026 = {d: name for d, name in holidays_in_year(2026)}
        assert date(2026, 1, 1) in holidays_2026
        assert "Yılbaşı" == holidays_2026[date(2026, 1, 1)]
        assert date(2026, 4, 23) in holidays_2026


class TestSalaryDays:
    def test_civil_servant_15(self):
        # 15 Ocak 2026 Perşembe (iş günü)
        salary = salary_day_for_month(2026, 1, SalaryPattern.CIVIL_SERVANT)
        assert salary == date(2026, 1, 15)
        assert is_salary_day(date(2026, 1, 15))

    def test_salary_day_shifts_to_previous_business(self):
        # Temmuz 2026: 15 Çarşamba — Demokrasi Bayramı! → 14 Salı'ya kayar
        salary = salary_day_for_month(2026, 7, SalaryPattern.CIVIL_SERVANT)
        assert salary == date(2026, 7, 14)
        # Ağustos 2026: 15 Cumartesi → 14 Cuma'ya kayar
        salary_aug = salary_day_for_month(2026, 8, SalaryPattern.CIVIL_SERVANT)
        assert salary_aug == date(2026, 8, 14)

    def test_private_monthly_last_business_day(self):
        # Ocak 2026 son günü = 31 (Cumartesi), o yüzden 30 (Cuma) olmalı
        salary = salary_day_for_month(2026, 1, SalaryPattern.PRIVATE_MONTHLY)
        assert salary == date(2026, 1, 30)

    def test_pension_bucket(self):
        # Emeklilik bucket 0 → 1. gün, bucket 5 → 6. gün
        salary_0 = salary_day_for_month(2026, 2, SalaryPattern.PENSION, pension_bucket=0)
        # 2026-02-01 Pazar → 2026-01-30 Cuma'ya geriler
        assert salary_0 == date(2026, 1, 30)
        salary_5 = salary_day_for_month(2026, 2, SalaryPattern.PENSION, pension_bucket=5)
        assert salary_5 == date(2026, 2, 6)  # Cuma
