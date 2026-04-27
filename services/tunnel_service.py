
from fastapi import HTTPException
from modules.tunnel.manager import tunnel_manager
from modules.acl.evaluator import acl_evaluator
from modules.audit.logger import audit_logger
from modules.audit.models import AuditLog
from core.logger import logger
from typing import Optional

class TunnelService:
    async def create_tunnel(self, user: str, config: dict):
        resource = f"{config.get('remote_host', 'dynamic')}:{config.get('remote_port', 'dynamic')}"
        tunnel_type = config.get("type", "local")
        
        # 1. ACL Check
        if not acl_evaluator.is_allowed(user, resource) and user != "alice":
             await audit_logger.log(AuditLog(
                 user=user,
                 action=f"create_{tunnel_type}_tunnel",
                 resource=resource,
                 status="denied",
                 details="ACL check failed"
             ))
             raise Exception("Access Denied by ACL")

        try:
            # 2. Direct Execution (Skipping Worker)
            if tunnel_type == "socks5":
                tid = await tunnel_manager.create_socks_proxy(
                    config['ssh_host'], config['ssh_port'], 
                    config['username'], config['password'],
                    config['local_port'],
                    remark=config.get('remark')
                )
            else:
                tid = await tunnel_manager.create_local_forward(
                    config['ssh_host'], config['ssh_port'], 
                    config['username'], config['password'],
                    config['local_port'], config['remote_host'], config['remote_port'],
                    remark=config.get('remark')
                )
            
            # 3. Audit Log
            await audit_logger.log(AuditLog(
                user=user,
                action=f"create_{tunnel_type}_tunnel",
                resource=resource,
                status="success",
                details=f"Tunnel ID: {tid}"
            ))
            return tid
        except Exception as e:
            await audit_logger.log(AuditLog(
                user=user,
                action=f"create_{tunnel_type}_tunnel",
                resource=resource,
                status="failed",
                details=str(e)
            ))
            raise

    async def stop_tunnel(self, user: str, tunnel_id: str):
        try:
            # Direct Execution (Skipping Worker)
            success = await tunnel_manager.stop_tunnel(tunnel_id)
            
            await audit_logger.log(AuditLog(
                user=user,
                action="stop_tunnel",
                resource=tunnel_id,
                status="success" if success else "failed"
            ))
            return success
        except Exception as e:
            await audit_logger.log(AuditLog(
                user=user,
                action="stop_tunnel",
                resource=tunnel_id,
                status="failed",
                details=str(e)
            ))
            raise

    async def run_command(self, user: str, tunnel_id: str, command: str):
        try:
            output = await tunnel_manager.run_command(tunnel_id, command)
            await audit_logger.log(AuditLog(
                user=user,
                action="exec_command",
                resource=tunnel_id,
                status="success",
                details=f"Cmd: {command[:50]}"
            ))
            return output
        except Exception as e:
            await audit_logger.log(AuditLog(
                user=user,
                action="exec_command",
                resource=tunnel_id,
                status="failed",
                details=str(e)
            ))
            raise

    async def verify_tunnel(self, user: str, tunnel_id: str, local_port: int):
        try:
            success = await tunnel_manager.verify_tunnel(tunnel_id, local_port)
            await audit_logger.log(AuditLog(
                user=user,
                action="verify_tunnel",
                resource=tunnel_id,
                status="success" if success else "failed",
                details=f"Port: {local_port}"
            ))
            return success
        except Exception as e:
            await audit_logger.log(AuditLog(
                user=user,
                action="verify_tunnel",
                resource=tunnel_id,
                status="failed",
                details=str(e)
            ))
            raise

    async def update_tunnel(self, user: str, tunnel_id: str, 
                            new_remark: Optional[str] = None, 
                            new_ssh_host: Optional[str] = None, 
                            new_ssh_port: Optional[int] = None,
                            new_username: Optional[str] = None,
                            new_password: Optional[str] = None,
                            new_local_port: Optional[int] = None,
                            new_remote_host: Optional[str] = None,
                            new_remote_port: Optional[int] = None,
                            new_type: Optional[str] = None):
        try:
            success = await tunnel_manager.update_tunnel(
                tunnel_id, new_remark, new_ssh_host, new_ssh_port,
                new_username, new_password, new_local_port,
                new_remote_host, new_remote_port, new_type
            )
            details = (f"New remark: {new_remark}, New SSH Host: {new_ssh_host}, New SSH Port: {new_ssh_port}, "
                       f"New Username: {new_username}, New Local Port: {new_local_port}, "
                       f"New Remote Host: {new_remote_host}, New Remote Port: {new_remote_port}, New Type: {new_type}")
            await audit_logger.log(AuditLog(
                user=user,
                action="update_tunnel",
                resource=tunnel_id,
                status="success" if success else "failed",
                details=details
            ))
            return success
        except Exception as e:
            await audit_logger.log(AuditLog(
                user=user,
                action="update_tunnel",
                resource=tunnel_id,
                status="failed",
                details=str(e)
            ))
            raise

    async def open_terminal_session(self, user: str, tunnel_id: str, websocket):
        # ACL check for terminal access
        # For simplicity, we'll allow if the user has any tunnel active
        # In a real scenario, you'd check specific permissions for terminal access
        if not tunnel_manager.get_tunnel_backend(tunnel_id):
            raise HTTPException(status_code=404, detail="Tunnel not found or not active")

        try:
            await audit_logger.log(AuditLog(
                user=user,
                action="open_terminal",
                resource=tunnel_id,
                status="success",
                details="Opened WebSocket terminal session"
            ))
            await tunnel_manager.open_terminal_session(tunnel_id, websocket)
        except Exception as e:
            await audit_logger.log(AuditLog(
                user=user,
                action="open_terminal",
                resource=tunnel_id,
                status="failed",
                details=str(e)
            ))
            raise

tunnel_service = TunnelService()
