"""Безпечне керування обліковими записами: хешування, JWT, ролі."""
import uuid
from datetime import datetime, timezone

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import ACCESS_TTL, JWT_ALG, JWT_SECRET, REFRESH_TTL
from .db import get_db
from .errors import AppError
from .models import User


def hash_password(password: str) -> str:
    # bcrypt із сіллю та вартістю 12; пароль у відкритому вигляді не зберігається
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


# Хеш-заглушка: перевірка триває однаково для наявного й відсутнього e-mail,
# тому за часом відповіді не можна дізнатися, чи зареєстрована адреса.
DUMMY_HASH = hash_password("Dummy-password-0")


def create_token(user: User, kind: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.user_id),
        "role": user.role,
        "ver": user.token_version,  # зміна версії відкликає всі видані токени
        "type": kind,
        "iat": now,
        "exp": now + (ACCESS_TTL if kind == "access" else REFRESH_TTL),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str, kind: str) -> dict:
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise AppError(401, "Token expired")
    except jwt.InvalidTokenError:
        raise AppError(401, "Invalid token")
    if data.get("type") != kind:
        raise AppError(401, "Invalid token type")
    return data


bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    if creds is None:
        raise AppError(401, "Authentication required")
    data = decode_token(creds.credentials, "access")
    user = db.get(User, uuid.UUID(data["sub"]))
    if user is None or user.token_version != data["ver"]:
        raise AppError(401, "Session revoked")
    return user


def require_role(*roles: str):
    """Авторизація за роллю: tourist, author, admin."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise AppError(403, "Access denied")
        return user

    return dependency
