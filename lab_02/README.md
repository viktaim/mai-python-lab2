# streamstats

Лабораторная работа 2 по Python. Программа читает файлы с событиями (CSV или JSONL), считает статистику и сохраняет отчёт в JSON.

## Установка

```bash
git clone https://github.com/viktaim/mai-python-lab2.git
cd lab_02
python -m venv .venv
```

Активация окружения:

pip install -e ".[dev]"

## Формат файлов

У каждого события есть 4 поля:

- `timestamp` - дата и время в формате ISO 8601
- `level` - DEBUG, INFO, WARNING, ERROR или CRITICAL
- `source` - источник события, не пустая строка
- `message` - текст события

В CSV первая строка это заголовок `timestamp,level,source,message`. В JSONL каждая строка это один JSON-объект с такими же полями. Кодировка UTF-8 (по условию)

## Запуск

```bash
python -m streamstats analyze data/events_valid.csv --format csv
python -m streamstats analyze a.jsonl b.jsonl --format jsonl --output report.json
python -m streamstats analyze data/events_invalid.jsonl --format jsonl --skip-invalid
python -m streamstats --help
```

Параметры:

- `INPUT` - один или несколько файлов
- `--format` - csv или jsonl
- `--output` - файл для отчёта, если не указан, отчёт выводится на экран
- `--skip-invalid` - пропускать плохие строки

Если файлов несколько, они считаются вместе в один отчёт. Сами файлы программа не меняет.

## Ошибки

Без `--skip-invalid` программа останавливается на первой плохой строке, пишет файл и номер строки и завершается с кодом 2. Отчёт при этом не создаётся.

С `--skip-invalid` плохая строка пропускается, в лог пишется WARNING, а количество пропущенных строк записывается в поле `skipped` в отчёте.

Код 2 также возвращается, если файл не найден, формат неизвестен или отчёт указан как тот же файл, что и вход.

## Пример отчёта

```json
{
  "total": 12,
  "skipped": 0,
  "levels": {
    "CRITICAL": 2,
    "DEBUG": 2,
    "ERROR": 3,
    "INFO": 3,
    "WARNING": 2
  },
  "sources": {
    "api": 3,
    "auth": 1,
    "db": 4,
    "web": 2,
    "worker": 2
  },
  "top_error_sources": [
    {"source": "db", "count": 2},
    {"source": "api", "count": 1},
    {"source": "auth", "count": 1},
    {"source": "web", "count": 1}
  ],
  "first_timestamp": "2026-10-06T10:00:00+00:00",
  "last_timestamp": "2026-10-06T10:10:00+00:00"
}
```

`top_error_sources` - до 5 источников, у которых больше всего событий ERROR и CRITICAL. Если число одинаковое, источники сортируются по алфавиту. Для пустого файла отчёт получается нулевой: `total` равен 0, а даты равны `null`.

## Структура

```text
src/streamstats/
  errors.py     исключения
  models.py     Event и Stats
  parsers.py    парсеры CSV и JSONL
  analysis.py   подсчёт статистики
  report.py     JSON-отчёт
  __main__.py   командная строка
tests/          тесты
```

## Про память

Парсеры сделаны генераторами: файл читается построчно, и каждое событие сразу попадает в счётчики и больше не хранится. Список всех событий не создаётся, `readlines()` не используется. Поэтому память зависит не от размера файла, а только от числа разных уровней и источников.

## Проверка

```bash
python -m pytest
ruff check .
python -m streamstats --help
```