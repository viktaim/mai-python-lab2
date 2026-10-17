from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Event:
    """Одно событие из журнала."""
    
    timestamp: datetime
    level: str
    source: str
    message: str