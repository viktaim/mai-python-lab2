from datetime import datetime

from streamstats.errors import *
from streamstats.models import Event


def parse_timestamp(text: str) -> datetime:
    """Превращает строку в дату"""

    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise InvalidTimestampError(f"Временная метка {text!r} не соответствует формату ISO 8601") from exc


LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
FIELDS = ("timestamp", "level", "source", "message")


def make_event(data):
    """Проверяет словарь с данными строки и собирает из него событие."""
    
    for elem in FIELDS:
        if data.get(elem) is None:
            raise InvalidEventError(f"Отсутствует обязательное поле {elem!r}")
    timestamp = parse_timestamp(data["timestamp"])
    if data["level"] not in LEVELS:
        raise InvalidEventError(f"Недопустимый уровень {data["level"]!r}, ожидается один из: {sorted(LEVELS)}")
    if not data["source"].strip():
        raise InvalidEventError("Поле 'source' не должно быть пустым")

    return Event(timestamp=timestamp, level=data["level"], source=data["source"], message=data["message"])