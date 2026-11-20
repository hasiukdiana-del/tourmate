"""Чисті функції предметної області. Не залежать від БД і HTTP, тому покриваються модульними тестами."""
import math
from dataclasses import dataclass
from typing import Hashable, Iterable

EARTH_RADIUS_M = 6371000.0
WALK_SPEED_M_MIN = 75.0   # 4,5 км/год
DWELL_MIN = 15.0          # огляд однієї зупинки
LEARNING_STEP = 0.1       # зміна ваги тегу за один бал оцінки


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Відстань по поверхні Землі за формулою гаверсинусів, у метрах."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def recommendation_score(place_tags: Iterable[str], weights: dict[str, float]) -> tuple[float, list[str]]:
    """FR-08: релевантність дорівнює сумі ваг спільних тегів; спільні теги пояснюють рекомендацію."""
    matched = sorted({t for t in place_tags if t in weights}, key=lambda t: (-weights[t], t))
    return round(sum(weights[t] for t in matched), 2), matched


def updated_weight(old: float, rating: int) -> float:
    """FR-10: оцінка 4 або 5 підсилює тег, 1 або 2 послаблює; вага лишається в межах від 0 до 1."""
    if not 1 <= rating <= 5:
        raise ValueError("rating must be between 1 and 5")
    return round(min(1.0, max(0.0, old + (rating - 3) * LEARNING_STEP)), 2)


@dataclass(frozen=True)
class Candidate:
    key: Hashable
    lat: float
    lon: float
    score: float


@dataclass(frozen=True)
class WalkPlan:
    stops: list[Candidate]
    total_m: float
    est_min: float


def plan_walk(lat: float, lon: float, candidates: list[Candidate], budget_min: float) -> WalkPlan:
    """FR-11: жадібний вибір зупинки з найбільшою релевантністю на хвилину, доки вистачає часу."""
    if budget_min <= 0:
        raise ValueError("budget must be positive")
    left = list(candidates)
    stops: list[Candidate] = []
    minutes = meters = 0.0
    while left:
        best, best_value, best_d = None, -1.0, 0.0
        for c in left:
            d = distance_m(lat, lon, c.lat, c.lon)
            cost = d / WALK_SPEED_M_MIN + DWELL_MIN
            if minutes + cost > budget_min:
                continue
            value = (c.score + 0.2) / cost
            if value > best_value:
                best, best_value, best_d = c, value, d
        if best is None:
            break
        stops.append(best)
        meters += best_d
        minutes += best_d / WALK_SPEED_M_MIN + DWELL_MIN
        lat, lon = best.lat, best.lon
        left.remove(best)
    return WalkPlan(stops, meters, minutes)
