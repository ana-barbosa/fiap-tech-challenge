import time
from collections import defaultdict

from . import config

_calls: dict[str, list[float]] = defaultdict(list)


def check(conversation_id: str) -> bool:
    now = time.monotonic()
    cutoff = now - config.RATE_LIMIT_WINDOW_SECONDS
    timestamps = _calls[conversation_id]

    while timestamps and timestamps[0] < cutoff:
        timestamps.pop(0)

    if len(timestamps) >= config.RATE_LIMIT_MAX_REQUESTS:
        return False

    timestamps.append(now)
    return True
