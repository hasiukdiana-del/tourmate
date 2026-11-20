import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import not_found
from ..models import Place, User
from ..repositories import CityRepository, PlaceRepository, TagRepository
from ..schemas import CityPackage, HoursOut, PlaceCreate, PlaceDetail, PlaceOut, StatusIn
from ..security import get_current_user, require_role
from ..services.recommendations import place_out

router = APIRouter(tags=["places"])


def detail(p: Place, distance_m: int | None = None) -> PlaceDetail:
    return PlaceDetail(
        **place_out(p, distance_m).model_dump(), description=p.description, status=p.status,
        hours=[HoursOut(weekday=h.weekday, opens=h.opens.strftime("%H:%M"), closes=h.closes.strftime("%H:%M"))
               for h in p.hours],
    )


@router.get("/places", response_model=list[PlaceOut])
def nearby(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    radius: int = Query(1000, ge=500, le=5000),  # FR-04: від 0,5 до 5 км
    category: str | None = Query(None, max_length=50),
    q: str | None = Query(None, min_length=2, max_length=100),  # FR-06: пошук за назвою
    db: Session = Depends(get_db),
):
    return [place_out(p, d) for p, d in PlaceRepository(db).nearby(lat, lon, radius, category, q)]


@router.get("/places/{place_id}", response_model=PlaceDetail)
def get_place(place_id: uuid.UUID, db: Session = Depends(get_db)):
    """FR-05: картка об’єкта з годинами роботи."""
    p = PlaceRepository(db).get(place_id)
    if p is None or p.status != "approved":
        raise not_found("Place")
    return detail(p)


@router.post("/places", response_model=PlaceDetail, status_code=status.HTTP_201_CREATED)
def create_place(data: PlaceCreate, user: User = Depends(require_role("author", "admin")),
                 db: Session = Depends(get_db)):
    """FR-13: автор додає об’єкт і розмічає його тегами; статус pending до модерації."""
    if CityRepository(db).get(data.city_id) is None:
        raise not_found("City")
    tags = TagRepository(db)
    p = Place(city_id=data.city_id, category_id=data.category_id, author_id=user.user_id,
              name=data.name, description=data.description, lat=data.lat, lon=data.lon, status="pending")
    p.tags = [tags.get_or_create(t) for t in dict.fromkeys(data.tags)]
    db.add(p)
    db.commit()
    db.refresh(p)
    return detail(p)


@router.patch("/places/{place_id}/status", response_model=PlaceDetail)
def moderate(place_id: uuid.UUID, data: StatusIn, _: User = Depends(require_role("admin")),
             db: Session = Depends(get_db)):
    """Модерація: лише адміністратор змінює статус."""
    p = PlaceRepository(db).get(place_id)
    if p is None:
        raise not_found("Place")
    p.status = data.status
    db.commit()
    return detail(p)


@router.get("/cities/{city_id}/package", response_model=CityPackage)
def city_package(city_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """FR-12: пакет міста для офлайн-використання."""
    city = CityRepository(db).get(city_id)
    if city is None:
        raise not_found("City")
    return CityPackage(city_id=city.city_id, name=city.name,
                       places=[detail(p) for p in PlaceRepository(db).by_city(city_id)])
