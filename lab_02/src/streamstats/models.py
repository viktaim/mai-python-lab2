from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Event:
    """Одно событие из журнала."""

    timestamp: datetime
    level: str
    source: str
    message: str


@dataclass
class Stats:
    """Сводка по прочитанным событиям."""

    total: int = 0  # колличество обработанных событий
    skipped: int = 0  # колличество пропущенных строк
    levels: Counter = field(default_factory=Counter)
    sources: Counter = field(default_factory=Counter)
    error_sources: Counter = field(default_factory=Counter)
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None