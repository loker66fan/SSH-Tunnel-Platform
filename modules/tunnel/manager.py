from modules.ssh.asyncssh_backend import AsyncSSHBackend
from core.logger import logger
import uuid
import socket
import asyncio
import time
from typing import Optional

class TunnelManager:
    def __init__(self):
        self._active_tunnels = {} # id -> backend

    def _is_port_in_use(self, port):
        # 1. 检查已管理的隧道
        for tid, backend in self._active_tunnels.items():
            if backend._tunnels:
                listener = backend._tunnels[0]
                try:
                    if hasattr(listener, 'get_port'):
                        if listener.get_port() == port:
                            return True
                    elif hasattr(listener, 'get_extra_info'):
                        addr = listener.get_extra_info('sockname')
                        if addr and addr[1] == port:
                            return True
                except:
                    pass
        
        # 2. 检查系统端口占用
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return False
            except socket.error:
                return True

    async def create_local_forward(self, host, port, username, password, local_port, remote_host, remote_port, remark: str = None):
        if self._is_port_in_use(local_port):
            raise Exception(f"Port {local_port} is already in use")
        
        tunnel_id = str(uuid.uuid4())
        backend = AsyncSSHBackend(host=host, port=port, username=username, password=password, remark=remark)
        try:
            await backend.connect(host, port, username, password)
            await backend.open_tunnel(local_port, remote_host, remote_port)
            self._active_tunnels[tunnel_id] = backend
            return tunnel_id
        except Exception as e:
            logger.error(f"Failed to create tunnel {tunnel_id}: {str(e)}")
            await backend.close()
            raise

    async def create_socks_proxy(self, host, port, username, password, local_port, remark: str = None):
        if self._is_port_in_use(local_port):
            raise Exception(f"Port {local_port} is already in use")
        
        tunnel_id = str(uuid.uuid4())
        backend = AsyncSSHBackend(host=host, port=port, username=username, password=password, remark=remark)
        try:
            await backend.connect(host, port, username, password)
            await backend.open_socks_proxy(local_port)
            self._active_tunnels[tunnel_id] = backend
            return tunnel_id
        except Exception as e:
            logger.error(f"Failed to create SOCKS proxy {tunnel_id}: {str(e)}")
            await backend.close()
            raise

    async def stop_tunnel(self, tunnel_id):
        if tunnel_id in self._active_tunnels:
            backend = self._active_tunnels.pop(tunnel_id)
            await backend.close()
            return True
        return False

    async def run_command(self, tunnel_id, command):
        if tunnel_id not in self._active_tunnels:
            raise Exception("Tunnel not found")
        backend = self._active_tunnels[tunnel_id]
        return await backend.run_command(command)

    def _check_port_with_latency(self, port):
        t0 = time.perf_counter()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            ok = s.connect_ex(('127.0.0.1', port)) == 0
        latency_ms = (time.perf_counter() - t0) * 1000
        return ok, latency_ms

    async def verify_tunnel(self, tunnel_id, local_port):
        if tunnel_id not in self._active_tunnels:
            raise Exception("Tunnel not found")
        backend = self._active_tunnels[tunnel_id]
        
        if hasattr(backend, '_is_socks') and backend._is_socks:
            if hasattr(backend, 'verify_socks'):
                ok = await backend.verify_socks(local_port)
                return {"success": ok, "latency_ms": None}
            return {"success": False, "latency_ms": None}
            
        loop = asyncio.get_running_loop()
        try:
            ok, latency_ms = await loop.run_in_executor(None, self._check_port_with_latency, local_port)
            return {"success": ok, "latency_ms": latency_ms}
        except Exception as e:
            logger.error(f"Local tunnel verification failed on port {local_port}: {str(e)}")
            return {"success": False, "latency_ms": None}

    async def update_tunnel(self, tunnel_id: str, 
                            new_remark: Optional[str] = None, 
                            new_ssh_host: Optional[str] = None, 
                            new_ssh_port: Optional[int] = None,
                            new_username: Optional[str] = None,
                            new_password: Optional[str] = None,
                            new_local_port: Optional[int] = None,
                            new_remote_host: Optional[str] = None,
                            new_remote_port: Optional[int] = None,
                            new_type: Optional[str] = None):
        if tunnel_id not in self._active_tunnels:
            return False
        backend = self._active_tunnels[tunnel_id]
        if new_remark is not None:
            backend.update_remark(new_remark)
        if new_ssh_host is not None or new_ssh_port is not None:
            backend.update_host_port(new_ssh_host, new_ssh_port)
        
        # For MVP, other parameters are not supported for live updates on an active tunnel.
        # Changing them would typically require stopping and re-creating the tunnel.
        if new_username is not None:
            logger.warning(f"Attempted to update username for active tunnel {tunnel_id}, but not supported for live update.")
        if new_password is not None:
            logger.warning(f"Attempted to update password for active tunnel {tunnel_id}, but not supported for live update.")
        if new_local_port is not None:
            logger.warning(f"Attempted to update local_port for active tunnel {tunnel_id}, but not supported for live update.")
        if new_remote_host is not None:
            logger.warning(f"Attempted to update remote_host for active tunnel {tunnel_id}, but not supported for live update.")
        if new_remote_port is not None:
            logger.warning(f"Attempted to update remote_port for active tunnel {tunnel_id}, but not supported for live update.")
        if new_type is not None:
            logger.warning(f"Attempted to update type for active tunnel {tunnel_id}, but not supported for live update.")

        return True

    def get_tunnel_backend(self, tunnel_id: str):
        return self._active_tunnels.get(tunnel_id)

    async def open_terminal_session(self, tunnel_id: str, websocket):
        backend = self._active_tunnels.get(tunnel_id)
        if not backend:
            raise Exception("Tunnel not found or not active")

        process = None
        try:
            process = await backend.open_shell(width=80, height=24)
            
            read_task = None
            write_task = None
            closed_by_error = False

            async def read_ssh_output():
                nonlocal closed_by_error
                try:
                    while True:
                        data = await process.stdout.read(4096)
                        if not data:
                            logger.info(f"SSH stdout EOF for tunnel {tunnel_id}")
                            break
                        if isinstance(data, bytes):
                            data = data.decode('utf-8', errors='ignore')
                        await websocket.send_text(data)
                except Exception as e:
                    logger.error(f"Error reading SSH stdout for tunnel {tunnel_id}: {e}")
                    closed_by_error = True
                finally:
                    try:
                        await websocket.close()
                    except:
                        pass

            async def write_ssh_input():
                nonlocal closed_by_error
                try:
                    while True:
                        message = await websocket.receive_text()
                        if process.stdin is None:
                            logger.error(f"process.stdin is None for tunnel {tunnel_id}. Cannot write to stdin.")
                            break
                        if process.stdin.is_closing():
                            logger.info(f"process.stdin is closing for tunnel {tunnel_id}. Cannot write to stdin.")
                            break
                        process.stdin.write(message)
                        await process.stdin.drain()
                except Exception as e:
                    logger.error(f"Error writing to SSH stdin for tunnel {tunnel_id}: {e}")
                    closed_by_error = True
                finally:
                    process.stdin.close()
                    try:
                        await websocket.close()
                    except:
                        pass

            read_task = asyncio.create_task(read_ssh_output())
            write_task = asyncio.create_task(write_ssh_input())

            done, pending = await asyncio.wait(
                [read_task, write_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()
                try:
                    await task
                except:
                    pass

        except Exception as e:
            logger.error(f"Failed to open terminal session for tunnel {tunnel_id}: {e}")
            raise
        finally:
            if process:
                try:
                    process.stdin.close()
                except:
                    pass
                process.close()
                try:
                    await asyncio.wait_for(process.wait_closed(), timeout=2)
                except:
                    pass
            logger.info(f"Terminal session closed for tunnel {tunnel_id}")

tunnel_manager = TunnelManager()

