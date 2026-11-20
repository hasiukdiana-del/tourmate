"""Налаштування застосунку. Значення беруться зі змінних середовища."""
import os
from datetime import timedelta

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://tourmate:tourmate@localhost:5432/tourmate"
)
# Секрет підпису JWT: у робочому середовищі задається лише через змінну оточення.
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-secret-change-me-0123456789abcdef0123")
JWT_ALG = "HS256"
ACCESS_TTL = timedelta(minutes=15)
REFRESH_TTL = timedelta(days=7)

# Захист від підбору пароля: 5 невдалих спроб блокують обліковий запис на 15 хв.
MAX_FAILED_LOGINS = 5
LOCKOUT = timedelta(minutes=15)

CORS_ORIGINS = [o for o in os.getenv("CORS_ORIGINS", "*").split(",") if o]
