"""MOEX raw data standardization."""

from __future__ import annotations

import logging

import pandas as pd

from etl.transformers.base_transformer import BaseTransformer

logger = logging.getLogger(__name__)


class StandardizeMoexTransformer(BaseTransformer):
    """Transform MOEX payload into standardized columns.

    Supports both candle-style fields (``begin``, ``close``) and
    board-history fields (``TRADEDATE``, ``CLOSE``).
    """

    def transform(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Convert MOEX frame into ``date`` and ``price`` schema.

        Args:
            raw_df: Raw MOEX DataFrame.

        Returns:
            Standardized DataFrame with ``date`` and ``price`` columns.

        Raises:
            ValueError: If required date/price columns are absent.
        """

        if raw_df.empty:
            return pd.DataFrame(columns=["date", "price"])

        date_column: str | None = None
        price_column: str | None = None

        if "begin" in raw_df.columns and "close" in raw_df.columns:
            date_column = "begin"
            price_column = "close"
        elif "TRADEDATE" in raw_df.columns and "CLOSE" in raw_df.columns:
            date_column = "TRADEDATE"
            price_column = "CLOSE"

        if date_column is None or price_column is None:
            raise ValueError(
                "MOEX data must include either ['begin', 'close'] or ['TRADEDATE', 'CLOSE'] columns."
            )

        frame = raw_df[[date_column, price_column]].rename(
            columns={date_column: "date", price_column: "price"}
        )
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
        frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
        frame = frame.dropna(subset=["date", "price"])
        frame = frame.sort_values("date").drop_duplicates(subset=["date"], keep="last")

        logger.debug("Standardized %s MOEX rows.", len(frame))
        return frame.reset_index(drop=True)
