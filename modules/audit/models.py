
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

class AuditLog(BaseModel):
    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user: str
    action: str
    resource: str
    status: str
    details: Optional[str] = None
