from datetime import datetime

from streamstats.errors import InvalidTimestampError


def parse_timestamp(text: str) -> datetime:
    """Превращает строку в дату"""

    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise InvalidTimestampError(f"Временная метка {text!r} не соответствует формату ISO 8601") from exc