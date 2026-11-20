"""Strategy: взаємозамінні алгоритми ранжування рекомендацій.

До рефакторингу обидва алгоритми були гілками if/else у функції recommend().
Тепер кожен алгоритм є окремим класом зі спільним інтерфейсом, а сервіс
працює з інтерфейсом і не залежить від конкретної реалізації.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from ..domain import recommendation_score


@dataclass(frozen=True)
class Ranked:
    place: Any
    distance_m: int
    score: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class RankingContext:
    weights: dict[str, float]
    # Популярність рахується запитом до БД, тому передається функцією і викликається лише за потреби.
    popularity: Callable[[], dict] = dict


class RankingStrategy(ABC):
    name: str

    @abstractmethod
    def rank(self, candidates: list[tuple[Any, int]], ctx: RankingContext) -> list[Ranked]:
        """Повертає кандидатів у порядку рекомендації."""


class ContentBasedStrategy(RankingStrategy):
    """FR-07, FR-08: релевантність за збігом тегів з профілем; за рівності ближчий об’єкт."""
    name = "content"

    def rank(self, candidates, ctx):
        ranked = []
        for place, distance in candidates:
            score, reasons = recommendation_score((t.name for t in place.tags), ctx.weights)
            ranked.append(Ranked(place, distance, score, reasons))
        return sorted(ranked, key=lambda r: (-r.score, r.distance_m))


class PopularityStrategy(RankingStrategy):
    """NFR-09: без профілю інтересів об’єкти впорядковуються за кількістю взаємодій."""
    name = "popular"

    def rank(self, candidates, ctx):
        pop = ctx.popularity()
        ordered = sorted(candidates, key=lambda pd: (-pop.get(pd[0].place_id, 0), pd[1]))
        return [Ranked(place, distance, 0.0) for place, distance in ordered]


def select_strategy(weights: dict[str, float]) -> RankingStrategy:
    """Вибір алгоритму за станом профілю: холодний старт розв’язує популярність."""
    return ContentBasedStrategy() if weights else PopularityStrategy()
