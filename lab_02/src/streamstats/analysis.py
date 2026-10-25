from streamstats.models import Event, Stats


from streamstats.models import Event, Stats

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