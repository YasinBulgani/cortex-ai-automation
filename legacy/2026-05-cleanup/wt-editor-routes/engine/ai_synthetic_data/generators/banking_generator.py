"""
Bankacılık domain'i için korelasyon-koruyan sentetik veri üretici.

Müşteri segmenti, gelir, yaş, risk skoru ve hesap bakiyesi arasındaki
ilişkileri koruyarak gerçekçi test verisi üretir.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, asdict

from faker import Faker

fake = Faker("tr_TR")

SEGMENT_INCOME_MAP = {
    "bireysel": {"low": (2_000, 8_000), "mid": (8_000, 25_000), "high": (25_000, 100_000)},
    "ticari": {"low": (50_000, 200_000), "mid": (200_000, 1_000_000), "high": (1_000_000, 10_000_000)},
    "kobi": {"low": (10_000, 50_000), "mid": (50_000, 500_000), "high": (500_000, 5_000_000)},
}

SEGMENT_BALANCE_MAP = {
    "bireysel": {"low": (500, 5_000), "mid": (5_000, 50_000), "high": (50_000, 500_000)},
    "ticari": {"low": (10_000, 100_000), "mid": (100_000, 1_000_000), "high": (1_000_000, 50_000_000)},
    "kobi": {"low": (2_000, 20_000), "mid": (20_000, 200_000), "high": (200_000, 2_000_000)},
}

TX_DESCRIPTIONS = {
    "havale": ["Fatura ödemesi", "Kira transferi", "Maaş ödemesi", "Tedarikçi ödemesi"],
    "eft": ["EFT gönderimi", "Fatura ödemesi", "Kredi ödemesi"],
    "pos": ["Market alışverişi", "Online alışveriş", "Restoran", "Akaryakıt"],
    "atm": ["Nakit çekim", "Havale gönderimi"],
}


@dataclass
class CustomerProfile:
    customer_id: str
    segment: str
    tc_kimlik: str
    full_name: str
    birth_date: str
    city: str
    income_bracket: str
    risk_score: float


@dataclass
class AccountData:
    account_id: str
    customer_id: str
    account_type: str
    currency: str
    balance: float
    opened_date: str
    status: str


@dataclass
class TransactionData:
    transaction_id: str
    account_id: str
    transaction_type: str
    amount: float
    currency: str
    timestamp: str
    counterparty: str
    description: str


class BankingSyntheticGenerator:
    """Korelasyon-koruyan bankacılık sentetik veri üretici."""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        fake.seed_instance(seed)

    def generate_customer(self, segment: str | None = None) -> CustomerProfile:
        if segment is None:
            segment = random.choice(["bireysel", "ticari", "kobi"])
        income_bracket = random.choices(["low", "mid", "high"], weights=[0.5, 0.35, 0.15])[0]
        age = self._correlated_age(income_bracket)

        return CustomerProfile(
            customer_id=f"C{fake.unique.random_number(digits=8, fix_len=True)}",
            segment=segment,
            tc_kimlik=self._generate_tc_kimlik(),
            full_name=fake.name(),
            birth_date=fake.date_of_birth(minimum_age=max(18, age - 5), maximum_age=age + 5).isoformat(),
            city=fake.city(),
            income_bracket=income_bracket,
            risk_score=round(self._correlated_risk(segment, income_bracket, age), 2),
        )

    def generate_account(self, customer: CustomerProfile, account_type: str | None = None) -> AccountData:
        if account_type is None:
            account_type = random.choice(["vadesiz", "vadeli", "kredi"])
        balance_range = SEGMENT_BALANCE_MAP[customer.segment][customer.income_bracket]
        balance = round(random.uniform(*balance_range), 2)
        if account_type == "kredi":
            balance = -abs(balance)

        return AccountData(
            account_id=f"A{fake.unique.random_number(digits=10, fix_len=True)}",
            customer_id=customer.customer_id,
            account_type=account_type,
            currency="TRY",
            balance=balance,
            opened_date=fake.date_between(start_date="-5y").isoformat(),
            status=random.choices(["aktif", "pasif", "kapali"], weights=[0.85, 0.1, 0.05])[0],
        )

    def generate_transactions(self, account: AccountData, count: int = 10) -> list[TransactionData]:
        txns: list[TransactionData] = []
        base_amount = abs(account.balance) / max(count, 1)
        for _ in range(count):
            tx_type = random.choices(["havale", "eft", "pos", "atm"], weights=[0.3, 0.25, 0.3, 0.15])[0]
            txns.append(TransactionData(
                transaction_id=f"T{fake.unique.random_number(digits=12, fix_len=True)}",
                account_id=account.account_id,
                transaction_type=tx_type,
                amount=round(base_amount * random.uniform(0.1, 3.0), 2),
                currency=account.currency,
                timestamp=fake.date_time_between(start_date="-30d").isoformat(),
                counterparty=fake.company(),
                description=random.choice(TX_DESCRIPTIONS.get(tx_type, ["İşlem"])),
            ))
        txns.sort(key=lambda t: t.timestamp)
        return txns

    def generate_dataset(
        self,
        customer_count: int = 100,
        accounts_per_customer: int = 2,
        txns_per_account: int = 10,
    ) -> dict[str, list[dict]]:
        if customer_count < 0:
            raise ValueError(f"customer_count negatif olamaz: {customer_count}")
        if accounts_per_customer < 1:
            raise ValueError(f"accounts_per_customer en az 1 olmalı: {accounts_per_customer}")
        if txns_per_account < 1:
            raise ValueError(f"txns_per_account en az 1 olmalı: {txns_per_account}")

        customers, accounts, transactions = [], [], []
        for _ in range(customer_count):
            c = self.generate_customer()
            customers.append(asdict(c))
            for _ in range(random.randint(1, accounts_per_customer)):
                a = self.generate_account(c)
                accounts.append(asdict(a))
                for t in self.generate_transactions(a, random.randint(1, txns_per_account)):
                    transactions.append(asdict(t))
        return {"customers": customers, "accounts": accounts, "transactions": transactions}

    # ── korelasyon yardımcıları ─────────────────────────────────────────────

    @staticmethod
    def _correlated_age(income_bracket: str) -> int:
        ranges = {"low": (22, 35), "mid": (30, 50), "high": (35, 65)}
        return random.randint(*ranges[income_bracket])

    @staticmethod
    def _correlated_risk(segment: str, income: str, age: int) -> float:
        base = {"bireysel": 0.3, "ticari": 0.5, "kobi": 0.4}[segment]
        income_adj = {"low": 0.2, "mid": 0.0, "high": -0.15}[income]
        age_adj = -0.005 * (age - 30) if age > 30 else 0.01 * (30 - age)
        return max(0.01, min(0.99, base + income_adj + age_adj + random.uniform(-0.1, 0.1)))

    @staticmethod
    def _generate_tc_kimlik() -> str:
        digits = [random.randint(1, 9)] + [random.randint(0, 9) for _ in range(8)]
        d10 = ((sum(digits[0:9:2]) * 7) - sum(digits[1:8:2])) % 10
        digits.append(d10)
        d11 = sum(digits[:10]) % 10
        digits.append(d11)
        return "".join(map(str, digits))
