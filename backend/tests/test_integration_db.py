"""Інтеграційні тести IT-01...IT-03: взаємодія серверної частини з PostgreSQL."""
import uuid

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal
from app.main import app
from app.models import User
from app.repositories import UserRepository
from app.security import hash_password, verify_password

API = "/api/v1"
OPERA = "a0000000-0000-0000-0000-000000000001"
client = TestClient(app)


def test_it01_user_saved_and_found():
    """Репозиторій зберігає користувача; пошук за e-mail не залежить від регістру; пароль лише як хеш."""
    email = f"it-{uuid.uuid4().hex[:6]}@tourmate.ua"
    with SessionLocal() as db:
        users = UserRepository(db)
        users.add(User(email=email, password_hash=hash_password("Strong-pass-42")))
        db.commit()
    with SessionLocal() as db:
        saved = UserRepository(db).by_email(email.upper())
        assert saved is not None and saved.role == "tourist"
        assert saved.password_hash != "Strong-pass-42"
        assert verify_password("Strong-pass-42", saved.password_hash)


def test_it02_interests_persisted():
    """PUT /users/me/interests записує профіль у user_interests і створює нові теги."""
    email = f"it-{uuid.uuid4().hex[:6]}@tourmate.ua"
    token = client.post(f"{API}/auth/register", json={"email": email, "password": "Strong-pass-42"}).json()
    body = {"interests": [{"tag": "історія"}, {"tag": "кава", "weight": 0.5}, {"tag": "архітектура"}]}
    client.put(f"{API}/users/me/interests", json=body, headers={"Authorization": f"Bearer {token['access_token']}"})
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT t.name, ui.weight FROM user_interests ui
            JOIN users u USING (user_id) JOIN tags t USING (tag_id)
            WHERE u.email = :e ORDER BY t.name"""), {"e": email}).all()
    assert [n for n, _ in rows] == ["архітектура", "історія", "кава"]
    assert [w for _, w in rows] == pytest.approx([1.0, 1.0, 0.5])


def test_it03_rating_persisted_and_profile_updated():
    """POST /interactions записує оцінку в interactions і змінює вагу тегу в тій самій транзакції."""
    email = f"it-{uuid.uuid4().hex[:6]}@tourmate.ua"
    token = client.post(f"{API}/auth/register", json={"email": email, "password": "Strong-pass-42"}).json()
    h = {"Authorization": f"Bearer {token['access_token']}"}
    body = {"interests": [{"tag": "історія", "weight": 0.5}, {"tag": "кава"}, {"tag": "парк"}]}
    client.put(f"{API}/users/me/interests", json=body, headers=h)
    client.post(f"{API}/interactions", json={"place_id": OPERA, "type": "rate", "rating": 4}, headers=h)
    with SessionLocal() as db:
        rating = db.execute(text("""
            SELECT i.rating FROM interactions i JOIN users u USING (user_id)
            WHERE u.email = :e AND i.type = 'rate'"""), {"e": email}).scalar_one()
        weight = db.execute(text("""
            SELECT ui.weight FROM user_interests ui JOIN users u USING (user_id)
            JOIN tags t USING (tag_id) WHERE u.email = :e AND t.name = 'історія'"""), {"e": email}).scalar_one()
    assert rating == 4
    assert weight == pytest.approx(0.6)
