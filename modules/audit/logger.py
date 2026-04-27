
from modules.audit.models import AuditLog
from infra.db.sqlite import db
from core.logger import logger
import json

class AuditLogger:
    async def log(self, audit_log: AuditLog):
        try:
            # For now, we log to stdout via our core logger
            # and potentially save to DB
            log_msg = f"AUDIT: {audit_log.user} performed {audit_log.action} on {audit_log.resource} - Status: {audit_log.status}"
            logger.info(log_msg)
            
            # Save to database if initialized
            if db._db:
                await db._db.execute(
                    "INSERT INTO audit_logs (timestamp, user, action, resource, status, details) VALUES (?, ?, ?, ?, ?, ?)",
                    (audit_log.timestamp.isoformat(), audit_log.user, audit_log.action, 
                     audit_log.resource, audit_log.status, audit_log.details)
                )
                await db._db.commit()
        except Exception as e:
            logger.error(f"Failed to record audit log: {str(e)}")

audit_logger = AuditLogger()
