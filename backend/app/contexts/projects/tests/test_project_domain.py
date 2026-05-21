"""
Project domain unit tests.
"""

import pytest

from app.contexts.projects.domain.project import (
    ProductFamily,
    Project,
    ProjectId,
    ProjectName,
    ProjectStatus,
)
from app.contexts.projects.domain.events import (
    ProjectArchived,
    ProjectCreated,
    ProjectProductFamilyAssigned,
    ProjectRenamed,
    ProjectRestored,
)


class TestProjectName:
    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="boş"):
            ProjectName("")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValueError, match="boş"):
            ProjectName("   ")

    def test_too_long_rejected(self):
        with pytest.raises(ValueError, match="255"):
            ProjectName("x" * 256)

    def test_valid_accepted(self):
        n = ProjectName("Neurex QA Test")
        assert str(n) == "Neurex QA Test"


class TestProjectCreation:
    def test_create_emits_event(self):
        p = Project.create(
            name=ProjectName("Demo"),
            description="A demo",
            base_url="https://demo.example.com",
            product_family=ProductFamily.WEB,
        )
        assert str(p.name) == "Demo"
        assert p.status == ProjectStatus.ACTIVE
        assert p.product_family == ProductFamily.WEB
        events = p.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ProjectCreated)
        assert events[0].product_family == "web"

    def test_create_without_product_family(self):
        p = Project.create(name=ProjectName("X"))
        events = p.pull_events()
        assert events[0].product_family is None


class TestProjectBehavior:
    def _new(self) -> Project:
        return Project.create(name=ProjectName("Original"))

    def test_rename_emits_event(self):
        p = self._new()
        _ = p.pull_events()

        p.rename(ProjectName("Renamed"))
        events = p.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ProjectRenamed)
        assert events[0].old_name == "Original"
        assert events[0].new_name == "Renamed"

    def test_rename_to_same_name_no_event(self):
        p = self._new()
        _ = p.pull_events()
        p.rename(ProjectName("Original"))
        assert p.pull_events() == []

    def test_archive_emits_event(self):
        p = self._new()
        _ = p.pull_events()
        p.archive(reason="completed")
        events = p.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ProjectArchived)
        assert events[0].reason == "completed"
        assert p.status == ProjectStatus.ARCHIVED

    def test_archive_twice_no_extra_event(self):
        p = self._new()
        p.archive()
        _ = p.pull_events()
        p.archive()
        assert p.pull_events() == []

    def test_cannot_rename_archived(self):
        p = self._new()
        p.archive()
        with pytest.raises(ValueError, match="Arşivlenmiş"):
            p.rename(ProjectName("New"))

    def test_restore_archived(self):
        p = self._new()
        p.archive()
        _ = p.pull_events()
        p.restore()
        assert p.status == ProjectStatus.ACTIVE
        events = p.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ProjectRestored)

    def test_assign_product_family(self):
        p = self._new()
        _ = p.pull_events()
        p.assign_product_family(ProductFamily.MOBILE)
        events = p.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ProjectProductFamilyAssigned)
        assert events[0].old_family is None
        assert events[0].new_family == "mobile"

    def test_reassign_product_family(self):
        p = self._new()
        p.assign_product_family(ProductFamily.MOBILE)
        _ = p.pull_events()
        p.assign_product_family(ProductFamily.WEB)
        events = p.pull_events()
        assert events[0].old_family == "mobile"
        assert events[0].new_family == "web"

    def test_cannot_assign_family_archived(self):
        p = self._new()
        p.archive()
        with pytest.raises(ValueError, match="Arşivlenmiş"):
            p.assign_product_family(ProductFamily.WEB)
