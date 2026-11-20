"""ORM-моделі. Відповідають схемі БД з Лабораторної 5 (sql/001_schema.sql)."""
import uuid
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (BigInteger, Column, DateTime, Float, ForeignKey, Integer, Numeric,
                        SmallInteger, String, Table, Text, Time, func)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

place_tags = Table(
    "place_tags",
    Base.metadata,
    Column("place_id", UUID(as_uuid=True), ForeignKey("places.place_id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.tag_id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16), default="tourist")
    locale: Mapped[str] = mapped_column(String(2), default="uk")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # поля міграції 002_security.sql
    failed_logins: Mapped[int] = mapped_column(SmallInteger, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    token_version: Mapped[int] = mapped_column(Integer, default=0)

    interests: Mapped[list["UserInterest"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", passive_deletes=True)


class City(Base):
    __tablename__ = "cities"
    city_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    country_code: Mapped[str] = mapped_column(String(2))


class Category(Base):
    __tablename__ = "categories"
    category_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class Tag(Base):
    __tablename__ = "tags"
    tag_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class OpeningHours(Base):
    __tablename__ = "opening_hours"
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.place_id", ondelete="CASCADE"), primary_key=True)
    weekday: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    opens: Mapped[time] = mapped_column(Time)
    closes: Mapped[time] = mapped_column(Time)


class Place(Base):
    __tablename__ = "places"
    place_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.city_id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id"))
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    lon: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped[Category] = relationship(lazy="joined")
    tags: Mapped[list[Tag]] = relationship(secondary=place_tags, lazy="selectin")
    hours: Mapped[list[OpeningHours]] = relationship(lazy="selectin", order_by=OpeningHours.weekday)


class UserInterest(Base):
    __tablename__ = "user_interests"
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.tag_id", ondelete="CASCADE"), primary_key=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    tag: Mapped[Tag] = relationship(lazy="joined")


class Interaction(Base):
    __tablename__ = "interactions"
    interaction_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    place_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("places.place_id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(8))
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RouteStop(Base):
    __tablename__ = "route_stops"
    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.route_id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    place_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("places.place_id", ondelete="CASCADE"))
    place: Mapped[Place] = relationship(lazy="joined")


class Route(Base):
    __tablename__ = "routes"
    route_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    start_lat: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    start_lon: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    duration_min: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    stops: Mapped[list[RouteStop]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by=RouteStop.position)


class AuthEvent(Base):
    __tablename__ = "auth_events"
    event_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))
    email: Mapped[str | None] = mapped_column(String(254))
    event: Mapped[str] = mapped_column(String(32))
    ip: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
