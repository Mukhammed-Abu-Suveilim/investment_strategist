"""Strategy return orchestration logic."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from data.database import get_session
from data.models import Asset, Strategy, StrategyAllocation
from simulation.portfolio_calculator import calculate_portfolio_returns
from simulation.rolling_returns import calculate_rolling_returns, years_to_trading_days
from simulation.scenario_analysis import (
    calculate_detailed_metrics,
    calculate_metrics,
    calculate_scenarios,
)

logger = logging.getLogger(__name__)


def _format_chart_date(value: Any) -> str:
    """Format chart date values to ISO8601 date string.

    Args:
        value: Date-like value from pandas output.

    Returns:
        ISO8601 date representation.

    Raises:
        ValueError: If value cannot be parsed as date.
    """

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    parsed_value = pd.to_datetime(value, errors="coerce")
    parsed_timestamp = pd.Timestamp(parsed_value)
    if pd.isna(parsed_timestamp):
        raise ValueError("Unable to parse chart date value.")

    return parsed_timestamp.date().isoformat()


def _build_portfolio_series(
    strategy: Strategy,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Build portfolio daily return series for a strategy.

    Args:
        strategy: ORM strategy object with allocations loaded.
        start_date: Inclusive start date.
        end_date: Inclusive end date.

    Returns:
        DataFrame with columns ``date`` and ``portfolio_return``.

    Raises:
        ValueError: If required price data is missing.
    """

    allocation_map = {
        allocation.asset_id: allocation.weight for allocation in strategy.allocations
    }
    asset_ids = list(allocation_map.keys())

    records: list[dict[str, Any]] = []
    for allocation in strategy.allocations:
        if allocation.asset is None:
            continue
        for price in allocation.asset.prices:
            if price.date < start_date or price.date > end_date:
                continue
            records.append(
                {
                    "asset_id": allocation.asset_id,
                    "date": price.date,
                    "price": price.price,
                }
            )

    if not records:
        raise ValueError("No historical prices available for selected period.")

    prices_df = pd.DataFrame(records)
    pivot = (
        prices_df.pivot_table(
            index="date", columns="asset_id", values="price", aggfunc="last"
        )
        .sort_index()
        .ffill()
        .dropna(subset=asset_ids)
    )

    if pivot.empty or len(pivot) < 2:
        raise ValueError(
            "Insufficient overlapping historical prices to simulate strategy."
        )

    daily_returns = pivot.pct_change().dropna(how="any")
    if daily_returns.empty:
        raise ValueError("Insufficient return observations to simulate strategy.")

    ordered_weights = [
        float(allocation_map[int(asset_id)]) for asset_id in daily_returns.columns
    ]
    asset_return_series = [
        daily_returns[column].tolist() for column in daily_returns.columns
    ]
    portfolio_returns = calculate_portfolio_returns(
        asset_return_series, ordered_weights
    )

    portfolio_df = pd.DataFrame(
        {
            "date": list(daily_returns.index),
            "portfolio_return": portfolio_returns,
        }
    )
    return portfolio_df


def _calculate_expected_1y_values(
    rolling_returns_1y: list[float],
    initial_amount: float,
) -> tuple[dict[str, float], float, float]:
    """Calculate expected one-year scenario statistics and final value.

    Args:
        rolling_returns_1y: One-year rolling return observations.
        initial_amount: Initial investment amount in RUB.

    Returns:
        Tuple of ``(one_year_scenarios, expected_1y_return, expected_1y_final_value)``.
    """

    one_year_scenarios = calculate_scenarios(rolling_returns_1y)
    expected_1y_return = float(one_year_scenarios["median"])
    expected_1y_final_value = float(initial_amount * (1.0 + expected_1y_return))
    return one_year_scenarios, expected_1y_return, expected_1y_final_value


def _calculate_expected_selected_period_values(
    selected_period_returns: list[float],
    initial_amount: float,
) -> tuple[dict[str, float], float, float]:
    """Calculate selected-period scenario statistics and expected final value.

    Args:
        selected_period_returns: Rolling return observations for selected period.
        initial_amount: Initial investment amount in RUB.

    Returns:
        Tuple of ``(
            selected_period_scenarios,
            expected_selected_period_return,
            expected_selected_period_final_value,
        )``.
    """

    selected_period_scenarios = calculate_scenarios(selected_period_returns)
    expected_selected_period_return = float(selected_period_scenarios["median"])
    expected_selected_period_final_value = float(
        initial_amount * (1.0 + expected_selected_period_return)
    )
    return (
        selected_period_scenarios,
        expected_selected_period_return,
        expected_selected_period_final_value,
    )


def calculate_strategy_returns(
    strategy_id: int,
    start_date: date,
    end_date: date,
    initial_amount: float,
    period_years: int = 1,
) -> dict[str, Any]:
    """Calculate strategy performance and scenario analytics.

    Args:
        strategy_id: Strategy identifier.
        start_date: Inclusive start simulation date.
        end_date: Inclusive end simulation date.
        initial_amount: Initial investment amount in RUB.
        period_years: User-selected period in years for rolling scenarios.

    Returns:
        Simulation result dictionary.

    Raises:
        ValueError: If strategy or sufficient data is unavailable.
    """

    if initial_amount <= 0:
        raise ValueError("initial_amount must be greater than zero.")

    with get_session() as session:
        stmt = (
            select(Strategy)
            .options(
                joinedload(Strategy.allocations)
                .joinedload(StrategyAllocation.asset)
                .joinedload(Asset.prices)
            )
            .where(Strategy.id == strategy_id)
        )
        strategy = session.execute(stmt).scalars().unique().one_or_none()

        if strategy is None:
            raise ValueError(f"Strategy with id={strategy_id} not found.")

        if not strategy.allocations:
            raise ValueError("Strategy has no allocations.")

        portfolio_df = _build_portfolio_series(
            strategy, start_date=start_date, end_date=end_date
        )

    growth = (1.0 + portfolio_df["portfolio_return"]).cumprod()
    growth_df = pd.DataFrame({"date": portfolio_df["date"], "price": growth})

    selected_window_days = years_to_trading_days(period_years)
    selected_period_returns = calculate_rolling_returns(
        growth_df, window_days=selected_window_days
    )
    (
        selected_period_scenarios,
        expected_selected_period_return,
        expected_selected_period_final_value,
    ) = _calculate_expected_selected_period_values(
        selected_period_returns=selected_period_returns,
        initial_amount=initial_amount,
    )
    metrics = calculate_metrics(selected_period_returns)

    one_year_window_days = years_to_trading_days(1)
    one_year_returns = calculate_rolling_returns(
        growth_df, window_days=one_year_window_days
    )
    (
        one_year_scenarios,
        expected_1y_return,
        expected_1y_final_value,
    ) = _calculate_expected_1y_values(one_year_returns, initial_amount)

    selected_period_detailed_metrics = calculate_detailed_metrics(
        returns_list=selected_period_returns,
        wealth_series=growth_df["price"].tolist(),
        drawdown_window_days=selected_window_days,
    )
    one_year_detailed_metrics = calculate_detailed_metrics(
        returns_list=one_year_returns,
        wealth_series=growth_df["price"].tolist(),
        drawdown_window_days=one_year_window_days,
    )

    historical_full_period_final_value = float(initial_amount * float(growth.iloc[-1]))
    growth_chart_data = [
        {
            "date": _format_chart_date(record["date"]),
            "value": float(initial_amount * float(record["price"])),
        }
        for record in growth_df[["date", "price"]].to_dict(orient="records")
    ]

    return {
        "strategy_id": strategy.id,
        "strategy_name": strategy.name,
        "final_value": expected_selected_period_final_value,
        "expected_selected_period_return": expected_selected_period_return,
        "expected_selected_period_final_value": expected_selected_period_final_value,
        "selected_period_years": period_years,
        "selected_period_scenarios": selected_period_scenarios,
        "scenarios": selected_period_scenarios,
        "one_year_scenarios": one_year_scenarios,
        "expected_1y_return": expected_1y_return,
        "expected_1y_final_value": expected_1y_final_value,
        "metrics": metrics,
        "selected_period_detailed_metrics": selected_period_detailed_metrics,
        "detailed_metrics": selected_period_detailed_metrics,
        "one_year_detailed_metrics": one_year_detailed_metrics,
        "historical_full_period_final_value": historical_full_period_final_value,
        "growth_chart_data": growth_chart_data,
    }
