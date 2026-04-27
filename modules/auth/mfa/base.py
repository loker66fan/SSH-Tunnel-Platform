from abc import ABC, abstractmethod

class MFAProvider(ABC):
    @abstractmethod
    async def generate_secret(self) -> str:
        """生成 MFA 密钥"""
        pass

    @abstractmethod
    async def verify(self, secret: str, code: str) -> bool:
        """验证 MFA 验证码"""
        pass

    @abstractmethod
    def get_type(self) -> str:
        """返回 MFA 类型名称"""
        pass
