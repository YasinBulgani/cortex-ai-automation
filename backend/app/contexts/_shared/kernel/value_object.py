"""
Value Object base.

Identity'siz, immutable, value-equality değerler.
Email, Money, DateRange, etc.

Kullanım:
    @dataclass(frozen=True, slots=True)
    class Email(ValueObject):
        value: str

        def __post_init__(self):
            if "@" not in self.value:
                raise ValueError(f"Geçersiz email: {self.value}")
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValueObject:
    """Marker class — immutable, value-equality."""
    pass
