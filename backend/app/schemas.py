"""Схеми запитів і відповідей. Валідація виконується на сервері незалежно від клієнта."""
import re
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

# ---------- автентифікація ----------

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        # Політика паролів: щонайменше 10 символів, великі й малі літери, цифра.
        if not (re.search(r"[a-zа-яіїєґ]", v) and re.search(r"[A-ZА-ЯІЇЄҐ]", v) and re.search(r"\d", v)):
            raise ValueError("password must contain upper and lower case letters and a digit")
        return v

    @model_validator(mode="after")
    def password_not_email(self):
        if self.email.split("@")[0].lower() in self.password.lower():
            raise ValueError("password must not contain the e-mail name")
        return self


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------- користувач ----------

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    email: str
    role: str
    locale: str


class InterestIn(BaseModel):
    tag: str = Field(min_length=1, max_length=50)
    weight: float = Field(default=1.0, ge=0, le=1)


class InterestsIn(BaseModel):
    # FR-02: щонайменше 3 інтереси
    interests: list[InterestIn] = Field(min_length=3, max_length=30)


class InterestOut(BaseModel):
    tag: str
    weight: float


# ---------- об’єкти ----------

class HoursOut(BaseModel):
    weekday: int
    opens: str
    closes: str


class PlaceOut(BaseModel):
    place_id: uuid.UUID
    name: str
    category: str
    lat: float
    lon: float
    tags: list[str]
    distance_m: int | None = None


class PlaceDetail(PlaceOut):
    description: str | None
    status: str
    hours: list[HoursOut]


class PlaceCreate(BaseModel):
    city_id: int = Field(ge=1)
    category_id: int = Field(ge=1)
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    tags: list[str] = Field(default_factory=list, max_length=10)


class StatusIn(BaseModel):
    status: Literal["approved", "rejected"]


# ---------- рекомендації, взаємодії, маршрути ----------

class RecommendationOut(BaseModel):
    place: PlaceOut
    score: float
    reason_tags: list[str]


class InteractionIn(BaseModel):
    place_id: uuid.UUID
    type: Literal["view", "rate", "save"]
    rating: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def rating_only_for_rate(self):
        if (self.type == "rate") != (self.rating is not None):
            raise ValueError("rating is required for type 'rate' and forbidden otherwise")
        return self


class InteractionOut(BaseModel):
    interaction_id: int
    profile_changes: dict[str, float]


class RouteIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    duration_min: int = Field(ge=15, le=480)


class RouteOut(BaseModel):
    route_id: uuid.UUID
    duration_min: int
    total_m: int
    est_min: int
    stops: list[PlaceOut]


class CityPackage(BaseModel):
    city_id: int
    name: str
    places: list[PlaceDetail]
