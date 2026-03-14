"""Database query and upsert helpers.

This module centralizes data-access logic used by ETL, seeding, API, and
simulation layers.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session, joinedload

from data.models import Asset, HistoricalPrice, Strategy, StrategyAllocation

logger = logging.getLogger(__name__)


WEIGHT_TOLERANCE: float = 0.001


def validate_weight_sum(weights: Sequence[float]) -> None:
    """Validate that strategy weights sum to 1.0 ± tolerance.

    Args:
        weights: Allocation weight list.

    Raises:
        ValueError: If sum is outside tolerance.
    """

    total_weight = float(sum(weights))
    if abs(total_weight - 1.0) > WEIGHT_TOLERANCE:
        raise ValueError(
            f"Invalid weight sum {total_weight:.6f}. "
            f"Expected 1.0 ± {WEIGHT_TOLERANCE}."
        )


def upsert_asset(
    session: Session,
    symbol: str,
    name: str,
    category: str,
    source: str,
    currency: str,
) -> Asset:
    """Create or update asset metadata by symbol.

    Args:
        session: Active SQLAlchemy session.
        symbol: Ticker symbol.
        name: Human-readable asset name.
        category: Asset category.
        source: Data source name.
        currency: Source currency code.

    Returns:
        Persisted Asset object.
    """

    normalized_symbol = symbol.strip().upper()
    normalized_currency = currency.strip().upper()

    asset = session.scalar(select(Asset).where(Asset.symbol == normalized_symbol))
    if asset is None:
        asset = Asset(
            symbol=normalized_symbol,
            name=name,
            category=category,
            source=source,
            currency=normalized_currency,
        )
        session.add(asset)
        session.flush()
        logger.info("Created asset '%s'.", normalized_symbol)
        return asset

    asset.name = name
    asset.category = category
    asset.source = source
    asset.currency = normalized_currency
    session.flush()
    logger.debug("Updated asset '%s'.", normalized_symbol)
    return asset


def bulk_upsert_prices(
    session: Session,
    asset_id: int,
    prices_df: pd.DataFrame,
) -> int:
    """Upsert historical prices for one asset in an idempotent manner.

    Args:
        session: Active SQLAlchemy session.
        asset_id: Target asset id.
        prices_df: DataFrame with columns ``date`` and ``price``.

    Returns:
        Number of inserted or updated rows.

    Raises:
        ValueError: If required columns are missing.
    """

    required_columns = {"date", "price"}
    if not required_columns.issubset(set(prices_df.columns)):
        raise ValueError("prices_df must include 'date' and 'price' columns.")

    normalized_df = prices_df.copy()
    normalized_df["date"] = pd.to_datetime(normalized_df["date"], errors="coerce")
    normalized_df["price"] = pd.to_numeric(normalized_df["price"], errors="coerce")
    normalized_df = normalized_df.dropna(subset=["date", "price"])

    if normalized_df.empty:
        logger.warning("No price rows to upsert for asset_id=%s.", asset_id)
        return 0

    normalized_df["date"] = normalized_df["date"].dt.date
    normalized_df = normalized_df.sort_values("date").drop_duplicates(subset=["date"])

    if normalized_df.empty:
        logger.warning("No valid normalized rows to upsert for asset_id=%s.", asset_id)
        return 0

    date_values = [
        value for value in normalized_df["date"].tolist() if isinstance(value, date)
    ]
    existing_rows = session.scalars(
        select(HistoricalPrice).where(
            and_(
                HistoricalPrice.asset_id == asset_id,
                HistoricalPrice.date.in_(date_values),
            )
        )
    ).all()
    existing_map = {row.date: row for row in existing_rows}

    affected = 0
    for record in normalized_df[["date", "price"]].to_dict(orient="records"):
        current_date_raw = record["date"]
        current_price_raw = record["price"]

        if not isinstance(current_date_raw, date):
            continue

        current_date = current_date_raw
        current_price = float(current_price_raw)

        existing = existing_map.get(current_date)
        if existing is None:
            session.add(
                HistoricalPrice(
                    asset_id=asset_id,
                    date=current_date,
                    price=current_price,
                )
            )
            affected += 1
            continue

        if abs(existing.price - current_price) > 1e-12:
            existing.price = current_price
            affected += 1

    session.flush()
    logger.info(
        "Upserted %s historical price rows for asset_id=%s.", affected, asset_id
    )
    return affected


def upsert_strategy(
    session: Session,
    name: str,
    description: str,
    allocations: list[dict[str, Any]],
) -> Strategy:
    """Create or update strategy and its allocations.

    Args:
        session: Active SQLAlchemy session.
        name: Strategy name.
        description: Strategy description.
        allocations: Allocation definitions with ``asset_id`` and ``weight``.

    Returns:
        Persisted Strategy object.

    Raises:
        ValueError: If allocations are invalid.
    """

    weights = [float(item["weight"]) for item in allocations]
    validate_weight_sum(weights)

    strategy = session.scalar(select(Strategy).where(Strategy.name == name))
    if strategy is None:
        strategy = Strategy(name=name, description=description)
        session.add(strategy)
        session.flush()
        logger.info("Created strategy '%s'.", name)
    else:
        strategy.description = description
        logger.debug("Updating strategy '%s'.", name)

    existing_by_asset = {item.asset_id: item for item in strategy.allocations}
    incoming_asset_ids = {int(item["asset_id"]) for item in allocations}

    for allocation in list(strategy.allocations):
        if allocation.asset_id not in incoming_asset_ids:
            session.delete(allocation)

    for item in allocations:
        asset_id = int(item["asset_id"])
        weight = float(item["weight"])
        current = existing_by_asset.get(asset_id)
        if current is None:
            session.add(
                StrategyAllocation(
                    strategy_id=strategy.id,
                    asset_id=asset_id,
                    weight=weight,
                )
            )
            continue
        current.weight = weight

    session.flush()
    refreshed = session.scalar(
        select(Strategy)
        .options(joinedload(Strategy.allocations).joinedload(StrategyAllocation.asset))
        .where(Strategy.id == strategy.id)
    )
    if refreshed is None:
        raise RuntimeError("Failed to reload strategy after upsert.")
    return refreshed


def get_assets(session: Session) -> list[Asset]:
    """Return all assets sorted by symbol."""

    stmt: Select[tuple[Asset]] = select(Asset).order_by(Asset.symbol.asc())
    return list(session.scalars(stmt).all())


def get_strategies_with_allocations(session: Session) -> list[Strategy]:
    """Return strategies with eager-loaded allocations and assets."""

    stmt: Select[tuple[Strategy]] = (
        select(Strategy)
        .options(joinedload(Strategy.allocations).joinedload(StrategyAllocation.asset))
        .order_by(Strategy.name.asc())
    )
    return list(session.scalars(stmt).unique().all())


def get_price_history(
    session: Session,
    asset_ids: Sequence[int],
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    """Fetch historical prices for multiple assets as a DataFrame.

    Args:
        session: Active SQLAlchemy session.
        asset_ids: Asset id collection.
        start_date: Optional lower bound date.
        end_date: Optional upper bound date.

    Returns:
        DataFrame with columns ``asset_id``, ``date``, and ``price``.
    """

    if not asset_ids:
        return pd.DataFrame(columns=["asset_id", "date", "price"])

    stmt = select(
        HistoricalPrice.asset_id, HistoricalPrice.date, HistoricalPrice.price
    ).where(HistoricalPrice.asset_id.in_(list(asset_ids)))
    if start_date is not None:
        stmt = stmt.where(HistoricalPrice.date >= start_date)
    if end_date is not None:
        stmt = stmt.where(HistoricalPrice.date <= end_date)

    rows = session.execute(stmt.order_by(HistoricalPrice.date.asc())).all()
    return pd.DataFrame(rows, columns=["asset_id", "date", "price"])
