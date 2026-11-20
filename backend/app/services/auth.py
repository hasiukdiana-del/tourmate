"""Бізнес-логіка облікових записів: реєстрація, вхід із блокуванням, оновлення та відкликання токенів."""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..config import ACCESS_TTL, LOCKOUT, MAX_FAILED_LOGINS
from ..errors import AppError
from ..models import User
from ..repositories import UserRepository
from ..schemas import LoginIn, RegisterIn, TokenPair
from ..security import DUMMY_HASH, create_token, decode_token, hash_password, verify_password


def _tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_token(user, "access"),
        refresh_token=create_token(user, "refresh"),
        expires_in=int(ACCESS_TTL.total_seconds()),
    )


def register(db: Session, data: RegisterIn, ip: str | None) -> TokenPair:
    users = UserRepository(db)
    if users.by_email(data.email):
        raise AppError(409, "Email already registered")
    user = users.add(User(email=data.email.lower(), password_hash=hash_password(data.password)))
    users.log_event("register", user.email, user, ip)
    db.commit()
    return _tokens(user)


def login(db: Session, data: LoginIn, ip: str | None) -> TokenPair:
    users = UserRepository(db)
    user = users.by_email(data.email)
    now = datetime.now(timezone.utc)

    if user and user.locked_until and user.locked_until > now:
        users.log_event("login_locked", data.email, user, ip)
        db.commit()
        raise AppError(429, "Account temporarily locked")

    ok = verify_password(data.password, user.password_hash if user else DUMMY_HASH)
    if not ok:
        if user:
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILED_LOGINS:
                user.locked_until = now + LOCKOUT
                user.failed_logins = 0
                users.log_event("lockout", data.email, user, ip)
        users.log_event("login_failed", data.email, user, ip)
        db.commit()
        # однакова відповідь для невідомого e-mail і хибного пароля
        raise AppError(401, "Invalid email or password")

    user.failed_logins = 0
    user.locked_until = None
    users.log_event("login_ok", user.email, user, ip)
    db.commit()
    return _tokens(user)


def refresh(db: Session, token: str) -> TokenPair:
    data = decode_token(token, "refresh")
    user = db.get(User, uuid.UUID(data["sub"]))
    if user is None or user.token_version != data["ver"]:
        raise AppError(401, "Session revoked")
    return _tokens(user)


def logout_everywhere(db: Session, user: User, ip: str | None) -> None:
    # Збільшення версії робить недійсними всі раніше видані токени користувача.
    user.token_version += 1
    UserRepository(db).log_event("logout", user.email, user, ip)
    db.commit()
