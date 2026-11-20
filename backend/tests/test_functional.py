"""Функціональні тест-кейси TC-01...TC-14: перевірка вимог через REST API на тестових даних."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

API = "/api/v1"
RYNOK = {"lat": 49.8419, "lon": 24.0315}
OPERA = "a0000000-0000-0000-0000-000000000001"
client = TestClient(app)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register() -> dict:
    email = f"tc-{uuid.uuid4().hex[:8]}@test.ua"
    r = client.post(f"{API}/auth/register", json={"email": email, "password": "Strong-pass-42"})
    assert r.status_code == 201, r.text
    return {"email": email, **r.json()}


@pytest.fixture(scope="module")
def tourist() -> dict:
    r = client.post(f"{API}/auth/login", json={"email": "tourist@tourmate.ua", "password": "secret123"})
    return auth(r.json()["access_token"])


# ---------- позитивні ----------

def test_tc01_register_valid():
    user = register()
    assert user["access_token"] and user["refresh_token"]


def test_tc02_login_valid():
    user = register()
    r = client.post(f"{API}/auth/login", json={"email": user["email"].upper(), "password": "Strong-pass-42"})
    assert r.status_code == 200


def test_tc03_save_three_interests():
    h = auth(register()["access_token"])
    body = {"interests": [{"tag": "історія"}, {"tag": "кава", "weight": 0.5}, {"tag": "парк"}]}
    r = client.put(f"{API}/users/me/interests", json=body, headers=h)
    assert r.status_code == 200 and len(r.json()) == 3


def test_tc04_search_by_name():
    r = client.get(f"{API}/places", params={**RYNOK, "radius": 2000, "q": "опер"})
    assert [p["name"] for p in r.json()] == ["Львівська опера"]


def test_tc05_filter_by_category():
    r = client.get(f"{API}/places", params={**RYNOK, "radius": 5000, "category": "Гастрономія"})
    assert r.json() and all(p["category"] == "Гастрономія" for p in r.json())


def test_tc06_rating_updates_profile():
    h = auth(register()["access_token"])
    body = {"interests": [{"tag": "історія", "weight": 0.5}, {"tag": "кава"}, {"tag": "парк"}]}
    client.put(f"{API}/users/me/interests", json=body, headers=h)
    r = client.post(f"{API}/interactions", json={"place_id": OPERA, "type": "rate", "rating": 5}, headers=h)
    assert r.status_code == 201
    assert r.json()["profile_changes"] == {"історія": 0.2, "опера": 0.2}


def test_tc07_walk_within_60_minutes(tourist):
    r = client.post(f"{API}/routes", json={**RYNOK, "duration_min": 60}, headers=tourist)
    assert r.status_code == 201
    assert r.json()["stops"] and r.json()["est_min"] <= 60


def test_tc08_recommendations_within_radius(tourist):
    r = client.get(f"{API}/recommendations", params={**RYNOK, "radius": 1000}, headers=tourist)
    assert r.status_code == 200
    assert all(item["place"]["distance_m"] <= 1000 for item in r.json())


# ---------- негативні ----------

def test_tc09_login_wrong_password():
    user = register()
    r = client.post(f"{API}/auth/login", json={"email": user["email"], "password": "Wrong-pass-00"})
    assert r.status_code == 401


def test_tc10_two_interests_rejected():
    h = auth(register()["access_token"])
    body = {"interests": [{"tag": "історія"}, {"tag": "кава"}]}
    assert client.put(f"{API}/users/me/interests", json=body, headers=h).status_code == 400


def test_tc11_duplicate_interests_rejected():
    h = auth(register()["access_token"])
    body = {"interests": [{"tag": "Історія"}, {"tag": "історія "}, {"tag": "кава"}]}
    assert client.put(f"{API}/users/me/interests", json=body, headers=h).status_code == 400


def test_tc12_blank_interest_rejected():
    h = auth(register()["access_token"])
    body = {"interests": [{"tag": "   "}, {"tag": "історія"}, {"tag": "кава"}]}
    assert client.put(f"{API}/users/me/interests", json=body, headers=h).status_code == 400


def test_tc13_walk_too_short_rejected(tourist):
    r = client.post(f"{API}/routes", json={**RYNOK, "duration_min": 10}, headers=tourist)
    assert r.status_code == 400


def test_tc14_foreign_route_forbidden(tourist):
    route = client.post(f"{API}/routes", json={**RYNOK, "duration_min": 60}, headers=tourist).json()
    other = auth(register()["access_token"])
    assert client.get(f"{API}/routes/{route['route_id']}", headers=other).status_code == 403
