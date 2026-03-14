"""Master ETL pipeline.

This module orchestrates downloading data from MOEX and Yahoo Finance,
standardizing source formats, forward-filling daily series, converting
USD assets to RUB, and loading results into the database.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import pandas as pd

from config import settings
from data.database import create_all_tables, get_session
from data.queries import bulk_upsert_prices, upsert_asset
from etl.downloaders.moex_downloader import MoexDownloader
from etl.downloaders.yahoo_downloader import YahooDownloader
from etl.pipeline.currency_normalizer import normalize_to_rub
from etl.transformers.standardize_moex import StandardizeMoexTransformer
from etl.transformers.standardize_yahoo import StandardizeYahooTransformer
from etl.utils.calendar_utils import create_master_calendar, forward_fill_prices

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AssetSpec:
    """Asset extraction definition used by ETL pipeline."""

    symbol: str
    name: str
    category: str
    source: str
    currency: str
    provider_symbol: str


MOEX_ASSETS: tuple[AssetSpec, ...] = (
    AssetSpec(
        symbol="IMOEX",
        name="Moscow Exchange Index",
        category="Equity",
        source="MOEX",
        currency="RUB",
        provider_symbol="IMOEX",
    ),
    AssetSpec(
        symbol="RGBITR",
        name="Russian Government Bond Total Return Index",
        category="Fixed Income",
        source="MOEX",
        currency="RUB",
        provider_symbol="RGBITR",
    ),
)

YAHOO_USD_ASSETS: tuple[AssetSpec, ...] = (
    AssetSpec(
        symbol="GOLD_RUB",
        name="Gold Futures (normalized to RUB)",
        category="Commodity",
        source="YAHOO",
        currency="RUB",
        provider_symbol="GC=F",
    ),
)


USD_RUB_SYMBOL = "RUB=X"


def _get_today_date() -> date:
    """Return timezone-naive current UTC date."""

    return pd.Timestamp.utcnow().date()


def _download_moex_series(
    symbol: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    downloader = MoexDownloader(engine="stock", market="index")
    transformer = StandardizeMoexTransformer()
    raw = downloader.download(symbol=symbol, start_date=start_date, end_date=end_date)
    return transformer.transform(raw)


def _download_yahoo_series(
    symbol: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    downloader = YahooDownloader()
    transformer = StandardizeYahooTransformer()
    raw = downloader.download(symbol=symbol, start_date=start_date, end_date=end_date)
    return transformer.transform(raw)


def _prepare_daily_series(
    series_df: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    master_dates = create_master_calendar(start_date=start_date, end_date=end_date)
    filled = forward_fill_prices(series_df, master_dates)
    return filled.dropna(subset=["price"]).reset_index(drop=True)


def run_full_etl() -> None:
    """Run the complete ETL workflow.

    The workflow is idempotent and can safely be executed multiple times.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    start_date = settings.start_date
    end_date = _get_today_date()

    logger.info("Starting full ETL from %s to %s.", start_date, end_date)
    create_all_tables()

    usd_rub_df = _download_yahoo_series(
        symbol=USD_RUB_SYMBOL,
        start_date=start_date,
        end_date=end_date,
    )
    usd_rub_daily = _prepare_daily_series(
        usd_rub_df, start_date=start_date, end_date=end_date
    )

    with get_session() as session:
        for spec in MOEX_ASSETS:
            logger.info("Processing MOEX asset %s.", spec.symbol)
            standardized = _download_moex_series(
                symbol=spec.provider_symbol,
                start_date=start_date,
                end_date=end_date,
            )
            daily = _prepare_daily_series(
                standardized, start_date=start_date, end_date=end_date
            )
            asset = upsert_asset(
                session=session,
                symbol=spec.symbol,
                name=spec.name,
                category=spec.category,
                source=spec.source,
                currency=spec.currency,
            )
            bulk_upsert_prices(session=session, asset_id=asset.id, prices_df=daily)

        for spec in YAHOO_USD_ASSETS:
            logger.info("Processing Yahoo USD asset %s.", spec.symbol)
            standardized = _download_yahoo_series(
                symbol=spec.provider_symbol,
                start_date=start_date,
                end_date=end_date,
            )
            usd_daily = _prepare_daily_series(
                standardized, start_date=start_date, end_date=end_date
            )
            rub_daily = normalize_to_rub(
                usd_prices_df=usd_daily, usd_rub_rates_df=usd_rub_daily
            )

            asset = upsert_asset(
                session=session,
                symbol=spec.symbol,
                name=spec.name,
                category=spec.category,
                source=spec.source,
                currency=spec.currency,
            )
            bulk_upsert_prices(session=session, asset_id=asset.id, prices_df=rub_daily)

    logger.info("ETL completed successfully.")


def main() -> None:
    """CLI entrypoint for ``uv run etl``."""

    run_full_etl()


if __name__ == "__main__":
    main()
