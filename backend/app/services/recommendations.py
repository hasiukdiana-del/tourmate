"""Рекомендації (FR-07, FR-08) і навчання профілю інтересів (FR-10)."""
from sqlalchemy.orm import Session

from ..models import Place, User, UserInterest
from ..repositories import InterestRepository, PlaceRepository
from ..schemas import PlaceOut, RecommendationOut

SEARCH_RADIUS_M = 5000


def place_out(p: Place, distance_m: int | None = None) -> PlaceOut:
    return PlaceOut(
        place_id=p.place_id, name=p.name, category=p.category.name,
        lat=float(p.lat), lon=float(p.lon), tags=[t.name for t in p.tags], distance_m=distance_m,
    )


def recommend(db: Session, user: User, lat: float, lon: float, limit: int) -> list[RecommendationOut]:
    places = PlaceRepository(db)
    weights = InterestRepository(db).weights(user)
    rated = places.rated_by(user.user_id)
    candidates = [(p, d) for p, d in places.nearby(lat, lon, SEARCH_RADIUS_M, None, None)
                  if p.place_id not in rated]

    if not weights:
        # NFR-09: без профілю інтересів повертаються популярні об’єкти
        pop = places.popularity()
        candidates.sort(key=lambda pd: (-pop.get(pd[0].place_id, 0), pd[1]))
        return [RecommendationOut(place=place_out(p, d), score=0.0, reason_tags=[]) for p, d in candidates[:limit]]

    result = []
    for p, d in candidates:
        matched = sorted((t.name for t in p.tags if t.name in weights), key=lambda t: -weights[t])
        score = round(sum(weights[t] for t in matched), 2)
        result.append(RecommendationOut(place=place_out(p, d), score=score, reason_tags=matched))
    # релевантність, за рівності ближчий об’єкт
    result.sort(key=lambda r: (-r.score, r.place.distance_m))
    return result[:limit]


def learn_from_rating(db: Session, user: User, place: Place, rating: int) -> dict[str, float]:
    """Оцінка 4 або 5 підсилює теги об’єкта на 0,1 або 0,2, оцінка 1 або 2 послаблює."""
    delta = (rating - 3) * 0.1
    changes: dict[str, float] = {}
    if delta == 0:
        return changes
    interests = InterestRepository(db)
    for tag in place.tags:
        row = interests.get(user.user_id, tag.tag_id)
        old = row.weight if row else 0.0
        new = round(min(1.0, max(0.0, old + delta)), 2)
        if new == old:
            continue
        if row is None:
            db.add(UserInterest(user_id=user.user_id, tag_id=tag.tag_id, weight=new))
        elif new == 0:
            db.delete(row)
        else:
            row.weight = new
        changes[tag.name] = round(new - old, 2)
    return changes
