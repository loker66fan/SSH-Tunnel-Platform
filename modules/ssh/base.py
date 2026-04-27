
from abc import ABC, abstractmethod

class SSHBackend(ABC):
    @abstractmethod
    async def connect(self, host: str, port: int, username: str, password: str = None, client_keys: list = None):
        """Establish connection to remote SSH server"""
        pass

    @abstractmethod
    async def open_tunnel(self, local_port: int, remote_host: str, remote_port: int):
        """Open a local port forwarding tunnel"""
        pass

    @abstractmethod
    async def open_socks_proxy(self, local_port: int):
        """Open a dynamic SOCKS5 proxy tunnel"""
        pass

    @abstractmethod
    async def close(self):
        """Close the SSH connection and all tunnels"""
        pass

    @abstractmethod
    async def run_command(self, command: str) -> str:
        """Execute a command on the remote server"""
        pass

    @abstractmethod
    async def open_shell(self, term_type: str = 'xterm', width: int = 80, height: int = 24):
        """Open an interactive shell on the remote server"""
        pass
