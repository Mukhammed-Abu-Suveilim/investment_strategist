"""Abstract downloader contract for ETL data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class BaseDownloader(ABC):
    """Base class for all market data downloaders."""

    @abstractmethod
    def download(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Download historical data for a symbol.

        Args:
            symbol: Ticker or instrument code in provider-specific format.
            start_date: Inclusive start date.
            end_date: Inclusive end date.

        Returns:
            Raw provider-specific DataFrame.
        """
