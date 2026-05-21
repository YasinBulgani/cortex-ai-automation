"""Synthetic data generation integration tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestSyntheticData:
    PREFIX = "/api/v1/synthetic"

    def test_requires_auth(self, client: TestClient) -> None:
        r = client.get(f"{self.PREFIX}/generators")
        assert r.status_code == 401

    def test_list_generators(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        r = client.get(f"{self.PREFIX}/generators", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()["generators"]) >= 1

    def test_generate_data(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        r = client.post(
            f"{self.PREFIX}/generate",
            json={
                "count": 3,
                "generator_type": "kde",
                "sample_data": [
                    {"age": 30, "city": "Istanbul"},
                    {"age": 40, "city": "Ankara"},
                    {"age": 35, "city": "Izmir"},
                ],
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["record_count"] == 3

    def test_generate_with_invalid_schema(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        r = client.post(
            f"{self.PREFIX}/generate",
            json={"count": 2, "generator_type": "kde", "sample_data": []},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_banking_dataset(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        r = client.post(
            f"{self.PREFIX}/banking-dataset",
            json={"customer_count": 2, "accounts_per_customer": 1, "transactions_per_account": 1, "days": 5},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["fk_integrity"] is True
        assert body["stats"]["customer_count"] == 2

    def test_quality_check(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        payload = {
            "original": [{"age": 30, "city": "Istanbul"}, {"age": 40, "city": "Ankara"}],
            "synthetic": [{"age": 31, "city": "Istanbul"}, {"age": 39, "city": "Ankara"}],
        }
        r = client.post(f"{self.PREFIX}/quality-check", json=payload, headers=auth_headers)
        assert r.status_code == 200
        assert "overall_score" in r.json()

    def test_privacy_risk(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        payload = {
            "original": [{"email": "a@test.com", "age": 30}, {"email": "b@test.com", "age": 40}],
            "synthetic": [{"email": "x@test.com", "age": 31}, {"email": "y@test.com", "age": 39}],
        }
        r = client.post(f"{self.PREFIX}/privacy-risk", json=payload, headers=auth_headers)
        assert r.status_code == 200
        assert "risk_score" in r.json()

    def test_suggest_privacy_config(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        r = client.post(
            f"{self.PREFIX}/privacy/suggest-config",
            json={"data": [{"email": "a@test.com", "age": 30}, {"email": "b@test.com", "age": 40}]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert "suggestions" in r.json()
        assert "column_config" in r.json()

    def test_validate_tckn(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        r = client.post(
            f"{self.PREFIX}/privacy/validate-tckn",
            json={"tckn": "10000000146"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert "valid" in r.json()
