class StreamStatsError(Exception):
    """Базовое исключение пакета"""


class UnsupportedFormatError(StreamStatsError):
    """Формат входного файла не поддерживается"""


class InvalidEventError(StreamStatsError):
    """Событие не прошло валидацию"""


class InvalidTimestampError(InvalidEventError):
    """Временная метка не соответствует формату ISO 8601"""


class CLIConfigError(StreamStatsError):
    '''Некорректные аргументы или конфигурация CLI'''