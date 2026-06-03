"""Audit loglama yardımcıları — dekoratör ve context manager."""

from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Callable, Optional, TypeVar

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.utils import client_ip

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def audit_action(
    action: str,
    *,
    resource_type: str,
    resource_id_attr: str = "id",
    payload_attrs: Optional[list[str]] = None,
) -> Callable[[F], F]:
    """Route handler'ı sonrasında otomatik audit kaydı oluşturan dekoratör.

    Dekoratör; handler'ın dönüş değerinden ``resource_id_attr`` ile belirtilen
    alanı okur. ``db``, ``user`` ve opsiyonel ``request`` parametrelerini
    handler imzasından otomatik bulur.

    Kullanım::

        @router.post("", response_model=JobOut)
        @audit_action("job.enqueue", resource_type="generation_job")
        def enqueue_job(body: JobCreate, request: Request,
                        db: Annotated[Session, Depends(get_db)],
                        user: Annotated[User, Depends(get_current_user)]) -> Job:
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            _emit(func, args, kwargs, result, action, resource_type,
                  resource_id_attr, payload_attrs)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


def _emit(
    func: Callable,
    args: tuple,
    kwargs: dict,
    result: Any,
    action: str,
    resource_type: str,
    resource_id_attr: str,
    payload_attrs: Optional[list[str]],
) -> None:
    """Güvenli log — hata durumunda kırılmaz."""
    try:
        from app.domains.audit.service import log_audit

        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        params = bound.arguments

        db: Optional[Session] = params.get("db")
        user = params.get("user")
        req: Optional[Request] = params.get("request")

        if db is None or user is None:
            logger.warning("audit_action: db veya user bulunamadı, kayıt atlandı")
            return

        resource_id = str(getattr(result, resource_id_attr, None) or "")
        payload: dict[str, Any] = {}
        if payload_attrs:
            for attr in payload_attrs:
                val = getattr(result, attr, None)
                if val is not None:
                    payload[attr] = val

        log_audit(
            db,
            actor_user_id=str(user.id),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id or None,
            payload=payload or None,
            ip=client_ip(req) if req else None,
        )
    except Exception:
        logger.exception("audit_action: log_audit çağrısı başarısız")
