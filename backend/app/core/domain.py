"""Domain router fabrikası — standart bağımlılık zinciri ile APIRouter üretir.

Yeni domain router'ları için kullanım::

    from app.core.domain import DomainRouter

    router = DomainRouter("my-feature", require_auth=True)

    @router.get("")
    def list_things(...): ...

Mevcut router'lar eski ``APIRouter`` ile çalışmaya devam eder; bu sınıf
yalnızca yeni domain'ler için tercih edilmeli.
"""

from __future__ import annotations

from typing import Callable, Optional

from fastapi import APIRouter, Depends

from app.deps import get_current_user


def DomainRouter(
    name: str,
    *,
    require_auth: bool = True,
    prefix_override: Optional[str] = None,
    tags_override: Optional[list[str]] = None,
    **kwargs,
) -> APIRouter:
    """Standart prefix, tags ve auth dependency zinciri ile APIRouter üretir.

    Args:
        name: Domain adı — hem prefix hem tag olarak kullanılır.
              Örn: ``"jobs"`` → prefix ``/jobs``, tag ``["jobs"]``.
        require_auth: ``True`` (varsayılan) ise tüm endpoint'lere
                      ``get_current_user`` dependency'si eklenir.
        prefix_override: Varsayılan ``/{name}`` prefix'ini geçersiz kılar.
        tags_override: Varsayılan ``[name]`` tag listesini geçersiz kılar.
        **kwargs: Doğrudan ``APIRouter``'a iletilir.
    """
    prefix = prefix_override if prefix_override is not None else f"/{name}"
    tags = tags_override if tags_override is not None else [name]
    dependencies: list = []

    if require_auth:
        dependencies.append(Depends(get_current_user))

    return APIRouter(
        prefix=prefix,
        tags=tags,
        dependencies=dependencies,
        **kwargs,
    )
