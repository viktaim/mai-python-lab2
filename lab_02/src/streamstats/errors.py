class StreamStatsError(Exception):
    """Базовое исключение пакета"""


class UnsupportedFormatError(StreamStatsError):
    """Формат входного файла не поддерживается"""


class InvalidEventError(StreamStatsError):
    """Событие не прошло валидацию."""

    def __init__(
        self,
        message: str,
        line_number: int | None = None,
        path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.path = path


class InvalidTimestampError(InvalidEventError):
    """Временная метка не соответствует формату ISO 8601"""


class CLIConfigError(StreamStatsError):
    '''Некорректные аргументы или конфигурация CLI'''