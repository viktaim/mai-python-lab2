import csv
import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

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


def parse_csv(path: Path) -> Iterator[Event]:
    """Читает CSV-файл по одной строке и отдаёт события по очереди."""

    with open(path, encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                event = make_event(row)
            except InvalidEventError as exc:
                exc.line_number = reader.line_num
                exc.path = str(path)
                raise
            yield event


def parse_jsonl(path: Path) -> Iterator[Event]:
    """Читает JSONL-файл по одной строке и отдаёт события по очереди."""

    with open(path, encoding="utf-8") as file:
        for number, text in enumerate(file, start=1):
            if not text.strip():
                continue
            try:
                data = json.loads(text)
                event = make_event(data)
            except json.JSONDecodeError as exc:
                raise InvalidEventError(f"Повреждённый JSON: {exc.msg}", number, str(path)) from exc
            except InvalidEventError as exc:
                exc.line_number = number
                exc.path = str(path)
                raise
            yield event