"""Tests for ETL normalization helpers and source-specific transformers."""

from __future__ import annotations

from datetime import date

import pandas as pd

from etl.pipeline.currency_normalizer import normalize_to_rub
from etl.transformers.standardize_moex import StandardizeMoexTransformer
from etl.transformers.standardize_yahoo import StandardizeYahooTransformer
from etl.utils.calendar_utils import create_master_calendar, forward_fill_prices


def test_create_master_calendar_inclusive() -> None:
    """Master calendar contains both start and end dates."""

    result = create_master_calendar(date(2024, 1, 1), date(2024, 1, 3))
    assert result == [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]


def test_forward_fill_prices_applies_previous_value() -> None:
    """Forward fill creates continuous daily prices on sparse input."""

    sparse = pd.DataFrame(
        {
            "date": [date(2024, 1, 1), date(2024, 1, 3)],
            "price": [100.0, 120.0],
        }
    )
    calendar = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]

    result = forward_fill_prices(sparse, calendar)
    assert result["price"].tolist() == [100.0, 100.0, 120.0]


def test_normalize_to_rub_uses_usd_rub_rate() -> None:
    """USD-denominated asset prices are converted to RUB correctly."""

    usd_prices = pd.DataFrame(
        {
            "date": [date(2024, 1, 1), date(2024, 1, 2)],
            "price": [10.0, 11.0],
        }
    )
    usd_rub = pd.DataFrame(
        {
            "date": [date(2024, 1, 1), date(2024, 1, 2)],
            "price": [90.0, 100.0],
        }
    )

    result = normalize_to_rub(usd_prices_df=usd_prices, usd_rub_rates_df=usd_rub)
    assert result["price"].tolist() == [900.0, 1100.0]


def test_standardize_moex_accepts_board_history_columns() -> None:
    """MOEX transformer supports TRADEDATE/CLOSE payload format."""

    raw_df = pd.DataFrame(
        {
            "TRADEDATE": ["2024-01-01", "2024-01-02"],
            "CLOSE": [3200.5, 3210.2],
            "BOARDID": ["SNDX", "SNDX"],
        }
    )

    transformed = StandardizeMoexTransformer().transform(raw_df)

    assert list(transformed.columns) == ["date", "price"]
    assert transformed["date"].tolist() == [date(2024, 1, 1), date(2024, 1, 2)]
    assert transformed["price"].tolist() == [3200.5, 3210.2]


def test_standardize_yahoo_handles_multiindex_columns() -> None:
    """Yahoo transformer supports yfinance MultiIndex output."""

    columns = pd.MultiIndex.from_tuples(
        [
            ("Close", "GC=F"),
            ("High", "GC=F"),
            ("Low", "GC=F"),
            ("Open", "GC=F"),
            ("Volume", "GC=F"),
        ],
        names=["Price", "Ticker"],
    )

    raw_df = pd.DataFrame(
        [
            [2000.0, 2010.0, 1990.0, 2005.0, 1000],
            [2015.0, 2020.0, 2001.0, 2008.0, 1200],
        ],
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
        columns=columns,
    ).reset_index(names="Date")

    transformed = StandardizeYahooTransformer().transform(raw_df)

    assert list(transformed.columns) == ["date", "price"]
    assert transformed["date"].tolist() == [date(2024, 1, 1), date(2024, 1, 2)]
    assert transformed["price"].tolist() == [2000.0, 2015.0]
