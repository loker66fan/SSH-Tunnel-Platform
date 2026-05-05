
from datetime import datetime, timezone

import aiosqlite
import bcrypt

from core.config import settings


class SQLiteDB:
    def __init__(self, db_path=None):
        self._path = db_path or settings.DB_PATH
        self._db = None

    async def init(self):
        if self._db:
            return

        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA foreign_keys = ON")
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS users("
            "username TEXT PRIMARY KEY, "
            "password_hash TEXT NOT NULL, "
            "mfa_secret TEXT"
            ")"
        )

        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS roles("
            "name TEXT PRIMARY KEY, "
            "allow_patterns TEXT, "
            "deny_patterns TEXT"
            ")"
        )
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS user_roles("
            "username TEXT, "
            "role_name TEXT, "
            "PRIMARY KEY (username, role_name)"
            ")"
        )
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS acl_policies("
            "user TEXT PRIMARY KEY, "
            "allow_patterns TEXT, "
            "deny_patterns TEXT"
            ")"
        )
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS tunnels("
            "id TEXT PRIMARY KEY, "
            "user TEXT, "
            "remote_host TEXT, "
            "remote_port INTEGER, "
            "local_port INTEGER, "
            "status TEXT"
            ")"
        )
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS user_tunnels("
            "id TEXT PRIMARY KEY, "
            "owner TEXT NOT NULL, "
            "ssh_host TEXT NOT NULL, "
            "ssh_port INTEGER NOT NULL, "
            "ssh_username TEXT NOT NULL, "
            "ssh_password TEXT NOT NULL, "
            "local_port INTEGER NOT NULL, "
            "remote_host TEXT, "
            "remote_port INTEGER, "
            "tunnel_type TEXT NOT NULL, "
            "remark TEXT, "
            "is_active INTEGER NOT NULL DEFAULT 0, "
            "created_at TEXT NOT NULL, "
            "updated_at TEXT NOT NULL, "
            "FOREIGN KEY(owner) REFERENCES users(username)"
            ")"
        )
        if not await self._column_exists("user_tunnels", "group_name"):
            await self._db.execute("ALTER TABLE user_tunnels ADD COLUMN group_name TEXT")
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_tunnels_owner ON user_tunnels(owner)"
        )
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS audit_logs("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "timestamp TEXT, "
            "user TEXT, "
            "action TEXT, "
            "resource TEXT, "
            "status TEXT, "
            "details TEXT"
            ")"
        )
        await self._db.execute(
            "INSERT OR IGNORE INTO roles (name, allow_patterns, deny_patterns) VALUES (?, ?, ?)",
            ("admin", "*", ""),
        )
        await self._db.execute(
            "INSERT OR IGNORE INTO roles (name, allow_patterns, deny_patterns) VALUES (?, ?, ?)",
            ("user", "*", ""),
        )
        await self._db.execute("UPDATE user_tunnels SET is_active = 0 WHERE is_active != 0")
        await self._db.commit()

    async def _ensure_connection(self):
        if not self._db:
            await self.init()

    async def _column_exists(self, table_name: str, column_name: str) -> bool:
        cur = await self._db.execute(f"PRAGMA table_info({table_name})")
        rows = await cur.fetchall()
        return any(row["name"] == column_name for row in rows)

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize_username(username: str) -> str:
        return (username or "").strip()

    @staticmethod
    def _normalize_group_name(group_name: str):
        value = (group_name or "").strip()
        return value or None

    @staticmethod
    def _row_to_tunnel(row):
        if not row:
            return None
        return {
            "id": row["id"],
            "owner": row["owner"],
            "ssh_host": row["ssh_host"],
            "ssh_port": row["ssh_port"],
            "username": row["ssh_username"],
            "password": row["ssh_password"],
            "local_port": row["local_port"],
            "remote_host": row["remote_host"],
            "remote_port": row["remote_port"],
            "type": row["tunnel_type"],
            "remark": row["remark"],
            "group_name": row["group_name"],
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    async def create_user(self, username, password, overwrite: bool = False):
        await self._ensure_connection()

        username = self._normalize_username(username)
        if not username or not password:
            raise ValueError("Username and password are required")

        salt = bcrypt.gensalt()
        pwd_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

        if overwrite:
            cur = await self._db.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (pwd_hash, username),
            )
            if cur.rowcount == 0:
                await self._db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, pwd_hash),
                )
        else:
            try:
                await self._db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, pwd_hash),
                )
            except aiosqlite.IntegrityError as exc:
                raise ValueError("Username already exists") from exc

        await self._db.execute(
            "INSERT OR IGNORE INTO user_roles (username, role_name) VALUES (?, ?)",
            (username, "user"),
        )
        await self._db.commit()

    async def validate_password(self, username, password):
        await self._ensure_connection()
        cur = await self._db.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (self._normalize_username(username),),
        )
        row = await cur.fetchone()
        if not row:
            return False
        stored_hash = row["password_hash"]
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))

    async def get_mfa_secret(self, username):
        await self._ensure_connection()
        cur = await self._db.execute(
            "SELECT mfa_secret FROM users WHERE username = ?",
            (self._normalize_username(username),),
        )
        row = await cur.fetchone()
        return row["mfa_secret"] if row else None

    async def set_mfa_secret(self, username, secret):
        await self._ensure_connection()
        await self._db.execute(
            "UPDATE users SET mfa_secret = ? WHERE username = ?",
            (secret, self._normalize_username(username)),
        )
        await self._db.commit()

    async def save_user_tunnel(self, owner: str, tunnel_id: str, config: dict, is_active: bool):
        await self._ensure_connection()

        owner = self._normalize_username(owner)
        now = self._now()
        tunnel_type = config.get("type", "local")
        group_name = self._normalize_group_name(config.get("group_name"))
        values = (
            owner,
            config["ssh_host"],
            int(config.get("ssh_port", 22)),
            config["username"],
            config["password"],
            int(config["local_port"]),
            config.get("remote_host"),
            config.get("remote_port"),
            tunnel_type,
            config.get("remark"),
            group_name,
            1 if is_active else 0,
            now,
        )

        existing = await self.get_user_tunnel(owner, tunnel_id)
        if existing:
            await self._db.execute(
                "UPDATE user_tunnels SET "
                "owner = ?, ssh_host = ?, ssh_port = ?, ssh_username = ?, ssh_password = ?, "
                "local_port = ?, remote_host = ?, remote_port = ?, tunnel_type = ?, remark = ?, "
                "group_name = ?, is_active = ?, updated_at = ? "
                "WHERE id = ?",
                values + (tunnel_id,),
            )
        else:
            await self._db.execute(
                "INSERT INTO user_tunnels ("
                "owner, id, ssh_host, ssh_port, ssh_username, ssh_password, "
                "local_port, remote_host, remote_port, tunnel_type, remark, group_name, is_active, "
                "created_at, updated_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    owner,
                    tunnel_id,
                    config["ssh_host"],
                    int(config.get("ssh_port", 22)),
                    config["username"],
                    config["password"],
                    int(config["local_port"]),
                    config.get("remote_host"),
                    config.get("remote_port"),
                    tunnel_type,
                    config.get("remark"),
                    group_name,
                    1 if is_active else 0,
                    now,
                    now,
                ),
            )
        await self._db.commit()

    async def list_user_tunnels(self, owner: str):
        await self._ensure_connection()
        cur = await self._db.execute(
            "SELECT * FROM user_tunnels WHERE owner = ? ORDER BY updated_at DESC, id DESC",
            (self._normalize_username(owner),),
        )
        rows = await cur.fetchall()
        return [self._row_to_tunnel(row) for row in rows]

    async def get_user_tunnel(self, owner: str, tunnel_id: str):
        await self._ensure_connection()
        cur = await self._db.execute(
            "SELECT * FROM user_tunnels WHERE owner = ? AND id = ?",
            (self._normalize_username(owner), tunnel_id),
        )
        row = await cur.fetchone()
        return self._row_to_tunnel(row)

    async def update_user_tunnel(self, owner: str, tunnel_id: str, updates: dict, is_active=None):
        existing = await self.get_user_tunnel(owner, tunnel_id)
        if not existing:
            return False

        merged = {
            "ssh_host": updates.get("ssh_host", existing["ssh_host"]),
            "ssh_port": updates.get("ssh_port", existing["ssh_port"]),
            "username": updates.get("username", existing["username"]),
            "password": updates.get("password", existing["password"]),
            "local_port": updates.get("local_port", existing["local_port"]),
            "remote_host": updates.get("remote_host", existing["remote_host"]),
            "remote_port": updates.get("remote_port", existing["remote_port"]),
            "type": updates.get("type", existing["type"]),
            "remark": updates.get("remark", existing["remark"]),
            "group_name": updates.get("group_name", existing["group_name"]),
        }
        await self.save_user_tunnel(
            owner,
            tunnel_id,
            merged,
            existing["is_active"] if is_active is None else is_active,
        )
        return True

    async def set_user_tunnel_active(self, owner: str, tunnel_id: str, is_active: bool):
        await self._ensure_connection()
        cur = await self._db.execute(
            "UPDATE user_tunnels SET is_active = ?, updated_at = ? WHERE owner = ? AND id = ?",
            (1 if is_active else 0, self._now(), self._normalize_username(owner), tunnel_id),
        )
        await self._db.commit()
        return cur.rowcount > 0

    async def delete_user_tunnel(self, owner: str, tunnel_id: str):
        await self._ensure_connection()
        cur = await self._db.execute(
            "DELETE FROM user_tunnels WHERE owner = ? AND id = ?",
            (self._normalize_username(owner), tunnel_id),
        )
        await self._db.commit()
        return cur.rowcount > 0

    async def delete_user_tunnels(self, owner: str):
        await self._ensure_connection()
        await self._db.execute(
            "DELETE FROM user_tunnels WHERE owner = ?",
            (self._normalize_username(owner),),
        )
        await self._db.commit()

    async def list_user_tunnel_groups(self, owner: str):
        await self._ensure_connection()
        cur = await self._db.execute(
            "SELECT COALESCE(group_name, '') AS group_name, "
            "COUNT(*) AS tunnel_count, "
            "SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_count "
            "FROM user_tunnels WHERE owner = ? "
            "GROUP BY COALESCE(group_name, '') "
            "ORDER BY CASE WHEN COALESCE(group_name, '') = '' THEN 1 ELSE 0 END, LOWER(COALESCE(group_name, ''))",
            (self._normalize_username(owner),),
        )
        rows = await cur.fetchall()
        return [
            {
                "group_name": row["group_name"] or None,
                "tunnel_count": row["tunnel_count"],
                "active_count": row["active_count"] or 0,
            }
            for row in rows
        ]

    async def rename_user_tunnel_group(self, owner: str, old_group_name: str, new_group_name: str):
        await self._ensure_connection()
        owner = self._normalize_username(owner)
        old_group_name = self._normalize_group_name(old_group_name)
        new_group_name = self._normalize_group_name(new_group_name)

        if not old_group_name:
            raise ValueError("Source group is required")
        if not new_group_name:
            raise ValueError("Target group is required")
        if old_group_name == new_group_name:
            return 0

        cur = await self._db.execute(
            "UPDATE user_tunnels SET group_name = ?, updated_at = ? "
            "WHERE owner = ? AND group_name = ?",
            (new_group_name, self._now(), owner, old_group_name),
        )
        await self._db.commit()
        return cur.rowcount

    async def clear_user_tunnel_group(self, owner: str, group_name: str):
        await self._ensure_connection()
        owner = self._normalize_username(owner)
        group_name = self._normalize_group_name(group_name)
        if not group_name:
            raise ValueError("Group is required")

        cur = await self._db.execute(
            "UPDATE user_tunnels SET group_name = NULL, updated_at = ? "
            "WHERE owner = ? AND group_name = ?",
            (self._now(), owner, group_name),
        )
        await self._db.commit()
        return cur.rowcount

    async def add_audit_log(
        self,
        timestamp: str,
        user: str,
        action: str,
        resource: str,
        status: str,
        details: str = None,
    ):
        await self._ensure_connection()
        await self._db.execute(
            "INSERT INTO audit_logs (timestamp, user, action, resource, status, details) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, user, action, resource, status, details),
        )
        await self._db.commit()

    async def list_audit_logs(self, limit: int = 100):
        await self._ensure_connection()
        cur = await self._db.execute(
            "SELECT id, timestamp, user, action, resource, status, details "
            "FROM audit_logs ORDER BY datetime(timestamp) DESC, id DESC LIMIT ?",
            (limit,),
        )
        rows = await cur.fetchall()
        return [
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "user": row["user"],
                "action": row["action"],
                "resource": row["resource"],
                "status": row["status"],
                "details": row["details"],
            }
            for row in rows
        ]

    async def delete_audit_logs_older_than(self, cutoff_timestamp: str):
        await self._ensure_connection()
        cur = await self._db.execute(
            "SELECT COUNT(*) AS cnt FROM audit_logs WHERE datetime(timestamp) < datetime(?)",
            (cutoff_timestamp,),
        )
        row = await cur.fetchone()
        deleted_count = row["cnt"] if row else 0
        await self._db.execute(
            "DELETE FROM audit_logs WHERE datetime(timestamp) < datetime(?)",
            (cutoff_timestamp,),
        )
        await self._db.commit()
        return deleted_count

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None


db = SQLiteDB()
