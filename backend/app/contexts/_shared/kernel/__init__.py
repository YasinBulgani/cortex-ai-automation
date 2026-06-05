"""
Shared Kernel — domain'ler arası ortak primitive'ler.

Aggregate base, value object base, repository pattern, domain event base.
Tüm bounded context'ler bunu kullanır. Cross-context bağımlılık yoktur,
sadece bu kernel'ı paylaşırlar.
"""

from .aggregate import AggregateRoot
from .events import DomainEvent
from .identifiers import EntityId
from .repository import Repository
from .value_object import ValueObject

__all__ = [
    "AggregateRoot",
    "ValueObject",
    "Repository",
    "DomainEvent",
    "EntityId",
]
