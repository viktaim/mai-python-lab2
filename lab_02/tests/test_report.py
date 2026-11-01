import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from streamstats.models import Stats
from streamstats.report import (
    build_report,
    dump_report,
    top_error_sources,
    write_report,
)


def make_stats(error_sources: dict[str, int]) -> Stats:
    stats = Stats()
    stats.error_sources = Counter(error_sources)
    return stats


def test_top_error_sources_sorted_by_count_then_name() -> None:
    stats = make_stats({"web": 2, "db": 5, "auth": 2, "api": 2})

    assert top_error_sources(stats) == [("db", 5), ("api", 2), ("auth", 2), ("web", 2)]


def test_top_error_sources_does_not_depend_on_insertion_order() -> None:
    first = make_stats({"b": 1, "a": 1, "c": 1})
    second = make_stats({"c": 1, "a": 1, "b": 1})

    assert top_error_sources(first) == top_error_sources(second) == [("a", 1), ("b", 1), ("c", 1)]


def test_top_error_sources_default_is_five() -> None:
    stats = make_stats({name: 1 for name in "abcdefg"})

    assert len(top_error_sources(stats)) == 5


def test_top_error_sources_accepts_any_n() -> None:
    stats = make_stats({name: 1 for name in "abcdefg"})

    assert len(top_error_sources(stats, 3)) == 3
    assert len(top_error_sources(stats, 10)) == 7


def test_build_report_of_empty_stats_is_zero_report() -> None:
    report = build_report(Stats())

    assert report == {
        "total": 0,
        "skipped": 0,
        "levels": {},
        "sources": {},
        "top_error_sources": [],
        "first_timestamp": None,
        "last_timestamp": None,
    }


def test_build_report_converts_timestamps_to_iso() -> None:
    stats = Stats(total=2)
    stats.first_timestamp = datetime(2026, 10, 6, 10, 0, tzinfo=UTC)
    stats.last_timestamp = datetime(2026, 10, 6, 11, 0, tzinfo=UTC)

    report = build_report(stats)

    assert report["first_timestamp"] == "2026-10-06T10:00:00+00:00"
    assert report["last_timestamp"] == "2026-10-06T11:00:00+00:00"


def test_dump_report_keeps_cyrillic() -> None:
    stats = Stats(total=1)
    stats.sources = Counter({"апи": 1})

    text = dump_report(build_report(stats))

    assert "апи" in text
    assert "\\u" not in text


def test_write_report_writes_utf8_json(tmp_path: Path) -> None:
    stats = Stats(total=1)
    stats.sources = Counter({"апи": 1})
    file = tmp_path / "report.json"

    write_report(build_report(stats), file)

    data = json.loads(file.read_text(encoding="utf-8"))
    assert data["sources"] == {"апи": 1}