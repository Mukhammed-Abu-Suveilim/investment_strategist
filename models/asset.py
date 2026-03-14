"""Domain representation for assets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssetDefinition:
    """Represents an asset with metadata used by API/services.

    Attributes:
        id: Database identifier.
        symbol: Canonical internal symbol.
        name: Human-readable asset name.
        category: Asset category.
        source: Data provider source.
        currency: Asset quote currency.
    """

    id: int
    symbol: str
    name: str
    category: str
    source: str
    currency: str
