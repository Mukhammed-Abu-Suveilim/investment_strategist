"""Tests for simulation calculations."""

from __future__ import annotations

import pandas as pd
import pytest

from simulation.portfolio_calculator import (
    calculate_portfolio_returns,
    validate_weights,
)
from simulation.rolling_returns import calculate_rolling_returns, years_to_trading_days
from simulation.scenario_analysis import calculate_metrics, calculate_scenarios


def test_years_to_trading_days_conversion() -> None:
    """It converts years to expected trading-day windows."""

    assert years_to_trading_days(1) == 252
    assert years_to_trading_days(0.5) == 126


def test_calculate_rolling_returns_returns_expected_values() -> None:
    """It computes rolling simple returns for a fixed window."""

    prices_df = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=5, freq="D"),
            "price": [100.0, 110.0, 121.0, 133.1, 146.41],
        }
    )

    returns = calculate_rolling_returns(prices_df, window_days=2)
    assert len(returns) == 3
    assert pytest.approx(returns[0], rel=1e-9) == 0.21


def test_validate_weights_raises_on_invalid_sum() -> None:
    """It rejects weights that do not sum to 1.0 within tolerance."""

    with pytest.raises(ValueError):
        validate_weights([0.6, 0.3])


def test_calculate_portfolio_returns_weighted_average() -> None:
    """It computes weighted portfolio returns correctly."""

    asset_returns = [
        [0.10, 0.00, 0.05],
        [0.00, 0.10, 0.05],
    ]
    weights = [0.5, 0.5]

    result = calculate_portfolio_returns(asset_returns, weights)
    assert result == pytest.approx([0.05, 0.05, 0.05])


def test_calculate_scenarios_and_metrics_have_expected_keys() -> None:
    """It returns scenario percentiles and summary metrics."""

    data = [0.01, 0.02, -0.01, 0.03, 0.00]
    scenarios = calculate_scenarios(data)
    metrics = calculate_metrics(data)

    assert set(scenarios.keys()) == {"worst", "median", "best"}
    assert set(metrics.keys()) == {"mean", "std_dev", "min", "max", "sharpe_ratio"}
