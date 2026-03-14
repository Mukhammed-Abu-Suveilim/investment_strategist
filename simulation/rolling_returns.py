"""Rolling return calculations for investment horizons."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

TRADING_DAYS_PER_YEAR = 252
TRADING_DAYS_PER_MONTH = 21


def years_to_trading_days(years: int | float) -> int:
    """Convert years to approximate trading days.

    Args:
        years: User-selected investment horizon in years.

    Returns:
        Number of trading days.

    Raises:
        ValueError: If years is not positive.
    """

    if years <= 0:
        raise ValueError("years must be greater than zero.")
    return max(1, int(round(float(years) * TRADING_DAYS_PER_YEAR)))


def months_to_trading_days(months: int | float) -> int:
    """Convert months to approximate trading days.

    Args:
        months: User-selected investment horizon in months.

    Returns:
        Number of trading days.

    Raises:
        ValueError: If months is not positive.
    """

    if months <= 0:
        raise ValueError("months must be greater than zero.")
    return max(1, int(round(float(months) * TRADING_DAYS_PER_MONTH)))


def calculate_rolling_returns(prices_df: pd.DataFrame, window_days: int) -> list[float]:
    """Calculate rolling simple returns for a fixed window size.

    Formula:
        rolling_return = price_t / price_(t-window) - 1

    Args:
        prices_df: DataFrame with columns ``date`` and ``price``.
        window_days: Rolling window size in trading days.

    Returns:
        List of rolling returns as decimals.

    Raises:
        ValueError: If required columns are missing or window is invalid.
    """

    if window_days < 1:
        raise ValueError("window_days must be at least 1.")

    required_columns = {"date", "price"}
    if not required_columns.issubset(set(prices_df.columns)):
        raise ValueError("prices_df must include 'date' and 'price' columns.")

    working = prices_df.copy()
    working["date"] = pd.to_datetime(working["date"], errors="coerce")
    working["price"] = pd.to_numeric(working["price"], errors="coerce")
    working = working.dropna(subset=["date", "price"]).sort_values("date")

    if len(working) <= window_days:
        return []

    rolling = working["price"].shift(-window_days) / working["price"] - 1.0
    return [float(value) for value in rolling.dropna().tolist()]


def as_price_frame(values: Iterable[float]) -> pd.DataFrame:
    """Build synthetic price DataFrame for utility and testing use.

    Args:
        values: Price sequence.

    Returns:
        DataFrame with synthetic daily dates and prices.
    """

    series = list(values)
    return pd.DataFrame(
        {
            "date": pd.date_range(start="2000-01-01", periods=len(series), freq="D"),
            "price": series,
        }
    )
