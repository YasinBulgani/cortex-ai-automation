"""Paylaşılan yardımcı fonksiyonlar — domain bağımsız."""

from __future__ import annotations

from typing import Optional

from fastapi import Request


def client_ip(request: Request) -> Optional[str]:
    """İstemci IP adresini döner; bilinmiyorsa None."""
    if request.client:
        return request.client.host
    return None
