
from fastapi import APIRouter, HTTPException
from infra.db.sqlite import db

router = APIRouter()

@router.get("/audit/logs")
async def get_audit_logs():
    try:
        cur = await db._db.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 100")
        rows = await cur.fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "user": r[2],
                "action": r[3],
                "resource": r[4],
                "status": r[5],
                "details": r[6]
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
