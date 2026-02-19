import hashlib
import bcrypt


class Security:
    """Хэширование и проверка паролей (SHA-256 прехэш + bcrypt)."""

    def hash_password(self, password: str) -> str:
        """Возвращает bcrypt-хэш пароля."""
        digest = self._password_digest(password)
        return bcrypt.hashpw(digest, bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Проверяет пароль против bcrypt-хэша из БД."""
        digest = self._password_digest(password)
        return bcrypt.checkpw(digest, hashed_password.encode("utf-8"))

    def _password_digest(self, password) -> bytes:
        """SHA-256 прехэш для устранения ограничения длины пароля в bcrypt."""
        return hashlib.sha256(password.encode('utf-8')).digest()


security = Security()
