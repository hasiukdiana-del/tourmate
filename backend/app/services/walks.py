"""Прогулянка за доступним часом (FR-11): жадібний вибір зупинок."""
from sqlalchemy.orm import Session

from ..domain import DWELL_MIN, WALK_SPEED_M_MIN, Candidate, distance_m, plan_walk
from ..models import Route, RouteStop, User
from ..schemas import RouteIn, RouteOut
from .recommendations import place_out, recommend


def build_walk(db: Session, user: User, data: RouteIn) -> RouteOut:
    recs = {r.place.place_id: r for r in recommend(db, user, data.lat, data.lon, limit=20)}
    plan = plan_walk(data.lat, data.lon,
                     [Candidate(pid, r.place.lat, r.place.lon, r.score) for pid, r in recs.items()],
                     data.duration_min)
    chosen = [recs[c.key] for c in plan.stops]
    meters, minutes = plan.total_m, plan.est_min

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
