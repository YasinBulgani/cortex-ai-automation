"""Automation Engine proxy — forwards requests to the Flask engine service."""

import logging
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automation", tags=["automation"])

ENGINE_BASE = os.environ.get("ENGINE_BASE_URL", "http://127.0.0.1:5001")
_INTERNAL_KEY = os.environ.get("ENGINE_INTERNAL_KEY", "bgts-internal-key-change-me")
_ALLOWED_PROXY_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}
_ALLOWED_PROXY_PATH_PREFIXES = (
    "api/features",
    "api/run",
    "api/ai/",
    "api/manual-tests",
    "api/pipeline/",
    "api/runner/",
    "api/banking/",
    "api/accessibility/",
    "api/recorder/",
)
_FORWARDED_REQUEST_HEADERS = {
    "accept",
    "accept-language",
    "content-type",
    "user-agent",
    "x-request-id",
}


def _normalize_proxy_path(path: str) -> str:
    normalized = path.strip().lstrip("/")
    if not normalized:
        raise HTTPException(status_code=400, detail="Proxy path bos olamaz")
    if any(part == ".." for part in normalized.split("/")):
        raise HTTPException(status_code=400, detail="Gecersiz proxy path")
    return normalized


def _is_allowed_proxy_path(path: str) -> bool:
    for allowed in _ALLOWED_PROXY_PATH_PREFIXES:
        if allowed.endswith("/") and path.startswith(allowed):
            return True
        if path == allowed or path.startswith(f"{allowed}/"):
            return True
    return False


@router.get("/health")
async def engine_health():
    """Check automation engine health."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{ENGINE_BASE}/health",
                headers={"X-Internal-Key": _INTERNAL_KEY},
            )
            return resp.json()
    except httpx.RequestError:
        logger.warning("Automation engine health check failed for %s", ENGINE_BASE)
        return {"status": "unreachable", "engine_url": ENGINE_BASE}


@router.api_route(
    "/proxy/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False,
    dependencies=[Depends(get_current_user)],
)
async def _proxy_to_engine(path: str, request: Request):
    """
    Transparent proxy to the automation engine.
    Frontend calls  /api/v1/automation/proxy/api/features
    and this forwards to ENGINE_BASE/api/features.
    """
    if request.method.upper() not in _ALLOWED_PROXY_METHODS:
        raise HTTPException(status_code=405, detail="Method desteklenmiyor")

    normalized_path = _normalize_proxy_path(path)
    if not _is_allowed_proxy_path(normalized_path):
        raise HTTPException(status_code=403, detail="Bu proxy path'e izin verilmiyor")

    target = f"{ENGINE_BASE.rstrip('/')}/{normalized_path}"
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() in _FORWARDED_REQUEST_HEADERS
    }
    headers["x-internal-key"] = _INTERNAL_KEY

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.request(
            method=request.method,
            url=target,
            headers=headers,
            params=request.query_params,
            content=await request.body(),
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )


@router.get(
    "/proxy/{path:path}",
    operation_id="automation_proxy_get",
    dependencies=[Depends(get_current_user)],
)
async def proxy_to_engine_get(path: str, request: Request):
    """GET isteklerini otomasyon motoruna yonlendirir."""
    return await _proxy_to_engine(path, request)


@router.post(
    "/proxy/{path:path}",
    operation_id="automation_proxy_post",
    dependencies=[Depends(get_current_user)],
)
async def proxy_to_engine_post(path: str, request: Request):
    """POST isteklerini otomasyon motoruna yonlendirir."""
    return await _proxy_to_engine(path, request)


@router.put(
    "/proxy/{path:path}",
    operation_id="automation_proxy_put",
    dependencies=[Depends(get_current_user)],
)
async def proxy_to_engine_put(path: str, request: Request):
    """PUT isteklerini otomasyon motoruna yonlendirir."""
    return await _proxy_to_engine(path, request)


@router.delete(
    "/proxy/{path:path}",
    operation_id="automation_proxy_delete",
    dependencies=[Depends(get_current_user)],
)
async def proxy_to_engine_delete(path: str, request: Request):
    """DELETE isteklerini otomasyon motoruna yonlendirir."""
    return await _proxy_to_engine(path, request)


@router.patch(
    "/proxy/{path:path}",
    operation_id="automation_proxy_patch",
    dependencies=[Depends(get_current_user)],
)
async def proxy_to_engine_patch(path: str, request: Request):
    """PATCH isteklerini otomasyon motoruna yonlendirir."""
    return await _proxy_to_engine(path, request)
