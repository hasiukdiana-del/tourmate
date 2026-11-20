"""Рекомендації (FR-07, FR-08) і навчання профілю інтересів (FR-10)."""
from sqlalchemy.orm import Session

from ..domain import updated_weight

from ..models import Place, User, UserInterest
from ..repositories import InterestRepository, PlaceRepository
from ..patterns.ranking import RankingContext, RankingStrategy, select_strategy
from ..schemas import PlaceOut, RecommendationOut

SEARCH_RADIUS_M = 5000


def place_out(p: Place, distance_m: int | None = None) -> PlaceOut:
    return PlaceOut(
        place_id=p.place_id, name=p.name, category=p.category.name,
        lat=float(p.lat), lon=float(p.lon), tags=[t.name for t in p.tags], distance_m=distance_m,
    )


class Recommender:
    """Контекст патерна Strategy: збирає кандидатів і делегує ранжування стратегії."""

    def __init__(self, strategy: RankingStrategy | None = None):
        self.strategy = strategy  # None: стратегія вибирається за станом профілю

    def recommend(self, db: Session, user: User, lat: float, lon: float, limit: int,
                  radius: int = SEARCH_RADIUS_M) -> list[RecommendationOut]:
        places = PlaceRepository(db)
        weights = InterestRepository(db).weights(user)
        rated = places.rated_by(user.user_id)
        candidates = [(p, d) for p, d in places.nearby(lat, lon, radius, None, None)
                      if p.place_id not in rated]
        strategy = self.strategy or select_strategy(weights)
        ranked = strategy.rank(candidates, RankingContext(weights, places.popularity))
        return [RecommendationOut(place=place_out(r.place, r.distance_m), score=r.score, reason_tags=r.reasons)
                for r in ranked[:limit]]


def recommend(db: Session, user: User, lat: float, lon: float, limit: int,
              radius: int = SEARCH_RADIUS_M) -> list[RecommendationOut]:
    return Recommender().recommend(db, user, lat, lon, limit, radius)


def learn_from_rating(db: Session, user: User, place: Place, rating: int) -> dict[str, float]:
    """Оцінка 4 або 5 підсилює теги об’єкта на 0,1 або 0,2, оцінка 1 або 2 послаблює."""
    changes: dict[str, float] = {}
    interests = InterestRepository(db)
    for tag in place.tags:
        row = interests.get(user.user_id, tag.tag_id)
        old = row.weight if row else 0.0
        new = updated_weight(old, rating)
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
