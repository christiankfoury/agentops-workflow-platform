"""Bounded wall-clock cron selection with explicit platform DST semantics."""

import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from croniter import croniter

NAMES = set("jan feb mar apr may jun jul aug sep oct nov dec sun mon tue wed thu fri sat".split())


def validate_cron(expression, timezone):
    if not isinstance(expression, str) or len(expression) > 160 or len(expression.split()) != 5:
        raise ValueError("Use a standard five-field cron expression")
    if not re.fullmatch(r"[A-Za-z0-9*,/\-\s]+", expression) or any(
        name.lower() not in NAMES for name in re.findall(r"[A-Za-z]+", expression)
    ):
        raise ValueError("Cron supports numbers, names, lists, ranges, steps and wildcards")
    if not croniter.is_valid(expression):
        raise ValueError("Invalid cron expression")
    try:
        return ZoneInfo(timezone)
    except (KeyError, ValueError, TypeError) as error:
        raise ValueError("Use a valid IANA timezone") from error


def next_fire(expression, timezone, after):
    zone = validate_cron(expression, timezone)
    if not isinstance(after, datetime) or after.tzinfo is None:
        raise ValueError("Schedule clock must be timezone-aware")
    after = after.astimezone(UTC)
    local = after.astimezone(zone).replace(tzinfo=None)
    try:
        iterator = croniter(expression, local, max_years_between_matches=5)
        # Covers a skipped civil day without unbounded iteration on hostile input.
        for _ in range(2000):
            candidate = iterator.get_next(datetime)
            instant = candidate.replace(tzinfo=zone, fold=0).astimezone(UTC)
            if instant <= after:
                continue
            if instant.astimezone(zone).replace(tzinfo=None) == candidate:
                return instant
    except (ValueError, OverflowError) as error:
        raise ValueError("Cron has no supported next occurrence within five years") from error
    raise ValueError("Cron exceeds the bounded timezone search")
