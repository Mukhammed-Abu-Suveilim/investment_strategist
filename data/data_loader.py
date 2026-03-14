"""Database seed workflow.

This module runs ETL and creates default strategies required by the PRD.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select

from data.database import create_all_tables, get_session
from data.models import Asset
from data.queries import upsert_strategy
from etl.pipeline.master_pipeline import run_full_etl

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AllocationSeed:
    """Allocation seed definition.

    Attributes:
        symbol: Canonical asset symbol.
        weight: Portfolio allocation weight.
    """

    symbol: str
    weight: float


@dataclass(frozen=True)
class StrategySeed:
    """Strategy seed definition.

    Attributes:
        name: Strategy name.
        description: Strategy description.
        allocations: Strategy allocation legs.
    """

    name: str
    description: str
    allocations: tuple[AllocationSeed, ...]


DEFAULT_STRATEGIES: tuple[StrategySeed, ...] = (
    StrategySeed(
        name="Stocks Only",
        description="100% allocation to IMOEX equity index.",
        allocations=(AllocationSeed(symbol="IMOEX", weight=1.0),),
    ),
    StrategySeed(
        name="Bonds Only",
        description="100% allocation to RGBITR bond index.",
        allocations=(AllocationSeed(symbol="RGBITR", weight=1.0),),
    ),
    StrategySeed(
        name="Gold",
        description="100% allocation to GOLD_RUB.",
        allocations=(AllocationSeed(symbol="GOLD_RUB", weight=1.0),),
    ),
    StrategySeed(
        name="Balanced",
        description="60% IMOEX, 30% RGBITR, 10% GOLD_RUB.",
        allocations=(
            AllocationSeed(symbol="IMOEX", weight=0.60),
            AllocationSeed(symbol="RGBITR", weight=0.30),
            AllocationSeed(symbol="GOLD_RUB", weight=0.10),
        ),
    ),
    StrategySeed(
        name="Conservative",
        description="30% IMOEX, 60% RGBITR, 10% GOLD_RUB.",
        allocations=(
            AllocationSeed(symbol="IMOEX", weight=0.30),
            AllocationSeed(symbol="RGBITR", weight=0.60),
            AllocationSeed(symbol="GOLD_RUB", weight=0.10),
        ),
    ),
)


def seed_default_data() -> None:
    """Run ETL and seed default strategies idempotently."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    logger.info("Creating database tables and running ETL before strategy seeding.")
    create_all_tables()
    run_full_etl()

    with get_session() as session:
        assets = session.scalars(select(Asset)).all()
        assets_by_symbol = {asset.symbol: asset.id for asset in assets}

        for strategy in DEFAULT_STRATEGIES:
            allocations_payload: list[dict[str, int | float]] = []
            for allocation in strategy.allocations:
                if allocation.symbol not in assets_by_symbol:
                    raise ValueError(
                        f"Asset '{allocation.symbol}' is missing. "
                        "Run ETL and verify symbols."
                    )
                allocations_payload.append(
                    {
                        "asset_id": int(assets_by_symbol[allocation.symbol]),
                        "weight": float(allocation.weight),
                    }
                )

            upsert_strategy(
                session=session,
                name=strategy.name,
                description=strategy.description,
                allocations=allocations_payload,
            )

    logger.info("Default data seed completed successfully.")


def main() -> None:
    """CLI entrypoint for ``uv run seed``."""

    seed_default_data()


if __name__ == "__main__":
    main()
