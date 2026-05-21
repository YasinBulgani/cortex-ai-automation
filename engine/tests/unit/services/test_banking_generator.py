"""Banking Synthetic Generator unit tests."""

import pytest

from ai_synthetic_data.generators.banking_generator import BankingSyntheticGenerator

@pytest.fixture
def gen():
    return BankingSyntheticGenerator(seed=42)

class TestCustomerGeneration:
    def test_generates_customer(self, gen):
        c = gen.generate_customer()
        assert c.customer_id.startswith("C")
        assert c.segment in ("bireysel", "ticari", "kobi")
        assert len(c.tc_kimlik) == 11
        assert 0 < c.risk_score < 1

    def test_specific_segment(self, gen):
        c = gen.generate_customer(segment="ticari")
        assert c.segment == "ticari"

class TestAccountGeneration:
    def test_generates_account(self, gen):
        c = gen.generate_customer()
        a = gen.generate_account(c)
        assert a.account_id.startswith("A")
        assert a.customer_id == c.customer_id
        assert a.currency == "TRY"

    def test_kredi_negative_balance(self, gen):
        c = gen.generate_customer()
        a = gen.generate_account(c, account_type="kredi")
        assert a.balance < 0

class TestTransactionGeneration:
    def test_generates_transactions(self, gen):
        c = gen.generate_customer()
        a = gen.generate_account(c)
        txns = gen.generate_transactions(a, count=5)
        assert len(txns) == 5
        assert all(t.account_id == a.account_id for t in txns)

    def test_sorted_by_timestamp(self, gen):
        c = gen.generate_customer()
        a = gen.generate_account(c)
        txns = gen.generate_transactions(a, count=10)
        timestamps = [t.timestamp for t in txns]
        assert timestamps == sorted(timestamps)

class TestDataset:
    def test_full_dataset(self, gen):
        ds = gen.generate_dataset(customer_count=5, accounts_per_customer=2, txns_per_account=3)
        assert len(ds["customers"]) == 5
        assert len(ds["accounts"]) >= 5
        assert len(ds["transactions"]) >= 5

    def test_fk_integrity(self, gen):
        ds = gen.generate_dataset(customer_count=10)
        cids = {c["customer_id"] for c in ds["customers"]}
        aids = {a["account_id"] for a in ds["accounts"]}
        orphan_accs = [a for a in ds["accounts"] if a["customer_id"] not in cids]
        orphan_txns = [t for t in ds["transactions"] if t["account_id"] not in aids]
        assert orphan_accs == []
        assert orphan_txns == []

    def test_zero_customers(self, gen):
        ds = gen.generate_dataset(customer_count=0)
        assert ds == {"customers": [], "accounts": [], "transactions": []}

    def test_negative_count_raises(self, gen):
        with pytest.raises(ValueError):
            gen.generate_dataset(customer_count=-1)

    def test_zero_accounts_raises(self, gen):
        with pytest.raises(ValueError):
            gen.generate_dataset(accounts_per_customer=0)
