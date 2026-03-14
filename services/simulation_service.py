"""Service-layer orchestration for investment simulations."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from data.database import get_session
from data.queries import get_assets, get_strategies_with_allocations
from simulation.return_calculator import calculate_strategy_returns

logger = logging.getLogger(__name__)


class SimulationService:
    """Service API for strategy simulation workflows."""

    def list_assets(self) -> list[dict[str, Any]]:
        """Return available assets.

        Returns:
            List of serialized assets.
        """

        with get_session() as session:
            return [asset.to_dict() for asset in get_assets(session)]

    def list_strategies(self) -> list[dict[str, Any]]:
        """Return available strategies with allocations.

        Returns:
            List of serialized strategies.
        """

        with get_session() as session:
            return [
                strategy.to_dict()
                for strategy in get_strategies_with_allocations(session)
            ]

    def simulate(
        self,
        amount: float,
        period_years: int,
        strategy_ids: list[int],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Run simulation for selected strategies.

        Args:
            amount: Initial investment amount in RUB.
            period_years: User-selected horizon in years for rolling windows.
            strategy_ids: Strategy ids to evaluate.
            start_date: Inclusive start date for historical sample.
            end_date: Inclusive end date for historical sample.

        Returns:
            Per-strategy simulation result list.
        """

        results: list[dict[str, Any]] = []
        for strategy_id in strategy_ids:
            logger.info("Running simulation for strategy_id=%s", strategy_id)
            results.append(
                calculate_strategy_returns(
                    strategy_id=strategy_id,
                    start_date=start_date,
                    end_date=end_date,
                    initial_amount=amount,
                    period_years=period_years,
                )
            )
        return results
