"""
Projects application layer — CQRS command handlers + queries.

Domain logic'i orchestrate eder; HTTP/CLI'dan bağımsız.
Repository ve outbox Protocol arayüzleri üzerinden bağlanır → test-driven.
"""

from .create_project import CreateProjectCommand, CreateProjectHandler
from .rename_project import RenameProjectCommand, RenameProjectHandler
from .archive_project import (
    ArchiveProjectCommand,
    ArchiveProjectHandler,
    RestoreProjectCommand,
    RestoreProjectHandler,
)
from .repositories import ProjectRepository

__all__ = [
    "ProjectRepository",
    "CreateProjectCommand", "CreateProjectHandler",
    "RenameProjectCommand", "RenameProjectHandler",
    "ArchiveProjectCommand", "ArchiveProjectHandler",
    "RestoreProjectCommand", "RestoreProjectHandler",
]
