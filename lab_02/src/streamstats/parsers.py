import csv
import json
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path

from streamstats.errors import (
    InvalidEventError,
    InvalidTimestampError,
    UnsupportedFormatError,
)
from streamstats.models import Event

ErrorHandler = Callable[[InvalidEventError], None]

LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
FIELDS = ("timestamp", "level", "source", "message")


def parse_timestamp(text: str) -> datetime:
    """Превращает строку в дату."""

    try:
        return datetime.fromisoformat(text)
    except (TypeError, ValueError) as exc:
        raise InvalidTimestampError(
            f"Временная метка {text!r} не соответствует формату ISO 8601",
            field="timestamp",
        ) from exc


def make_event(data: object) -> Event:
    """Проверяет словарь с данными строки и собирает из него событие."""

    if not isinstance(data, dict):
        raise InvalidEventError("Строка должна быть объектом с полями события")
    for name in FIELDS:
        if data.get(name) is None:
            raise InvalidEventError(f"Отсутствует обязательное поле {name!r}", field=name)

    timestamp = parse_timestamp(data["timestamp"])
    level = data["level"]
    if not isinstance(level, str) or level not in LEVELS:
        raise InvalidEventError(
            f"Недопустимый уровень {level!r}, ожидается один из: {sorted(LEVELS)}",
            field="level",
        )
    source = data["source"]
    if not isinstance(source, str) or not source.strip():
        raise InvalidEventError("Поле 'source' должно быть непустой строкой", field="source")
    message = data["message"]
    if not isinstance(message, str):
        raise InvalidEventError("Поле 'message' должно быть строкой", field="message")

    return Event(timestamp=timestamp, level=level, source=source, message=message)


def parse_csv(path: Path, on_error: ErrorHandler | None = None) -> Iterator[Event]:
    """Читает CSV-файл по одной строке и отдаёт события по очереди.

    Если on_error не передан, первая плохая строка останавливает чтение.
    Если передан, плохая строка отдаётся в on_error, а чтение продолжается.
    """

    with open(path, encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                event = make_event(row)
            except InvalidEventError as exc:
                exc.line_number = reader.line_num
                exc.path = str(path)
                if on_error is None:
                    raise
                on_error(exc)
                continue
            yield event


def parse_jsonl(path: Path, on_error: ErrorHandler | None = None) -> Iterator[Event]:
    """Читает JSONL-файл по одной строке и отдаёт события по очереди.

    Правила для on_error такие же, как в parse_csv.
    """

    with open(path, encoding="utf-8") as file:
        for number, text in enumerate(file, start=1):
            if not text.strip():
                continue
            try:
                try:
                    data = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise InvalidEventError(f"Повреждённый JSON: {exc.msg}") from exc
                event = make_event(data)
            except InvalidEventError as exc:
                exc.line_number = number
                exc.path = str(path)
                if on_error is None:
                    raise
                on_error(exc)
                continue
            yield event


PARSERS = {"csv": parse_csv, "jsonl": parse_jsonl}


def get_parser(fmt: str) -> Callable[[Path, ErrorHandler | None], Iterator[Event]]:
    """Возвращает функцию-парсер для указанного формата."""

    try:
        return PARSERS[fmt]
    except KeyError as exc:
        raise UnsupportedFormatError(
            f"Неподдерживаемый формат {fmt!r}, ожидается один из: {sorted(PARSERS)}"
        ) from exc