"""Yahoo Finance historical data downloader."""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd
import yfinance as yf

from etl.downloaders.base_downloader import BaseDownloader

logger = logging.getLogger(__name__)


class YahooDownloader(BaseDownloader):
    """Downloader for Yahoo Finance historical close prices."""

    def download(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Download historical data from Yahoo Finance.

        Args:
            symbol: Yahoo ticker symbol.
            start_date: Inclusive start date.
            end_date: Inclusive end date.

        Returns:
            DataFrame with Yahoo historical OHLCV fields.

        Raises:
            RuntimeError: If Yahoo Finance request fails.
        """

        logger.info(
            "Downloading Yahoo Finance data for %s from %s to %s.",
            symbol,
            start_date,
            end_date,
        )

        try:
            raw_frame = yf.download(
                tickers=symbol,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                auto_adjust=False,
                progress=False,
                threads=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to download Yahoo data for %s.", symbol)
            raise RuntimeError(f"Failed to download Yahoo data for {symbol}") from exc

        frame: pd.DataFrame = pd.DataFrame(raw_frame)
        if frame.empty:
            logger.warning("Yahoo Finance returned empty data for symbol %s.", symbol)
            return frame

        normalized: pd.DataFrame = frame.reset_index()
        if "Date" in normalized.columns:
            normalized["Date"] = pd.to_datetime(normalized["Date"], errors="coerce")

        return normalized
