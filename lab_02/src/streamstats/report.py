import json
from pathlib import Path
from typing import Any

from streamstats.models import Stats


def top_error_sources(stats: Stats, n: int = 5) -> list[tuple[str, int]]:
    """Возвращает n источников с наибольшим числом ошибок.

    При равном числе ошибок источники идут по алфавиту, чтобы порядок
    не зависел от того, в каком порядке читались файлы.
    """

    ordered = sorted(stats.error_sources.items(), key=lambda item: (-item[1], item[0]))
    return ordered[:n]


def build_report(stats: Stats, top_n: int = 5) -> dict[str, Any]:
    """Собирает из сводки словарь, который можно записать в JSON."""

    first = stats.first_timestamp
    last = stats.last_timestamp
    return {
        "total": stats.total,
        "skipped": stats.skipped,
        "levels": dict(sorted(stats.levels.items())),
        "sources": dict(sorted(stats.sources.items())),
        "top_error_sources": [
            {"source": source, "count": count} for source, count in top_error_sources(stats, top_n)
        ],
        "first_timestamp": first.isoformat() if first is not None else None,
        "last_timestamp": last.isoformat() if last is not None else None,
    }


def dump_report(report: dict[str, Any]) -> str:
    """Превращает отчёт в JSON-текст."""

    return json.dumps(report, ensure_ascii=False, indent=2)


def write_report(report: dict[str, Any], path: Path) -> None:
    """Записывает отчёт в файл."""

    path.write_text(dump_report(report) + "\n", encoding="utf-8")