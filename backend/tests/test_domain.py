"""Модульні тести чистих функцій предметної області (app/domain.py). БД і сервер не потрібні."""
import pytest

from app.domain import Candidate, distance_m, plan_walk, recommendation_score, updated_weight

RYNOK = (49.8419, 24.0315)
OPERA = (49.8440, 24.0262)


def test_distance_same_point_is_zero():
    assert distance_m(*RYNOK, *RYNOK) == 0


def test_distance_rynok_to_opera():
    assert distance_m(*RYNOK, *OPERA) == pytest.approx(446, abs=2)


def test_score_sums_matching_tags_ordered_by_weight():
    score, reasons = recommendation_score(["бароко", "опера", "історія"], {"історія": 1.0, "опера": 0.8, "кава": 0.3})
    assert score == 1.8
    assert reasons == ["історія", "опера"]


def test_score_without_matches_is_zero():
    assert recommendation_score(["парк"], {"кава": 0.3}) == (0.0, [])


def test_high_rating_increases_weight():
    assert updated_weight(0.5, 5) == 0.7


def test_low_rating_decreases_weight():
    assert updated_weight(0.5, 1) == 0.3


def test_neutral_rating_keeps_weight():
    assert updated_weight(0.5, 3) == 0.5


def test_weight_stays_within_bounds():
    assert updated_weight(0.95, 5) == 1.0
    assert updated_weight(0.05, 1) == 0.0


def test_rating_out_of_range_rejected():
    with pytest.raises(ValueError):
        updated_weight(0.5, 6)


def test_walk_respects_time_budget():
    places = [Candidate("опера", *OPERA, 1.8), Candidate("ринок", 49.8419, 24.0316, 1.0),
              Candidate("цвинтар", 49.8318, 24.0556, 0.0)]
    plan = plan_walk(*RYNOK, places, budget_min=60)
    assert plan.est_min <= 60
    assert [c.key for c in plan.stops] == ["опера", "ринок"]  # цвинтар не вміщається в час
    assert plan_walk(*RYNOK, places, budget_min=10).stops == []
