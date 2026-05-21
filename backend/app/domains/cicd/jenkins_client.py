"""Async HTTP client for talking to a Jenkins controller via its REST API.

Uses HTTP Basic auth (username + API token). Tested against Jenkins 2.x
controllers. Methods only cover what the minimum integration needs:
ping, trigger build, fetch last build status.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0)


class JenkinsClientError(Exception):
    """Raised when Jenkins returns an unexpected response."""


class JenkinsClient:
    def __init__(self, base_url: str, username: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, token)

    async def ping(self) -> dict[str, Any]:
        """Hit `/api/json` to verify the URL + credentials are valid."""
        url = f"{self.base_url}/api/json"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, auth=self.auth)
        if resp.status_code == 401:
            raise JenkinsClientError("401 Unauthorized — kullanıcı adı veya API token hatalı")
        if resp.status_code == 403:
            raise JenkinsClientError("403 Forbidden — kullanıcının yetkisi yok")
        if resp.status_code >= 400:
            raise JenkinsClientError(f"Jenkins HTTP {resp.status_code}: {resp.text[:200]}")
        try:
            data = resp.json()
        except ValueError as exc:
            raise JenkinsClientError("Jenkins JSON dönmedi (URL'i kontrol edin)") from exc
        return {
            "version": resp.headers.get("X-Jenkins", "unknown"),
            "node_name": data.get("nodeName", ""),
            "mode": data.get("mode", ""),
        }

    async def trigger_build(
        self,
        job_name: str,
        parameters: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Trigger a build. Returns the queue item URL on success."""
        safe_job = job_name.strip("/").replace(" ", "%20")
        if parameters:
            endpoint = f"{self.base_url}/job/{safe_job}/buildWithParameters"
            payload = parameters
        else:
            endpoint = f"{self.base_url}/job/{safe_job}/build"
            payload = None

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(endpoint, auth=self.auth, data=payload)

        if resp.status_code == 404:
            raise JenkinsClientError(f"Job bulunamadı: {job_name}")
        if resp.status_code in (401, 403):
            raise JenkinsClientError("Build tetikleme yetkisi yok")
        if resp.status_code not in (200, 201):
            raise JenkinsClientError(
                f"Build tetiklenemedi: HTTP {resp.status_code} — {resp.text[:200]}"
            )

        queue_url = resp.headers.get("Location", "")
        return {"queue_url": queue_url, "job": job_name}

    async def last_build(self, job_name: str) -> dict[str, Any]:
        """Return last build summary: number, status, timestamp, url."""
        safe_job = job_name.strip("/").replace(" ", "%20")
        url = f"{self.base_url}/job/{safe_job}/lastBuild/api/json"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, auth=self.auth)
        if resp.status_code == 404:
            return {"exists": False, "job": job_name}
        if resp.status_code >= 400:
            raise JenkinsClientError(
                f"Son build okunamadı: HTTP {resp.status_code} — {resp.text[:200]}"
            )
        data = resp.json()
        return {
            "exists": True,
            "job": job_name,
            "number": data.get("number"),
            "result": data.get("result"),
            "building": bool(data.get("building")),
            "duration_ms": data.get("duration"),
            "timestamp": data.get("timestamp"),
            "url": data.get("url"),
        }
