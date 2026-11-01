import logging
from collections.abc import Sequence
from pathlib import Path

from streamstats.errors import InvalidEventError
from streamstats.models import Event, Stats
from streamstats.parsers import get_parser

logger = logging.getLogger(__name__)

ERROR_LEVELS = {"ERROR", "CRITICAL"}


def update_stats(stats: Stats, event: Event) -> None:
    """Вносит одно событие в сводку."""
    stats.total += 1
    stats.levels[event.level] += 1
    stats.sources[event.source] += 1

    if event.level in ERROR_LEVELS:
        stats.error_sources[event.source] += 1

    if stats.first_timestamp is None or event.timestamp < stats.first_timestamp:
        stats.first_timestamp = event.timestamp
    if stats.last_timestamp is None or event.timestamp > stats.last_timestamp:
        stats.last_timestamp = event.timestamp


def analyze(paths: Sequence[Path], fmt: str, *, skip_invalid: bool = False) -> Stats:
    """Читает файлы потоком и возвращает одну общую сводку."""

    stats = Stats()
    parser = get_parser(fmt)

    def skip(error: InvalidEventError) -> None:
        stats.skipped += 1
        logger.warning("%s, строка %s: %s", error.path, error.line_number, error)

    on_error = skip if skip_invalid else None

    for path in paths:
        for event in parser(path, on_error):
            update_stats(stats, event)
    return stats