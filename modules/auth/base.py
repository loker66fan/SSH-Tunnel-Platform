from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional

class AuthRequest(BaseModel):
    username: str
    password: str
    mfa_code: Optional[str] = None
    token: Optional[str] = None

class AuthProvider(ABC):
    @abstractmethod
    async def authenticate(self, request: AuthRequest) -> bool:
        pass
