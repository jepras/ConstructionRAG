from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class RequestContext(BaseModel):
    request_id: str
    user_id: Optional[str] = None
    is_authenticated: bool = False
    org_id: Optional[str] = None
    roles: List[str] = []
