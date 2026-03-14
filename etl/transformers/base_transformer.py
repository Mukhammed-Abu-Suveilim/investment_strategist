"""Abstract transformer contract for ETL standardization."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseTransformer(ABC):
    """Base class for raw source DataFrame standardization."""

    @abstractmethod
    def transform(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Transform provider-specific columns into standardized schema.

        Args:
            raw_df: Raw provider DataFrame.

        Returns:
            DataFrame with standardized columns ``date`` and ``price``.
        """
