"""Прогулянка за доступним часом (FR-11): жадібний вибір зупинок."""
import math

from sqlalchemy.orm import Session

from ..models import Route, RouteStop, User
from ..schemas import RouteIn, RouteOut
from .recommendations import place_out, recommend

WALK_SPEED_M_MIN = 75.0   # 4,5 км/год
DWELL_MIN = 15.0          # огляд однієї зупинки


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def build_walk(db: Session, user: User, data: RouteIn) -> RouteOut:
    candidates = recommend(db, user, data.lat, data.lon, limit=20)
    lat, lon, minutes, meters = data.lat, data.lon, 0.0, 0.0
    chosen = []
    while candidates:
        best, best_value, best_d = None, -1.0, 0.0
        for c in candidates:
            d = distance_m(lat, lon, c.place.lat, c.place.lon)
            cost = d / WALK_SPEED_M_MIN + DWELL_MIN
            if minutes + cost > data.duration_min:
                continue  # не вміщається в доступний час
            value = (c.score + 0.2) / cost  # релевантність на хвилину
            if value > best_value:
                best, best_value, best_d = c, value, d
        if best is None:
            break
        chosen.append(best)
        meters += best_d
        minutes += best_d / WALK_SPEED_M_MIN + DWELL_MIN
        lat, lon = best.place.lat, best.place.lon
        candidates.remove(best)

    route = Route(user_id=user.user_id, start_lat=data.lat, start_lon=data.lon, duration_min=data.duration_min)
    route.stops = [RouteStop(position=i + 1, place_id=c.place.place_id) for i, c in enumerate(chosen)]
    db.add(route)
    db.commit()
    return RouteOut(
        route_id=route.route_id, duration_min=data.duration_min, total_m=round(meters),
        est_min=round(minutes), stops=[c.place for c in chosen],
    )


def route_out(route: Route) -> RouteOut:
    lat, lon = float(route.start_lat), float(route.start_lon)
    meters = 0.0
    for s in route.stops:
        meters += distance_m(lat, lon, float(s.place.lat), float(s.place.lon))
        lat, lon = float(s.place.lat), float(s.place.lon)
    return RouteOut(
        route_id=route.route_id, duration_min=route.duration_min, total_m=round(meters),
        est_min=round(meters / WALK_SPEED_M_MIN + DWELL_MIN * len(route.stops)),
        stops=[place_out(s.place) for s in route.stops],
    )
