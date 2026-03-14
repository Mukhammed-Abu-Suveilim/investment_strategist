"""Scenario analysis and risk metrics for strategy returns."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from config import settings


def calculate_scenarios(returns_list: list[float]) -> dict[str, float]:
    """Calculate worst, median, and best return scenarios.

    Args:
        returns_list: Historical return observations as decimal values.

    Returns:
        Dictionary with percentile scenarios.
    """

    if not returns_list:
        return {"worst": 0.0, "median": 0.0, "best": 0.0}

    values = np.array(returns_list, dtype=float)
    return {
        "worst": float(np.percentile(values, 5)),
        "median": float(np.percentile(values, 50)),
        "best": float(np.percentile(values, 95)),
    }


def calculate_metrics(returns_list: list[float]) -> dict[str, float]:
    """Calculate descriptive and risk-adjusted metrics for returns.

    Args:
        returns_list: Historical return observations as decimal values.

    Returns:
        Dictionary with mean, std_dev, min, max, and sharpe_ratio metrics.
    """

    if not returns_list:
        return {
            "mean": 0.0,
            "std_dev": 0.0,
            "min": 0.0,
            "max": 0.0,
            "sharpe_ratio": 0.0,
        }

    values = np.array(returns_list, dtype=float)
    mean_return = float(np.mean(values))
    std_dev = float(np.std(values, ddof=0))
    min_value = float(np.min(values))
    max_value = float(np.max(values))

    annual_rf = settings.risk_free_rate
    daily_rf = (1.0 + annual_rf) ** (1.0 / 252.0) - 1.0
    excess_mean = mean_return - daily_rf
    sharpe_ratio = 0.0
    if std_dev > 0:
        sharpe_ratio = float((excess_mean / std_dev) * math.sqrt(252.0))

    return {
        "mean": mean_return,
        "std_dev": std_dev,
        "min": min_value,
        "max": max_value,
        "sharpe_ratio": sharpe_ratio,
    }


def _to_numeric_array(values: Sequence[float]) -> NDArray[np.float64]:
    """Normalize an input sequence into finite ``float`` NumPy array.

    Args:
        values: Numeric values sequence.

    Returns:
        Array filtered to finite values.
    """

    normalized = np.asarray(list(values), dtype=np.float64)
    if normalized.size == 0:
        return normalized

    finite_values = [
        float(value) for value in normalized.tolist() if np.isfinite(value)
    ]
    return np.asarray(finite_values, dtype=np.float64)


def calculate_max_drawdown(
    wealth_series: Sequence[float],
    window_days: int | None = None,
) -> float:
    """Calculate maximum drawdown for a wealth path.

    Args:
        wealth_series: Portfolio wealth/index level values.
        window_days: Optional drawdown lookback in trading days. If omitted,
            calculates drawdown against running all-time peak.

    Returns:
        Maximum drawdown as a negative decimal value.
    """

    values = _to_numeric_array(wealth_series)
    if values.size < 2:
        return 0.0

    positive_mask = values > 0.0
    values = values[positive_mask]
    if values.size < 2:
        return 0.0

    if window_days is not None and window_days > 0:
        rolling_peaks = (
            pd.Series(values)
            .rolling(window=window_days, min_periods=1)
            .max()
            .to_numpy()
        )
    else:
        rolling_peaks = np.maximum.accumulate(values)

    drawdowns = values / rolling_peaks - 1.0
    return float(np.min(drawdowns))


def calculate_detailed_metrics(
    returns_list: list[float],
    wealth_series: Sequence[float] | None = None,
    drawdown_window_days: int | None = None,
) -> dict[str, float]:
    """Calculate detailed risk and reliability metrics.

    Args:
        returns_list: Return observations for the selected horizon.
        wealth_series: Optional wealth path used for max drawdown calculation.
        drawdown_window_days: Optional drawdown lookback window in trading days.

    Returns:
        Dictionary with volatility, max_drawdown, VaR/CVaR, profit probability,
        and Omega ratio.
    """

    values = _to_numeric_array(returns_list)

    if values.size == 0:
        max_drawdown = (
            calculate_max_drawdown(wealth_series, drawdown_window_days)
            if wealth_series is not None
            else 0.0
        )
        return {
            "volatility": 0.0,
            "max_drawdown": max_drawdown,
            "var95": 0.0,
            "cvar95": 0.0,
            "probability_of_profit": 0.0,
            "omega_ratio": 0.0,
        }

    volatility = float(np.std(values, ddof=0))
    var95 = float(np.percentile(values, 5))

    tail_losses = values[values <= var95]
    cvar95 = float(np.mean(tail_losses)) if tail_losses.size > 0 else var95

    probability_of_profit = float(np.mean(values > 0.0))

    gains = float(np.sum(values[values > 0.0]))
    losses_abs = float(abs(np.sum(values[values < 0.0])))
    omega_ratio = gains / losses_abs if losses_abs > 0 else 0.0

    max_drawdown = (
        calculate_max_drawdown(wealth_series, drawdown_window_days)
        if wealth_series is not None
        else 0.0
    )

    return {
        "volatility": volatility,
        "max_drawdown": max_drawdown,
        "var95": var95,
        "cvar95": cvar95,
        "probability_of_profit": probability_of_profit,
        "omega_ratio": float(omega_ratio),
    }
