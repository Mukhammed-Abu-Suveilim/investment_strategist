"""MOEX historical market data downloader."""

from __future__ import annotations

import logging
from datetime import date

import apimoex
import pandas as pd
import requests

from etl.downloaders.base_downloader import BaseDownloader

logger = logging.getLogger(__name__)


class MoexDownloader(BaseDownloader):
    """Downloader for Moscow Exchange historical data.

    Attributes:
        engine: MOEX engine name.
        market: MOEX market name.
        board: MOEX board code.
    """

    def __init__(
        self,
        engine: str = "stock",
        market: str = "index",
        board: str = "SNDX",
    ) -> None:
        self.engine = engine
        self.market = market
        self.board = board

    def download(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Download MOEX historical rows for a ticker.

        This method uses ``apimoex.get_board_history`` for compatibility with
        common MOEX index/fx dataset scripts.

        Args:
            symbol: MOEX ticker symbol.
            start_date: Inclusive start date.
            end_date: Inclusive end date.

        Returns:
            DataFrame with raw MOEX response.

        Raises:
            RuntimeError: If request fails.
        """

        logger.info(
            "Downloading MOEX board history for %s (%s/%s/%s) from %s to %s.",
            symbol,
            self.engine,
            self.market,
            self.board,
            start_date,
            end_date,
        )

        try:
            with requests.Session() as session:
                try:
                    data = apimoex.get_board_history(
                        session,
                        symbol,
                        start=start_date.isoformat(),
                        board=self.board,
                        market=self.market,
                        engine=self.engine,
                        end=end_date.isoformat(),
                    )
                except TypeError:
                    data = apimoex.get_board_history(
                        session,
                        symbol,
                        start=start_date.isoformat(),
                        board=self.board,
                        market=self.market,
                        engine=self.engine,
                    )
        except requests.RequestException as exc:
            logger.exception(
                "Network error while downloading MOEX data for %s.", symbol
            )
            raise RuntimeError(f"Failed to download MOEX data for {symbol}") from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Unexpected error while downloading MOEX data for %s.", symbol
            )
            raise RuntimeError(
                f"Unexpected MOEX downloader failure for {symbol}"
            ) from exc

        frame = pd.DataFrame(data)
        if frame.empty:
            logger.warning("MOEX returned no rows for symbol %s.", symbol)
            return frame

        if "TRADEDATE" in frame.columns:
            frame["TRADEDATE"] = pd.to_datetime(frame["TRADEDATE"], errors="coerce")
            frame = frame[frame["TRADEDATE"].dt.date <= end_date]

        return frame.reset_index(drop=True)
