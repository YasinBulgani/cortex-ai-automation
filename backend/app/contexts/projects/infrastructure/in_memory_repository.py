"""
In-memory project repository — testler ve local dev için.

Thread-safe değil, persistence yok, restart'ta sıfırlanır. Production'a
SqlAlchemyProjectRepository kullan.
"""

from __future__ import annotations

from app.contexts.projects.application import ProjectRepository
from app.contexts.projects.domain import Project, ProjectId, ProjectName


class InMemoryProjectRepository(ProjectRepository):
    """ProjectRepository in-memory implementasyonu."""

    def __init__(self):
        self._by_id: dict[ProjectId, Project] = {}
        self._by_name: dict[str, ProjectId] = {}

    async def get(self, project_id: ProjectId) -> Project | None:
        return self._by_id.get(project_id)

    async def get_by_name(self, name: ProjectName) -> Project | None:
        pid = self._by_name.get(str(name))
        return self._by_id.get(pid) if pid else None

    async def save(self, project: Project) -> None:
        # Eski isim varsa index'i temizle (rename senaryosu)
        for name, pid in list(self._by_name.items()):
            if pid == project.id and name != str(project.name):
                del self._by_name[name]
        self._by_id[project.id] = project
        self._by_name[str(project.name)] = project.id

    # Yardımcı (test'ler için)
    def clear(self) -> None:
        self._by_id.clear()
        self._by_name.clear()

    def __len__(self) -> int:
        return len(self._by_id)
