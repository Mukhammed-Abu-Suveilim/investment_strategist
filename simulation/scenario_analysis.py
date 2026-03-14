"""Scenario analysis and risk metrics for strategy returns."""

from __future__ import annotations

import math

import numpy as np

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
