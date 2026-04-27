
class Config:
    DB_PATH = "data.db"
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    API_SECRET = "change-me"

    SSH_HOST = "0.0.0.0"
    SSH_PORT = 2222

    HOST_KEY_RSA = "keys/ssh_host_rsa"
    HOST_KEY_ED25519 = "keys/ssh_host_ed25519"

    ALLOW_PORT_FORWARDING = True
    ALLOW_AGENT_FORWARDING = True
    ALLOW_X11_FORWARDING = False
    ALLOW_SFTP = True

    MAX_AUTH_FAILURES = 10
    AUTH_WINDOW_SEC = 300
    MAX_SESSIONS = 5

    LOG_LEVEL = "INFO"
