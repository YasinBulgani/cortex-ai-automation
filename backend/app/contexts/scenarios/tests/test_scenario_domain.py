"""Scenario domain unit tests — state machine + business rules."""

import pytest
from uuid import uuid4

from app.contexts.scenarios.domain.scenario import (
    Scenario,
    ScenarioStatus,
    ScenarioStep,
    ScenarioTitle,
    StepType,
)
from app.contexts.scenarios.domain.events import (
    ScenarioApproved,
    ScenarioArchived,
    ScenarioCreated,
    ScenarioPublished,
    ScenarioRejected,
    ScenarioStepAdded,
    ScenarioStepRemoved,
)


class TestScenarioTitle:
    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="boş"):
            ScenarioTitle("")

    def test_too_long_rejected(self):
        with pytest.raises(ValueError, match="500"):
            ScenarioTitle("x" * 501)


class TestScenarioStep:
    def test_empty_text_rejected(self):
        with pytest.raises(ValueError, match="boş"):
            ScenarioStep(type=StepType.GIVEN, text="", order=1)

    def test_negative_order_rejected(self):
        with pytest.raises(ValueError, match="negatif"):
            ScenarioStep(type=StepType.GIVEN, text="x", order=-1)


class TestScenarioCreation:
    def test_create(self):
        s = Scenario.create(project_id=uuid4(), title=ScenarioTitle("Login flow"))
        assert s.status == ScenarioStatus.DRAFT
        assert s.steps == []
        events = s.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ScenarioCreated)


class TestScenarioSteps:
    def _new(self) -> Scenario:
        return Scenario.create(project_id=uuid4(), title=ScenarioTitle("Test"))

    def test_add_step(self):
        s = self._new()
        _ = s.pull_events()
        s.add_step(ScenarioStep(type=StepType.GIVEN, text="user logged in", order=1))
        assert len(s.steps) == 1
        events = s.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ScenarioStepAdded)

    def test_order_conflict_rejected(self):
        s = self._new()
        s.add_step(ScenarioStep(StepType.GIVEN, "a", 1))
        with pytest.raises(ValueError, match="kullanımda"):
            s.add_step(ScenarioStep(StepType.WHEN, "b", 1))

    def test_remove_step(self):
        s = self._new()
        s.add_step(ScenarioStep(StepType.GIVEN, "a", 1))
        s.add_step(ScenarioStep(StepType.WHEN, "b", 2))
        _ = s.pull_events()

        s.remove_step(1)
        assert len(s.steps) == 1
        events = s.pull_events()
        assert isinstance(events[0], ScenarioStepRemoved)

    def test_remove_nonexistent_step_noop(self):
        s = self._new()
        _ = s.pull_events()
        s.remove_step(999)  # nonexistent
        assert s.pull_events() == []

    def test_step_sorted_by_order(self):
        s = self._new()
        s.add_step(ScenarioStep(StepType.THEN, "c", 3))
        s.add_step(ScenarioStep(StepType.GIVEN, "a", 1))
        s.add_step(ScenarioStep(StepType.WHEN, "b", 2))
        orders = [step.order for step in s.steps]
        assert orders == [1, 2, 3]

    def test_cannot_add_step_when_approved(self):
        s = self._new()
        s.add_step(ScenarioStep(StepType.GIVEN, "x", 1))
        s.submit_for_review()
        s.approve("yasin")
        with pytest.raises(ValueError, match="Step eklenemez"):
            s.add_step(ScenarioStep(StepType.WHEN, "y", 2))


class TestStateMachine:
    def _ready_for_review(self) -> Scenario:
        s = Scenario.create(project_id=uuid4(), title=ScenarioTitle("X"))
        s.add_step(ScenarioStep(StepType.GIVEN, "step", 1))
        return s

    def test_submit_for_review_requires_steps(self):
        s = Scenario.create(project_id=uuid4(), title=ScenarioTitle("X"))
        with pytest.raises(ValueError, match="Step'siz"):
            s.submit_for_review()

    def test_full_happy_path(self):
        s = self._ready_for_review()
        s.submit_for_review()
        s.approve("yasin")
        s.publish()
        assert s.status == ScenarioStatus.PUBLISHED

    def test_reject_returns_to_draft(self):
        s = self._ready_for_review()
        s.submit_for_review()
        s.reject("yasin", "needs more steps")
        assert s.status == ScenarioStatus.REJECTED
        # Can edit again
        s.add_step(ScenarioStep(StepType.WHEN, "y", 2))
        assert len(s.steps) == 2

    def test_cannot_publish_directly_from_draft(self):
        s = self._ready_for_review()
        with pytest.raises(ValueError, match="Sadece onaylı"):
            s.publish()

    def test_cannot_publish_from_review(self):
        s = self._ready_for_review()
        s.submit_for_review()
        with pytest.raises(ValueError, match="Sadece onaylı"):
            s.publish()

    def test_published_scenario_terminal_only_archive(self):
        s = self._ready_for_review()
        s.submit_for_review()
        s.approve("y")
        s.publish()
        # Cannot go back
        with pytest.raises(ValueError, match="Geçersiz state"):
            s.approve("y")
        # Can archive
        s.archive()
        assert s.status == ScenarioStatus.ARCHIVED

    def test_archived_is_terminal(self):
        s = self._ready_for_review()
        s.archive()
        with pytest.raises(ValueError, match="Geçersiz state"):
            s.submit_for_review()
