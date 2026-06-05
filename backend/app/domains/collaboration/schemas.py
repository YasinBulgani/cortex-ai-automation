"""Collaboration domain için Pydantic şemaları.

Request şemaları:
    * MentionPreviewRequest : @mention önizleme isteği

Response şemaları:
    * PresenceMember        : odadaki tek bir kullanıcı
    * PresenceResponse      : oda varlık durumu
    * ResolvedUser          : çözümlenmiş @mention kullanıcısı
    * MentionPreviewResponse: @mention önizleme sonucu
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ── Request şemaları ──────────────────────────────────────────────────────────

class MentionPreviewRequest(BaseModel):
    """POST /collab/mentions/preview request body."""

    body: str = Field(..., description="@mention içerebilen yorum metni")


# ── Response şemaları ─────────────────────────────────────────────────────────

class PresenceMember(BaseModel):
    """Odada aktif olan tek bir kullanıcı."""

    user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class PresenceResponse(BaseModel):
    """GET /collab/presence/{room} yanıtı."""

    room: str
    members: List[PresenceMember]


class ResolvedUser(BaseModel):
    """Çözümlenmiş @mention kullanıcısı."""

    id: str
    email: str
    full_name: Optional[str] = None


class MentionPreviewResponse(BaseModel):
    """POST /collab/mentions/preview yanıtı."""

    handles: List[str] = Field(default_factory=list, description="Metinde bulunan @handle'lar")
    resolved: List[ResolvedUser] = Field(default_factory=list, description="Kullanıcı kaydına çözümlenenler")
