import base64
import hashlib
import config
from cryptography.fernet import Fernet


class Encryption:

    def __init__(self):
        self._key = self._derive_key(config.SECRET_KEY)
        self._fernet = Fernet(self._key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()

    def hash(self, value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def _derive_key(self, secret: str) -> bytes:
        digest = hashlib.sha256(secret.encode()).digest()
        return base64.urlsafe_b64encode(digest)


encryption = Encryption()
