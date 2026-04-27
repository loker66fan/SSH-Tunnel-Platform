
from modules.auth.base import AuthProvider, AuthRequest
from infra.db.sqlite import db

class PasswordAuthProvider(AuthProvider):
    async def authenticate(self, request: AuthRequest) -> bool:
        if not request.username or not request.password:
            return False
        return await db.validate_password(request.username, request.password)
