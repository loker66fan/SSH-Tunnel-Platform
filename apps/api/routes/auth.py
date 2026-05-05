
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from modules.auth.password import PasswordAuthProvider
from modules.auth.base import AuthRequest
from modules.auth.mfa.totp import TOTPProvider
from infra.db.sqlite import db
from modules.acl.evaluator import acl_evaluator
from modules.audit.logger import audit_logger
from modules.audit.models import AuditLog

router = APIRouter()
auth_provider = PasswordAuthProvider()
totp_provider = TOTPProvider()
AUDIT_RETENTION_OPTIONS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}


class AuditCleanupRequest(BaseModel):
    retention: str

@router.post("/register")
async def register(request: AuthRequest):
    try:
        await db.create_user(request.username, request.password)
        await acl_evaluator.load_policies()
        await audit_logger.log(AuditLog(
            user=request.username,
            action="register",
            resource="system",
            status="success"
        ))
        return {
            "message": "User created",
            "token": "dummy-token-for-mvp",
            "username": request.username
        }
    except Exception as e:
        await audit_logger.log(AuditLog(
            user=request.username,
            action="register",
            resource="system",
            status="failed",
            details=str(e)
        ))
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(request: AuthRequest):
    # 1. Validate password
    if not await auth_provider.authenticate(request):
        await audit_logger.log(AuditLog(
            user=request.username,
            action="login",
            resource="system",
            status="failed",
            details="Invalid credentials"
        ))
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 2. Check MFA
    # mfa_secret = await db.get_mfa_secret(request.username)
    # if mfa_secret:
    #     if not request.mfa_code:
    #         await audit_logger.log(AuditLog(
    #             user=request.username,
    #             action="login_mfa_pending",
    #             resource="system",
    #             status="success"
    #         ))
    #         raise HTTPException(status_code=401, detail="MFA_REQUIRED")
    #     if not await totp_provider.verify(mfa_secret, request.mfa_code):
    #         await audit_logger.log(AuditLog(
    #             user=request.username,
    #             action="login_mfa",
    #             resource="system",
    #             status="failed",
    #             details="Invalid MFA code"
    #         ))
    #         raise HTTPException(status_code=401, detail="Invalid MFA code")
            
    await audit_logger.log(AuditLog(
        user=request.username,
        action="login",
        resource="system",
        status="success"
    ))
    return {"message": "Login successful", "token": "dummy-token-for-mvp", "username": request.username}

@router.post("/mfa/setup")
async def setup_mfa(username: str):
    # For MVP, just return a secret for the user to add to their app
    # In a real app, this would be a pending MFA that needs verification before activation
    secret = await totp_provider.generate_secret()
    await db.set_mfa_secret(username, secret)
    uri = totp_provider.get_provisioning_uri(secret, username)
    qr_code = totp_provider.generate_qr_code_base64(uri)
    return {
        "secret": secret, 
        "uri": uri,
        "qr_code": f"data:image/png;base64,{qr_code}"
    }

class MFAVerifyRequest(BaseModel):
    username: str
    code: str

@router.post("/mfa/verify")
async def verify_mfa(request: MFAVerifyRequest):
    mfa_secret = await db.get_mfa_secret(request.username)
    if not mfa_secret:
        raise HTTPException(status_code=404, detail="MFA not set up for this user")
    
    if await totp_provider.verify(mfa_secret, request.code):
        await audit_logger.log(AuditLog(
            user=request.username,
            action="mfa_verify",
            resource="system",
            status="success"
        ))
        return {"message": "MFA verified successfully"}
    else:
        await audit_logger.log(AuditLog(
            user=request.username,
            action="mfa_verify",
            resource="system",
            status="failed",
            details="Invalid code"
        ))
        raise HTTPException(status_code=400, detail="Invalid MFA code")

@router.get("/logs")
async def get_audit_logs(x_user: str = Header("user")):
    if x_user != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return {"logs": await db.list_audit_logs(limit=100)}


@router.post("/logs/cleanup")
async def cleanup_audit_logs(request: AuditCleanupRequest, x_user: str = Header("user")):
    if x_user != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    retention_delta = AUDIT_RETENTION_OPTIONS.get(request.retention)
    if retention_delta is None:
        raise HTTPException(status_code=400, detail="Unsupported retention option")

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
