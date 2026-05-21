"""
BcryptPasswordHasher — production PasswordHasher implementasyonu.

bcrypt sektör standardıdır: adaptive cost factor, built-in salt.
Test'lerde FakeHasher kullan (bcrypt pahalıdır, argon2 daha güçlüdür).
"""

from __future__ import annotations


class BcryptPasswordHasher:
    """PasswordHasher protocol implementasyonu (bcrypt)."""

    def __init__(self, rounds: int = 12):
        self._rounds = rounds

    def hash(self, plain: str) -> str:
        import bcrypt  # type: ignore[import-not-found]
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=self._rounds)).decode()

    def verify(self, plain: str, hashed: str) -> bool:
        import bcrypt  # type: ignore[import-not-found]
        return bcrypt.checkpw(plain.encode(), hashed.encode())


class FakePasswordHasher:
    """Test'ler için deterministik hasher (bcrypt bağımlılığı yok)."""

    def hash(self, plain: str) -> str:
        # Prefix ile real hash'ten ayırt edilebilir
        return f"fake-hash-{plain}" + "x" * max(0, 32 - len(f"fake-hash-{plain}"))

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == self.hash(plain)
