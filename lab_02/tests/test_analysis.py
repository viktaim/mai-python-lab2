import inspect
import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
from streamstats.analysis import analyze, update_stats
from streamstats.errors import InvalidEventError
from streamstats.models import Event, Stats
from streamstats.parsers import parse_csv

CSV_HEADER = "timestamp,level,source,message\n"


def ts(minute: int) -> datetime:
    return datetime(2026, 10, 6, 10, minute, tzinfo=UTC)


def iso(minute: int) -> str:
    return ts(minute).isoformat()


def write_csv(path: Path, *rows: str) -> Path:
    path.write_text(CSV_HEADER + "".join(row + "\n" for row in rows), encoding="utf-8")
    return path


def write_jsonl(path: Path, *lines: str) -> Path:
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return path


def jsonl(minute: int, level: str, source: str, message: str = "m") -> str:
    return (
        f'{{"timestamp": "{iso(minute)}", "level": "{level}", '
        f'"source": "{source}", "message": "{message}"}}'
    )


def test_update_stats_counts_one_event() -> None:
    stats = Stats()

    update_stats(stats, Event(ts(5), "INFO", "api", "hello"))

    assert stats.total == 1
    assert stats.levels == {"INFO": 1}
    assert stats.sources == {"api": 1}
    assert stats.first_timestamp == ts(5)
    assert stats.last_timestamp == ts(5)


def test_only_error_and_critical_go_to_error_sources() -> None:
    stats = Stats()

    for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        update_stats(stats, Event(ts(0), level, "db", "m"))

    assert stats.error_sources == {"db": 2}
    assert stats.sources == {"db": 5}


def test_first_and_last_timestamp_ignore_order() -> None:
    stats = Stats()

    for minute in (7, 3, 9, 5):
        update_stats(stats, Event(ts(minute), "INFO", "api", "m"))

    assert stats.first_timestamp == ts(3)
    assert stats.last_timestamp == ts(9)


@pytest.mark.parametrize("fmt", ["csv", "jsonl"])
def test_empty_file_gives_zero_stats(fmt: str, tmp_path: Path) -> None:
    file = tmp_path / "empty"
    file.write_text("", encoding="utf-8")

    stats = analyze([file], fmt)

    assert stats == Stats()


def test_csv_and_jsonl_give_same_stats(tmp_path: Path) -> None:
    csv_file = write_csv(
        tmp_path / "events.csv",
        f"{iso(0)},INFO,api,m",
        f"{iso(1)},ERROR,db,m",
        f"{iso(2)},CRITICAL,db,m",
    )
    jsonl_file = write_jsonl(
        tmp_path / "events.jsonl",
        jsonl(0, "INFO", "api"),
        jsonl(1, "ERROR", "db"),
        jsonl(2, "CRITICAL", "db"),
    )

    assert analyze([csv_file], "csv") == analyze([jsonl_file], "jsonl")


def test_multiple_files_are_aggregated(tmp_path: Path) -> None:
    first = write_jsonl(tmp_path / "a.jsonl", jsonl(5, "INFO", "api"), jsonl(6, "ERROR", "db"))
    second = write_jsonl(tmp_path / "b.jsonl", jsonl(1, "ERROR", "db"), jsonl(9, "INFO", "web"))

    stats = analyze([first, second], "jsonl")

    assert stats.total == 4
    assert stats.levels == {"INFO": 2, "ERROR": 2}
    assert stats.sources == {"api": 1, "db": 2, "web": 1}
    assert stats.error_sources == {"db": 2}
    assert stats.first_timestamp == ts(1)
    assert stats.last_timestamp == ts(9)


def test_invalid_line_stops_analysis_by_default(tmp_path: Path) -> None:
    file = write_jsonl(
        tmp_path / "events.jsonl",
        jsonl(0, "INFO", "api"),
        "{not json}",
        jsonl(2, "INFO", "api"),
    )

    with pytest.raises(InvalidEventError) as excinfo:
        analyze([file], "jsonl")

    assert excinfo.value.line_number == 2


def test_skip_invalid_keeps_good_lines_and_counts_skipped(tmp_path: Path, caplog) -> None:
    file = write_jsonl(
        tmp_path / "events.jsonl",
        jsonl(0, "INFO", "api"),
        "{not json}",
        jsonl(2, "TRACE", "api"),
        jsonl(3, "ERROR", "db"),
    )
    caplog.set_level(logging.WARNING)

    stats = analyze([file], "jsonl", skip_invalid=True)

    assert stats.total == 2
    assert stats.skipped == 2
    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 2
    assert "2" in warnings[0].getMessage()


def test_skip_invalid_counts_skipped_across_files(tmp_path: Path) -> None:
    first = write_csv(tmp_path / "a.csv", f"{iso(0)},INFO,api,m", "bad,INFO,api,m")
    second = write_csv(tmp_path / "b.csv", f"{iso(1)},INFO,api,m", f"{iso(2)},TRACE,api,m")

    stats = analyze([first, second], "csv", skip_invalid=True)

    assert stats.total == 2
    assert stats.skipped == 2


def test_source_file_is_not_modified(tmp_path: Path) -> None:
    file = write_jsonl(tmp_path / "events.jsonl", jsonl(0, "INFO", "api"), "{not json}")
    before = file.read_bytes()

    analyze([file], "jsonl", skip_invalid=True)

    assert file.read_bytes() == before


def test_parser_is_lazy_generator(tmp_path: Path) -> None:
    file = write_csv(tmp_path / "events.csv", f"{iso(0)},INFO,api,first", "bad,INFO,api,broken")

    events = parse_csv(file)

    assert inspect.isgenerator(events)
    assert next(events).message == "first"
    with pytest.raises(InvalidEventError):
        next(events)