import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from streamstats.analysis import analyze
from streamstats.errors import CLIConfigError, InvalidEventError, StreamStatsError
from streamstats.parsers import PARSERS
from streamstats.report import build_report, dump_report, write_report

EXIT_OK = 0
EXIT_ERROR = 2


def build_arg_parser() -> argparse.ArgumentParser:
    """Описывает аргументы командной строки."""

    parser = argparse.ArgumentParser(
        prog="streamstats",
        description="Потоковый анализатор файлов событий.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="построить статистический отчёт")
    analyze_parser.add_argument("inputs", nargs="+", type=Path, metavar="INPUT", help="входные файлы")
    analyze_parser.add_argument(
        "--format", dest="fmt", required=True, choices=sorted(PARSERS), help="формат входных файлов"
    )
    analyze_parser.add_argument(
        "--output", type=Path, metavar="REPORT.json", help="куда записать отчёт (по умолчанию в stdout)"
    )
    analyze_parser.add_argument(
        "--skip-invalid", action="store_true", help="пропускать повреждённые строки вместо остановки"
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    """Проверяет аргументы, которые argparse проверить не может."""

    for path in args.inputs:
        if not path.is_file():
            raise CLIConfigError(f"Входной файл не найден: {path}")
    if args.output is not None:
        if not args.output.parent.is_dir():
            raise CLIConfigError(f"Папка для отчёта не существует: {args.output.parent}")
        if args.output.resolve() in {path.resolve() for path in args.inputs}:
            raise CLIConfigError("Файл отчёта совпадает с входным файлом")


def main(argv: Sequence[str] | None = None) -> int:
    """Точка входа CLI. Возвращает код завершения."""

    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    try:
        validate_args(args)
        stats = analyze(args.inputs, args.fmt, skip_invalid=args.skip_invalid)
        report = build_report(stats)
        if args.output is None:
            print(dump_report(report))
        else:
            write_report(report, args.output)
    except InvalidEventError as exc:
        print(f"Ошибка: файл {exc.path}, строка {exc.line_number}: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except StreamStatsError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Ошибка чтения или записи файла: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())