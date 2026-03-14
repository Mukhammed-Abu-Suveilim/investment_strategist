"""Calendar and time-series helpers for ETL normalization."""

from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd


def create_master_calendar(start_date: date, end_date: date) -> list[date]:
    """Create a dense daily calendar between two dates, inclusive.

    Args:
        start_date: Inclusive start boundary.
        end_date: Inclusive end boundary.

    Returns:
        Daily date list covering the full interval.

    Raises:
        ValueError: If start date is after end date.
    """

    if start_date > end_date:
        raise ValueError("start_date must not be greater than end_date.")

    return [ts.date() for ts in pd.date_range(start=start_date, end=end_date, freq="D")]


def forward_fill_prices(df: pd.DataFrame, master_dates: Iterable[date]) -> pd.DataFrame:
    """Align prices to a master calendar and forward-fill missing values.

    The implementation uses vectorized Pandas operations for performance.

    Args:
        df: Input DataFrame with columns ``date`` and ``price``.
        master_dates: Target date sequence.

    Returns:
        DataFrame with columns ``date`` and ``price`` aligned to all dates.
    """

    if df.empty:
        base = pd.DataFrame({"date": list(master_dates)})
        base["price"] = pd.NA
        return base

    working = df.copy()
    working["date"] = pd.to_datetime(working["date"], errors="coerce").dt.date
    working["price"] = pd.to_numeric(working["price"], errors="coerce")
    working = working.dropna(subset=["date"]).sort_values("date")
    working = working.drop_duplicates(subset=["date"], keep="last")

    calendar_df = pd.DataFrame({"date": list(master_dates)})
    merged = calendar_df.merge(working[["date", "price"]], on="date", how="left")
    merged["price"] = merged["price"].ffill()

    return merged
