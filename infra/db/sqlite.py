
import aiosqlite
import bcrypt
from core.config import settings

class SQLiteDB:
    def __init__(self, db_path=None):
        self._path = db_path or settings.DB_PATH
        self._db = None

    async def init(self):
        self._db = await aiosqlite.connect(self._path)
        await self._db.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password_hash TEXT, mfa_secret TEXT)")
        
        # RBAC Tables
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
        await self._db.commit()

    async def create_user(self, username, password):
        salt = bcrypt.gensalt()
        pwd_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        await self._db.execute("INSERT OR REPLACE INTO users (username, password_hash) VALUES (?,?)",(username,pwd_hash))
        await self._db.commit()

    async def validate_password(self, username, password):
        if not self._db:
            await self.init()
        cur = await self._db.execute("SELECT password_hash FROM users WHERE username=?",(username,))
        row = await cur.fetchone()
        if not row:
            return False
        stored_hash = row[0]
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))

    async def get_mfa_secret(self, username):
        if not self._db:
            await self.init()
        cur = await self._db.execute("SELECT mfa_secret FROM users WHERE username=?",(username,))
        row = await cur.fetchone()
        return row[0] if row else None

    async def set_mfa_secret(self, username, secret):
        if not self._db:
            await self.init()
        await self._db.execute("UPDATE users SET mfa_secret=? WHERE username=?",(secret, username))
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()

db = SQLiteDB()
