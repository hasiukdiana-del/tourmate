"""Рівень доступу до даних: усі запити до БД зосереджено тут."""
import uuid

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .models import AuthEvent, City, Interaction, Place, Route, Tag, User, UserInterest


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(func.lower(User.email) == email.lower()))

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def log_event(self, event: str, email: str | None, user: User | None, ip: str | None) -> None:
        self.db.add(AuthEvent(event=event, email=email, user_id=user.user_id if user else None, ip=ip))


class TagRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, name: str) -> Tag:
        name = name.strip().lower()
        tag = self.db.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name)
            self.db.add(tag)
            self.db.flush()
        return tag


class PlaceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, place_id: uuid.UUID) -> Place | None:
        return self.db.get(Place, place_id)

    def nearby(self, lat: float, lon: float, radius: int, category: str | None, q: str | None):
        """Схвалені об’єкти в радіусі (FR-04). Індекс GiST і earthdistance, як у запиті Q1."""
        sql = text("""
            SELECT p.place_id,
                   round(earth_distance(ll_to_earth(:lat, :lon),
                                        ll_to_earth(p.lat::float8, p.lon::float8)))::int AS distance_m
            FROM places p JOIN categories c USING (category_id)
            WHERE p.status = 'approved'
              AND earth_box(ll_to_earth(:lat, :lon), :r) @> ll_to_earth(p.lat::float8, p.lon::float8)
              AND earth_distance(ll_to_earth(:lat, :lon), ll_to_earth(p.lat::float8, p.lon::float8)) <= :r
              AND (CAST(:cat AS text) IS NULL OR c.name = CAST(:cat AS text))
              AND (CAST(:q AS text) IS NULL OR p.name ILIKE '%' || CAST(:q AS text) || '%')
            ORDER BY distance_m
        """)
        rows = self.db.execute(sql, {"lat": lat, "lon": lon, "r": radius, "cat": category, "q": q}).all()
        places = {p.place_id: p for p in self.db.scalars(
            select(Place).where(Place.place_id.in_([r.place_id for r in rows])))}
        return [(places[r.place_id], r.distance_m) for r in rows]

    def rated_by(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        return set(self.db.scalars(select(Interaction.place_id).where(
            Interaction.user_id == user_id, Interaction.type == "rate")))

    def popularity(self) -> dict[uuid.UUID, int]:
        rows = self.db.execute(select(Interaction.place_id, func.count()).group_by(Interaction.place_id))
        return {pid: n for pid, n in rows}

    def by_city(self, city_id: int) -> list[Place]:
        return list(self.db.scalars(select(Place).where(
            Place.city_id == city_id, Place.status == "approved").order_by(Place.name)))


class InterestRepository:
    def __init__(self, db: Session):
        self.db = db

    def weights(self, user: User) -> dict[str, float]:
        return {i.tag.name: i.weight for i in user.interests}

    def get(self, user_id: uuid.UUID, tag_id: int) -> UserInterest | None:
        return self.db.get(UserInterest, (user_id, tag_id))


class CityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, city_id: int) -> City | None:
        return self.db.get(City, city_id)


class RouteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, route_id: uuid.UUID) -> Route | None:
        return self.db.get(Route, route_id)
