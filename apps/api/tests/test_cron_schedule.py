from datetime import datetime

import pytest

from src.services.cron_schedule import next_fire


@pytest.mark.parametrize(
    "expression,zone,after,expected",
    [
        ("*/5 * * * *", "UTC", "2026-01-01T10:00:00+00:00", "2026-01-01T10:05:00+00:00"),
        (
            "30 2 * * *",
            "America/New_York",
            "2026-03-08T00:00:00+00:00",
            "2026-03-09T06:30:00+00:00",
        ),
        (
            "30 1 * * *",
            "America/New_York",
            "2026-11-01T00:00:00+00:00",
            "2026-11-01T05:30:00+00:00",
        ),
        (
            "30 1 * * *",
            "America/New_York",
            "2026-11-01T05:30:00+00:00",
            "2026-11-02T06:30:00+00:00",
        ),
        (
            "30 1 * * *",
            "America/New_York",
            "2026-11-01T06:00:00+00:00",
            "2026-11-02T06:30:00+00:00",
        ),
        (
            "15 2 * * *",
            "Australia/Lord_Howe",
            "2026-10-03T15:00:00+00:00",
            "2026-10-04T15:15:00+00:00",
        ),
        ("0 12 * * *", "Pacific/Apia", "2011-12-30T00:00:00+00:00", "2011-12-30T22:00:00+00:00"),
        ("0 0 29 feb *", "UTC", "2026-01-01T00:00:00+00:00", "2028-02-29T00:00:00+00:00"),
        (
            "0 9 * * mon-fri",
            "Asia/Kolkata",
            "2026-09-18T04:00:00+00:00",
            "2026-09-21T03:30:00+00:00",
        ),
    ],
)
def test_clock_and_dst_rules(expression, zone, after, expected):
    assert next_fire(expression, zone, datetime.fromisoformat(after)) == datetime.fromisoformat(
        expected
    )


@pytest.mark.parametrize(
    "expression,zone",
    [
        ("* * * * * *", "UTC"),
        ("@daily", "UTC"),
        ("70 * * * *", "UTC"),
        ("0 0 30 feb *", "UTC"),
        ("R * * * *", "UTC"),
        ("H * * * *", "UTC"),
        ("* * * * *", "Not/AZone"),
        ("* * * * *", "../UTC"),
    ],
)
def test_invalid_or_unbounded_cron_is_rejected(expression, zone):
    with pytest.raises(ValueError):
        next_fire(expression, zone, datetime.fromisoformat("2026-01-01T00:00:00+00:00"))
