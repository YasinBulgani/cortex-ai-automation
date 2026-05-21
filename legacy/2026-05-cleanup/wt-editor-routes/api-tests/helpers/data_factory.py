"""Test data generators using Faker."""

import uuid

from faker import Faker

fake = Faker("tr_TR")


def random_uuid() -> str:
    return str(uuid.uuid4())


def random_project_name() -> str:
    return f"Test_Proje_{fake.word()}_{fake.random_int(1000, 9999)}"


def random_scenario_title() -> str:
    return f"Senaryo_{fake.sentence(nb_words=4)}"


def random_dataset_name() -> str:
    return f"Dataset_{fake.word()}_{fake.random_int(100, 999)}"


def random_email() -> str:
    return fake.email()


def random_password(length: int = 12) -> str:
    return fake.password(length=length)


def random_requirement() -> dict:
    return {
        "external_id": f"REQ-{fake.random_int(1, 999)}",
        "title": fake.sentence(nb_words=5),
        "description": fake.paragraph(),
        "priority": fake.random_element(["low", "medium", "high", "critical"]),
    }


def random_schedule() -> dict:
    return {
        "name": f"Schedule_{fake.word()}",
        "cron_expression": "0 9 * * *",
        "is_active": True,
    }


def random_api_collection() -> dict:
    return {
        "name": f"Collection_{fake.word()}",
        "description": fake.sentence(),
        "base_url": fake.url(),
    }


def random_api_request() -> dict:
    return {
        "name": f"Request_{fake.word()}",
        "method": fake.random_element(["GET", "POST", "PUT", "DELETE"]),
        "path": f"/api/{fake.word()}",
    }


def snapshot_v1(fields: list[dict] | None = None) -> dict:
    """Generate a valid SchemaSnapshotV1."""
    if fields is None:
        fields = [
            {"name": "id", "type": "integer", "nullable": False},
            {"name": "name", "type": "string", "nullable": False},
            {"name": "email", "type": "string", "nullable": True},
        ]
    return {"version": 1, "fields": fields}


def long_string(length: int = 1000) -> str:
    return "A" * length
