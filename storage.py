
import aiosqlite
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Storage:
    def __init__(self, db_path="data.db"):
        self._path = db_path
        self._db = None

    async def init(self):
        self._db = await aiosqlite.connect(self._path)
        await self._db.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password_hash TEXT)")
        await self._db.commit()

    async def create_user(self, username, password):
        pwd_hash = pwd_context.hash(password)
        await self._db.execute("INSERT INTO users VALUES (?,?)",(username,pwd_hash))
        await self._db.commit()

    async def validate_password(self, username, password):
        cur = await self._db.execute("SELECT password_hash FROM users WHERE username=?",(username,))
        row = await cur.fetchone()
        if not row:
            return False
        return pwd_context.verify(password, row[0])
