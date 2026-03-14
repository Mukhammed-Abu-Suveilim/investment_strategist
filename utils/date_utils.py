"""Shared date utility helpers."""

from __future__ import annotations

from datetime import date, datetime


def parse_iso_date(value: str) -> date:
    """Parse an ISO date string.

    Args:
        value: ISO 8601 date string in ``YYYY-MM-DD`` format.

    Returns:
        Parsed ``date`` instance.

    Raises:
        ValueError: If input format is invalid.
    """

    return date.fromisoformat(value)


def utc_today_naive() -> date:
    """Return current UTC date as timezone-naive value."""

    return datetime.utcnow().date()


def clamp_date_range(start_date: date, end_date: date) -> tuple[date, date]:
    """Validate and normalize date ranges.

    Args:
        start_date: Start boundary.
        end_date: End boundary.

    Returns:
        Validated date-range tuple.

    Raises:
        ValueError: If start date is after end date.
    """

    if start_date > end_date:
        raise ValueError("start_date must be earlier than or equal to end_date.")
    return start_date, end_date
