
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AuditLog(BaseModel):
    id: Optional[str] = None
    timestamp: datetime = datetime.now()
    user: str
    action: str
    resource: str
    status: str
    details: Optional[str] = None
