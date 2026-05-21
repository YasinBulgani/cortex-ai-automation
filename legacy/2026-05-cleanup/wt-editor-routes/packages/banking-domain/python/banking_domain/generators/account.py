"""
Account generator — Geçerli TR IBAN + hesap tipi + bakiye.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from ..validators.iban import generate_iban_tr


class AccountType(str, Enum):
    CHECKING = "checking"         # Vadesiz
    SAVINGS = "savings"           # Vadeli
    SALARY = "salary"             # Maaş hesabı
    TIME_DEPOSIT = "time_deposit" # Vadeli mevduat
    FX = "fx"                     # Döviz
    INVESTMENT = "investment"     # Yatırım
    CREDIT = "credit"             # Kredili mevduat (KMH)
    BUSINESS = "business"         # Ticari (SME)


class Currency(str, Enum):
    TRY = "TRY"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


@dataclass
class Account:
    id: str
    customer_id: str
    iban: str
    bank_code: str
    account_type: AccountType
    currency: Currency
    balance: float
    available_balance: float      # Bakiye - bloke
    blocked_amount: float = 0.0
    credit_limit: float = 0.0     # KMH veya kredi kartı için
    interest_rate: float = 0.0    # Vadeliler için
    is_active: bool = True
    opened_at: date = field(default_factory=date.today)
    closed_at: date | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "iban": self.iban,
            "bank_code": self.bank_code,
            "account_type": self.account_type.value,
            "currency": self.currency.value,
            "balance": self.balance,
            "available_balance": self.available_balance,
            "blocked_amount": self.blocked_amount,
            "credit_limit": self.credit_limit,
            "interest_rate": self.interest_rate,
            "is_active": self.is_active,
            "opened_at": self.opened_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }


def _balance_for(account_type: AccountType, currency: Currency, income: float) -> float:
    """Tipik bakiye hesabı — segment gelirine oranlı."""
    if account_type == AccountType.CHECKING:
        base = random.uniform(0.1, 3.0) * income  # 0.1x - 3x aylık gelir
    elif account_type in (AccountType.SAVINGS, AccountType.TIME_DEPOSIT):
        base = random.uniform(2.0, 24.0) * income
    elif account_type == AccountType.SALARY:
        base = random.uniform(0.3, 1.5) * income
    elif account_type == AccountType.FX:
        # Döviz bakiyesi TL karşılığı
        base = random.uniform(0.5, 10.0) * income
    elif account_type == AccountType.INVESTMENT:
        base = random.uniform(1.0, 50.0) * income
    elif account_type == AccountType.CREDIT:
        base = random.uniform(-5000, 0)  # Negatif (KMH borç)
    elif account_type == AccountType.BUSINESS:
        base = random.uniform(5.0, 100.0) * income
    else:
        base = random.uniform(0, income)

    # Döviz için kur yaklaşık dönüşüm
    if currency == Currency.USD:
        base /= 35.0
    elif currency == Currency.EUR:
        base /= 38.0
    elif currency == Currency.GBP:
        base /= 44.0

    return round(base, 2)


def _interest_rate_for(account_type: AccountType) -> float:
    """Yıllık faiz (2026 yaklaşımı)."""
    if account_type == AccountType.TIME_DEPOSIT:
        return round(random.uniform(40.0, 52.0), 2)  # 2026 TL vadeli %40-52
    if account_type == AccountType.SAVINGS:
        return round(random.uniform(35.0, 45.0), 2)
    if account_type == AccountType.CHECKING:
        return 0.0
    if account_type == AccountType.CREDIT:
        return round(random.uniform(60.0, 80.0), 2)  # KMH faizi
    return 0.0


def generate_account(
    customer,
    *,
    account_type: AccountType | str | None = None,
    currency: Currency | str = Currency.TRY,
    bank_code: str | None = None,
    include_credit_line: bool = False,
) -> Account:
    """
    Geçerli IBAN + bakiye ile hesap üret.

    Args:
        customer: Customer instance (income'u kullanır)
        account_type: Hesap tipi (default: CHECKING)
        currency: Para birimi
        bank_code: Belirli banka zorla (default: rastgele)
        include_credit_line: KMH limiti ekle
    """
    if account_type is None:
        account_type_enum = AccountType.CHECKING
    elif isinstance(account_type, str):
        account_type_enum = AccountType(account_type)
    else:
        account_type_enum = account_type

    if isinstance(currency, str):
        currency_enum = Currency(currency)
    else:
        currency_enum = currency

    iban = generate_iban_tr(bank_code=bank_code)
    extracted_bank = iban[4:9]

    income = getattr(customer, "income", 30_000)
    balance = _balance_for(account_type_enum, currency_enum, income)
    blocked = round(random.uniform(0, max(0, balance * 0.05)), 2) if balance > 0 else 0.0
    available = balance - blocked

    credit_limit = 0.0
    if include_credit_line or account_type_enum == AccountType.CREDIT:
        credit_limit = round(income * random.uniform(1.0, 5.0), 2)

    return Account(
        id=str(uuid4()),
        customer_id=getattr(customer, "id", "unknown"),
        iban=iban,
        bank_code=extracted_bank,
        account_type=account_type_enum,
        currency=currency_enum,
        balance=balance,
        available_balance=available,
        blocked_amount=blocked,
        credit_limit=credit_limit,
        interest_rate=_interest_rate_for(account_type_enum),
    )
