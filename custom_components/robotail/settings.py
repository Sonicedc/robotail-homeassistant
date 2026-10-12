"""Interpret Robotail's seconds-based cleaning delay."""

import math
from typing import Any


def delay_minutes(value: Any) -> float | None:
    """Convert API seconds to minutes without rounding malformed settings."""
    if value is None or isinstance(value, bool):
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(seconds) or not 0 <= seconds <= 3600:
        return None
    return seconds / 60
