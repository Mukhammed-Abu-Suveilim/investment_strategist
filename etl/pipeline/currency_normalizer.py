"""Currency normalization utilities.

Methodology:
1. Input USD asset prices and USD/RUB FX rates are converted to daily series.
2. Series are merged by date and sorted in ascending order.
3. Missing FX rates are forward-filled to preserve continuity.
4. Normalized RUB price is computed as ``price_usd * usd_rub_rate``.

This method keeps ETL idempotent and deterministic across repeated runs.
"""

from __future__ import annotations

import pandas as pd


def normalize_to_rub(
    usd_prices_df: pd.DataFrame, usd_rub_rates_df: pd.DataFrame
) -> pd.DataFrame:
    """Convert USD-denominated prices to RUB.

    Args:
        usd_prices_df: DataFrame with ``date`` and ``price`` (USD).
        usd_rub_rates_df: DataFrame with ``date`` and ``price`` (USD/RUB rate).

    Returns:
        DataFrame with columns ``date`` and ``price`` normalized to RUB.

    Raises:
        ValueError: If required columns are missing.
    """

    required_columns = {"date", "price"}
    if not required_columns.issubset(set(usd_prices_df.columns)):
        raise ValueError("usd_prices_df must include 'date' and 'price' columns.")
    if not required_columns.issubset(set(usd_rub_rates_df.columns)):
        raise ValueError("usd_rub_rates_df must include 'date' and 'price' columns.")

    prices = usd_prices_df.copy()
    rates = usd_rub_rates_df.copy()

    prices["date"] = pd.to_datetime(prices["date"], errors="coerce").dt.date
    prices["price"] = pd.to_numeric(prices["price"], errors="coerce")
    prices = prices.dropna(subset=["date", "price"]).drop_duplicates(
        subset=["date"], keep="last"
    )

    rates["date"] = pd.to_datetime(rates["date"], errors="coerce").dt.date
    rates["price"] = pd.to_numeric(rates["price"], errors="coerce")
    rates = rates.dropna(subset=["date", "price"]).drop_duplicates(
        subset=["date"], keep="last"
    )
    rates = rates.rename(columns={"price": "usd_rub_rate"})

    merged = prices.merge(rates, on="date", how="left").sort_values("date")
    merged["usd_rub_rate"] = merged["usd_rub_rate"].ffill()
    merged["price"] = merged["price"] * merged["usd_rub_rate"]

    normalized = (
        merged[["date", "price"]].dropna(subset=["price"]).reset_index(drop=True)
    )
    return normalized
