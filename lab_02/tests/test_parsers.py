import json
from pathlib import Path

import pytest

from streamstats.errors import (
    InvalidEventError,
    InvalidTimestampError,
    UnsupportedFormatError,
)
from streamstats.parsers import get_parser, parse_csv, parse_jsonl

CSV_HEADER = "timestamp,level,source,message\n"
GOOD_TS = "2026-10-06T10:00:00+00:00"


def write_csv(path: Path, *rows: str) -> Path:
    path.write_text(CSV_HEADER + "".join(row + "\n" for row in rows), encoding="utf-8")
    return path


def write_jsonl(path: Path, *lines: str) -> Path:
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return path


def jsonl_line(**overrides: object) -> str:
    data = {"timestamp": GOOD_TS, "level": "INFO", "source": "api", "message": "ok"}
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False)


def test_parse_csv_reads_valid_row(tmp_path: Path) -> None:
    file = write_csv(tmp_path / "events.csv", f"{GOOD_TS},INFO,api,Service started")

    events = list(parse_csv(file))

    assert len(events) == 1
    assert events[0].level == "INFO"
    assert events[0].source == "api"
    assert events[0].message == "Service started"
    assert events[0].timestamp.isoformat() == GOOD_TS


def test_parse_jsonl_reads_valid_row(tmp_path: Path) -> None:
    file = write_jsonl(tmp_path / "events.jsonl", jsonl_line(message="Service started"))

    events = list(parse_jsonl(file))

    assert len(events) == 1
    assert events[0].level == "INFO"
    assert events[0].source == "api"
    assert events[0].message == "Service started"
    assert events[0].timestamp.isoformat() == GOOD_TS


@pytest.mark.parametrize("parser", [parse_csv, parse_jsonl])
def test_empty_file_gives_no_events(parser, tmp_path: Path) -> None:
    file = tmp_path / "empty"
    file.write_text("", encoding="utf-8")

    assert list(parser(file)) == []


def test_csv_with_only_header_gives_no_events(tmp_path: Path) -> None:
    file = write_csv(tmp_path / "events.csv")

    assert list(parse_csv(file)) == []


def test_jsonl_ignores_blank_lines(tmp_path: Path) -> None:
    file = write_jsonl(tmp_path / "events.jsonl", jsonl_line(), "", jsonl_line())

    assert len(list(parse_jsonl(file))) == 2


def test_csv_bad_timestamp_reports_line_and_field(tmp_path: Path) -> None:
    file = write_csv(
        tmp_path / "events.csv",
        f"{GOOD_TS},INFO,api,ok",
        "not-a-date,ERROR,db,bad",
    )

    with pytest.raises(InvalidTimestampError) as excinfo:
        list(parse_csv(file))

    assert excinfo.value.line_number == 3
    assert excinfo.value.field == "timestamp"
    assert excinfo.value.path == str(file)


def test_jsonl_broken_json_reports_line(tmp_path: Path) -> None:
    file = write_jsonl(tmp_path / "events.jsonl", jsonl_line(), "{not json}", jsonl_line())

    with pytest.raises(InvalidEventError) as excinfo:
        list(parse_jsonl(file))

    assert excinfo.value.line_number == 2
    assert excinfo.value.path == str(file)


def test_jsonl_bad_timestamp_reports_line_and_field(tmp_path: Path) -> None:
    file = write_jsonl(tmp_path / "events.jsonl", jsonl_line(timestamp="not-a-date"))

    with pytest.raises(InvalidTimestampError) as excinfo:
        list(parse_jsonl(file))

    assert excinfo.value.line_number == 1
    assert excinfo.value.field == "timestamp"


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"level": "TRACE"}, "level"),
        ({"level": 5}, "level"),
        ({"source": ""}, "source"),
        ({"source": "   "}, "source"),
        ({"message": 3}, "message"),
    ],
)
def test_jsonl_invalid_fields_name_the_field(tmp_path: Path, overrides: dict, field: str) -> None:
    file = write_jsonl(tmp_path / "events.jsonl", jsonl_line(**overrides))

    with pytest.raises(InvalidEventError) as excinfo:
        list(parse_jsonl(file))

    assert excinfo.value.field == field
    assert excinfo.value.line_number == 1


def test_jsonl_missing_field_is_reported(tmp_path: Path) -> None:
    file = write_jsonl(tmp_path / "events.jsonl", '{"timestamp": "2026-10-06T10:00:00+00:00"}')

    with pytest.raises(InvalidEventError) as excinfo:
        list(parse_jsonl(file))

    assert excinfo.value.field == "level"


def test_jsonl_line_that_is_not_an_object_is_rejected(tmp_path: Path) -> None:
    file = write_jsonl(tmp_path / "events.jsonl", "[1, 2, 3]")

    with pytest.raises(InvalidEventError):
        list(parse_jsonl(file))


def test_csv_invalid_level_and_empty_source(tmp_path: Path) -> None:
    bad_level = write_csv(tmp_path / "level.csv", f"{GOOD_TS},TRACE,api,msg")
    empty_source = write_csv(tmp_path / "source.csv", f"{GOOD_TS},INFO,,msg")

    with pytest.raises(InvalidEventError) as level_info:
        list(parse_csv(bad_level))
    with pytest.raises(InvalidEventError) as source_info:
        list(parse_csv(empty_source))

    assert level_info.value.field == "level"
    assert source_info.value.field == "source"


def test_csv_unicode_message(tmp_path: Path) -> None:
    file = write_csv(tmp_path / "events.csv", f'{GOOD_TS},INFO,апи,"Привет, мир"')

    events = list(parse_csv(file))

    assert events[0].source == "апи"
    assert events[0].message == "Привет, мир"


def test_jsonl_unicode_plain_and_escaped(tmp_path: Path) -> None:
    plain = jsonl_line(message="Привет, мир")
    escaped = json.dumps(
        {"timestamp": GOOD_TS, "level": "INFO", "source": "api", "message": "Привет, мир"},
        ensure_ascii=True,
    )
    assert "\\u" in escaped
    file = write_jsonl(tmp_path / "events.jsonl", plain, escaped)

    events = list(parse_jsonl(file))

    assert [event.message for event in events] == ["Привет, мир", "Привет, мир"]


def test_csv_on_error_skips_bad_rows(tmp_path: Path) -> None:
    file = write_csv(
        tmp_path / "events.csv",
        f"{GOOD_TS},INFO,api,first",
        "not-a-date,ERROR,db,bad",
        f"{GOOD_TS},WARNING,db,third",
    )
    errors: list[InvalidEventError] = []

    events = list(parse_csv(file, on_error=errors.append))

    assert [event.message for event in events] == ["first", "third"]
    assert len(errors) == 1
    assert errors[0].line_number == 3


def test_jsonl_on_error_skips_bad_lines(tmp_path: Path) -> None:
    file = write_jsonl(
        tmp_path / "events.jsonl",
        jsonl_line(message="first"),
        "{not json}",
        jsonl_line(level="TRACE"),
        jsonl_line(message="last"),
    )
    errors: list[InvalidEventError] = []

    events = list(parse_jsonl(file, on_error=errors.append))

    assert [event.message for event in events] == ["first", "last"]
    assert [error.line_number for error in errors] == [2, 3]


def test_get_parser_returns_matching_function() -> None:
    assert get_parser("csv") is parse_csv
    assert get_parser("jsonl") is parse_jsonl


def test_get_parser_rejects_unknown_format() -> None:
    with pytest.raises(UnsupportedFormatError):
        get_parser("xml")