"""
Projects infrastructure layer — persistence + cross-context adapters.

İki repo implementasyonu sunulur:
- InMemoryProjectRepository: test/dev için, sıfır dış bağımlılık.
- SqlAlchemyProjectRepository: production (Postgres), async session bağımlı.

Ayrıca scenarios context'in ihtiyaç duyduğu `ProjectExistsCheck` protokolünü
karşılayan adapter buradadır (cross-context guard composition root'ta
inject edilir).
"""

from .in_memory_repository import InMemoryProjectRepository
from .sql_repository import SqlAlchemyProjectRepository, ProjectRow
from .project_check_adapter import ProjectExistsCheckAdapter

__all__ = [
    "InMemoryProjectRepository",
    "SqlAlchemyProjectRepository",
    "ProjectRow",
    "ProjectExistsCheckAdapter",
]
