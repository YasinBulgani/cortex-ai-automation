from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class WSMessage(BaseModel):
    type: str
    payload: dict[str, Any] = {}
    timestamp: Optional[str] = None
