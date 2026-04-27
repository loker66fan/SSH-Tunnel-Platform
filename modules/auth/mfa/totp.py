import pyotp
import qrcode
import io
import base64
from modules.auth.mfa.base import MFAProvider

class TOTPProvider(MFAProvider):
    def get_type(self) -> str:
        return "totp"

    async def generate_secret(self) -> str:
        return pyotp.random_base32()

    async def verify(self, secret: str, code: str) -> bool:
        totp = pyotp.TOTP(secret)
        return totp.verify(code)

    def get_provisioning_uri(self, secret: str, username: str, issuer_name: str = "SSH-Gateway") -> str:
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=issuer_name)

    def generate_qr_code_base64(self, uri: str) -> str:
        """生成 QR 码的 base64 字符串"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
