"""Domain representations for strategies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyLeg:
    """One strategy allocation leg.

    Attributes:
        asset_id: Asset identifier.
        asset_symbol: Optional asset symbol.
        weight: Allocation weight in range [0, 1].
    """

    asset_id: int
    asset_symbol: str
    weight: float


@dataclass(frozen=True)
class StrategyDefinition:
    """Strategy definition with allocation legs.

    Attributes:
        id: Strategy identifier.
        name: Strategy display name.
        description: Human-readable description.
        allocations: Strategy allocation legs.
    """

    id: int
    name: str
    description: str
    allocations: list[StrategyLeg]
