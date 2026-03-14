"""Yahoo Finance raw data standardization."""

from __future__ import annotations

import pandas as pd

from etl.transformers.base_transformer import BaseTransformer


class StandardizeYahooTransformer(BaseTransformer):
    """Transform Yahoo payload into standardized ``date``/``price`` format."""

    @staticmethod
    def _flatten_columns(raw_df: pd.DataFrame) -> pd.DataFrame:
        """Flatten possible MultiIndex columns from yfinance.

        Args:
            raw_df: Raw Yahoo DataFrame.

        Returns:
            DataFrame with single-level columns.
        """

        frame = raw_df.copy()
        if isinstance(frame.columns, pd.MultiIndex):
            flattened_columns = []
            for first, second in frame.columns.to_list():
                first_name = str(first).strip()
                second_name = str(second).strip()
                if first_name.lower() in {"close", "open", "high", "low", "volume"}:
                    flattened_columns.append(first_name)
                elif first_name.lower() == "date":
                    flattened_columns.append("Date")
                elif second_name and second_name.lower() != "":
                    flattened_columns.append(second_name)
                else:
                    flattened_columns.append(first_name)
            frame.columns = flattened_columns

        return frame

    def transform(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Convert Yahoo frame into ``date`` and ``price`` schema.

        Args:
            raw_df: Raw Yahoo DataFrame.

        Returns:
            Standardized DataFrame with ``date`` and ``price`` columns.

        Raises:
            ValueError: If required columns are missing.
        """

        if raw_df.empty:
            return pd.DataFrame(columns=["date", "price"])

        frame = self._flatten_columns(raw_df)

        source_date_column = "Date" if "Date" in frame.columns else "date"
        source_price_column = "Close" if "Close" in frame.columns else "close"

        if (
            source_date_column not in frame.columns
            or source_price_column not in frame.columns
        ):
            raise ValueError("Yahoo data must include date and close columns.")

        standardized = frame[[source_date_column, source_price_column]].rename(
            columns={source_date_column: "date", source_price_column: "price"}
        )
        standardized["date"] = pd.to_datetime(
            standardized["date"], errors="coerce"
        ).dt.date
        standardized["price"] = pd.to_numeric(standardized["price"], errors="coerce")
        standardized = standardized.dropna(subset=["date", "price"])
        standardized = standardized.sort_values("date").drop_duplicates(
            subset=["date"],
            keep="last",
        )
        return standardized.reset_index(drop=True)
