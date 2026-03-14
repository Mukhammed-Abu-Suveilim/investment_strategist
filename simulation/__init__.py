"""Simulation engine package."""

from simulation.portfolio_calculator import calculate_portfolio_returns
from simulation.return_calculator import calculate_strategy_returns
from simulation.rolling_returns import calculate_rolling_returns, years_to_trading_days
from simulation.scenario_analysis import calculate_metrics, calculate_scenarios

__all__ = [
    "calculate_portfolio_returns",
    "calculate_strategy_returns",
    "calculate_rolling_returns",
    "years_to_trading_days",
    "calculate_scenarios",
    "calculate_metrics",
]
