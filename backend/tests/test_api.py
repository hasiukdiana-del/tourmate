"""Інтеграційні тести API: застосунок + PostgreSQL з тестовими даними (sql/003_seed.sql)."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

API = "/api/v1"
RYNOK = {"lat": 49.8419, "lon": 24.0315}  # площа Ринок, Львів
OPERA = "a0000000-0000-0000-0000-000000000001"
PENDING = "a0000000-0000-0000-0000-000000000006"

client = TestClient(app)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(email: str, password: str = "secret123") -> str:
    r = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def new_user() -> tuple[str, str, dict]:
    email = f"user-{uuid.uuid4().hex[:8]}@test.ua"
    password = "Strong-pass-42"
    r = client.post(f"{API}/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return email, password, r.json()


@pytest.fixture(scope="module")
def tourist() -> str:
    return login("tourist@tourmate.ua")


# ---------- автентифікація ----------

def test_register_weak_password_rejected():
    r = client.post(f"{API}/auth/register", json={"email": "weak@test.ua", "password": "12345678"})
    assert r.status_code == 400
    assert r.json()["message"] == "Validation error"


def test_register_duplicate_email_conflict():
    email, password, _ = new_user()
    r = client.post(f"{API}/auth/register", json={"email": email, "password": password})
    assert r.status_code == 409


def test_wrong_password_unauthorized():
    r = client.post(f"{API}/auth/login", json={"email": "tourist@tourmate.ua", "password": "wrong"})
    assert r.status_code == 401
    assert r.json() == {"status": 401, "message": "Invalid email or password"}


def test_lockout_after_five_failures():
    email, password, _ = new_user()
    for _ in range(5):
        client.post(f"{API}/auth/login", json={"email": email, "password": "wrong-password"})
    r = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 429


def test_protected_endpoint_requires_token():
    assert client.get(f"{API}/users/me").status_code == 401


def test_logout_revokes_tokens():
    _, _, tokens = new_user()
    h = auth(tokens["access_token"])
    assert client.post(f"{API}/auth/logout", headers=h).status_code == 204
    assert client.get(f"{API}/users/me", headers=h).status_code == 401


def test_tourist_cannot_create_place(tourist):
    body = {"city_id": 1, "category_id": 1, "name": "Тест", "lat": 49.84, "lon": 24.03}
    assert client.post(f"{API}/places", json=body, headers=auth(tourist)).status_code == 403


# ---------- об’єкти та рекомендації ----------

def test_nearby_sorted_and_pending_hidden():
    r = client.get(f"{API}/places", params={**RYNOK, "radius": 1000})
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert names[0] == "Площа Ринок"
    assert "Нова кав’ярня" not in names  # статус pending


def test_radius_out_of_range_rejected():
    assert client.get(f"{API}/places", params={**RYNOK, "radius": 10000}).status_code == 400


def test_unknown_place_not_found():
    r = client.get(f"{API}/places/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["message"] == "Place not found"


def test_recommendations_match_lab5_q2(tourist):
    r = client.get(f"{API}/recommendations", params=RYNOK, headers=auth(tourist))
    assert r.status_code == 200
    first = r.json()[0]
    assert first["place"]["name"] == "Львівська опера"
    assert first["reason_tags"] == ["історія", "опера"]


def test_rating_updates_profile():
    email, password, tokens = new_user()
    h = auth(tokens["access_token"])
    interests = {"interests": [{"tag": "історія"}, {"tag": "кава", "weight": 0.5}, {"tag": "парк"}]}
    assert client.put(f"{API}/users/me/interests", json=interests, headers=h).status_code == 200
    r = client.post(f"{API}/interactions", json={"place_id": OPERA, "type": "rate", "rating": 5}, headers=h)
    assert r.status_code == 201
    assert r.json()["profile_changes"] == {"опера": 0.2}  # історія вже 1,0


def test_rate_without_rating_rejected(tourist):
    r = client.post(f"{API}/interactions", json={"place_id": OPERA, "type": "rate"}, headers=auth(tourist))
    assert r.status_code == 400


def test_walk_fits_time_budget(tourist):
    r = client.post(f"{API}/routes", json={**RYNOK, "duration_min": 90}, headers=auth(tourist))
    assert r.status_code == 201
    body = r.json()
    assert body["stops"] and body["est_min"] <= 90
    again = client.get(f"{API}/routes/{body['route_id']}", headers=auth(tourist))
    assert again.status_code == 200 and len(again.json()["stops"]) == len(body["stops"])
