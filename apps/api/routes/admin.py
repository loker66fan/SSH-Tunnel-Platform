
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from infra.db.sqlite import db
from modules.audit.logger import audit_logger
from modules.audit.models import AuditLog

router = APIRouter()
AUDIT_RETENTION_OPTIONS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}


class AuditCleanupRequest(BaseModel):
    retention: str

@router.get("/audit/logs")
async def get_audit_logs(x_user: str = Header("user")):
    if x_user != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        return await db.list_audit_logs(limit=100)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audit/logs/cleanup")
async def cleanup_audit_logs(request: AuditCleanupRequest, x_user: str = Header("user")):
    if x_user != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    retention_delta = AUDIT_RETENTION_OPTIONS.get(request.retention)
    if retention_delta is None:
        raise HTTPException(status_code=400, detail="Unsupported retention option")

    try:
        cutoff = datetime.now(timezone.utc) - retention_delta
        deleted_count = await db.delete_audit_logs_older_than(cutoff.isoformat())
        await audit_logger.log(AuditLog(
            user=x_user,
            action="cleanup_audit_logs",
            resource="audit_logs",
            status="success",
            details=f"retention={request.retention}, deleted={deleted_count}"
        ))
        return {"deleted_count": deleted_count, "retention": request.retention}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
