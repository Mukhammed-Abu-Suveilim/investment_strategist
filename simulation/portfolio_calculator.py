"""Portfolio return aggregation utilities."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

WEIGHT_TOLERANCE = 0.001


def validate_weights(weights: Sequence[float]) -> None:
    """Validate allocation weights.

    Args:
        weights: Portfolio weights.

    Raises:
        ValueError: If weights are empty, out of range, or do not sum to 1.
    """

    if not weights:
        raise ValueError("weights must not be empty.")

    if any(weight < 0 or weight > 1 for weight in weights):
        raise ValueError("each weight must be in range [0, 1].")

    total = float(sum(weights))
    if abs(total - 1.0) > WEIGHT_TOLERANCE:
        raise ValueError(
            f"weights must sum to 1.0 ± {WEIGHT_TOLERANCE}. Got {total:.6f}."
        )


def calculate_portfolio_returns(
    asset_returns: Sequence[Sequence[float]],
    weights: Sequence[float],
) -> list[float]:
    """Calculate weighted portfolio returns.

    Args:
        asset_returns: A 2D-like structure where each inner sequence is one asset's
            return series.
        weights: Asset weights aligned with ``asset_returns`` order.

    Returns:
        Weighted portfolio return list.

    Raises:
        ValueError: If dimensions are invalid or weights fail validation.
    """

    validate_weights(weights)

    if len(asset_returns) != len(weights):
        raise ValueError("asset_returns and weights length mismatch.")

    if not asset_returns:
        return []

    min_length = min(len(series) for series in asset_returns)
    if min_length == 0:
        return []

    matrix = np.array(
        [list(series[:min_length]) for series in asset_returns], dtype=float
    )
    weight_vector = np.array(list(weights), dtype=float)

    portfolio = matrix.T @ weight_vector
    return [float(value) for value in portfolio.tolist()]
