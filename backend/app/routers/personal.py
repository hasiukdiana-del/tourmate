"""Персональні ресурси: рекомендації, взаємодії, прогулянки."""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import AppError, not_found
from ..models import Interaction, User
from ..repositories import PlaceRepository, RouteRepository
from ..schemas import InteractionIn, InteractionOut, RecommendationOut, RouteIn, RouteOut
from ..security import get_current_user
from ..services.recommendations import learn_from_rating, recommend
from ..services.walks import build_walk, route_out

router = APIRouter(tags=["personal"])


@router.get("/recommendations", response_model=list[RecommendationOut])
def recommendations(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    limit: int = Query(20, ge=1, le=50),  # FR-07: стрічка з 20 рекомендацій
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return recommend(db, user, lat, lon, limit)


@router.post("/interactions", response_model=InteractionOut, status_code=status.HTTP_201_CREATED)
def add_interaction(data: InteractionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """FR-09: перегляд, оцінка, збереження. FR-10: оцінка оновлює профіль інтересів."""
    place = PlaceRepository(db).get(data.place_id)
    if place is None or place.status != "approved":
        raise not_found("Place")
    item = Interaction(user_id=user.user_id, place_id=place.place_id, type=data.type, rating=data.rating)
    db.add(item)
    changes = learn_from_rating(db, user, place, data.rating) if data.type == "rate" else {}
    db.commit()
    return InteractionOut(interaction_id=item.interaction_id, profile_changes=changes)


@router.post("/routes", response_model=RouteOut, status_code=status.HTTP_201_CREATED)
def create_route(data: RouteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """FR-11: прогулянка з рекомендованих об’єктів за точкою старту та доступним часом."""
    return build_walk(db, user, data)


@router.get("/routes/{route_id}", response_model=RouteOut)
def get_route(route_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    route = RouteRepository(db).get(route_id)
    if route is None:
        raise not_found("Route")
    if route.user_id != user.user_id:
        raise AppError(403, "Access denied")  # чужі маршрути недоступні
    return route_out(route)
