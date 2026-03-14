"""SQLAlchemy ORM models for investment simulation data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.database import Base


class Asset(Base):
    """Represents a tradable asset from a market data source."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    prices: Mapped[list[HistoricalPrice]] = relationship(
        "HistoricalPrice", back_populates="asset", cascade="all, delete-orphan"
    )
    allocations: Mapped[list[StrategyAllocation]] = relationship(
        "StrategyAllocation", back_populates="asset", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize asset into API-friendly dictionary."""

        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "category": self.category,
            "source": self.source,
            "currency": self.currency,
        }


class HistoricalPrice(Base):
    """Represents a daily close price for a specific asset."""

    __tablename__ = "historical_prices"
    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_historical_prices_asset_date"),
        CheckConstraint("price > 0", name="ck_historical_prices_positive_price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    asset: Mapped[Asset] = relationship("Asset", back_populates="prices")


class Strategy(Base):
    """Represents a portfolio strategy definition."""

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )

    allocations: Mapped[list[StrategyAllocation]] = relationship(
        "StrategyAllocation", back_populates="strategy", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize strategy and allocations into API-friendly dictionary."""

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "allocations": [allocation.to_dict() for allocation in self.allocations],
        }


class StrategyAllocation(Base):
    """Represents an allocation weight of one asset in one strategy."""

    __tablename__ = "strategy_allocations"
    __table_args__ = (
        UniqueConstraint(
            "strategy_id", "asset_id", name="uq_strategy_allocations_strategy_asset"
        ),
        CheckConstraint(
            "weight >= 0 AND weight <= 1", name="ck_allocations_weight_range"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id"), nullable=False, index=True
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"), nullable=False, index=True
    )
    weight: Mapped[float] = mapped_column(Float, nullable=False)

    strategy: Mapped[Strategy] = relationship("Strategy", back_populates="allocations")
    asset: Mapped[Asset] = relationship("Asset", back_populates="allocations")

    def to_dict(self) -> dict[str, Any]:
        """Serialize strategy allocation into API-friendly dictionary."""

        return {
            "asset_id": self.asset_id,
            "asset_symbol": self.asset.symbol if self.asset else None,
            "asset_name": self.asset.name if self.asset else None,
            "weight": self.weight,
        }
