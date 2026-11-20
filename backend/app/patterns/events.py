"""Observer: реакції на взаємодію користувача з об’єктом.

До рефакторингу маршрутизатор POST /interactions сам викликав навчання профілю.
Тепер він лише публікує подію, а підписники реагують на неї незалежно один від одного.
Новий підписник додається без зміни маршрутизатора.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..services.recommendations import learn_from_rating

log = logging.getLogger("tourmate.events")


@dataclass
class InteractionEvent:
    db: Any
    user: Any
    place: Any
    interaction: Any
    profile_changes: dict[str, float] = field(default_factory=dict)


class InteractionObserver(ABC):
    @abstractmethod
    def notify(self, event: InteractionEvent) -> None:
        """Реакція на взаємодію."""


class InteractionPublisher:
    def __init__(self) -> None:
        self._observers: list[InteractionObserver] = []

    def subscribe(self, observer: InteractionObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def unsubscribe(self, observer: InteractionObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def publish(self, event: InteractionEvent) -> InteractionEvent:
        # Підписники виконуються в межах транзакції запиту: зміна профілю
        # фіксується разом із взаємодією або не фіксується зовсім.
        for observer in self._observers:
            observer.notify(event)
        return event


class ProfileLearner(InteractionObserver):
    """FR-10: оцінка змінює ваги тегів у профілі інтересів."""

    def notify(self, event: InteractionEvent) -> None:
        if event.interaction.type != "rate":
            return
        event.profile_changes.update(
            learn_from_rating(event.db, event.user, event.place, event.interaction.rating))


class InteractionLogger(InteractionObserver):
    """Журнал взаємодій для аналізу популярності об’єктів."""

    def notify(self, event: InteractionEvent) -> None:
        log.info("interaction type=%s place=%s user=%s", event.interaction.type,
                 event.place.place_id, event.user.user_id)


interaction_events = InteractionPublisher()
interaction_events.subscribe(ProfileLearner())
interaction_events.subscribe(InteractionLogger())
