
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 18002
    API_SECRET: str = "change-me"
    
    # SSH Server Settings
    SSH_HOST: str = "0.0.0.0"
    SSH_PORT: int = 2222
    
    # DB Settings
    DB_PATH: str = "data.db"
    
    # SSH Key Settings
    HOST_KEY_RSA: str = "keys/ssh_host_rsa"
    HOST_KEY_ED25519: str = "keys/ssh_host_ed25519"
    
    # SSH Capabilities
    ALLOW_PORT_FORWARDING: bool = True
    ALLOW_AGENT_FORWARDING: bool = True
    ALLOW_X11_FORWARDING: bool = False
    ALLOW_SFTP: bool = True
    
    # Security Settings
    MAX_AUTH_FAILURES: int = 10
    AUTH_WINDOW_SEC: int = 300
    MAX_SESSIONS: int = 5
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
