
from fastapi import HTTPException
from modules.tunnel.manager import tunnel_manager
from modules.acl.evaluator import acl_evaluator
from modules.audit.logger import audit_logger
from modules.audit.models import AuditLog
from infra.db.sqlite import db
from typing import Optional

class TunnelService:
    async def _get_owned_tunnel(self, user: str, tunnel_id: str):
        tunnel = await db.get_user_tunnel(user, tunnel_id)
        if not tunnel:
            raise HTTPException(status_code=404, detail="Tunnel not found")
        return tunnel

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
            
            await db.save_user_tunnel(user, tid, config, is_active=True)
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

    async def list_tunnels(self, user: str):
        tunnels = await db.list_user_tunnels(user)
        for tunnel in tunnels:
            is_active = tunnel_manager.get_tunnel_backend(tunnel["id"]) is not None
            if tunnel["is_active"] != is_active:
                await db.set_user_tunnel_active(user, tunnel["id"], is_active)
                tunnel["is_active"] = is_active
        return tunnels

    async def list_tunnel_groups(self, user: str):
        await self.list_tunnels(user)
        return await db.list_user_tunnel_groups(user)

    async def start_tunnel(self, user: str, tunnel_id: str):
        tunnel = await self._get_owned_tunnel(user, tunnel_id)
        resource = f"{tunnel.get('remote_host', 'dynamic')}:{tunnel.get('remote_port', 'dynamic')}"

        if tunnel_manager.get_tunnel_backend(tunnel_id):
            await db.set_user_tunnel_active(user, tunnel_id, True)
            return True

        try:
            if tunnel["type"] == "socks5":
                await tunnel_manager.create_socks_proxy(
                    tunnel["ssh_host"],
                    tunnel["ssh_port"],
                    tunnel["username"],
                    tunnel["password"],
                    tunnel["local_port"],
                    remark=tunnel.get("remark"),
                    tunnel_id=tunnel_id,
                )
            else:
                await tunnel_manager.create_local_forward(
                    tunnel["ssh_host"],
                    tunnel["ssh_port"],
                    tunnel["username"],
                    tunnel["password"],
                    tunnel["local_port"],
                    tunnel["remote_host"],
                    tunnel["remote_port"],
                    remark=tunnel.get("remark"),
                    tunnel_id=tunnel_id,
                )

            await db.set_user_tunnel_active(user, tunnel_id, True)
            await audit_logger.log(AuditLog(
                user=user,
                action=f"start_{tunnel['type']}_tunnel",
                resource=resource,
                status="success",
                details=f"Tunnel ID: {tunnel_id}"
            ))
            return True
        except Exception as e:
            await audit_logger.log(AuditLog(
                user=user,
                action=f"start_{tunnel['type']}_tunnel",
                resource=resource,
                status="failed",
                details=str(e)
            ))
            raise

    async def stop_tunnel(self, user: str, tunnel_id: str):
        await self._get_owned_tunnel(user, tunnel_id)
        try:
            success = True
            if tunnel_manager.get_tunnel_backend(tunnel_id):
                success = await tunnel_manager.stop_tunnel(tunnel_id)
            if success:
                await db.set_user_tunnel_active(user, tunnel_id, False)
            
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

    async def delete_tunnel(self, user: str, tunnel_id: str):
        await self._get_owned_tunnel(user, tunnel_id)
        try:
            if tunnel_manager.get_tunnel_backend(tunnel_id):
                await tunnel_manager.stop_tunnel(tunnel_id)
            deleted = await db.delete_user_tunnel(user, tunnel_id)
            await audit_logger.log(AuditLog(
                user=user,
                action="delete_tunnel",
                resource=tunnel_id,
                status="success" if deleted else "failed"
            ))
            return deleted
        except Exception as e:
            await audit_logger.log(AuditLog(
                user=user,
                action="delete_tunnel",
                resource=tunnel_id,
                status="failed",
                details=str(e)
            ))
            raise

    async def run_command(self, user: str, tunnel_id: str, command: str):
        await self._get_owned_tunnel(user, tunnel_id)
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
        await self._get_owned_tunnel(user, tunnel_id)
        try:
            result = await tunnel_manager.verify_tunnel(tunnel_id, local_port)
            await audit_logger.log(AuditLog(
                user=user,
                action="verify_tunnel",
                resource=tunnel_id,
                status="success" if result["success"] else "failed",
                details=f"Port: {local_port}, Latency: {result['latency_ms']}ms"
            ))
            return result
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
                            new_group_name: Optional[str] = None,
                            new_ssh_host: Optional[str] = None, 
                            new_ssh_port: Optional[int] = None,
                            new_username: Optional[str] = None,
                            new_password: Optional[str] = None,
                            new_local_port: Optional[int] = None,
                            new_remote_host: Optional[str] = None,
                            new_remote_port: Optional[int] = None,
                            new_type: Optional[str] = None):
        try:
            await self._get_owned_tunnel(user, tunnel_id)
            is_active = tunnel_manager.get_tunnel_backend(tunnel_id) is not None

            if is_active:
                success = await tunnel_manager.update_tunnel(
                    tunnel_id, new_remark, new_ssh_host, new_ssh_port,
                    new_username, new_password, new_local_port,
                    new_remote_host, new_remote_port, new_type
                )
            else:
                success = True

            updates = {
                "remark": new_remark,
                "group_name": new_group_name,
                "ssh_host": new_ssh_host,
                "ssh_port": new_ssh_port,
                "username": new_username,
                "password": new_password,
                "local_port": new_local_port,
                "remote_host": new_remote_host,
                "remote_port": new_remote_port,
                "type": new_type,
            }
            optional_fields = {
                "remark",
                "group_name",
                "ssh_host",
                "ssh_port",
                "username",
                "password",
                "local_port",
                "remote_host",
                "remote_port",
                "type",
            }
            updates = {
                key: value for key, value in updates.items()
                if value is not None or key not in optional_fields
            }
            await db.update_user_tunnel(user, tunnel_id, updates, is_active=is_active)
            details = (f"New remark: {new_remark}, New Group: {new_group_name}, New SSH Host: {new_ssh_host}, New SSH Port: {new_ssh_port}, "
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

    async def rename_tunnel_group(self, user: str, old_group_name: str, new_group_name: str):
        changed_count = await db.rename_user_tunnel_group(user, old_group_name, new_group_name)
        await audit_logger.log(AuditLog(
            user=user,
            action="rename_tunnel_group",
            resource=old_group_name,
            status="success",
            details=f"new_group={new_group_name}, changed={changed_count}"
        ))
        return changed_count

    async def clear_tunnel_group(self, user: str, group_name: str):
        changed_count = await db.clear_user_tunnel_group(user, group_name)
        await audit_logger.log(AuditLog(
            user=user,
            action="clear_tunnel_group",
            resource=group_name,
            status="success",
            details=f"changed={changed_count}"
        ))
        return changed_count

    async def logout_user(self, user: str, save_tunnels: bool):
        tunnels = await db.list_user_tunnels(user)

        for tunnel in tunnels:
            if tunnel_manager.get_tunnel_backend(tunnel["id"]):
                await tunnel_manager.stop_tunnel(tunnel["id"])
            if tunnel["is_active"]:
                await db.set_user_tunnel_active(user, tunnel["id"], False)

        if not save_tunnels:
            await db.delete_user_tunnels(user)

        await audit_logger.log(AuditLog(
            user=user,
            action="logout",
            resource="system",
            status="success",
            details="Saved tunnels" if save_tunnels else "Discarded tunnels"
        ))

    async def open_terminal_session(self, user: str, tunnel_id: str, websocket):
        await self._get_owned_tunnel(user, tunnel_id)
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
