"""
Sentetik veri entegrasyon hook'u.

Kullanım:
    @pytest.fixture
    def sample_user(synthetic):
        return synthetic.user()

    @pytest.fixture
    def sample_scenario(synthetic):
        return synthetic.scenario(step_count=5)
"""

from __future__ import annotations

import random
import string
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class SyntheticUser:
    email: str
    password: str = "TestPass123!"
    first_name: str = "Test"
    last_name: str = "User"
    role: str = "operator"


@dataclass
class SyntheticScenario:
    title: str
    description: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    priority: str = "P2"


@dataclass
class SyntheticFeature:
    name: str
    content: str
    scenarios: list[SyntheticScenario] = field(default_factory=list)


class SyntheticDataGenerator:
    """Deterministic yet varied test data generator with optional seed for reproducibility."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"{self._counter:04d}"

    def _random_string(self, length: int = 8) -> str:
        return "".join(self._rng.choices(string.ascii_lowercase, k=length))

    def user(self, role: str = "operator") -> SyntheticUser:
        uid = self._next_id()
        return SyntheticUser(
            email=f"synth_{uid}_{self._random_string(4)}@test.bgtest.dev",
            first_name=f"User{uid}",
            last_name=f"Test{uid}",
            role=role,
        )

    def scenario(self, step_count: int = 3, tags: list[str] | None = None) -> SyntheticScenario:
        sid = self._next_id()
        steps = [
            {"order": i, "text": f"Adım {i + 1}: {self._random_string(12)}"}
            for i in range(step_count)
        ]
        return SyntheticScenario(
            title=f"Sentetik Senaryo {sid}",
            description=f"Otomatik üretilmiş test senaryosu {sid}",
            steps=steps,
            tags=tags or [f"syn-{sid}"],
            priority=self._rng.choice(["P1", "P2", "P3"]),
        )

    def feature(self, scenario_count: int = 2) -> SyntheticFeature:
        fid = self._next_id()
        scenarios = [self.scenario() for _ in range(scenario_count)]
        gherkin_lines = [f"Feature: Sentetik Feature {fid}", ""]
        for sc in scenarios:
            gherkin_lines.append(f"  Scenario: {sc.title}")
            for step in sc.steps:
                prefix = "Given" if step["order"] == 0 else "When" if step["order"] < len(sc.steps) - 1 else "Then"
                gherkin_lines.append(f"    {prefix} {step['text']}")
            gherkin_lines.append("")
        return SyntheticFeature(
            name=f"Sentetik Feature {fid}",
            content="\n".join(gherkin_lines),
            scenarios=scenarios,
        )

    def bulk_scenarios(self, count: int = 10) -> list[SyntheticScenario]:
        return [self.scenario(step_count=self._rng.randint(2, 8)) for _ in range(count)]

    def execution_payload(self, scenario_ids: list[str] | None = None) -> dict[str, Any]:
        eid = self._next_id()
        return {
            "name": f"Sentetik Koşum {eid}",
            "scenario_ids": scenario_ids or [],
            "scheduled_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
        }
