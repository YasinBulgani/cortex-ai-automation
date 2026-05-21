"""
Shared Kernel — domain'ler arası ortak primitive'ler.

Aggregate base, value object base, repository pattern, domain event base.
Tüm bounded context'ler bunu kullanır. Cross-context bağımlılık yoktur,
sadece bu kernel'ı paylaşırlar.
"""

from .aggregate import AggregateRoot
from .value_object import ValueObject
from .repository import Repository
from .events import DomainEvent
from .identifiers import EntityId

__all__ = [
    "AggregateRoot",
    "ValueObject",
    "Repository",
    "DomainEvent",
    "EntityId",
]
