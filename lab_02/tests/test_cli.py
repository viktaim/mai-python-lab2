import json
import os
import subprocess
import sys
from pathlib import Path

GOOD_1 = '{"timestamp": "2026-10-06T10:00:00+00:00", "level": "INFO", "source": "api", "message": "m"}'
GOOD_2 = '{"timestamp": "2026-10-06T10:05:00+00:00", "level": "ERROR", "source": "db", "message": "m"}'
GOOD_RU = '{"timestamp": "2026-10-06T10:09:00+00:00", "level": "ERROR", "source": "апи", "message": "Привет"}'


def run_cli(*args: object) -> subprocess.CompletedProcess[str]:
    """Запускает `python -m streamstats ...` как отдельный процесс."""

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, "-m", "streamstats", *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )


def write_lines(path: Path, *lines: str) -> Path:
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return path


def test_help_works() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "analyze" in result.stdout


def test_cli_writes_report_for_several_files(tmp_path: Path) -> None:
    first = write_lines(tmp_path / "a.jsonl", GOOD_1)
    second = write_lines(tmp_path / "b.jsonl", GOOD_2, GOOD_RU)
    report_file = tmp_path / "report.json"

    result = run_cli("analyze", first, second, "--format", "jsonl", "--output", report_file)

    assert result.returncode == 0
    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["total"] == 3
    assert report["skipped"] == 0
    assert report["sources"] == {"api": 1, "db": 1, "апи": 1}
    assert report["top_error_sources"] == [
        {"source": "db", "count": 1},
        {"source": "апи", "count": 1},
    ]
    assert report["first_timestamp"] == "2026-10-06T10:00:00+00:00"
    assert report["last_timestamp"] == "2026-10-06T10:09:00+00:00"
    assert "апи" in report_file.read_text(encoding="utf-8")


def test_cli_prints_report_to_stdout_without_output(tmp_path: Path) -> None:
    file = write_lines(tmp_path / "events.jsonl", GOOD_1)

    result = run_cli("analyze", file, "--format", "jsonl")

    assert result.returncode == 0
    assert json.loads(result.stdout)["total"] == 1


def test_cli_stops_with_code_2_on_invalid_line(tmp_path: Path) -> None:
    file = write_lines(tmp_path / "events.jsonl", GOOD_1, GOOD_2, "{not json}", GOOD_1)
    report_file = tmp_path / "report.json"

    result = run_cli("analyze", file, "--format", "jsonl", "--output", report_file)

    assert result.returncode == 2
    assert "events.jsonl" in result.stderr
    assert "строка 3" in result.stderr
    assert not report_file.exists()


def test_cli_skip_invalid_processes_remaining_lines(tmp_path: Path) -> None:
    file = write_lines(tmp_path / "events.jsonl", GOOD_1, "{not json}", GOOD_2)
    report_file = tmp_path / "report.json"

    result = run_cli("analyze", file, "--format", "jsonl", "--skip-invalid", "--output", report_file)

    assert result.returncode == 0
    assert "WARNING" in result.stderr
    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["total"] == 2
    assert report["skipped"] == 1


def test_cli_reports_missing_input_file(tmp_path: Path) -> None:
    result = run_cli("analyze", tmp_path / "missing.csv", "--format", "csv")

    assert result.returncode == 2
    assert "missing.csv" in result.stderr


def test_cli_refuses_to_overwrite_input_file(tmp_path: Path) -> None:
    file = write_lines(tmp_path / "events.jsonl", GOOD_1)
    before = file.read_bytes()

    result = run_cli("analyze", file, "--format", "jsonl", "--output", file)

    assert result.returncode == 2
    assert file.read_bytes() == before


def test_cli_rejects_unknown_format(tmp_path: Path) -> None:
    file = write_lines(tmp_path / "events.jsonl", GOOD_1)

    result = run_cli("analyze", file, "--format", "xml")

    assert result.returncode == 2