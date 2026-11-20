"""Модульні тести патернів Strategy і Observer. БД не потрібна: об’єкти підміняються простими заглушками."""
from types import SimpleNamespace as NS

from app.patterns.events import InteractionEvent, InteractionObserver, InteractionPublisher, ProfileLearner
from app.patterns.ranking import (ContentBasedStrategy, PopularityStrategy, RankingContext,
                                  select_strategy)


def place(pid: str, *tags: str) -> NS:
    return NS(place_id=pid, tags=[NS(name=t) for t in tags])


OPERA, RYNOK, KAVA = place("opera", "опера", "історія"), place("rynok", "бароко", "історія"), place("kava", "кава")
CANDIDATES = [(RYNOK, 7), (KAVA, 101), (OPERA, 446)]


# ---------- Strategy ----------

def test_content_strategy_ranks_by_profile():
    ranked = ContentBasedStrategy().rank(CANDIDATES, RankingContext({"історія": 1.0, "опера": 0.8}))
    assert [r.place.place_id for r in ranked] == ["opera", "rynok", "kava"]
    assert ranked[0].score == 1.8 and ranked[0].reasons == ["історія", "опера"]


def test_popularity_strategy_ranks_by_interactions():
    ctx = RankingContext({}, popularity=lambda: {"kava": 5, "opera": 2})
    ranked = PopularityStrategy().rank(CANDIDATES, ctx)
    assert [r.place.place_id for r in ranked] == ["kava", "opera", "rynok"]
    assert all(r.score == 0.0 and r.reasons == [] for r in ranked)


def test_strategy_selected_by_profile_state():
    assert isinstance(select_strategy({}), PopularityStrategy)
    assert isinstance(select_strategy({"кава": 0.3}), ContentBasedStrategy)


def test_content_strategy_does_not_query_popularity():
    def fail():
        raise AssertionError("popularity must not be loaded")
    ContentBasedStrategy().rank(CANDIDATES, RankingContext({"кава": 1.0}, popularity=fail))


# ---------- Observer ----------

class Recorder(InteractionObserver):
    def __init__(self, log: list, name: str):
        self.log, self.name = log, name

    def notify(self, event):
        self.log.append(self.name)


def event(kind: str = "view") -> InteractionEvent:
    return InteractionEvent(db=None, user=NS(user_id="u"), place=OPERA, interaction=NS(type=kind, rating=None))


def test_publisher_notifies_subscribers_in_order():
    log, pub = [], InteractionPublisher()
    pub.subscribe(Recorder(log, "a"))
    pub.subscribe(Recorder(log, "b"))
    pub.publish(event())
    assert log == ["a", "b"]


def test_unsubscribed_observer_not_notified():
    log, pub, obs = [], InteractionPublisher(), None
    obs = Recorder(log, "a")
    pub.subscribe(obs)
    pub.unsubscribe(obs)
    pub.publish(event())
    assert log == []


def test_observer_subscribed_once():
    log, pub = [], InteractionPublisher()
    obs = Recorder(log, "a")
    pub.subscribe(obs)
    pub.subscribe(obs)
    pub.publish(event())
    assert log == ["a"]


def test_profile_learner_ignores_views():
    e = event("view")
    ProfileLearner().notify(e)  # db=None: звернення до БД спричинило б помилку
    assert e.profile_changes == {}
