import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

MERCHANTS = {
    "GROCERY": ["Migros", "A101", "BİM", "CarrefourSA", "Macro Center", "ŞOK Market"],
    "FOOD_AND_DRINK": ["Starbucks", "Burger King", "Dominos", "Kahve Dünyası", "Simit Sarayı"],
    "UTILITIES": ["İGDAŞ", "İSKİ", "Enerjisa", "Turkcell", "Vodafone", "Türk Telekom"],
    "TRANSPORT": ["İstanbulkart", "Uber", "BiTaksi", "IETT", "BP Akaryakıt", "Shell"],
    "SHOPPING": ["Trendyol", "Hepsiburada", "Amazon TR", "Boyner", "LC Waikiki", "Zara"],
    "ENTERTAINMENT": ["Netflix", "Spotify", "Disney+", "CGV Cinemas"],
    "HEALTH": ["Memorial Hastanesi", "Anadolu Eczanesi", "Gratis"],
    "RENT": ["Kira Ödemesi"],
    "SALARY": ["Maaş Ödemesi"],
    "TRANSFER": ["Havale - Gelen", "EFT - Gelen", "Dahili Transfer"],
    "INTEREST": ["Banka Faiz Geliri"]
}

EXPENSE_RANGES = {
    "GROCERY":        (50, 800),
    "FOOD_AND_DRINK": (30, 250),
    "UTILITIES":      (80, 500),
    "TRANSPORT":      (15, 300),
    "SHOPPING":       (50, 3000),
    "ENTERTAINMENT":  (30, 150),
    "HEALTH":         (50, 2000),
    "RENT":           (3000, 15000),
}


class TransactionGenerator:
    def generate(self, accounts: List[Dict[str, Any]], constraints: Dict[str, Any],
                 txn_count_per_account: int = 15) -> List[Dict[str, Any]]:
        all_transactions: List[Dict[str, Any]] = []

        salary = constraints.get("annual_salary_try")
        monthly_salary = round(salary / 12, 2) if salary else None

        for account in accounts:
            acc_id = account["account_id"]
            acc_type = account["account_type"]
            balance = account["balance"]

            if acc_type == "SAVINGS":
                txns = self._generate_savings_txns(acc_id, balance)
            else:
                txns = self._generate_checking_txns(acc_id, balance, monthly_salary, txn_count_per_account)

            all_transactions.extend(txns)

        return all_transactions

    def _generate_checking_txns(self, account_id: str, current_balance: float,
                                 monthly_salary: Optional[float], count: int) -> List[Dict[str, Any]]:
        transactions = []
        balance = current_balance
        base_date = datetime(2026, 3, 26)

        # Add salary deposits on 1st and 15th
        if monthly_salary:
            half_salary = round(monthly_salary / 2, 2)
            for day_offset in [25, 11]:  # ~March 1 and ~March 15 going backwards
                balance_before = balance
                balance += half_salary
                transactions.append({
                    "txn_id": f"TXN-{uuid.uuid4().hex[:8].upper()}",
                    "account_id": account_id,
                    "amount": half_salary,
                    "balance_after": round(balance, 2),
                    "merchant": random.choice(MERCHANTS["SALARY"]),
                    "category": "SALARY",
                    "date": (base_date - timedelta(days=day_offset)).strftime("%Y-%m-%d"),
                    "type": "CREDIT"
                })

        # Generate expense transactions
        expense_categories = ["GROCERY", "FOOD_AND_DRINK", "UTILITIES", "TRANSPORT",
                              "SHOPPING", "ENTERTAINMENT", "HEALTH"]

        remaining = count - len(transactions)
        for i in range(remaining):
            category = random.choice(expense_categories)
            lo, hi = EXPENSE_RANGES[category]
            amount = round(random.uniform(lo, hi), 2)

            day_offset = random.randint(0, 30)
            txn_date = (base_date - timedelta(days=day_offset)).strftime("%Y-%m-%d")

            balance -= amount

            transactions.append({
                "txn_id": f"TXN-{uuid.uuid4().hex[:8].upper()}",
                "account_id": account_id,
                "amount": -amount,
                "balance_after": round(balance, 2),
                "merchant": random.choice(MERCHANTS[category]),
                "category": category,
                "date": txn_date,
                "type": "DEBIT"
            })

        transactions.sort(key=lambda t: t["date"], reverse=True)
        return transactions

    def _generate_savings_txns(self, account_id: str, current_balance: float) -> List[Dict[str, Any]]:
        transactions = []
        base_date = datetime(2026, 3, 26)

        # Monthly interest
        interest_rate = random.uniform(0.25, 0.45)
        monthly_interest = round(current_balance * (interest_rate / 12), 2)
        transactions.append({
            "txn_id": f"TXN-{uuid.uuid4().hex[:8].upper()}",
            "account_id": account_id,
            "amount": monthly_interest,
            "balance_after": round(current_balance + monthly_interest, 2),
            "merchant": random.choice(MERCHANTS["INTEREST"]),
            "category": "INTEREST",
            "date": (base_date - timedelta(days=1)).strftime("%Y-%m-%d"),
            "type": "CREDIT"
        })

        # Monthly auto-transfer in
        transfer_amount = round(random.uniform(500, 3000), 2)
        transactions.append({
            "txn_id": f"TXN-{uuid.uuid4().hex[:8].upper()}",
            "account_id": account_id,
            "amount": transfer_amount,
            "balance_after": round(current_balance + monthly_interest + transfer_amount, 2),
            "merchant": random.choice(MERCHANTS["TRANSFER"]),
            "category": "TRANSFER",
            "date": (base_date - timedelta(days=16)).strftime("%Y-%m-%d"),
            "type": "CREDIT"
        })

        return transactions
