
import asyncssh
import httpx
import socket
import asyncio
from modules.ssh.base import SSHBackend
from core.logger import logger

class AsyncSSHBackend(SSHBackend):
    def __init__(self, host: str = None, port: int = None, username: str = None, password: str = None, remark: str = None,
                 local_port: int = None, remote_host: str = None, remote_port: int = None):
        self._conn = None
        self._tunnels = []
        self._is_socks = False
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._remark = remark
        self._local_port = local_port
        self._remote_host = remote_host
        self._remote_port = remote_port

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    @property
    def remark(self):
        return self._remark

    @property
    def local_port(self):
        return self._local_port

    @property
    def remote_host(self):
        return self._remote_host

    @property
    def remote_port(self):
        return self._remote_port

    def update_remark(self, new_remark: str):
        self._remark = new_remark

    def update_host_port(self, new_host: str = None, new_port: int = None):
        if new_host:
            self._host = new_host
        if new_port:
            self._port = new_port

    async def connect(self, host: str, port: int, username: str, password: str = None, client_keys: list = None):
        try:
            logger.info(f"Connecting to {host}:{port} as {username}")
            self._conn = await asyncssh.connect(
                host, 
                port=port, 
                username=username, 
                password=password,
                client_keys=client_keys,
                known_hosts=None  # For MVP, we skip host key validation. Should be fixed in production.
            )
            logger.info(f"Successfully connected to {host}")
        except Exception as e:
            logger.error(f"Failed to connect to {host}: {str(e)}")
            raise

    async def open_tunnel(self, local_port: int, remote_host: str, remote_port: int):
        if not self._conn:
            raise Exception("SSH connection not established")
        
        try:
            logger.info(f"Opening tunnel: localhost:{local_port} -> {remote_host}:{remote_port}")
            listener = await self._conn.forward_local_port(
                '', local_port, remote_host, remote_port
            )
            self._tunnels.append(listener)
            return listener
        except Exception as e:
            logger.error(f"Failed to open tunnel: {str(e)}")
            raise

    async def open_socks_proxy(self, local_port: int):
        if not self._conn:
            raise Exception("SSH connection not established")
        
        try:
            logger.info(f"Opening dynamic SOCKS proxy on localhost:{local_port}")
            # Correct method for asyncssh is forward_socks
            listener = await self._conn.forward_socks('', local_port)
            self._tunnels.append(listener)
            self._is_socks = True
            return listener
        except Exception as e:
            logger.error(f"Failed to open SOCKS proxy: {str(e)}")
            raise

    async def close(self):
        for tunnel in self._tunnels:
            tunnel.close()
            await tunnel.wait_closed()
        
        if self._conn:
            self._conn.close()
            await self._conn.wait_closed()
        logger.info("SSH connection and tunnels closed")

    async def run_command(self, command: str) -> str:
        if not self._conn:
            raise Exception("SSH connection not established")
        
        try:
            logger.info(f"Executing command: {command}")
            result = await self._conn.run(command)
            return result.stdout or result.stderr or ""
        except Exception as e:
            logger.error(f"Failed to execute command: {str(e)}")
            raise

    async def open_shell(self, term_type: str = 'xterm', width: int = 80, height: int = 24):
        if not self._conn:
            raise Exception("SSH connection not established")
        
        try:
            logger.info(f"Opening interactive shell with PTY: {term_type}, {width}x{height}")
            process = await self._conn.create_process(
                    'bash',
                    term_type=term_type,
                    term_size=(width, height),
                    stdin=asyncssh.PIPE,
                    stdout=asyncssh.PIPE,
                    stderr=asyncssh.PIPE
                )
            return process
        except Exception as e:
            logger.error(f"Failed to open interactive shell: {str(e)}")
            raise

    async def verify_socks(self, local_port: int) -> bool:
        """验证 SOCKS5 代理是否正常工作"""
        try:
            # 只需要尝试最基础的 TCP 握手验证，确保端口确实在提供 SOCKS5 服务
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            try:
                sock.connect(('127.0.0.1', local_port))
                # 发送 SOCKS5 初始握手: version 5, 1 auth method (no auth)
                sock.sendall(b'\x05\x01\x00')
                resp = sock.recv(2)
                if resp == b'\x05\x00':
                    sock.close()
                    return True
                logger.error(f"SOCKS5 handshake failed on port {local_port}: expected b'\\x05\\x00', got {resp!r}")
                sock.close()
                return False
            except Exception as e:
                logger.error(f"SOCKS5 TCP connect failed on port {local_port}: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"SOCKS5 verification error: {str(e)}")
            return False
